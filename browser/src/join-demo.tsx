import React, {useEffect, useLayoutEffect, useState, useSyncExternalStore} from 'react';
import {createRoot} from 'react-dom/client';
import {
  BrowserProductProvider, ProductProvider, createTopicHooks, defineJoin,
  useViewServerHealthSummary, useSourceHealth,
} from './product-provider';
import {aggregateDecimal, validateSchema, schemaFingerprint, verifyCatalog, type BrowserCatalog} from './topic-schema';
import {catalog as generatedCatalog} from './generated/expanded-topics';

// The generated catalog is the only business schema authority in this example.
export const demoCatalog = {shit: generatedCatalog.shit, nested_positions: generatedCatalog.nested_positions};
export const hooks = createTopicHooks(demoCatalog);
export const joined = defineJoin(demoCatalog, {
  left: {topic: 'shit', as: 'l'}, right: {topic: 'nested_positions', as: 'r'},
  kind: 'left', cardinality: 'many_to_one', on: {left: 'oo.name', right: 'details.name'},
  limits: {maxLeftRowsPerKey: 4, maxOutputRows: 1000},
});
const inner = defineJoin(demoCatalog, {...joined.joinDefinition, kind: 'inner'});
export const selected = {
  select: ['l.label', 'l.oo.name', 'l.oo.status', 'l.oo.price', 'r.details.name', 'r.details.status', 'r.details.price'],
  orderBy: [{field: 'l.label', direction: 'asc'}],
} as const;
const observed: Record<string, unknown> = {};
let provider: BrowserProductProvider | undefined;
let root: ReturnType<typeof createRoot> | undefined;

function Status({value}: {value: string}) {return <span className={`status ${value}`}>{value}</span>;}
function Json({value}: {value: unknown}) {return <pre>{JSON.stringify(value, null, 2)}</pre>;}
function message(error: unknown) {return error instanceof Error ? error.message : String(error);}

function Demo({activeProvider}: {activeProvider: BrowserProductProvider}) {
  const [filter, setFilter] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState('Alice starts without a matching right row.');
  const left = hooks.useLiveQuery(joined, {...selected, where: {op: 'contains', field: 'l.label', value: filter}});
  const matched = hooks.useLiveQuery(inner, selected);
  const global = hooks.useLiveQuery(joined, {
    global: true, aggregates: {n: {aggFunc: 'count'}, sum: {aggFunc: 'sum', field: 'r.details.price'}}, orderBy: [],
  });
  const grouped = hooks.useLiveQuery(joined, {
    groupBy: ['l.oo.status'], aggregates: {sum: {aggFunc: 'sum', field: 'r.details.price'}},
    having: {op: 'gt', field: 'sum', value: aggregateDecimal('0')}, orderBy: [],
  });
  const view = hooks.useLiveQueryViewport(joined);
  const helper = view.useWholeResult(selected);
  // Derive the sink's state from the actual hook result, never a duplicate row interface.
  const [windowRows, setWindowRows] = useState<ReadonlyArray<typeof helper.rows[number]>>([]);
  const [count, setCount] = useState(0);
  const health = useViewServerHealthSummary();
  const leftHealth = useSourceHealth({topic: 'shit'});
  const rightHealth = useSourceHealth({topic: 'nested_positions'});
  const diagnostics = useSyncExternalStore(activeProvider.subscribeHealth, activeProvider.getHealthSnapshot, activeProvider.getHealthSnapshot);

  useEffect(() => {
    const generation = view.viewport.replace({query: selected, window: {firstRow: 0, lastRow: 1}, sink: {
      setRowCount(next) {setCount(next); observed.count = next;},
      setRowData(rows) {setWindowRows(Object.values(rows)); observed.window = rows;},
    }});
    return () => generation.release();
  }, [view.viewport]);
  useLayoutEffect(() => {
    Object.assign(observed, {left, inner: matched, global, grouped, helper, health, dependencies: diagnostics.snapshot?.dependencies});
  }, [left, matched, global, grouped, helper, health, diagnostics]);

  async function act(action: 'match' | 'update' | 'delete' | 'reset') {
    if (busy) return;
    setBusy(true); setActionMessage('Sending source change…');
    try {
      const response = await fetch('/source-action', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action})});
      if (!response.ok) throw new Error(`Source change failed (${response.status}): ${await response.text()}`);
      setActionMessage(`${action === 'delete' ? 'Delete' : action === 'reset' ? 'Reset' : action === 'match' ? 'Match' : 'Update'} acknowledged by the source. Live query results update independently.`);
    } catch (error) {setActionMessage(message(error));}
    finally {setBusy(false);}
  }

  return <main>
    <header><p className="eyebrow">VIEW SERVER · LOCAL EXAMPLE</p><h1>Two sources. One live view.</h1><p>Follow Alice through a LEFT join. Queries use the production Worker and generated schema types.</p>
      <div className="pills"><span>Connection <Status value={health.connection}/></span><span>Health <Status value={health.status}/></span><span>Queries <Status value={left.status}/></span></div>
    </header>
    <section className="controls"><div><h2>Change the source</h2><p>Create a match at 7, change its exact value to 9, or remove it. Reset restores Alice with no match.</p></div>
      <div className="buttons"><button disabled={busy} onClick={() => void act('match')}>Match · 7</button><button disabled={busy} onClick={() => void act('update')}>Update · 9</button><button disabled={busy} onClick={() => void act('delete')}>Remove match</button><button className="secondary" disabled={busy} onClick={() => void act('reset')}>Reset</button></div>
      <p role="status" className="action-message">{actionMessage}</p>
    </section>
    <section><div className="section-title"><div><h2>Selected fields · LEFT join</h2><p><code>useLiveQuery</code> · version {left.version} · {left.totalRows} row(s). A null right alias means unmatched.</p></div><label>Literal label filter<input value={filter} onChange={event => setFilter(event.target.value)} placeholder="Try Alice"/></label></div>
      {left.message && <p role="alert">{left.message}</p>}
      <div className="table-wrap"><table><thead><tr><th>Person / key</th><th>Source enum</th><th>Exact left Decimal</th><th>Right match / Decimal</th><th>Stable readonly rowId</th></tr></thead><tbody>{left.rows.map(row => <tr key={row.rowId}><td><strong>{row.l.label}</strong><small>{row.l.oo?.name ?? 'missing key'}</small></td><td>{row.l.oo ? `${row.l.oo.status.domain} · ${row.l.oo.status.code}` : 'missing parent'}</td><td>{row.l.oo?.price === undefined ? 'missing' : row.l.oo.price === null ? 'null' : row.l.oo.price}</td><td>{row.r === null ? <span className="unmatched">Unmatched · null</span> : <>{row.r.details?.name ?? 'missing key'}<small>{row.r.details?.price === undefined ? 'missing' : row.r.details.price === null ? 'null' : row.r.details.price}</small></>}</td><td><code className="row-id">{row.rowId}</code></td></tr>)}</tbody></table>{left.rows.length === 0 && <p className="empty">{left.status === 'ready' ? 'No rows match this label filter.' : 'Waiting for a query result…'}</p>}</div>
      <details><summary>Exact selected result, including nested enum values</summary><Json value={left.rows}/></details>
    </section>
    <div className="grid"><section><h2>Global aggregate</h2><p>All LEFT rows, before the label filter. Count and sum remain exact strings.</p><Status value={global.status}/><Json value={global.rows}/></section><section><h2>Grouped + HAVING</h2><p>Group by the nested source enum; show groups whose joined sum is greater than zero.</p><Status value={grouped.status}/><Json value={grouped.rows}/></section></div>
    <section><h2>Viewport + whole-result helper</h2><p><code>useLiveQueryViewport</code> drives a two-row sink, while <code>useWholeResult</code> reads the same selected shape. Both are unfiltered.</p><div className="pills"><span>Viewport <Status value={view.status}/></span><span>Helper <Status value={helper.status}/></span><span>Total {count}</span><span>INNER matches {matched.totalRows} · {matched.status}</span></div><div className="grid"><div><h3>Sink rows 0–1</h3><Json value={windowRows}/></div><div><h3>Whole-result helper</h3><Json value={helper.rows}/></div></div></section>
    <section><h2>Freshness and dependencies</h2><p>Query status describes query freshness. Source acknowledgements and connection status do not replace it.</p><div className="pills"><span>Runtime {health.runtime ?? 'waiting'}</span><span>Serving ready {health.ready === undefined ? 'unknown' : String(health.ready)}</span><span>Sample {health.sampledAt ? new Date(health.sampledAt).toLocaleTimeString() : 'waiting'}</span></div>{health.error && <p role="alert">{health.error}</p>}
      <ul className="dependencies">{diagnostics.snapshot?.dependencies.map(dependency => <li key={dependency.id}><strong>{dependency.role}</strong> <Status value={dependency.state}/><small>{dependency.resource_id}{dependency.reason ? ` · ${dependency.reason}` : ''}</small></li>)}</ul>
      <details><summary>Per-source progress and dependency IDs</summary><Json value={{left: leftHealth, right: rightHealth}}/></details>
    </section>
    <footer>Local developer example · selected-field patches and WebSocket compression are off by default.</footer>
  </main>;
}

/** A typed entry point for embedding this example. Generated schema fingerprints must agree. */
export async function start(url: string, token: string, catalog: BrowserCatalog, fieldPatches = false) {
  await verifyCatalog(catalog);
  for (const topic of ['shit', 'nested_positions'] as const) if (catalog[topic]?.fingerprint !== demoCatalog[topic].fingerprint) throw new Error(`Demo schema mismatch: ${topic}`);
  dispose();
  const element = document.getElementById('root');
  if (!element) throw new Error('Demo mount element is missing');
  const activeProvider = new BrowserProductProvider({mode: 'remote', url, token, catalog: demoCatalog, subscriptions: 32, fieldPatches});
  provider = activeProvider; root = createRoot(element);
  root.render(<ProductProvider provider={activeProvider}><Demo activeProvider={activeProvider}/></ProductProvider>);
}
export function dispose() {root?.unmount(); provider?.dispose(); root = undefined; provider = undefined;}
function object(value: unknown): value is Record<string, unknown> {return value !== null && typeof value === 'object' && !Array.isArray(value);}
async function bootstrap() {
  const response = await fetch('/local-config.json', {cache: 'no-store'});
  if (!response.ok) throw new Error(`Local configuration unavailable (${response.status})`);
  const value: unknown = await response.json();
  if (!object(value) || typeof value.url !== 'string' || typeof value.token !== 'string' || !object(value.catalog)) throw new Error('Invalid local configuration');
  const endpoint = new URL(value.url);
  if (!['ws:', 'wss:'].includes(endpoint.protocol) || endpoint.hostname !== location.hostname) throw new Error('Expected a same-host query endpoint');
  for (const topic of ['shit', 'nested_positions'] as const) {
    const entry = value.catalog[topic];
    if (!object(entry) || entry.fingerprint !== demoCatalog[topic].fingerprint) throw new Error(`Local schema mismatch: ${topic}`);
    validateSchema(entry.schema);
    if (await schemaFingerprint(entry.schema) !== entry.fingerprint) throw new Error(`Invalid schema fingerprint: ${topic}`);
  }
  await start(value.url, value.token, demoCatalog);
}
Object.assign(window, {joinDemo: {start, observe: () => ({...observed, diagnostics: provider?.connectionDiagnostics, errors: provider?.consumerErrors}), dispose}});
// ?manual preserves an explicit start entry point for the bounded smoke harness.
if (!new URLSearchParams(location.search).has('manual')) void bootstrap().catch(error => {
  const element = document.getElementById('root');
  if (element) {const title = document.createElement('h1'); title.textContent = 'The local example could not start'; const detail = document.createElement('p'); detail.textContent = message(error); element.replaceChildren(title, detail);}
});
