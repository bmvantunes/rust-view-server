//! Explicit fixture generator / bounded restore measurement. Destination must be absent.
use product_source_ingestion::{coordination::Record, durable::*};
use rust_differential_product_core::{
    engine_contract::{ProductEngine, SelectedProductEngine},
    product::*,
    source::*,
};
use std::time::Instant;
fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(
        args.len(),
        3,
        "durable_fixture <new-db-path> <1..1024 rows>"
    );
    let n: u64 = args[2].parse().unwrap();
    assert!((1..=1024).contains(&n));
    let source = SourceIdentity {
        incarnation: "fixture-cluster/products-lifetime-1".into(),
        topic: "products".into(),
        schema: "product-v1".into(),
    };
    let mut store = SqliteStore::create(&args[1], source.clone()).unwrap();
    let (token, _) = store.acquire(0, "fixture-generator").unwrap();
    let records: Vec<_> = (0..n)
        .map(|i| {
            Record::new(SourceMutation {
                partition: 0,
                offset: i,
                mutation: ProductMutation::Upsert {
                    row: ProductRow {
                        id: format!("row-{i:06}"),
                        category: "fixture".into(),
                        label: OptionalString::Value("exact\0日本語".into()),
                        quantity: ExactInteger::parse("9223372036854775807").unwrap(),
                        amount: ExactDecimal::parse(&format!("{i}.000000000000000001")).unwrap(),
                    },
                },
            })
        })
        .collect();
    let start = Instant::now();
    store.commit(&token, 0, &records).unwrap();
    let commit_ns = start.elapsed().as_nanos();
    store.release(&token).unwrap();
    drop(store);
    let start = Instant::now();
    let mut store = SqliteStore::open(&args[1], source).unwrap();
    let snapshot = store.load().unwrap().snapshot;
    let restore_ns = start.elapsed().as_nanos();
    let start = Instant::now();
    let mut engine = SelectedProductEngine::load(snapshot).unwrap();
    engine
        .command(ProductCommand::Open {
            subscription: "fixture".into(),
            query: Query {
                where_expr: Expr::True,
                direction: Direction::Ascending,
                offset: 0,
                limit: n,
            },
        })
        .unwrap();
    let result = engine.read("fixture").unwrap();
    let engine_ns = start.elapsed().as_nanos();
    println!(
        "{}",
        serde_json::json!({"rows":n,"sqlite":rusqlite::version(),"durable_commit_ns":commit_ns,"open_validate_restore_ns":restore_ns,"engine_rebuild_query_ns":engine_ns,"complete_result":result})
    );
}
