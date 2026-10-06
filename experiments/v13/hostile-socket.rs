// Inserted only into each isolated candidate's native socket tests.
#[test]
fn malformed_binary_disconnects_acquisition_and_healthy_peer_survives() {
 let server=Server::new();
 for bytes in HOSTILE_BYTES {
  let(mut bad,ready)=server.connect();
  bad.send(command(&ready,1,1,open())).unwrap();read(&mut bad);read(&mut bad);
  bad.send(Message::Binary(bytes.into())).unwrap();assert!(bad.read().is_err());
 }
 for kind in ["result","ack"] {
  let(mut bad,r)=server.connect();
  bad.send(wire(json!({"v":13,"type":kind,"incarnation":r["incarnation"],"connection":r["connection"],"nonce":r["nonce"]}))).unwrap();
  assert!(bad.read().is_err());
 }
 let(mut healthy,r)=server.connect();healthy.send(command(&r,1,1,open())).unwrap();read(&mut healthy);read(&mut healthy);
 server.put(0,"after-hostiles");let live=read(&mut healthy);assert_eq!(live["type"],"result");assert_eq!(live["result"]["rows"][0]["label"]["value"],"after-hostiles");
}
