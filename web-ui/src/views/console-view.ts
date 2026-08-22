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
 *  (UI-SPEC §10); the server projection stays authoritative (§11). */
@customElement("zuaef-console")
export class ZuaefConsole extends LitElement {
  @property({ attribute: false }) private ui: UiState = initialUiState;

  @state() private runs: RunView[] = [];
  @state() private nextCursor: string | null = null;
  @state() private loadingMore = false;

  @state() private projection: RunProjection | null = null;
  @state() private projectionLoading = false;
  @state() private projectionError = "";

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

  private async reloadRuns(): Promise<void> {
    try {
      const page: RunListPage = await api.listRuns();
      this.runs = page.runs;
      this.nextCursor = page.next_cursor;
      // Default selection: newest run once, on first load.
      if (!this.ui.selectedRunId && this.runs.length > 0) {
        this.selectRun(this.runs[0].run_id);
      } else if (this.ui.selectedRunId) {
        void this.reloadProjection(this.ui.selectedRunId);
      }
    } catch (error) {
      this.projectionError = `Failed to load runs: ${messageOf(error)}`;
    }
  }

  private async loadMore(cursor: string): Promise<void> {
    this.loadingMore = true;
    try {
      const page = await api.listRuns(cursor);
      const seen = new Set(this.runs.map((run) => run.run_id));
      this.runs = [...this.runs, ...page.runs.filter((run) => !seen.has(run.run_id))];
      this.nextCursor = page.next_cursor;
    } catch (error) {
      this.projectionError = `Failed to load more runs: ${messageOf(error)}`;
    } finally {
      this.loadingMore = false;
    }
  }

  private async reloadProjection(runId: string): Promise<void> {
    this.projectionLoading = !this.projection ||
      this.projection.run.run_id !== runId;
    if (this.projectionLoading) this.projectionError = "";
    try {
      this.projection = await api.getRun(runId);
      this.projectionError = "";
      document.title =
        `${this.projection.run.display_label} — ZUAEF Console`;
    } catch (error) {
      this.projectionError = `Failed to load run: ${messageOf(error)}`;
    } finally {
      this.projectionLoading = false;
    }
  }

  private patchUi(patch: Partial<UiState>) {
    this.ui = { ...this.ui, ...patch };
  }

  private selectRun(runId: string) {
    if (runId === this.ui.selectedRunId) return;
    this.patchUi({ selectedRunId: runId, selectedEventId: undefined });
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
          @event-selected=${(e: CustomEvent<{ rowId: string }>) =>
            this.patchUi({ selectedEventId: e.detail.rowId })}
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
    await this.reloadRuns();
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
