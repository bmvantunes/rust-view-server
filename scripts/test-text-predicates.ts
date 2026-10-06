import assert from 'node:assert/strict';
import {validateQuery,requiresTextPredicate} from '../browser/src/topic-schema.ts';
import {schemas} from '../browser/src/generated/expanded-topics.ts';
const s=schemas.shit;
for(const op of ['contains','startsWith','endsWith'])for(const value of ['', 'é','e\u0301','.+']){const q={select:['oo.price'],where:{op,field:'oo.name',value},orderBy:[]};validateQuery(s,q);assert(requiresTextPredicate(q.where));}
for(const where of [{op:'contains',field:'oo.price',value:'1'},{op:'contains',field:'oo.name',value:'a',mode:'insensitive'},{op:'contains',field:'oo.name',value:'a',caseSensitive:false},{op:'contains',field:'oo.name',value:'\ud800'},{op:'contains',field:'oo.name',value:'x'.repeat(4097)}])assert.throws(()=>validateQuery(s,{select:['oo.price'],where,orderBy:[]}));
assert(requiresTextPredicate({op:'not',clause:{op:'and',clauses:[{op:'endsWith',field:'oo.name',value:'z'}]}}));
console.log('PASS text client validation: 12 positives, 5 negatives, recursive capability detection');
