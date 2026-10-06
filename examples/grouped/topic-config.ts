import {compactRowId} from '../../browser/src/row-id-selector.ts';
import {keyFields} from './browser/src/generated/topics.ts';
export const topics={grouped_fixture:{message:'GroupedFixture',keyMessage:'GroupedKey',identity:compactRowId(keyFields['GroupedKey'],[{source:'key',field:'key'}])}} as const;
