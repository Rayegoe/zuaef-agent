import { LitElement, css, html, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { TimelineRow } from "../api";
import {
  buildOverview,
  formatDuration,
  formatTime,
  formatTokens,
  statusGlyph,
  type OverviewBar,
  type OverviewMetric,
} from "../state";

const METRICS: Array<{ id: OverviewMetric; label: string }> = [
  { id: "latency", label: "Latency" },
  { id: "input", label: "Input tokens" },
  { id: "output", label: "Output tokens" },
];

/** Live Request Overview (T008B): a time-proportional minimap above the
 *  trajectory ledger — one bar per model request, tool calls as baseline
 *  ticks. Plain positioned divs, no chart library. Clicking selects the
 *  ledger row; the selected ledger row highlights its bar in return.
 *  A running request is drawn as an outlined hatched bar whose height is
 *  live elapsed time and whose label says "elapsed", never "duration". */
@customElement("zuaef-overview-strip")
export class ZuaefOverviewStrip extends LitElement {
  @property({ attribute: false }) timeline: TimelineRow[] = [];
  @property() selectedEventId = "";

  @state() private metric: OverviewMetric = "latency";
  @state() private now = Date.now();

  private ticker: ReturnType<typeof setInterval> | null = null;

  static styles = css`
    :host {
      display: block;
      border-bottom: 1px solid var(--z-border);
      padding: var(--z-space-2) var(--z-space-3) var(--z-space-1);
    }
    .head {
      display: flex;
      align-items: baseline;
      gap: var(--z-space-3);
      margin-bottom: var(--z-space-1);
    }
    .label {
      font-size: 10px;
      letter-spacing: 0.08em;
      color: var(--z-text-subtle);
    }
    .metric {
      padding: 0 var(--z-space-2);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
      background: transparent;
      border: none;
      border-bottom: 1px solid transparent;
      cursor: pointer;
    }
    .metric:hover { color: var(--z-text); }
    .metric[aria-pressed="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .metric:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .spacer { flex: 1; }
    .active-note {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-accent);
    }
    .plot {
      position: relative;
      height: 64px;
      border-bottom: 1px solid var(--z-border);
    }
    .bar {
      position: absolute;
      bottom: 0;
      width: 8px;
      min-height: 3px;
      transform: translateX(-50%);
      background: var(--z-text-subtle);
      border: none;
      padding: 0;
      cursor: pointer;
    }
    .bar:hover { background: var(--z-text-muted); }
    .bar:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: 1px;
    }
    .bar[aria-selected="true"] { background: var(--z-accent); }
    .bar.state-failed { background: var(--z-danger); }
    /* Running request: outlined hatch — visibly "not settled yet". */
    .bar.active {
      background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 2px,
        var(--z-accent) 2px,
        var(--z-accent) 3px
      );
      border: 1px solid var(--z-accent);
    }
    .tick {
      position: absolute;
      bottom: 0;
      width: 2px;
      height: 5px;
      transform: translateX(-50%);
      background: var(--z-text-subtle);
      opacity: 0.7;
    }
    .tick.selected { background: var(--z-accent); opacity: 1; }
    .tick.state-failed { background: var(--z-danger); }
    .nowline {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      background: var(--z-warning);
      opacity: 0.6;
    }
    .axis {
      display: flex;
      justify-content: space-between;
      font-family: var(--z-font-mono);
      font-size: 10px;
      color: var(--z-text-subtle);
      padding-top: 2px;
    }
    /* CSS-only tooltip: facts on hover/focus, no floating layer. */
    .tip {
      display: none;
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%);
      z-index: 1;
      white-space: nowrap;
      text-align: left;
      font-family: var(--z-font-mono);
      font-size: 11px;
      line-height: 1.5;
      color: var(--z-text);
      background: var(--z-surface);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: var(--z-space-1) var(--z-space-2);
      pointer-events: none;
    }
    .tip .muted { color: var(--z-text-muted); }
    .bar:hover .tip,
    .bar:focus-visible .tip { display: block; }
  `;

  updated(changed: Map<string, unknown>) {
    super.updated(changed);
    const hasActive = this.timeline.some((row) => row.status === "started");
    if (hasActive && this.ticker === null) {
      this.ticker = setInterval(() => {
        this.now = Date.now();
      }, 1000);
    } else if (!hasActive && this.ticker !== null) {
      clearInterval(this.ticker);
      this.ticker = null;
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.ticker !== null) clearInterval(this.ticker);
    this.ticker = null;
  }

  private select(rowId: string) {
    this.dispatchEvent(
      new CustomEvent("event-selected", {
        detail: { rowId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private tipLines(bar: OverviewBar): TemplateResult[] {
    const row = bar.row;
    const lines = [
      html`<div>${row.title}</div>`,
      html`<div class="muted">${formatTime(row.started_at)}</div>`,
    ];
    if (row.status === "started") {
      lines.push(
        html`<div class="muted">
          elapsed ${formatDuration(this.now - (Date.parse(row.started_at ?? "") || 0))}
        </div>`,
      );
    } else if (row.duration_ms !== null) {
      lines.push(
        html`<div class="muted">latency ${formatDuration(row.duration_ms)}</div>`,
      );
    }
    if (row.usage?.input_tokens !== undefined) {
      lines.push(html`<div class="muted">in ${formatTokens(row.usage.input_tokens)}</div>`);
    }
    if (row.usage?.output_tokens !== undefined) {
      lines.push(html`<div class="muted">out ${formatTokens(row.usage.output_tokens)}</div>`);
    }
    if (row.status && row.status !== "completed") {
      lines.push(
        html`<div class="muted">${statusGlyph(row.status)} ${row.status}</div>`,
      );
    }
    return lines;
  }

  render() {
    const model = buildOverview(this.timeline, this.metric, this.now);
    if (model.bars.length === 0) return "";
    const active = model.bars.find((bar) => bar.active);
    return html`
      <div class="head">
        <span class="label">OVERVIEW</span>
        ${METRICS.map(
          (entry) => html`<button
            class="metric"
            aria-pressed=${this.metric === entry.id ? "true" : "false"}
            @click=${() => {
              this.metric = entry.id;
            }}
          >
            ${entry.label}
          </button>`,
        )}
        <span class="spacer"></span>
        ${active
          ? html`<span class="active-note">
              ${active.row.title} running ·
              ${formatDuration(
                this.now - (Date.parse(active.row.started_at ?? "") || 0),
              )}
              elapsed
            </span>`
          : ""}
      </div>
      <div class="plot" role="group" aria-label="Request overview minimap">
        ${model.ticks.map(
          (tick) => html`<span
            class=${[
              "tick",
              tick.row.id === this.selectedEventId ? "selected" : "",
              tick.row.status ? `state-${tick.row.status}` : "",
            ].join(" ")}
            style="left: ${(tick.x * 100).toFixed(3)}%"
            title=${tick.row.title}
          ></span>`,
        )}
        ${model.bars.map((bar) => {
          const selected = bar.row.id === this.selectedEventId;
          const classes = [
            "bar",
            bar.active ? "active" : "",
            bar.row.status && !bar.active ? `state-${bar.row.status}` : "",
          ].join(" ");
          return html`<button
            class=${classes}
            role="option"
            aria-selected=${selected ? "true" : "false"}
            aria-label=${`${bar.row.title} at ${formatTime(bar.row.started_at)}`}
            style=${`left: ${(bar.x * 100).toFixed(3)}%; height: ${(
              bar.h * 100
            ).toFixed(1)}%`}
            title=${bar.row.title}
            @click=${() => this.select(bar.row.id)}
          >
            <span class="tip">${this.tipLines(bar)}</span>
          </button>`;
        })}
        ${active
          ? html`<span
              class="nowline"
              style="left: 100%"
              title="now"
            ></span>`
          : ""}
      </div>
      <div class="axis">
        <span>${formatTime(new Date(model.t0).toISOString())}</span>
        <span>${active ? "NOW" : formatTime(new Date(model.t1).toISOString())}</span>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-overview-strip": ZuaefOverviewStrip;
  }
}
