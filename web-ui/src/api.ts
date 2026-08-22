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

  /** SSE invalidation stream (T008C): thin run_changed frames only. */
  runEventsUrl: (runId: string) =>
    `/api/runs/${encodeURIComponent(runId)}/events`,
};
