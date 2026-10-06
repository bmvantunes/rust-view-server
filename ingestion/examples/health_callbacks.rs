//! Real service integration, no separate instrumentation runtime or globals.
use product_source_ingestion::{health::Callbacks,service::run_with_callbacks};
fn main()->Result<(),String>{let path=std::env::args().nth(1).ok_or("CONFIG.json required")?;
 run_with_callbacks(path,Callbacks{
  on_heartbeat:Some(Box::new(|snapshot|{println!("{}",serde_json::json!({"event":"heartbeat","instance":snapshot.instance,"phase":snapshot.phase,"ready":snapshot.ready,"sampled_at_unix_ms":snapshot.sampled_at_unix_ms}));Ok(())})),
  on_dependencies_update:Some(Box::new(|inventory|{println!("{}",serde_json::json!({"event":"dependencies","inventory":inventory}));Ok(())})),
 })
}
