import assert from 'node:assert/strict';
import {defineRetentionPolicy,retentionDurationMs,validateRetentionPolicy} from '../browser/src/topic-schema.ts';

assert.equal(retentionDurationMs(1440),86_400_000);
assert.equal(retentionDurationMs(0.00001),1);
for(const value of [0,-1,NaN,Infinity,5_256_001])assert.throws(()=>retentionDurationMs(value));
assert.doesNotThrow(()=>validateRetentionPolicy('delete',{maxRetentionMinutes:1440,maxRetentionMessages:50},100));
assert.doesNotThrow(()=>validateRetentionPolicy('compact',{maxRetentionMessagesPerKey:4},100));
assert.doesNotThrow(()=>validateRetentionPolicy('compact,delete',{maxRetentionMessagesPerKey:4},100));
assert.throws(()=>validateRetentionPolicy('delete',{maxRetentionMessagesPerKey:4},100),/requires source cleanupPolicy/);
assert.throws(()=>validateRetentionPolicy('compact',{maxRetentionMessages:4},100),/requires source cleanupPolicy/);
assert.throws(()=>validateRetentionPolicy('delete',{maxRetentionMessages:1.5},100));
assert.throws(()=>validateRetentionPolicy('delete',{maxRetentionMessages:101},100));
assert.throws(()=>validateRetentionPolicy('delete',{maxRetentionMessages:1,maxRetentionMessagesPerKey:1},100),/mutually exclusive/);
assert.throws(()=>validateRetentionPolicy('compact',{maxRetentionMinutes:3,extra:true},100));
assert.deepEqual(defineRetentionPolicy('compact',{maxRetentionMinutes:60,maxRetentionMessagesPerKey:1},100),{maxRetentionMinutes:60,maxRetentionMessagesPerKey:1});
console.log('TypeScript runtime retention validation: all checks passed');
