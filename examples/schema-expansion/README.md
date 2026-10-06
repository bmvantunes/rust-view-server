# Runnable illustrative schema graph

These are test fixtures, not the company's Buf inputs. Author fields only in the
proto files. `common.proto` is reused twice by Shit; `other.proto` deliberately
reuses the short names Details and Status in another package. Position includes
a nested Meta declaration. Third exercises another root on the same server binary.

From the composed work directory, with the existing pinned caches linked:

```
/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node scripts/generate-proto-topics.mjs --input examples/schema-expansion/topics.proto
/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node scripts/test-schema-expansion.mjs
python3 scripts/build-schema-expansion.py
/bin/sh scripts/test-schema-expansion-pinned.sh
python3 scripts/run-schema-expansion-kafka.py
python3 scripts/run-schema-expansion-cleanup.py green
```

The last three checks require ordinary scoped private-loopback permission. There
is no dependency installation. Generation emits `expanded-topics.ts` plus catalog,
source descriptors/mappings and provenance under `fixtures/expanded-topics`.
A version 3 root opts in with `(view.expanded)=true`. Its descendants' presence
comes from protobuf declarations and the existing optional/null/decimal metadata.

```tsx
import {createTopicHooks} from './product-provider';
import {catalog, enums} from './generated/expanded-topics';
const {useLiveQuery} = createTopicHooks(catalog);
const result = useLiveQuery('shit', {
  select: ['oo.name'],
  where: {op: 'eq', field: 'oo.status', value: enums['example.common.Status'].OPEN},
  orderBy: [{field: 'oo.name', direction: 'asc'}],
});
// Each row exposes readonly rowId and oo?.name only.
```

The company's `message MyShit { decimal price = 1; }` snippet does not supply
its referenced type. No proprietary decimal or Buf plugin behavior is inferred.
See the contract's Buf boundary and the workspace inspection evidence.
