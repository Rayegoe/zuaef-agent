import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { ArtifactFact, PauseView } from "../api";
import { formatBytes } from "../state";

/** Bottom bar: artifact facts + pause notice. Read-only build — there is no
 *  artifact content endpoint and no approval action wired (T010 is later). */
@customElement("zuaef-artifact-bar")
export class ZuaefArtifactBar extends LitElement {
  @property({ attribute: false }) artifacts: ArtifactFact[] = [];
  @property({ attribute: false }) pause: PauseView | null = null;

  static styles = css`
    :host {
      display: flex;
      align-items: center;
      gap: var(--z-space-4);
      padding: var(--z-space-2) var(--z-space-3);
      border-top: 1px solid var(--z-border);
      background: var(--z-surface);
      overflow-x: auto;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .label {
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--z-text-subtle);
      flex-shrink: 0;
    }
    .artifact {
      display: inline-flex;
      align-items: baseline;
      gap: var(--z-space-2);
      font-family: var(--z-font-mono);
      font-size: 12px;
    }
    .path { color: var(--z-text); }
    .fact { color: var(--z-text-muted); font-size: 11px; }
    .none { color: var(--z-text-subtle); font-size: 12px; }
    .pause {
      color: var(--z-warning);
      font-size: 12px;
      border-left: 1px solid var(--z-border);
      padding-left: var(--z-space-4);
      flex-shrink: 0;
    }
  `;

  render() {
    return html`
      <span class="label">Artifact</span>
      ${this.artifacts.length === 0
        ? html`<span class="none">No artifacts recorded for this run</span>`
        : this.artifacts.map(
            (artifact) => html`<span class="artifact" title=${artifact.sha256}>
              <span class="path">${artifact.path}</span>
              <span class="fact">${formatBytes(artifact.size)}</span>
              <span class="fact">${artifact.change}</span>
              <span class="fact">sha256:${artifact.sha256.slice(0, 12)}</span>
            </span>`,
          )}
      ${this.pause
        ? html`<span class="pause">
            ⏸ paused — ${this.pause.pending_approvals.length} approval(s) pending
            (supervision not wired in read-only build)
          </span>`
        : ""}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-artifact-bar": ZuaefArtifactBar;
  }
}
