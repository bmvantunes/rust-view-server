import {spawn,execFileSync} from 'node:child_process';
import {mkdtemp,writeFile,appendFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createServer} from 'node:net';
import {createHash,randomBytes} from 'node:crypto';
import {createRequire} from 'node:module';
export const root=resolve(import.meta.dirname,'..');
const require=createRequire(join(root,'browser/package.json'));const {chromium}=require('playwright');
export const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
export async function wait(test,label){const end=Date.now()+20000;while(Date.now()<end){if(await test())return;await new Promise(r=>setTimeout(r,5));}throw Error('timeout '+label);}
async function port(){const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
export async function setup(name){
 const dir=await mkdtemp(join(tmpdir(),'v123-'+name+'-')),token=randomBytes(24).toString('hex'),http=await port(),ws=await port();
 const logs=[],children=[],resources=[];let browser,native,timer;
 const feed=join(dir,'fixture.jsonl'),db=join(dir,'canonical.db'),stop=join(dir,'stop');await writeFile(feed,'');
 function launch(command,args,options={}){const p=spawn(command,args,{cwd:root,detached:true,env:{...process.env,V12_SESSION_TOKEN:token},...options});children.push(p);p.on('error',e=>logs.push(String(e)));p.stdout?.on('data',b=>logs.push(b.toString()));p.stderr?.on('data',b=>logs.push(b.toString()));return p;}
 launch(join(root,'browser/node_modules/.bin/vp'),['dev','--host','127.0.0.1','--port',String(http),'--strictPort'],{cwd:join(root,'browser')});await wait(async()=>{try{return(await fetch(`http://127.0.0.1:${http}/remote-demo.html`)).ok;}catch{return false;}},'Vite');
 browser=await chromium.launch({headless:true});const page=await browser.newPage();
 await page.addInitScript(()=>{
  window.v123ledger=[];let next=0;const Original=window.Worker;
  window.Worker=new Proxy(Original,{construct(Target,args){const worker=new Target(...args);const id=++next;
   const save=(type,message)=>{if(window.v123ledger.length>=16384)throw Error('test event ledger budget exceeded');window.v123ledger.push({worker:id,type,message:structuredClone(message),mainThreadNs:Math.round(performance.now()*1e6)});};
   const send=worker.postMessage.bind(worker);worker.postMessage=(m,...rest)=>{if(m.type==='apply')save('send',m);return send(m,...rest);};
   worker.addEventListener('message',e=>{if(['ack','live','request_error','fatal'].includes(e.data.type))save('receive',e.data);});return worker;}});
 });
 await page.goto(`http://127.0.0.1:${http}/remote-demo.html`);await page.waitForFunction(()=>!!window.v12);
 const url=`ws://127.0.0.1:${ws}/v12`;
 async function server(faults=false){await rm(stop,{force:true});const config={bind:`127.0.0.1:${ws}`,origin:`http://127.0.0.1:${http}`,database:db,source:{incarnation:'v123-fixture',topic:'products',schema:'product-v1'},expected_partitions:[0],mode:{kind:'fixture',path:feed},run_ms:180000,stop_file:stop,subscription_limits:{per_client:70,total:80},profile:true};const cp=join(dir,'config.json');await writeFile(cp,JSON.stringify(config));const start=logs.length;native=launch(join(root,faults?'bin/view_server_faults':'bin/view_server'),[cp],{env:{...process.env,V12_SESSION_TOKEN:token,...(faults?{V121_FAULT_DIR:dir}:{})}});await wait(()=>logs.slice(start).join('').includes('"state":"ready"'),'native ready');return native;}
 const parsed=()=>logs.join('').split('\n').flatMap(l=>{try{return[JSON.parse(l)];}catch{return[];}});
 const sample=()=>{if(native?.exitCode===null)try{const fields=execFileSync('ps',['-o','pid=,rss=,%cpu=,time=','-p',String(native.pid)],{encoding:'utf8'}).trim().split(/\s+/);resources.push({nodeNs:Number(process.hrtime.bigint()),pid:Number(fields[0]),rssKiB:Number(fields[1]),cpuPercent:fields[2],cumulativeCpu:fields[3]});}catch{}};
 async function connect(name,subscriptions=16){await page.evaluate(async({name,url,token,subscriptions})=>window.v12.connect(name,url,token,subscriptions),{name,url,token,subscriptions});}
 async function shutdown(){clearInterval(timer);sample();if(native?.exitCode===null){await writeFile(stop,'stop');await wait(()=>native.exitCode!==null,'shutdown');}}
 return {dir,feed,db,stop,token,url,page,logs,parsed,resources,server,connect,profile(){sample();timer=setInterval(sample,100);},shutdown,
  async cleanup(){clearInterval(timer);await browser.close();for(const p of children)try{process.kill(-p.pid,'SIGTERM');}catch{}await writeFile(join(root,'evidence/v12.3/'+name+'.log'),logs.join(''));await rm(dir,{recursive:true,force:true});},
  async evidence(value){await writeFile(join(root,'evidence/v12.3/'+name+'.json'),JSON.stringify({...value,run_id:process.env.ACCEPTANCE_RUN_ID??null,browser:await browser.version(),node:process.version,release_binary_sha256:await hash(join(root,'bin/view_server')),resources},null,2)+'\n');}
 };
}
