/** Presentation state only (UI-SPEC §11). The server projection is always
 *  authoritative; this module never mirrors runtime business state. */
import type { RunView, TimelineRow } from "./api";

export type InspectorTab = "summary" | "io" | "usage" | "raw";

export interface UiState {
  selectedRunId?: string;
  selectedEventId?: string;
  inspectorTab: InspectorTab;
  runFilter?: string;
}

export const initialUiState: UiState = {
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
