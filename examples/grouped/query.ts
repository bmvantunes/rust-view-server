import {createTopicHooks} from '../../browser/src/product-provider';
import {catalog} from './browser/src/generated/topics';
export const hooks=createTopicHooks(catalog);
export const grouped={groupBy:['group'],aggregates:{rows:{aggFunc:'count'},distinctValues:{aggFunc:'countDistinct',field:'decimal'},total:{aggFunc:'sum',field:'decimal'},average:{aggFunc:'avg',field:'decimal'},lowest:{aggFunc:'min',field:'decimal'},highest:{aggFunc:'max',field:'decimal'}},orderBy:[{aggregate:'total',direction:'desc'}]} as const;
export function useGroupedValues(){return hooks.useLiveQuery('grouped_fixture',grouped);}
export function useGroupedViewport(){return hooks.useLiveQueryViewport('grouped_fixture');}
