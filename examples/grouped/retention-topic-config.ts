import {defineRetentionPolicy,type RetentionPolicy} from '../../browser/src/topic-schema.ts';
import {topics} from './topic-config.ts';

const policy=topics.grouped_fixture.identity.source_policy;
const groupedFixtureRetention:RetentionPolicy<typeof policy>=defineRetentionPolicy(policy,{
 maxRetentionMinutes:1440,
 // This key-only compact identity admits one rowId per source key, so this cap
 // is intentionally nonbinding; it does not promise per-key history.
 maxRetentionMessagesPerKey:1,
},100000);

export const retentionPolicies={grouped_fixture:groupedFixtureRetention} as const;
