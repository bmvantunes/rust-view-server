#!/usr/bin/env python3
"""Isolated Kafka process-crash qualification. Never accepts arbitrary broker addresses."""
import json,os,pathlib,subprocess,tempfile,time,uuid,signal,hashlib,sys,shutil,threading,platform
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=pathlib.Path('/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime')
KAFKA=RUNTIME/'kafka_2.13-4.1.0/bin'
NODE='/Users/bruno/.nvm/versions/node/v26.1.0/bin/node'
TOKEN='kill-sqlite-test-session-token-0000000000'
RUN=ROOT/'evidence/kill-sqlite'/('run-'+str(uuid.uuid4()))
RUN.mkdir(); ENV={**os.environ,'JAVA_HOME':'/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home','V12_SESSION_TOKEN':TOKEN}
processes=[];checks=[];dirs=[]
BINDINGS=[ROOT/'ingestion/src/kafka_canonical.rs',ROOT/'ingestion/src/kafka_state.rs',ROOT/'ingestion/src/durable.rs',ROOT/'ingestion/src/durable_coordinator.rs',ROOT/'ingestion/src/faults.rs',ROOT/'ingestion/src/bin/view_server.rs',ROOT/'ingestion/Cargo.toml',ROOT/'ingestion/Cargo.lock',ROOT/'browser/src/product.remote.worker.ts',ROOT/'browser/src/product-provider.tsx',RUNTIME/'view_server',RUNTIME/'view_server_faults',RUNTIME/'kafka_probe']
if os.environ.get('HOT_SERVICE_BINARY'):BINDINGS.append(pathlib.Path(os.environ['HOT_SERVICE_BINARY']))
IDENTITIES={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in BINDINGS}
(RUN/'bindings-start.json').write_text(json.dumps(IDENTITIES,indent=2))
(RUN/'environment.json').write_text(json.dumps({'platform':platform.platform(),'machine':platform.machine(),'python':sys.version,'broker':'Kafka 4.1.0','broker_config':(RUNTIME/'broker.properties').read_text(),'consumer_isolation':'read_committed','transaction_timeout_ms':30000,'max_poll_interval_ms':300000},indent=2))
def record(name,**data):
    checks.append({'name':name,**data});(RUN/'checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks[-1]),flush=True)
def command(args,**kwargs):
    result=subprocess.run(list(map(str,args)),env=ENV,text=True,capture_output=True,timeout=60,**kwargs)
    if result.returncode:raise RuntimeError(f'{args}: {result.stdout}\n{result.stderr}')
    return result.stdout

def topics(tag,policy='compact',partitions=2):
    source='ksq-'+RUN.name[4:12]+'-'+tag+'-source';state=source.replace('-source','-state');group=source+'-group'
    for name,policy_ in [(source,'delete'),(state,policy)]:
        command([KAFKA/'kafka-topics.sh','--bootstrap-server','127.0.0.1:34492','--create','--topic',name,'--partitions',str(partitions),'--replication-factor','1','--config','cleanup.policy='+policy_,'--config','min.compaction.lag.ms=3600000'])
    schemas={str(i):{'schemaType':'PROTOBUF','schema':(ROOT/'ingestion/fixtures'/f).read_text()} for i,f in [(1,'key.proto'),(2,'product-v1.proto')]}
    return {'bind':'127.0.0.1:34501','origin':'http://127.0.0.1:34494','source':{'incarnation':source+'-lifetime','topic':source,'schema':'product-v1'},'expected_partitions':list(range(partitions)),'mode':{'kind':'kafka_canonical','config':{'brokers':'127.0.0.1:34492','group':group,'state_topic':state,'initialize_empty':True,'schemas':schemas}},'run_ms':600000,'stop_file':str(RUN/(tag+'-stop'))}

def save_config(c,label):
    p=RUN/(label+'-config.json');p.write_text(json.dumps(c));return p

def events(p):
    out=[]
    for line in p['log'].read_text().splitlines():
        try:out.append(json.loads(line))
        except ValueError:pass
    return out

def wait(test,label,timeout=35):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        if test():return
        time.sleep(.02)
    raise RuntimeError('timeout '+label)

def launch(c,label,fault=None,readonly=True):
    cp=save_config(c,label);wd=pathlib.Path(tempfile.mkdtemp(prefix='ksq-'+label+'-')).resolve();assert not list(wd.iterdir());dirs.append(wd)
    controls=RUN/(label+'-controls');controls.mkdir()
    if fault:(controls/(fault+'.arm')).write_text('wait')
    log=RUN/(label+'.log');profile='(version 1)(allow default)(deny file-write*)'
    if fault:profile+='(allow file-write* (subpath '+json.dumps(str(controls))+'))'
    for old in dirs[:-1]:profile+='(deny file-read* (subpath '+json.dumps(str(old))+'))'
    cmd=[os.environ.get('HOT_SERVICE_BINARY',str(RUNTIME/('view_server_faults' if fault or os.environ.get('KILL_SQLITE_SAME_BINARY')=='1' else 'view_server'))),str(cp)]
    if readonly:
        denied=subprocess.run(['/usr/bin/sandbox-exec','-p',profile,'/usr/bin/touch',str(wd/'forbidden-write-probe')],capture_output=True,text=True)
        assert denied.returncode!=0 and not list(wd.iterdir()),denied
        prior=[]
        for old in dirs[:-1]:
            result=subprocess.run(['/usr/bin/sandbox-exec','-p',profile,'/bin/ls',str(old)],capture_output=True,text=True)
            assert result.returncode!=0,(old,result)
            prior.append({'path':str(old),'returncode':result.returncode})
        (RUN/(label+'-sandbox-proof.json')).write_text(json.dumps({'write_denied':denied.returncode,'prior_directory_reads_denied':prior,'profile':profile},indent=2))
        cmd=['/usr/bin/sandbox-exec','-p',profile]+cmd
    output=open(log,'w');start=time.monotonic();proc=subprocess.Popen(cmd,cwd=wd,env={**ENV,'V121_FAULT_DIR':str(controls)},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    def capture():
        for line in proc.stdout:output.write(line);output.flush()
    thread=threading.Thread(target=capture,daemon=True);thread.start()
    p={'proc':proc,'wd':wd,'config':cp,'log':log,'controls':controls,'started':start,'output':output,'label':label,'thread':thread};processes.append(p)
    return p

def ready(p):
    def check():
        if p['proc'].poll() is not None:raise RuntimeError(str(p['proc'].returncode)+': '+p['log'].read_text())
        return any(v.get('state')=='ready' for v in events(p))
    wait(check,'ready '+p['label'])
    record(p['label']+'-ready',seconds=time.monotonic()-p['started'],events=events(p),cwd=str(p['wd']),created_files=[str(f.relative_to(p['wd'])) for f in p['wd'].rglob('*')]);assert not list(p['wd'].iterdir())

def kill(p,sig=signal.SIGKILL):
    if p['proc'].poll() is None:p['proc'].send_signal(sig);p['proc'].wait(timeout=15)
    p['output'].flush();assert not list(p['wd'].iterdir());record(p['label']+'-exit',returncode=p['proc'].returncode,signal=sig,files=[])

def feed(cp,rows,abort=False):
    return command([RUNTIME/'kafka_probe','abort' if abort else 'feed',cp],input=''.join(json.dumps(v)+'\n' for v in rows))
def inspect(cp,state_only=False):return json.loads(command([RUNTIME/'kafka_probe','inspect-state' if state_only else 'inspect',cp]))
def browser(p,ids,live=None):
    expected=RUN/(p['label']+'-expected.json');expected.write_text(json.dumps({'hook':str(len(ids))+'|'+','.join(ids),'live':live}))
    result=json.loads(command([NODE,ROOT/'scripts/query-kill-sqlite-browser.mjs',p['config'],expected]))
    assert not result['errors'];cut=inspect(p['config'])['recovery']['snapshot'];assert {r['id']:r for r in (result['live'] or result['response'])['rows']}=={r['id']:r for r in cut['rows']};assert (result['live'] or result['response'])['total_rows']==len(cut['rows']);assert (result['live'] or result['response'])['remote']['sourceSequence']==str(cut['last_source_batch']);(RUN/(p['label']+'-browser.json')).write_text(json.dumps(result,indent=2));record(p['label']+'-browser',hook=result['hook'],browser=result['browser']);return result

def committed(p,count):wait(lambda:len([v for v in events(p) if v.get('state')=='source_committed'])>=count,'committed')

def qualify():
    try:
        assert '127.0.0.1:34492' in (RUNTIME/'broker.properties').read_text()
        c=topics('crash');a=launch(c,'commit-a');ready(a)
        feed(a['config'],[{'id':'a','partition':0,'amount':'1.234567890123456789'},{'id':'b','partition':1,'amount':'9'}]);committed(a,2)
        initial=inspect(a['config']);assert len(initial['recovery']['snapshot']['rows'])==2;browser(a,['a','b'])
        (a['controls']/'kafka_after_commit.arm').write_text('wait')
        # A initially had no fault writes permitted; restart with a control-enabled profile.
        pathlib.Path(c['stop_file']).write_text('stop');a['proc'].wait(timeout=15);pathlib.Path(c['stop_file']).unlink();kill(a)
        a=launch(c,'commit-a-armed',fault='kafka_after_commit');ready(a)
        feed(a['config'],[{'id':'c','partition':0,'amount':'20'}]);wait(lambda:(a['controls']/'kafka_after_commit.reached').exists(),'after commit')
        committed_cut=inspect(a['config']);assert len(committed_cut['recovery']['snapshot']['rows'])==3
        kill(a);b=launch(c,'commit-b');ready(b);after=inspect(b['config'])
        assert after['recovery']==committed_cut['recovery'];assert after['group_offsets']==committed_cut['group_offsets'];browser(b,['a','b','c'])
        record('crash-A-commit-before-derived',passed=True,committed=committed_cut,restored=after)
        kill(b,signal.SIGTERM)
        a=launch(c,'abort-a',fault='kafka_before_commit');ready(a)
        feed(a['config'],[{'id':'d','partition':1,'amount':'30'}]);wait(lambda:(a['controls']/'kafka_before_commit.reached').exists(),'before commit')
        hidden=inspect(a['config'],state_only=True);assert hidden['recovery']==after['recovery'];kill(a)
        b=launch(c,'abort-b');ready(b);restored=[v['metrics'] for v in events(b) if v.get('state')=='restore_proven'][0]
        assert restored['restored_sequence']==after['recovery']['snapshot']['last_source_batch'];assert restored['restored_rows']==3
        replayed=inspect(b['config']);assert len(replayed['recovery']['snapshot']['rows'])==4;assert replayed['recovery']['snapshot']['last_source_batch']==restored['restored_sequence']+1;browser(b,['a','b','c','d'])
        record('crash-B-uncommitted-invisible-then-source-replayed-once',passed=True,hidden=hidden,restored=restored,after=replayed)
        feed(b['config'],[{'id':'ghost','partition':0,'amount':'-1'}],abort=True)
        feed(b['config'],[{'id':'a','partition':0,'delete':True}]);committed(b,1);browser(b,['b','c','d']);cut=inspect(b['config']);assert all(r['id']!='ghost' for r in cut['recovery']['snapshot']['rows']);record('aborted-source-and-tombstone',passed=True,cut=cut)
        kill(b);b=launch(c,'delete-successor');ready(b);assert inspect(b['config'])['recovery']==cut['recovery'];browser(b,['b','c','d'],live={'rows':[{'id':'e','partition':1,'amount':'40'}],'hook':'4|b,c,d,e'});record('mounted-hook-live-update-after-replacement',passed=True);kill(b)
        # Fail closed on unsupported retention; this must never announce READY.
        bad=topics('bad-policy','compact,delete');p=launch(bad,'bad-policy');p['proc'].wait(timeout=15);assert p['proc'].returncode!=0;assert 'cleanup.policy must be exactly compact' in p['log'].read_text();record('compact-delete-rejected',passed=True)
        record('result',passed=True,scope='real Kafka crash A/B, empty/read-only filesystems, MessagePack Worker mounted hook, source abort/delete, successor, retention policy')
    except BaseException as e:
        record('failure',error=str(e));raise
    finally:
        for p in processes:
            if p['proc'].poll() is None:p['proc'].kill();p['proc'].wait(timeout=10)
            p['thread'].join(timeout=5);p['output'].close()
        record('bindings-unchanged',passed=IDENTITIES=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in BINDINGS})
        (RUN/'identities.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RUNTIME/'view_server_faults',RUNTIME/'kafka_probe',ROOT/'ingestion/src/kafka_canonical.rs',ROOT/'ingestion/src/kafka_state.rs',ROOT/'ingestion/src/bin/view_server.rs']},indent=2))
        print('EVIDENCE='+str(RUN),flush=True)

if __name__=="__main__":qualify()
