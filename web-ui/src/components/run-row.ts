import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { RunView } from "../api";
import { formatRelative } from "../state";

/** One selectable run row (UI-SPEC §4): status, label, time, tiny metadata. */
@customElement("zuaef-run-row")
export class ZuaefRunRow extends LitElement {
  @property({ attribute: false }) run!: RunView;
  @property({ type: Boolean }) selected = false;

  static styles = css`
    button {
      display: grid;
      grid-template-columns: 14px minmax(0, 1fr) auto;
      gap: 2px var(--z-space-2);
      width: 100%;
      padding: 5px var(--z-space-3);
      text-align: left;
      background: transparent;
      border: none;
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
    .glyph {
      grid-row: 1 / 3;
      align-self: center;
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .glyph.failed { color: var(--z-danger); }
    .glyph.paused, .glyph.limit_reached { color: var(--z-warning); }
    .glyph.incomplete, .glyph.started { color: var(--z-accent); }
    .glyph.completed { color: var(--z-text-subtle); }
    .label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--z-text);
    }
    .meta {
      font-size: 11px;
      color: var(--z-text-subtle);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .time {
      grid-column: 3;
      grid-row: 1 / 3;
      align-self: center;
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
    }
  `;

  private select() {
    this.dispatchEvent(
      new CustomEvent("run-selected", {
        detail: { runId: this.run.run_id },
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    const run = this.run;
    const meta = [run.model, run.profile].filter(Boolean).join(" · ");
    return html`
      <button
        role="option"
        aria-selected=${this.selected ? "true" : "false"}
        title=${`${run.display_label} — ${run.status} (${run.started_at ?? "unknown start"})`}
        @click=${this.select}
      >
        <span class="glyph ${run.status}" aria-hidden="true"
          >${glyphFor(run.status)}</span
        >
        <span class="label">${run.display_label}</span>
        <span class="time">${formatRelative(run.started_at)}</span>
        ${meta
          ? html`<span class="meta">${meta}</span>`
          : html`<span class="meta">no model/profile recorded</span>`}
      </button>
    `;
  }
}

function glyphFor(status: string): string {
  switch (status) {
    case "completed": return "✓";
    case "failed": return "✗";
    case "paused": return "⏸";
    case "limit_reached": return "⏹";
    case "incomplete":
    case "started": return "●";
    default: return "?";
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-run-row": ZuaefRunRow;
  }
}
