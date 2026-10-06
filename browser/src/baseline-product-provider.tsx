import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useId,
  useState,
  type PropsWithChildren,
} from "react";

export type ProductAcquisitionIdentity = number;

export type ProductResult = {
  /** Transport receipt metadata, not React commit/paint; integers stay exact strings. */
  remote?: { sourceSequence: string; incarnation: string; connection: string; acquisition: number; requestId?: number; receivedNs: number; encodedBytes: number };
  keys?: string[];
  subscription: string;
  query_generation: number;
  sequence: number;
  start_rank: number;
  version: number;
  total_rows: number;
  rows: Array<Partial<ProductPayload>>;
};

export type ProductPayload = {
    id: string;
    category: string;
    label: { state: "missing" | "null" } | { state: "value"; value: string };
    quantity: string;
    amount: { coefficient: string; scale: number };
  };

export type ProductQuery = {
  projection?: readonly ProductField[];
  where_expr: unknown;
  direction: "ascending" | "descending";
  offset: number;
  limit: number;
};

type Listener = ((result: ProductResult) => void) & { onError?: (error: Error) => void };
export type ProductCoreStats = {
  upsert_predicate_checks: number;
  delete_predicate_checks: number;
  query_seed_rows_scanned: number;
  final_close_rows_scanned: number;
  differential_input_insertions: number;
  differential_input_retractions: number;
  differential_output_updates_observed: number;
  consolidation_input_records: number;
  consolidated_deltas_emitted: number;
  shape_id_lookups: number;
  ranked_index_insertions: number;
  ranked_index_retractions: number;
  result_calls: number;
  result_rows_extracted: number;
  active_subscriptions: number;
  active_query_shapes: number;
  retained_rows: number;
  worker_results_built: number;
  worker_rows_serialized: number;
  worker_messages_published: number;
  worker_unaffected_subscriptions_skipped: number;
  worker_no_result_commands: number;
  directed_index_records_traversed: number;
  directed_index_records_cloned: number;
  directed_index_records_transferred: number;
  directed_indexes_constructed: number;
  wasm_result_rows_encoded: number;
  worker_ack_count: number;
  worker_result_message_count: number;
  worker_message_count: number;
  worker_ack_row_occurrences: number;
  worker_result_row_occurrences: number;
  worker_control_row_occurrences: number;
  worker_control_message_count: number;
  worker_results_coalesced: number;
};
type ApplyResponse = { type: "ack"; id: number; results: Record<string, ProductResult>; acquisitions: Record<string, number>; stats: ProductCoreStats; traceparent: string };
type WorkerMessage =
  | { type: "ready"; wasmSha256?: string; serverIncarnation?: string }
  | { type: "live"; results: Record<string, ProductResult>; acquisitions: Record<string, number> }
  | { type: "fatal"; error: string }
  | ApplyResponse
  | { type: "request_error"; id: number; error: string; currentAcquisition?: number; traceparent: string };

class CommandRejection extends Error {
  constructor(message: string, readonly currentAcquisition: number | undefined) { super(message); }
}

export type ProviderOptions = { mode: "local" } | {
  mode: "remote"; url: string; token: string;
  /** Must fit the server's advertised capability. Default preserves the remote demo cap. */
  subscriptions?: number;
};

export class BrowserProductProvider {
  private readonly worker: Worker;
  private readonly listeners = new Map<string, { acquisition: ProductAcquisitionIdentity; listener: Listener; release: () => void; isActive: () => boolean }>();
  private readonly acquisitions = new Map<string, ProductAcquisitionIdentity>();
  private readonly pending = new Map<number, { resolve: (results: Record<string, ProductResult>) => void; reject: (error: Error) => void; traceparent: string }>();
  private readonly freshness = new Map<string, ProductResult>();
  // One latest completed candidate per registered subscription, never a result history.
  // A pending desired acquisition can suppress delivery without destroying rollback data.
  private readonly completed = new Map<string, { acquisition: ProductAcquisitionIdentity; result: ProductResult }>();
  private reporting = false;
  private submitted = 0;
  private readonly subscriptionLimit: number;
  private readonly commandLimit: number;
  private readonly commandWindow: number;
  private readonly dispatchQueue: Array<{ send: () => void; reject: (error: Error) => void }> = [];
  private draining = false;
  /** Bounded counters, useful for admission and cleanup diagnostics. */
  get admission() { return { subscriptions: this.listeners.size, outstanding: this.submitted,
    inFlight: this.pending.size, queued: this.dispatchQueue.length,
    subscriptionLimit: this.subscriptionLimit, commandLimit: this.commandLimit, commandWindow: this.commandWindow }; }
  private drain(): void {
    if (this.draining || this.terminalCause) return;
    this.draining = true;
    try { while (!this.terminalCause && this.pending.size < this.commandWindow && this.dispatchQueue.length) this.dispatchQueue.shift()!.send(); }
    finally { this.draining = false; }
  }
  private nextRequestId = 1;
  private nextAcquisition = 1;
  private terminalCause?: Error;
  lastWorkerTraceparent?: string;
  lastWorkerWasmSha256?: string;
  lastWorkerStats?: ProductCoreStats;
  /** Observable, non-recursive fallback, including exceptions thrown by the reporter itself. */
  readonly consumerErrors: Array<{ subscription: string; error: Error }> = [];
  onConsumerError?: (error: Error, subscription: string) => void;
  private lifecycle: "initializing" | "ready" | "failed" | "disposed" = "initializing";
  private readyResolve!: () => void;
  private readyReject!: (error: Error) => void;
  readonly ready: Promise<void>;

  constructor(options: ProviderOptions = { mode: "local" }) {
    const subscriptions = options.mode === "remote" ? options.subscriptions ?? 16 : Infinity;
    if (options.mode === "remote" && (!Number.isInteger(subscriptions) || subscriptions < 1 || subscriptions > 128)) throw new Error("remote subscription limit must be 1..128");
    this.subscriptionLimit = subscriptions;
    // Reserve bounded room for mount, StrictMode cleanup/remount, and navigation.
    this.commandLimit = options.mode === "remote" ? 4 * subscriptions + 32 : Infinity;
    this.commandWindow = options.mode === "remote" ? 4 : Infinity;
    this.ready = new Promise<void>((resolve, reject) => { this.readyResolve = resolve; this.readyReject = reject; });
    // Initialization can fail even when no caller has requested readiness yet.
    void this.ready.catch(() => undefined);
    this.worker = options.mode === "remote"
      ? new Worker(new URL("./product.remote.worker.ts", import.meta.url), { type: "module" })
      : new Worker(new URL("./product.worker.ts", import.meta.url), { type: "module" });
    this.worker.onmessage = (event: MessageEvent<WorkerMessage>) => this.receive(event.data);
    this.worker.onerror = (event) => this.fail(new Error(event.message || "ProductCore Worker failed"));
    this.worker.onmessageerror = () => this.fail(new Error("ProductCore Worker message could not be decoded"));
    if (options.mode === "remote") this.worker.postMessage({ type: "configure", options });
  }

  private receive(message: WorkerMessage): void {
    if (this.terminalCause) return;
    if (message.type === "ready") {
      if (this.lifecycle === "initializing") { this.lastWorkerWasmSha256 = message.wasmSha256; this.lifecycle = "ready"; this.readyResolve(); }
      return;
    }
    if (message.type === "fatal") { this.fail(new Error(message.error)); return; }
    if (message.type === "live") { this.publish(message.results, message.acquisitions); return; }
    // Unknown/obsolete variants cannot mutate freshness or consumer state.
    if (message.type !== "ack" && message.type !== "request_error") return;
    const pending = this.pending.get(message.id);
    if (!pending) return;
    this.pending.delete(message.id);
    this.lastWorkerTraceparent = message.traceparent;
    if (message.traceparent !== pending.traceparent) {
      const error = new Error("W3C traceparent changed across Worker boundary");
      pending.reject(error); this.fail(error); return;
    }
    if (message.type === "request_error") { pending.reject(new CommandRejection(message.error, message.currentAcquisition)); this.drain(); return; }
    this.lastWorkerStats = message.stats;
    // Settlement is independent of user callbacks; the same objects are reused locally.
    pending.resolve(message.results);
    this.publish(message.results, message.acquisitions);
    this.drain();
  }

  private publish(results: Record<string, ProductResult>, acquisitions: Record<string, number>): void {
    for (const [subscription, next] of Object.entries(results)) {
      if (this.terminalCause) break; // a callback can reenter dispose/fail
      const acquisition = acquisitions[subscription];
      const entry = this.listeners.get(subscription);
      if (!entry || !this.acquisitions.has(subscription) || next.subscription !== subscription) continue;
      const candidate = this.completed.get(subscription);
      if (!candidate || acquisition > candidate.acquisition ||
        (acquisition === candidate.acquisition && isNewerResult(next, candidate.result))) {
        this.completed.set(subscription, { acquisition, result: next });
      }
      this.deliver(subscription, acquisition, next);
    }
  }

  /** @internal Capture the invocation's acquisition, not just the mutable registration. */
  deliveryGuard(subscription: string, listener: Listener): () => boolean {
    const entry = this.listeners.get(subscription);
    const acquisition = entry?.acquisition;
    return () => !!entry && this.listeners.get(subscription) === entry && entry.acquisition === acquisition && this.ownsDelivery(subscription, listener);
  }
  private ownsDelivery(subscription: string, listener: Listener): boolean {
    const entry = this.listeners.get(subscription);
    return !this.terminalCause && entry?.listener === listener && entry.isActive() &&
      this.acquisitions.get(subscription) === entry.acquisition;
  }
  private deliver(subscription: string, acquisition: number, next: ProductResult): void {
    const entry = this.listeners.get(subscription);
    if (!entry || entry.acquisition !== acquisition || !this.ownsDelivery(subscription, entry.listener)) return;
    const prior = this.freshness.get(subscription);
    if (prior && !isNewerResult(next, prior)) return;
    this.freshness.set(subscription, next);
    const stillOwned = this.deliveryGuard(subscription, entry.listener);
    try { entry.listener(next); }
    catch (error) {
      if (stillOwned()) this.notifyError(subscription, entry.listener, normalizeError(error), stillOwned);
      else this.report(subscription, normalizeError(error));
    }
  }

  private report(subscription: string, error: Error): void {
    this.consumerErrors.push({ subscription, error });
    if (this.reporting) return;
    this.reporting = true;
    try { this.onConsumerError?.(error, subscription); }
    catch (reportError) { this.consumerErrors.push({ subscription, error: normalizeError(reportError) }); }
    finally { this.reporting = false; }
  }
  private notifyError(subscription: string, listener: Listener, error: Error, stillOwned: () => boolean = () => true): void {
    this.report(subscription, error);
    if (!stillOwned()) return;
    try { listener.onError?.(error); }
    catch (callbackError) { this.report(subscription, normalizeError(callbackError)); }
  }
  private terminate(error: Error, state: "failed" | "disposed"): void {
    if (this.terminalCause) { if(state === "disposed") this.lifecycle = state; return; }
    this.terminalCause = error;
    this.lifecycle = state;
    const listeners = [...this.listeners.entries()];
    this.listeners.clear(); this.acquisitions.clear(); this.freshness.clear(); this.completed.clear();
    const pending = [...this.pending.values(), ...this.dispatchQueue]; this.pending.clear(); this.dispatchQueue.length = 0;
    this.readyReject(error);
    for (const request of pending) request.reject(error);
    this.worker.terminate();
    // All delivery has been invalidated before any reentrant user callback.
    for (const [subscription, entry] of listeners) this.notifyError(subscription, entry.listener, error, entry.isActive);
  }
  private fail(error: Error): void { this.terminate(error, "failed"); }

  apply(command: unknown, traceparent = newTraceparent()): Promise<Record<string, ProductResult>> {
    return this.submit(command, traceparent);
  }
  private async submit(command: unknown, traceparent: string, ownedAcquisition?: ProductAcquisitionIdentity): Promise<Record<string, ProductResult>> {
    // Registration release owns a reserved control slot. Ordinary admission can
    // fail without preventing cleanup or terminating unrelated healthy listeners.
    const cleanup = ownedAcquisition !== undefined && typeof command === "object" && command !== null &&
      (command as { command?: string }).command === "close";
    const capacity = this.commandLimit - (!cleanup && Number.isFinite(this.subscriptionLimit) ? this.subscriptionLimit : 0);
    if (this.submitted >= capacity) throw new Error("commands in flight budget exceeded");
    this.submitted += 1;
    try { return await this.submitReserved(command, traceparent, ownedAcquisition); }
    finally { this.submitted -= 1; }
  }
  private async submitReserved(command: unknown, traceparent: string, ownedAcquisition?: ProductAcquisitionIdentity): Promise<Record<string, ProductResult>> {
    if (this.terminalCause) throw this.terminalCause;
    // This executes before the first await: clone errors allocate no request record.
    const snapshot = structuredClone(command);
    const cmd = snapshot as { command?: string; subscription?: string };
    const subscription = cmd?.subscription;
    const replacing = cmd?.command === "open" || cmd?.command === "change_query";
    const previous = typeof subscription === "string" ? this.acquisitions.get(subscription) : undefined;
    const acquisition = ownedAcquisition ?? (replacing ? this.nextAcquisition++ : previous);
    if (replacing && typeof subscription === "string") {
      this.acquisitions.set(subscription, acquisition!);
      const entry = this.listeners.get(subscription);
      if (entry && ownedAcquisition === undefined) entry.acquisition = acquisition!;
    }
    const rollback = (error: Error) => {
      // Resolve ownership at the response/send-failure boundary, before another
      // envelope or callback can observe it. Promise catch timing is not a transaction.
      if (!this.terminalCause && replacing && typeof subscription === "string" && this.acquisitions.get(subscription) === acquisition) {
        const restored = error instanceof CommandRejection ? error.currentAcquisition : previous;
        if (restored !== undefined) this.acquisitions.set(subscription, restored);
        else this.acquisitions.delete(subscription);
        const entry = this.listeners.get(subscription);
        if (entry && ownedAcquisition === undefined && entry.acquisition === acquisition && restored !== undefined) entry.acquisition = restored;
        const candidate = this.completed.get(subscription);
        if (candidate && candidate.acquisition === restored) this.deliver(subscription, restored, candidate.result);
        if (restored === undefined) this.completed.delete(subscription);
      }
    };
    try { await this.ready; }
    catch (error) { const cause = normalizeError(error); rollback(cause); throw cause; }
    if (this.terminalCause) throw this.terminalCause;
    const id = this.nextRequestId++;
    return new Promise<Record<string, ProductResult>>((resolve, reject) => {
      const rejectOwned = (error: Error) => { rollback(error); reject(error); };
      const resolveOwned = (results: Record<string, ProductResult>) => {
        // Direct close is transactional. Until its ACK, the still-live acquisition
        // remains deliverable. Release cancels immediately through its own path.
        if (cmd?.command === "close" && typeof subscription === "string" && this.acquisitions.get(subscription) === acquisition) {
          this.acquisitions.delete(subscription); this.freshness.delete(subscription); this.completed.delete(subscription);
        }
        resolve(results);
      };
      this.dispatchQueue.push({ reject: rejectOwned, send: () => {
        this.pending.set(id, { resolve: resolveOwned, reject: rejectOwned, traceparent });
        try { this.worker.postMessage({ type: "apply", id, command: snapshot, acquisition, previousAcquisition: previous, traceparent }); }
        catch (error) { this.pending.delete(id); rejectOwned(normalizeError(error)); }
      }});
      this.drain();
    });
  }

  async open(subscription: string, query: ProductQuery): Promise<ProductResult> {
    const results = await this.apply({ command: "open", subscription, query });
    if (!Object.hasOwn(results, subscription)) throw new Error(`missing snapshot for ${subscription}`);
    return results[subscription];
  }

  watch(subscription: string, query: ProductQuery, listener: Listener): () => void {
    if (!this.listeners.has(subscription) && this.listeners.size >= this.subscriptionLimit) throw new Error("subscription budget exceeded");
    if (this.terminalCause) throw this.terminalCause;
    if (this.submitted >= this.commandLimit - (Number.isFinite(this.subscriptionLimit) ? this.subscriptionLimit : 0)) throw new Error("watch command budget exceeded");
    // Clone failure must not release an existing valid registration.
    const querySnapshot = structuredClone(query);
    // Each registration owns an acquisition; replacement releases only its predecessor.
    this.listeners.get(subscription)?.release();
    const acquisition = this.nextAcquisition++;
    let active = true;
    const release = () => {
      if (!active) return;
      active = false;
      if (this.listeners.get(subscription) !== registration) return;
      const owned = registration.acquisition;
      this.listeners.delete(subscription);
      if (this.acquisitions.get(subscription) === owned) {
        this.acquisitions.delete(subscription); this.freshness.delete(subscription);
      }
      this.completed.delete(subscription);
      // Cancellation only stops delivery. An already applied mutation is not rolled back.
      const closeCancelled = async () => {
        try { await this.submit({ command: "close", subscription }, newTraceparent(), owned); }
        catch (error) {
          // A cancelled speculative replacement may never have reached native state.
          // Retry once against the explicitly confirmed predecessor, only while no
          // local successor owns this subscription. Worker identity checks still apply.
          if (!this.terminalCause && error instanceof CommandRejection && error.currentAcquisition !== undefined &&
            error.currentAcquisition < owned && !this.acquisitions.has(subscription)) {
            await this.submit({ command: "close", subscription }, newTraceparent(), error.currentAcquisition);
          } else throw error;
        }
      };
      void closeCancelled().catch((error: unknown) => {
        if (this.terminalCause) return;
        // A confirmed missing or newer native acquisition cannot leak the released one.
        if (error instanceof CommandRejection && (error.currentAcquisition === undefined || error.currentAcquisition > owned)) return;
        const cause = new Error(`release cleanup failed; provider terminated: ${normalizeError(error).message}`);
        this.fail(cause); this.report(subscription, cause);
      });
    };
    const registration = { acquisition, listener, release, isActive: () => active };
    this.listeners.set(subscription, registration);
    void this.submit({ command: "open", subscription, query: querySnapshot }, newTraceparent(), acquisition).catch((error: unknown) => {
      if (active && !this.terminalCause && this.listeners.get(subscription)?.acquisition === acquisition) this.notifyError(subscription, listener, normalizeError(error), () => active && this.listeners.get(subscription) === registration);
      else if (active && this.terminalCause && this.listeners.get(subscription)?.acquisition === acquisition) {
        this.listeners.delete(subscription); this.notifyError(subscription, listener, this.terminalCause, () => active);
      }
    });
    return release;
  }

  dispose(): void { this.terminate(this.terminalCause ?? new Error(Number.isFinite(this.subscriptionLimit) ? "provider is disposed; pending completion uncertain" : "provider is disposed"), "disposed"); }
  close(): void { this.dispose(); }
}
function normalizeError(error: unknown): Error { return error instanceof Error ? error : new Error(String(error)); }

function newTraceparent(): string {
  const randomHex = (length: number) => Array.from(crypto.getRandomValues(new Uint8Array(length)), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `00-${randomHex(16)}-${randomHex(8)}-01`;
}

function isNewerResult(next: ProductResult, prior: ProductResult): boolean {
  return !(next.query_generation < prior.query_generation || next.version < prior.version ||
    (next.query_generation === prior.query_generation && next.sequence < prior.sequence) ||
    (next.query_generation === prior.query_generation && next.version === prior.version && next.sequence === prior.sequence));
}

const ProductContext = createContext<BrowserProductProvider | null>(null);

export function ProductProvider({
  provider,
  children,
}: PropsWithChildren<{ provider: BrowserProductProvider }>) {
  return <ProductContext.Provider value={provider}>{children}</ProductContext.Provider>;
}

export function useProductLiveQuery(subscription: string, query: ProductQuery) {
  return useProductQuery(subscription, query);
}

function useProductQuery(subscription: string, query: ProductQuery) {
  const provider = useContext(ProductContext);
  const queryKey = JSON.stringify(query);
  const stableQuery = useMemo(() => JSON.parse(queryKey) as ProductQuery, [queryKey]);
  // Render-local identity has no external effects. Abandoned renders cannot cancel work.
  const identity = useMemo(() => ({ provider, subscription, stableQuery }), [provider, subscription, stableQuery]);
  const [state, setState] = useState<{ identity: typeof identity; data?: ProductResult; error?: Error }>();
  useEffect(() => {
    if (!provider) throw new Error("ProductProvider is missing");
    let active = true;
    setState({ identity });
    const listener: Listener = (data) => { if (active) setState({ identity, data }); };
    listener.onError = (error) => { if (active) setState(previous => ({ identity, data: previous?.identity === identity ? previous.data : undefined, error })); };
    let stop = () => {};
    try { stop = provider.watch(subscription, stableQuery, listener); }
    catch (error) { listener.onError(normalizeError(error)); }
    return () => { active = false; stop(); };
  }, [identity]);
  const current = state?.identity === identity ? state : undefined;
  return { data: current?.data, error: current?.error, isLoading: !current?.data && !current?.error };
}

/** The product adapter mirrors the frozen React package's topic/query hook contract. */
export type ProductField = "id" | "category" | "label" | "quantity" | "amount";
export type ProductViewRow = ProductPayload;
export type ProductRawQuery = {
  readonly select: readonly [ProductField, ...ProductField[]];
  readonly where: readonly ({ readonly field: "category"; readonly type: "equals"; readonly filter: string })[];
  readonly orderBy: readonly [] | readonly [{ readonly field: "amount"; readonly direction: "asc" | "desc" }];
};
type SelectedRow<Query extends ProductRawQuery> = Pick<ProductViewRow, Query["select"][number]>;
export type ProductLiveQueryResult<Row> = {
  readonly rows: ReadonlyArray<Row>;
  readonly totalRows: number;
  readonly version: number;
  readonly status: "loading" | "ready" | "error";
  readonly message?: string;
};

export function toProductQuery(query: ProductRawQuery, offset = 0, limit = 0xffff_ffff): ProductQuery {
  if (!query || !Array.isArray(query.select) || query.select.length === 0 || query.select.some((field) => !["id", "category", "label", "quantity", "amount"].includes(field))) {
    throw new Error("ProductCore requires a non-empty selection of supported product fields");
  }
  if (!Array.isArray(query.where) || query.where.some((condition) => condition.field !== "category" || condition.type !== "equals" || typeof condition.filter !== "string")) {
    throw new Error("ProductCore currently supports category equality filters only");
  }
  if (!Array.isArray(query.orderBy) || query.orderBy.length > 1 || query.orderBy.some((order) => order.field !== "amount" || !["asc", "desc"].includes(order.direction))) {
    throw new Error("ProductCore accepts at most one exact amount sort");
  }
  const conditions = query.where.map((condition) => ({ op: "condition", args: { field: "category_equals", condition: condition.filter } }));
  const predicate = conditions.length === 0 ? { op: "true" } : conditions.length === 1 ? conditions[0] : { op: "and", args: conditions };
  const firstOrder = query.orderBy[0];
  return {
    projection: query.select,
    where_expr: predicate,
    direction: firstOrder?.direction === "desc" ? "descending" : "ascending",
    offset,
    limit,
  };
}

function project<Row extends ProductField>(row: Partial<ProductViewRow>, fields: readonly Row[]): Pick<ProductViewRow, Row> {
  const selected: Partial<ProductViewRow> = {};
  for (const field of fields) {
    if (!Object.hasOwn(row, field)) throw new Error("Missing selected product field: " + field);
    selected[field] = row[field] as never;
  }
  return selected as Pick<ProductViewRow, Row>;
}

export function useLiveQuery<const Query extends ProductRawQuery>(
  topic: "products",
  query: Query,
): ProductLiveQueryResult<SelectedRow<Query>> {
  const consumerId = useId();
  const productQuery = toProductQuery(query);
  const { data, error } = useProductQuery(`${topic}:consumer:${consumerId}`, productQuery);
  const incomplete = data !== undefined && data.total_rows !== data.rows.length;
  return {
    rows: data?.rows.map((row) => project(row, query.select)) ?? [],
    totalRows: data?.total_rows ?? 0,
    version: data?.version ?? 0,
    status: error || incomplete ? "error" : data ? "ready" : "loading",
    message: error?.message ?? (incomplete ? "ProductCore result limit did not contain the full result" : undefined),
  };
}

export type ProductViewportWindow = { readonly firstRow: number; readonly lastRow: number };
export type ProductViewportSink<Row> = {
  setRowCount(count: number, keepRenderedRows?: boolean): void;
  setRowData(rowsByAbsoluteIndex: Readonly<Record<number, Row>>, rowKeysByIndex: Readonly<Record<number, string>>): void;
};
export type ProductViewportGeneration = {
  setWindow(window: ProductViewportWindow): void;
  release(): void;
};

export function useLiveQueryViewport(topic: "products") {
  const provider = useContext(ProductContext);
  const hookId = useId();
  type Chrome = { totalRows: number; version: number; status: "loading" | "ready" | "error"; message?: string };
  const owner = useMemo(() => ({ provider, topic }), [provider, topic]);
  const loading: Chrome = { totalRows: 0, version: 0, status: "loading" };
  const [chromeState, setChromeState] = useState<{ owner: typeof owner; value: Chrome }>({ owner, value: loading });
  const setChrome = useMemo(() => (value: Chrome) => setChromeState({ owner, value }), [owner]);
  const chrome = chromeState.owner === owner ? chromeState.value : loading;
  const viewport = useMemo(() => {
    let generation = 0;
    let activeStop: (() => void) | undefined;
    return {
      release() { generation += 1; activeStop?.(); activeStop = undefined; },
      semanticKey(query: ProductRawQuery) { return JSON.stringify(query); },
      replace<const Query extends ProductRawQuery>(input: {
        readonly window: ProductViewportWindow;
        readonly query: Query;
        readonly sink: ProductViewportSink<SelectedRow<Query>>;
      }): ProductViewportGeneration {
        if (!provider) throw new Error("ProductProvider is missing");
        const querySnapshot = structuredClone(input.query);
        validateViewportWindow(input.window);
        const query = toProductQuery(querySnapshot, input.window.firstRow, input.window.lastRow - input.window.firstRow + 1);
        const current = ++generation;
        setChrome({ totalRows: 0, version: 0, status: "loading" });
        const previousStop = activeStop;
        activeStop = undefined;
        previousStop?.();
        const subscription = `viewport:${topic}:${hookId}:${current}`;
        const sendWindow = (window: ProductViewportWindow) => {
          if (!Number.isSafeInteger(window.firstRow) || !Number.isSafeInteger(window.lastRow) || window.firstRow < 0 || window.lastRow < window.firstRow) {
            throw new Error("invalid viewport window");
          }
          const ownsInvocation = provider.deliveryGuard(subscription, listener);
          void provider.apply({ command: "change_window", subscription, offset: window.firstRow, limit: window.lastRow - window.firstRow + 1 }).catch((error: unknown) => {
            if (generation === current && !released && ownsInvocation()) setChrome({ totalRows: 0, version: 0, status: "error", message: error instanceof Error ? error.message : String(error) });
          });
        };
        const listener: Listener = (result) => {
          const ownsInvocation = provider.deliveryGuard(subscription, listener);
          const valid = () => generation === current && !released && ownsInvocation();
          if (!valid()) return;
          const rows: Record<number, SelectedRow<Query>> = {};
          const keys: Record<number, string> = {};
          result.rows.forEach((row, index) => {
            const absoluteIndex = result.start_rank + index;
            rows[absoluteIndex] = project(row, querySnapshot.select);
            const key = result.keys?.[index] ?? row.id;
            if (key === undefined) throw new Error("Missing stable row key");
            keys[absoluteIndex] = key;
          });
          if (result.subscription !== subscription ||
            (result.start_rank > result.total_rows && result.rows.length !== 0) ||
            (result.start_rank <= result.total_rows && result.rows.length > result.total_rows - result.start_rank)) return;
          input.sink.setRowCount(result.total_rows);
          if (!valid()) return;
          input.sink.setRowData(rows, keys);
          if (!valid()) return;
          setChrome({ totalRows: result.total_rows, version: result.version, status: "ready" });
        };
        listener.onError = (error) => { if (generation === current) setChrome({ totalRows: 0, version: 0, status: "error", message: error.message }); };
        let released = false;
        let stop = () => {};
        try { stop = provider.watch(subscription, query, listener); }
        catch (error) { listener.onError(normalizeError(error)); }
        activeStop = stop;
        return {
          setWindow(window) { if (!released && generation === current) sendWindow(window); },
          release() {
            if (released) return;
            released = true;
            if (generation === current) {
              generation += 1;
              if (activeStop === stop) activeStop = undefined;
            }
            stop();
          },
        };
      },
    };
  }, [provider, topic, setChrome]);
  useEffect(() => () => viewport.release(), [viewport]);
  const completeRawSelect = ["id", "category", "label", "quantity", "amount"] as const;
  const useWholeResult = <const Query extends ProductRawQuery>(query: Query) => useLiveQuery(topic, query);
  return { viewport, completeRawSelect, useWholeResult, ...chrome };
}

function validateViewportWindow(window: ProductViewportWindow): void {
  if (!Number.isSafeInteger(window.firstRow) || !Number.isSafeInteger(window.lastRow) || window.firstRow < 0 || window.lastRow < window.firstRow || window.lastRow >= 0xffff_ffff) throw new Error("invalid viewport window");
}
