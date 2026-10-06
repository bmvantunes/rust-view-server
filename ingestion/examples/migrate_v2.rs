//! Explicit offline migration. Back up and release all owners with the old binary first.
use product_source_ingestion::durable::{SourceIdentity, SqliteStore};
fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert!(
        args.len() == 5 && args[1] == "--owners-excluded",
        "migrate_v2 --owners-excluded <database> <source-incarnation> <topic>; stop/exclude every old process first"
    );
    SqliteStore::migrate_v2_offline(
        &args[2],
        SourceIdentity {
            incarnation: args[3].clone(),
            topic: args[4].clone(),
            schema: "product-v1".into(),
        },
    )
    .expect("migration failed; do not reset the database");
    println!("Format 3 migration committed. Reacquire owners and rebuild engines.");
}
