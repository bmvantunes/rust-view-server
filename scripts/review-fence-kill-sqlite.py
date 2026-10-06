#!/usr/bin/env python3
import importlib.util,subprocess,json
spec=importlib.util.spec_from_file_location('h',str(__import__('pathlib').Path(__file__).with_name('run-kill-sqlite.py')));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for mode in ['prepared','idle']:
 c=h.topics('fence-'+mode,partitions=1);topic=c['mode']['config']['state_topic']
 a=subprocess.Popen([str(h.ROOT/'ingestion/target/debug/examples/review_fencing'),mode,topic],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=h.ENV)
 try:
  assert a.stdout.readline().strip()=='prepared'
  successor=h.command([h.ROOT/'ingestion/target/debug/examples/review_fencing','successor',topic]);assert 'successor-committed' in successor
  out,err=a.communicate('wake\n',timeout=20);assert a.returncode==0;result=json.loads(out)
  read=subprocess.run([str(h.KAFKA/'kafka-console-consumer.sh'),'--bootstrap-server','127.0.0.1:34492','--topic',topic,'--from-beginning','--isolation-level','read_committed','--timeout-ms','1000'],env=h.ENV,text=True,capture_output=True,timeout=20)
  assert read.stdout.splitlines()==['committed'],read.stdout
  h.record('native-producer-fencing-'+mode,passed=True,result=result,read_committed=read.stdout,stderr=err)
 finally:
  if a.poll() is None:a.kill();a.wait(timeout=10)
print('EVIDENCE='+str(h.RUN))
