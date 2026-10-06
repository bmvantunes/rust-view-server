//! Frozen v2 fixture producer, executed against the accepted v9 source.
use product_source_ingestion::{coordination::Record, durable::*};
use rust_differential_product_core::{product::*, source::*, topic::RowId};
fn main() {
    let args: Vec<_> = std::env::args().collect();
    let identity = SourceIdentity {
        incarnation: "fixture-cluster/products-lifetime-1".into(),
        topic: "products".into(),
        schema: "product-v1".into(),
    };
    let mut s = SqliteStore::create(&args[1], identity).unwrap();
    for p in 0..16 {
        let (t, _) = s.acquire(p, "v9-fixture").unwrap();
        let records = (0..256)
            .map(|i| {
                Record::new(SourceMutation {
                    partition: p,
                    offset: i,
                    mutation: if i == 255 {
                        ProductMutation::Delete {
                            key: RowId(format!("p{p}-0")),
                        }
                    } else {
                        ProductMutation::Upsert {
                            row: ProductRow {
                                id: format!("p{p}-{i}"),
                                category: if i % 2 == 0 { "a" } else { "b" }.into(),
                                label: OptionalString::Value("exact\0日本語".into()),
                                quantity: ExactInteger::parse("9223372036854775807").unwrap(),
                                amount: ExactDecimal::parse(&format!("{i}.000000000000000001"))
                                    .unwrap(),
                            },
                        }
                    },
                })
            })
            .collect::<Vec<_>>();
        s.commit(&t, p as u64, &records).unwrap();
        s.label_checkpoint(&t, &format!("partition-{p}-through-255"))
            .unwrap();
        s.release(&t).unwrap();
    }
    println!("{}", serde_json::to_string(&s.load().unwrap()).unwrap());
}
