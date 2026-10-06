#!/usr/bin/env python3
"""Small scan-based retention oracle, intentionally independent of Rust indexes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import json
import unittest

MAX_FUTURE_SKEW_MS = 300_000


@dataclass(frozen=True)
class Retained:
    source_key: str
    payload: dict
    age_origin_ms: int | None
    order: int


class TopicModel:
    """One logical topic. Recomputes expiry and caps by scanning current rows."""

    def __init__(self, *, max_age_ms=None, max_messages=None, count_scope=None):
        self.max_age_ms = max_age_ms
        self.max_messages = max_messages
        self.count_scope = count_scope
        self.current: dict[str, Retained] = {}
        self.owners: dict[str, tuple[int, str]] = {}
        self.next_offset = {0: 0, 1: 0}
        self.order = 0
        self.reference_ms = 0
        self.source_sequence = 0
        self.maintenance_sequence = 0
        if (max_messages is None) != (count_scope is None):
            raise ValueError("count cap and scope must be configured together")

    def admit(self, partition, offset, row_id, source_key, payload, timestamp_ms, reference_ms):
        self.reference_ms = max(self.reference_ms, reference_ms)
        if offset < self.next_offset[partition]:
            return False  # committed replay cannot refresh age or order
        identity = (partition, source_key)
        if row_id in self.owners and self.owners[row_id] != identity:
            raise ValueError("row ownership changed")
        self.owners[row_id] = identity
        self.order += 1
        origin = None
        if payload is not None and self.max_age_ms is not None:
            if timestamp_ms is None or timestamp_ms < 0:
                raise ValueError("missing supported Kafka timestamp")
            if timestamp_ms > self.reference_ms + MAX_FUTURE_SKEW_MS:
                raise ValueError("timestamp too far in future")
            origin = timestamp_ms
        if payload is None:
            self.current.pop(row_id, None)
        else:
            # One current value per (topic,rowId), regardless of count cap.
            self.current[row_id] = Retained(source_key, copy.deepcopy(payload), origin, self.order)
            if self._expired(self.current[row_id], self.reference_ms):
                self.current.pop(row_id, None)
        self.next_offset[partition] = offset + 1
        self.source_sequence += 1
        self._enforce_count_caps()
        return True

    def _expired(self, row, reference_ms):
        return self.max_age_ms is not None and row.age_origin_ms + self.max_age_ms <= reference_ms

    def advance(self, wall_ms):
        reference = max(self.reference_ms, wall_ms)
        expired = [key for key, row in self.current.items() if self._expired(row, reference)]
        self.reference_ms = reference
        if expired:
            for key in expired:
                self.current.pop(key, None)
            self.maintenance_sequence += 1
        return len(expired)

    def _enforce_count_caps(self):
        if self.max_messages is None:
            return
        if self.count_scope == "topic":
            while len(self.current) > self.max_messages:
                oldest = min(self.current, key=lambda key: (self.current[key].order, key))
                self.current.pop(oldest)
        elif self.count_scope == "per_key":
            keys = {row.source_key for row in self.current.values()}
            for source_key in keys:
                while sum(row.source_key == source_key for row in self.current.values()) > self.max_messages:
                    candidates = [key for key, row in self.current.items() if row.source_key == source_key]
                    oldest = min(candidates, key=lambda key: (self.current[key].order, key))
                    self.current.pop(oldest)
        else:
            raise ValueError("unknown count scope")

    def snapshot(self):
        return {
            "current": {key: asdict(row) for key, row in sorted(self.current.items())},
            "owners": {key: list(value) for key, value in sorted(self.owners.items())},
            "next_offset": {str(key): value for key, value in sorted(self.next_offset.items())},
            "order": self.order,
            "reference_ms": self.reference_ms,
            "source_sequence": self.source_sequence,
            "maintenance_sequence": self.maintenance_sequence,
        }

    @classmethod
    def restore(cls, snapshot, *, max_age_ms=None, max_messages=None, count_scope=None):
        model = cls(max_age_ms=max_age_ms, max_messages=max_messages, count_scope=count_scope)
        model.current = {key: Retained(**value) for key, value in snapshot["current"].items()}
        model.owners = {key: tuple(value) for key, value in snapshot["owners"].items()}
        model.next_offset = {int(key): value for key, value in snapshot["next_offset"].items()}
        model.order = snapshot["order"]
        model.reference_ms = snapshot["reference_ms"]
        model.source_sequence = snapshot["source_sequence"]
        model.maintenance_sequence = snapshot["maintenance_sequence"]
        return model


class RetentionReferenceTests(unittest.TestCase):
    def test_global_n_plus_one_across_partitions_and_replacement_no_history(self):
        model = TopicModel(max_messages=2, count_scope="topic")
        model.admit(0, 0, "a", "key-a", {"v": 1}, None, 10)
        model.admit(1, 0, "b", "key-b", {"v": 2}, None, 10)
        model.admit(0, 1, "c", "key-c", {"v": 3}, None, 10)
        self.assertEqual(set(model.current), {"b", "c"})
        model.admit(0, 2, "c", "key-c", {"v": 4}, None, 11)
        self.assertEqual(len(model.current), 2)
        self.assertEqual(model.current["c"].payload, {"v": 4})
        model.advance(100)
        self.assertEqual(model.current["c"].payload, {"v": 4})

    def test_per_key_global_across_partitions_and_nonbinding_cap(self):
        model = TopicModel(max_messages=1, count_scope="per_key")
        model.admit(0, 0, "x1", "X", {"v": 1}, None, 10)
        model.admit(1, 0, "y1", "Y", {"v": 2}, None, 10)
        model.admit(0, 1, "x2", "X", {"v": 3}, None, 10)
        self.assertEqual(set(model.current), {"x2", "y1"})
        nonbinding = TopicModel(max_messages=2, count_scope="per_key")
        nonbinding.admit(0, 0, "current", "X", {"v": 1}, None, 10)
        nonbinding.admit(0, 1, "current", "X", {"v": 2}, None, 11)
        self.assertEqual(len(nonbinding.current), 1)
        self.assertEqual(nonbinding.current["current"].payload, {"v": 2})

    def test_exact_boundary_restart_replay_late_and_stale_generation(self):
        model = TopicModel(max_age_ms=10)
        model.admit(0, 0, "same", "key", {"v": 1}, 100, 100)
        saved = model.snapshot()
        restored = TopicModel.restore(saved, max_age_ms=10)
        self.assertFalse(restored.admit(0, 0, "same", "key", {"v": 1}, 100, 100))
        self.assertEqual(restored.current["same"].age_origin_ms, 100)
        self.assertEqual(restored.advance(109), 0)
        restored.admit(0, 1, "same", "key", {"v": 2}, 105, 105)
        self.assertEqual(restored.advance(110), 0)  # stale expiry for v1 cannot remove v2
        self.assertEqual(restored.current["same"].payload, {"v": 2})
        self.assertEqual(restored.advance(115), 1)
        self.assertNotIn("same", restored.current)
        restored.admit(0, 2, "boundary", "key", {"v": 3}, 200, 200)
        self.assertEqual(restored.advance(209), 0)
        self.assertEqual(restored.advance(210), 1)
        restored.admit(0, 3, "late", "key", {"v": 4}, 50, 300)
        self.assertNotIn("late", restored.current)

    def test_future_bound_clock_rollback_and_topic_isolation(self):
        model = TopicModel(max_age_ms=1_000)
        with self.assertRaisesRegex(ValueError, "future"):
            model.admit(0, 0, "bad", "key", {"v": 0}, 400_001, 100_000)
        self.assertEqual(model.next_offset[0], 0)
        model.admit(0, 0, "ok", "key", {"v": 1}, 100_000, 100_000)
        model.advance(101_000)
        self.assertEqual(model.advance(99_000), 0)
        other_topic = TopicModel(max_messages=1, count_scope="topic")
        other_topic.admit(0, 0, "ok", "key", {"v": 9}, None, 1)
        self.assertEqual(model.current, {})
        self.assertEqual(other_topic.current["ok"].payload, {"v": 9})


if __name__ == "__main__":
    unittest.main(verbosity=2)
