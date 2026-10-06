//! Common v10/v11 local harness. One coordinator, exact oracle outside timings.
use product_source_ingestion::{coordination::{Authority,Record,Partition,Delivery,BoundedQueue,Limits,BatchLimits},durable::{SourceIdentity,SqliteStore,DurableStore},durable_coordinator::{Session,DurableCoordinator}};
use rust_differential_product_core::{engine_contract::SelectedProductEngine,product::*,source::*,topic::RowId};
use sha2::{Digest,Sha256};
use std::{collections::BTreeMap,sync::{Arc,Mutex},time::{Instant,Duration},path::Path};
fn row(i:usize)->ProductRow {ProductRow{id:format!("row-{i:09}"),category:if i%2==0{"a"}else{"b"}.into(),label:OptionalString::Value("exact\0日本語".into()),quantity:ExactInteger::parse("9223372036854775807").unwrap(),amount:ExactDecimal::parse(&format!("{i}.0001")).unwrap()}}
fn record(p:u32,offset:u64,mutation:ProductMutation)->Record{Record::new(SourceMutation{partition:p,offset,mutation})}
fn main(){
 let args:Vec<_>=std::env::args().collect();let path=Path::new(&args[1]);let p:usize=args[2].parse().unwrap();let l:usize=args[3].parse().unwrap();let cap:usize=args[4].parse().unwrap();let mode=&args[5];
 let n=10000usize;let seed=90210usize;assert!([1,16,256].contains(&p)&&l>0&&l<=p&&[1,32,256,1024].contains(&cap));assert!(mode=="dense"||mode=="sparse");
 let identity=SourceIdentity{incarnation:"v11-controlled-topic".into(),topic:"products".into(),schema:"product-v1".into()};
 let setup=Instant::now();let mut store=SqliteStore::create(path,identity.clone()).unwrap();
 let tokens=(0..p).map(|i|store.acquire(i as u32,"seed").unwrap().0).collect::<Vec<_>>();
 let mut expected:BTreeMap<String,ProductRow>=(0..n).map(|i|{let r=row(i);(r.id.clone(),r)}).collect();
 let mut offsets=vec![0u64;p];let mut seq=0;
 for part in 0..p {
  let rows=(part..n).step_by(p).collect::<Vec<_>>();
  for chunk in rows.chunks(1000){let records=chunk.iter().map(|i|{let r=record(part as u32,offsets[part],ProductMutation::Upsert{row:row(*i)});offsets[part]+=1;r}).collect::<Vec<_>>();store.commit(&tokens[part],seq,&records).unwrap();seq+=1;}
  let records=(0..256).map(|_|{let r=record(part as u32,offsets[part],ProductMutation::Upsert{row:row(part)});offsets[part]+=1;r}).collect::<Vec<_>>();store.commit(&tokens[part],seq,&records).unwrap();seq+=1;
 }
 for _ in 0..256 {store.commit(&tokens[0],seq,&[record(0,offsets[0],ProductMutation::Upsert{row:row(0)})]).unwrap();offsets[0]+=1;seq+=1;}
 for t in &tokens {store.release(t).unwrap();}drop(store);
 let store=SqliteStore::open(path,identity.clone()).unwrap();let authority=Authority::default();let shared=Arc::new(Mutex::new(Session::new(store,"measure".into(),authority)));
 let leases=(0..l).map(|i|shared.lock().unwrap().acquire(Partition{topic:"products".into(),partition:i as u32}).unwrap().0).collect::<Vec<_>>();
 let mut c:DurableCoordinator<SelectedProductEngine,SqliteStore>=DurableCoordinator::new(shared.clone()).unwrap();
 let queries=[("top",false,0,false,16),("deep",true,n/2,false,16),("category",false,n/4,true,16),("full",false,0,false,20000)];
 for (name,desc,start,filtered,limit) in queries {c.command(ProductCommand::Open{subscription:name.into(),query:Query{where_expr:if filtered{Expr::Condition(Condition::CategoryEquals("a".into()))}else{Expr::True},direction:if desc{Direction::Descending}else{Direction::Ascending},offset:start as u64,limit}}).unwrap();}
 let mut q=BoundedQueue::new(Limits{batches:4,bytes:4*1024*1024,events:2048}).unwrap();q.set_batch_limits(BatchLimits{records:cap,bytes:2*1024*1024,latency_ms:if mode=="sparse" {4}else{1000}}).unwrap();
 println!("{}",serde_json::json!({"kind":"setup","P":p,"L":shared.lock().unwrap().leases().len(),"H":256,"rows":n,"cap":cap,"mode":mode,"seed":seed,"row_distribution":(0..p).map(|i|(i..n).step_by(p).count()).collect::<Vec<_>>(),"sqlite":rusqlite::version(),"queries":queries,"warmup_batches":8,"samples":32,"setup_ns":setup.elapsed().as_nanos()}));
 let origin=Instant::now();
 for sample in 0..40usize {
  let part=sample%l;let count=if mode=="sparse" {1}else{cap};let arrival=Instant::now();let mut arrivals=Vec::new();let mut keys=std::collections::BTreeSet::new();let mut build_ns=0u128;
  let serial_before=q.metrics().queue_records_serialized;
  for j in 0..count {
   let build=Instant::now();arrivals.push(build);
   let available=(part..n).step_by(p).count();let i=part+p*((seed+sample*37+j*13)%available);let id=row(i).id;
   let mutation=match sample%6 {
    0=>ProductMutation::Upsert{row:row(part+p*(n+sample*cap+j))},
    1=>{let mut r=row(i);r.amount=ExactDecimal::parse(&format!("-{}.0001",i+1)).unwrap();ProductMutation::Upsert{row:r}},
    2=>ProductMutation::Delete{key:RowId(id.clone())},
    3=>ProductMutation::Upsert{row:expected.get(&id).cloned().unwrap_or_else(||row(i))},
    4=>{let mut r=expected.get(&id).cloned().unwrap_or_else(||row(i));r.label=OptionalString::Value(format!("selected-{sample}"));ProductMutation::Upsert{row:r}},
    _=>{let mut r=expected.get(&id).cloned().unwrap_or_else(||row(i));r.category=if r.category=="a"{"b"}else{"a"}.into();ProductMutation::Upsert{row:r}}
   };
   match &mutation{ProductMutation::Upsert{row}=>{keys.insert(row.id.clone());expected.insert(row.id.clone(),row.clone());},ProductMutation::Delete{key}=>{keys.insert(key.0.clone());expected.remove(&key.0);}}
   q.push_record(Delivery{lease:leases[part].clone(),records:vec![record(part as u32,offsets[part],mutation)]},origin.elapsed().as_millis() as u64).unwrap();offsets[part]+=1;build_ns+=build.elapsed().as_nanos();
  }
  let queue_peak=q.metrics().queued_bytes;let building_peak=q.metrics().building_bytes;
  // Real bounded wait, with the same production queue deadline. No sleep in semantic tests.
  while q.ready(origin.elapsed().as_millis() as u64).is_none(){std::thread::sleep(Duration::from_micros(200));}
  let service=Instant::now();let waits=arrivals.iter().map(|t|service.duration_since(*t).as_nanos()).collect::<Vec<_>>();
  // Slow construction may itself deadline-flush; drain every completed batch.
  let mut batches=0;let mut records=0;let mut sizes=Vec::new();let mut durable=0;let mut reconcile=0;
  shared.lock().unwrap().reset_storage_work();
  while q.metrics().queued_events>0 {
   while q.ready(origin.elapsed().as_millis() as u64).is_none(){std::thread::sleep(Duration::from_micros(200));}
   let d=q.front().unwrap().clone();let bd=c.metrics().durable_transaction_ns;let be=c.metrics().engine_reconciliation_ns;
   c.apply(&d).unwrap();durable+=c.metrics().durable_transaction_ns-bd;reconcile+=c.metrics().engine_reconciliation_ns-be;records+=d.records.len();sizes.push(d.records.len());batches+=1;q.record_completed();q.pop();
  }
  let apply_work=shared.lock().unwrap().storage_work();shared.lock().unwrap().reset_storage_work();
  let read=Instant::now();let results=queries.iter().map(|(name,_,_,_,_)|c.read(name).unwrap().unwrap().result).collect::<Vec<_>>();let read_ns=read.elapsed().as_nanos();let completed=Instant::now();
  let query_work=shared.lock().unwrap().storage_work();shared.lock().unwrap().reset_storage_work();
  let auth=Instant::now();c.commit_offset(&leases[part],|next|{assert_eq!(next,offsets[part]);Ok(())}).unwrap();let authorize_ns=auth.elapsed().as_nanos();let authorize_work=shared.lock().unwrap().storage_work();
  for ((_,desc,start,filtered,limit),result) in queries.iter().zip(&results){let mut rows=expected.values().filter(|r| !filtered||r.category=="a").cloned().collect::<Vec<_>>();rows.sort_by(|a,b|{let order=a.amount.cmp(&b.amount);(if *desc{order.reverse()}else{order}).then(a.id.cmp(&b.id))});assert_eq!(result.total_rows,rows.len() as u64);assert_eq!(result.start_rank,*start as u64);assert_eq!(result.rows,rows.into_iter().skip(*start).take(*limit as usize).collect::<Vec<_>>());}
  if sample>=8 {println!("{}",serde_json::json!({"kind":"sample","sample":sample-8,"target":part,"K":keys.len(),"records":records,"batches":batches,"batch_sizes":sizes,"durable_ns":durable,"reconciliation_ns":reconcile,"read_ns":read_ns,"authorize_ns":authorize_ns,"service_ns":completed.duration_since(service).as_nanos(),"source_to_result_ns":completed.duration_since(arrival).as_nanos(),"record_latency_ns":arrivals.iter().map(|a|completed.duration_since(*a).as_nanos()).collect::<Vec<_>>(),"record_wait_ns":waits,"batch_build_ns":build_ns,"queue_bytes":queue_peak,"building_bytes":building_peak,"spill_bytes":0,"paused_ns":0,"queue_records_serialized":q.metrics().queue_records_serialized-serial_before,"apply_work":apply_work,"query_work":query_work,"authorize_work":authorize_work,"oracle":true}));}
 }
 let durable=c.checkpoint().unwrap();assert_eq!(durable.snapshot.rows,expected.values().cloned().collect::<Vec<_>>());assert_eq!(durable.snapshot.offsets,offsets.iter().enumerate().map(|(p,o)|(p as u32,o-1)).collect());
 let digest=format!("{:x}",Sha256::digest(serde_json::to_vec(&durable).unwrap()));
 println!("{}",serde_json::json!({"kind":"end","full_recovery_sha256":digest,"end_rows":durable.snapshot.rows.len(),"records_committed":q.metrics().completed_records,"batches_committed":q.metrics().completed_batches,"db_bytes":std::fs::metadata(path).unwrap().len(),"wal_bytes":std::fs::metadata(format!("{}-wal",path.display())).map(|m|m.len()).unwrap_or(0)}));
}
