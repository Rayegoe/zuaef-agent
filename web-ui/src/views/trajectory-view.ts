import { LitElement, css, html, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { RunProjection, TimelineRow } from "../api";
import {
  formatDuration,
  formatTime,
  groupContiguousToolRows,
  groupContains,
  isToolRowGroup,
  type LedgerEntry,
} from "../state";
import "../components/event-row";
import "../components/overview-strip";
import "../components/status-badge";

/** Center pane: the trajectory ledger for the selected run.
 *  Contiguous same-name tool rows collapse into one group header (default
 *  collapsed); expansion is transient component state, never persisted. */
@customElement("zuaef-trajectory-view")
export class ZuaefTrajectoryView extends LitElement {
  @property({ attribute: false }) projection: RunProjection | null = null;
  @property({ type: Boolean }) loading = false;
  @property() selectedEventId = "";
  @property() error = "";

  @state() private expandedGroups: string[] = [];
  private lastRunId: string | null = null;

  protected updated(changed: Map<string, unknown>) {
    super.updated(changed);
    if (changed.has("selectedEventId") || changed.has("projection")) {
      this.scrollToSelected();
    }
  }

  /** Minimap → ledger linkage (T008B): an external selection scrolls the
   *  row into view. block:"nearest" makes same-pane clicks a no-op. */
  private scrollToSelected() {
    const id = this.selectedEventId;
    if (!id) return;
    for (const el of this.renderRoot.querySelectorAll("zuaef-event-row")) {
      if ((el as { row?: TimelineRow }).row?.id === id) {
        el.scrollIntoView({ block: "nearest", behavior: "smooth" });
        return;
      }
    }
  }

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
    }
    header {
      display: flex;
      align-items: baseline;
      gap: var(--z-space-3);
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
      min-width: 0;
    }
    h2 {
      margin: 0;
      font-size: 13px;
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .model {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
    }
    .diag {
      padding: var(--z-space-1) var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-warning);
      border-bottom: 1px solid var(--z-border);
      overflow-wrap: anywhere;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      padding-top: var(--z-space-1);
    }
    .state {
      padding: var(--z-space-4) var(--z-space-3);
      color: var(--z-text-muted);
    }
    .error {
      color: var(--z-danger);
    }
    /* Group header shares the event-row ledger grid. */
    .group-header {
      display: grid;
      grid-template-columns:
        66px 44px 34px minmax(0, 1fr) 62px 110px 96px;
      gap: var(--z-space-3);
      align-items: baseline;
      width: 100%;
      padding: 2px var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 12px;
      text-align: left;
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--z-divider);
      color: inherit;
      white-space: nowrap;
    }
    .group-header:hover { background: var(--z-hover-tint); }
    .group-header:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .group-header .time { color: var(--z-text-subtle); }
    .group-header .kind {
      color: var(--z-text-subtle);
      letter-spacing: 0.04em;
      font-size: 11px;
    }
    .group-header .summary {
      overflow: hidden;
      text-overflow: ellipsis;
      padding-left: 14px;
      color: var(--z-text-muted);
    }
    .group-header .caret {
      display: inline-block;
      width: 1.1em;
      color: var(--z-text-subtle);
    }
    .group-header .dur {
      color: var(--z-text-muted);
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .group-header .status {
      text-align: right;
      color: var(--z-text-subtle);
      font-size: 11px;
    }
  `;

  private toggleGroup(groupId: string) {
    this.expandedGroups = this.expandedGroups.includes(groupId)
      ? this.expandedGroups.filter((id) => id !== groupId)
      : [...this.expandedGroups, groupId];
  }

  private isOpen(group: {
    groupId: string;
    rows: TimelineRow[];
  }): boolean {
    return (
      this.expandedGroups.includes(group.groupId) ||
      groupContains(group, this.selectedEventId)
    );
  }

  private groupTotal(group: { rows: TimelineRow[] }): string {
    const total = group.rows.reduce(
      (sum, row) => (row.duration_ms !== null ? sum + row.duration_ms : sum),
      0,
    );
    return total > 0 ? formatDuration(total) : "";
  }

  private renderEntry(entry: LedgerEntry): TemplateResult {
    if (!isToolRowGroup(entry)) {
      return html`<zuaef-event-row
        role="option"
        .row=${entry}
        ?selected=${entry.id === this.selectedEventId}
        @event-selected=${(e: CustomEvent<{ rowId: string }>) =>
          this.dispatchEvent(
            new CustomEvent("event-selected", {
              detail: e.detail,
              bubbles: true,
              composed: true,
            }),
          )}
      ></zuaef-event-row>`;
    }
    const open = this.isOpen(entry);
    const first = entry.rows[0];
    const header = html`<button
      class="group-header"
      aria-expanded=${open ? "true" : "false"}
      title=${`${entry.toolName} ×${entry.rows.length} — click to ${open ? "collapse" : "expand"}`}
      @click=${() => this.toggleGroup(entry.groupId)}
    >
      <span class="time">${formatTime(first.started_at)}</span>
      <span class="kind">TOOL</span>
      <span class="step"></span>
      <span class="summary"
        ><span class="caret" aria-hidden="true">${open ? "▾" : "▸"}</span
        >${entry.toolName} ×${entry.rows.length}</span
      >
      <span class="dur">${this.groupTotal(entry)}</span>
      <span class="usage"></span>
      <span class="status">${entry.rows.length} calls</span>
    </button>`;
    if (!open) return header;
    return html`${header}
      ${entry.rows.map((row) => this.renderEntry(row))}`;
  }

  render() {
    const run = this.projection?.run;
    if (run && run.run_id !== this.lastRunId) {
      this.lastRunId = run.run_id;
      this.expandedGroups = [];
    }
    return html`
      <header>
        <h2>${run ? run.display_label : "Trajectory"}</h2>
        ${run
          ? html`<zuaef-status-badge .status=${run.status}></zuaef-status-badge>`
          : ""}
        ${run && run.model ? html`<span class="model">${run.model}</span>` : ""}
      </header>
      ${this.projection?.diagnostics?.length
        ? this.projection.diagnostics.map(
            (line) => html`<div class="diag">${line}</div>`,
          )
        : ""}
      ${this.projection && !this.error
        ? html`<zuaef-overview-strip
            .timeline=${this.projection.timeline}
            .selectedEventId=${this.selectedEventId}
            @event-selected=${(e: CustomEvent<{ rowId: string }>) =>
              this.dispatchEvent(
                new CustomEvent("event-selected", {
                  detail: e.detail,
                  bubbles: true,
                  composed: true,
                }),
              )}
          ></zuaef-overview-strip>`
        : ""}
      <div class="scroll">
        ${this.error
          ? html`<div class="state error">${this.error}</div>`
          : this.loading
            ? html`<div class="state">Loading trajectory…</div>`
            : !this.projection
              ? html`<div class="state">Select a run to inspect its trajectory.</div>`
              : this.projection.timeline.length === 0
                ? html`<div class="state">
                    No step events persisted for this run — only receipt-level facts exist.
                  </div>`
                : groupContiguousToolRows(this.projection.timeline).map(
                    (entry) => this.renderEntry(entry),
                  )}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-trajectory-view": ZuaefTrajectoryView;
  }
}
