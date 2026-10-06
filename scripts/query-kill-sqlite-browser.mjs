import {execFileSync} from "node:child_process";
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {readFile} from 'node:fs/promises';
const root=resolve(import.meta.dirname,'..');const require=createRequire(root+'/browser/package.json');const {chromium}=require('playwright');
const cfg=JSON.parse(await readFile(process.argv[2],'utf8'));const expected=JSON.parse(await readFile(process.argv[3],'utf8'));
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(cfg.origin+'/remote-demo.html');await page.waitForFunction(()=>!!window.v12);
 await page.evaluate(async({cfg,token})=>{await window.v12.connect('kafka','ws://'+cfg.bind+'/v13',token);window.v12.mount('kafka');},{cfg,token:process.env.V12_SESSION_TOKEN});
 await page.waitForFunction(want=>document.querySelector('[data-testid="kafka"]')?.textContent===want,expected.hook,{timeout:20000});
 const response=await page.evaluate(()=>window.v12.snapshot('kafka','exact',{where_expr:{op:'true'},direction:'ascending',offset:0,limit:1024}));
 const result=response.results?.exact??response.results?.[0]??response;
 // Preserve the actual Worker response; compare exact string and coefficient values in Python.
 let live=null;
 if(expected.live){
  execFileSync('/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime/kafka_probe',['feed',process.argv[2]],{input:expected.live.rows.map(r=>JSON.stringify(r)).join('\n')+'\n'});
  await page.waitForFunction(want=>document.querySelector('[data-testid="kafka"]')?.textContent===want,expected.live.hook,{timeout:20000});
  live=await page.evaluate(()=>window.v12.snapshot('kafka','after-live',{where_expr:{op:'true'},direction:'ascending',offset:0,limit:1024}));
 }
 console.log(JSON.stringify({live,hook:await page.locator('[data-testid="kafka"]').textContent(),response,result,errors,browser:await browser.version()}));
 await page.evaluate(()=>{window.v12.unmount();window.v12.close('kafka');});
 if(errors.length)throw Error(errors.join('; '));
}finally{await browser.close();}
