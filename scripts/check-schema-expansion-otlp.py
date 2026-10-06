"""Read captured OTLP protobuf wire fields without importing the service decoder.

Field numbers checked against the pinned opentelemetry-proto 0.33.0 schemas.
This is a review evidence extractor; it does not modify application code.
"""
import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path


def varint(blob, pos):
    value = 0
    for shift in range(0, 70, 7):
        assert pos < len(blob), "truncated varint"
        byte = blob[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise AssertionError("oversize varint")


def fields(blob):
    found = defaultdict(list)
    pos = 0
    while pos < len(blob):
        key, pos = varint(blob, pos)
        tag, wire = key >> 3, key & 7
        assert tag > 0
        if wire == 0:
            value, pos = varint(blob, pos)
        elif wire in (1, 5):
            length = 8 if wire == 1 else 4
            value = blob[pos:pos + length]
            assert len(value) == length
            pos += length
        elif wire == 2:
            length, pos = varint(blob, pos)
            value = blob[pos:pos + length]
            assert len(value) == length
            pos += length
        else:
            raise AssertionError(f"unsupported protobuf wire kind {wire}")
        found[tag].append((wire, value))
    return found


def messages(parsed, tag):
    values = parsed.get(tag, [])
    assert all(wire == 2 for wire, _ in values)
    return [value for _, value in values]


def one(parsed, tag, default=None):
    values = parsed.get(tag, [])
    assert len(values) <= 1
    return values[0][1] if values else default


def attributes(values):
    out = {}
    for value in values:
        key_value = fields(value)
        key = one(key_value, 1, b"").decode()
        av = fields(one(key_value, 2, b""))
        if 1 in av:
            scalar = one(av, 1).decode()
        elif 2 in av:
            scalar = bool(one(av, 2))
        elif 3 in av:
            scalar = one(av, 3)
            scalar -= (1 << 64) if scalar >= (1 << 63) else 0
        elif 4 in av:
            scalar = struct.unpack("<d", one(av, 4))[0]
        else:
            raise AssertionError("non-scalar selected attribute")
        assert key not in out
        out[key] = scalar
    return out


def fixed64(parsed, tag):
    return int.from_bytes(one(parsed, tag, bytes(8)), "little")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("captures", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    delivery = json.loads((args.captures / "telemetry-receipts.json").read_text())
    spans, metrics = [], []
    for index, receipt in enumerate(delivery):
        kind = receipt["path"].rsplit("/", 1)[-1]
        name = f"otlp-{index}-{kind}.pb"
        blob = (args.captures / name).read_bytes()
        assert len(blob) == receipt["bytes"]
        assert hashlib.sha256(blob).hexdigest() == receipt["sha256"]
        for resource_blob in messages(fields(blob), 1):
            resource = fields(resource_blob)
            resource_attributes = attributes(messages(fields(one(resource, 1, b"")), 1))
            instance = resource_attributes.get("service.instance.id")
            assert instance
            for scope_blob in messages(resource, 2):
                for item_blob in messages(fields(scope_blob), 2):
                    item = fields(item_blob)
                    if kind == "traces":
                        span_name = one(item, 5, b"").decode()
                        if not span_name.startswith("retention_"):
                            continue
                        attrs = attributes(messages(item, 9))
                        assert len(attrs) <= 8
                        assert len(messages(item, 11)) <= 4
                        assert len(messages(item, 13)) <= 4
                        assert attrs.get("topic") in ("shit", "nested_positions", "nested_third")
                        assert fixed64(item, 8) >= fixed64(item, 7)
                        spans.append({"capture": name, "instance": instance,
                                      "name": span_name, "attributes": attrs,
                                      "trace_id": one(item, 1).hex(),
                                      "span_id": one(item, 2).hex(),
                                      "start_ns": str(fixed64(item, 7)),
                                      "end_ns": str(fixed64(item, 8))})
                    else:
                        metric_name = one(item, 1, b"").decode()
                        if not metric_name.startswith("view_server.retention."):
                            continue
                        data_tag = 5 if 5 in item else 7
                        assert data_tag in item
                        for point_blob in messages(fields(one(item, data_tag)), 1):
                            point = fields(point_blob)
                            attrs = attributes(messages(point, 7))
                            assert set(attrs) <= {"topic"}
                            if attrs:
                                assert attrs["topic"] in ("shit", "nested_positions", "nested_third")
                            value = (struct.unpack("<q", one(point, 6))[0]
                                     if 6 in point else struct.unpack("<d", one(point, 4))[0])
                            metrics.append({"capture": name, "instance": instance,
                                            "name": metric_name, "attributes": attrs,
                                            "value": value, "time_ns": str(fixed64(point, 3))})
    maintenance = [span for span in spans if span["name"] == "retention_maintenance"]
    assert maintenance, "missing actual maintenance span export"
    for name in ("view_server.retention.maintenance.transactions", "view_server.retention.evicted.rows"):
        assert any(metric["name"] == name and metric["value"] > 0 for metric in metrics)
    maxima = {}
    for metric in metrics:
        if metric["name"] in ("view_server.retention.maintenance.transactions", "view_server.retention.evicted.rows"):
            key = (metric["instance"], metric["name"], metric["attributes"].get("topic"))
            maxima[key] = max(maxima.get(key, 0), metric["value"])
    result = {"status": "PASS", "scope": "Actual fresh export captures, decoded with independent protobuf field reader",
              "capture_files_verified": len(delivery), "retention_spans": len(spans),
              "maintenance_spans": len(maintenance), "retention_metric_points": len(metrics),
              "bounded_span_attributes": True, "metric_attribute_keys": ["topic"],
              "counter_maxima_per_instance_not_summed_across_exports": [
                  {"instance": key[0], "metric": key[1], "topic": key[2], "maximum": value}
                  for key, value in sorted(maxima.items())],
              "spans": spans, "metric_points": metrics, "raw_capture_receipts": delivery}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("spans", "metric_points", "raw_capture_receipts")}, indent=2))


if __name__ == "__main__":
    main()
