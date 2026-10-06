use product_source_ingestion::row_delta::{batch,project,Baseline};
use rust_differential_product_core::product::{ProductCore,ProductCommand};
use serde_json::{json,Value};
fn apply(core:&mut ProductCore,v:Value){core.apply(serde_json::from_value::<ProductCommand>(v).unwrap()).unwrap();}
fn next(seed:&mut u64)->u64{*seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);*seed}
fn row(i:u64,step:u64)->Value{let id=match i{31=>"\u{e000}".into(),32=>"\u{10000}".into(),_=>format!("r{i:03}")};json!({"id":id,"category":format!("c{}",step%3),"quantity":if step%2==0{"9223372036854775807"}else{"18446744073709551617"},"amount":{"coefficient":(step as i64%13-6).to_string(),"scale":2},"label":match step%4{0=>json!({"state":"missing"}),1=>json!({"state":"null"}),2=>json!({"state":"value","value":""}),_=>json!({"state":"value","value":format!("日本語🦀-{step}")})}})}
fn main(){let mut core=ProductCore::new();let mut seed=0x41a53;let initial=(0..30).map(|i|row(i,i)).collect::<Vec<_>>();for r in &initial{apply(&mut core,json!({"command":"upsert","row":r}));}
 let mut queries=vec![];let mut bases:Vec<Option<Baseline>>=vec![None;6];let projections=(0..6).map(|i|if i%2==0{vec!["label".into(),"quantity".into()]}else{vec!["amount".into()]}).collect::<Vec<Vec<String>>>();
 for i in 0..6{let query=json!({"where_expr":if i%3==0{json!({"op":"true"})}else{json!({"op":"condition","args":{"field":"category_equals","condition":format!("c{}",i%3-1)}})},"direction":if i<3{"ascending"}else{"descending"},"offset":0,"limit":12});apply(&mut core,json!({"command":"open","subscription":format!("s{i}"),"query":query}));queries.push(query);}
 for step in 0..501{let mut command=Value::Null;let mut navigation=Value::Null;
  if step>0{let i=next(&mut seed)%36;command=if next(&mut seed)%4==0{json!({"command":"delete","id":row(i,step)["id"]})}else{json!({"command":"upsert","row":row(i,next(&mut seed)%200)})};apply(&mut core,command.clone());}
  let mut force=vec![step==0;6];if step>0&&step%7==0{let i=next(&mut seed) as usize%6;queries[i]["offset"]=json!(next(&mut seed)%50);queries[i]["limit"]=json!(next(&mut seed)%16);navigation=json!({"subscription":i,"query":queries[i]});apply(&mut core,json!({"command":"change_window","subscription":format!("s{i}"),"offset":queries[i]["offset"],"limit":queries[i]["limit"]}));force[i]=true;}
  let mut frames=vec![];for i in 0..6{let native=serde_json::to_value(core.result(&format!("s{i}")).unwrap()).unwrap();let projected=project(&native,&projections[i]);let(frame,base)=batch(bases[i].as_ref(),1,&projections[i],projected,force[i]);let binary=v13_codec_experiment::encode_mp(&v13_codec_experiment::prepare(&frame).unwrap()).unwrap();frames.push(json!({"subscription":i,"query":queries[i],"projection":projections[i],"binary":binary}));bases[i]=Some(base);}
  println!("{}",json!({"step":step,"initial":if step==0{json!(initial)}else{Value::Null},"command":command,"navigation":navigation,"frames":frames}));
 }
}
