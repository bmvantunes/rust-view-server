"""Guard selected production sources; legacy experiment and private backend are explicit."""
from pathlib import Path
import re
root=Path(__file__).resolve().parent.parent
errors=[]
for p in (root/'native/src').rglob('*.rs'):
    rel=p.relative_to(root/'native/src').as_posix()
    if rel=='product_engine.rs' or rel.startswith(('product_engine/','differential/')):continue
    for no,line in enumerate(p.read_text().splitlines(),1):
        if re.search(r'\b(?:differential_dataflow|timely)::|\b(?:InputSession|VecCollection|TraceAgent)\s*[<:]' ,line):errors.append(f'{rel}:{no}: engine implementation type crosses boundary')
for p in [root/'native/src/source.rs',root/'native/src/topic.rs']:
    if re.search(r'crate::(?:product_engine|differential|viewport|common)::',p.read_text()):errors.append(f'{p.name}: source/retained ownership depends on execution')
for p in (root/'native/tests/support').glob('*.rs'):
    if re.search(r'\b(?:ProductCore|DifferentialProductEngine|SelectedProductEngine|sortable_token|ViewportHub|MembershipEngine)\b|(?:product_engine|differential_dataflow|timely|viewport|common)::',p.read_text()):errors.append(f'{p.name}: independent reference imports selected implementation')
for p in (root/'ingestion/src').rglob('*.rs'):
    if re.search(r'\b(?:differential_dataflow|timely|product_engine|viewport|common)::|\b(?:InputSession|Collection|Arrangement|Scope|TraceAgent)\s*[<:]',p.read_text()): errors.append(f'{p.name}: source adapter imports engine implementation')
for p in (root/'native/src').rglob('*.rs'):
    if re.search(r'\b(?:rdkafka|reqwest|prost|rusqlite|libsqlite3_sys)::|\b(?:BorrowedMessage|TopicPartitionList|ConsumerContext)\b',p.read_text()): errors.append(f'{p.name}: Kafka/decoder implementation crosses product boundary')
for p in [root/'ingestion/src/durable.rs']:
    if p.exists() and re.search(r'engine_contract::|\b(?:ProductEngine|SelectedProductEngine|ProductCore|KafkaSource)\b|\brdkafka::',p.read_text()):
        errors.append(f'{p.name}: durable store imports evaluator or Kafka')
if errors:raise SystemExit('\n'.join(errors))
print('engine boundary source guards passed')
