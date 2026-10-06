//! Matched finite work/representation comparison; not a saturation benchmark.
use rust_differential_product_core::{schema::{Schema,Catalog,Manifest,Topic,Scalar,encode_row_id,path_get},generic::{Runtime,Mutation}};
use serde_json::{Value,json};
fn run(schema:Schema,rows:Vec<Value>)->Value{
 let fp=schema.fingerprint().to_owned();let mut rt=Runtime::new(Catalog::new(Manifest{format:1,schemas:vec![schema.definition().clone()],topics:vec![Topic{topic:"comparison".into(),schema:fp.clone()}]}).unwrap(),1000).unwrap();
 let fields=schema.definition().fields.iter().map(|f|f.name.clone()).collect::<Vec<_>>();
 let price=fields.iter().find(|f|f.as_str()=="oo.price"||f.as_str()=="oo_price").unwrap();
 rt.apply_committed("comparison",&fp,&rows.iter().map(|r|Mutation::Upsert{row:r.clone()}).collect::<Vec<_>>()).unwrap();
 rt.open("raw","comparison",&fp,serde_json::from_value(json!({"select":fields,"order_by":[{"field":price,"direction":"asc"}]})).unwrap()).unwrap();let before=rt.metrics();
 for i in 0..128{rt.apply_committed("comparison",&fp,&[Mutation::Upsert{row:rows[i%rows.len()].clone()}]).unwrap();}
 let after=rt.metrics();let results=rt.read("raw",0,100,4*1024*1024).unwrap();let parent_entries=rows.iter().map(|r|schema.row(r).unwrap().parents.len()).sum::<usize>();
 assert_eq!(after["changed_rows"].as_u64().unwrap()-before["changed_rows"].as_u64().unwrap(),128);assert_eq!(before["seed_rows"],after["seed_rows"]);
 json!({"rows":rows.len(),"updates":128,"before":before,"after":after,"result_json_bytes":serde_json::to_vec(&results).unwrap().len(),"canonical_json_bytes":serde_json::to_vec(&rows).unwrap().len(),"retained_scalar_cell_slots":rows.len()*fields.len(),"retained_parent_presence_entries":parent_entries})
}
fn main(){let catalog:Manifest=serde_json::from_str(include_str!("../../fixtures/expanded-topics/catalog.json")).unwrap();let nested=Schema::new(catalog.schemas.into_iter().find(|s|s.id=="shit_v3").unwrap()).unwrap();let mut d=nested.definition().clone();d.format=2;d.version=2;d.id="matched_flat_v2".into();d.expansion=None;for f in &mut d.fields{f.name=f.name.replace('.',"_")}let flat_definition=d;let mut nested_rows=vec![];let mut flat_rows=vec![];for i in 0..32{let id=encode_row_id(&[Scalar::String(i.to_string())]).unwrap();let row=json!({"rowId":id,"label":"same","oo":{"name":format!("name-{i}"),"status":{"domain":"example.common.Status","code":1},"price":"9007199254740993.01"}});nested_rows.push(row);}
 // Enums need their domain metadata, so compare the identical non-enum leaves only.
 let mut nd=nested.definition().clone();let keep=nd.fields.iter().map(|f|f.kind!=rust_differential_product_core::schema::Kind::Enum).collect::<Vec<_>>();nd.fields=nd.fields.into_iter().enumerate().filter_map(|(i,f)|keep[i].then_some(f)).collect();let e=nd.expansion.as_mut().unwrap();e.leaves=e.leaves.clone().into_iter().enumerate().filter_map(|(i,l)|keep[i].then_some(l)).collect();e.enums.clear();let nested=Schema::new(nd).unwrap();let mut fd=flat_definition;fd.fields=fd.fields.into_iter().enumerate().filter_map(|(i,f)|keep[i].then_some(f)).collect();let flat=Schema::new(fd).unwrap();
 for row in &mut nested_rows{row["oo"].as_object_mut().unwrap().remove("status");let mut out=serde_json::Map::new();out.insert("rowId".into(),row["rowId"].clone());for f in &nested.definition().fields{if let Some(v)=path_get(row,&f.name){out.insert(f.name.replace('.',"_"),v.clone());}}flat_rows.push(Value::Object(out));}
 println!("{}",json!({"scope":"32 rows, 128 one-row replacements, identical exact values and non-enum scalar cell count; JSON bytes and retained cell/parent entries are representation proxies, not heap/RSS or latency claims","flat":run(flat,flat_rows),"nested":run(nested,nested_rows)}));
}
