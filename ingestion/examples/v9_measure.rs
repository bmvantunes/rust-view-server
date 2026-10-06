//! Identical bounded harness copied into the accepted baseline, never modifying its archive.
use product_source_ingestion::{coordination::{Authority,Record,Partition,Delivery},durable::{SourceIdentity,SqliteStore,DurableStore},durable_coordinator::{Session,DurableCoordinator}};
use rust_differential_product_core::{engine_contract::SelectedProductEngine,product::*,source::*,topic::RowId};
use std::{collections::BTreeMap,sync::{Arc,Mutex},time::Instant,path::Path};
fn row(i:usize)->ProductRow {ProductRow{id:format!("row-{i:06}"),category:if i%2==0{"a"}else{"b"}.into(),label:OptionalString::Value("exact\0日本語".into()),quantity:ExactInteger::parse("9223372036854775807").unwrap(),amount:ExactDecimal::parse(&format!("{i}.0001")).unwrap()}}
fn record(offset:u64,mutation:ProductMutation)->Record{Record::new(SourceMutation{partition:0,offset,mutation})}
fn footprint(path:&Path)->serde_json::Value {serde_json::json!({"db_bytes":std::fs::metadata(path).map(|m|m.len()).unwrap_or(0),"wal_bytes":std::fs::metadata(format!("{}-wal",path.display())).map(|m|m.len()).unwrap_or(0)})}
fn main(){
    let args:Vec<_>=std::env::args().collect();let path=Path::new(&args[1]);let n:usize=args[2].parse().unwrap();let cap:usize=args[3].parse().unwrap();let seed:usize=args[4].parse().unwrap();
    assert!([1000,10000].contains(&n)&&[1,32].contains(&cap));
    let identity=SourceIdentity{incarnation:"v9-bounded-measurement".into(),topic:"products".into(),schema:"product-v1".into()};
    let empty=Instant::now();let mut store=SqliteStore::create(path,identity.clone()).unwrap();let empty_create_ns=empty.elapsed().as_nanos();
    let empty_restore=Instant::now();assert!(store.load().unwrap().snapshot.rows.is_empty());let empty_restore_ns=empty_restore.elapsed().as_nanos();
    let (token,_)=store.acquire(0,"seed").unwrap();let mut seq=0;
    let mut expected:BTreeMap<String,ProductRow>=BTreeMap::new();
    for start in (0..n).step_by(1000){let records=(start..start+1000).map(|i|{let r=row(i);expected.insert(r.id.clone(),r.clone());record(i as u64,ProductMutation::Upsert{row:r})}).collect::<Vec<_>>();store.commit(&token,seq,&records).unwrap();seq+=1;}
    store.release(&token).unwrap();drop(store);
    // New connection/engine; OS cache has NOT been forcibly evicted.
    let cold=Instant::now();let store=SqliteStore::open(path,identity).unwrap();let shared=Arc::new(Mutex::new(Session::new(store,"measure".into(),Authority::default())));
    let (lease,_)=shared.lock().unwrap().acquire(Partition{topic:"products".into(),partition:0}).unwrap();
    let mut c:DurableCoordinator<SelectedProductEngine,SqliteStore>=DurableCoordinator::new(shared.clone()).unwrap();
    let restore_ns=cold.elapsed().as_nanos();
    let queries=[("top",false,0,false),("deep",true,n/2,false),("category",false,n/4,true)];
    for (name,desc,offset,filtered) in queries {c.command(ProductCommand::Open{subscription:name.into(),query:Query{where_expr:if filtered{Expr::Condition(Condition::CategoryEquals("a".into()))}else{Expr::True},direction:if desc{Direction::Descending}else{Direction::Ascending},offset:offset as u64,limit:16}}).unwrap();}
    println!("{}",serde_json::json!({"kind":"setup","rows":n,"cap":cap,"seed":seed,"sqlite":rusqlite::version(),"empty_create_ns":empty_create_ns,"empty_restore_ns":empty_restore_ns,"new_connection_engine_restore_ns":restore_ns,"storage":footprint(path),"queries":queries,"warmup_batches":16,"samples":64}));
    let mut offset=n as u64;
    for sample in 0..80usize {
        let building=Instant::now();
        let mut records=Vec::new();
        for j in 0..cap {
            let i=(seed+sample*37+j*13)%n;let id=format!("row-{i:06}");
            let mutation=match sample%6 {
                0=>ProductMutation::Upsert{row:row(n+sample*cap+j)},
                1=>{let mut r=row(i);r.amount=ExactDecimal::parse(&format!("-{}.0001",i+1)).unwrap();ProductMutation::Upsert{row:r}},
                2=>ProductMutation::Delete{key:RowId(id.clone())},
                3=>ProductMutation::Upsert{row:expected.get(&id).cloned().unwrap_or_else(||row(i))},
                4=>{let mut r=expected.get(&id).cloned().unwrap_or_else(||row(i));r.label=OptionalString::Value(format!("selected-{sample}"));ProductMutation::Upsert{row:r}},
                _=>{let mut r=expected.get(&id).cloned().unwrap_or_else(||row(i));r.category=if r.category=="a"{"b"}else{"a"}.into();ProductMutation::Upsert{row:r}}
            };
            match &mutation {ProductMutation::Upsert{row}=>{expected.insert(row.id.clone(),row.clone());},ProductMutation::Delete{key}=>{expected.remove(&key.0);}}
            records.push(record(offset,mutation));offset+=1;
        }
        let building_ns=building.elapsed().as_nanos();
        let started=Instant::now();let before_durable=c.metrics().durable_transaction_ns;let before_engine=c.metrics().engine_reconciliation_ns;
        c.apply(&Delivery{lease:lease.clone(),records}).unwrap();
        let results=queries.iter().map(|(name,_,_,_)|c.read(name).unwrap().unwrap().result).collect::<Vec<_>>();
        let available_ns=started.elapsed().as_nanos();
        c.commit_offset(&lease,|next|{assert_eq!(next,offset);Ok(())}).unwrap();
        // Independent full sort oracle OUTSIDE the measured service interval.
        for ((_,desc,start,filtered),result) in queries.iter().zip(&results) {
            let mut rows=expected.values().filter(|r| !filtered || r.category=="a").cloned().collect::<Vec<_>>();
            rows.sort_by(|a,b|{let order=a.amount.cmp(&b.amount);(if *desc{order.reverse()}else{order}).then(a.id.cmp(&b.id))});
            assert_eq!(result.total_rows,rows.len() as u64);assert_eq!(result.start_rank,*start as u64);
            assert_eq!(result.rows,rows.into_iter().skip(*start).take(16).collect::<Vec<_>>());
        }
        if sample>=16 {println!("{}",serde_json::json!({"kind":"sample","sample":sample-16,"case":(["insert","rank","delete","equal_noop","selected","membership"][sample%6]),"records":cap,"available_ns":available_ns,"durable_ns":c.metrics().durable_transaction_ns-before_durable,"reconciliation_ns":c.metrics().engine_reconciliation_ns-before_engine,"batch_build_ns":building_ns,"queue_wait_ns":0,"batching_wait_note":"synchronous size-flushed harness; build includes fixture generation; no simulated free latency","oracle":"exact rows/order/totals/deep windows passed"}));}
    }
    let snap=c.checkpoint().unwrap().snapshot;assert_eq!(snap.rows,expected.values().cloned().collect::<Vec<_>>());
    println!("{}",serde_json::json!({"kind":"end","storage":footprint(path),"metrics":c.metrics(),"end_rows":snap.rows.len(),"sequence":snap.last_source_batch}));
}
