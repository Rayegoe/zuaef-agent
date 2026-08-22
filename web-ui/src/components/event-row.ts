import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { TimelineRow } from "../api";
import {
  formatDuration,
  formatTime,
  formatUsageCell,
  statusGlyph,
} from "../state";

const KIND_TAGS: Record<string, string> = {
  run: "RUN",
  model_request: "REQ",
  tool_call: "TOOL",
};

/** One dense ledger row — timestamp | kind | step | summary | dur | usage.
 *  Never a card (UI-SPEC §16). Visual hierarchy (v0.2 pass): rows are quiet
 *  by default; requests form the skeleton, tools are secondary, and only
 *  failed/unresolved/paused rows raise a high-salience signal. */
@customElement("zuaef-event-row")
export class ZuaefEventRow extends LitElement {
  @property({ attribute: false }) row!: TimelineRow;
  @property({ type: Boolean }) selected = false;

  static styles = css`
    button {
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
      white-space: nowrap;
      color: inherit;
    }
    button:hover { background: var(--z-hover-tint); }
    button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    button[aria-selected="true"] {
      background: var(--z-selected-surface);
      box-shadow: inset 2px 0 0 var(--z-accent);
    }
    /* Anomalies are the loudest element on the ledger. */
    button.state-failed { background: var(--z-danger-tint); }
    button.state-unresolved { background: var(--z-warning-tint); }
    button.state-paused { background: var(--z-warning-tint); }

    .time { color: var(--z-text-subtle); }
    .kind {
      color: var(--z-text-subtle);
      letter-spacing: 0.04em;
      font-size: 11px;
    }
    .step { color: var(--z-text-subtle); }
    .summary {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--z-text);
    }
    .summary .detail { color: var(--z-text-muted); }
    .dur, .usage {
      color: var(--z-text-muted);
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .status { text-align: right; color: var(--z-text-subtle); }
    .status.failed { color: var(--z-danger); }
    .status.paused, .status.limit_reached { color: var(--z-warning); }
    .status.incomplete, .status.started { color: var(--z-accent); }
    .status.unresolved, .status.unknown { color: var(--z-warning); }

    /* Secondary layer: tool rows are indented and muted inside their own
       summary cell so the shared ledger columns stay aligned. */
    button.tool .summary,
    button.tool .kind {
      padding-left: 14px;
      color: var(--z-text-muted);
    }
    /* Model requests carry the skeleton: slightly more breathing room. */
    button.request { margin-top: 4px; }
    button.run { margin-top: 2px; margin-bottom: 2px; }
  `;

  private select() {
    this.dispatchEvent(
      new CustomEvent("event-selected", {
        detail: { rowId: this.row.id },
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    const row = this.row;
    const isRun = row.kind === "run";
    const kindTag = KIND_TAGS[row.kind] ?? "EVENT";
    const weight =
      row.kind === "tool_call" ? "tool" : isRun ? "run" : "request";
    return html`
      <button
        role="option"
        aria-selected=${this.selected ? "true" : "false"}
        class=${[weight, row.status ? `state-${row.status}` : ""].join(" ")}
        title=${row.title}
        @click=${this.select}
      >
        <span class="time">${formatTime(row.started_at)}</span>
        <span class="kind">${isRun ? "" : kindTag}</span>
        <span class="step">${row.step_index !== null ? `#${row.step_index}` : ""}</span>
        <span class="summary"
          >${row.title}${row.detail
            ? html` <span class="detail">— ${row.detail}</span>`
            : ""}</span
        >
        <span class="dur">${formatDuration(row.duration_ms)}</span>
        <span class="usage">${formatUsageCell(row.usage)}</span>
        <span class="status ${row.status ?? ""}"
          >${row.status ? `${statusGlyph(row.status)} ${row.status}` : ""}</span
        >
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-event-row": ZuaefEventRow;
  }
}
