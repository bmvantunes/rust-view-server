use std::{io::BufRead,net::TcpStream,time::Duration};
use serde_json::{json,Value};
use tungstenite::{Message,client::IntoClientRequest};
fn main(){
 let cfg:Value=serde_json::from_str(&std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap()).unwrap();let token=std::env::var("V12_SESSION_TOKEN").unwrap();
 let mut request=format!("ws://{}/v14",cfg["bind"].as_str().unwrap()).into_client_request().unwrap();request.headers_mut().insert("origin",cfg["origin"].as_str().unwrap().parse().unwrap());request.headers_mut().insert("sec-websocket-protocol","view-server.v14.msgpack".parse().unwrap());let socket=TcpStream::connect(cfg["bind"].as_str().unwrap()).unwrap();socket.set_read_timeout(Some(Duration::from_secs(5))).unwrap();socket.set_write_timeout(Some(Duration::from_secs(5))).unwrap();let(mut ws,_)=tungstenite::client(request,socket).unwrap();
 let wire=|v:Value|Message::Binary(v13_codec_experiment::encode_mp(&v13_codec_experiment::prepare(&v).unwrap()).unwrap().into());
 ws.send(wire(json!({"type":"hello","v":14,"token":token,"nonce":"01234567890123456789012345678901"}))).unwrap();let ready=loop{if let Message::Binary(b)=ws.read().unwrap(){break v13_codec_experiment::adapt(&v13_codec_experiment::decode_mp(&b).unwrap()).unwrap()}};assert_eq!(ready["type"],"ready");
 for id in 1..=100{let command=if id==1{json!({"command":"open","subscription":"same","query":{"where_expr":{"op":"true"},"direction":"ascending","offset":0,"limit":32}})}else{json!({"command":"change_window","subscription":"same","offset":0,"limit":32})};ws.send(wire(json!({"v":14,"type":"command","incarnation":ready["incarnation"],"connection":ready["connection"],"nonce":ready["nonce"],"request":{"id":id,"acquisition":1,"previous_acquisition":null,"traceparent":"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01","command":command}}))).unwrap();}
 println!("PRESSURE_READY 99");let mut done=String::new();let _=std::io::stdin().lock().read_line(&mut done);
}
