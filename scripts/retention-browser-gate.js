const status=document.getElementById('retention-status');
const output=document.getElementById('retention-result');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const canonical=value=>JSON.stringify(value,(key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0)):item);
async function post(event){const response=await fetch('/result',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(event)});if(!response.ok)throw Error(`evidence relay returned ${response.status}`);}
async function getHealth(){const response=await fetch('/health',{cache:'no-store'});if(!response.ok)throw Error(`health proxy returned ${response.status}`);return response.json();}
async function getMetrics(){const response=await fetch('/metrics',{cache:'no-store'});if(!response.ok)throw Error(`metrics proxy returned ${response.status}`);return response.text();}
async function waitFor(predicate,label,timeout=30000){const end=Date.now()+timeout;let last;while(Date.now()<end){try{last=await predicate();if(last)return last;}catch{}await pause(100);}throw Error(`timeout ${label}: ${JSON.stringify(last)}`);}
function groupId(topic,catalog,query,row){
 const schema=catalog[topic].schema;
 const parts=query.groupBy.map(name=>{const field=schema.fields.find(value=>value.name===name);const state=!Object.hasOwn(row,name)?0:row[name]===null?1:2;let value=state===2?row[name]:null;if(state===2&&field.kind==='number'){const bytes=new ArrayBuffer(8);new DataView(bytes).setFloat64(0,value===0?0:value,false);value=Array.from(new Uint8Array(bytes),byte=>byte.toString(16).padStart(2,'0')).join('');}return[name,field.kind,state,value];});
 return 'gid1:'+Array.from(new TextEncoder().encode(JSON.stringify([1,topic,catalog[topic].fingerprint,parts])),byte=>byte.toString(16).padStart(2,'0')).join('');
}
function oracle(name,definition,caseData,stage){
 const topic=definition.topic,query=definition.query,records=caseData.stages[stage][topic];
 if(query.select)return records.map(record=>({...Object.fromEntries(query.select.filter(field=>Object.hasOwn(record,field)).map(field=>[field,record[field]])),rowId:record.rowId})).sort((a,b)=>a.rowId<b.rowId?-1:a.rowId>b.rowId?1:0);
 const groups=new Map();for(const record of records){const id=groupId(topic,caseData.catalog,query,record);if(!groups.has(id))groups.set(id,[]);groups.get(id).push(record);}
 const result=[];
 for(const[id,rows]of groups){const output=Object.fromEntries(query.groupBy.filter(field=>Object.hasOwn(rows[0],field)).map(field=>[field,rows[0][field]]));
  for(const[alias,aggregate]of Object.entries(query.aggregates).sort(([a],[b])=>a<b?-1:a>b?1:0)){
   const hasField=Object.hasOwn(aggregate,'field');const values=hasField?rows.filter(row=>Object.hasOwn(row,aggregate.field)&&row[aggregate.field]!==null).map(row=>row[aggregate.field]):[];
   const kind=hasField?caseData.catalog[topic].schema.fields.find(field=>field.name===aggregate.field)?.kind:undefined;
   switch(aggregate.aggFunc){
    case'count':output[alias]=String(rows.length);break;
    case'countDistinct':output[alias]=String(new Set(rows.map(row=>Object.hasOwn(row,aggregate.field)?JSON.stringify(row[aggregate.field]):'missing')).size);break;
    case'sum':output[alias]=kind==='number'?values.reduce((sum,value)=>sum+value,0):values.reduce((sum,value)=>sum+BigInt(value),0n).toString();break;
    case'avg':if(!values.length){output[alias]=null;break;}if(kind==='number'){output[alias]=values.reduce((sum,value)=>sum+value,0)/values.length;break;}{const total=values.reduce((sum,value)=>sum+BigInt(value),0n),scale=10n**18n,denominator=BigInt(values.length),negative=total<0n,absolute=negative?-total:total,numerator=absolute*scale;let rounded=numerator/denominator,remainder=numerator%denominator;if(remainder*2n>denominator||remainder*2n===denominator&&rounded%2n)rounded++;let text=rounded.toString().padStart(19,'0');text=text.slice(0,-18)+'.'+text.slice(-18);text=text.replace(/0+$/,'').replace(/\.$/,'');output[alias]=(negative?'-':'')+text;}break;
    case'min':case'max':if(!values.length){output[alias]=null;break;}{const compare=(a,b)=>['int64','uint64','decimal'].includes(kind)?(BigInt(a)<BigInt(b)?-1:BigInt(a)>BigInt(b)?1:0):(a<b?-1:a>b?1:0);output[alias]=[...values].sort(compare)[aggregate.aggFunc==='min'?0:values.length-1];}break;
   }
  }
  output.rowId=id;result.push(output);
 }
 result.sort((a,b)=>{const av=BigInt(a.s),bv=BigInt(b.s);return av>bv?-1:av<bv?1:a.rowId<b.rowId?-1:a.rowId>b.rowId?1:0;});return result;
}
async function verifyStage(caseData,stage){
 const expected=Object.fromEntries(Object.entries(caseData.definitions).map(([name,definition])=>[name,oracle(name,definition,caseData,stage)]));
 await waitFor(async()=>{const {latest:observed,helpers}=window.groupedDemo.observe();return Object.keys(expected).every(name=>[observed[name],helpers[name]].every(value=>value?.status==='ready'&&canonical(value.rows)===canonical(expected[name])&&value.totalRows===expected[name].length));},`${stage} raw/grouped oracle`,45000);
 const views=window.groupedDemo.observe().windows;
 for(const[name,rows]of Object.entries(expected)){const expectedWindow=Object.fromEntries(rows.slice(0,2).map((row,index)=>[index,row]));if(canonical(views[name]?.rows)!==canonical(expectedWindow))throw Error(`${stage} ${name} viewport differs from the independent oracle`);}
 return {expected,observed:structuredClone(window.groupedDemo.observe()),at:Date.now()};
}
function nextByTopic(health){return Object.fromEntries(health.sources.map(source=>[source.topic,Object.fromEntries(source.partitions.map(p=>[String(p.partition),String(p.durable_next)]))]));}
async function run(){
 const caseResponse=await waitFor(async()=>{const response=await fetch('/retention-case.json',{cache:'no-store'});return response.ok?response:null;},'retention case data',120000);
 const caseData=await caseResponse.json();
 await waitFor(()=>window.groupedDemo?.start,'production application bundle');
 window.groupedDemo.start(caseData.wsUrl,caseData.token,caseData.catalog,caseData.definitions,caseData.endpoint);
 status.textContent='Connected: checking the independent raw and six-aggregate oracle.';
 const initial=await verifyStage(caseData,'initial');const base=await getHealth();
 if(base.records_committed!==caseData.baseline.recordsCommitted)throw Error(`source counter mismatch at initial cut ${base.records_committed}`);
 if(canonical(nextByTopic(base))!==canonical(caseData.baseline.sourceNext))throw Error('source NEXT differs at initial cut');
 const beforeObs=initial.observed.observations.length;
 await post({stage:'browser_ready',status:'PASS',raw:initial,health:base,at:initial.at,queries:Object.fromEntries(Object.entries(initial.expected).map(([name,rows])=>[name,rows.length])),recordsCommitted:base.records_committed,sourceNext:nextByTopic(base)});
 status.textContent='Initial raw and grouped views match. Waiting for source-silent expiry and maintenance recovery.';
 await waitFor(async()=>{const health=await getHealth();const orders=health.sources.find(source=>source.topic==='orders'),positions=health.sources.find(source=>source.topic==='positions');const ready=orders?.retention.active_payload_rows===2&&positions?.retention.active_payload_rows===7&&orders?.retention.maintenance_sequence>0&&orders?.retention.safe&&positions?.retention.safe;const rows=window.groupedDemo.observe().latest;const expected=Object.fromEntries(Object.entries(caseData.definitions).map(([name,definition])=>[name,oracle(name,definition,caseData,'first_expiry').length]));return ready&&Object.entries(expected).every(([name,count])=>rows[name]?.status==='ready'&&rows[name]?.totalRows===count);},'orders expiry while positions remain retained',95000);
 const first=await verifyStage(caseData,'first_expiry');const afterFirst=await getHealth();
 if(afterFirst.instance===base.instance||afterFirst.records_committed!==0)throw Error('first expiry did not recover in a clean process with no source records');
 if(canonical(nextByTopic(afterFirst))!==canonical(nextByTopic(base)))throw Error('timer-only first expiry advanced source NEXT');
 const firstOrders=afterFirst.sources.find(source=>source.topic==='orders').retention,firstPositions=afterFirst.sources.find(source=>source.topic==='positions').retention;
 if(firstOrders.maintenance_sequence<1||firstPositions.maintenance_sequence!==0)throw Error('first expiry changed another topic or lost durable maintenance progress');
 await post({stage:'first_expiry',status:'PASS',raw:first,health:afterFirst,at:first.at,orders:2,positions:7,ordersMaintenanceSequence:afterFirst.sources.find(source=>source.topic==='orders').retention.maintenance_sequence,positionsMaintenanceSequence:afterFirst.sources.find(source=>source.topic==='positions').retention.maintenance_sequence,recordsCommitted:afterFirst.records_committed,processInstance:afterFirst.instance,sourceNext:nextByTopic(afterFirst),observationsAdded:first.observed.observations.length-beforeObs});
 status.textContent='First timer cut passed. The delete topic expired while the compact topic retained its rows.';
 await waitFor(async()=>{const health=await getHealth(),latest=window.groupedDemo.observe().latest;return health.sources.every(source=>source.retention.active_payload_rows===0&&source.retention.safe&&!source.retention.pending_due)&&Object.keys(caseData.definitions).every(name=>latest[name]?.status==='ready'&&latest[name]?.totalRows===0);},'both topic expiries and process recovery',95000);
 const finalCut=await verifyStage(caseData,'complete');const finalHealth=await getHealth();
 if(finalHealth.records_committed!==0)throw Error('timer-only final expiry fabricated source records');
 if(canonical(nextByTopic(finalHealth))!==canonical(nextByTopic(base)))throw Error('timer-only final expiry advanced source NEXT');
 const finalSequences=Object.fromEntries(finalHealth.sources.map(source=>[source.topic,source.retention.maintenance_sequence]));
 const finalRetention=Object.fromEntries(finalHealth.sources.map(source=>[source.topic,{active_payload_rows:source.retention.active_payload_rows,sticky_keys:source.retention.sticky_keys,scheduled_expiries:source.retention.scheduled_expiries,maintenance_sequence:source.retention.maintenance_sequence,canonical_version:source.retention.canonical_version,derived_version:source.retention.derived_version,safe:source.retention.safe}]));
 if(finalSequences.orders<=firstOrders.maintenance_sequence||finalSequences.positions<1)throw Error('completed expiry lost durable per-topic maintenance progress');
 const metrics=await getMetrics();if(!metrics.includes('view_server_retention_maintenance_transactions_total')||!metrics.includes('view_server_retention_evicted_rows_total'))throw Error('Prometheus output missing retention instruments');
 if(finalHealth.maintenance_rows_evicted!==7||finalHealth.maintenance_transactions<1)throw Error('post-restart maintenance counters do not account for the seven compact-topic expiry rows');
 const result={stage:'complete',status:'PASS',raw:finalCut,health:finalHealth,at:finalCut.at,recordsCommitted:finalHealth.records_committed,sourceNext:nextByTopic(finalHealth),maintenanceTransactions:finalHealth.maintenance_transactions,maintenanceRowsEvicted:finalHealth.maintenance_rows_evicted,orders:finalHealth.sources.find(source=>source.topic==='orders').retention,positions:finalHealth.sources.find(source=>source.topic==='positions').retention,metricsSamples:metrics.split('\n').filter(line=>line.startsWith('view_server_retention_'))};
 output.textContent=JSON.stringify(result,null,2);status.textContent='PASS: both topics expired under source silence; raw and grouped views recovered on the same page.';await post(result);
 await waitFor(async()=>{const response=await fetch('/phase.json',{cache:'no-store'});return response.ok&&(await response.json()).phase==='survivors';},'survivor cut',45000);
 Object.assign(caseData,await(await fetch('/retention-case.json',{cache:'no-store'})).json());
 const survivors=await verifyStage(caseData,'survivors');const survivorHealth=await getHealth();
 const metadata=h=>Object.fromEntries(h.sources.map(s=>[s.topic,{...s.retention,last_commit_unix_ms:undefined,last_expiry_delay_ms:undefined}]));
 await post({stage:'survivors',status:'PASS',raw:survivors,health:survivorHealth});
 await waitFor(async()=>{const response=await fetch('/phase.json',{cache:'no-store'});return response.ok&&(await response.json()).phase==='post_cleaner_recovery';},'write-denied successor',90000);
 const recoveredCut=await verifyStage(caseData,'survivors');const recovered=await getHealth();
 if(recovered.instance===survivorHealth.instance||recovered.records_committed!==0||canonical(nextByTopic(recovered))!==canonical(nextByTopic(survivorHealth)))throw Error('write-denied successor progress/instance mismatch');
 if(canonical(metadata(recovered))!==canonical(metadata(survivorHealth)))throw Error('retained metadata changed across cleaner/recovery');
 await post({stage:'post_cleaner_recovery',status:'PASS',raw:recoveredCut,health:recovered});
 await waitFor(async()=>{const response=await fetch('/phase.json',{cache:'no-store'});return response.ok&&(await response.json()).phase==='live';},'successor live update',30000);
 Object.assign(caseData,await(await fetch('/retention-case.json',{cache:'no-store'})).json());const live=await verifyStage(caseData,'live');const liveHealth=await getHealth();
 await post({stage:'post_cleaner_live',status:'PASS',raw:live,health:liveHealth});status.textContent='PASS: source-silent expiry, crashes, nonempty cleaner recovery, write-denied successor and live update.';window.retentionFinished=true;
}
run().catch(async error=>{const failure={stage:'failed',status:'FAIL',message:String(error),stack:error?.stack};status.textContent='FAIL: '+String(error);output.textContent=JSON.stringify(failure,null,2);try{await post(failure);}catch{}});
