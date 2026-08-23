/** Presentation state only (UI-SPEC §11). The server projection is always
 *  authoritative; this module never mirrors runtime business state. */
import type { RunView, TimelineRow } from "./api";

export type InspectorTab = "summary" | "io" | "usage" | "raw";
export type InspectorView = "run" | "inspection" | "analysis";

export interface UiState {
  selectedRunId?: string;
  selectedEventId?: string;
  inspectorView: InspectorView;
  inspectorTab: InspectorTab;
  runFilter?: string;
}

export const initialUiState: UiState = {
  inspectorView: "run",
  inspectorTab: "summary",
};

// ---- pure presentation helpers shared by the row components ----

const MS_DAY = 86_400_000;

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString(undefined, { hour12: false });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatRelative(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const delta = now - date.getTime();
  if (delta < 60_000) return "just now";
  if (delta < 3_600_000) return `${Math.floor(delta / 60_000)}m ago`;
  if (delta < MS_DAY) return `${Math.floor(delta / 3_600_000)}h ago`;
  if (delta < 7 * MS_DAY) return `${Math.floor(delta / MS_DAY)}d ago`;
  return date.toLocaleDateString();
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms < 0) return "";
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds - minutes * 60);
  return `${minutes}m${String(rest).padStart(2, "0")}s`;
}

export function formatTokens(count: number | undefined): string {
  if (typeof count !== "number") return "";
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

export function formatBytes(size: number | null | undefined): string {
  if (size === null || size === undefined) return "Unknown";
  if (size >= 1_048_576) return `${(size / 1_048_576).toFixed(1)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${size} B`;
}

/** Ledger usage cell: "8.9k in · 5.8k out" with only persisted sides shown. */
export function formatUsageCell(usage: Record<string, number> | null | undefined): string {
  if (!usage) return "";
  const parts: string[] = [];
  const input = formatTokens(usage.input_tokens);
  const output = formatTokens(usage.output_tokens);
  if (input) parts.push(`${input} in`);
  if (output) parts.push(`${output} out`);
  return parts.join(" · ");
}

export type RunGroup = "Today" | "Yesterday" | "Older";

export function runGroup(run: RunView, now = Date.now()): RunGroup {
  if (!run.started_at) return "Older";
  const started = new Date(run.started_at).getTime();
  if (Number.isNaN(started)) return "Older";
  const startOfDay = new Date(now).setHours(0, 0, 0, 0);
  if (started >= startOfDay) return "Today";
  if (started >= startOfDay - MS_DAY) return "Yesterday";
  return "Older";
}

/** Status glyph + word so status never rides on color alone (UI-SPEC §14). */
export const STATUS_GLYPHS: Record<string, string> = {
  completed: "✓",
  failed: "✗",
  paused: "⏸",
  incomplete: "◔",
  started: "●",
  unresolved: "?",
  unknown: "?",
  limit_reached: "⏹",
};

export function statusGlyph(status: string | null | undefined): string {
  if (!status) return "";
  return STATUS_GLYPHS[status] ?? "·";
}

export function findRow(
  timeline: TimelineRow[],
  rowId: string | undefined,
): TimelineRow | undefined {
  if (!rowId) return undefined;
  return timeline.find((row) => row.id === rowId);
}

// ---- contiguous tool-row grouping (transient presentation only) ----

export interface ToolRowGroup {
  groupId: string;
  toolName: string;
  rows: TimelineRow[];
}

export type LedgerEntry = TimelineRow | ToolRowGroup;

export function isToolRowGroup(entry: LedgerEntry): entry is ToolRowGroup {
  return "groupId" in entry;
}

/** Collapse runs of contiguous tool rows that share one tool_name into a
 *  single group entry (e.g. check_claim ×7). Pure and transient: input rows
 *  are the already-projected timeline; nothing here touches the API, DTOs
 *  or any persisted shape. A single tool row is never wrapped. */
export function groupContiguousToolRows(rows: TimelineRow[]): LedgerEntry[] {
  const entries: LedgerEntry[] = [];
  let index = 0;
  while (index < rows.length) {
    const row = rows[index];
    if (row.kind !== "tool_call") {
      entries.push(row);
      index += 1;
      continue;
    }
    let end = index + 1;
    while (
      end < rows.length &&
      rows[end].kind === "tool_call" &&
      rows[end].title === row.title
    ) {
      end += 1;
    }
    if (end - index >= 2) {
      entries.push({
        groupId: `tool-group-${row.id}`,
        toolName: row.title,
        rows: rows.slice(index, end),
      });
    } else {
      entries.push(row);
    }
    index = end;
  }
  return entries;
}

export function groupContains(
  group: Pick<ToolRowGroup, "rows">,
  rowId: string | undefined,
): boolean {
  if (!rowId) return false;
  return group.rows.some((row) => row.id === rowId);
}

// ---- live request overview strip (transient presentation only) ----

export type OverviewMetric = "latency" | "input" | "output";

export const OVERVIEW_MAX_BARS = 60;
export const OVERVIEW_MAX_TICKS = 200;

export interface OverviewBar {
  row: TimelineRow;
  /** horizontal position as a fraction of the window span (0..1) */
  x: number;
  /** plotted height as a fraction of the window maximum (0..1) */
  h: number;
  /** the value actually plotted; null when the selected fact is unavailable */
  value: number | null;
  /** request still running — its latency is elapsed time, not final duration */
  active: boolean;
}

export interface OverviewTick {
  row: TimelineRow;
  x: number;
}

export interface OverviewModel {
  bars: OverviewBar[];
  ticks: OverviewTick[];
  /** window bounds as epoch ms; span <= 0 means "not plottable" */
  t0: number;
  t1: number;
  span: number;
}

function startMs(row: TimelineRow): number | null {
  if (!row.started_at) return null;
  const ms = Date.parse(row.started_at);
  return Number.isNaN(ms) ? null : ms;
}

/** Only a request explicitly marked 'started' is known to still be running.
 *  'incomplete' is a historical uncertainty, not evidence of liveness. */
export function isActiveRequest(row: TimelineRow): boolean {
  return row.status === "started";
}

function endMs(row: TimelineRow, now: number): number | null {
  const start = startMs(row);
  if (start === null) return null;
  if (isActiveRequest(row)) return Math.max(now, start);
  if (row.duration_ms !== null) return start + row.duration_ms;
  const finish = row.finished_at ? Date.parse(row.finished_at) : NaN;
  return Number.isNaN(finish) || finish < start ? null : finish;
}

function metricValue(
  row: TimelineRow,
  metric: OverviewMetric,
  now: number,
): number | null {
  if (metric === "input") return row.usage?.input_tokens ?? null;
  if (metric === "output") return row.usage?.output_tokens ?? null;
  const start = startMs(row);
  if (isActiveRequest(row)) {
    // A started request is the only request for which elapsed time is a
    // current fact. It is deliberately not a final latency measurement.
    return start === null ? null : Math.max(now - start, 0);
  }
  return row.duration_ms;
}

/** Time-proportional minimap of one run's model requests. Bars are placed
 *  by started_at over the most recent OVERVIEW_MAX_BARS requests; tool
 *  calls become baseline ticks. Pure and transient: input rows are the
 *  already-projected timeline; nothing here touches the API, DTOs or any
 *  persisted shape. */
export function buildOverview(
  rows: TimelineRow[],
  metric: OverviewMetric,
  now: number,
): OverviewModel {
  const requests = rows
    .filter((row) => row.kind === "model_request" && startMs(row) !== null)
    .sort((a, b) => (startMs(a) ?? 0) - (startMs(b) ?? 0));
  const windowed = requests.slice(-OVERVIEW_MAX_BARS);
  if (windowed.length === 0) {
    return { bars: [], ticks: [], t0: 0, t1: 0, span: 0 };
  }
  let t0 = startMs(windowed[0]) ?? 0;
  const t1 = Math.max(
    ...windowed.map((row) => endMs(row, now) ?? startMs(row) ?? 0),
  );

  const inWindow = (row: TimelineRow): boolean => {
    const start = startMs(row);
    return (
      row.kind === "tool_call" &&
      start !== null &&
      start >= t0 &&
      start <= t1
    );
  };
  const ticks: OverviewTick[] = rows
    .filter(inWindow)
    .slice(0, OVERVIEW_MAX_TICKS)
    .map((row) => ({ row, x: 0 }));

  const span = Math.max(t1 - t0, 1);
  const frac = (ms: number): number =>
    Math.min(Math.max((ms - t0) / span, 0), 1);

  const values = windowed.map((row) => metricValue(row, metric, now));
  const knownValues = values.filter((value): value is number => value !== null);
  const max = Math.max(...knownValues, 1);
  const bars: OverviewBar[] = windowed.map((row, index) => ({
    row,
    x: frac(startMs(row) ?? t0),
    h:
      values[index] === null
        ? 0.04
        : Math.max(Math.min(values[index] / max, 1), 0.04),
    value: values[index],
    active: isActiveRequest(row),
  }));
  for (const tick of ticks) tick.x = frac(startMs(tick.row) ?? t0);
  return { bars, ticks, t0, t1, span };
}
