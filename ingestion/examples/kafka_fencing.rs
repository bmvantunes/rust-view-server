#[cfg(feature = "kafka-canonical")]
fn main() -> Result<(), Box<dyn std::error::Error>> {
    use rdkafka::{
        ClientConfig,
        producer::{BaseProducer, BaseRecord, Producer},
    };
    use std::{io::Write, time::Duration};
    let a = std::env::args().collect::<Vec<_>>();
    let topic = &a[2];
    assert!(topic.starts_with("ksq-"));
    let p: BaseProducer = ClientConfig::new()
        .set("bootstrap.servers", "127.0.0.1:29492")
        .set("transactional.id", format!("fence-{topic}"))
        .set("transaction.timeout.ms", "30000")
        .create()?;
    let d = Duration::from_secs(10);
    p.init_transactions(d)?;
    if a[1] == "successor" {
        p.begin_transaction()?;
        p.send(
            BaseRecord::to(topic)
                .partition(0)
                .key("successor")
                .payload("committed"),
        )
        .map_err(|(e, _)| e)?;
        p.commit_transaction(d)?;
        println!("successor-committed");
        return Ok(());
    }
    p.begin_transaction()?;
    if a[1] == "prepared" {
        p.send(
            BaseRecord::to(topic)
                .partition(0)
                .key("old-prepared")
                .payload("must-abort"),
        )
        .map_err(|(e, _)| e)?;
        p.flush(d)?;
    }
    println!("prepared");
    std::io::stdout().flush()?;
    let mut line = String::new();
    std::io::stdin().read_line(&mut line)?;
    let mut outcomes = vec![];
    for key in [
        "stale-update",
        "stale-delete",
        "stale-progress",
        "stale-replay",
        "stale-shutdown-flush",
    ] {
        outcomes.push(format!(
            "{key}: {:?}",
            p.send(BaseRecord::to(topic).partition(0).key(key).payload("stale"))
                .map_err(|(e, _)| e)
        ));
    }
    outcomes.push(format!(
        "stale-tombstone: {:?}",
        p.send(
            BaseRecord::<str, str>::to(topic)
                .partition(0)
                .key("stale-tombstone")
        )
        .map_err(|(e, _)| e)
    ));
    let result = p.commit_transaction(d);
    assert!(result.is_err(), "old epoch committed after successor");
    println!(
        "{}",
        serde_json::json!({"outcomes":outcomes,"commit":format!("{result:?}"),"passed":true})
    );
    Ok(())
}
#[cfg(not(feature = "kafka-canonical"))]
fn main() {
    panic!("requires kafka-canonical");
}
