import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import type {
  InspectionRequestFact,
  InspectionTimelineFact,
  InspectionToolFact,
  MessagePart,
  RunAnalysis,
  RunInspection,
  RunProjection,
  TimelineRow,
} from "../api";
import {
  formatBytes,
  formatDateTime,
  formatDuration,
  formatTokens,
  findRow,
  type InspectorTab,
  type InspectorView,
} from "../state";
import "./status-badge";

const PREVIEW_CHARS = 2_000;
const RAW_CAP = 20_000;

/** Right pane: detail for the selected event, or the run overview.
 *  Tabs appear only where real data exists (UI-SPEC §6); gaps stay labeled
 *  Unknown / Not persisted — never inferred. */
@customElement("zuaef-inspector")
export class ZuaefInspector extends LitElement {
  @property({ attribute: false }) projection: RunProjection | null = null;
  @property({ attribute: false }) inspection: RunInspection | null = null;
  @property() inspectorView: InspectorView = "run";
  @property({ attribute: false }) analysis: RunAnalysis | null = null;
  @property() selectedEventId = "";
  @property() inspectorTab: InspectorTab = "summary";
  @property() inspectionLoading = false;
  @property() inspectionError = "";
  @property() analysisLoading = false;
  @property() analysisError = "";

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--z-surface);
      border-left: 1px solid var(--z-border);
    }
    .tabs {
      display: flex;
      border-bottom: 1px solid var(--z-border);
      flex-shrink: 0;
    }
    .view-tabs {
      display: flex;
      border-bottom: 1px solid var(--z-border);
      background: var(--z-bg);
      flex-shrink: 0;
    }
    .view-tabs button {
      padding: var(--z-space-2) var(--z-space-3);
      font-size: 12px;
      color: var(--z-text-muted);
      background: transparent;
      border: none;
      border-bottom: 1px solid transparent;
      margin-bottom: -1px;
      cursor: pointer;
    }
    .view-tabs button:hover { color: var(--z-text); }
    .view-tabs button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .view-tabs button[aria-selected="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .tabs button {
      padding: var(--z-space-2) var(--z-space-3);
      font-size: 12px;
      color: var(--z-text-muted);
      background: transparent;
      border: none;
      border-bottom: 1px solid transparent;
      margin-bottom: -1px;
      cursor: pointer;
    }
    .tabs button:hover { color: var(--z-text); }
    .tabs button:focus-visible {
      outline: 1px dashed var(--z-accent);
      outline-offset: -1px;
    }
    .tabs button[aria-selected="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      padding: var(--z-space-3);
    }
    h3 {
      margin: 0 0 var(--z-space-2);
      font-size: 13px;
    }
    h4 {
      margin: var(--z-space-4) 0 var(--z-space-1);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--z-text-subtle);
    }
    dl {
      display: grid;
      grid-template-columns: 110px minmax(0, 1fr);
      gap: 4px var(--z-space-2);
      margin: 0;
    }
    dt {
      color: var(--z-text-subtle);
      font-size: 11px;
      letter-spacing: 0.02em;
      padding-top: 1px;
    }
    dd {
      margin: 0;
      font-family: var(--z-font-mono);
      font-size: 12px;
      color: var(--z-text);
      overflow-wrap: anywhere;
    }
    dd.none { color: var(--z-text-subtle); }
    pre {
      margin: var(--z-space-2) 0;
      padding: var(--z-space-2);
      background: var(--z-bg);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      font-size: 11px;
      overflow-x: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      max-height: 420px;
      overflow-y: auto;
    }
    details summary {
      cursor: pointer;
      color: var(--z-accent);
      font-size: 12px;
      user-select: none;
    }
    .part {
      border-top: 1px solid var(--z-border);
      padding-top: var(--z-space-2);
      margin-top: var(--z-space-2);
    }
    .part:first-of-type { border-top: none; margin-top: 0; padding-top: 0; }
    .muted { color: var(--z-text-muted); font-size: 12px; }
    .diag {
      color: var(--z-warning);
      font-family: var(--z-font-mono);
      font-size: 11px;
      overflow-wrap: anywhere;
      margin: 2px 0;
    }
    .error-line { color: var(--z-danger); overflow-wrap: anywhere; }
    .inspection-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .inspection-table th,
    .inspection-table td {
      border-bottom: 1px solid var(--z-divider);
      padding: 5px 4px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    .inspection-table th {
      color: var(--z-text-subtle);
      font-weight: 500;
    }
    .inspection-table td.number,
    .inspection-table th.number { text-align: right; }
    .inspection-table td.unknown { color: var(--z-text-subtle); }
    .inspection-list {
      margin: 0;
      padding-left: 18px;
      color: var(--z-text-muted);
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .inspection-note {
      color: var(--z-text-muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .analysis-action {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: var(--z-space-2) var(--z-space-3);
      color: var(--z-text);
      background: var(--z-bg);
      cursor: pointer;
      font-size: 12px;
    }
    .analysis-action:hover:not(:disabled) { background: var(--z-surface-hover); }
    .analysis-action:disabled { opacity: 0.55; cursor: default; }
    .analysis-output {
      max-height: none;
      white-space: pre-wrap;
      font-family: var(--z-font-mono);
      line-height: 1.45;
    }
  `;

  private get row(): TimelineRow | undefined {
    return findRow(this.projection?.timeline ?? [], this.selectedEventId);
  }

  private get availableTabs(): InspectorTab[] {
    const row = this.row;
    if (!row) return ["summary"];
    const tabs: InspectorTab[] = ["summary"];
    if ((row.payload.response_parts ?? []).length > 0) tabs.push("io");
    if (row.usage && Object.keys(row.usage).length > 0) tabs.push("usage");
    tabs.push("raw");
    return tabs;
  }

  private setTab(tab: InspectorTab) {
    this.dispatchEvent(
      new CustomEvent("tab-selected", {
        detail: { tab },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private setView(view: InspectorView) {
    this.dispatchEvent(
      new CustomEvent("view-selected", {
        detail: { view },
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    const viewTabs = html`<div class="view-tabs" role="tablist" aria-label="Inspector view">
      ${(["run", "inspection", "analysis"] as InspectorView[]).map(
        (view) => html`<button
          role="tab"
          aria-selected=${view === this.inspectorView ? "true" : "false"}
          @click=${() => this.setView(view)}
        >
          ${view === "run" ? "Run" : view === "inspection" ? "Inspection" : "Analysis"}
        </button>`,
      )}
    </div>`;

    if (this.inspectorView === "inspection") {
      return html`${viewTabs}${this.renderInspection()}`;
    }
    if (this.inspectorView === "analysis") {
      return html`${viewTabs}${this.renderAnalysis()}`;
    }

    const tabs = this.availableTabs;
    const active: InspectorTab = tabs.includes(this.inspectorTab)
      ? this.inspectorTab
      : "summary";
    const row = this.row;
    return html`${viewTabs}
      ${tabs.length > 1
        ? html`<div class="tabs" role="tablist">
            ${tabs.map(
              (tab) => html`<button
                role="tab"
                aria-selected=${tab === active ? "true" : "false"}
                @click=${() => this.setTab(tab)}
              >
                ${TAB_LABELS[tab]}
              </button>`,
            )}
          </div>`
        : ""}
      <div class="scroll">
        ${row ? this.renderEvent(active, row) : this.renderRunOverview()}
      </div>
    `;
  }

  // ---- deterministic run inspection ------------------------------------

  private renderInspection() {
    if (this.inspectionLoading) {
      return html`<div class="scroll"><p class="inspection-note">Loading inspection…</p></div>`;
    }
    if (this.inspectionError) {
      return html`<div class="scroll"><p class="error-line">${this.inspectionError}</p></div>`;
    }
    const inspection = this.inspection;
    if (!inspection) {
      return html`<div class="scroll"><p class="inspection-note">Select a run.</p></div>`;
    }

    const summary = inspection.summary;
    return html`
      <div class="scroll">
        <h3>Inspection</h3>
        <p class="inspection-note">
          Deterministic facts from the current run projection. Model input/output content is excluded.
        </p>
        <dl>
          <dt>Status</dt>
          <dd><zuaef-status-badge .status=${summary.status ?? ""}></zuaef-status-badge></dd>
          <dt>Run ID</dt>
          <dd>${summary.run_id ?? "Unknown"}</dd>
          <dt>Model</dt>
          <dd class=${summary.model ? "" : "none"}>${summary.model ?? "Unknown"}</dd>
          <dt>Profile</dt>
          <dd class=${summary.profile ? "" : "none"}>${summary.profile ?? "Unknown"}</dd>
          <dt>Duration</dt>
          <dd class=${summary.duration_ms === null ? "none" : ""}>
            ${summary.duration_ms === null ? "Unknown" : formatDuration(summary.duration_ms)}
          </dd>
          <dt>Requests</dt><dd>${this.knownNumber(summary.requests)}</dd>
          <dt>Tool calls</dt><dd>${this.knownNumber(summary.tool_calls)}</dd>
          <dt>Input tokens</dt><dd>${formatTokens(summary.input_tokens ?? undefined) || "Unknown"}</dd>
          <dt>Output tokens</dt><dd>${formatTokens(summary.output_tokens ?? undefined) || "Unknown"}</dd>
          <dt>Usage basis</dt><dd>${summary.usage_source ?? "Unknown"}</dd>
        </dl>

        ${this.renderRequestRanking("Slowest requests", inspection.rankings.slowest_requests)}
        ${this.renderRequestRanking("Largest input", inspection.rankings.largest_input_requests)}
        ${this.renderRequestRanking("Largest output", inspection.rankings.largest_output_requests)}
        ${this.renderToolActivity(inspection.tool_activity)}
        ${this.renderInspectionTimeline(
          inspection.timeline,
          inspection.bounds.chronology_omitted ?? 0,
        )}
        ${this.renderInspectionArtifacts(inspection)}
        ${this.renderUnknownFacts(inspection)}
      </div>
    `;
  }

  private createAnalysis() {
    this.dispatchEvent(
      new CustomEvent("analysis-create", {
        bubbles: true,
        composed: true,
      }),
    );
  }

  private renderAnalysis() {
    if (this.analysisLoading && !this.analysis) {
      return html`<div class="scroll"><p class="inspection-note">Starting analysis…</p></div>`;
    }
    if (this.analysisError && !this.analysis) {
      return html`<div class="scroll">
        <p class="error-line">${this.analysisError}</p>
        <button class="analysis-action" @click=${() => this.createAnalysis()}>Retry analysis</button>
      </div>`;
    }
    const analysis = this.analysis;
    if (!analysis || analysis.state === "not_started") {
      return html`<div class="scroll">
        <h3>Run Analysis</h3>
        <p class="inspection-note">
          The Agent receives only bounded deterministic inspection facts. It does not browse, use a shell, or modify the subject run.
        </p>
        <button class="analysis-action" ?disabled=${this.analysisLoading} @click=${() => this.createAnalysis()}>
          ${this.analysisLoading ? "Starting…" : "Create analysis.md"}
        </button>
      </div>`;
    }
    if (analysis.state === "running") {
      return html`<div class="scroll">
        <h3>Run Analysis</h3>
        <p class="inspection-note">Analysis Agent is inspecting the subject run…</p>
        <dl>
          <dt>Analysis run</dt><dd>${analysis.analysis_run_id ?? "Unknown"}</dd>
          <dt>Artifact</dt><dd>${analysis.artifact_path ?? "Unknown"}</dd>
        </dl>
      </div>`;
    }
    if (analysis.state === "failed") {
      return html`<div class="scroll">
        <h3>Run Analysis</h3>
        <p class="error-line">${analysis.error ?? "Analysis run failed."}</p>
        <dl>
          <dt>Analysis run</dt><dd>${analysis.analysis_run_id ?? "Unknown"}</dd>
          <dt>Artifact</dt><dd>${analysis.artifact_path ?? "Unknown"}</dd>
        </dl>
        <button class="analysis-action" @click=${() => this.createAnalysis()}>Retry analysis</button>
      </div>`;
    }
    return html`<div class="scroll">
      <h3>Run Analysis</h3>
      <p class="inspection-note">
        Semantic diagnosis is stored as a human/Agent work artifact. Runtime facts remain in Inspection.
      </p>
      <dl>
        <dt>Analysis run</dt><dd>${analysis.analysis_run_id ?? "Unknown"}</dd>
        <dt>Artifact</dt><dd>${analysis.artifact_path ?? "Unknown"}</dd>
      </dl>
      ${analysis.content
        ? html`<pre class="analysis-output">${analysis.content}</pre>`
        : html`<p class="inspection-note">analysis.md has no readable content.</p>`}
    </div>`;
  }

  private renderRequestRanking(title: string, rows: InspectionRequestFact[]) {
    return html`
      <h4>${title}</h4>
      ${rows.length === 0
        ? html`<p class="inspection-note">No authoritative values available.</p>`
        : html`<table class="inspection-table">
            <thead><tr><th>Request</th><th class="number">Latency</th><th class="number">Input</th><th class="number">Output</th><th>Status</th></tr></thead>
            <tbody>${rows.map((row) => html`<tr>
              <td>${row.request}</td>
              <td class="number ${row.latency_ms === null ? "unknown" : ""}">${this.durationValue(row.latency_ms)}</td>
              <td class="number ${row.input_tokens === null ? "unknown" : ""}">${this.tokenValue(row.input_tokens)}</td>
              <td class="number ${row.output_tokens === null ? "unknown" : ""}">${this.tokenValue(row.output_tokens)}</td>
              <td>${row.status ?? "Unknown"}</td>
            </tr>`)}</tbody>
          </table>`}
    `;
  }

  private renderToolActivity(rows: InspectionToolFact[]) {
    return html`
      <h4>Tool activity</h4>
      ${rows.length === 0
        ? html`<p class="inspection-note">No tool calls recorded.</p>`
        : html`<table class="inspection-table">
            <thead><tr><th>Tool</th><th class="number">Total</th><th>Contiguous groups</th></tr></thead>
            <tbody>${rows.map((row) => html`<tr>
              <td>${row.tool}</td>
              <td class="number">${row.total}</td>
              <td>${row.contiguous_groups.join(", ") || "None"}</td>
            </tr>`)}</tbody>
          </table>`}
    `;
  }

  private renderInspectionTimeline(rows: InspectionTimelineFact[], omitted: number) {
    return html`
      <h4>Observed sequence</h4>
      ${rows.length === 0
        ? html`<p class="inspection-note">No bounded timeline facts available.</p>`
        : html`<table class="inspection-table">
            <thead><tr><th>Step</th><th>Kind</th><th>Title</th><th>Duration</th><th>Status</th></tr></thead>
            <tbody>${rows.map((row) => html`<tr>
              <td>${row.step ?? "?"}</td>
              <td>${row.kind ?? "Unknown"}</td>
              <td>${row.title ?? "Unknown"}</td>
              <td>${this.durationValue(row.duration_ms)}</td>
              <td>${row.status ?? "Unknown"}</td>
            </tr>`)}</tbody>
          </table>`}
      ${omitted > 0
        ? html`<p class="inspection-note">${omitted.toLocaleString()} chronology row(s) omitted by the bounded view.</p>`
        : nothing}
    `;
  }

  private renderInspectionArtifacts(inspection: RunInspection) {
    return html`
      <h4>Artifacts</h4>
      ${inspection.artifacts.length === 0
        ? html`<p class="inspection-note">No artifact facts recorded.</p>`
        : html`<ul class="inspection-list">${inspection.artifacts.map((artifact) => html`<li>
            ${artifact.path}${artifact.size !== null ? ` — ${formatBytes(artifact.size)}` : ""}
            ${artifact.change ? ` (${artifact.change})` : ""}
          </li>`)}</ul>`}
    `;
  }

  private renderUnknownFacts(inspection: RunInspection) {
    const unknown = inspection.unknown_facts;
    const unresolved = [...unknown.incomplete_requests, ...unknown.unresolved_tool_calls, ...unknown.started_tool_calls];
    const hasUnknown = unresolved.length > 0 || unknown.unavailable_usage.length > 0 || unknown.diagnostics.length > 0;
    if (!hasUnknown) return nothing;
    return html`
      <h4>Unknown facts</h4>
      ${unknown.unavailable_usage.length > 0
        ? html`<p class="inspection-note">Unavailable: ${unknown.unavailable_usage.join(", ")}</p>`
        : nothing}
      ${unresolved.length > 0
        ? html`<pre>${JSON.stringify(unresolved, null, 2)}</pre>`
        : nothing}
      ${unknown.diagnostics.map((diagnostic) => html`<p class="diag">${diagnostic}</p>`)}
    `;
  }

  private knownNumber(value: number | null): string {
    return value === null ? "Unknown" : value.toLocaleString();
  }

  private durationValue(value: number | null): string {
    return value === null ? "Unknown" : formatDuration(value);
  }

  private tokenValue(value: number | null): string {
    return value === null ? "Unknown" : formatTokens(value);
  }

  // ---- event detail ----

  private renderEvent(active: InspectorTab, row: TimelineRow) {
    switch (active) {
      case "io":
        return this.renderIo(row);
      case "usage":
        return this.renderUsage(row);
      case "raw":
        return this.renderRaw(row);
      default:
        return this.renderSummary(row);
    }
  }

  private renderSummary(row: TimelineRow) {
    const events = row.payload.events ?? [];
    const toolCallId = events.find((e) => e.tool_call_id)?.tool_call_id;
    return html`
      <h3>${row.title}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${row.status ?? ""}></zuaef-status-badge></dd>
        <dt>Kind</dt>
        <dd>${row.kind}</dd>
        ${row.step_index !== null
          ? html`<dt>Step</dt><dd>#${row.step_index}</dd>`
          : nothing}
        <dt>Started</dt>
        <dd class=${row.started_at ? "" : "none"}>${row.started_at ?? "Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${row.finished_at ? "" : "none"}>${row.finished_at ?? "Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${row.duration_ms !== null ? "" : "none"}>
          ${row.duration_ms !== null ? formatDuration(row.duration_ms) : "Not derivable"}
        </dd>
        ${toolCallId
          ? html`<dt>tool_call_id</dt><dd>${String(toolCallId)}</dd>`
          : nothing}
        ${row.detail
          ? html`<dt>Error</dt><dd class="error-line">${row.detail}</dd>`
          : nothing}
        <dt>Derived from</dt>
        <dd>${row.source.join(", ")}</dd>
      </dl>
      ${this.renderEventPayloadHint(row)}
    `;
  }

  private renderEventPayloadHint(row: TimelineRow) {
    if (row.kind === "model_request") {
      const ioAvailable = (row.payload.response_parts ?? []).length > 0;
      return html`<h4>Persisted data</h4>
        <p class="muted">
          ${ioAvailable
            ? "Per-response output parts are persisted (see Input/Output)."
            : "No response message persisted for this request."}
        </p>`;
    }
    if (row.kind === "tool_call") {
      const effect = row.detail;
      return html`<h4>Persisted data</h4>
        <p class="muted">
          ${effect ? `Effect ledger: ${effect}` : "No effect summary recorded."}
          Raw lifecycle events are under Raw.
        </p>`;
    }
    return nothing;
  }

  private renderIo(row: TimelineRow) {
    const parts = row.payload.response_parts ?? [];
    if (parts.length === 0) {
      return html`<p class="muted">Not persisted</p>`;
    }
    return html`${parts.map((part, index) => this.renderPart(part, index))}`;
  }

  private renderPart(part: MessagePart, index: number) {
    const content = typeof part.content === "string" ? part.content : null;
    return html`
      <div class="part">
        <h4>Response part #${index} · ${part.part_kind}</h4>
        ${part.tool_name
          ? html`<dl><dt>Tool</dt><dd>${part.tool_name}</dd></dl>`
          : nothing}
        ${content !== null ? this.renderText(content, part.truncated === true) : nothing}
        ${part.args
          ? html`<details>
              <summary>args</summary>
              <pre>${JSON.stringify(part.args, null, 2)}</pre>
            </details>`
          : nothing}
      </div>
    `;
  }

  private renderText(content: string, truncatedByApi: boolean) {
    if (content.length <= PREVIEW_CHARS) {
      return html`<pre>${content}</pre>`;
    }
    const suffix =
      truncatedByApi || content.length >= RAW_CAP
        ? " (already truncated by the API)"
        : "";
    return html`<pre>${content.slice(0, PREVIEW_CHARS)}…</pre>
    <details>
      <summary>Show full text (${content.length.toLocaleString()} chars)${suffix}</summary>
      <pre>${content}</pre>
    </details>`;
  }

  private renderUsage(row: TimelineRow) {
    const usage = row.usage ?? {};
    return html`
      <h3>Usage</h3>
      <dl>
        <dt>Input tokens</dt>
        <dd class=${usage.input_tokens !== undefined ? "" : "none"}>
          ${usage.input_tokens !== undefined ? usage.input_tokens.toLocaleString() : "Unknown"}
        </dd>
        <dt>Output tokens</dt>
        <dd class=${usage.output_tokens !== undefined ? "" : "none"}>
          ${usage.output_tokens !== undefined ? usage.output_tokens.toLocaleString() : "Unknown"}
        </dd>
        ${typeof usage.requests === "number"
          ? html`<dt>Requests</dt><dd>${usage.requests}</dd>`
          : nothing}
      </dl>
    `;
  }

  private renderRaw(row: TimelineRow) {
    const json = JSON.stringify(row.payload, null, 2) ?? "{}";
    return html`
      <h3>Raw</h3>
      <p class="muted">Exactly what GET /api/runs returned for this row.</p>
      ${json.length > RAW_CAP
        ? html`<p class="muted">Preview truncated at ${RAW_CAP.toLocaleString()} chars.</p>
            <pre>${json.slice(0, RAW_CAP)}…</pre>`
        : html`<pre>${json}</pre>`}
    `;
  }

  // ---- run overview (no event selected) ----

  private renderRunOverview() {
    const projection = this.projection;
    if (!projection) return html`<p class="muted">Select a run.</p>`;
    const run = projection.run;
    const composition = projection.composition;
    return html`
      <h3>${run.display_label}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${run.status}></zuaef-status-badge></dd>
        <dt>Run ID</dt>
        <dd>${run.run_id}</dd>
        ${run.conversation_id
          ? html`<dt>Conversation</dt><dd>${run.conversation_id}</dd>`
          : nothing}
        ${run.parent_run_id
          ? html`<dt>Parent run</dt><dd>${run.parent_run_id}</dd>`
          : nothing}
        ${run.continued_from_run_id
          ? html`<dt>Continued from</dt><dd>${run.continued_from_run_id}</dd>`
          : nothing}
        <dt>Model</dt>
        <dd class=${run.model ? "" : "none"}>${run.model ?? "Unknown"}</dd>
        <dt>Profile</dt>
        <dd class=${run.profile ? "" : "none"}>${run.profile ?? "Unknown"}</dd>
        ${run.agent_name
          ? html`<dt>Agent</dt><dd>${run.agent_name}</dd>`
          : nothing}
        <dt>Started</dt>
        <dd class=${run.started_at ? "" : "none"}>${formatDateTime(run.started_at) || "Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${run.finished_at ? "" : "none"}>${formatDateTime(run.finished_at) || "Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${run.duration_ms !== null ? "" : "none"}>
          ${run.duration_ms !== null ? formatDuration(run.duration_ms) : "Not derivable"}
        </dd>
        <dt>Requests</dt>
        <dd>${run.request_count}</dd>
        <dt>Tool calls</dt>
        <dd>${run.tool_call_count}</dd>
      </dl>

      <h4>Usage</h4>
      ${projection.usage
        ? html`<dl>
            <dt>Input tokens</dt>
            <dd class=${projection.usage.input_tokens !== undefined ? "" : "none"}>
              ${projection.usage.input_tokens !== undefined
                ? projection.usage.input_tokens.toLocaleString()
                : "Unknown"}
            </dd>
            <dt>Output tokens</dt>
            <dd class=${projection.usage.output_tokens !== undefined ? "" : "none"}>
              ${projection.usage.output_tokens !== undefined
                ? projection.usage.output_tokens.toLocaleString()
                : "Unknown"}
            </dd>
            <dt>Basis</dt>
            <dd>${projection.usage.source ?? "unknown"}</dd>
          </dl>`
        : html`<p class="muted">Not persisted</p>`}

      <h4>Composition</h4>
      ${composition
        ? html`<details>
            <summary>${composition.profile ?? "composition recorded"}</summary>
            <pre>${JSON.stringify(composition, null, 2)}</pre>
          </details>`
        : html`<p class="muted">Receipt unavailable</p>`}

      ${projection.pause
        ? html`<h4>Pause</h4>
            <p class="muted">
              Paused with ${projection.pause.pending_approvals.length} pending
              approval(s). Supervision actions are not part of this read-only build.
            </p>`
        : nothing}

      ${projection.unresolved_effects.length > 0
        ? html`<h4>Unresolved effects</h4>
            <pre>${JSON.stringify(projection.unresolved_effects, null, 2)}</pre>`
        : nothing}

      ${projection.diagnostics.length > 0
        ? html`<h4>Diagnostics</h4>
            ${projection.diagnostics.map((line) => html`<p class="diag">${line}</p>`)}`
        : nothing}

      ${projection.artifacts.length > 0
        ? html`<h4>Artifacts</h4>
            ${projection.artifacts.map(
              (artifact) => html`<p class="muted">
                ${artifact.path}${artifact.size !== null
                  ? ` — ${formatBytes(artifact.size)}`
                  : ""}
              </p>`,
            )}`
        : nothing}
    `;
  }
}

const TAB_LABELS: Record<InspectorTab, string> = {
  summary: "Summary",
  io: "Input/Output",
  usage: "Usage",
  raw: "Raw",
};

declare global {
  interface HTMLElementTagNameMap {
    "zuaef-inspector": ZuaefInspector;
  }
}
