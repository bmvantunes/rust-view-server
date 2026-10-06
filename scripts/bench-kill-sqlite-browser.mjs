import {createRequire} from 'node:module';import{resolve}from'node:path';import{readFile}from'node:fs/promises';
const root=resolve(import.meta.dirname,'..'),require=createRequire(root+'/browser/package.json'),{chromium}=require('playwright');
const cfg=JSON.parse(await readFile(process.argv[2],'utf8')),browser=await chromium.launch({headless:true});
try{const page=await browser.newPage();await page.goto(cfg.origin+'/remote-demo.html');await page.waitForFunction(()=>!!window.v12);
const r=await page.evaluate(async({cfg,token})=>{await window.v12.connect('bench','ws://'+cfg.bind+'/v13',token);const start=performance.now();const result=await window.v12.snapshot('bench','first',{where_expr:{op:'true'},direction:'ascending',offset:0,limit:16});const elapsedMs=performance.now()-start;window.v12.close('bench');return{elapsedMs,result};},{cfg,token:process.env.V12_SESSION_TOKEN});console.log(JSON.stringify(r));}finally{await browser.close();}
