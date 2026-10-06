"""Auditable counter/timer-only overlay for the immutable accepted v10 baseline."""
def overlay(name, s):
    if name == 'ingestion/src/durable.rs':
        s=s.replace('pub metadata_reads: u64,', '''pub metadata_reads: u64,
    pub global_records_validated: u64,
    pub partition_records_validated: u64,
    pub global_history_entries_decoded: u64,
    pub partition_history_entries_decoded: u64,
    pub guarded_leases: u64,
    pub guard_validation_ns: u64,
    pub guard_action_ns: u64,
    pub receipt_coordinates_copied: u64,''')
        s=s.replace('state.validate(source, format_expected != FORMAT_VERSION)?;', '''work.global_history_entries_decoded += state.recovery.snapshot.recent_batches.len() as u64;
        state.validate(source, format_expected != FORMAT_VERSION)?;
        work.global_records_validated += 1;''')
        s=s.replace('let part: PartitionState = serde_json::from_slice(&payload)?;', '''let part: PartitionState = serde_json::from_slice(&payload)?;
        work.partition_history_entries_decoded += part.recent.len() as u64;''')
        s=s.replace('state.validate(&state.source, false)?;\n        Ok(())\n    }\n    fn read_local', 'state.validate(&state.source, false)?;\n        work.partition_records_validated += state.partitions.contains_key(&p) as u64;\n        Ok(())\n    }\n    fn read_local')
        s=s.replace('before.offsets = self.cut.as_ref().ok_or(Error::StaleSnapshot)?.1.clone();', '''before.offsets = self.cut.as_ref().ok_or(Error::StaleSnapshot)?.1.clone();
        self.work.receipt_coordinates_copied += before.offsets.len() as u64;''')
        s=s.replace('let mut offsets = before.offsets.clone();', 'self.work.receipt_coordinates_copied += before.offsets.len() as u64;\n        let mut offsets = before.offsets.clone();')
        s=s.replace('self.cut = Some((after.sequence, after.offsets.clone()));', 'self.work.receipt_coordinates_copied += after.offsets.len() as u64;\n        self.cut = Some((after.sequence, after.offsets.clone()));')
        # Only the guard implementation, not its trait declaration.
        start=s.index('    fn guard<T>(',s.index('impl DurableStore for SqliteStore'))
        end=s.index('    fn authorize<T>(',start)
        guard=s[start:end].replace('self.work.transactions += 1;', 'let guard_started = std::time::Instant::now();\n        self.work.transactions += 1;',1)
        guard=guard.replace('state.fence(token)?;', 'state.fence(token)?;\n            self.work.guarded_leases += 1;')
        guard=guard.replace('let result = action()?;', '''self.work.guard_validation_ns += guard_started.elapsed().as_nanos() as u64;
        let action_started = std::time::Instant::now();
        let result = action()?;
        self.work.guard_action_ns += action_started.elapsed().as_nanos() as u64;''')
        s=s[:start]+guard+s[end:]
    elif name == 'ingestion/src/coordination.rs':
        s=s.replace('pub batching_wait_ms: u64,', 'pub batching_wait_ms: u64,\n    pub queue_records_serialized: u64,')
        s=s.replace('let bytes = delivery.bytes()?;', 'self.metrics.queue_records_serialized += delivery.records.len() as u64;\n        let bytes = delivery.bytes()?;')
        s=s.replace('let tail_bytes = tail.bytes()?;', 'self.metrics.queue_records_serialized += tail.records.len() as u64;\n            let tail_bytes = tail.bytes()?;')
        s=s.replace('self.metrics.queued_bytes -= d.bytes()', 'self.metrics.queue_records_serialized += d.records.len() as u64;\n        self.metrics.queued_bytes -= d.bytes()')
        s=s.replace('                metrics.queued_bytes -= d.bytes()', 'metrics.queue_records_serialized += d.records.len() as u64;\n                metrics.queued_bytes -= d.bytes()')
    else: raise ValueError(name)
    return s
NAMES=['ingestion/src/durable.rs','ingestion/src/coordination.rs']
