import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { RunProjection, TimelineRow } from "../api";
import "../components/event-row";
import "../components/status-badge";

/** Center pane: the trajectory ledger for the selected run. */
@customElement("zuaef-trajectory-view")
export class ZuaefTrajectoryView extends LitElement {
  @property({ attribute: false }) projection: RunProjection | null = null;
  @property({ type: Boolean }) loading = false;
  @property() selectedEventId = "";
  @property() error = "";

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
  `;

  private select(event: CustomEvent<{ rowId: string }>) {
    this.dispatchEvent(
      new CustomEvent("event-selected", {
        detail: event.detail,
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    const run = this.projection?.run;
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
                : this.projection.timeline.map(
                    (row: TimelineRow) => html`
                      <zuaef-event-row
                        role="option"
                        .row=${row}
                        ?selected=${row.id === this.selectedEventId}
                        @event-selected=${(e: CustomEvent<{ rowId: string }>) =>
                          this.select(e)}
                      ></zuaef-event-row>
                    `,
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
