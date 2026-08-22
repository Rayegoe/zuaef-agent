import { LitElement, css, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { api, type RunListPage, type RunProjection, type RunView } from "../api";
import { initialUiState, type InspectorTab, type UiState } from "../state";
import "../components/artifact-bar";
import "../components/inspector";
import "../components/run-list";
import "./trajectory-view";

/** Console coordinator: owns the tiny UiState and all API calls.
 *  Components receive data via properties and emit UI intent via events
 *  (UI-SPEC §10); the server projection stays authoritative (§11).
 *  Tail-follow (T008C): while LIVE, a thin SSE run_changed stream triggers
 *  a debounced refetch of the same HTTP projection — the stream never
 *  carries timeline data. Selecting any event pauses live so inspection
 *  is never yanked around; the topbar control resumes (= jump to now). */
@customElement("zuaef-console")
export class ZuaefConsole extends LitElement {
  @property({ attribute: false }) private ui: UiState = initialUiState;

  @state() private runs: RunView[] = [];
  @state() private nextCursor: string | null = null;
  @state() private loadingMore = false;

  @state() private projection: RunProjection | null = null;
  @state() private projectionLoading = false;
  @state() private projectionError = "";

  @state() private live = true;
  /** SSE endpoint unreachable/errored — degrade to manual Refresh once. */
  @state() private liveAvailable = true;

  private es: EventSource | null = null;
  private esRunId: string | undefined = undefined;
  private invalidateTimer: ReturnType<typeof setTimeout> | null = null;
  private listRequestGeneration = 0;
  private projectionRequestGeneration = 0;

  static styles = css`
    :host {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      height: 100vh;
    }
    .topbar {
      display: flex;
      align-items: center;
      gap: var(--z-space-4);
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
      background: var(--z-surface);
    }
    .brand {
      font-weight: 700;
      letter-spacing: 0.12em;
      font-size: 13px;
    }
    .topbar .spacer { flex: 1; }
    .meta {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .refresh {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 2px var(--z-space-2);
      color: var(--z-text-muted);
      font-size: 12px;
      background: transparent;
    }
    .refresh:hover { color: var(--z-text); background: var(--z-surface-hover); }
    .live {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 2px var(--z-space-2);
      font-size: 12px;
      font-family: var(--z-font-mono);
      background: transparent;
      cursor: pointer;
    }
    .live[aria-pressed="true"] { color: var(--z-accent); }
    .live[aria-pressed="false"] { color: var(--z-text-muted); }
    .live:hover:not(:disabled) { color: var(--z-text); background: var(--z-surface-hover); }
    .live:disabled { opacity: 0.5; cursor: default; }
    .live:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: 1px;
    }
    .panes {
      display: grid;
      grid-template-columns: 264px minmax(0, 1fr) 380px;
      min-height: 0;
    }
    @media (max-width: 1100px) {
      .panes { grid-template-columns: 220px minmax(0, 1fr) 320px; }
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    void this.reloadRuns();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.closeStream();
    if (this.invalidateTimer !== null) clearTimeout(this.invalidateTimer);
  }

  protected willUpdate(changed: Map<string, unknown>) {
    super.willUpdate(changed);
    if (changed.has("ui") || changed.has("live") || changed.has("liveAvailable")) {
      const prevUi = changed.get("ui") as UiState | undefined;
      const runChanged =
        changed.has("ui") &&
        (!prevUi || prevUi.selectedRunId !== this.ui.selectedRunId);
      if (runChanged && this.ui.selectedRunId) this.live = true;
      this.syncStream();
    }
  }

  // ---- tail-follow (T008C) ----

  private closeStream() {
    this.es?.close();
    this.es = null;
    this.esRunId = undefined;
    if (this.invalidateTimer !== null) clearTimeout(this.invalidateTimer);
    this.invalidateTimer = null;
  }

  private syncStream() {
    const runId = this.live && this.liveAvailable ? this.ui.selectedRunId : undefined;
    if (this.es && this.esRunId === runId) return;
    this.closeStream();
    if (!runId) return;
    const stream = new EventSource(api.runEventsUrl(runId));
    this.es = stream;
    this.esRunId = runId;
    stream.addEventListener("run_changed", () => this.scheduleInvalidate(runId));
    stream.onerror = () => {
      // A closed old stream may report its error after a new selection has
      // already installed another stream; it must not disable that stream.
      if (this.es !== stream || this.esRunId !== runId) return;
      // Native reconnect would spam while the server is down; degrade to
      // manual Refresh instead and let the next selection retry.
      this.liveAvailable = false;
      this.live = false;
      this.closeStream();
    };
  }

  private scheduleInvalidate(runId: string | undefined = this.esRunId) {
    if (!runId) return;
    if (this.invalidateTimer !== null) clearTimeout(this.invalidateTimer);
    this.invalidateTimer = setTimeout(() => {
      this.invalidateTimer = null;
      if (
        !this.live ||
        !this.liveAvailable ||
        this.ui.selectedRunId !== runId ||
        this.esRunId !== runId
      ) {
        return;
      }
      void this.reloadProjection(runId);
      void this.reloadRuns();
    }, 150);
  }

  private setLive(on: boolean) {
    if (on && !this.liveAvailable) return;
    this.live = on;
    if (on && this.ui.selectedRunId) {
      // Resume === jump to now: refresh immediately, then keep following.
      void this.reloadProjection(this.ui.selectedRunId);
      void this.reloadRuns();
    }
  }

  private async reloadRuns(): Promise<void> {
    const requestGeneration = ++this.listRequestGeneration;
    this.loadingMore = false;
    try {
      const page: RunListPage = await api.listRuns();
      if (requestGeneration !== this.listRequestGeneration) return;
      this.runs = page.runs;
      this.nextCursor = page.next_cursor;
      // Default selection: newest run once, on first load.
      if (!this.ui.selectedRunId && this.runs.length > 0) {
        this.selectRun(this.runs[0].run_id);
      }
    } catch (error) {
      if (requestGeneration !== this.listRequestGeneration) return;
      this.projectionError = `Failed to load runs: ${messageOf(error)}`;
    }
  }

  private async loadMore(cursor: string): Promise<void> {
    const requestGeneration = ++this.listRequestGeneration;
    this.loadingMore = true;
    try {
      const page = await api.listRuns(cursor);
      if (requestGeneration !== this.listRequestGeneration) return;
      const seen = new Set(this.runs.map((run) => run.run_id));
      this.runs = [...this.runs, ...page.runs.filter((run) => !seen.has(run.run_id))];
      this.nextCursor = page.next_cursor;
    } catch (error) {
      if (requestGeneration !== this.listRequestGeneration) return;
      this.projectionError = `Failed to load more runs: ${messageOf(error)}`;
    } finally {
      if (requestGeneration === this.listRequestGeneration) {
        this.loadingMore = false;
      }
    }
  }

  private async reloadProjection(runId: string): Promise<void> {
    const requestGeneration = ++this.projectionRequestGeneration;
    const isCurrent = () =>
      requestGeneration === this.projectionRequestGeneration &&
      this.ui.selectedRunId === runId;
    this.projectionLoading = !this.projection ||
      this.projection.run.run_id !== runId;
    if (this.projectionLoading) this.projectionError = "";
    try {
      const projection = await api.getRun(runId);
      if (!isCurrent()) return;
      this.projection = projection;
      this.projectionError = "";
      document.title =
        `${this.projection.run.display_label} — ZUAEF Console`;
    } catch (error) {
      if (!isCurrent()) return;
      this.projectionError = `Failed to load run: ${messageOf(error)}`;
    } finally {
      if (isCurrent()) this.projectionLoading = false;
    }
  }

  private patchUi(patch: Partial<UiState>) {
    this.ui = { ...this.ui, ...patch };
  }

  private selectRun(runId: string) {
    // A deliberate selection is also an explicit retry after an SSE error.
    this.liveAvailable = true;
    this.live = true;
    if (runId === this.ui.selectedRunId) {
      this.syncStream();
      void this.reloadProjection(runId);
      return;
    }
    this.patchUi({ selectedRunId: runId, selectedEventId: undefined });
    this.syncStream();
    void this.reloadProjection(runId);
  }

  render() {
    const run = this.projection?.run ?? null;
    const meta = run
      ? [run.model ?? "model unknown", run.profile ?? "profile unknown"].join(" · ")
      : "";
    return html`
      <header class="topbar">
        <span class="brand">ZUAEF</span>
        <span class="meta">${meta}</span>
        <span class="spacer"></span>
        <button
          class="live"
          aria-pressed=${this.live ? "true" : "false"}
          ?disabled=${!this.liveAvailable}
          title=${this.liveAvailable
            ? this.live
              ? "Live: refetches on server invalidation. Click to pause."
              : "Paused so you can inspect history. Click to resume (jump to now)."
            : "Live updates unavailable — use Refresh."}
          @click=${() => this.setLive(!this.live)}
        >
          ${this.live
            ? "● LIVE"
            : this.liveAvailable
              ? "○ paused · jump to now"
              : "○ live off"}
        </button>
        <button class="refresh" @click=${() => void this.refresh()}>
          Refresh
        </button>
      </header>
      <div class="panes">
        <zuaef-run-list
          .runs=${this.runs}
          .selectedRunId=${this.ui.selectedRunId ?? ""}
          .nextCursor=${this.nextCursor}
          .loadingMore=${this.loadingMore}
          .filter=${this.ui.runFilter ?? ""}
          @run-selected=${(e: CustomEvent<{ runId: string }>) =>
            this.selectRun(e.detail.runId)}
          @run-filter=${(e: CustomEvent<{ value: string }>) =>
            this.patchUi({ runFilter: e.detail.value })}
          @load-more=${() => {
            if (this.nextCursor) void this.loadMore(this.nextCursor);
          }}
        ></zuaef-run-list>

        <zuaef-trajectory-view
          .projection=${this.projection}
          .loading=${this.projectionLoading}
          .selectedEventId=${this.ui.selectedEventId ?? ""}
          .error=${this.projectionError}
          @event-selected=${(e: CustomEvent<{ rowId: string }>) => {
            this.patchUi({ selectedEventId: e.detail.rowId });
            // Inspecting history pauses tail-follow (the view must not
            // jump while the operator reads); resume is explicit.
            this.setLive(false);
          }}
        ></zuaef-trajectory-view>

        <zuaef-inspector
          .projection=${this.projection}
          .selectedEventId=${this.ui.selectedEventId ?? ""}
          .inspectorTab=${this.ui.inspectorTab}
          @tab-selected=${(e: CustomEvent<{ tab: InspectorTab }>) =>
            this.patchUi({ inspectorTab: e.detail.tab })}
        ></zuaef-inspector>
      </div>
      <zuaef-artifact-bar
        .artifacts=${this.projection?.artifacts ?? []}
        .pause=${this.projection?.pause ?? null}
      ></zuaef-artifact-bar>
    `;
  }

  private async refresh(): Promise<void> {
    // Refresh is the explicit recovery action after a failed live stream.
    this.liveAvailable = true;
    this.live = true;
    this.syncStream();
    const selectedRunId = this.ui.selectedRunId;
    await this.reloadRuns();
    if (selectedRunId && this.ui.selectedRunId === selectedRunId) {
      await this.reloadProjection(selectedRunId);
    }
  }
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-console": ZuaefConsole;
  }
}
