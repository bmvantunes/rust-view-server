#!/usr/bin/env python3
"""Finite loopback Kafka + production browser Worker retention acceptance."""
from __future__ import annotations

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "work"
OLD = Path("/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime")
KAFKA = OLD / "kafka_2.13-4.1.0" / "bin"
NODE = Path("/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node")
CARGO = Path("/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo")
JAVA_HOME = "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
LABEL = "retention-" + uuid.uuid4().hex[:8]
RT = ROOT / "runtime" / LABEL
OUT = W / "evidence" / "retention" / LABEL
TOKEN = "configurable-local-test-token-000000000000"
CHILDREN: list[tuple[subprocess.Popen, object, str]] = []
EVENT_LOCK = threading.Lock()
EVENTS: list[dict] = []
OTLP: list[dict] = []
SERVICE = None
SERVICE_LOG = None
CASE_PATH = RT / "retention-case.json"
PORTS: dict[str, int] = {}
BROKER = ""
HTTP: ThreadingHTTPServer | None = None
HTTP_THREAD = None


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def record_process(proc: subprocess.Popen, log, name: str):
    CHILDREN.append((proc, log, name))
    return proc


def command(args, *, timeout=60, check=True):
    result = subprocess.run(list(map(str, args)), env=ENV, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(map(str, args))}\n{result.stdout}\n{result.stderr}")
    return result


def kafka_cli(name, *args, timeout=60, check=True):
    return command([KAFKA / name, *args], timeout=timeout, check=check)


def admin_offsets(topic: str) -> dict[int, int]:
    result = kafka_cli("kafka-get-offsets.sh", "--bootstrap-server", BROKER, "--topic", topic, "--time", "-1")
    offsets = {}
    for line in result.stdout.splitlines():
        fields = line.strip().split(":")
        if len(fields) >= 3:
            offsets[int(fields[1])] = int(fields[-1])
    return offsets


def create_topic(topic: str, *, policy: str | None = None, retention_ms: int | None = None, canonical=False):
    args = ["--bootstrap-server", BROKER, "--create", "--topic", topic, "--partitions", "2", "--replication-factor", "1"]
    if policy is not None:
        args += ["--config", "cleanup.policy=" + policy]
    if retention_ms is not None:
        args += ["--config", "retention.ms=" + str(retention_ms)]
    if canonical:
        args += ["--config", "cleanup.policy=compact", "--config", "min.compaction.lag.ms=0", "--config", "segment.ms=1000", "--config", "min.cleanable.dirty.ratio=0.01", "--config", "delete.retention.ms=86400000"]
    kafka_cli("kafka-topics.sh", *args)
    (OUT / f"topic-{topic}.log").write_text(kafka_cli("kafka-topics.sh", "--bootstrap-server", BROKER, "--describe", "--topic", topic).stdout)


def describe_config(topic: str) -> str:
    return kafka_cli("kafka-configs.sh", "--bootstrap-server", BROKER, "--describe", "--entity-type", "topics", "--entity-name", topic, "--all").stdout


def send_json(handler: BaseHTTPRequestHandler, status: int, value):
    body = json.dumps(value).encode()
    handler.send_response(status)
    handler.send_header("content-type", "application/json")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def proxy_health(path: str):
    request = urllib.request.Request(f"http://127.0.0.1:{PORTS['health']}{path}", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(request, timeout=2) as response:
        return response.status, response.read(), response.headers.get("content-type", "application/json")


def page_html() -> bytes:
    html=(W / "build/grouped/grouped-demo.html").read_text()
    return html.replace('</body>', '<p id="retention-status">Starting</p><pre id="retention-result"></pre><script type="module" src="/retention-browser-gate.js"></script></body>').encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        return

    def end(self, status: int, body: bytes, content_type="application/octet-stream"):
        self.send_response(status)
        origin = self.headers.get("origin")
        if origin and origin.startswith("http://127.0.0.1:"):
            self.send_header("access-control-allow-origin", origin)
        self.send_header("access-control-allow-headers", "content-type")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.end(204, b"")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            try:
                status, body, content_type = proxy_health("/health")
                self.end(status, body, content_type)
            except Exception as exc:
                self.end(503, json.dumps({"error": str(exc)}).encode(), "application/json")
            return
        if path == "/metrics":
            try:
                status, body, content_type = proxy_health("/metrics")
                self.end(status, body, content_type)
            except Exception as exc:
                self.end(503, str(exc).encode(), "text/plain")
            return
        if path == "/retention-case.json":
            try:
                self.end(200, CASE_PATH.read_bytes(), "application/json")
            except OSError as exc:
                self.end(503, str(exc).encode(), "text/plain")
            return
        if path == "/phase.json":
            self.end(200, (RT / "phase.json").read_bytes(), "application/json")
            return
        if path == "/retention-browser.html":
            self.end(200, page_html(), "text/html; charset=utf-8")
            return
        if path == "/retention-browser-gate.js":
            self.end(200, (W / "scripts" / "retention-browser-gate.js").read_bytes(), "text/javascript; charset=utf-8")
            return
        if path.startswith("/assets/") or path in ("/product-core-100.json", "/product_core.sha256", "/product_core.wasm", "/request_admission.wasm"):
            candidate = (W / "build" / "grouped" / path.lstrip("/")).resolve()
            base = (W / "build" / "grouped").resolve()
            if not str(candidate).startswith(str(base) + os.sep) or not candidate.is_file():
                self.end(404, b"missing")
                return
            kind = "text/javascript" if candidate.suffix == ".js" else "application/wasm" if candidate.suffix == ".wasm" else "application/json"
            self.end(200, candidate.read_bytes(), kind)
            return
        self.end(404, b"missing")

    def do_POST(self):
        size = int(self.headers.get("content-length", "0"))
        if size < 0 or size > 1_048_576:
            self.end(413, b"body bound")
            return
        body = self.rfile.read(size)
        if self.path in ("/v1/traces", "/v1/metrics"):
            summary = {"path": self.path, "bytes": size, "sha256": hashlib.sha256(body).hexdigest(), "received_unix_ms": int(time.time() * 1000)}
            with EVENT_LOCK:
                index = len(OTLP)
                OTLP.append(summary)
            (OUT / f"otlp-{index}-{self.path.rsplit('/', 1)[-1]}.pb").write_bytes(body)
            self.end(200, b"", "application/x-protobuf")
            return
        if self.path == "/result":
            try:
                event = json.loads(body)
                with EVENT_LOCK:
                    EVENTS.append(event)
                    (OUT / "browser-events.json").write_text(json.dumps(EVENTS, indent=2))
                print("BROWSER_EVENT=" + json.dumps({"stage": event.get("stage"), "status": event.get("status")}), flush=True)
                send_json(self, 200, {"accepted": True})
            except Exception as exc:
                self.end(400, str(exc).encode(), "text/plain")
            return
        self.end(404, b"missing")


def start_http():
    global HTTP, HTTP_THREAD
    HTTP = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    HTTP.daemon_threads = True
    HTTP.timeout = 0.2
    PORTS["web"] = HTTP.server_address[1]
    HTTP_THREAD = threading.Thread(target=HTTP.serve_forever, name="retention-http", daemon=True)
    HTTP_THREAD.start()


def current_health() -> dict:
    _, body, _ = proxy_health("/health")
    return json.loads(body)


def source_health(health: dict, topic: str) -> dict:
    return next(source for source in health["sources"] if source["topic"] == topic)


def wait_until(predicate, label: str, timeout=30, interval=0.1):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            last = predicate()
            if last:
                return last
        except Exception:
            pass
        time.sleep(interval)
    raise RuntimeError(f"timed out waiting for {label}; last={last!r}")


def wait_browser(stage: str, timeout=60):
    event = wait_until(lambda: next((item for item in EVENTS if item.get("stage") in (stage, "failed")), None),
                       f"browser stage {stage}", timeout, 0.2)
    if event.get("stage") == "failed" or event.get("status") != "PASS":
        raise RuntimeError(f"production browser gate failed during {stage}: {event}")
    return event


def source_next(health: dict) -> dict[str, dict[str, str]]:
    result = {}
    for source in health["sources"]:
        result[source["topic"]] = {str(p["partition"]): str(p.get("durable_next")) for p in source["partitions"]}
    return result


def make_row(topic: str, index: int, revision: int = 0):
    if topic == "orders":
        row = {"orderId": f"order{index}", "customer": f"C{index % 3}", "open": True,
               "units": str(9_007_199_254_740_993 + index + revision), "price": str((index + revision) % 7)}
        if index % 3 == 1:
            row["note"] = None
        elif index % 3 == 2:
            row["note"] = ""
        return row
    return {"positionId": f"p{index}", "symbol": f"S{index % 3}", "quantity": str(-index - revision),
            "risk": (index + revision) % 8 / 4, "hedged": bool(index % 2)}


def make_key(index: int):
    return {"tenant": "local", "desk": "desk", "account": str(index), "partitionKey": str(index % 2)}


def identity_id(source: dict, key: dict, row: dict) -> str:
    parts = [bytes([1, len(source["identity"]["components"])])]
    key_fields = {field["name"]: field for field in source["key_fields"]}
    catalog = json.loads((W / "fixtures" / "proto-topics" / "catalog.json").read_text())
    schema = next(entry for entry in catalog["schemas"] if hashlib.sha256(json.dumps(entry, separators=(",", ":")).encode()).hexdigest() == source["schema"])
    value_fields = {field["name"]: field for field in schema["fields"]}
    for component in source["identity"]["components"]:
        field = key_fields[component["field"]] if component["source"] == "key" else value_fields[component["field"]]
        value = key[component["field"]] if component["source"] == "key" else row[component["field"]]
        kind = field.get("kind") or field.get("type")
        if kind == "string" or kind == "decimal":
            data = str(value).encode()
            tag = 1 if kind == "string" else 6
        elif kind == "boolean":
            data, tag = bytes([int(bool(value))]), 2
        elif kind == "number":
            import struct
            data, tag = struct.pack(">d", float(value)), 3
        elif kind in ("int64", "uint64"):
            data, tag = int(value).to_bytes(8, "big", signed=kind == "int64"), (4 if kind == "int64" else 5)
        else:
            raise ValueError(f"unrecognized identity field kind {kind!r}: {field!r}")
        parts.extend((bytes([tag]) + len(data).to_bytes(4, "big"), data))
    return "rid2:" + b"".join(parts).hex()


def create_case(sources: list[dict], catalog: dict, final_rows: dict, first_rows: dict, baseline: dict):
    def attach(topic: str, rows: list[tuple[str, dict]]):
        return [dict(row, rowId=row_id) for row_id, row in sorted(rows, key=lambda x: x[0])]
    case = {
        "wsUrl": f"ws://127.0.0.1:{PORTS['query']}/v15", "token": TOKEN,
        "endpoint": f"http://127.0.0.1:{PORTS['web']}", "healthUrl": "/health", "metricsUrl": "/metrics",
        "catalog": catalog,
        "definitions": {
            "ordersRaw": {"topic": "orders", "query": {"select": [f["name"] for f in catalog["orders"]["schema"]["fields"]], "orderBy": []}},
            "ordersGroup": {"topic": "orders", "query": {"groupBy": ["customer"], "aggregates": {"n":{"aggFunc":"count"},"d":{"aggFunc":"countDistinct","field":"note"},"s":{"aggFunc":"sum","field":"units"},"a":{"aggFunc":"avg","field":"price"},"lo":{"aggFunc":"min","field":"price"},"hi":{"aggFunc":"max","field":"price"}}, "orderBy": [{"aggregate":"s","direction":"desc"}]}},
            "positionsRaw": {"topic": "positions", "query": {"select": [f["name"] for f in catalog["positions"]["schema"]["fields"]], "orderBy": []}},
            "positionsGroup": {"topic": "positions", "query": {"groupBy": ["symbol"], "aggregates": {"n":{"aggFunc":"count"},"d":{"aggFunc":"countDistinct","field":"hedged"},"s":{"aggFunc":"sum","field":"quantity"},"a":{"aggFunc":"avg","field":"risk"},"lo":{"aggFunc":"min","field":"quantity"},"hi":{"aggFunc":"max","field":"risk"}}, "orderBy": [{"aggregate":"s","direction":"desc"}]}}
        },
        "stages": {
            "initial": {topic: attach(topic, final_rows[topic]) for topic in ("orders", "positions")},
            "first_expiry": {topic: attach(topic, first_rows[topic]) for topic in ("orders", "positions")},
            "complete": {"orders": [], "positions": []}
        },
        "baseline": {"recordsCommitted": baseline["records_committed"], "sourceNext": source_next(baseline),
                     "maintenanceTransactions": baseline["maintenance_transactions"],
                     "maintenanceRowsEvicted": baseline["maintenance_rows_evicted"]}
    }
    CASE_PATH.write_text(json.dumps(case, indent=2))


def config_doc(sources: list[dict], catalog: dict, query_port: int, health_port: int, web_port: int, *, probe=False):
    return {"bind": f"127.0.0.1:{query_port}", "origin": f"http://127.0.0.1:{web_port}", "catalog": catalog,
            "sources": sources,
            "health": {"bind": f"127.0.0.1:{health_port}", "readiness": sources[0]["readiness"], "sample_ms": 1000,
                       "stdout": True, **({} if probe else {"telemetry": {"otlp_endpoint": f"http://127.0.0.1:{web_port}", "trace_sample_ratio": 1}})},
            "subscription_limits": {"per_client": 32, "total": 64}, "run_ms": 0, "run_until_shutdown": True}


def start_service(config_path: Path, *, faults=False, write_denied=False):
    global SERVICE, SERVICE_LOG
    env = dict(ENV)
    if faults:
        env["V121_FAULT_DIR"] = str(RT / "faults")
    name = "fault-owner" if faults else "ordinary-owner"
    SERVICE_LOG = open(OUT / f"{name}.log", "a")
    cmd=[str(W / "bin" / ("view_server_grouped_faults" if faults else "view_server_grouped")), str(config_path)]
    cwd=RT
    if write_denied:
        if faults: raise RuntimeError("write-denied successor must use the ordinary binary")
        cwd=RT / ("empty-successor-"+uuid.uuid4().hex[:8]);cwd.mkdir()
        profile='(version 1)(allow default)(deny file-write*)'
        probe=subprocess.run(['/usr/bin/sandbox-exec','-p',profile,'/usr/bin/touch',str(cwd/'forbidden-write-probe')],cwd=cwd,capture_output=True,text=True)
        if probe.returncode==0 or list(cwd.iterdir()): raise RuntimeError("write denial negative probe failed")
        cmd=['/usr/bin/sandbox-exec','-p',profile,*cmd]
        (OUT/'write-denied-launch.json').write_text(json.dumps({'command':cmd,'cwd':str(cwd),'initial_entries':[],'negative_probe':{'exit':probe.returncode,'stdout':probe.stdout,'stderr':probe.stderr},'config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((W/'bin/view_server_grouped').read_bytes()).hexdigest()},indent=2))
    SERVICE = record_process(subprocess.Popen(cmd, env=env, cwd=cwd, stdout=SERVICE_LOG, stderr=subprocess.STDOUT), SERVICE_LOG, name)
    return SERVICE


def stop_service(sig=signal.SIGTERM):
    global SERVICE, SERVICE_LOG
    if SERVICE is not None and SERVICE.poll() is None:
        SERVICE.send_signal(sig)
        try:
            SERVICE.wait(timeout=15)
        except subprocess.TimeoutExpired:
            SERVICE.kill()
            SERVICE.wait(timeout=10)
    if SERVICE_LOG is not None:
        SERVICE_LOG.flush()


def start_broker():
    props = (OLD / "broker.properties").read_text()
    props = props.replace("34492", str(PORTS["broker"])).replace("34493", str(PORTS["controller"]))
    props = props.replace(str(OLD / "broker-data"), str(RT / "broker-data"))
    (RT / "broker.properties").write_text(props)
    log = open(OUT / "broker.log", "w")
    cluster = command([KAFKA / "kafka-storage.sh", "random-uuid"]).stdout.strip()
    formatted = command([KAFKA / "kafka-storage.sh", "format", "--standalone", "-t", cluster, "-c", RT / "broker.properties"])
    (OUT / "format.log").write_text(formatted.stdout + formatted.stderr)
    process = record_process(subprocess.Popen([str(KAFKA / "kafka-server-start.sh"), str(RT / "broker.properties")], env=ENV, cwd=RT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True), log, "broker")
    wait_until(lambda: "Kafka Server started" in (OUT / "broker.log").read_text(errors="replace"), "Kafka broker startup", 60, 0.2)
    return process


ENV = {**os.environ, "JAVA_HOME": JAVA_HOME, "KAFKA_HEAP_OPTS": "-Xms256m -Xmx512m",
       "V12_SESSION_TOKEN": TOKEN, "PATH": str(NODE.parent) + ":" + os.environ.get("PATH", "")}


def main():
    global BROKER, PORTS
    RT.mkdir(parents=True, exist_ok=False)
    OUT.mkdir(parents=True, exist_ok=False)
    PORTS = {name: free_port() for name in ("broker", "controller", "query", "health")}
    start_http()
    PORTS["web"] = HTTP.server_address[1]
    print(f"BROWSER_URL=http://127.0.0.1:{PORTS['web']}/retention-browser.html", flush=True)
    BROKER = f"127.0.0.1:{PORTS['broker']}"
    (OUT / "run.json").write_text(json.dumps({"label": LABEL, "ports": PORTS, "kafka": str(KAFKA), "javaHome": JAVA_HOME}, indent=2))
    broker = start_broker()

    bindings_path = RT / "bindings.json"
    command([NODE, W / "scripts" / "generate-proto-source-config.mjs", bindings_path, BROKER, LABEL])
    sources = [s for s in json.loads(bindings_path.read_text()) if s["topic"] in ("orders", "positions")]
    for source in sources:
        source["state_topic"] = f"{LABEL}-{source['topic']}-canonical-rowid-retention-v3"
        source["identity"]["components"] = ([{"source":"key","field":"tenant"},{"source":"key","field":"desk"},{"source":"value","field":"orderId"}]
                                              if source["topic"] == "orders" else source["identity"]["components"])
        source["retention"] = ({"maxRetentionMinutes": 1, "maxRetentionMessages": 6}
                                if source["topic"] == "orders" else {"maxRetentionMinutes": 2, "maxRetentionMessagesPerKey": 1})
        source["max_rows"] = 10000
        source["readiness"] = dict(enter_offset_distance=2, exit_offset_distance=5, max_sample_age_ms=3000, enter_hold_ms=100, exit_hold_ms=100)

    # The orders source inherits Kafka's effective delete and retention defaults.
    # Positions changes cleanup.policy explicitly to compact. Canonical topics stay compact-only.
    orders = next(s for s in sources if s["topic"] == "orders")
    positions = next(s for s in sources if s["topic"] == "positions")
    create_topic(orders["source_topic"])
    create_topic(positions["source_topic"], policy="compact", retention_ms=1000)
    for source in sources:
        create_topic(source["state_topic"], canonical=True)
    (OUT / "effective-orders-source-config.txt").write_text(describe_config(orders["source_topic"]))
    (OUT / "effective-positions-source-config.txt").write_text(describe_config(positions["source_topic"]))
    for source in sources:
        (OUT / f"canonical-policy-{source['topic']}.txt").write_text(describe_config(source["state_topic"]))

    # Actual broker topic override must fail before any canonical write or group progress.
    probe = deepcopy(orders)
    probe.update(topic="orders", source_topic="orders.v1", state_topic=f"{LABEL}-probe-canonical", source_incarnation="retention-probe-incarnation", group=f"{LABEL}-probe-group", retention={"maxRetentionMinutes":1440,"maxRetentionMessages":6})
    create_topic(probe["source_topic"], policy="delete", retention_ms=10_800_000)
    create_topic(probe["state_topic"], canonical=True)
    manifest = json.loads((W / "fixtures" / "proto-topics" / "catalog.json").read_text())
    manifest["topics"] = [t for t in manifest["topics"] if t["topic"] in ("orders", "positions")]
    main_schemas = {t["schema"] for t in manifest["topics"]}
    manifest["schemas"] = [s for s in manifest["schemas"] if hashlib.sha256(json.dumps(s, separators=(",", ":")).encode()).hexdigest() in main_schemas]
    probe_catalog = dict(manifest)
    probe_catalog["topics"] = [t for t in manifest["topics"] if t["topic"] == "orders"]
    used = {t["schema"] for t in probe_catalog["topics"]}
    probe_catalog["schemas"] = [s for s in manifest["schemas"] if hashlib.sha256(json.dumps(s, separators=(",", ":")).encode()).hexdigest() in used]
    probe_cfg = config_doc([probe], probe_catalog, free_port(), free_port(), PORTS["web"], probe=True)
    probe_path = RT / "probe-config.json"
    probe_path.write_text(json.dumps(probe_cfg))
    probe_run = command([W / "bin" / "view_server_grouped", probe_path], timeout=30, check=False)
    expected_message = "Invalid retention for logical topic 'orders' (Kafka topic 'orders.v1'): maxRetentionMinutes=1440 requests 24 hours (86400000 ms), but Kafka retention.ms=10800000 (3 hours). Reduce the application horizon or change Kafka retention before starting this service. No configuration was changed."
    if expected_message not in probe_run.stdout + probe_run.stderr:
        raise RuntimeError("actual Kafka retention override probe did not emit the required diagnostic\n" + probe_run.stdout + probe_run.stderr)
    probe_state_offsets = admin_offsets(probe["state_topic"])
    if probe_run.returncode == 0 or any(probe_state_offsets.values()):
        raise RuntimeError(f"startup rejection changed canonical state or succeeded: rc={probe_run.returncode}, offsets={probe_state_offsets}")
    (OUT / "startup-rejection.json").write_text(json.dumps({"status":"PASS","returncode":probe_run.returncode,"diagnostic":expected_message,
        "stateOffsetsAfterRejection":probe_state_offsets,"sourceOffsetsAfterRejection":admin_offsets(probe["source_topic"]),
        "consumerGroupProgressAfterRejection":(lambda result:{"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr})(
            kafka_cli("kafka-consumer-groups.sh","--bootstrap-server",BROKER,"--group",probe["group"],"--describe",check=False)),
        "sourceConfig":describe_config(probe["source_topic"])}, indent=2))
    (OUT / "startup-rejection.log").write_text(probe_run.stdout + probe_run.stderr)

    config = config_doc(sources, manifest, PORTS["query"], PORTS["health"], PORTS["web"])
    config_path = RT / "config.json"
    config_path.write_text(json.dumps(config))
    (OUT / "configuration.json").write_text(json.dumps(config, indent=2))

    # Persistent producer and one ordinary service/provider/production Worker.
    producer_log = open(OUT / "producer.log", "w")
    producer = record_process(subprocess.Popen([str(W / "bin" / "generic_kafka_producer_grouped"), str(config_path)], env=ENV, cwd=RT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=producer_log, text=True, bufsize=1), producer_log, "producer")
    ready = producer.stdout.readline()
    if json.loads(ready).get("producer_ready") is not True:
        raise RuntimeError("persistent producer failed to start: " + ready)
    start_service(config_path)
    wait_until(lambda: current_health().get("ready") is True, "ordinary service readiness", 60, 0.2)

    rows_by_topic: dict[str, list[tuple[str, dict]]] = {"orders": [], "positions": []}
    next_offsets = {"orders": {0: 0, 1: 0}, "positions": {0: 0, 1: 0}}
    first_source_time: dict[str, int] = {}
    ack_id = 0
    source_records = []

    def put(topic: str, index: int, revision=0):
        nonlocal ack_id
        source = next(s for s in sources if s["topic"] == topic)
        key = make_key(index)
        row = make_row(topic, index, revision)
        row_id = identity_id(source, key, row)
        partition = index % 2
        ack_id += 1
        source_input={"topic":topic,"partition":partition,"ack":ack_id,"key":key,"row":row,"timestamp_ms":int(time.time()*1000)}
        producer.stdin.write(json.dumps(source_input) + "\n")
        producer.stdin.flush()
        ack = json.loads(producer.stdout.readline())
        if ack.get("ack") != ack_id or ack.get("key") != row_id or ack.get("partition") != partition:
            raise RuntimeError(f"producer independent rid2/partition oracle mismatch: {ack=} expected={row_id=} {partition=}")
        source_records.append({"input":source_input,"ack":ack})
        (OUT/"source-records.json").write_text(json.dumps(source_records,indent=2))
        offset = int(ack["offset"])
        expected_next = offset + 1
        wait_until(lambda: any(int(p.get("durable_next") or -1) >= expected_next for p in source_health(current_health(), topic)["partitions"] if int(p["partition"]) == partition),
                   f"{topic} partition {partition} durable NEXT {expected_next}", 15, 0.05)
        # Capture a conservative local lower bound after durable source progress
        # is visible. It avoids scheduling the harness before the service's
        # accepted timestamp while keeping all age assertions source-silent.
        first_source_time.setdefault(topic, int(time.time() * 1000))
        next_offsets[topic][partition] = expected_next
        if index == 0 and revision == 0:
            rows_by_topic[topic].append((row_id, row))
        elif index > 0 and revision == 0:
            rows_by_topic[topic].append((row_id, row))
        elif revision > 0:
            rows_by_topic[topic] = [(rid, row if rid == row_id else value) for rid, value in rows_by_topic[topic]]
            if not any(rid == row_id for rid, _ in rows_by_topic[topic]):
                raise RuntimeError("replacement unexpectedly changed rowId")

    for index in range(6):
        put("orders", index)
    # Separate the older generation from its replacement by a useful but
    # finite window. The first timer cut can then prove that a stale expiry
    # entry does not remove the newer (topic,rowId) UPSERT.
    time.sleep(30)
    put("orders", 0, revision=7)
    put("orders", 6)
    for index in range(6):
        put("positions", index)
    put("positions", 0, revision=7)
    put("positions", 6)

    # Global delete count evicts the known oldest row after its owner-ordered N+1.
    order_rows = rows_by_topic["orders"]
    oldest = next(row_id for row_id, row in order_rows if row["orderId"] == "order1")
    final_orders = [(rid, row) for rid, row in order_rows if rid != oldest]
    if len(final_orders) != 6 or any(row.get("orderId") == "order1" for _, row in final_orders):
        raise RuntimeError("topic N/N+1 oracle mismatch")
    final_positions = rows_by_topic["positions"]
    if len(final_positions) != 7 or len({rid for rid, _ in final_positions}) != 7:
        raise RuntimeError("compact key-only per-key cap evicted an unrelated key or invented versions")
    first_orders = [(rid, row) for rid, row in final_orders if row.get("orderId") in ("order0", "order6")]
    if len(first_orders) != 2:
        raise RuntimeError("replacement/stale-generation oracle setup mismatch")

    baseline = current_health()
    (RT / "phase.json").write_text(json.dumps({"phase":"running"}))
    if baseline["records_committed"] < 16:
        raise RuntimeError("initial source records are not independently reflected in the source counter")
    browser_catalog = json.loads((W / "fixtures" / "proto-topics" / "browser-catalog.json").read_text())
    browser_catalog = {topic: value for topic, value in browser_catalog.items() if topic in ("orders", "positions")}
    first_map = {"orders": first_orders, "positions": final_positions}
    create_case(sources, browser_catalog, {"orders": final_orders, "positions": final_positions}, first_map, baseline)
    (OUT / "producer-acks.json").write_text(json.dumps({"count": ack_id, "finalRows": {t: len(v) for t, v in rows_by_topic.items()},
        "oldestTopicRowEvicted": oldest, "sameRowIdUpdates": 2, "next": next_offsets}, indent=2))
    print(f"EVIDENCE={OUT}", flush=True)

    # Wait until the production browser has independently checked the first cut.
    (OUT/"case-initial.json").write_bytes(CASE_PATH.read_bytes())
    browser_log=open(OUT/"browser-driver.log","w")
    browser_driver=record_process(subprocess.Popen([str(NODE),str(W/"scripts/retention-production-browser.mjs"),f"http://127.0.0.1:{PORTS['web']}/retention-browser.html",str(OUT/"browser-raw.json")],env=ENV,stdout=browser_log,stderr=subprocess.STDOUT),browser_log,"browser")
    wait_browser("browser_ready",90)

    # Fault after the first timer-only Kafka transaction commits, before its delta publishes.
    first_due = first_source_time["orders"] + 60_000
    time.sleep(max(0, (first_due - int(time.time() * 1000) - 5000) / 1000))
    stop_service()
    fault_dir = RT / "faults"
    fault_dir.mkdir(exist_ok=True)
    (fault_dir / "orders-retention_before_publication.arm").write_text("crash")
    fault_owner = start_service(config_path, faults=True)
    wait_until(lambda: fault_owner.poll() is not None, "post-commit pre-publication retention crash", 25, 0.1)
    if fault_owner.returncode != 86 or not (fault_dir / "orders-retention_before_publication.reached").exists():
        raise RuntimeError(f"post-commit/pre-publication fault did not fire: {fault_owner.returncode}")
    (OUT / "fault-after-maintenance-commit.json").write_text(json.dumps({"status":"PASS","point":"retention_before_publication","exit":fault_owner.returncode,
        "sourceNextBeforeRestart":source_next(baseline)}, indent=2))
    start_service(config_path)
    wait_until(lambda: current_health().get("ready") is True, "post-commit restart readiness", 60, 0.2)

    # The browser reports the first expiry cut once both raw and grouped hooks reconverge.
    wait_browser("first_expiry",90)
    positions_due = first_source_time["positions"] + 120_000
    time.sleep(max(0, (positions_due - int(time.time() * 1000) - 5000) / 1000))
    stop_service()
    (fault_dir / "positions-retention_before_commit.arm").write_text("crash")
    precommit = start_service(config_path, faults=True)
    wait_until(lambda: precommit.poll() is not None, "pre-commit retention crash", 25, 0.1)
    if precommit.returncode != 86 or not (fault_dir / "positions-retention_before_commit.reached").exists():
        raise RuntimeError(f"pre-commit fault did not fire: {precommit.returncode}")
    (OUT / "fault-before-maintenance-commit.json").write_text(json.dumps({"status":"PASS","point":"retention_before_commit","exit":precommit.returncode,
        "noMaintenanceTransactionPublished":True}, indent=2))
    start_service(config_path)
    wait_until(lambda: current_health().get("ready") is True, "pre-commit restart readiness", 60, 0.2)

    # The browser keeps the original page/subscriptions across both process changes.
    wait_browser("complete",100)
    # Keep both live survivors and expired sticky ownership in the cleaner proof.
    for topic in ("orders","positions"):put(topic,99)
    wait_until(lambda:all(source_health(current_health(),t)["retention"]["active_payload_rows"]==1 and source_health(current_health(),t)["retention"]["safe"] for t in ("orders","positions")),"survivor derived cut",20)
    survivor_health=current_health();(OUT/"survivor-health.json").write_text(json.dumps(survivor_health,indent=2))
    case=json.loads(CASE_PATH.read_text());case["stages"]["survivors"]={t:[dict(make_row(t,99),rowId=identity_id(next(s for s in sources if s["topic"]==t),make_key(99),make_row(t,99)))] for t in ("orders","positions")}
    CASE_PATH.write_text(json.dumps(case));(OUT/"case-survivors.json").write_bytes(CASE_PATH.read_bytes());(RT/"phase.json").write_text(json.dumps({"phase":"survivors"}));wait_browser("survivors",25)
    def snapshot(name):
        capture=command([W/"ingestion/target/release/examples/retention_snapshot",config_path],timeout=90)
        (OUT/name).write_text(capture.stdout);(OUT/(name+".stderr")).write_text(capture.stderr)
    snapshot("canonical-before-cleaner.ndjson")
    time.sleep(12)
    cleaner_partitions = {}
    for source in sources:
        directories = sorted((RT / "broker-data").glob(source["state_topic"] + "-*"))
        cleaner_partitions[source["topic"]] = []
        for directory in directories:
            if not directory.is_dir():
                continue
            deleted = sorted(path.name for path in directory.glob("*.log.deleted"))
            active = sorted(path.name for path in directory.glob("*.log") if not path.name.endswith(".deleted"))
            cleaner_partitions[source["topic"]].append({"partition":directory.name.rsplit("-",1)[-1],"deletedLogSegments":deleted,"activeLogSegments":active})
    if any(not any(partition["deletedLogSegments"] for partition in cleaner_partitions[topic]) for topic in cleaner_partitions):
        raise RuntimeError(f"bounded Kafka canonical cleaner gate saw no compacted/deleted log segments: {cleaner_partitions}")
    cleaner_offsets = {source["topic"]:admin_offsets(source["state_topic"]) for source in sources}
    (OUT / "canonical-cleaner.json").write_text(json.dumps({"status":"PASS","evidence":"Kafka compact-only canonical partitions contain cleaner-produced .log.deleted segments after a bounded wait.",
        "topics":[s["state_topic"] for s in sources],"partitions":cleaner_partitions,"endOffsetsBeforeRestart":cleaner_offsets,
        "cleanupPolicy":{"orders":"compact","positions":"compact"}}, indent=2))
    stop_service()
    restart = start_service(config_path,write_denied=True)
    wait_until(lambda: current_health().get("ready") is True, "post-cleaner exact recovery", 60, 0.2)
    final = current_health()
    if final["records_committed"] != 0:
        raise RuntimeError("fresh post-cleaner process observed source records during timer-only expiry")
    for topic in ("orders", "positions"):
        src = source_health(final, topic)
        if src["retention"]["active_payload_rows"] != 1 or not src["retention"]["safe"] or src["retention"]["pending_due"]:
            raise RuntimeError(f"post-cleaner retention metadata/image is unsafe for {topic}: {src['retention']}")
        if source_next(final)[topic] != source_next(survivor_health)[topic]:
            raise RuntimeError(f"timer-only maintenance advanced source NEXT for {topic}")
    (OUT / "post-cleaner-recovery-health.json").write_text(json.dumps(final, indent=2))
    snapshot("canonical-after-cleaner.ndjson")
    checked=command([sys.executable,W/"scripts/verify-retention-snapshot.py",OUT/"canonical-before-cleaner.ndjson",OUT/"canonical-after-cleaner.ndjson"])
    (OUT/"canonical-image-equality.json").write_text(checked.stdout);(OUT/"canonical-image-equality.log").write_text(checked.stderr)
    launch=json.loads((OUT/"write-denied-launch.json").read_text());launch["predecessor_instance"]=survivor_health["instance"];launch["successor_instance"]=final["instance"];launch["final_entries"]=[p.name for p in Path(launch["cwd"]).iterdir()];assert not launch["final_entries"] and launch["predecessor_instance"]!=launch["successor_instance"];(OUT/"write-denied-launch.json").write_text(json.dumps(launch,indent=2))
    after_cleaner_restart_offsets = {source["topic"]:admin_offsets(source["state_topic"]) for source in sources}
    (OUT / "canonical-cleaner.json").write_text(json.dumps({"status":"PASS","evidence":"Kafka compact-only canonical partitions contain cleaner-produced .log.deleted segments after a bounded wait. Exact same-page query and retention metadata were compared after restart. Canonical topic end offsets can advance for the serialized reconnect guard transaction.",
        "topics":[s["state_topic"] for s in sources],"partitions":cleaner_partitions,"endOffsetsBeforeRestart":cleaner_offsets,
        "endOffsetsAfterRestart":after_cleaner_restart_offsets,"cleanupPolicy":{"orders":"compact","positions":"compact"}}, indent=2))
    time.sleep(6)
    (OUT / "otlp-delivery.json").write_text(json.dumps(OTLP, indent=2))
    if not any(item["path"] == "/v1/metrics" for item in OTLP) or not any(item["path"] == "/v1/traces" for item in OTLP):
        raise RuntimeError(f"actual OTel receiver missed retention metrics or traces: {OTLP}")
    status, metrics, _ = proxy_health("/metrics")
    if status != 200:
        raise RuntimeError("Prometheus scrape failed")
    (OUT / "prometheus.metrics").write_bytes(metrics)
    required_gauges = (b"view_server_retention_backlog", b"view_server_retention_payload_rows",
                       b"view_server_retention_scheduled_expiries", b"view_server_retention_sticky_keys")
    if any(name not in metrics for name in required_gauges):
        raise RuntimeError("Prometheus output missing cached bounded retention gauges")
    (RT / "phase.json").write_text(json.dumps({"phase":"post_cleaner_recovery"}))
    wait_browser("post_cleaner_recovery",45)
    for topic in ("orders","positions"):put(topic,99,1)
    case["stages"]["live"]={t:[dict(make_row(t,99,1),rowId=identity_id(next(s for s in sources if s["topic"]==t),make_key(99),make_row(t,99,1)))] for t in ("orders","positions")};CASE_PATH.write_text(json.dumps(case));(OUT/"case-live.json").write_bytes(CASE_PATH.read_bytes());(RT/"phase.json").write_text(json.dumps({"phase":"live"}));wait_browser("post_cleaner_live",30)
    browser_driver.wait(timeout=15);assert browser_driver.returncode==0
    (OUT/"post-successor-live-health.json").write_text(json.dumps(current_health(),indent=2))
    (OUT / "qualification.json").write_text(json.dumps({"status":"PASS","scope":"Kafka 4.1 loopback; two topics by two partitions; effective source defaults and topic override; exact startup rejection; retention count, source-silent time expiry; production Worker and raw/grouped hooks; two maintenance fault cuts; cleaner/restart recovery; OTel/Prometheus",
        "serviceOrdinarySha256":hashlib.sha256((W / "bin" / "view_server_grouped").read_bytes()).hexdigest(),
        "serviceFaultsSha256":hashlib.sha256((W / "bin" / "view_server_grouped_faults").read_bytes()).hexdigest(),
        "producerSha256":hashlib.sha256((W / "bin" / "generic_kafka_producer_grouped").read_bytes()).hexdigest(),
        "recordsCommittedBeforeMaintenance":baseline["records_committed"],"recordsCommittedInFreshProcess":final["records_committed"],"maintenanceTransactions":final["maintenance_transactions"],
        "maintenanceRowsEvicted":final["maintenance_rows_evicted"],"sourceNext":source_next(final),
        "sourceAgeLowerBoundsUnixMs":first_source_time,
        "browserStages":[event for event in EVENTS if event.get("status")=="PASS"],"otlp":OTLP,
        "limitations":"Kafka cleaner timing is asynchronous; exact delay is recorded, with no hard real-time SLA claim."}, indent=2))
    print("PASS=" + str(OUT), flush=True)


try:
    main()
finally:
    stop_service()
    for proc, log, name in reversed(CHILDREN):
        if proc.poll() is None:
            try:
                if name == "broker":
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    if name == "broker":
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait(timeout=10)
                except ProcessLookupError:
                    pass
        try:
            log.close()
        except Exception:
            pass
    if HTTP is not None:
        HTTP.shutdown()
        HTTP.server_close()
