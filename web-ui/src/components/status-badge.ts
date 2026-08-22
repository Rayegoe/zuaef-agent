import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { STATUS_GLYPHS } from "../state";

/** Status as dot glyph + word; color is never the only carrier (UI-SPEC §14). */
@customElement("zuaef-status-badge")
export class ZuaefStatusBadge extends LitElement {
  @property() status = "";

  static styles = css`
    span {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-family: var(--z-font-mono);
      font-size: 11px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .completed { color: var(--z-success); }
    .failed { color: var(--z-danger); }
    .paused { color: var(--z-warning); }
    .limit_reached { color: var(--z-warning); }
    .incomplete, .started { color: var(--z-accent); }
    .unknown, .unresolved { color: var(--z-text-muted); }
  `;

  render() {
    const status = this.status || "unknown";
    return html`<span class=${status}
      ><span aria-hidden="true">${STATUS_GLYPHS[status] ?? "·"}</span>${status}</span
    >`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-status-badge": ZuaefStatusBadge;
  }
}
