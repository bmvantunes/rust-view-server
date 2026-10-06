#!/usr/bin/env python3
"""Foreground private local example; reuse CP4 Kafka helpers, never historical broker data."""
from pathlib import Path
import argparse,fcntl,hashlib,json,mimetypes,os,signal,subprocess,sys,threading,time,types,urllib.request,uuid
from http.server import ThreadingHTTPServer
W=Path(__file__).resolve().parents[1];ROOT=W.parent;CURRENT=ROOT/'local-demo.json';STOP=threading.Event();ACTIONS=threading.Lock()
source=W/'scripts/run-retention-kafka.py';h=types.ModuleType('local_helpers');h.__file__=str(source)
exec(compile(source.read_text().rsplit('\ntry:\n    main()',1)[0],str(source),'exec'),h.__dict__)
h.W=W;h.ROOT=ROOT
NODE=h.NODE;ENV=h.ENV

def request(url,token):
 req=urllib.request.Request(url+'/shutdown',data=b'{}',headers={'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
 with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)

def preflight():
 required=[NODE,Path(h.JAVA_HOME)/'bin/java',h.KAFKA/'kafka-server-start.sh',h.OLD/'broker.properties',W/'browser/node_modules/typescript/package.json',W/'experiments/v131/node_modules/protobufjs/package.json']
 for p in required:
  if not p.is_file():raise RuntimeError('Missing existing prerequisite: '+str(p)+'; restore the approved pinned input. This launcher installs nothing.')
 baseline=json.loads((ROOT/'BASE-CP4.json').read_text())
 for n in ['bin/view_server_expanded','bin/generic_kafka_producer_expanded']:
  p=W/n
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=baseline[n]:raise RuntimeError('Expected reviewed CP4 executable differs or is missing: '+str(p))
 v=h.command([NODE,'--version']).stdout.strip()
 if v!='v26.1.0':raise RuntimeError('Expected qualified Node v26.1.0 at '+str(NODE)+'; got '+v)
 props=(h.OLD/'broker.properties').read_text()
 for expected in ['PLAINTEXT://127.0.0.1:34492','CONTROLLER://127.0.0.1:34493','log.dirs='+str(h.OLD/'broker-data')]:
  if expected not in props:raise RuntimeError('Existing private broker template differs; inspect '+str(h.OLD/'broker.properties'))
 h.command([Path(h.JAVA_HOME)/'bin/java','-version'])
 h.command(['sh',W/'scripts/typecheck-browser.sh'],timeout=60)
 print('Preflight PASS: Node26.1.0, project-local TypeScript/React, Java21, existing Kafka4.1.0 and exact CP4 binaries.',flush=True)

def action(name):
 with ACTIONS:
  if STOP.is_set():raise RuntimeError('Demo is stopping')
  log=open(h.OUT/('source-'+uuid.uuid4().hex[:8]+'.log'),'w')
  p=h.record_process(subprocess.Popen([str(NODE),str(W/'scripts/local-source.mjs'),str(h.RT/'service.json'),name],cwd=W,env=ENV,stdout=subprocess.PIPE,stderr=log,text=True,start_new_session=True),log,'action')
  try:out,_=p.communicate(timeout=20)
  except subprocess.TimeoutExpired:
   if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
   p.wait();raise RuntimeError('Source action exceeded20second bound; see '+str(h.OUT))
  if p.returncode:raise RuntimeError('Source action failed; see '+str(h.OUT))
  result=json.loads(out);(h.OUT/('action-'+str(time.time_ns())+'.json')).write_text(json.dumps(result,indent=2)+'\n');return result

class Handler(h.Handler):
 def do_GET(self):
  path=self.path.split('?',1)[0]
  if path=='/local-config.json':
   self.end(200,json.dumps({'url':f"ws://127.0.0.1:{h.PORTS['query']}/v15",'token':h.TOKEN,'catalog':PUBLIC}).encode(),'application/json');return
  if path in ['/','/join-demo.html']:
   self.end(200,(W/'build/join/join-demo.html').read_bytes(),'text/html; charset=utf-8');return
  if path.startswith('/assets/'):
   p=(W/'build/join'/path.lstrip('/')).resolve();base=(W/'build/join').resolve()
   if not p.is_relative_to(base) or not p.is_file():self.end(404,b'missing');return
   self.end(200,p.read_bytes(),mimetypes.guess_type(p)[0] or 'application/octet-stream');return
  if path=='/health':super().do_GET();return
  self.end(404,b'missing')
 def do_POST(self):
  if self.path=='/shutdown':
   if self.headers.get('Authorization')!='Bearer '+CONTROL:self.end(403,b'invalid run token');return
   self.end(200,b'{"stopping":true}','application/json');STOP.set();return
  if self.path!='/source-action':self.end(404,b'missing');return
  if self.headers.get('Origin')!=ORIGIN:self.end(403,b'expected same local origin');return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=256:raise ValueError('Expected a small action document')
   doc=json.loads(self.rfile.read(size))
   if not isinstance(doc,dict) or set(doc)!={'action'} or doc['action'] not in ['reset','match','update','delete']:raise ValueError('Choose reset, match, update or delete')
   self.end(200,json.dumps(action(doc['action'])).encode(),'application/json')
  except Exception as e:self.end(400,json.dumps({'error':str(e)}).encode(),'application/json')

def stop_owned():
 errors=[]
 for p,log,name in reversed(h.CHILDREN):
  try:
   if p.poll() is None:
    try:
     if name in ['broker','action']:os.killpg(p.pid,signal.SIGTERM)
     else:p.terminate()
    except ProcessLookupError:pass # It exited between poll and signal; still reap it.
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:
     try:
      if name in ['broker','action']:os.killpg(p.pid,signal.SIGKILL)
      else:p.kill()
     except ProcessLookupError:pass
     p.wait(timeout=5)
  except Exception as e:errors.append({'pid':p.pid,'name':name,'error':str(e)})
  finally:
   if log:
    try:log.close()
    except Exception as e:errors.append({'pid':p.pid,'name':name,'error':'log close: '+str(e)})
 owned=[{'pid':p.pid,'name':name,'exit':p.poll()} for p,_,name in h.CHILDREN]
 return {'stopped':all(p['exit'] is not None for p in owned),'owned':owned,'errors':errors}

def start(port):
 global PUBLIC,CONTROL,ORIGIN
 if not 1024<=port<=65535:raise RuntimeError("Choose a local browser port between1024 and65535")
 lock=open(ROOT/'local-demo.lock','a+')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise RuntimeError('This development checkout already owns a demo. Use status or stop.')
 preflight()
 built=subprocess.run([str(NODE),'node_modules/vite-plus/bin/vp','build','--config','vite.join.config.ts'],cwd=W/'browser',env=ENV,capture_output=True,text=True,timeout=60)
 if built.returncode:raise RuntimeError(built.stdout+built.stderr)
 run='local-'+uuid.uuid4().hex[:12];h.LABEL=run;h.RT=ROOT/'runtime'/run;h.OUT=ROOT/'evidence'/run;h.RT.mkdir(parents=True);h.OUT.mkdir(parents=True);(h.OUT/'browser-build.log').write_text(built.stdout+built.stderr)
 h.PORTS={name:h.free_port() for name in ['broker','controller','query','health']};CONTROL=uuid.uuid4().hex+uuid.uuid4().hex
 catalog=json.loads((W/'fixtures/expanded-topics/catalog.json').read_text());PUBLIC={k:v for k,v in json.loads((W/'fixtures/expanded-topics/browser-catalog.json').read_text()).items() if k in ['shit','nested_positions']}
 http=ThreadingHTTPServer(('127.0.0.1',port),Handler);http.daemon_threads=True;h.PORTS['web']=http.server_address[1];ORIGIN=f"http://127.0.0.1:{h.PORTS['web']}";h.BROKER=f"127.0.0.1:{h.PORTS['broker']}";h.HTTP=http
 thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
 signal.signal(signal.SIGINT,lambda *_:STOP.set());signal.signal(signal.SIGTERM,lambda *_:STOP.set())
 try:
  h.start_broker();bindings=json.loads((W/'fixtures/expanded-topics/source-bindings.json').read_text());sources=[]
  for topic,root in [('shit','example.Shit'),('nested_positions','example.Position')]:
   b=bindings[root];key=bindings['example.common.Key'];s=dict(topic=topic,schema=PUBLIC[topic]['fingerprint'],brokers=h.BROKER,source_topic=run+'-'+topic,source_incarnation=run+'-'+topic,group=run+'-'+topic+'-owner',state_topic=run+'-'+topic+'-canonical',initialize_empty=True,partitions=[0,1],key_descriptor=key['descriptor'],value_descriptor=b['descriptor'],key_tag=0,key_fields=key['key_fields'],mapping=b['mapping'],identity={'source_policy':'compact','components':[{'source':'key','field':'account.id'}]},readiness={'enter_offset_distance':2,'exit_offset_distance':5,'max_sample_age_ms':3000,'enter_hold_ms':100,'exit_hold_ms':100},max_rows=1000)
   sources.append(s);h.create_topic(s['source_topic'],policy='compact');h.create_topic(s['state_topic'],canonical=True)
  catalog['topics']=[t for t in catalog['topics'] if t['topic'] in PUBLIC];ids={t['schema'] for t in catalog['topics']};catalog['schemas']=[s for s in catalog['schemas'] if hashlib.sha256(json.dumps(s,separators=(',',':')).encode()).hexdigest() in ids]
  config=h.config_doc(sources,catalog,h.PORTS['query'],h.PORTS['health'],h.PORTS['web'],probe=True);(h.RT/'service.json').write_text(json.dumps(config,indent=2)+'\n')
  log=open(h.OUT/'service.log','w');service=h.record_process(subprocess.Popen([str(W/'bin/view_server_expanded'),str(h.RT/'service.json')],cwd=h.RT,env=ENV,stdout=log,stderr=subprocess.STDOUT),log,'service')
  h.wait_until(lambda:h.current_health()['ready'],'private service readiness',40);action('reset');h.wait_until(lambda:h.current_health()['ready'],'seed readiness',10)
  meta={'run':run,'url':ORIGIN+'/','control':CONTROL,'runtime':str(h.RT),'evidence':str(h.OUT),'service_config':str(h.RT/'service.json'),'owned_pids':[p.pid for p,_,_ in h.CHILDREN if p.poll() is None]};CURRENT.write_text(json.dumps(meta,indent=2)+'\n');os.chmod(CURRENT,0o600);(h.OUT/'run.json').write_text(json.dumps({k:v for k,v in meta.items() if k!='control'},indent=2)+'\n')
  print('BROWSER_URL='+ORIGIN+'/',flush=True);print('Ready. Open that URL. Ctrl+C or: python3 scripts/local-demo.py stop',flush=True)
  while not STOP.wait(.5):
   if service.poll() is not None or h.CHILDREN[0][0].poll() is not None:raise RuntimeError('Task-owned service/broker exited; see '+str(h.OUT))
 finally:
  STOP.set()
  try:http.shutdown();http.server_close()
  except Exception as e:print('Local HTTP shutdown: '+str(e),file=sys.stderr)
  cleanup=stop_owned()
  if cleanup['stopped'] and CURRENT.exists() and json.loads(CURRENT.read_text()).get('run')==run:CURRENT.unlink()
  (h.OUT/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
  if not cleanup['stopped']:raise RuntimeError('Cleanup incomplete; inspect '+str(h.OUT/'cleanup.json')+'; unrelated processes were not signalled.')
  print('Stopped task-owned processes. Logs retained at '+str(h.OUT),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['preflight','start','status','stop']);parser.add_argument('--port',type=int,default=4173,help='loopback browser port (default4173)');args=parser.parse_args()
 try:
  if args.command=='preflight':preflight()
  elif args.command=='start':start(args.port)
  elif not CURRENT.exists():print('No active demo recorded for this checkout.')
  else:
   doc=json.loads(CURRENT.read_text())
   if args.command=='status':print(json.dumps({k:v for k,v in doc.items() if k!='control'},indent=2))
   else:
    print(request(doc['url'].rstrip('/'),doc['control']))
    end=time.monotonic()+40
    while CURRENT.exists() and time.monotonic()<end:time.sleep(.2)
    if CURRENT.exists():raise RuntimeError('Stop requested; cleanup has not completed. Inspect task logs; no unrelated PIDs were signalled.')
 except (Exception,KeyboardInterrupt) as e:print('Local demo: '+str(e),file=sys.stderr);sys.exit(1)
