// No business-field identity: selectors are restricted to the generated key fields.
import {keyFields} from './browser/src/generated/topics.ts';
import {compactRowId} from '../../browser/src/row-id-selector.ts';
export const topics={balances:{message:'Balances',keyMessage:'BalanceKey',identity:compactRowId(keyFields["BalanceKey"],[{source:'key',field:'tenant'},{source:'key',field:'account'}])}} as const;
