import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const smokeDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(smokeDir, "../..");
const staticRoot = resolve(projectRoot, "src/zuaef_agent/web/static/dist");
const chromePath = "/usr/bin/google-chrome";

const wait = (ms) => new Promise((resolvePromise) => setTimeout(resolvePromise, ms));

async function freePort() {
  const server = createServer();
  await new Promise((resolvePromise, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolvePromise);
  });
  const address = server.address();
  const port = address.port;
  await new Promise((resolvePromise) => server.close(resolvePromise));
  return port;
}

function iso(offsetMs) {
  return new Date(Date.now() + offsetMs).toISOString();
}

function runView(runId, label, status, startedAt) {
  return {
    run_id: runId,
    conversation_id: null,
    parent_run_id: null,
    continued_from_run_id: null,
    status,
    model: "mock-model",
    profile: "smoke",
    agent_name: "smoke-agent",
    display_label: label,
    started_at: startedAt,
    finished_at: status === "completed" ? iso(-8_000) : null,
    duration_ms: status === "completed" ? 1_000 : null,
    request_count: 1,
    tool_call_count: 0,
  };
}

function row(id, title, startedAt, fields = {}) {
  return {
    id,
    kind: "model_request",
    step_index: fields.step_index ?? 1,
    started_at: startedAt,
    finished_at: fields.finished_at ?? null,
    duration_ms: fields.duration_ms ?? null,
    status: fields.status ?? "completed",
    title,
    detail: null,
    usage: fields.usage ?? null,
    source: ["browser-smoke"],
    payload: {},
  };
}

function createMockState() {
  const runs = [
    runView("completed-run", "Completed run", "completed", iso(-20_000)),
    runView("live-run", "Live fidelity run", "incomplete", iso(-9_000)),
    runView("slow-run", "Slow selection", "completed", iso(-30_000)),
    runView("fast-run", "Fast selection", "completed", iso(-25_000)),
  ];
  const projections = new Map([
    [
      "completed-run",
      {
        run: runs[0],
        usage: { input_tokens: 100, output_tokens: 20, requests: 1, source: "per_response" },
        timeline: [
          row("completed-request", "completed request", iso(-19_000), {
            finished_at: iso(-18_000),
            duration_ms: 1_000,
            usage: { input_tokens: 100, output_tokens: 20 },
          }),
        ],
        artifacts: [],
        pause: null,
        unresolved_effects: [],
        composition: null,
        diagnostics: [],
        action_in_flight: false,
      },
    ],
    [
      "live-run",
      {
        run: runs[1],
        usage: { input_tokens: 1_000, output_tokens: 100, requests: 3, source: "receipt_aggregate" },
        timeline: [
          row("known-request", "known request", iso(-8_000), {
            finished_at: iso(-7_500),
            duration_ms: 500,
            usage: { input_tokens: 1_000, output_tokens: 100 },
          }),
          row("incomplete-request", "incomplete request", iso(-6_000), {
            status: "incomplete",
          }),
          row("active-request", "active request", iso(-3_000), {
            status: "started",
            usage: { input_tokens: 30 },
          }),
        ],
        artifacts: [],
        pause: null,
        unresolved_effects: [],
        composition: null,
        diagnostics: [],
        action_in_flight: false,
      },
    ],
  ]);
  for (const run of runs.slice(2)) {
    projections.set(run.run_id, {
      run,
      usage: { input_tokens: 10, output_tokens: 5, requests: 1, source: "per_response" },
      timeline: [
        row(`${run.run_id}-request`, `${run.display_label} request`, run.started_at, {
          finished_at: run.finished_at,
          duration_ms: run.duration_ms,
          usage: { input_tokens: 10, output_tokens: 5 },
        }),
      ],
      artifacts: [],
      pause: null,
      unresolved_effects: [],
      composition: null,
      diagnostics: [],
      action_in_flight: false,
    });
  }
  return {
    runs,
    projections,
    projectionDelays: new Map(),
    counts: { list: 0, projections: new Map(), eventConnections: 0 },
    eventClients: new Set(),
  };
}

function sendJson(response, body, status = 200) {
  const data = JSON.stringify(body);
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(data),
  });
  response.end(data);
}

function contentType(pathname) {
  switch (extname(pathname)) {
    case ".html": return "text/html; charset=utf-8";
    case ".js": return "text/javascript; charset=utf-8";
    case ".css": return "text/css; charset=utf-8";
    case ".svg": return "image/svg+xml";
    default: return "application/octet-stream";
  }
}

async function createMockServer(state) {
  const server = createServer(async (request, response) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    const parts = url.pathname.split("/").filter(Boolean);

    if (url.pathname === "/api/health") {
      sendJson(response, { ok: true, version: "browser-smoke" });
      return;
    }
    if (url.pathname === "/api/runs") {
      state.counts.list += 1;
      sendJson(response, { runs: state.runs, next_cursor: null });
      return;
    }
    if (parts.length === 4 && parts[0] === "api" && parts[1] === "runs" && parts[3] === "events") {
      const runId = decodeURIComponent(parts[2]);
      if (!state.projections.has(runId)) {
        sendJson(response, { error: { code: "NOT_FOUND", message: "unknown run" } }, 404);
        return;
      }
      response.writeHead(200, {
        "content-type": "text/event-stream; charset=utf-8",
        "cache-control": "no-cache",
        connection: "keep-alive",
      });
      response.write(": connected\n\n");
      state.counts.eventConnections += 1;
      state.eventClients.add(response);
      request.on("close", () => state.eventClients.delete(response));
      return;
    }
    if (parts.length === 3 && parts[0] === "api" && parts[1] === "runs") {
      const runId = decodeURIComponent(parts[2]);
      const projection = state.projections.get(runId);
      if (!projection) {
        sendJson(response, { error: { code: "NOT_FOUND", message: "unknown run" } }, 404);
        return;
      }
      state.counts.projections.set(
        runId,
        (state.counts.projections.get(runId) ?? 0) + 1,
      );
      const delay = state.projectionDelays.get(runId) ?? 0;
      if (delay > 0) await wait(delay);
      sendJson(response, projection);
      return;
    }

    const relativePath = url.pathname === "/" ? "index.html" : decodeURIComponent(url.pathname.slice(1));
    const filePath = resolve(staticRoot, relativePath);
    if (filePath !== staticRoot && !filePath.startsWith(`${staticRoot}${sep}`)) {
      response.writeHead(400);
      response.end("bad path");
      return;
    }
    try {
      const file = await readFile(filePath);
      response.writeHead(200, { "content-type": contentType(filePath) });
      response.end(file);
    } catch {
      response.writeHead(404);
      response.end("not found");
    }
  });
  const port = await new Promise((resolvePromise, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolvePromise(server.address().port));
  });
  return { server, port };
}

function sendRunChanged(state) {
  for (const response of state.eventClients) {
    response.write("event: run_changed\ndata: {}\n\n");
  }
}

function closeLiveClients(state) {
  for (const response of [...state.eventClients]) response.end();
  state.eventClients.clear();
}

class CdpClient {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    socket.onmessage = (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id !== undefined) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
        else pending.resolve(message.result);
      }
    };
  }

  call(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolvePromise, reject) => {
      this.pending.set(id, { resolve: resolvePromise, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.socket.close();
  }
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`GET ${url} returned ${response.status}`);
  return response.json();
}

async function waitFor(description, predicate, timeoutMs = 8_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      if (await predicate()) return;
    } catch (error) {
      lastError = error;
    }
    await wait(50);
  }
  throw new Error(`等待失败: ${description}${lastError ? ` (${lastError.message})` : ""}`);
}

async function evaluate(cdp, expression) {
  const result = await cdp.call("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? "browser evaluation failed");
  }
  return result.result?.value;
}

async function clickRun(cdp, runId) {
  const clicked = await evaluate(cdp, `(() => {
    const list = document.querySelector("zuaef-console")?.shadowRoot?.querySelector("zuaef-run-list");
    const row = [...(list?.shadowRoot?.querySelectorAll("zuaef-run-row") ?? [])]
      .find((candidate) => candidate.run?.run_id === ${JSON.stringify(runId)});
    row?.shadowRoot?.querySelector("button")?.click();
    return Boolean(row);
  })()`);
  assert.equal(clicked, true, `browser 中应找到 run ${runId}`);
}

async function overviewSnapshot(cdp) {
  return evaluate(cdp, `(() => {
    const host = document.querySelector("zuaef-console")?.shadowRoot
      ?.querySelector("zuaef-trajectory-view")?.shadowRoot
      ?.querySelector("zuaef-overview-strip");
    const root = host?.shadowRoot;
    return {
      text: root?.textContent ?? "",
      axis: root?.querySelector(".axis")?.textContent?.trim() ?? "",
      labels: [...(root?.querySelectorAll(".bar") ?? [])]
        .map((bar) => bar.getAttribute("aria-label") ?? ""),
      activeLabels: [...(root?.querySelectorAll(".bar.active") ?? [])]
        .map((bar) => bar.getAttribute("aria-label") ?? ""),
      nowline: root?.querySelector(".nowline")?.getAttribute("style") ?? "",
      positions: [...(root?.querySelectorAll(".bar") ?? [])]
        .map((bar) => ({
          label: bar.getAttribute("aria-label") ?? "",
          left: bar.style.left,
        })),
      heights: [...(root?.querySelectorAll(".bar") ?? [])]
        .map((bar) => ({
          label: bar.getAttribute("aria-label") ?? "",
          height: bar.style.height,
        })),
    };
  })()`);
}

async function runTitle(cdp) {
  return evaluate(cdp, `document.querySelector("zuaef-console")?.shadowRoot
    ?.querySelector("zuaef-trajectory-view")?.shadowRoot
    ?.querySelector("h2")?.textContent?.trim() ?? ""`);
}

async function clickOverviewMetric(cdp, label) {
  const clicked = await evaluate(cdp, `(() => {
    const root = document.querySelector("zuaef-console")?.shadowRoot
      ?.querySelector("zuaef-trajectory-view")?.shadowRoot
      ?.querySelector("zuaef-overview-strip")?.shadowRoot;
    const button = [...(root?.querySelectorAll("button.metric") ?? [])]
      .find((candidate) => candidate.textContent?.trim() === ${JSON.stringify(label)});
    button?.click();
    return Boolean(button);
  })()`);
  assert.equal(clicked, true, `overview 中应找到指标 ${label}`);
}

async function connectChrome(url, cdpPort) {
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--remote-debugging-address=127.0.0.1",
    `--remote-debugging-port=${cdpPort}`,
    `--user-data-dir=${await mkdtemp(`${tmpdir()}/zuaef-console-smoke-`)}`,
    url,
  ], { stdio: "ignore" });
  await waitFor("Chrome DevTools endpoint", async () => {
    try {
      return Boolean(await getJson(`http://127.0.0.1:${cdpPort}/json/version`));
    } catch {
      return false;
    }
  }, 15_000);
  const pages = await getJson(`http://127.0.0.1:${cdpPort}/json/list`);
  const page = pages.find((entry) => entry.type === "page");
  if (!page?.webSocketDebuggerUrl) {
    chrome.kill("SIGTERM");
    throw new Error("Chrome 没有可用的 page CDP target");
  }
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolvePromise, reject) => {
    socket.addEventListener("open", resolvePromise, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  const cdp = new CdpClient(socket);
  await cdp.call("Runtime.enable");
  return { chrome, cdp };
}

async function main() {
  const state = createMockState();
  const { server, port } = await createMockServer(state);
  const cdpPort = await freePort();
  let chrome = null;
  let cdp = null;
  try {
    ({ chrome, cdp } = await connectChrome(`http://127.0.0.1:${port}/`, cdpPort));
    await waitFor("Console 初始投影", async () => {
      const snapshot = await overviewSnapshot(cdp);
      return snapshot.labels.length === 1 && snapshot.axis.length > 0;
    });

    const completed = await overviewSnapshot(cdp);
    assert.match(completed.axis, /:/);
    assert.doesNotMatch(completed.axis, /NOW/);
    console.log("✓ 已完成 run 使用完成时间轴，不显示 NOW");

    await clickRun(cdp, "live-run");
    await waitFor("live overview", async () => {
      const snapshot = await overviewSnapshot(cdp);
      return snapshot.activeLabels.length === 1 && /NOW/.test(snapshot.axis);
    });
    const live = await overviewSnapshot(cdp);
    assert.match(live.activeLabels[0], /active request/);
    assert.match(live.nowline, /left:\s*100%/);
    const activePosition = live.positions.find((entry) => /active request/.test(entry.label));
    assert.ok(activePosition && parseFloat(activePosition.left) < 100);
    assert.equal(live.activeLabels.some((label) => /incomplete request/.test(label)), false);
    const incompleteLabel = live.labels.find((label) => /incomplete request/.test(label));
    assert.ok(incompleteLabel?.includes("Unknown"), "incomplete latency 应为 Unknown");
    console.log("✓ started 显示 elapsed/NOW，incomplete 不被当作 live");

    await clickOverviewMetric(cdp, "Output tokens");
    await waitFor("Unknown metric label", async () => {
      const snapshot = await overviewSnapshot(cdp);
      return snapshot.labels.some((label) => /active request/.test(label) && /Unknown/.test(label));
    });
    const outputMetric = await overviewSnapshot(cdp);
    const unknownHeight = outputMetric.heights.find((entry) => /active request/.test(entry.label));
    const knownHeight = outputMetric.heights.find((entry) => /known request/.test(entry.label));
    assert.ok(unknownHeight?.label.includes("Unknown"));
    assert.ok(knownHeight && parseFloat(knownHeight.height) > parseFloat(unknownHeight.height));
    assert.doesNotMatch(unknownHeight.label, /output 0/i);
    const tooltip = await evaluate(cdp, `(() => {
      const root = document.querySelector("zuaef-console")?.shadowRoot
        ?.querySelector("zuaef-trajectory-view")?.shadowRoot
        ?.querySelector("zuaef-overview-strip")?.shadowRoot;
      const bar = [...(root?.querySelectorAll(".bar") ?? [])]
        .find((candidate) => candidate.getAttribute("aria-label")?.includes("active request"));
      bar?.focus();
      return bar?.querySelector(".tip")?.textContent ?? "";
    })()`);
    assert.match(tooltip, /Unknown/);
    console.log("✓ 缺失指标显示 Unknown，且不以 0 污染比例尺");

    await waitFor("live SSE connection", () => state.eventClients.size > 0);
    const beforeList = state.counts.list;
    const beforeProjection = state.counts.projections.get("live-run") ?? 0;
    sendRunChanged(state);
    await waitFor("SSE 单次刷新", () =>
      state.counts.list >= beforeList + 1 &&
      (state.counts.projections.get("live-run") ?? 0) >= beforeProjection + 1,
    );
    await wait(350);
    assert.equal(state.counts.list, beforeList + 1);
    assert.equal(state.counts.projections.get("live-run") ?? 0, beforeProjection + 1);
    console.log("✓ 一次 SSE invalidation 只触发一次 list 和一次 projection fetch");

    state.projectionDelays.set("slow-run", 450);
    state.projectionDelays.set("fast-run", 10);
    await evaluate(cdp, `(() => {
      const list = document.querySelector("zuaef-console")?.shadowRoot?.querySelector("zuaef-run-list");
      for (const runId of ["slow-run", "fast-run"]) {
        const row = [...(list?.shadowRoot?.querySelectorAll("zuaef-run-row") ?? [])]
          .find((candidate) => candidate.run?.run_id === runId);
        row?.shadowRoot?.querySelector("button")?.click();
      }
    })()`);
    await waitFor("最新选择覆盖旧 projection", async () => (await runTitle(cdp)) === "Fast selection");
    await wait(550);
    assert.equal(await runTitle(cdp), "Fast selection");
    console.log("✓ 旧 projection 响应不能覆盖较新的 run 选择");

    await clickRun(cdp, "live-run");
    await waitFor("live retry target", () => state.eventClients.size > 0);
    const beforeReconnects = state.counts.eventConnections;
    closeLiveClients(state);
    await waitFor("live stream error state", async () =>
      evaluate(cdp, `Boolean(document.querySelector("zuaef-console")?.shadowRoot?.querySelector("button.live")?.disabled)`),
    );
    const unavailableLabel = await evaluate(cdp, `document.querySelector("zuaef-console")?.shadowRoot?.querySelector("button.live")?.textContent?.trim() ?? ""`);
    assert.match(unavailableLabel, /live off/i);
    await evaluate(cdp, `document.querySelector("zuaef-console")?.shadowRoot?.querySelector("button.refresh")?.click()`);
    await waitFor("Refresh 恢复 live", async () => {
      const enabled = await evaluate(cdp, `!document.querySelector("zuaef-console")?.shadowRoot?.querySelector("button.live")?.disabled`);
      return enabled && state.counts.eventConnections >= beforeReconnects + 1;
    });
    console.log("✓ live 失败后通过 Refresh 可显式重试并重建 SSE");
  } finally {
    cdp?.close();
    chrome?.kill("SIGTERM");
    await new Promise((resolvePromise) => server.close(resolvePromise));
  }
}

main().catch((error) => {
  console.error(`browser smoke 失败: ${error.stack ?? error}`);
  process.exitCode = 1;
});
