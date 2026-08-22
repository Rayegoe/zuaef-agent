import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { RunView } from "../api";
import { runGroup } from "../state";
import "./run-row";

/** Run list: filter + Today/Yesterday/Older groups + bounded "Load more". */
@customElement("zuaef-run-list")
export class ZuaefRunList extends LitElement {
  @property({ attribute: false }) runs: RunView[] = [];
  @property() selectedRunId = "";
  @property({ attribute: false }) nextCursor: string | null = null;
  @property({ type: Boolean }) loadingMore = false;
  @property() filter = "";

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--z-surface);
      border-right: 1px solid var(--z-border);
    }
    .filter {
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
    }
    input {
      width: 100%;
      background: var(--z-bg);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 3px var(--z-space-2);
      color: var(--z-text);
      font-family: var(--z-font-mono);
      font-size: 12px;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }
    .group {
      padding: var(--z-space-2) var(--z-space-3) var(--z-space-1);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--z-text-subtle);
    }
    .more,
    .state {
      display: block;
      width: 100%;
      padding: var(--z-space-2) var(--z-space-3);
      border: none;
      border-top: 1px solid var(--z-border);
      background: transparent;
      color: var(--z-text-muted);
      font-size: 12px;
      text-align: left;
    }
    button.more:hover { background: var(--z-surface-hover); color: var(--z-text); }
    .count {
      padding: var(--z-space-1) var(--z-space-3);
      border-top: 1px solid var(--z-border);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-subtle);
    }
  `;

  private onFilter(event: Event) {
    this.dispatchEvent(
      new CustomEvent("run-filter", {
        detail: { value: (event.target as HTMLInputElement).value },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private passesFilter(run: RunView): boolean {
    return this.filter === "" ? true : matchesFilter(run, this.filter);
  }

  render() {
    const visible = this.runs.filter((run) => this.passesFilter(run));
    const groups: Array<[string, RunView[]]> = [
      ["Today", []],
      ["Yesterday", []],
      ["Older", []],
    ];
    for (const run of visible) {
      groups[["Today", "Yesterday", "Older"].indexOf(runGroup(run))][1].push(run);
    }
    const shown = visible.length;
    const total = this.runs.length;

    return html`
      <div class="filter">
        <input
          type="search"
          placeholder="Filter runs…"
          .value=${this.filter}
          @input=${this.onFilter}
          aria-label="Filter runs"
        />
      </div>
      <div class="scroll" role="listbox" aria-label="Runs">
        ${total === 0
          ? html`<div class="state">Loading runs…</div>`
          : shown === 0
            ? html`<div class="state">No runs match this filter.</div>`
            : groups.map(
                ([name, rows]) =>
                  rows.length > 0
                    ? html`
                        <div class="group">${name}</div>
                        ${rows.map(
                          (run) => html`
                            <zuaef-run-row
                              role="option"
                              .run=${run}
                              ?selected=${run.run_id === this.selectedRunId}
                            ></zuaef-run-row>
                          `,
                        )}
                      `
                    : "",
              )}
      </div>
      ${this.nextCursor
        ? html`<button
            class="more"
            ?disabled=${this.loadingMore}
            @click=${() =>
              this.dispatchEvent(
                new CustomEvent("load-more", { bubbles: true, composed: true }),
              )}
          >
            ${this.loadingMore ? "Loading…" : `Load more (${shown} of ${total}+ loaded)`}
          </button>`
        : html`<div class="count">${shown}${shown < total ? ` of ${total}` : ""} runs</div>`}
    `;
  }
}

function matchesFilter(run: RunView, needle: string): boolean {
  const haystack = [run.display_label, run.run_id, run.model, run.profile, run.status]
    .filter(Boolean)
    .join("\n")
    .toLowerCase();
  return haystack.includes(needle.toLowerCase());
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-run-list": ZuaefRunList;
  }
}
