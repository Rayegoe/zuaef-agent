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
 *  Never a card (UI-SPEC §16). */
@customElement("zuaef-event-row")
export class ZuaefEventRow extends LitElement {
  @property({ attribute: false }) row!: TimelineRow;
  @property({ type: Boolean }) selected = false;

  static styles = css`
    button {
      display: grid;
      grid-template-columns:
        66px 44px 34px minmax(0, 1fr) 62px 110px 92px;
      gap: var(--z-space-3);
      align-items: baseline;
      width: 100%;
      padding: 2px var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 12px;
      text-align: left;
      border-left: 2px solid transparent;
      white-space: nowrap;
    }
    button:hover { background: var(--z-surface-hover); }
    button[aria-selected="true"] {
      background: var(--z-surface-hover);
      border-left-color: var(--z-accent);
    }
    .time { color: var(--z-text-subtle); }
    .kind {
      color: var(--z-text-muted);
      letter-spacing: 0.04em;
      font-size: 11px;
    }
    .step { color: var(--z-text-subtle); }
    .summary {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--z-text);
    }
    .summary .detail {
      color: var(--z-text-muted);
    }
    .dur, .usage { color: var(--z-text-muted); text-align: right; }
    .status { text-align: right; }
    .status.completed { color: var(--z-success); }
    .status.failed { color: var(--z-danger); }
    .status.paused, .status.limit_reached { color: var(--z-warning); }
    .status.incomplete, .status.started { color: var(--z-accent); }
    .status.unresolved, .status.unknown { color: var(--z-text-muted); }
    /* Row-level emphasis for non-happy states: border + glyph, not just hue. */
    button.state-failed { background: rgba(212, 104, 95, 0.07); }
    button.state-unresolved { background: rgba(211, 160, 79, 0.06); }
    button.state-paused { background: rgba(211, 160, 79, 0.09); }
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
    const summary = html`<span class="summary"
      >${row.title}${row.detail
        ? html` <span class="detail">— ${row.detail}</span>`
        : ""}</span
    >`;
    return html`
      <button
        role="option"
        aria-selected=${this.selected ? "true" : "false"}
        class=${row.status ? `state-${row.status}` : ""}
        title=${row.title}
        @click=${this.select}
      >
        <span class="time">${formatTime(row.started_at)}</span>
        <span class="kind">${isRun ? "" : kindTag}</span>
        <span class="step">${row.step_index !== null ? `#${row.step_index}` : ""}</span>
        ${summary}
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
