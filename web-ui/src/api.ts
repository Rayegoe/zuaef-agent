/** Typed client for the read-only console API (API-CONTRACT §2–§4, §7).
 *  Mirrors src/zuaef_agent/web/projector.py DTOs; unknown stays null. */

export interface RunView {
  run_id: string;
  conversation_id: string | null;
  parent_run_id: string | null;
  continued_from_run_id: string | null;
  status: string;
  model: string | null;
  profile: string | null;
  agent_name: string | null;
  display_label: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  request_count: number;
  tool_call_count: number;
}

export interface UsageView {
  input_tokens?: number;
  output_tokens?: number;
  requests?: number;
  source?: string;
  [key: string]: unknown;
}

export interface MessagePart {
  part_kind: string;
  content?: string;
  truncated?: boolean;
  tool_name?: string;
  tool_call_id?: string;
  args?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TimelineRow {
  id: string;
  kind: "run" | "model_request" | "tool_call" | string;
  step_index: number | null;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  status: string | null;
  title: string;
  detail: string | null;
  usage: Record<string, number> | null;
  source: string[];
  payload: {
    events?: Record<string, unknown>[];
    response_parts?: MessagePart[];
    [key: string]: unknown;
  };
}

export interface ArtifactFact {
  path: string;
  size: number | null;
  sha256: string;
  change: string;
  label: string;
}

export interface PauseView {
  pending_approvals: string[];
  pending_calls: string[];
}

export interface RunProjection {
  run: RunView;
  usage: UsageView | null;
  timeline: TimelineRow[];
  artifacts: ArtifactFact[];
  pause: PauseView | null;
  unresolved_effects: Record<string, unknown>[];
  composition: Record<string, unknown> | null;
  diagnostics: string[];
  action_in_flight: boolean;
}

export interface RunListPage {
  runs: RunView[];
  next_cursor: string | null;
}

export interface InspectionRequestFact {
  request: string;
  step: number | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  status: string | null;
}

export interface InspectionTimelineFact {
  id: string;
  step: number | null;
  kind: string | null;
  title: string | null;
  status: string | null;
  duration_ms: number | null;
  usage: Record<string, number> | null;
}

export interface InspectionToolFact {
  tool: string;
  total: number;
  contiguous_groups: number[];
}

export interface RunInspection {
  run_id: string | null;
  summary: {
    run_id: string | null;
    status: string | null;
    started_at: string | null;
    finished_at: string | null;
    wall_clock_ms: number | null;
    duration_ms: number | null;
    model: string | null;
    profile: string | null;
    requests: number | null;
    tool_calls: number | null;
    input_tokens: number | null;
    output_tokens: number | null;
    usage_source: string | null;
  };
  rankings: {
    slowest_requests: InspectionRequestFact[];
    largest_input_requests: InspectionRequestFact[];
    largest_output_requests: InspectionRequestFact[];
  };
  tool_activity: InspectionToolFact[];
  timeline: InspectionTimelineFact[];
  artifacts: ArtifactFact[];
  unknown_facts: {
    incomplete_requests: Record<string, unknown>[];
    unresolved_tool_calls: Record<string, unknown>[];
    started_tool_calls: Record<string, unknown>[];
    unavailable_usage: string[];
    diagnostics: string[];
  };
  bounds: Record<string, number>;
}

export interface RunAnalysis {
  state: "not_started" | "running" | "completed" | "failed" | string;
  subject_run_id: string;
  analysis_run_id: string | null;
  artifact_path: string | null;
  content?: string | null;
  error?: string | null;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function get<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    let code = "INTERNAL_ERROR";
    let message = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { error?: { code?: string; message?: string } };
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
    } catch {
      // non-JSON error body — keep the HTTP fallbacks
    }
    throw new ApiError(code, message, response.status);
  }
  return (await response.json()) as T;
}

async function post<T>(url: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let code = "INTERNAL_ERROR";
    let message = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { error?: { code?: string; message?: string } };
      if (payload.error?.code) code = payload.error.code;
      if (payload.error?.message) message = payload.error.message;
    } catch {
      // non-JSON error body — keep the HTTP fallbacks
    }
    throw new ApiError(code, message, response.status);
  }
  return (await response.json()) as T;
}

const PAGE_LIMIT = 200;

export const api = {
  health: () => get<{ ok: boolean; version: string }>("/api/health"),

  listRuns: (cursor?: string | null) =>
    get<RunListPage>(
      cursor
        ? `/api/runs?limit=${PAGE_LIMIT}&cursor=${encodeURIComponent(cursor)}`
        : `/api/runs?limit=${PAGE_LIMIT}`,
    ),

  getRun: (runId: string) =>
    get<RunProjection>(`/api/runs/${encodeURIComponent(runId)}`),

  getRunInspection: (runId: string) =>
    get<RunInspection>(`/api/runs/${encodeURIComponent(runId)}/inspection`),

  getRunAnalysis: (runId: string) =>
    get<RunAnalysis>(`/api/runs/${encodeURIComponent(runId)}/analysis`),

  createRunAnalysis: (
    runId: string,
    options: { selectedRowId?: string | null; intent?: string } = {},
  ) =>
    post<{
      accepted: boolean;
      subject_run_id: string;
      analysis_run_id: string;
      artifact_path: string;
    }>(`/api/runs/${encodeURIComponent(runId)}/analysis`, {
      scope: "full",
      selected_row_id: options.selectedRowId ?? null,
      intent: options.intent ?? "Diagnose this run for the next smallest engineering experiment.",
      agent: true,
    }),

  /** SSE invalidation stream (T008C): thin run_changed frames only. */
  runEventsUrl: (runId: string) =>
    `/api/runs/${encodeURIComponent(runId)}/events`,
};
