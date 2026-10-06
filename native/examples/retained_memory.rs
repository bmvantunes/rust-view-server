//! Standalone measurement harness, not a product allocator or engine benchmark.
use rust_differential_product_core::{
    engine_contract::{DifferentialProductEngine as Engine, ProductEngine},
    product::{
        Direction, ExactDecimal, ExactInteger, Expr, OptionalString, ProductCommand, ProductRow,
        Query,
    },
    source::{ProductMutation, SourceBatch, SourceMutation},
    topic::TopicStore,
};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicIsize, Ordering};
static LIVE: AtomicIsize = AtomicIsize::new(0);
struct CountAllocator;
unsafe impl GlobalAlloc for CountAllocator {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc(l) };
        if !p.is_null() {
            LIVE.fetch_add(l.size() as isize, Ordering::Relaxed);
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        LIVE.fetch_sub(l.size() as isize, Ordering::Relaxed);
        unsafe { System.dealloc(p, l) }
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        let q = unsafe { System.realloc(p, l, n) };
        if !q.is_null() {
            LIVE.fetch_add(n as isize - l.size() as isize, Ordering::Relaxed);
        }
        q
    }
}
#[global_allocator]
static ALLOC: CountAllocator = CountAllocator;
fn live() -> isize {
    LIVE.load(Ordering::Relaxed)
}
fn main() {
    let count: usize = std::env::args()
        .nth(1)
        .unwrap_or("10000".into())
        .parse()
        .unwrap();
    println!(
        "ALLOCATOR_MEASUREMENT rows={count}; requested live allocation bytes, not RSS or throughput"
    );
    let mut engine = Engine::load(TopicStore::default().snapshot()).unwrap();
    let empty = live();
    for (index, start) in (0..count).step_by(1000).enumerate() {
        let mutations = (start..(start + 1000).min(count))
            .map(|i| SourceMutation {
                partition: 0,
                offset: i as u64,
                mutation: ProductMutation::Upsert {
                    row: ProductRow {
                        id: format!("r{i:08}"),
                        category: format!("category-{}", i % 8),
                        label: OptionalString::Value("x".repeat(64)),
                        quantity: ExactInteger::parse("9223372036854775807").unwrap(),
                        amount: ExactDecimal::parse(&format!("{i}.125")).unwrap(),
                    },
                },
            })
            .collect();
        engine
            .commit(SourceBatch {
                topic: TopicStore::default().id().clone(),
                schema: "product-v1".into(),
                sequence: index as u64 + 1,
                mutations,
            })
            .unwrap();
    }
    let retained = live();
    let snapshot = engine.checkpoint().unwrap();
    let with_snapshot = live();
    drop(snapshot);
    let snapshot_dropped = live();
    let q = Query {
        where_expr: Expr::True,
        direction: Direction::Ascending,
        offset: 0,
        limit: 10,
    };
    engine
        .command(ProductCommand::Open {
            subscription: "one".into(),
            query: q.clone(),
        })
        .unwrap();
    let one = live();
    engine
        .command(ProductCommand::Open {
            subscription: "shared".into(),
            query: Query {
                offset: 100,
                ..q.clone()
            },
        })
        .unwrap();
    let shared = live();
    engine
        .command(ProductCommand::Open {
            subscription: "desc".into(),
            query: Query {
                direction: Direction::Descending,
                ..q
            },
        })
        .unwrap();
    let both = live();
    for id in ["one", "shared", "desc"] {
        engine
            .command(ProductCommand::Close {
                subscription: id.into(),
            })
            .unwrap();
    }
    let closed = live();
    println!(
        "{}",
        serde_json::json!({"rows":count,"unit":"live requested allocation bytes (System wrapper)","empty_engine":empty,"retained_no_queries":retained,"retained_increment":retained-empty,"detached_snapshot_increment":with_snapshot-retained,"after_snapshot_drop":snapshot_dropped,"one_shape_asc":one,"one_shape_asc_increment":one-retained,"same_shape_second_window_increment":shared-one,"additional_desc_index_increment":both-shared,"after_final_release":closed,"release_retained_capacity_increment":closed-retained})
    );
}
