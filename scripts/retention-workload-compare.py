#!/usr/bin/env python3
"""Paired small persistent-producer workload, retention absent vs enabled."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
import uuid
import urllib.request

W = Path(__file__).resolve().parents[1]
ROOT = W.parent
OLD = Path("/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime")
KAFKA = OLD / "kafka_2.13-4.1.0" / "bin"
NODE = Path("/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node")
JAVA_HOME = "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
LABEL = "retention-measure-" + uuid.uuid4().hex[:8]
RT = ROOT / "runtime" / LABEL
OUT = W / "evidence" / "retention" / LABEL
TOKEN = "configurable-local-measurement-token-000000000000"
PROCS: list[tuple[subprocess.Popen, str]] = []
BROKER = ""
HEALTH_PORT = 0
ENV = {**os.environ, "JAVA_HOME": JAVA_HOME, "KAFKA_HEAP_OPTS": "-Xms256m -Xmx512m",
       "V12_SESSION_TOKEN": TOKEN, "PATH": str(NODE.parent) + ":" + os.environ.get("PATH", "")}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run(args, *, check=True, timeout=60):
    result = subprocess.run(list(map(str, args)), env=ENV, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"command failed: {' '.join(map(str,args))}\n{result.stdout}\n{result.stderr}")
    return result


def kafka(name, *args):
    return run([KAFKA / name, *args])


def wait_until(predicate, label, timeout=30):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            last = predicate()
            if last:
                return last
        except Exception:
            pass
        time.sleep(0.05)
    raise RuntimeError(f"timed out waiting for {label}; last={last!r}")


def start(args, name, *, cwd=RT, stdout=None, stdin=None, stderr=None, session=False):
    proc = subprocess.Popen(list(map(str,args)), env=ENV, cwd=cwd, stdout=stdout, stdin=stdin,
                            stderr=subprocess.STDOUT if stderr is None else stderr, text=True, bufsize=1, start_new_session=session)
    PROCS.append((proc,name))
    return proc


def health() -> dict:
    req=urllib.request.Request(f"http://127.0.0.1:{HEALTH_PORT}/health",headers={"Authorization":f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req,timeout=2) as response:
        return json.loads(response.read())


def source_health(snapshot:dict,topic:str)->dict:
    return next(source for source in snapshot["sources"] if source["topic"]==topic)


def source_next(snapshot:dict,topic:str)->dict[str,str]:
    return {str(p["partition"]):str(p.get("durable_next")) for p in source_health(snapshot,topic)["partitions"]}


def row_id(source:dict,key:dict,row:dict)->str:
    parts=[bytes([1,len(source["identity"]["components"])])]
    key_fields={field["name"]:field for field in source["key_fields"]}
    catalog=json.loads((W/"fixtures/proto-topics/catalog.json").read_text())
    schema=next(entry for entry in catalog["schemas"] if hashlib.sha256(json.dumps(entry,separators=(",",":")).encode()).hexdigest()==source["schema"])
    value_fields={field["name"]:field for field in schema["fields"]}
    for component in source["identity"]["components"]:
        field=key_fields[component["field"]] if component["source"]=="key" else value_fields[component["field"]]
        value=key[component["field"]] if component["source"]=="key" else row[component["field"]]
        kind=field.get("kind") or field.get("type")
        if kind=="string" or kind=="decimal":
            data=str(value).encode();tag=1 if kind=="string" else 6
        elif kind=="boolean": data,tag=bytes([int(bool(value))]),2
        elif kind=="number":
            import struct
            data,tag=struct.pack(">d",float(value)),3
        elif kind in ("int64","uint64"): data,tag=int(value).to_bytes(8,"big",signed=kind=="int64"),(4 if kind=="int64" else 5)
        else: raise ValueError(f"unrecognized identity kind {kind}")
        parts.extend((bytes([tag])+len(data).to_bytes(4,"big"),data))
    return "rid2:"+b"".join(parts).hex()


def cpu_seconds(value:str)->float:
    fields=value.split(":")
    if len(fields)==3:
        return int(fields[0])*3600+int(fields[1])*60+float(fields[2])
    if len(fields)==2:
        return int(fields[0])*60+float(fields[1])
    return float(value)


def resources(proc:subprocess.Popen)->dict:
    output=run(["ps","-o","rss=","-o","time=","-p",proc.pid]).stdout.strip().split()
    if len(output)<2: raise RuntimeError("could not sample service RSS/CPU")
    return {"rssKb":int(output[0]),"cpuSeconds":cpu_seconds(output[1])}


def canonical_bytes(topic:str)->int:
    return sum(path.stat().st_size for directory in (RT/"broker-data").glob(topic+"-*") if directory.is_dir()
               for path in directory.iterdir() if path.is_file() and
               (path.name.endswith(".log") or path.name.endswith(".log.deleted")))


def topic_config(topic:str, *, canonical=False):
    args=["--bootstrap-server",BROKER,"--create","--topic",topic,"--partitions","2","--replication-factor","1"]
    if canonical:
        args += ["--config","cleanup.policy=compact","--config","min.compaction.lag.ms=0","--config","segment.ms=1000",
                 "--config","min.cleanable.dirty.ratio=0.01","--config","delete.retention.ms=86400000"]
    kafka("kafka-topics.sh",*args)


def main():
    global BROKER, HEALTH_PORT
    RT.mkdir(parents=True,exist_ok=False);OUT.mkdir(parents=True,exist_ok=False)
    broker_port,controller_port=free_port(),free_port();BROKER=f"127.0.0.1:{broker_port}"
    props=(OLD/"broker.properties").read_text().replace("34492",str(broker_port)).replace("34493",str(controller_port)).replace(str(OLD/"broker-data"),str(RT/"broker-data"))
    (RT/"broker.properties").write_text(props)
    cluster=run([KAFKA/"kafka-storage.sh","random-uuid"]).stdout.strip()
    run([KAFKA/"kafka-storage.sh","format","--standalone","-t",cluster,"-c",RT/"broker.properties"])
    broker_log=open(OUT/"broker.log","w")
    broker=start([KAFKA/"kafka-server-start.sh",RT/"broker.properties"],"broker",stdout=broker_log,session=True)
    wait_until(lambda:"Kafka Server started" in (OUT/"broker.log").read_text(errors="replace"),"Kafka startup",60)

    generated=RT/"bindings.json"
    run([NODE,W/"scripts/generate-proto-source-config.mjs",generated,BROKER,LABEL])
    base=next(source for source in json.loads(generated.read_text()) if source["topic"]=="orders")
    source_schema=base["schema"]
    catalog=json.loads((W/"fixtures/proto-topics/catalog.json").read_text())
    manifest={"format":catalog["format"],"schemas":[entry for entry in catalog["schemas"] if hashlib.sha256(json.dumps(entry,separators=(",",":")).encode()).hexdigest()==source_schema],"topics":[]}
    sources=[]
    for suffix in ("off","on"):
        source=deepcopy(base);source["topic"]=f"ordersBench{suffix.title()}";source["source_topic"]=f"{LABEL}-{suffix}-source";source["state_topic"]=f"{LABEL}-{suffix}-canonical-rowid-{'retention-v3' if suffix=='on' else 'v2'}";source["group"]=f"{LABEL}-{suffix}-group";source["source_incarnation"]=f"{LABEL}-{suffix}-incarnation";source["max_rows"]=1000
        source["identity"]["components"]=[{"source":"key","field":"tenant"},{"source":"key","field":"desk"},{"source":"value","field":"orderId"}]
        if suffix=="on": source["retention"]={"maxRetentionMinutes":0.2,"maxRetentionMessages":100}
        else: source.pop("retention",None)
        topic_config(source["source_topic"]);topic_config(source["state_topic"],canonical=True)
        sources.append(source);manifest["topics"].append({"topic":source["topic"],"schema":source_schema})

    query_port,HEALTH_PORT,web_port=free_port(),free_port(),free_port()
    config={"bind":f"127.0.0.1:{query_port}","origin":f"http://127.0.0.1:{web_port}","catalog":manifest,"sources":sources,
            "health":{"bind":f"127.0.0.1:{HEALTH_PORT}","readiness":sources[0]["readiness"],"sample_ms":1000,"stdout":True},
            "subscription_limits":{"per_client":32,"total":64},"run_ms":0,"run_until_shutdown":True}
    config_path=RT/"config.json";config_path.write_text(json.dumps(config))
    service_log=open(OUT/"service.log","w")
    service=start([W/"bin/view_server_grouped",config_path],"service",stdout=service_log)
    wait_until(lambda:health().get("ready") is True,"benchmark service readiness",60)
    producer_log=open(OUT/"producer.log","w")
    producer=start([W/"bin/generic_kafka_producer_grouped",config_path],"producer",stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=producer_log,session=False)
    ready=json.loads(producer.stdout.readline())
    if ready.get("producer_ready") is not True: raise RuntimeError(f"benchmark producer did not start: {ready}")

    resource_cuts={};workload_count=64;next_ack=0;index_samples=[]
    source_by_mode={source["topic"]:source for source in sources}
    key={"tenant":"local","desk":"desk","account":"0","partitionKey":"0"}
    for mode,topic in (("off","ordersBenchOff"),("on","ordersBenchOn")):
        proc_sample_start=resources(service);wall_start=time.monotonic();last_ack_ms=0;source=source_by_mode[topic]
        for revision in range(workload_count):
            row={"orderId":"order0","customer":"C0","open":True,"units":str(9_007_199_254_740_993+revision),"price":str(revision%7)}
            if revision%3==1: row["note"]=None
            elif revision%3==2: row["note"]=""
            next_ack+=1;expected_id=row_id(source,key,row);producer.stdin.write(json.dumps({"topic":topic,"partition":0,"ack":next_ack,"key":key,"row":row})+"\n");producer.stdin.flush()
            ack=json.loads(producer.stdout.readline())
            if ack.get("ack")!=next_ack or ack.get("key")!=expected_id or ack.get("partition")!=0: raise RuntimeError(f"producer identity mismatch: {ack}")
            expected_next=int(ack["offset"])+1
            wait_until(lambda: any(int(partition.get("durable_next") or -1)>=expected_next for partition in source_health(health(),topic)["partitions"] if int(partition["partition"])==0),f"{topic} source NEXT {expected_next}",15)
            last_ack_ms=int(time.time()*1000)
            snapshot=health()
            if mode=="on": index_samples.append({"observedUnixMs":int(time.time()*1000),"sourceNext":source_next(snapshot,topic),"globalRecordsCommitted":snapshot["records_committed"],"active":source_health(snapshot,topic)["retention"]["active_payload_rows"],"sticky":source_health(snapshot,topic)["retention"]["sticky_keys"],"scheduled":source_health(snapshot,topic)["retention"]["scheduled_expiries"]})
        after=health();rss_cpu=resources(service);wall_ms=round((time.monotonic()-wall_start)*1000,3)
        resource_cuts[mode]={"records":workload_count,"sameRowId":expected_id,"wallMs":wall_ms,"cpuMs":round(max(0,rss_cpu["cpuSeconds"]-proc_sample_start["cpuSeconds"])*1000,3),
                             "rssKbBefore":proc_sample_start["rssKb"],"rssKbAfter":rss_cpu["rssKb"],"rssDeltaKb":rss_cpu["rssKb"]-proc_sample_start["rssKb"],
                             "canonicalLogBytes":canonical_bytes(source["state_topic"]),"sourceNext":source_next(after,topic),"liveRows":after["live_rows"],
                             "recordsCommitted":after["records_committed"],"outputQueueFrames":after["output_queue_frames"],"outputQueueBytes":after["output_queue_bytes"]}
        if mode=="off":
            if after["live_rows"]!=1 or source_health(after,topic)["retention"]["enabled"]: raise RuntimeError(f"retention-off baseline did not retain one current row: {after}")
            resource_cuts[mode]["retentionEnabled"]=False
        else:
            retained=source_health(after,topic)["retention"]
            if retained["active_payload_rows"]!=1 or retained["sticky_keys"]!=1 or retained["scheduled_expiries"]!=1 or max(item["scheduled"] for item in index_samples)>1:
                raise RuntimeError(f"repeated same-row updates grew retained payload/stale timers: {retained}, samples={index_samples}")
            resource_cuts[mode]["retentionEnabled"]=True
            resource_cuts[mode]["retentionAfterUpdates"]={k:retained[k] for k in ("active_payload_rows","sticky_keys","scheduled_expiries","maintenance_sequence","canonical_version","derived_version")}
            resource_cuts[mode]["scheduledIndexSamples"]={"raw":index_samples,"count":len(index_samples),"max":max(item["scheduled"] for item in index_samples),"distinctCounts":sorted({item["scheduled"] for item in index_samples})}
            resource_cuts[mode]["expiryDueUnixMs"]=retained["next_expiry_unix_ms"];resource_cuts[mode]["lastUpdateAckUnixMs"]=last_ack_ms

    before_expiry=health();on_topic="ordersBenchOn";off_topic="ordersBenchOff";next_before={topic:source_next(before_expiry,topic) for topic in (off_topic,on_topic)}
    records_before_expiry=before_expiry["records_committed"]
    due=int(resource_cuts["on"]["expiryDueUnixMs"])
    waited=wait_until(lambda:(lambda h:h if source_health(h,on_topic)["retention"]["active_payload_rows"]==0 and source_health(h,on_topic)["retention"]["maintenance_sequence"]>0 and h["live_rows"]==1 else None)(health()),"on-policy expiry and derived removal",25)
    observed_ms=int(time.time()*1000);after_expiry=waited;on_retention=source_health(after_expiry,on_topic)["retention"]
    if after_expiry["records_committed"]!=records_before_expiry or source_next(after_expiry,on_topic)!=next_before[on_topic] or source_next(after_expiry,off_topic)!=next_before[off_topic]:
        raise RuntimeError("timer-only measurement expiry changed source accounting/progress")
    if after_expiry["live_rows"]!=1 or source_health(after_expiry,off_topic)["retention"]["enabled"]: raise RuntimeError("retention-off row did not remain after paired age cut")
    resource_cuts["on"]["afterExpiry"]={"activePayloadRows":on_retention["active_payload_rows"],"stickyKeys":on_retention["sticky_keys"],"scheduledExpiries":on_retention["scheduled_expiries"],
        "maintenanceTransactions":after_expiry["maintenance_transactions"],"maintenanceRowsEvicted":after_expiry["maintenance_rows_evicted"],"sourceNext":source_next(after_expiry,on_topic),
        "recordsCommitted":after_expiry["records_committed"],"lastCommitUnixMs":on_retention["last_commit_unix_ms"],"lastExpiryDelayMs":on_retention["last_expiry_delay_ms"],
        "observedAfterDueMs":observed_ms-due,"actualCommitAfterDueMs":int(on_retention["last_commit_unix_ms"])-due,"canonicalLogBytes":canonical_bytes(source_by_mode[on_topic]["state_topic"])}
    (OUT/"workload-comparison.json").write_text(json.dumps({"status":"PASS","scope":"one private Kafka 4.1 broker, one ordinary service and one persistent producer; paired 64-record same-rowId update cuts. CPU/RSS and liveRows/recordsCommitted are process-wide, not topic costs; no SLA claim",
        "configuration":{"retentionMinutesOn":0.2,"onCountCap":100,"offPolicy":"absent","rowId":"rid2; same key and orderId for all updates"},
        "off":resource_cuts["off"],"on":resource_cuts["on"],"conclusion":"Both modes held one current payload through repeated updates. With retention enabled the row had exactly one live expiry entry after all updates, then one sticky identity and zero payload after source-silent expiry; the off-policy row remained live. CPU/RSS and Kafka log-byte values are single-run paired observations only."},indent=2))
    print("PASS="+str(OUT),flush=True)


try:
    main()
finally:
    for proc,name in reversed(PROCS):
        if proc.poll() is None:
            try:
                if name=="broker": os.killpg(proc.pid,signal.SIGTERM)
                else: proc.terminate()
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    if name=="broker": os.killpg(proc.pid,signal.SIGKILL)
                    else: proc.kill()
                except ProcessLookupError: pass
    for path in (OUT/"broker.log",OUT/"service.log",OUT/"producer.log"):
        if path.exists():
            try: path.open("a").close()
            except OSError: pass
