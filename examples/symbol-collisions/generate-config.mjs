import fs from 'node:fs';
import {catalog,schemas,keyFields} from './browser/src/generated/topics.ts';
import {compactRowId} from '../../browser/src/row-id-selector.ts';
const [output,brokers,prefix]=process.argv.slice(2),bindings=JSON.parse(fs.readFileSync(import.meta.dirname+'/fixtures/proto-topics/source-bindings.json'));
const sources=Object.keys(catalog).map((topic,i)=>({topic,schema:catalog[topic].fingerprint,brokers,source_topic:prefix+'-'+topic,source_incarnation:prefix+'-'+topic+'-lifetime',group:prefix+'-'+topic+'-owner',state_topic:prefix+'-'+topic+'-canonical-rowid-v2',initialize_empty:true,partitions:[0,1],key_descriptor:bindings.BalanceKey.descriptor,value_descriptor:bindings['Row'+i].descriptor,key_tag:1,key_fields:bindings.BalanceKey.key_fields,mapping:bindings['Row'+i].mapping,identity:compactRowId(keyFields['BalanceKey'],[{source:'key',field:'tenant'},{source:'key',field:'account'}]),readiness:{enter_offset_distance:2,exit_offset_distance:5,max_sample_age_ms:3000,enter_hold_ms:100,exit_hold_ms:100},max_rows:1000}));
fs.writeFileSync(output,JSON.stringify(sources,null,2)+'\n');
