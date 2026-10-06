//! Common v10/v11 local harness. One coordinator, exact oracle outside timings.
use product_source_ingestion::{coordination::{Authority,Record,Partition,Delivery,BoundedQueue,Limits,BatchLimits},durable::{SourceIdentity,SqliteStore,DurableStore},durable_coordinator::{Session,DurableCoordinator}};
use rust_differential_product_core::{engine_contract::SelectedProductEngine,product::*,source::*,topic::RowId};
use sha2::{Digest,Sha256};
use std::{collections::BTreeMap,sync::{Arc,Mutex},time::{Instant,Duration},path::Path};
fn row(i:usize)->ProductRow {ProductRow{id:format!("row-{i:09}"),category:if i%2==0{"a"}else{"b"}.into(),label:OptionalString::Value("exact\0日本語".into()),quantity:ExactInteger::parse("9223372036854775807").unwrap(),amount:ExactDecimal::parse(&format!("{i}.0001")).unwrap()}}
fn record(p:u32,offset:u64,mutation:ProductMutation)->Record{Record::new(SourceMutation{partition:p,offset,mutation})}
fn main(){
 let args:Vec<_>=std::env::args().collect();let path=Path::new(&args[1]);let p:usize=args[2].parse().unwrap();let l=p;let cap=1;let mode="dense";
 let n=10000usize;let seed=90210usize;assert!([1,16,256].contains(&p)&&l>0&&l<=p&&[1,32,256,1024].contains(&cap));assert!(mode=="dense"||mode=="sparse");
 let identity=SourceIdentity{incarnation:"v11-controlled-topic".into(),topic:"products".into(),schema:"product-v1".into()};
 let setup=Instant::now();let mut store=SqliteStore::create(path,identity.clone()).unwrap();
 let tokens=(0..p).map(|i|store.acquire(i as u32,"seed").unwrap().0).collect::<Vec<_>>();
 let expected:BTreeMap<String,ProductRow>=(0..n).map(|i|{let r=row(i);(r.id.clone(),r)}).collect();
 let mut offsets=vec![0u64;p];let mut seq=0;
 for part in 0..p {
  let rows=(part..n).step_by(p).collect::<Vec<_>>();
  for chunk in rows.chunks(1000){let records=chunk.iter().map(|i|{let r=record(part as u32,offsets[part],ProductMutation::Upsert{row:row(*i)});offsets[part]+=1;r}).collect::<Vec<_>>();store.commit(&tokens[part],seq,&records).unwrap();seq+=1;}
  let records=(0..256).map(|_|{let r=record(part as u32,offsets[part],ProductMutation::Upsert{row:row(part)});offsets[part]+=1;r}).collect::<Vec<_>>();store.commit(&tokens[part],seq,&records).unwrap();seq+=1;
 }
 for _ in 0..256 {store.commit(&tokens[0],seq,&[record(0,offsets[0],ProductMutation::Upsert{row:row(0)})]).unwrap();offsets[0]+=1;seq+=1;}
 for t in &tokens {store.release(t).unwrap();}drop(store);
 let store=SqliteStore::open(path,identity.clone()).unwrap();let authority=Authority::default();let shared=Arc::new(Mutex::new(Session::new(store,"measure".into(),authority)));
 let _leases=(0..l).map(|i|shared.lock().unwrap().acquire(Partition{topic:"products".into(),partition:i as u32}).unwrap().0).collect::<Vec<_>>();
 let mut c:DurableCoordinator<SelectedProductEngine,SqliteStore>=DurableCoordinator::new(shared.clone()).unwrap();
 let queries=[("top",false,0,false,16),("deep",true,n/2,false,16),("category",false,n/4,true,16),("full",false,0,false,20000)];
 for (name,desc,start,filtered,limit) in queries {c.command(ProductCommand::Open{subscription:name.into(),query:Query{where_expr:if filtered{Expr::Condition(Condition::CategoryEquals("a".into()))}else{Expr::True},direction:if desc{Direction::Descending}else{Direction::Ascending},offset:start as u64,limit}}).unwrap();}
 println!("{}",serde_json::json!({"kind":"setup","P":p,"L":l,"H":256,"rows":n,"seed":seed,"setup_ns":setup.elapsed().as_nanos()}));
 let requests=queries.iter().map(|(id,_,_,_,_)|product_source_ingestion::durable_coordinator::ReadRequest{subscription:(*id).into(),acquisition:1}).collect::<Vec<_>>();
 let bounds=product_source_ingestion::durable_coordinator::ReadBounds{requests:4,rows:65536,bytes:32*1024*1024};
 for sample in 0..12 {
  let mut exact=None;
  for grouped in if sample%2==0{[false,true]}else{[true,false]} {
   shared.lock().unwrap().reset_storage_work();let started=Instant::now();
   let results=if grouped{c.read_many(&requests,bounds).unwrap().results}else{queries.iter().map(|(name,_,_,_,_)|c.read(name).unwrap().unwrap().result).collect::<Vec<_>>()};
   let elapsed=started.elapsed().as_nanos();let work=shared.lock().unwrap().storage_work();
   for ((_,desc,start,filtered,limit),result) in queries.iter().zip(&results){let mut rows=expected.values().filter(|r| !filtered||r.category=="a").cloned().collect::<Vec<_>>();rows.sort_by(|a,b|{let order=a.amount.cmp(&b.amount);(if *desc{order.reverse()}else{order}).then(a.id.cmp(&b.id))});assert_eq!(result.total_rows,rows.len() as u64);assert_eq!(result.rows,rows.into_iter().skip(*start).take(*limit as usize).collect::<Vec<_>>());}
   if let Some(prior)=&exact{assert_eq!(&results,prior);}else{exact=Some(results.clone());}
   let encoded=serde_json::to_vec(&results).unwrap();println!("{}",serde_json::json!({"kind":"sample","sample":sample,"grouped":grouped,"elapsed_ns":elapsed,"results":results.len(),"rows":results.iter().map(|r|r.rows.len()).sum::<usize>(),"result_bytes":encoded.len(),"result_sha256":format!("{:x}",Sha256::digest(&encoded)),"work":work,"oracle":true}));
  }
 }
}
