use product_source_ingestion::wire::{Product,ProductKey};
use prost::Message;
use rdkafka::{ClientConfig,ClientContext,Message as KafkaMessage,producer::{BaseProducer,BaseRecord,Producer,ProducerContext,DeliveryResult}};
use std::{io::{BufRead,Write},sync::{Arc,Mutex},time::{Instant,Duration}};
#[derive(Clone)]struct Context(Arc<Mutex<Option<Result<(i32,i64),String>>>>);
impl ClientContext for Context{}
impl ProducerContext for Context{type DeliveryOpaque=();fn delivery(&self,result:&DeliveryResult,_:()){let v=result.as_ref().map(|m|(m.partition(),m.offset())).map_err(|(e,_)|e.to_string());let mut slot=self.0.lock().unwrap();assert!(slot.is_none());*slot=Some(v);}}
fn main()->Result<(),Box<dyn std::error::Error>>{
 let args:Vec<String>=std::env::args().collect();let c:serde_json::Value=serde_json::from_slice(&std::fs::read(&args[1])?)?;
 let brokers=c["mode"]["config"]["brokers"].as_str().ok_or("brokers")?;assert!(brokers.starts_with("127.0.0.1:"));let topic=c["source"]["topic"].as_str().ok_or("topic")?;
 let context=Context(Arc::new(Mutex::new(None)));let p:BaseProducer<Context>=ClientConfig::new().set("bootstrap.servers",brokers).set("enable.idempotence","true").set("acks","all").create_with_context(context.clone())?;
 println!("{{\"ready\":true}}");std::io::stdout().flush()?;
 for line in std::io::stdin().lock().lines(){let started=Instant::now();let v:serde_json::Value=serde_json::from_str(&line?)?;let id=v["id"].as_str().unwrap();let label=v["label"].as_str().unwrap();let mut key=vec![0,0,0,0,1,0];key.extend(ProductKey{id:id.into()}.encode_to_vec());let mut payload=vec![0,0,0,0,2,0];payload.extend(Product{id:id.into(),category:"a".into(),quantity:i64::MAX,amount:"-10.01".into(),label:Some(label.into())}.encode_to_vec());
 p.send(BaseRecord::to(topic).partition(0).key(&key).payload(&payload)).map_err(|(e,_)|e)?;
 let enqueued=started.elapsed();let delivered=loop{p.poll(Duration::from_millis(1));if let Some(result)=context.0.lock().unwrap().take(){break result?}if started.elapsed()>Duration::from_secs(10){return Err("source delivery timeout".into())}};
 println!("{}",serde_json::json!({"label":label,"partition":delivered.0,"offset":delivered.1,"enqueue_us":enqueued.as_micros(),"delivery_callback_us":started.elapsed().as_micros()}));std::io::stdout().flush()?;
 }
 p.flush(Duration::from_secs(10))?;Ok(())
}
