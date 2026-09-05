Read `/home/barry/zuaef-agent/_bmad/render/bmad-build/zuaef-agent-f082b5034e23/18c4e41fa5ea8faba674/review-prompts/edge-case-hunter.md` completely and follow it as your review instructions.

Review content:

diff --git a/.codebase-memory/artifact.json b/.codebase-memory/artifact.json
index a7beb55..3024c66 100644
--- a/.codebase-memory/artifact.json
+++ b/.codebase-memory/artifact.json
@@ -1,11 +1,11 @@
 {
     "schema_version": 2,
-    "commit": "cbb6d54a6798f080f574eeeb828dfd89d1071102",
-    "indexed_at": "2026-09-04T10:46:32Z",
+    "commit": "58142afaa51b56365cb01d31251a2d14c52296c3",
+    "indexed_at": "2026-09-04T14:41:17Z",
     "project": "home-barry-zuaef-agent",
-    "nodes": 13276,
-    "edges": 40672,
-    "original_size": 32047104,
-    "compressed_size": 6159397,
+    "nodes": 0,
+    "edges": 0,
+    "original_size": 102400,
+    "compressed_size": 1468,
     "compression_level": 3
 }
\ No newline at end of file
diff --git a/.codebase-memory/graph.db.zst b/.codebase-memory/graph.db.zst
index bca13ce..804cf56 100644
Binary files a/.codebase-memory/graph.db.zst and b/.codebase-memory/graph.db.zst differ
diff --git a/BUILD_MANIFEST.json b/BUILD_MANIFEST.json
index 90749ac..8db5a6f 100644
--- a/BUILD_MANIFEST.json
+++ b/BUILD_MANIFEST.json
@@ -1548,13 +1548,13 @@
     },
     {
       "path": "plugins/zuaef-quant/zuaef_quant/plugin.py",
-      "bytes": 3512,
-      "sha256": "628d07c5925f63c9394fdf91be3a305ba9c8cd8cb69d69b8a0b656d392797bd9"
+      "bytes": 5709,
+      "sha256": "cfdf85ec925167af4a74264ba03724faa117dcee1be32dbc13ecd8b5c0170035"
     },
     {
       "path": "plugins/zuaef-quant/zuaef_quant/toolset.py",
-      "bytes": 13731,
-      "sha256": "c71b58ac3ad260d38ec563e3babcc87f6aab8010b05f6679dc57f13a1fe2dd4e"
+      "bytes": 19158,
+      "sha256": "5e2f24274c3cb7f884273022e1880dd4ae7e6117e24b007480746873bb1cedaf"
     },
     {
       "path": "plugins/zuaef-telegram/skill/SKILL.md",
@@ -2258,13 +2258,13 @@
     },
     {
       "path": "tests/test_quant_business.py",
-      "bytes": 47238,
-      "sha256": "2c6d2711e07e9289022273de4d3d6c156603d64506046f7fa325542720ea5618"
+      "bytes": 67496,
+      "sha256": "1a7036201563719d9e63c3296e6ba2e476978cec8d95833e7fed3007dd1e91f3"
     },
     {
       "path": "tests/test_quant_plugin.py",
-      "bytes": 11974,
-      "sha256": "ee8c5650c4eeabdd54484858162f31ebc2eb41b5f01a8e1d16fe9a24ba1b6111"
+      "bytes": 19270,
+      "sha256": "c3f0fa53e1d642b12f8ef58213936106adc123b3057908736d75c630db554b8a"
     },
     {
       "path": "tests/test_quant_replay.py",
@@ -2273,8 +2273,8 @@
     },
     {
       "path": "tests/test_quant_trading_monitor.py",
-      "bytes": 15191,
-      "sha256": "2d4b87c696bc2f7a74bd5e206f0b852cdd49bec456e0e290642d621fef243a0d"
+      "bytes": 19063,
+      "sha256": "8154ae01cd73f68798bc888dc9eda96d76d71d522978da752da41bc1b3894e27"
     },
     {
       "path": "tests/test_receipt_store.py",
@@ -2418,8 +2418,8 @@
     },
     {
       "path": "tools/quant_render_business_dashboard.py",
-      "bytes": 68833,
-      "sha256": "f94ec56900e36ad5486c0345e9603faa06afca44ab383ed75b6ccc9edaeab22c"
+      "bytes": 110362,
+      "sha256": "e9a3aa7b2d01f0f5d90d285578449478bc0d9d2b594ae0eb1d157c2ec522fcd3"
     },
     {
       "path": "tools/quant_render_dashboard.py",
@@ -2428,13 +2428,13 @@
     },
     {
       "path": "tools/quant_serve.py",
-      "bytes": 5338,
-      "sha256": "9a60d40f323688bd06f6dcd9d595aa589e57ad2d2d1cb7a76308b93ab4c1bb06"
+      "bytes": 11196,
+      "sha256": "f224843e15bb24099964c72caf4f3bf1949212cee136ec0203283faff3aeae4c"
     },
     {
       "path": "tools/quant_trading_monitor.py",
-      "bytes": 29885,
-      "sha256": "7540f3aa028ee3e57108e4e75c5d8f91354b72804c81fbe229ce961b3d712fc9"
+      "bytes": 33851,
+      "sha256": "5c6ad1248e86ff8410bac4791dd3e88faa3ff3ff14a90c9ee1ee647927bef55d"
     },
     {
       "path": "tools/quant_validate_semantics.py",
diff --git a/docs/quant/README.md b/docs/quant/README.md
index 42dc81f..e08ec69 100644
--- a/docs/quant/README.md
+++ b/docs/quant/README.md
@@ -26,6 +26,24 @@ C Qlib 局限/D-E bug/F 无法解释),**任何 UNEXPLAINED 残留 = P0.5 失败*
 另:评估/审计工具(quant_core/live_scan/anti_leakage/pit_audit/eval_qlib/validate_semantics)随冻结期
 修订同步更新;business/dashboard 快照刷新。日常操作索引见 `workspace/knowledge/concepts/quant-live-ops.md`。
 
+**2026-09-04 增补 · Trading Workbench v0.1 Phase 1(Dashboard 层,T1–T6):**
+`docs/quant/business.html` 升级为 Human-Agent Trading Workbench 第一阶段。① **truth 收敛**:
+`record_trade_outcome`(zuaef-quant toolset)停止写 `workspace/quant/outcomes.jsonl`,改走 canonical
+`quant_trading_monitor.py ack-buy/ack-sell`(LOCAL fact write,无 approval——记录人的既成事实,不下单);
+ack 增加 `--venue`(paper/real,落 position 与 alert)/`--note`;sell 仅全仓平仓(shares 不等于持仓即拒),
+且 venue 必须与持仓一致;新增 `skip` 子命令(HUMAN_SKIP alert + SKIP forward 观察,走既有 settle,
+机会状态机不动)。② **NOW 层**:页面顶部唯一当前事实卡,由 `now_snapshot()`(renderer 内单实现,serve
+经 `/api/quant/now` 共用)投影 durable artifacts——`heartbeat_at`(soak 尾行)与 `last_scan_at`(symbols>0
+的真实扫描)分离;`data_trust`(PASS/FAIL/UNKNOWN,随周期写 state.json)与 `system_unavailable`
+(runtime availability)是两个字段;**STALE 仅在交易时段内、心跳 >90s 时触发**,非时段不按 age 报故障;
+Action Queue 只收 READY/EXIT/SYSTEM_UNAVAILABLE/DATA_UNTRUSTED,每卡区分 RUNTIME/AGENT/HUMAN
+三态,Agent brief 仅当 `recorded_at ≥ 该 symbol 最新 material event` 才匹配,否则显示"尚未复核"。
+③ **Human Action API**:serve 新增 POST `/api/quant/ack-buy|ack-sell|skip`(canonical CLI 薄 adapter,
+缺字段 400,canonical 拒绝原样透传),**写接口 loopback-only**(`--host` 非回环地址即 403)。
+④ Timeline(今日事件时间线)只列 durable alerts;Open Positions 卡含 venue/P&L/Holding D+n;
+页面按 LIVE/TODAY/HISTORICAL/RESEARCH 标注口径。新增工具 `get_trading_context`(只读 canonical
+context)与 `render_quant_business_artifact`(确定性渲染到 `artifacts/quant/delivery/`)。
+Telegram 层(T7–T10)延后。
 ---
 
 ## 目录
diff --git a/docs/quant/business.html b/docs/quant/business.html
index ce2a20b..ce04bb9 100644
--- a/docs/quant/business.html
+++ b/docs/quant/business.html
@@ -10,6 +10,7 @@
   --acc:#4cc2ff; --green:#3fb950; --amber:#d29922; --red:#f85149;
 }
 *{box-sizing:border-box;margin:0;padding:0}
+body{overflow-x:hidden}
 body{background:var(--bg);color:var(--tx);font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,sans-serif;padding:24px 20px 60px}
 .wrap{max-width:1280px;margin:0 auto}
 a{color:var(--acc);text-decoration:none} a:hover{text-decoration:underline}
@@ -53,18 +54,59 @@ tr:last-child td{border-bottom:none}
 .empty .t{font-size:16px;font-weight:700;color:var(--tx);letter-spacing:.5px}
 .empty .s{font-size:12.5px;color:var(--mut);margin-top:6px}
 .question{border-left:3px solid var(--acc);padding:6px 12px;margin-bottom:12px;font-size:13px;color:#b7c2d4}
-.layout-board{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:16px;margin-top:16px;align-items:start}
+.scope{font-size:10px;font-weight:700;letter-spacing:.6px;padding:1px 8px;border-radius:10px;border:1px solid var(--line2);color:var(--dim)}
+.scope.live{color:var(--green);border-color:var(--green)}
+.scope.today{color:var(--acc);border-color:var(--acc)}
+.scope.hist{color:var(--amber);border-color:var(--amber)}
+.scope.research{color:var(--mut)}
+.nowgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
+.nowgrid .n{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
+.nowgrid .n .k{font-size:10.5px;color:var(--dim);letter-spacing:.4px}
+.nowgrid .n .v{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:2px}
+.action-card{border:1px solid var(--line2);border-radius:10px;padding:12px 14px;margin-bottom:10px;background:var(--panel2)}
+.action-card .ac-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
+.action-card .ac-kind{font-size:11px;font-weight:700;letter-spacing:.5px;padding:2px 9px;border-radius:12px}
+.ac-kind.READY{color:#163a22;background:var(--green)}
+.ac-kind.EXIT{color:#3b1110;background:var(--red)}
+.ac-kind.SYSTEM_UNAVAILABLE,.ac-kind.DATA_UNTRUSTED{color:#3b1110;background:var(--red)}
+.ac-kind.NEAR{color:#3a2c0d;background:var(--amber)}
+.threestate{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:12.5px;margin:8px 0}
+.threestate .st-k{color:var(--dim);letter-spacing:.4px;font-size:11px;padding-top:1px}
+.btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
+.btn{font-size:12px;font-weight:600;padding:4px 12px;border-radius:8px;border:1px solid var(--line2);background:var(--panel);color:var(--tx);cursor:pointer}
+.btn:hover{border-color:var(--acc);color:var(--acc)}
+.btn.primary{background:var(--acc);border-color:var(--acc);color:#062a3d}
+.btn.danger{border-color:var(--red);color:var(--red)}
+.tl{list-style:none;font-size:12.5px}
+.tl li{display:flex;gap:10px;padding:3px 0;border-bottom:1px dashed var(--line)}
+.tl li:last-child{border-bottom:none}
+.tl .ts{color:var(--dim);font-variant-numeric:tabular-nums;white-space:nowrap}
+.form-row{display:flex;gap:10px;margin-bottom:8px;align-items:center}
+.form-row label{font-size:12px;color:var(--mut);min-width:90px}
+.form-row input,.form-row select{background:var(--panel2);border:1px solid var(--line2);border-radius:6px;color:var(--tx);padding:5px 8px;font-size:13px;flex:1}
+.form-msg{font-size:12.5px;margin-top:6px;min-height:16px}
+.layout-board{display:block;margin-top:16px}
 .layout-board .card{margin-top:0}
-.note-side{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}
-@media(max-width:1080px){.layout-board{grid-template-columns:1fr}.note-side{position:static;max-height:none}}
+.glossary-toggle{margin-left:auto;white-space:nowrap}
+.drawer-backdrop{position:fixed;inset:0;background:rgba(3,6,10,.66);z-index:60;opacity:0;transition:opacity .2s ease}
+.drawer-backdrop[hidden]{display:none}
+.drawer-backdrop.is-open{opacity:1}
+.drawer{position:fixed;top:0;right:0;width:min(420px,100vw);max-width:100%;height:100vh;height:100dvh;overflow-y:auto;background:var(--panel);border-left:1px solid var(--line2);box-shadow:-18px 0 60px rgba(0,0,0,.45);z-index:61;transform:translateX(100%);transition:transform .2s ease;padding:18px}
+.drawer[hidden]{display:none}
+.drawer.is-open{transform:translateX(0)}
+.drawer-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px}
+.drawer-head h2{font-size:14px;letter-spacing:.3px;color:#b7c2d4;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
+.drawer-head .cnt{font-size:11px;color:var(--dim);font-weight:400}
+.drawer-body{padding-top:14px}
+@media(max-width:480px){.drawer{width:100vw;padding:14px}}
+@media(prefers-reduced-motion:reduce){.drawer,.drawer-backdrop{transition:none}}
 .g-list{display:flex;flex-direction:column;gap:6px}
-.g-item{display:flex;align-items:baseline;gap:8px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font-size:12.5px;background:var(--panel2)}
+.g-item{display:flex;align-items:baseline;gap:8px;width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:12.5px;text-align:left;color:var(--tx);background:var(--panel2);cursor:pointer}
 .g-item:hover{border-color:var(--acc)}
 .g-item .gk{font-weight:700;color:var(--acc);white-space:nowrap}
-.g-item .g1{color:var(--mut);font-size:11.5px;line-height:1.45}
+.g-item .g1{min-width:0;color:var(--mut);font-size:11.5px;line-height:1.45;overflow-wrap:anywhere}
 [data-m]{cursor:help}
-.g-item{cursor:pointer}
-.modal{position:fixed;inset:0;background:rgba(3,6,10,.66);display:flex;align-items:flex-start;justify-content:center;padding:6vh 16px;z-index:50;backdrop-filter:blur(2px)}
+.modal{position:fixed;inset:0;background:rgba(3,6,10,.66);display:flex;align-items:flex-start;justify-content:center;padding:6vh 16px;z-index:70;backdrop-filter:blur(2px)}
 .modal[hidden]{display:none}
 .modal-box{background:var(--panel);border:1px solid var(--line2);border-radius:14px;max-width:640px;width:100%;max-height:82vh;overflow:auto;box-shadow:0 18px 60px rgba(0,0,0,.5)}
 .modal-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel)}
@@ -97,53 +139,88 @@ footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(
   <div class="banner-warn" id="strategy-warning"></div>
   <div class="banner-degraded" id="dq-banner" style="display:none"></div>
 
+  <div class="card" id="now-card">
+    <h2>NOW <span class="scope live">LIVE</span> <span class="cnt" id="now-meta"></span></h2>
+    <div class="nowgrid" id="now-grid"></div>
+    <div id="now-stale" class="banner-degraded" style="display:none;margin-top:10px"></div>
+  </div>
+
   <div class="card" id="attention-card">
-    <h2>现在需要我做什么？ <span class="cnt" id="att-meta">交易盯盘 · 30s 自动刷新</span></h2>
+    <h2>现在需要我做什么？ <span class="scope live">LIVE</span> <span class="cnt" id="att-meta">交易盯盘 · 30s 自动刷新</span></h2>
     <div id="att-status" style="font-weight:700;font-size:14px;margin-bottom:8px"></div>
+    <div id="att-actions"></div>
     <div id="att-items" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px"></div>
     <div style="display:flex;gap:24px;flex-wrap:wrap">
       <div style="flex:1;min-width:260px">
-        <div class="mut" style="font-weight:600;margin-bottom:4px">今天盯什么（READY / NEAR）</div>
+        <div class="mut" style="font-weight:600;margin-bottom:4px">次级 Watch（NEAR — 未到行动级）</div>
         <div id="att-watch" class="mut"></div>
       </div>
-      <div style="flex:1.4;min-width:300px">
-        <div class="mut" style="font-weight:600;margin-bottom:4px">我现在持有什么</div>
-        <div id="att-positions" class="mut"></div>
-      </div>
     </div>
     <div id="att-alerts" style="margin-top:8px;font-size:12px"></div>
   </div>
 
+  <div class="card" id="positions-card">
+    <h2>Open Positions <span class="scope live">LIVE</span> <span class="cnt">持仓生命周期独立于候选池 · 只由 ack 建立/关闭</span></h2>
+    <div id="att-positions-box"></div>
+  </div>
+
+  <div class="card" id="timeline-card">
+    <h2>今日事件时间线 <span class="scope live">LIVE</span> <span class="cnt" id="tl-meta">durable alerts · 只列真实持久化事件</span></h2>
+    <ul class="tl" id="tl-list"></ul>
+  </div>
+
+  <div class="card" id="real-trend-card">
+    <h2>真实运行数据趋势 <span class="scope live">LIVE · HISTORICAL</span> <span class="cnt" id="rt-meta">M1 trading artifacts · 缺失保持缺失, 不补曲线</span></h2>
+    <dl class="kv" id="m1-evidence" style="margin-bottom:10px"></dl>
+    <div id="rt-chart"></div>
+    <div id="rt-forward" style="margin-top:10px;font-size:13px"></div>
+    <div id="rt-diagnostic" style="margin-top:12px"></div>
+    <div class="mut" style="font-weight:600;margin:12px 0 4px;font-size:12px">真实 monitor 记录（trading/soak.jsonl · 一行 = 一次真实周期, 不去失真）</div>
+    <div style="overflow-x:auto"><table>
+      <thead><tr><th>时间</th><th>状态</th><th class="num-h">扫描数量</th><th class="num-h">universe size</th><th class="num-h">告警/事件数</th><th>来源</th></tr></thead>
+      <tbody id="rt-rows"></tbody>
+    </table></div>
+  </div>
+
   <div class="kpi">
     <div class="k"><div class="v" id="kpi-decision">—</div><div class="l">今日决策</div></div>
     <div class="k"><div class="v" id="kpi-triggers">—</div><div class="l">实时触发</div></div>
     <div class="k"><div class="v" id="kpi-candidates">—</div><div class="l">活跃候选</div></div>
-    <div class="k"><div class="v" id="kpi-settled">—</div><div class="l">前向已结算交易</div></div>
+    <div class="k"><div class="v" id="kpi-settled">—</div><div class="l">前向已结算交易（正式）</div></div>
     <div class="k"><div class="v" id="kpi-evidence">—</div><div class="l">策略证据</div></div>
   </div>
 
   <div class="card">
-    <h2>今日动作候选 <span class="cnt" id="scan-meta"></span></h2>
+    <h2>今日动作候选 <span class="scope today">TODAY · LIVE</span> <span class="cnt" id="scan-meta"></span></h2>
     <div id="trigger-box"></div>
   </div>
 
   <div class="layout-board">
   <div class="card">
-    <h2>价值 · 质量机会板 <span class="cnt" id="board-meta"></span></h2>
+    <h2>价值 · 质量机会板 <span class="scope today">TODAY</span> <span class="cnt" id="board-meta"></span>
+      <button class="btn glossary-toggle" id="glossary-open" type="button" aria-expanded="false" aria-controls="glossary-drawer">查看指标备注</button>
+    </h2>
     <div style="overflow-x:auto"><table id="board">
       <thead><tr id="board-head"></tr></thead>
       <tbody id="board-rows"></tbody>
     </table></div>
     <div class="mut" style="font-size:11.5px;margin-top:8px" id="not-a-buy"></div>
   </div>
-  <aside class="card note-side">
-    <h2>指标备注 <span class="cnt">点击任一指标 / 单元格弹出详细说明</span></h2>
-    <div class="g-list" id="glossary-list"></div>
-  </aside>
   </div>
 
+  <div class="drawer-backdrop" id="glossary-backdrop" hidden></div>
+  <aside class="drawer" id="glossary-drawer" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="glossary-title">
+    <div class="drawer-head">
+      <h2 id="glossary-title">指标备注 <span class="cnt">点击任一指标 / 单元格弹出详细说明</span></h2>
+      <button class="modal-x" id="glossary-close" type="button" title="关闭" aria-label="关闭指标备注">×</button>
+    </div>
+    <div class="drawer-body">
+      <div class="g-list" id="glossary-list"></div>
+    </div>
+  </aside>
+
   <div class="card">
-    <h2>历史持仓 · 套牢仓位 <span class="cnt" id="legacy-count">自选/持仓名单 — 诊断位, 不是机会宇宙</span></h2>
+    <h2>历史持仓 · 套牢仓位 <span class="scope hist">HISTORICAL</span> <span class="cnt" id="legacy-count">自选/持仓名单 — 诊断位, 不是机会宇宙</span></h2>
     <div class="mut question" id="legacy-question"></div>
     <div style="overflow-x:auto"><table>
       <thead><tr><th>代码</th><th>名称</th><th>现价</th><th>综合分</th><th>价值</th><th>质量</th><th>Timing</th>
@@ -154,7 +231,7 @@ footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(
 
   <div class="grid two">
     <div class="card">
-      <h2>策略证据</h2>
+      <h2>策略证据 <span class="scope research">RESEARCH · frozen S3</span></h2>
       <div id="strategy-box"></div>
       <details style="margin-top:12px">
         <summary>策略实验历史 (基线 / S1 / S2 / S3)</summary>
@@ -165,17 +242,19 @@ footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(
       </details>
     </div>
     <div class="card">
-      <h2>前向证据 <span class="cnt">只有真实前向观察, 无合成占位</span></h2>
+      <h2>前向证据 <span class="scope research">RESEARCH · FORMAL</span> <span class="cnt">正式 = trading/forward.json · 无合成占位</span></h2>
+      <div id="formal-forward" style="font-size:13px;margin-bottom:10px"></div>
+      <div class="mut" style="font-weight:600;font-size:12px;margin-bottom:4px">历史每日扫描日志（旧每日链路口径 — 仅历史兼容, 非当前 M1 truth）</div>
       <table>
         <thead><tr><th>日期</th><th>时间</th><th style="text-align:right">扫描只数</th><th style="text-align:right">触发数</th><th>决策</th><th>备注</th></tr></thead>
         <tbody id="obs-rows"></tbody>
       </table>
-      <div class="mut" style="font-size:11.5px;margin-top:8px">入场 / D+1 / D+3 / D+5 / D+8 价格路径与最大有利·不利偏移 (MFE/MAE) 在人工结算产生真实记录后展示; 当前结算笔数见 Forward Settled Trades。</div>
+      <div class="mut" style="font-size:11.5px;margin-top:8px">入场 / D+1 / D+3 / D+5 / D+8 价格路径与最大有利·不利偏移 (MFE/MAE) 在正式 forward observation 产生后展示；诊断性记录只出现在「真实运行数据趋势」卡并明确标记 diagnostic。</div>
     </div>
   </div>
 
   <div class="card">
-    <h2>数据质量</h2>
+    <h2>数据质量 <span class="scope today">TODAY</span></h2>
     <div id="dq-box"></div>
   </div>
 
@@ -185,6 +264,21 @@ footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(
     <a href="/engineering">工程 / 审计 → /engineering</a>。
   </footer>
 </div>
+<div class="modal" id="trade-modal" hidden>
+  <div class="modal-box" style="max-width:480px">
+    <div class="modal-head"><h3 id="tm-title"></h3><button class="modal-x" id="tm-close" title="关闭">×</button></div>
+    <div class="modal-body">
+      <div class="form-row"><label>symbol</label><input id="tm-symbol" readonly></div>
+      <div class="form-row"><label>shares</label><input id="tm-shares" type="number" min="1" step="1"></div>
+      <div class="form-row"><label>price</label><input id="tm-price" type="number" min="0.0001" step="0.0001"></div>
+      <div class="form-row"><label>venue</label><select id="tm-venue"><option value="paper">paper</option><option value="real">real</option></select></div>
+      <div class="form-row"><label>executed_at</label><input id="tm-time"></div>
+      <div class="form-row"><label>note</label><input id="tm-note" placeholder="可选备注"></div>
+      <div class="form-msg" id="tm-msg"></div>
+      <div class="btnrow"><button class="btn primary" id="tm-submit">确认记录</button></div>
+    </div>
+  </div>
+</div>
 <div class="modal" id="metric-modal" hidden>
   <div class="modal-box">
     <div class="modal-head"><h3 id="mm-title"></h3><button class="modal-x" id="mm-close" title="关闭">×</button></div>
@@ -193,14 +287,14 @@ footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(
 </div>
 <script>
 window.DASH = {
- "generated_at": "2026-09-03 12:19 UTC",
+ "generated_at": "2026-09-04 14:39 UTC",
  "warning": "历史 S3 证据薄弱;盈利能力仍未证明 (NOT YET)。",
  "not_a_buy_note": "候选排名只是研究关注度的排序,不是买入建议;实际动作仍需确定性实时触发加人工决策。盈利能力仍未证明。",
  "trading": {
   "present": true,
   "state": {
-   "as_of": "2026-09-03T18:26:31.810405+08:00",
-   "day": "2026-09-03",
+   "as_of": "2026-09-04T19:10:35.702555+08:00",
+   "day": "2026-09-04",
    "status": "MARKET_CLOSED",
    "symbols_scanned": 0,
    "attention_items": 0,
@@ -216,15 +310,134 @@ window.DASH = {
   "open_positions": [],
   "alerts": []
  },
+ "now": {
+  "generated_at": "2026-09-04T22:39:19+08:00",
+  "present": true,
+  "as_of": "2026-09-04T19:10:35.702555+08:00",
+  "day": "2026-09-04",
+  "status": "MARKET_CLOSED",
+  "market": "CLOSED",
+  "expected_live": false,
+  "runtime": "HEALTHY",
+  "stale": false,
+  "heartbeat_at": "2026-09-04T19:10:35+08:00",
+  "heartbeat_age_seconds": 12524,
+  "last_scan_at": null,
+  "scan_age_seconds": null,
+  "symbols_scanned": 0,
+  "universe_size": 50,
+  "data_trust": "UNKNOWN",
+  "ready": [],
+  "near": [],
+  "exit_alerts": [],
+  "positions": [],
+  "attention": [],
+  "recent_alerts": []
+ },
+ "timeline": [],
+ "real_trend": {
+  "points": [
+   {
+    "ts": "2026-09-03T17:17:39+08:00",
+    "status": "MARKET_CLOSED",
+    "symbols_scanned": 0,
+    "universe_size": 50,
+    "events": 0,
+    "source": "trading/soak.jsonl"
+   },
+   {
+    "ts": "2026-09-03T17:18:24+08:00",
+    "status": "MARKET_CLOSED",
+    "symbols_scanned": 0,
+    "universe_size": 50,
+    "events": 0,
+    "source": "trading/soak.jsonl"
+   },
+   {
+    "ts": "2026-09-03T17:19:09+08:00",
+    "status": "MARKET_CLOSED",
+    "symbols_scanned": 0,
+    "universe_size": 50,
+    "events": 0,
+    "source": "trading/soak.jsonl"
+   },
+   {
+    "ts": "2026-09-03T17:19:54+08:00",
+    "status": "MARKET_CLOSED",
+    "symbols_scanned": 0,
+    "universe_size": 50,
+    "events": 0,
+    "source": "trading/soak.jsonl"
+   },
+   {
+    "ts": "2026-09-04T19:10:35+08:00",
+    "status": "MARKET_CLOSED",
+    "symbols_scanned": 0,
+    "universe_size": 50,
+    "events": 0,
+    "source": "trading/soak.jsonl"
+   }
+  ],
+  "record_count": 5,
+  "universe_size": 50,
+  "forward": {
+   "present": true,
+   "count": 0,
+   "settled": 0
+  },
+  "m1_evidence": {
+   "market_data_valid": {
+    "ok": true,
+    "detail": "最新 semantic proof 2026-09-04T19:09:35.981218+08:00 · all 50 sampled symbols cache canonical share volume under current cache contracts; same-date quote health PASS: 50 same-date cross-check(s) consistent; 0 not aligned today"
+   },
+   "single_scan_valid": {
+    "ok": true,
+    "detail": "单次全宇宙报价核验 50/50 (2026-09-04T19:09:35.981218+08:00) — 单次验证, 不是连续监控"
+   },
+   "continuous_monitoring": {
+    "ok": false,
+    "detail": "soak 真实记录 5 条, 其中盘中有效扫描 0 条 — 连续实时监控未证明"
+   },
+   "formal_forward_count": 0,
+   "formal_forward_settled": 0,
+   "verdict": "PARTIAL"
+  },
+  "diagnostic_rows": [
+   {
+    "kind": "diagnostic",
+    "symbol": "600015",
+    "day": "2026-09-03",
+    "state": "NEAR",
+    "ref_price": 6.27,
+    "pullback_5d": -0.0529,
+    "volume_ratio_20d": 1.462,
+    "source": "trading-diagnostic/alerts.jsonl",
+    "d1_day": "2026-09-04",
+    "d1": 0.007974
+   },
+   {
+    "kind": "diagnostic",
+    "symbol": "601799",
+    "day": "2026-09-03",
+    "state": "NEAR",
+    "ref_price": 74.88,
+    "pullback_5d": -0.0853,
+    "volume_ratio_20d": 2.204,
+    "source": "trading-diagnostic/alerts.jsonl",
+    "d1_day": "2026-09-04",
+    "d1": 0.019231
+   }
+  ]
+ },
  "kpi": {
-  "today_decision": "NO_TRADE",
+  "today_decision": "NOT_RUN_TODAY",
   "live_triggers": 0,
   "active_candidates": 50,
   "forward_settled_trades": 0,
   "strategy_evidence": "UNPROVEN"
  },
  "decision": {
-  "state": "NO_TRADE",
+  "state": "NOT_RUN_TODAY",
   "action": "NO_TRADE",
   "last_run_day": "2026-09-03",
   "brief": {
@@ -1671,7 +1884,7 @@ window.DASH = {
   "best_annualized_pct": 0.3653,
   "best_trades": 29,
   "pit_bias": true,
-  "forward_triggers": 0,
+  "forward_observations": 0,
   "forward_settled": 0,
   "forward_hit_rate": "—",
   "results": [
@@ -1737,12 +1950,12 @@ window.DASH = {
     "detail": "必要字段覆盖率 100%"
    },
    "freshness": {
-    "status": "PASS",
-    "detail": "行情与财报/估值均为最新"
+    "status": "WARN",
+    "detail": "行情非今日 (20260903)"
    },
    "semantic_integrity": {
     "status": "PASS",
-    "detail": "all 50 sampled symbols cache canonical share volume under current cache contracts; same-date quote health PASS: 47 same-date cross-check(s) consistent; 3 not aligned today"
+    "detail": "all 50 sampled symbols cache canonical share volume under current cache contracts; same-date quote health PASS: 50 same-date cross-check(s) consistent; 0 not aligned today"
    },
    "source_degradation": {
     "status": "PASS",
@@ -1762,7 +1975,7 @@ window.DASH = {
   "quotes_source": "qt.gtimg.cn batch quote (Tencent)",
   "concentration": "enforced",
   "degradations": [],
-  "banner": "数据质量分维未全绿: pit=FAIL"
+  "banner": "数据质量分维未全绿: freshness=WARN; pit=FAIL"
  },
  "anti_leakage": {
   "verdict": "P0_4_SCOPED_PASS"
@@ -1818,15 +2031,44 @@ function closeMetric(){
   $('metric-modal').hidden = true;
 }
 function renderGlossary(){
-  $('glossary-list').innerHTML = Object.entries(GLOSSARY).map(([k,g])=>`<div class="g-item" data-m="${esc(k)}" title="点击查看 ${esc(g.t)} 的详细说明"><span class="gk">${esc(g.t)}</span><span class="g1">${esc(g.h||'')}</span></div>`).join('');
+  $('glossary-list').innerHTML = Object.entries(GLOSSARY).map(([k,g])=>`<button type="button" class="g-item" data-m="${esc(k)}" title="点击查看 ${esc(g.t)} 的详细说明"><span class="gk">${esc(g.t)}</span><span class="g1">${esc(g.h||'')}</span></button>`).join('');
 }
+function setGlossaryOpen(open){
+  const trigger = $('glossary-open');
+  const drawer = $('glossary-drawer');
+  const backdrop = $('glossary-backdrop');
+  if(!trigger || !drawer || !backdrop) return;
+  trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
+  drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
+  if(open){
+    drawer.hidden = false;
+    backdrop.hidden = false;
+    drawer.classList.add('is-open');
+    backdrop.classList.add('is-open');
+    $('glossary-close').focus();
+  } else {
+    drawer.classList.remove('is-open');
+    backdrop.classList.remove('is-open');
+    drawer.hidden = true;
+    backdrop.hidden = true;
+    trigger.focus();
+  }
+}
+function openGlossary(){ setGlossaryOpen(true); }
+function closeGlossary(){ setGlossaryOpen(false); }
 document.addEventListener('click', (e)=>{
   const el = e.target.closest('[data-m]');
   if(el){ openMetric(el.dataset.m); return; }
+  if(e.target.id === 'glossary-open'){ openGlossary(); return; }
+  if(e.target.id === 'glossary-close' || e.target.id === 'glossary-backdrop'){ closeGlossary(); return; }
   if(e.target.id === 'mm-close'){ closeMetric(); return; }
   if(e.target.closest('#metric-modal') && !e.target.closest('.modal-box')){ closeMetric(); }
 });
-document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') closeMetric(); });
+document.addEventListener('keydown', (e)=>{
+  if(e.key !== 'Escape') return;
+  if(!$('glossary-drawer').hidden){ closeGlossary(); return; }
+  closeMetric();
+});
 
 function kpiColor(v){ return v==null ? 'var(--dim)' : 'var(--tx)'; }
 
@@ -1854,43 +2096,370 @@ function drawTriggers(trs, live){
       <td class="rf">${(t.red_flags&&t.red_flags.length)?esc(zhFlags(t.red_flags)):'无候选红旗记录'}</td></tr>`).join('')}</tbody></table></div>`;
 }
 
-function renderTrading(t){
-  const st = $('att-status'), items = $('att-items'), watch = $('att-watch'), pos = $('att-positions'), al = $('att-alerts');
-  if(!t || !t.present){
-    st.textContent = '盯盘监控未运行 — 启动: python tools/quant_trading_monitor.py session';
-    st.style.color = 'var(--amber)'; items.innerHTML=''; watch.textContent='—'; pos.textContent='无持仓记录'; al.innerHTML=''; return;
+/* ---- NOW / Action Queue / Positions: single fact = /api/quant/now ---- */
+const fmtAge = (s) => s==null ? '—' : (s < 90 ? s+'s' : Math.floor(s/60)+'m'+(s%60)+'s');
+const nowTs = (v) => v ? String(v).slice(11,19) : '—';
+let lastNow = null;
+
+function renderNow(n){
+  lastNow = n || lastNow;
+  n = n || {};
+  const grid = $('now-grid'), st = $('now-stale');
+  $('now-meta').textContent = n.present
+    ? `as_of ${nowTs(n.as_of)} · generated ${nowTs(n.generated_at)}`
+    : 'monitor 尚未运行 — 无 NOW 事实';
+  if(!n.present){
+    grid.innerHTML = '<div class="n"><div class="k">Runtime</div><div class="v" style="color:var(--amber)">UNKNOWN</div></div>' +
+      '<div class="n"><div class="k">说明</div><div class="v" style="font-size:12px">启动: python tools/quant_trading_monitor.py session</div></div>';
+    st.style.display = 'none';
+    renderAttention(n);
+    return;
+  }
+  const cov = (n.symbols_scanned!=null && n.universe_size) ? `${n.symbols_scanned}/${n.universe_size}`
+            : (n.universe_size ? `—/${n.universe_size}` : '—');
+  const cells = [
+    ['市场', n.market, n.market==='OPEN'?'var(--green)':'var(--mut)'],
+    ['Runtime', n.runtime, n.runtime==='HEALTHY'?'var(--green)':(n.runtime==='STALE'?'var(--red)':'var(--amber)')],
+    ['交易时段', n.expected_live?'ACTIVE':'CLOSED', n.expected_live?'var(--green)':'var(--mut)'],
+    ['最后心跳', `${nowTs(n.heartbeat_at)} · age ${fmtAge(n.heartbeat_age_seconds)}`],
+    ['最后成功扫描', n.last_scan_at ? `${nowTs(n.last_scan_at)} · age ${fmtAge(n.scan_age_seconds)}` : '无真实扫描记录'],
+    ['扫描覆盖', cov],
+    ['Data trust', n.data_trust, n.data_trust==='PASS'?'var(--green)':(n.data_trust==='FAIL'?'var(--red)':'var(--amber)')],
+    ['READY', (n.ready||[]).length, (n.ready||[]).length?'var(--green)':null],
+    ['NEAR', (n.near||[]).length, null],
+    ['EXIT', (n.exit_alerts||[]).length, (n.exit_alerts||[]).length?'var(--red)':null],
+    ['Open positions', (n.positions||[]).length, null],
+  ];
+  grid.innerHTML = cells.map(([k,v,c])=>
+    `<div class="n"><div class="k">${esc(k)}</div><div class="v"${c?` style="color:${c}"`:''}>${esc(String(v??'—'))}</div></div>`).join('');
+  // STALE fires only while the session clock expects a live loop (server-side rule)
+  if(n.stale){
+    st.className = 'banner-degraded'; st.style.display = 'block';
+    st.textContent = `RUNTIME STALE — 交易时段内心跳超龄 (>90s) · Last success ${nowTs(n.heartbeat_at)} · Age ${fmtAge(n.heartbeat_age_seconds)}`;
+  } else if(!n.expected_live){
+    st.className = ''; st.style.display = 'block';
+    st.style.cssText = 'display:block;margin-top:10px;color:var(--dim);font-size:12px';
+    st.textContent = '非交易时段 — 显示最后心跳 / 最后成功扫描，不按心跳 age 报故障';
+  } else {
+    st.style.display = 'none';
+  }
+  renderAttention(n);
+}
+
+function renderAttention(n){
+  const statusEl = $('att-status');
+  const state = n || {};
+  if(!state.present){
+    statusEl.textContent = '盯盘监控未运行 — 启动: python tools/quant_trading_monitor.py session';
+    statusEl.style.color = 'var(--amber)';
+  } else if(state.status === 'SYSTEM_UNAVAILABLE'){
+    statusEl.textContent = 'SYSTEM_UNAVAILABLE — 系统不可用/数据不可信（这不是 NO_TRADE）';
+    statusEl.style.color = 'var(--red)';
+  } else if(state.data_trust === 'FAIL'){
+    statusEl.textContent = 'DATA_UNTRUSTED — semantic gate fail-closed，触发条件被抑制（这与系统失联是两回事）';
+    statusEl.style.color = 'var(--red)';
+  } else if((state.ready||[]).length || (state.exit_alerts||[]).length){
+    statusEl.textContent = `需要行动 — READY ${(state.ready||[]).length} · EXIT ${(state.exit_alerts||[]).length}`;
+    statusEl.style.color = 'var(--amber)';
+  } else if(state.status === 'MARKET_CLOSED'){
+    statusEl.textContent = '已收盘 — 监控待下一交易时段（无合成活动）';
+    statusEl.style.color = 'var(--mut)';
+  } else {
+    statusEl.textContent = '有效扫描 · 无机会 — 市场已扫描，当前无 READY/EXIT';
+    statusEl.style.color = 'var(--acc)';
+  }
+  const items = state.attention || [];
+  $('att-actions').innerHTML = items.length ? items.map(actionCardHTML).join('')
+    : '<div class="mut" style="font-size:12.5px;margin-bottom:8px">当前无需要行动的事项（无 READY / EXIT / 系统事件）</div>';
+  const near = state.near || [];
+  $('att-watch').textContent = near.length ? near.join(', ') : '当前无 NEAR';
+  const alerts = state.recent_alerts || [];
+  $('att-alerts').innerHTML = alerts.length ? alerts.slice().reverse().slice(0,5).map(a=>
+    `<div>· <b>${esc(a.type||'')}</b> ${a.symbol?esc(a.symbol)+' — ':''}${esc(a.what||'')}${a.why?` · ${esc(a.why)}`:''}</div>`).join('') : '';
+}
+
+const agentState = (a) => a
+  ? `<span class="chip B">${esc(a.action||'?')}</span> <span class="dim">${esc(a.decision_id||'')}</span>${a.why?`<div class="mut" style="font-size:12px">为什么: ${esc(a.why)}</div>`:''}${a.invalidation?`<div class="mut" style="font-size:12px">失效: ${esc(a.invalidation)}</div>`:''}`
+  : '<span class="chip gray">尚未复核</span> <span class="dim">没有晚于本事件的 Agent brief</span>';
+const humanState = (h) => h
+  ? `<span class="chip NEAR">${esc(h.action||'?')}</span>${h.venue?` <span class="dim">venue ${esc(h.venue)}</span>`:''}${h.note?` <span class="dim">· ${esc(h.note)}</span>`:''} <span class="dim">${nowTs(h.ts)}</span>`
+  : '<span class="dim">NO ACTION YET</span>';
+
+function actionCardHTML(it){
+  const head = `<div class="ac-head">
+    <span class="ac-kind ${esc(it.kind)}">${esc(it.kind)}</span>
+    ${it.symbol?`<code>${esc(it.symbol)}</code>`:''}
+    ${it.price!=null?`<span class="num">${fmt(it.price)}</span>`:''}
+    <span class="dim">${nowTs(it.ts)}</span>
+    ${it.entry_price!=null?`<span class="dim">entry ${fmt(it.entry_price)}</span>`:''}
+    ${it.pnl!=null?`<span class="num">P&L ${fmt(it.pnl)}</span>`:''}
+    ${it.venue?`<span class="chip gray">${esc(it.venue)}</span>`:''}
+  </div>`;
+  let runtime = '', btns = '';
+  if(it.kind === 'READY'){
+    const c = it.conditions || {};
+    runtime = `<div class="mut" style="font-size:12.5px">Deterministic: pullback ${fmt(c.pullback_5d!=null?c.pullback_5d*100:null,2)}% · 量比 ${fmt(c.volume_ratio_20d)} · 1d strength ${fmt(c.strength_1d)} — 冻结入场条件全部成立</div>`;
+    btns = [['ack-buy','Paper Buy','paper','primary'],['ack-buy','Record Real Buy','real','danger'],['skip','Skip',null,''],
+            ['ask','Ask Agent',null,''],['keep','Keep Watching',null,'']];
+  } else if(it.kind === 'EXIT'){
+    runtime = `<div class="mut" style="font-size:12.5px">触发: ${esc(it.why||'冻结退出规则')}</div>`;
+    btns = [['ack-sell','Paper Sell','paper','primary'],['ack-sell','Record Real Sell','real','danger'],['ask','Ask Agent',null,'']];
+  } else {
+    runtime = `<div class="mut" style="font-size:12.5px">${esc(it.why||'系统级事件 — 需要人知晓')}</div>`;
+  }
+  const btnHTML = btns.map(([k,label,venue,cls]) =>
+    `<button class="btn ${cls}" data-act="${k}" data-symbol="${esc(it.symbol||'')}" ${venue?`data-venue="${venue}"`:''}
+      data-shares="${esc((lastNow&&((lastNow.positions||[]).find(p=>p.symbol===it.symbol))||{}).shares??'')}"
+      data-price="${esc(it.price??'')}">${esc(label)}</button>`).join('');
+  return `<div class="action-card" data-kind="${esc(it.kind)}" data-symbol="${esc(it.symbol||'')}">${head}
+    ${runtime}
+    <div class="threestate">
+      <span class="st-k">RUNTIME</span><span>${esc(it.kind)}</span>
+      <span class="st-k">AGENT</span><span>${agentState(it.agent)}</span>
+      <span class="st-k">HUMAN</span><span>${humanState(it.human)}</span>
+    </div>
+    <div class="btnrow">${btnHTML}</div>
+  </div>`;
+}
+
+/* ---- Open Positions ---- */
+function renderPositions(positions){
+  const box = $('att-positions-box');
+  if(!positions || !positions.length){
+    box.innerHTML = '<div class="mut" style="font-size:12.5px">无持仓记录 — Position 只由用户 ack-buy 建立</div>';
+    return;
+  }
+  box.innerHTML = positions.map(p=>{
+    const days = p.entry_date ? Math.max(0, Math.floor((Date.now() - Date.parse(p.entry_date)) / 86400000)) : null;
+    return `<div class="action-card"><div class="ac-head">
+      <code>${esc(p.symbol)}</code><span class="chip gray">${esc(p.venue||'paper')}</span>
+      <span class="num">${fmt(p.shares,0)}股</span>
+      <span class="dim">entry ${fmt(p.entry_price)}</span>
+      ${p.price!=null?`<span class="num">现价 ${fmt(p.price)}</span>`:''}
+      ${p.pnl!=null?`<span class="num" style="color:${p.pnl>=0?'var(--green)':'var(--red)'}">P&L ${fmt(p.pnl)}</span>`:''}
+      ${days!=null?`<span class="dim">Holding D+${days}</span>`:''}
+      <span class="chip ${p.state==='EXIT_ALERT'?'EXIT':'gray'}">${esc(p.state||'?')}</span>
+    </div>
+    ${p.exit_reason?`<div class="rf">exit_rule: ${esc(p.exit_reason)}</div>`:''}
+    <div class="btnrow">
+      <button class="btn primary" data-act="ack-sell" data-symbol="${esc(p.symbol)}" data-venue="${esc(p.venue||'paper')}" data-shares="${esc(p.shares)}" data-price="${esc(p.price??'')}">Paper Sell</button>
+      <button class="btn danger" data-act="ack-sell" data-symbol="${esc(p.symbol)}" data-venue="real" data-shares="${esc(p.shares)}" data-price="${esc(p.price??'')}">Record Real Sell</button>
+      <button class="btn" data-act="ask" data-symbol="${esc(p.symbol)}">Ask Agent</button>
+    </div></div>`;
+  }).join('');
+}
+
+/* ---- trade modal (canonical ack POST; the server never invents fields) ---- */
+let tmKind = 'ack-buy';
+function openTrade(kind, symbol, venue, shares, price){
+  tmKind = kind;
+  $('tm-title').textContent = kind === 'skip' ? '记录 SKIP 决定' : (kind === 'ack-buy' ? `记录买入 — ${symbol||''}` : `记录卖出（全仓平仓）— ${symbol||''}`);
+  $('tm-symbol').value = symbol || '';
+  $('tm-shares').value = shares || '';
+  $('tm-shares').parentElement.style.display = kind === 'skip' ? 'none' : '';
+  $('tm-price').value = price || '';
+  if(venue) $('tm-venue').value = venue;
+  $('tm-venue').parentElement.style.display = kind === 'skip' ? 'none' : '';
+  $('tm-time').value = new Date().toISOString();
+  $('tm-note').value = '';
+  $('tm-msg').textContent = '';
+  $('tm-msg').style.color = '';
+  $('trade-modal').hidden = false;
+}
+async function submitTrade(){
+  const payload = {
+    symbol: $('tm-symbol').value.trim(),
+    executed_at: $('tm-time').value.trim(),
+    note: $('tm-note').value.trim(),
+  };
+  if(tmKind === 'skip'){
+    payload.price = parseFloat($('tm-price').value);
+  } else {
+    payload.shares = parseInt($('tm-shares').value, 10);
+    payload.price = parseFloat($('tm-price').value);
+    payload.venue = $('tm-venue').value;
   }
-  const s = t.state || {};
-  if (s.system_unavailable){ st.textContent = 'SYSTEM_UNAVAILABLE — 系统不可用/数据不可信（这不是 NO_TRADE）'; st.style.color = 'var(--red)'; }
-  else if (s.market_no_trade){ st.textContent = `有效 NO_TRADE — 市场已扫描 ${(s.symbols_scanned??0)} 只，当前无 READY 机会`; st.style.color = 'var(--acc)'; }
-  else if (s.status === 'MARKET_CLOSED'){ st.textContent = '已收盘 — 监控待下一交易时段（无合成活动）'; st.style.color = 'var(--mut)'; }
-  else if (s.status === 'ALERTS'){ st.textContent = `需要行动 — READY ${(s.ready||[]).length} · EXIT_ALERT ${(s.exit_alerts||[]).length}`; st.style.color = 'var(--amber)'; }
-  else { st.textContent = '监控运行中 — ' + (s.status||'?'); st.style.color = 'var(--acc)'; }
-  const chips = [];
-  (s.ready||[]).forEach(sym=>chips.push(`<span class="chip B">READY ${esc(sym)}</span>`));
-  (s.exit_alerts||[]).forEach(sym=>chips.push(`<span class="chip S">EXIT_ALERT ${esc(sym)}</span>`));
-  (s.near||[]).forEach(sym=>chips.push(`<span class="chip gray">NEAR ${esc(sym)}</span>`));
-  items.innerHTML = chips.join('') || '<span class="dim">当前无 attention 项</span>';
-  const watchList = [...(s.ready||[]), ...(s.near||[])];
-  watch.textContent = watchList.length ? watchList.join(', ') : '当前无 READY/NEAR — 快层持续扫描活跃宇宙';
-  const ps = t.open_positions || [];
-  pos.innerHTML = ps.length ? ps.map(p=>`<div><code>${esc(p.symbol)}</code> ${p.shares}股 @${p.entry_price}` +
-    (p.price!=null?` → 现价 ${p.price}`:'') + (p.pnl!=null?` · 盈亏 ${p.pnl}`:'') +
-    ` · <b>${esc(p.state||'HOLD')}</b>${p.exit_reason?` · ${esc(p.exit_reason)}`:''}</div>`).join('') : '无持仓';
-  al.innerHTML = (t.alerts||[]).slice(0,5).map(a=>
-    `<div>· <b>${esc(a.type||'')}</b> ${a.symbol?esc(a.symbol)+' — ':''}${esc(a.what||'')}${a.why?` · ${esc(a.why)}`:''}</div>`).join('');
+  const msg = $('tm-msg');
+  msg.textContent = '记录中…'; msg.style.color = 'var(--mut)';
+  try{
+    const r = await fetch('/api/quant/' + tmKind, {
+      method: 'POST', headers: {'Content-Type': 'application/json'},
+      body: JSON.stringify(payload),
+    });
+    const j = await r.json().catch(()=>({}));
+    if(r.ok){
+      msg.style.color = 'var(--green)';
+      msg.textContent = '已记录到 canonical trading state: ' + JSON.stringify(j);
+      pollNow();
+    } else {
+      msg.style.color = 'var(--red)';
+      msg.textContent = '拒绝: ' + (j.error || ('http ' + r.status)) + '（canonical host 规则原样返回，未被 API 覆盖）';
+    }
+  }catch(e){
+    msg.style.color = 'var(--red)';
+    msg.textContent = '无法连接 quant_serve — 记录交易需运行: python3 tools/quant_serve.py（静态文件模式不产生任何写入）';
+  }
+}
+
+/* ---- 今日事件时间线: durable alerts only ---- */
+function renderTimeline(rows){
+  rows = rows || [];
+  $('tl-meta').textContent = `durable alerts · ${rows.length} 条真实持久化事件`;
+  $('tl-list').innerHTML = rows.length ? rows.map(r=>
+    `<li><span class="ts">${esc(String(r.ts||'').slice(5,19))}</span><span><b>${esc(r.type||'')}</b>` +
+    (r.symbol?` <code>${esc(r.symbol)}</code>`:'') + ` ${esc(r.what||'')}` +
+    (r.price!=null?` · @${esc(r.price)}`:'') + (r.venue?` · ${esc(r.venue)}`:'') +
+    (r.why?` <span class="mut">— ${esc(r.why)}</span>`:'') + '</span></li>').join('')
+    : '<li class="mut">当日无持久化事件 — 无事件只是没有 material change，不是无活动</li>';
 }
-async function pollAttention(){
+
+async function pollNow(){
   try{
-    const r = await fetch('/api/attention', {cache:'no-store'});
+    const r = await fetch('/api/quant/now', {cache:'no-store'});
     const j = await r.json();
-    renderTrading({present: !!j.as_of, state: j, open_positions: j.positions || [], alerts: j.events || []});
-  }catch(e){ /* keep the last good render */ }
+    renderNow(j);
+    renderPositions(j.positions || []);
+    $('now-meta').textContent += ' · 实时已连接';
+  }catch(e){
+    /* keep the embedded render-time snapshot; degrade visually, never fake live */
+    renderNow(D.now || {});
+    renderPositions((D.now||{}).positions || []);
+    $('now-meta').textContent += ' · server 未连接 — 显示生成时快照';
+  }
+}
+
+/* button wiring: action cards + position cards share data-act buttons */
+document.addEventListener('click', (e)=>{
+  const btn = e.target.closest('[data-act]');
+  if(!btn) return;
+  const act = btn.dataset.act;
+  if(act === 'ask'){
+    const sym = btn.dataset.symbol || '当前标的';
+    const promptText = `分析${sym}：先调用 get_trading_context 读取 canonical trading 事实，再解释当前 deterministic 状态（触发条件、风险、失效条件），区分 Runtime/Agent/Human 三态；不要宣称盈利能力，不要把 SYSTEM_UNAVAILABLE 说成 NO_TRADE。`;
+    (navigator.clipboard?.writeText(promptText) || Promise.reject()).then(
+      ()=>{ btn.textContent = '已复制提示词'; setTimeout(()=>{btn.textContent='Ask Agent';}, 1500); },
+      ()=>{ window.prompt('复制以下提示词发给 Agent:', promptText); });
+    return;
+  }
+  if(act === 'keep'){
+    const card = btn.closest('.action-card');
+    if(card){ card.style.opacity = '.45'; btn.disabled = true; btn.textContent = 'Watching'; }
+    return;
+  }
+  openTrade(act, btn.dataset.symbol, btn.dataset.venue,
+            btn.dataset.shares || '', btn.dataset.price || '');
+});
+document.addEventListener('click', (e)=>{
+  if(e.target.id === 'tm-close'){ $('trade-modal').hidden = true; return; }
+  if(e.target.id === 'tm-submit'){ submitTrade(); return; }
+  if(e.target.closest('#trade-modal') && !e.target.closest('.modal-box')){ $('trade-modal').hidden = true; }
+});
+document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') $('trade-modal').hidden = true; });
+setInterval(pollNow, 30000);
+
+/* ---- 真实运行数据趋势: trading artifacts 的忠实投影, 不补曲线不填 0 ---- */
+const RT_STATUS_ZH = {
+  SCANNED: '已扫描', NO_TRADE: '有效扫描 · 无机会', ALERTS: '需要行动',
+  MARKET_CLOSED: '已收盘（无扫描）', SYSTEM_UNAVAILABLE: '系统不可用（≠ NO_TRADE）',
+};
+const RT_STATUS_COLOR = {
+  SCANNED: 'var(--green)', NO_TRADE: 'var(--acc)', ALERTS: 'var(--amber)',
+  MARKET_CLOSED: '#8b96a8', SYSTEM_UNAVAILABLE: 'var(--red)',
+};
+const rtChip = (st) => `<span class="chip" style="color:${RT_STATUS_COLOR[st] || 'var(--mut)'};background:var(--panel2);border:1px solid var(--line2)" title="${esc(st)}">${esc(RT_STATUS_ZH[st] || st || '—')}</span>`;
+
+function renderM1Evidence(m1){
+  const box = $('m1-evidence');
+  const line = (label, ok, detail, forceText) => {
+    const v = forceText ?? (ok ? '有' : '未证明');
+    const color = forceText ? 'var(--amber)' : (ok ? 'var(--green)' : 'var(--amber)');
+    return `<dt style="min-width:150px">${esc(label)}</dt><dd style="color:${color};font-weight:700">${esc(v)}<span class="dim" style="font-weight:400"> — ${esc(detail||'')}</span></dd>`;
+  };
+  const fwd = m1.formal_forward_count ?? 0;
+  box.innerHTML = [
+    line('有效市场数据', !!(m1.market_data_valid||{}).ok, (m1.market_data_valid||{}).detail),
+    line('有效单次扫描', !!(m1.single_scan_valid||{}).ok, (m1.single_scan_valid||{}).detail),
+    line('连续实时监控', !!(m1.continuous_monitoring||{}).ok, (m1.continuous_monitoring||{}).detail),
+    line('正式 forward evidence', null, '正式 forward observation 计数 (trading/forward.json)', String(fwd)),
+    `<dt style="min-width:150px">M1 production evidence</dt><dd style="color:var(--amber);font-weight:700">${esc(m1.verdict || 'NO_REAL_EVIDENCE')} <span class="dim" style="font-weight:400">— 按 artifacts 真实状态投影, 不包装成 M1 PASS</span></dd>`,
+  ].join('');
 }
-setInterval(pollAttention, 30000);
+
+function renderRealTrendChart(pts){
+  const box = $('rt-chart');
+  if (!pts.length){
+    box.innerHTML = '<div class="empty"><div class="t">无真实运行记录</div><div class="s">trading/soak.jsonl 尚不存在 — monitor 从未运行, 不画任何合成曲线</div></div>';
+    return;
+  }
+  const W=1000, H=210, L=46, R=16, T=14, B=30;
+  const X = (i) => pts.length === 1 ? (L + (W-L-R)/2) : L + i*(W-L-R)/(pts.length-1);
+  const Y = (v) => T + (1-v)*(H-T-B);           // v = scanned/universe, 0..1
+  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">`;
+  for (let g=0; g<=2; g++){                     // 0% / 50% / 100% grid
+    const v=g/2, y=Y(v);
+    svg += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#1f2733" stroke-width="1"/>`+
+           `<text x="${L-6}" y="${y+4}" fill="#5c6678" font-size="10.5" text-anchor="end">${v*100}%</text>`;
+  }
+  const scanRatio = (p) => (p.symbols_scanned==null || !p.universe_size) ? null : p.symbols_scanned/p.universe_size;
+  // connect only consecutive points where a real scan happened on both sides;
+  // MARKET_CLOSED / SYSTEM_UNAVAILABLE gaps stay visually separate, no interpolation
+  for (let i=0; i+1<pts.length; i++){
+    const a=scanRatio(pts[i]), b=scanRatio(pts[i+1]);
+    if (a==null || b==null || pts[i].symbols_scanned<=0 || pts[i+1].symbols_scanned<=0) continue;
+    svg += `<line x1="${X(i)}" y1="${Y(a)}" x2="${X(i+1)}" y2="${Y(b)}" stroke="#4cc2ff" stroke-width="1.6" opacity=".85"/>`;
+  }
+  pts.forEach((p,i)=>{
+    const r = scanRatio(p);
+    const color = RT_STATUS_COLOR[p.status] || 'var(--mut)';
+    const tip = `${p.ts} · ${p.status}\n扫描 ${p.symbols_scanned ?? '缺失'}/${p.universe_size ?? '缺失'} · 事件 ${p.events ?? '缺失'}\n${p.source}`;
+    if (r == null){ return; }                   // missing stays missing: no fabricated point
+    svg += `<circle cx="${X(i)}" cy="${Y(r)}" r="${(p.events>0)?6:4.5}" fill="${color}" ${p.events>0?`stroke="var(--amber)" stroke-width="2" fill-opacity=".55"`:''}><title>${esc(tip)}</title></circle>`;
+    svg += `<text x="${X(i)}" y="${H-10}" fill="#5c6678" font-size="10" text-anchor="middle">${esc(String(p.ts).slice(5,16))}</text>`;
+  });
+  svg += '</svg>';
+  box.innerHTML = `<div class="chart-box">${svg}
+    <div class="legend" style="display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:12px;color:var(--mut)">
+      ${Object.keys(RT_STATUS_ZH).filter(s=>pts.some(p=>p.status===s)).map(s=>`<span style="display:flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:50%;display:inline-block;background:${RT_STATUS_COLOR[s]}"></i>${esc(RT_STATUS_ZH[s])}</span>`).join('')}
+      <span class="dim">折线只连接相邻两个真实扫描点；MARKET_CLOSED = 收盘无扫描, 不是扫描失败</span>
+    </div></div>`;
+}
+
+function renderRealTrend(){
+  const rt = D.real_trend || {};
+  const pts = rt.points || [];
+  $('rt-meta').textContent = `真实记录 ${rt.record_count ?? pts.length} 条 · universe ${rt.universe_size ?? '—'} 只 · M1 trading artifacts`;
+  renderM1Evidence(rt.m1_evidence || {});
+  renderRealTrendChart(pts);
+  const fwd = rt.forward || {};
+  $('rt-forward').innerHTML = fwd.count
+    ? `<b style="color:var(--green)">正式 forward observation：${fwd.count}</b>（已结算 ${fwd.settled ?? 0}）<span class="dim"> — trading/forward.json</span>`
+    : `<b style="color:var(--amber)">尚无正式 forward evidence</b><span class="dim"> — 正式 forward observation 0 条 (trading/forward.json)；不显示 0% 胜率, 不以诊断记录代替</span>`;
+  const diag = rt.diagnostic_rows || [];
+  $('rt-diagnostic').innerHTML = diag.length ? `
+    <div class="question" style="margin-bottom:6px;border-left-color:var(--amber)">以下为 <b>diagnostic forward evidence</b> — 来自隔离诊断运行（--state-dir 隔离, trading-diagnostic/），不是正式 forward observation, 不计入策略收益、胜率或已成交记录。</div>
+    <table><thead><tr><th>日期</th><th>代码</th><th>事件</th><th class="num-h">参考价</th><th class="num-h">5日回撤</th><th class="num-h">20日量比</th><th class="num-h">D+1（诊断）</th><th>标记</th></tr></thead><tbody>
+    ${diag.map(r=>`<tr>
+      <td class="num">${esc(r.day)}</td><td><code>${esc(r.symbol)}</code></td><td><span class="chip gray">${esc(r.state)}</span></td>
+      <td class="num">${fmt(r.ref_price)}</td>
+      <td class="num">${fmt(r.pullback_5d!=null?r.pullback_5d*100:null,2)}%</td>
+      <td class="num">${fmt(r.volume_ratio_20d)}</td>
+      <td class="num" style="color:var(--acc)">${r.d1!=null?`${r.d1>=0?'+':''}${(r.d1*100).toFixed(4)}% <span class="dim">(${esc(r.d1_day||'')})</span>`:'<span class="dim">待结算 — 缓存尚无后续日线</span>'}</td>
+      <td><span class="chip NEAR">diagnostic</span></td></tr>`).join('')}
+    </tbody></table>` : '';
+  $('rt-rows').innerHTML = pts.length ? pts.map(p=>`<tr>
+    <td class="num">${esc(p.ts)}</td><td>${rtChip(p.status)}</td>
+    <td class="num">${p.symbols_scanned ?? '—'}</td><td class="num">${p.universe_size ?? '—'}</td>
+    <td class="num">${p.events ?? '—'}</td><td class="mut"><code>${esc(p.source||'')}</code></td></tr>`).join('')
+    : '<tr><td colspan="6" class="mut">无真实记录 — 运行 python tools/quant_trading_monitor.py session 开始积累</td></tr>';
+}
+
 
 function renderStatic(){
-  pollAttention();
+  renderNow(D.now || {});
+  renderPositions((D.now||{}).positions || []);
+  renderTimeline(D.timeline || []);
+  pollNow();
+  renderRealTrend();
   $('gen-time').textContent = D.generated_at;
   $('strategy-warning').textContent = '⚠ ' + D.warning;
   $('not-a-buy').textContent = D.not_a_buy_note;
@@ -1989,8 +2558,8 @@ function renderStatic(){
     <dt>历史最佳年化</dt><dd>${fmt(s.best_annualized_pct,2)}% <span class="dim">(重放, 噪声内, 非已证明优势)</span></dd>
     <dt>历史交易笔数</dt><dd>${fmt(s.best_trades,0)}</dd>
     <dt>PIT / 成分偏差</dt><dd>存在 <span class="dim">(今日成员回看历史; 任何盈利声明的前置门)</span></dd>
-    <dt>前向触发累计</dt><dd>${fmt(s.forward_triggers,0)}</dd>
-    <dt>前向已结算交易</dt><dd>${fmt(s.forward_settled,0)}</dd>
+    <dt>前向观察（正式）</dt><dd>${fmt(s.forward_observations,0)} <span class="dim">(trading/forward.json)</span></dd>
+    <dt>前向已结算交易（正式）</dt><dd>${fmt(s.forward_settled,0)}</dd>
     <dt>前向胜率</dt><dd>${s.forward_hit_rate ? '积累足够结算笔数后再计算' : fmt(s.forward_hit_rate,3)}</dd>
   </dl>`;
   $('results-rows').innerHTML = (s.results||[]).map(r=>`<tr>
@@ -1998,8 +2567,11 @@ function renderStatic(){
     <td class="num">${fmt(r.trades,0)}</td><td class="num">${fmt(r.max_drawdown_pct,2)}%</td>
     <td class="mut">${esc(r.verdict)}</td></tr>`).join('') || '<tr><td colspan="5" class="mut">无评估工件</td></tr>';
 
-  // forward evidence
-  $('obs-rows').innerHTML = (D.obs_rows||[]).length ? D.obs_rows.slice().reverse().map(r=>`<tr>
+  // forward evidence: formal observations (trading/forward.json) + history log
+  const f = (D.real_trend||{}).forward || {};
+  $('formal-forward').innerHTML = f.count
+    ? `<b style="color:var(--green)">正式 forward observation：${f.count}</b>（已结算 ${f.settled??0}）— 明细随正式记录产生后在此展开`
+    : `<b style="color:var(--amber)">尚无正式 forward observation</b>（trading/forward.json 为 0 条）— 不显示 0% 胜率, 不以历史日志或诊断记录代替`;  $('obs-rows').innerHTML = (D.obs_rows||[]).length ? D.obs_rows.slice().reverse().map(r=>`<tr>
     <td class="num">${esc(r.date)}</td><td class="num">${esc(r.time)}</td>
     <td class="num">${esc(r.scanned)}</td>
     <td class="num" style="color:${r.triggers&&r.triggers!=='0'?'var(--red)':'var(--dim)'}">${esc(r.triggers)}</td>
diff --git a/plugins/zuaef-quant/zuaef_quant/plugin.py b/plugins/zuaef-quant/zuaef_quant/plugin.py
index 0c1802a..141e127 100644
--- a/plugins/zuaef-quant/zuaef_quant/plugin.py
+++ b/plugins/zuaef-quant/zuaef_quant/plugin.py
@@ -23,29 +23,66 @@ from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv
 from .toolset import make_toolset
 
 QUANT_INSTRUCTIONS = """\
-You support a small-capital A-share trader with evidence-based decisions.
+You are the decision-support layer of ZUAEF-ASHARE-001, a small-capital
+A-share program. A deterministic host-side monitor owns data, scans and the
+opportunity lifecycle (WATCH→NEAR→READY→INVALIDATED); the host owns the
+evaluator, market rules, costs and the canonical trade ledger. You own
+interpretation, bounded decisions and honest reporting. You are NOT the
+polling loop: never promise to "keep scanning" — trigger reads are
+on-demand calls, and monitoring continuity is proven by artifacts, not by
+your attention.
 
-1. Evidence before intuition; simulation before capital.
-2. Distinguish backtest, paper and real evidence. Real evidence outranks
-   simulated evidence when they conflict, respecting sample size.
-3. Research rounds follow one shape, then END: read the prior Strategy
+Evidence hierarchy: real > paper > diagnostic-forward > backtest, respecting
+sample size. Profitability is UNPROVEN (S3 frozen, PIT-contaminated
+universe): never present backtest or diagnostic numbers as expected
+returns, and say so when reporting performance claims.
+
+Truth sources — read these, never recompute or invent parallel ones:
+- Current trading state: get_trading_context (canonical truth is
+  workspace/artifacts/quant/trading/; never write a second ledger).
+- Domain background: knowledge concepts, entry point
+  knowledge/concepts/zuaef-quant-overview.md (execution truth, live ops,
+  data plane, eval methodology, strategy mechanics, fundamentals).
+- Executable spec: zuaef-quant-final-spec-v2.0-optimized/ (00_START_HERE.md
+  first); ops guide: docs/quant/README.md.
+- Human-readable view for the user: render_quant_business_artifact produces
+  a self-contained HTML under workspace/artifacts/quant/delivery/.
+
+Reporting semantics (the monitor's contract — violations fabricate evidence):
+- MARKET_CLOSED is not a scan failure; SYSTEM_UNAVAILABLE is not NO_TRADE.
+- data_trust (PASS|FAIL|UNKNOWN) is data quality; system availability is a
+  separate fact; never merge them.
+- Missing data stays missing — never 0-fill, never interpolate, never
+  carry yesterday's triggers onto today's facts.
+- Zero forward observations means "no forward evidence yet", not "no
+  signals exist"; M1 production evidence is currently PARTIAL.
+
+Operating rules:
+1. Research rounds follow one shape, then END: read the prior Strategy
    Result → propose one material mutation → evaluate_strategy exactly once
    → write the child's Strategy Result → stop. One evaluation per round is
    a hard host limit.
-4. Never claim an opportunity without deterministic trigger evidence
-   from get_live_signals. NO_TRADE is always a valid answer.
-5. evaluate_strategy is host-owned: you cannot modify the evaluator,
-   market rules, cost model, data split or benchmark; do not try.
-6. Never generate or execute arbitrary strategy Python; supply numeric
+2. evaluate_strategy is host-owned: you cannot modify the evaluator, market
+   rules, cost model, data split or benchmark; do not try.
+3. Never generate or execute arbitrary strategy Python; supply numeric
    strategy parameters only.
-7. Decision Briefs: use get_live_signals for triggers, decide
+4. Never claim an opportunity without deterministic trigger evidence from
+   get_live_signals. NO_TRADE is always a valid answer.
+5. Decision Briefs: use get_live_signals for triggers, decide
    NO_TRADE / WATCH / ENTER_CANDIDATE / HOLD / REDUCE / EXIT, and persist
    via record_decision_brief. ENTER_CANDIDATE is a candidate, never an
    order; the user decides whether to act.
-8. File tools take workspace-relative paths — use the result_file path
+6. Trade facts: record_trade_outcome writes the canonical ack only when
+   symbol/action/shares/price/venue are ALL explicit in the human's
+   statement; if any is missing, ask — never guess a fill, a price or a
+   venue (venue is 'paper' or 'real'). The tool records facts, it does not
+   place orders; Phase 1 sells close the full position only.
+7. File tools take workspace-relative paths — use the result_file path
    exactly as returned by tools; never prefix it.
-9. State uncertainty and data limitations explicitly; the universe carries
-   a current-membership survivorship limitation.
+8. State uncertainty and data limitations explicitly; the universe carries
+   a current-membership survivorship limitation. Insufficient evidence is a
+   valid answer — preserve the unknown instead of inspecting unchanged
+   evidence repeatedly.
 """
 
 #: Side-environment python used for evaluation/live scans (repo-relative).
diff --git a/plugins/zuaef-quant/zuaef_quant/toolset.py b/plugins/zuaef-quant/zuaef_quant/toolset.py
index 2deef10..fe9b29e 100644
--- a/plugins/zuaef-quant/zuaef_quant/toolset.py
+++ b/plugins/zuaef-quant/zuaef_quant/toolset.py
@@ -51,9 +51,14 @@ REPO_ROOT = resolve_repo_root()
 TOOLS_DIR = REPO_ROOT / "tools"
 QUANT_EVAL_SCRIPT = TOOLS_DIR / "quant_eval_qlib.py"
 QUANT_SCAN_SCRIPT = TOOLS_DIR / "quant_live_scan.py"
+QUANT_MONITOR_SCRIPT = TOOLS_DIR / "quant_trading_monitor.py"
+QUANT_RENDER_SCRIPT = TOOLS_DIR / "quant_render_business_dashboard.py"
 DEFAULT_BENCH_DIR = REPO_ROOT / "benchmarks" / "quant" / "gen1"
 EVAL_TIMEOUT_S = 1200
 SCAN_TIMEOUT_S = 300
+ACK_TIMEOUT_S = 120
+RENDER_TIMEOUT_S = 120
+GEN1_DIR = DEFAULT_BENCH_DIR
 
 #: Whitelisted StrategySpec keys (schema 1). Nothing else crosses the boundary.
 SPEC_KEYS = {
@@ -134,6 +139,29 @@ def _slug(name: str) -> str:
     return re.sub(r"[^a-z0-9_]", "_", name)
 
 
+def _read_json(path: Path, default):
+    """Tolerant canonical-artifact read: absent/corrupt -> the default, never
+    a fabricated business state."""
+    try:
+        return json.loads(path.read_text(encoding="utf-8"))
+    except (OSError, ValueError):
+        return default
+
+
+def _read_jsonl_tail(path: Path, limit: int) -> list[dict]:
+    try:
+        lines = path.read_text(encoding="utf-8").splitlines()
+    except OSError:
+        return []
+    rows = []
+    for line in lines[-limit:]:
+        try:
+            rows.append(json.loads(line))
+        except ValueError:
+            continue
+    return rows
+
+
 def _run(script: Path, args: list[str], quant_python: Path, timeout: int) -> str:
     proc = subprocess.run(
         [str(quant_python), str(script), *args],
@@ -320,8 +348,14 @@ def make_toolset(*, quant_python: Path, workspace_root: Path) -> AbstractToolset
         executed_at: str,
         notes: str = "",
     ) -> str:
-        """Record one manually executed or paper trade outcome (file-native,
-        no broker action). venue must be 'paper' or 'real'.
+        """Record one human-completed or paper trade FACT into the canonical
+        trading state via the canonical ack host operation (LOCAL fact write;
+        no broker action is taken and none can be). action must be BUY or
+        SELL; venue must be 'paper' or 'real'; executed_at is the human
+        fact's own ISO time. BUY creates a Position; SELL closes the FULL
+        position only (shares must equal the open position's shares) and its
+        venue must match the position's venue — the canonical host rejects
+        anything else and this tool surfaces that rejection verbatim.
         """
         if action not in ("BUY", "SELL"):
             raise ValueError("action must be BUY or SELL")
@@ -329,20 +363,105 @@ def make_toolset(*, quant_python: Path, workspace_root: Path) -> AbstractToolset
             raise ValueError("venue must be 'paper' or 'real'")
         if shares <= 0 or price <= 0:
             raise ValueError("shares and price must be positive")
-        record = {
-            "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(),
-            "symbol": symbol,
-            "action": action,
-            "shares": shares,
-            "price": price,
-            "venue": venue,
-            "executed_at": executed_at,
-            "notes": notes,
-        }
-        outcomes = workspace_root / "quant" / "outcomes.jsonl"
-        outcomes.parent.mkdir(parents=True, exist_ok=True)
-        with outcomes.open("a", encoding="utf-8") as fh:
-            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
-        return json.dumps({"recorded": True, "file": str(outcomes)}, ensure_ascii=False)
+        args = [
+            "--state-dir", str(workspace_root / "artifacts" / "quant" / "trading"),
+            "ack-buy" if action == "BUY" else "ack-sell",
+            "--symbol", symbol.strip().upper(),
+            "--price", repr(float(price)),
+            "--shares", str(int(shares)),
+            "--venue", venue,
+            "--time", executed_at,
+        ]
+        if notes.strip():
+            args += ["--note", notes.strip()]
+        stdout = _run(QUANT_MONITOR_SCRIPT, args, quant_python, ACK_TIMEOUT_S)
+        ack = json.loads(stdout.strip() or "{}")
+        return json.dumps(
+            {
+                "recorded": True,
+                "canonical": "workspace/artifacts/quant/trading/",
+                "ack": ack,
+                "note": "human trade fact via canonical ack; no broker action",
+            },
+            ensure_ascii=False,
+        )
+
+    @toolset.tool_plain
+    def get_trading_context() -> str:
+        """Read the bounded CURRENT trading context from the canonical M1
+        artifacts (workspace/artifacts/quant/trading/). Read-only projection:
+        never recomputes the market and never re-derives triggers. Returns
+        system health, market/data-trust status, READY/NEAR lists, open
+        positions, exit alerts, recent durable material events, forward
+        summary and heartbeat/last-scan times. Base every trading answer on
+        this context instead of memory; a stale context is a fact to report,
+        not to refresh by re-scanning.
+        """
+        trading = workspace_root / "artifacts" / "quant" / "trading"
+        state = _read_json(trading / "state.json", {})
+        positions = _read_json(trading / "positions.json", {"open": [], "closed": []})
+        forward = _read_json(trading / "forward.json", {"observations": []})
+        soak = _read_jsonl_tail(trading / "soak.jsonl", 50)
+        alerts = _read_jsonl_tail(trading / "alerts.jsonl", 20)
+        observations = forward.get("observations") or []
+        events = [
+            {k: a.get(k) for k in ("ts", "type", "symbol", "what", "why", "price", "venue")}
+            for a in alerts
+        ]
+        return json.dumps(
+            {
+                "present": bool(state),
+                "as_of": state.get("as_of"),
+                "day": state.get("day"),
+                "status": state.get("status"),
+                "data_trust": state.get("data_trust") or "UNKNOWN",
+                "market_no_trade": state.get("market_no_trade"),
+                "system_unavailable": state.get("system_unavailable"),
+                "heartbeat_at": soak[-1].get("ts") if soak else None,
+                "last_scan_at": next(
+                    (r.get("ts") for r in reversed(soak) if (r.get("symbols") or 0) > 0), None
+                ),
+                "ready": state.get("ready") or [],
+                "near": state.get("near") or [],
+                "exit_alerts": state.get("exit_alerts") or [],
+                "positions": positions.get("open") or [],
+                "recent_material_events": events,
+                "forward": {
+                    "observations": len(observations),
+                    "settled": sum(1 for o in observations if o.get("d8") is not None),
+                },
+                "limitations": [
+                    "strategy profitability UNPROVEN (S3 frozen, PIT-contaminated universe)",
+                    "READY/NEAR are deterministic facts from the frozen scan rules, not orders",
+                ],
+            },
+            ensure_ascii=False,
+        )
+
+    @toolset.tool_plain
+    def render_quant_business_artifact() -> str:
+        """Deterministically render the current business dashboard HTML from
+        the canonical trading artifacts (runs the host renderer; the model
+        never assembles HTML itself). Returns the workspace-relative artifact
+        path under artifacts/quant/delivery/ plus the renderer's bounded OK
+        summary. The output is a single-file self-contained HTML suitable for
+        direct delivery as a document attachment.
+        """
+        stamp = _dt.datetime.now(_dt.UTC).strftime("%Y%m%d-%H%M")
+        delivery = workspace_root / "artifacts" / "quant" / "delivery"
+        delivery.mkdir(parents=True, exist_ok=True)
+        out = delivery / f"quant-business-{stamp}.html"
+        stdout = _run(
+            QUANT_RENDER_SCRIPT, ["--out", str(out)], quant_python, RENDER_TIMEOUT_S
+        )
+        summary = next((ln for ln in stdout.splitlines() if ln.startswith("OK ->")), stdout[-200:])
+        return json.dumps(
+            {
+                "artifact": str(out.relative_to(workspace_root)),
+                "summary": summary,
+                "note": "single-file self-contained HTML; opens offline",
+            },
+            ensure_ascii=False,
+        )
 
     return toolset
diff --git a/tests/test_quant_business.py b/tests/test_quant_business.py
index 64dd2e4..5fdd05d 100644
--- a/tests/test_quant_business.py
+++ b/tests/test_quant_business.py
@@ -350,7 +350,11 @@ def biz_env(tmp_path):
         "status": tmp_path / "STATUS.md",
         "active": tmp_path / "active.toml",
         "legacy": tmp_path / "legacy_watchlist.toml",
-        "outcomes": tmp_path / "outcomes.jsonl",
+        "trading": tmp_path / "trading",
+        "diagnostic": tmp_path / "diagnostic",
+        "daily": tmp_path / "daily",
+        "active_symbols": tmp_path / "active_symbols.json",
+        "semantic": tmp_path / "semantic",
     }
 
 
@@ -360,6 +364,40 @@ class TestBusinessRenderer:
         assert "</script><script>alert(1)" not in html
         assert "\\u003c/script\\u003e" in html
 
+    def test_indicator_notes_default_to_hidden_full_width_board(self):
+        html = biz.render_html({})
+        assert 'id="glossary-open"' in html
+        assert 'aria-expanded="false" aria-controls="glossary-drawer"' in html
+        assert 'id="glossary-backdrop" hidden' in html
+        assert 'id="glossary-drawer" hidden' in html
+        assert 'class="card note-side"' not in html
+        assert 'layout-board{display:block' in html
+        assert 'grid-template-columns:minmax(0,1fr) 330px' not in html
+        assert 'width:min(420px,100vw)' in html
+
+    def test_indicator_notes_drawer_hooks_manage_open_close_and_focus(self):
+        html = biz.render_html({})
+        for hook in (
+            "function openGlossary(){ setGlossaryOpen(true); }",
+            "function closeGlossary(){ setGlossaryOpen(false); }",
+            "drawer.classList.add('is-open')",
+            "backdrop.classList.add('is-open')",
+            "e.target.id === 'glossary-close' || e.target.id === 'glossary-backdrop'",
+            "if(!$('glossary-drawer').hidden){ closeGlossary(); return; }",
+            "$('glossary-close').focus()",
+            "trigger.focus()",
+        ):
+            assert hook in html
+
+    def test_indicator_notes_keep_single_glossary_metric_modal_path(self):
+        html = biz.render_html({})
+        assert html.count('id="glossary-list"') == 1
+        assert html.count("const GLOSSARY = ") == 1
+        assert '<button type="button" class="g-item" data-m="${esc(k)}"' in html
+        assert "if(!g) return;" in html
+        for label in ("定义", "口径 / 计算", "怎么用", "局限", "数据来源"):
+            assert label in html
+
     def test_zero_triggers_shows_no_action_candidate(self, biz_env):
         write_snapshot(biz_env["snapshot"], [cand("600000")])
         write_scan(biz_env["scan"], [])
@@ -368,7 +406,7 @@ class TestBusinessRenderer:
         data = biz.build_data(
             snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
             briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
-            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
+            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
         )
         html = biz.render_html(data)
         assert "无今日动作候选" in html
@@ -395,7 +433,7 @@ class TestBusinessRenderer:
         data = biz.build_data(
             snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
             briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
-            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
+            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
         )
         html = biz.render_html(data)
         assert data["kpi"]["live_triggers"] == 2
@@ -417,7 +455,7 @@ class TestBusinessRenderer:
         data = biz.build_data(
             snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
             briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
-            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
+            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
         )
         html = biz.render_html(data)
         assert "DATA DEGRADED" in html
@@ -429,7 +467,7 @@ class TestBusinessRenderer:
         data = biz.build_data(
             snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
             briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
-            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
+            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
         )
         html = biz.render_html(data)
         assert data["data_quality"]["status"] == "MISSING"
@@ -447,7 +485,7 @@ class TestBusinessRenderer:
         data = biz.build_data(
             snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
             briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
-            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
+            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
         )
         html = biz.render_html(data)
         # engineering proof-chain stage identifiers must not lead the page
@@ -468,11 +506,160 @@ class TestBusinessRenderer:
         data = biz.build_data(
             snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
             briefs_dir=briefs, obs_path=biz_env["obs"], status_path=biz_env["status"],
-            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
+            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
         )
         assert data["kpi"]["today_decision"] == "NOT_RUN_TODAY"
 
 
+# ---------------------------------------------------------------------------
+# M1 real-run evidence trend: workspace/artifacts/quant/trading/ is the only
+# current trading truth; missing data stays missing, MARKET_CLOSED and
+# SYSTEM_UNAVAILABLE keep their real meanings
+# ---------------------------------------------------------------------------
+
+
+CLOSED_POINT = {"ts": "2026-09-04T19:10:35+08:00", "status": "MARKET_CLOSED", "events": 0, "symbols": 0, "ms": 0}
+
+
+def write_trading(env, soak, forward='{"observations": []}', alerts=None):
+    env["trading"].mkdir(parents=True, exist_ok=True)
+    (env["trading"] / "soak.jsonl").write_text(
+        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in soak), encoding="utf-8"
+    )
+    (env["trading"] / "forward.json").write_text(forward, encoding="utf-8")
+    if alerts is not None:
+        (env["trading"] / "alerts.jsonl").write_text(
+            "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in alerts), encoding="utf-8"
+        )
+
+
+def build_with_rt(env):
+    return biz.build_data(
+        snapshot_path=env["snapshot"], scan_path=env["scan"],
+        briefs_dir=env["briefs"], obs_path=env["obs"], status_path=env["status"],
+        active_path=env["active"], legacy_path=env["legacy"],
+        trading_dir=env["trading"], diagnostic_dir=env["diagnostic"],
+        daily_dir=env["daily"], active_symbols_path=env["active_symbols"],
+        semantic_dir=env["semantic"],
+    )
+
+
+class TestRealTrend:
+    def test_single_closed_point_is_one_real_point_not_a_curve(self, biz_env):
+        write_trading(biz_env, [CLOSED_POINT])
+        data = build_with_rt(biz_env)
+        rt = data["real_trend"]
+        assert rt["record_count"] == 1 and len(rt["points"]) == 1
+        p = rt["points"][0]
+        assert p["status"] == "MARKET_CLOSED"  # verbatim artifact status
+        assert p["symbols_scanned"] == 0  # real recorded zero, not missing
+        assert p["source"] == "trading/soak.jsonl"
+        html = biz.render_html(data)
+        assert "真实运行数据趋势" in html
+        assert "已收盘（无扫描）" in html
+        assert "不是扫描失败" in html
+
+    def test_duplicate_real_record_counts_once(self, biz_env):
+        write_trading(biz_env, [CLOSED_POINT, CLOSED_POINT])
+        rt = build_with_rt(biz_env)["real_trend"]
+        assert rt["record_count"] == 1
+
+    def test_missing_field_stays_missing_never_zero(self, biz_env):
+        row = {"ts": "2026-09-04T19:10:35+08:00", "status": "MARKET_CLOSED", "events": 0, "ms": 0}
+        write_trading(biz_env, [row])
+        p = build_with_rt(biz_env)["real_trend"]["points"][0]
+        assert p["symbols_scanned"] is None  # not coerced to 0
+
+    def test_events_refine_from_alerts_stream(self, biz_env):
+        alert = {"ts": CLOSED_POINT["ts"], "type": "NEW_READY", "symbol": "600000", "day": "2026-09-04"}
+        write_trading(biz_env, [CLOSED_POINT], alerts=[alert])
+        p = build_with_rt(biz_env)["real_trend"]["points"][0]
+        assert p["events"] == 1
+
+    def test_zero_observations_show_no_forward_evidence_never_zero_winrate(self, biz_env):
+        write_trading(biz_env, [CLOSED_POINT])
+        data = build_with_rt(biz_env)
+        assert data["real_trend"]["forward"]["count"] == 0
+        assert data["kpi"]["forward_settled_trades"] == 0
+        html = biz.render_html(data)
+        assert "尚无正式 forward observation" in html
+        assert "尚无正式 forward evidence" in html
+
+    def test_m1_verdict_partial_with_single_scan_but_no_continuous_monitor(self, biz_env):
+        write_trading(biz_env, [CLOSED_POINT])
+        biz_env["semantic"].mkdir(parents=True)
+        (biz_env["semantic"] / "semantic_proof_20260904T110935Z.json").write_text(json.dumps({
+            "status": "PASS", "reason": "50 consistent", "sample_size": 50,
+            "as_of": "2026-09-04T19:09:35+08:00",
+            "same_date_cross_check": {"status": "PASS"},
+        }))
+        data = build_with_rt(biz_env)
+        m1 = data["real_trend"]["m1_evidence"]
+        assert m1["market_data_valid"]["ok"] is True
+        assert m1["single_scan_valid"]["ok"] is True
+        assert m1["continuous_monitoring"]["ok"] is False
+        assert m1["formal_forward_count"] == 0
+        assert m1["verdict"] == "PARTIAL"
+        html = biz.render_html(data)
+        assert "M1 production evidence" in html and "PARTIAL" in html
+        assert "连续实时监控" in html and "未证明" in html
+
+    def test_system_unavailable_is_never_no_trade_and_scan_is_distinct(self, biz_env):
+        soak = [
+            {"ts": "2026-09-04T10:00:00+08:00", "status": "SYSTEM_UNAVAILABLE", "events": 1, "symbols": 50, "ms": 10},
+            {"ts": "2026-09-04T10:01:00+08:00", "status": "NO_TRADE", "events": 0, "symbols": 50, "ms": 10},
+            CLOSED_POINT,
+        ]
+        write_trading(biz_env, soak)
+        html = biz.render_html(build_with_rt(biz_env))
+        assert "系统不可用（≠ NO_TRADE）" in html
+        assert "有效扫描 · 无机会" in html
+        assert "已收盘（无扫描）" in html
+        # an in-session scanned point exists -> continuous monitoring has evidence
+        m1 = build_with_rt(biz_env)["real_trend"]["m1_evidence"]
+        assert m1["continuous_monitoring"]["ok"] is True
+
+    def test_diagnostic_d1_from_real_cache_and_pending_stays_pending(self, biz_env):
+        biz_env["diagnostic"].mkdir(parents=True)
+        alerts = [
+            {"ts": "2026-09-03T14:00:00+08:00", "type": "NEW_NEAR", "symbol": "600015", "day": "2026-09-03",
+             "price": 6.27, "conditions": {"pullback_5d": -0.0529, "volume_ratio_20d": 1.462}},
+            {"ts": "2026-09-03T14:00:00+08:00", "type": "NEW_NEAR", "symbol": "601799", "day": "2026-09-03",
+             "price": 74.88, "conditions": {"pullback_5d": -0.0853, "volume_ratio_20d": 2.204}},
+        ]
+        (biz_env["diagnostic"] / "alerts.jsonl").write_text(
+            "".join(json.dumps(a) + "\n" for a in alerts), encoding="utf-8"
+        )
+        header = "date,symbol,open,high,low,close,volume,amount,turnover\n"
+        biz_env["daily"].mkdir(parents=True)
+        (biz_env["daily"] / "600015_qfq.csv").write_text(
+            header + "2026-09-03,600015,6.22,6.33,6.22,6.27,1,1,0\n"
+            + "2026-09-04,600015,6.26,6.35,6.25,6.32,1,1,0\n", encoding="utf-8"
+        )
+        (biz_env["daily"] / "601799_qfq.csv").write_text(
+            header + "2026-09-03,601799,79.0,79.0,74.18,74.88,1,1,0\n", encoding="utf-8"
+        )
+        data = build_with_rt(biz_env)
+        diag = data["real_trend"]["diagnostic_rows"]
+        by_sym = {r["symbol"]: r for r in diag}
+        assert by_sym["600015"]["d1"] == 0.007974 and by_sym["600015"]["d1_day"] == "2026-09-04"
+        assert "d1" not in by_sym["601799"]  # no future bar -> pending, not 0
+        # diagnostic records never become formal forward observations
+        assert data["real_trend"]["forward"]["count"] == 0
+        html = biz.render_html(data)
+        assert "diagnostic forward evidence" in html
+        assert "不计入策略收益" in html
+
+    def test_old_outcomes_file_no_longer_drives_current_truth(self, biz_env, tmp_path):
+        write_trading(biz_env, [CLOSED_POINT])
+        stale = tmp_path / "outcomes.jsonl"
+        stale.write_text('{"action": "SELL"}\n{"action": "SELL"}\n', encoding="utf-8")
+        data = build_with_rt(biz_env)
+        html = biz.render_html(data)
+        assert data["kpi"]["forward_settled_trades"] == 0  # truth = forward.json, not outcomes
+        assert "outcomes" not in html
+
+
 # ---------------------------------------------------------------------------
 # server routes (T007)
 # ---------------------------------------------------------------------------
@@ -958,3 +1145,252 @@ class TestAntiLeakage:
         assert leak.scoped_verdict([{"status": "LOOKAHEAD_FAIL"}], {"status": "PASS"}) == "P0_4_FAIL"
         assert leak.scoped_verdict([], {"status": "PASS"}) == "P0_4_UNKNOWN"
         assert leak.scoped_verdict([{"status": "UNKNOWN"}], {"status": "PASS"}) == "P0_4_UNKNOWN"
+
+# ---------------------------------------------------------------------------
+# NOW projection (now_snapshot): heartbeat != last successful scan,
+# session-aware stale, event-matched agent brief, durable attention
+# ---------------------------------------------------------------------------
+
+
+IN_SESSION = datetime(2026, 9, 4, 11, 10, tzinfo=biz.TZ_SHANGHAI)   # Friday
+AFTER_CLOSE = datetime(2026, 9, 4, 19, 47, tzinfo=biz.TZ_SHANGHAI)
+
+NOW_STATE = {
+    "as_of": "2026-09-04T11:07:42+08:00", "day": "2026-09-04", "status": "ALERTS",
+    "symbols_scanned": 50, "data_trust": "PASS", "ready": [], "near": [],
+    "exit_alerts": [], "positions": [], "market_no_trade": False, "system_unavailable": False,
+}
+
+
+def write_now_env(env, *, alerts=None, soak=None, state=None):
+    env["trading"].mkdir(parents=True, exist_ok=True)
+    (env["trading"] / "state.json").write_text(json.dumps(state if state is not None else NOW_STATE), encoding="utf-8")
+    for name, rows in (("soak.jsonl", soak), ("alerts.jsonl", alerts)):
+        if rows is not None:
+            (env["trading"] / name).write_text(
+                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
+
+
+def write_brief(env, decision_id, *, symbol, recorded_at, action="WATCH"):
+    env["briefs"].mkdir(parents=True, exist_ok=True)
+    (env["briefs"] / f"{decision_id}.json").write_text(json.dumps({
+        "decision_id": decision_id, "symbol": symbol, "action": action,
+        "recorded_at": recorded_at, "why": "w", "invalidation": "i",
+    }), encoding="utf-8")
+
+
+class TestNowSnapshot:
+    def _snap(self, env, now):
+        return biz.now_snapshot(
+            trading_dir=env["trading"], briefs_dir=env["briefs"],
+            active_symbols_path=env["active_symbols"], now=now,
+        )
+
+    def test_heartbeat_and_last_scan_split(self, biz_env):
+        write_now_env(biz_env, soak=[
+            {"ts": "2026-09-04T09:31:00+08:00", "status": "MARKET_CLOSED", "symbols": 0},
+            {"ts": "2026-09-04T11:07:00+08:00", "status": "NO_TRADE", "symbols": 50},
+        ])
+        biz_env["active_symbols"].write_text(json.dumps({"symbols": ["600000", "600001"]}))
+        n = self._snap(biz_env, IN_SESSION)
+        assert n["heartbeat_at"] == "2026-09-04T11:07:00+08:00"
+        assert n["last_scan_at"] == "2026-09-04T11:07:00+08:00"
+        assert n["universe_size"] == 2 and n["market"] == "OPEN" and n["data_trust"] == "PASS"
+        # a closing-only soak never becomes a fake scan
+        write_now_env(biz_env, soak=[
+            {"ts": "2026-09-04T19:10:35+08:00", "status": "MARKET_CLOSED", "symbols": 0},
+        ], state={**NOW_STATE, "status": "MARKET_CLOSED", "symbols_scanned": 0})
+        n2 = self._snap(biz_env, AFTER_CLOSE)
+        assert n2["heartbeat_at"] == "2026-09-04T19:10:35+08:00" and n2["last_scan_at"] is None
+        assert n2["market"] == "CLOSED" and n2["stale"] is False
+
+    def test_stale_only_when_session_expects_a_live_loop(self, biz_env):
+        write_now_env(biz_env, soak=[
+            {"ts": "2026-09-04T11:07:00+08:00", "status": "NO_TRADE", "symbols": 50},
+        ])
+        n = self._snap(biz_env, IN_SESSION)  # heartbeat age 180s in-session
+        assert n["stale"] is True and n["runtime"] == "STALE"
+        n2 = self._snap(biz_env, AFTER_CLOSE)  # same age after close: not a fault
+        assert n2["stale"] is False and n2["runtime"] == "HEALTHY"
+
+    def test_ready_attention_with_event_matched_brief(self, biz_env):
+        write_now_env(biz_env, alerts=[
+            {"ts": "2026-09-04T11:07:42+08:00", "type": "NEW_READY", "symbol": "601799",
+             "price": 76.32, "what": "none -> READY", "why": "frozen entry conditions met"},
+        ], state={**NOW_STATE, "ready": ["601799"]})
+        # an older judgement must never answer a newer material event
+        write_brief(biz_env, "brief-20260903-601799", symbol="601799",
+                    recorded_at="2026-09-03T18:28:00+08:00", action="WATCH")
+        n = self._snap(biz_env, IN_SESSION)
+        item = n["attention"][0]
+        assert item["kind"] == "READY" and item["price"] == 76.32 and item["agent"] is None
+        write_brief(biz_env, "brief-20260904-601799", symbol="601799",
+                    recorded_at="2026-09-04T11:09:00+08:00", action="WATCH")
+        n2 = self._snap(biz_env, IN_SESSION)
+        assert n2["attention"][0]["agent"]["decision_id"] == "brief-20260904-601799"
+
+    def test_exit_attention_carries_position_and_human_fact(self, biz_env):
+        write_now_env(biz_env, alerts=[
+            {"ts": "2026-09-04T10:00:00+08:00", "type": "POSITION_OPENED", "symbol": "601799",
+             "price": 74.88, "venue": "paper", "note": "entry"},
+            {"ts": "2026-09-04T14:17:00+08:00", "type": "POSITION_EXIT_ALERT", "symbol": "601799",
+             "what": "HOLD -> EXIT_ALERT", "why": "close_below_ma5"},
+        ], state={**NOW_STATE, "exit_alerts": ["601799"], "data_trust": "FAIL",
+                  "positions": [{"symbol": "601799", "entry_price": 74.88, "price": 77.2,
+                                 "pnl": 232.0, "shares": 100, "venue": "paper", "state": "EXIT_ALERT"}]})
+        n = self._snap(biz_env, IN_SESSION)
+        kinds = {i["kind"] for i in n["attention"]}
+        assert {"EXIT", "DATA_UNTRUSTED"} <= kinds
+        exit_item = next(i for i in n["attention"] if i["kind"] == "EXIT")
+        assert exit_item["why"] == "close_below_ma5" and exit_item["entry_price"] == 74.88
+        assert exit_item["venue"] == "paper"
+        assert exit_item["human"]["action"].startswith("HOLD")
+
+    def test_system_unavailable_surfaces_as_attention(self, biz_env):
+        write_now_env(biz_env, state={**NOW_STATE, "status": "SYSTEM_UNAVAILABLE",
+                                      "system_unavailable": True, "data_trust": "UNKNOWN"})
+        n = self._snap(biz_env, IN_SESSION)
+        assert any(i["kind"] == "SYSTEM_UNAVAILABLE" for i in n["attention"])
+
+    def test_timeline_lists_only_state_day_events(self, biz_env):
+        write_now_env(biz_env, alerts=[
+            {"ts": "2026-09-03T14:00:00+08:00", "day": "2026-09-03", "type": "NEW_NEAR", "symbol": "600015", "what": "none -> NEAR"},
+            {"ts": "2026-09-04T11:07:42+08:00", "day": "2026-09-04", "type": "NEW_READY", "symbol": "601799", "what": "none -> READY"},
+        ])
+        rows = biz.load_timeline(biz_env["trading"], day="2026-09-04")
+        assert [r["type"] for r in rows] == ["NEW_READY"]
+
+    def test_build_data_embeds_now_and_timeline(self, biz_env):
+        write_trading(biz_env, [CLOSED_POINT])
+        (biz_env["trading"] / "state.json").write_text(json.dumps({
+            "as_of": CLOSED_POINT["ts"], "day": "2026-09-04",
+            "status": "MARKET_CLOSED", "data_trust": "UNKNOWN",
+        }), encoding="utf-8")
+        data = build_with_rt(biz_env)
+        assert data["now"]["present"] is True
+        assert data["now"]["runtime"] in ("HEALTHY", "STALE", "UNKNOWN")
+        assert isinstance(data["timeline"], list)
+        html = biz.render_html(data)
+        assert 'id="now-card"' in html and "今日事件时间线" in html
+        assert "尚未复核" in html  # agent three-state exists even without briefs
+
+
+class TestAckCommandBuilder:
+    def test_buy_builds_canonical_argv(self):
+        cmd = serve.ack_command_for("ack-buy", {
+            "symbol": "601799", "shares": 100, "price": 76.32, "venue": "paper",
+            "executed_at": "2026-09-04T11:07:42+08:00", "note": "n",
+        })
+        assert "tools/quant_trading_monitor.py" in cmd and "ack-buy" in cmd
+        assert cmd[cmd.index("--state-dir") + 1] == "workspace/artifacts/quant/trading"
+        assert cmd[cmd.index("--venue") + 1] == "paper"
+        assert cmd[cmd.index("--shares") + 1] == "100"
+        assert cmd[cmd.index("--note") + 1] == "n"
+
+    def test_skip_needs_no_venue_or_shares(self):
+        cmd = serve.ack_command_for("skip", {
+            "symbol": "601799", "price": 76.32,
+            "executed_at": "2026-09-04T11:07:42+08:00",
+        })
+        assert "skip" in cmd and "--venue" not in cmd and "--shares" not in cmd
+
+    @pytest.mark.parametrize("kind,payload,match", [
+        ("ack-buy", {"shares": 1, "price": 1, "venue": "paper", "executed_at": "t"}, "symbol"),
+        ("ack-buy", {"symbol": "X", "price": 1, "venue": "paper", "executed_at": "t"}, "shares"),
+        ("ack-buy", {"symbol": "X", "shares": 1, "venue": "paper"}, "executed_at"),
+        ("ack-buy", {"symbol": "X", "shares": 1, "venue": "paper", "executed_at": "t"}, "price"),
+        ("ack-buy", {"symbol": "X", "shares": 1, "price": 1, "executed_at": "t"}, "venue"),
+        ("ack-buy", {"symbol": "X", "shares": 1, "price": 1, "venue": "demo", "executed_at": "t"}, "venue"),
+        ("ack-buy", {"symbol": "X", "shares": 1.5, "price": 1, "venue": "paper", "executed_at": "t"}, "shares"),
+        ("skip", {"symbol": "X", "executed_at": "t"}, "price"),
+        ("nope", {"symbol": "X"}, "unknown ack kind"),
+    ])
+    def test_missing_or_invalid_fields_rejected(self, kind, payload, match):
+        with pytest.raises(ValueError, match=match):
+            serve.ack_command_for(kind, payload)
+
+    def test_writes_are_loopback_only(self):
+        assert all(serve.writes_enabled_for_host(h) for h in ("127.0.0.1", "localhost", "::1"))
+        assert not any(serve.writes_enabled_for_host(h) for h in ("0.0.0.0", "192.168.1.5", "example.com"))
+
+
+class TestQuantHttpApi:
+    import threading
+    import urllib.error
+    import urllib.request
+
+    def _server(self):
+        srv = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
+        thread = self.threading.Thread(target=srv.serve_forever, daemon=True)
+        thread.start()
+        return srv
+
+    def _post(self, port, path, payload):
+        req = self.urllib.request.Request(
+            f"http://127.0.0.1:{port}{path}",
+            data=json.dumps(payload).encode("utf-8"),
+            headers={"Content-Type": "application/json"}, method="POST")
+        return self.urllib.request.urlopen(req, timeout=5)
+
+    def test_post_ack_invokes_canonical_command(self, monkeypatch):
+        captured = {}
+
+        def fake_run(cmd, **kwargs):
+            captured["cmd"] = cmd
+            return type("R", (), {"returncode": 0, "stdout": '{"position": "p-0001"}', "stderr": ""})()
+
+        monkeypatch.setattr(serve.subprocess, "run", fake_run)
+        srv = self._server()
+        try:
+            with self._post(srv.server_address[1], "/api/quant/ack-buy", {
+                "symbol": "601799", "shares": 100, "price": 76.32,
+                "venue": "paper", "executed_at": "2026-09-04T11:07:42+08:00",
+            }) as resp:
+                body = json.loads(resp.read())
+            assert body["position"] == "p-0001"
+            assert "ack-buy" in captured["cmd"]
+            assert captured["cmd"][captured["cmd"].index("--venue") + 1] == "paper"
+        finally:
+            srv.shutdown()
+
+    def test_post_canonical_rejection_is_400_verbatim(self, monkeypatch):
+        def rejecting_run(cmd, **kwargs):
+            return type("R", (), {"returncode": 1, "stdout": "",
+                                  "stderr": '{"error": "venue mismatch: position opened as paper"}'})()
+
+        monkeypatch.setattr(serve.subprocess, "run", rejecting_run)
+        srv = self._server()
+        try:
+            with pytest.raises(self.urllib.error.HTTPError) as err:
+                self._post(srv.server_address[1], "/api/quant/ack-sell", {
+                    "symbol": "601799", "shares": 100, "price": 77.2,
+                    "venue": "real", "executed_at": "2026-09-04T14:17:00+08:00",
+                })
+            assert err.value.code == 400
+            assert "venue mismatch" in err.value.read().decode()
+        finally:
+            srv.shutdown()
+
+    def test_post_validation_error_is_400(self):
+        srv = self._server()
+        try:
+            with pytest.raises(self.urllib.error.HTTPError) as err:
+                self._post(srv.server_address[1], "/api/quant/ack-buy",
+                           {"symbol": "601799", "shares": 100, "price": 76.32})
+            assert err.value.code == 400
+        finally:
+            srv.shutdown()
+
+    def test_post_disabled_on_non_loopback_host(self):
+        srv = self._server()
+        serve.Handler.writes_enabled = False
+        try:
+            with pytest.raises(self.urllib.error.HTTPError) as err:
+                self._post(srv.server_address[1], "/api/quant/ack-buy", {
+                    "symbol": "601799", "shares": 100, "price": 76.32,
+                    "venue": "paper", "executed_at": "t",
+                })
+            assert err.value.code == 403
+        finally:
+            srv.shutdown()
+            serve.Handler.writes_enabled = True
diff --git a/tests/test_quant_plugin.py b/tests/test_quant_plugin.py
index 26f6329..b04ec75 100644
--- a/tests/test_quant_plugin.py
+++ b/tests/test_quant_plugin.py
@@ -106,29 +106,158 @@ class TestPluginFactory:
 
 
 class TestRecordOutcome:
-    def test_outcome_written_as_jsonl(self, tmp_path, monkeypatch):
+    def _toolset(self, tmp_path, monkeypatch):
         monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
         monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
         env = _env(tmp_path)
         bundle = create_plugin(env, {})
-        toolset = bundle.capabilities[0].toolsets[0]
-        call = toolset.tools["record_trade_outcome"]
-        # direct function invocation via the tool object's function
-        func = call.function if hasattr(call, "function") else call
+        return bundle.capabilities[0].toolsets[0], env
+
+    def test_buy_routes_to_canonical_ack_with_venue_and_note(self, tmp_path, monkeypatch):
+        toolset, env = self._toolset(tmp_path, monkeypatch)
+        func = toolset.tools["record_trade_outcome"].function
+        captured = {}
+
+        def fake_run(script, args, quant_python, timeout):
+            captured["script"], captured["args"] = script, args
+            return json.dumps({"position": "p-0001", "symbol": "600519", "state": "HOLD", "venue": "paper"})
+
+        import zuaef_quant.toolset as toolset_mod
+        monkeypatch.setattr(toolset_mod, "_run", fake_run)
         result = json.loads(func(
-            symbol="600519",
-            action="BUY",
-            shares=100,
-            price=1297.4,
-            venue="paper",
-            executed_at="2026-08-28T15:00:00+08:00",
-            notes="paper entry",
+            symbol="600519", action="BUY", shares=100, price=1297.4,
+            venue="paper", executed_at="2026-09-04T11:07:42+08:00", notes="paper entry",
         ))
         assert result["recorded"] is True
-        outcomes = env.workspace_root / "quant" / "outcomes.jsonl"
-        lines = outcomes.read_text(encoding="utf-8").strip().splitlines()
-        assert len(lines) == 1
-        assert json.loads(lines[0])["symbol"] == "600519"
+        assert result["canonical"] == "workspace/artifacts/quant/trading/"
+        assert result["ack"]["position"] == "p-0001"
+        args = captured["args"]
+        assert "ack-buy" in args
+        assert args[args.index("--symbol") + 1] == "600519"
+        assert args[args.index("--shares") + 1] == "100"
+        assert args[args.index("--venue") + 1] == "paper"
+        assert args[args.index("--time") + 1] == "2026-09-04T11:07:42+08:00"
+        assert args[args.index("--note") + 1] == "paper entry"
+        assert args[args.index("--state-dir") + 1] == str(env.workspace_root / "artifacts" / "quant" / "trading")
+        # the legacy outcomes ledger is never written again
+        assert not (env.workspace_root / "quant" / "outcomes.jsonl").exists()
+        # a human-fact record is a LOCAL write: no approval requirement
+        assert not getattr(toolset.tools["record_trade_outcome"], "requires_approval", False)
+
+    def test_sell_routes_to_ack_sell_without_note_flag_when_empty(self, tmp_path, monkeypatch):
+        toolset, _ = self._toolset(tmp_path, monkeypatch)
+        func = toolset.tools["record_trade_outcome"].function
+        captured = {}
+
+        def fake_run(script, args, quant_python, timeout):
+            captured["args"] = args
+            return json.dumps({"closed": "p-0001", "pnl": 150.0, "venue": "real"})
+
+        import zuaef_quant.toolset as toolset_mod
+        monkeypatch.setattr(toolset_mod, "_run", fake_run)
+        result = json.loads(func(
+            symbol="600519", action="SELL", shares=100, price=1320.0,
+            venue="real", executed_at="2026-09-04T13:45:00+08:00",
+        ))
+        assert result["ack"]["closed"] == "p-0001"
+        assert "ack-sell" in captured["args"] and "--note" not in captured["args"]
+
+    def test_canonical_host_rejection_surfaces_verbatim(self, tmp_path, monkeypatch):
+        toolset, _ = self._toolset(tmp_path, monkeypatch)
+        func = toolset.tools["record_trade_outcome"].function
+
+        def rejecting_run(script, args, quant_python, timeout):
+            raise RuntimeError("canonical ack rejected the trade record: venue mismatch")
+
+        import zuaef_quant.toolset as toolset_mod
+        monkeypatch.setattr(toolset_mod, "_run", rejecting_run)
+        with pytest.raises(RuntimeError, match="venue mismatch"):
+            func(symbol="600519", action="SELL", shares=100, price=10.0,
+                 venue="real", executed_at="2026-09-04T13:45:00+08:00")
+
+    def test_invalid_action_rejected_before_side_env(self, tmp_path, monkeypatch):
+        toolset, _ = self._toolset(tmp_path, monkeypatch)
+        func = toolset.tools["record_trade_outcome"].function
+        with pytest.raises(ValueError, match="action"):
+            func(symbol="600519", action="BUY_NOW", shares=100, price=10.0,
+                 venue="paper", executed_at="2026-09-04T13:45:00+08:00")
+        with pytest.raises(ValueError, match="venue"):
+            func(symbol="600519", action="BUY", shares=100, price=10.0,
+                 venue="demo", executed_at="2026-09-04T13:45:00+08:00")
+
+
+class TestGetTradingContext:
+    def _toolset(self, tmp_path, monkeypatch):
+        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
+        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
+        env = _env(tmp_path)
+        bundle = create_plugin(env, {})
+        return bundle.capabilities[0].toolsets[0], env
+
+    def test_absent_artifacts_are_reported_not_fabricated(self, tmp_path, monkeypatch):
+        toolset, _ = self._toolset(tmp_path, monkeypatch)
+        data = json.loads(toolset.tools["get_trading_context"].function())
+        assert data["present"] is False
+        assert data["data_trust"] == "UNKNOWN"
+        assert data["ready"] == [] and data["positions"] == []
+        assert data["heartbeat_at"] is None and data["last_scan_at"] is None
+
+    def test_bounded_context_from_canonical_artifacts(self, tmp_path, monkeypatch):
+        toolset, env = self._toolset(tmp_path, monkeypatch)
+        trading = env.workspace_root / "artifacts" / "quant" / "trading"
+        trading.mkdir(parents=True)
+        (trading / "state.json").write_text(json.dumps({
+            "as_of": "2026-09-04T10:00:00+08:00", "day": "2026-09-04", "status": "ALERTS",
+            "data_trust": "PASS", "ready": ["601799"], "near": ["600015"], "exit_alerts": [],
+            "market_no_trade": False, "system_unavailable": False,
+        }), encoding="utf-8")
+        (trading / "positions.json").write_text(json.dumps({
+            "open": [{"id": "p-0001", "symbol": "601799", "venue": "paper", "shares": 100,
+                      "entry_price": 76.32, "state": "HOLD"}], "closed": [],
+        }), encoding="utf-8")
+        (trading / "forward.json").write_text(json.dumps({
+            "observations": [{"kind": "EXECUTED"}, {"kind": "SKIP", "d8": 0.01}],
+        }), encoding="utf-8")
+        (trading / "soak.jsonl").write_text(
+            '{"ts": "2026-09-04T09:31:00+08:00", "status": "MARKET_CLOSED", "symbols": 0}\n'
+            '{"ts": "2026-09-04T09:47:00+08:00", "status": "ALERTS", "symbols": 50}\n', encoding="utf-8")
+        (trading / "alerts.jsonl").write_text(
+            '{"ts": "2026-09-04T09:47:00+08:00", "type": "NEW_READY", "symbol": "601799", "what": "none -> READY"}\n',
+            encoding="utf-8")
+        data = json.loads(toolset.tools["get_trading_context"].function())
+        assert data["present"] is True and data["status"] == "ALERTS" and data["data_trust"] == "PASS"
+        assert data["ready"] == ["601799"] and data["near"] == ["600015"]
+        assert data["positions"][0]["venue"] == "paper"
+        # heartbeat != last successful scan
+        assert data["heartbeat_at"] == "2026-09-04T09:47:00+08:00"
+        assert data["last_scan_at"] == "2026-09-04T09:47:00+08:00"
+        assert data["forward"] == {"observations": 2, "settled": 1}
+        assert data["recent_material_events"][0]["type"] == "NEW_READY"
+        assert any("UNPROVEN" in l for l in data["limitations"])
+
+
+class TestRenderBusinessArtifact:
+    def test_renders_into_delivery_dir_with_bounded_summary(self, tmp_path, monkeypatch):
+        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
+        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
+        env = _env(tmp_path)
+        bundle = create_plugin(env, {})
+        toolset = bundle.capabilities[0].toolsets[0]
+        func = toolset.tools["render_quant_business_artifact"].function
+        captured = {}
+
+        def fake_run(script, args, quant_python, timeout):
+            captured["script"], captured["args"] = script, args
+            return "OK -> /tmp/x.html (90.2 KB, also y); decision=NO_TRADE real_records=5 m1=PARTIAL"
+
+        import zuaef_quant.toolset as toolset_mod
+        monkeypatch.setattr(toolset_mod, "_run", fake_run)
+        result = json.loads(func())
+        assert captured["script"].name == "quant_render_business_dashboard.py"
+        assert "--out" in captured["args"]
+        assert result["artifact"].startswith("artifacts/quant/delivery/quant-business-")
+        assert not result["artifact"].startswith(str(env.workspace_root))
+        assert "m1=PARTIAL" in result["summary"]
 
 
 class TestEvaluateStrategy:
diff --git a/tests/test_quant_trading_monitor.py b/tests/test_quant_trading_monitor.py
index fc7587b..fffba94 100644
--- a/tests/test_quant_trading_monitor.py
+++ b/tests/test_quant_trading_monitor.py
@@ -256,6 +256,69 @@ class TestAckBoundary:
         assert opened["data_trust"] == "USER_CONFIRMED"  # a human fact, not a system signal
 
 
+class TestAckVenueNoteSkip:
+    def test_buy_persists_venue_and_alert_fields(self, tmp_path, monitor_env):
+        store = fresh_store(tmp_path)
+        rc = mon.cmd_ack_buy(SimpleNamespace(
+            symbol="600001", price=9.9, shares=500, time=None, venue="real", note="my entry"), store)
+        assert rc == 0
+        assert store.positions["open"][0]["venue"] == "real"
+        alerts = [json.loads(l) for l in (store.dir / "alerts.jsonl").read_text().splitlines()]
+        opened = next(a for a in alerts if a["type"] == mon.EVENT_POSITION_OPENED)
+        assert opened["venue"] == "real" and opened["note"] == "my entry"
+
+    def test_sell_rejects_partial_close(self, tmp_path, monitor_env):
+        store = fresh_store(tmp_path)
+        store.open_position("600001", 9.9, 500, "2026-09-02T10:00:00", SPEC.name)
+        rc = mon.cmd_ack_sell(SimpleNamespace(
+            symbol="600001", price=10.2, shares=100, time=None, venue="real"), store)
+        assert rc == 1 and len(store.positions["open"]) == 1
+
+    def test_sell_rejects_venue_mismatch(self, tmp_path, monitor_env):
+        store = fresh_store(tmp_path)
+        store.open_position("600001", 9.9, 500, "2026-09-02T10:00:00", SPEC.name, venue="paper")
+        rc = mon.cmd_ack_sell(SimpleNamespace(
+            symbol="600001", price=10.2, shares=500, time=None, venue="real"), store)
+        assert rc == 1 and len(store.positions["open"]) == 1
+
+    def test_sell_defaults_to_position_venue_and_closes(self, tmp_path, monitor_env):
+        store = fresh_store(tmp_path)
+        store.open_position("600001", 9.9, 500, "2026-09-02T10:00:00", SPEC.name, venue="real")
+        # args without a venue attr (older CLI callers) inherit the position venue
+        rc = mon.cmd_ack_sell(SimpleNamespace(
+            symbol="600001", price=10.2, shares=500, time=None), store)
+        assert rc == 0 and store.positions["open"] == []
+
+    def test_skip_records_human_fact_without_touching_lifecycle(self, tmp_path, monitor_env):
+        store = fresh_store(tmp_path)
+        store.opportunities["600001"] = {"state": "READY", "since": "2026-09-02"}
+        rc = mon.cmd_skip(SimpleNamespace(
+            symbol="600001", price=9.95, time=None, note="too extended"), store)
+        assert rc == 0
+        assert store.opportunities["600001"]["state"] == "READY"  # state machine untouched
+        assert store.forward["observations"][-1]["kind"] == "SKIP"
+        assert store.forward["observations"][-1]["ref_price"] == 9.95
+        alerts = [json.loads(l) for l in (store.dir / "alerts.jsonl").read_text().splitlines()]
+        skip = next(a for a in alerts if a["type"] == mon.EVENT_HUMAN_SKIP)
+        assert skip["symbol"] == "600001" and skip["note"] == "too extended"
+        assert skip["data_trust"] == "USER_CONFIRMED"
+
+    def test_summary_data_trust_follows_semantic_gate_not_availability(self, tmp_path, monitor_env, monkeypatch):
+        store = fresh_store(tmp_path)
+        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
+        state = json.loads((store.dir / "state.json").read_text())
+        assert state["data_trust"] == "PASS"
+        monkeypatch.setattr(mon, "load_volume_semantics", lambda **k: {"status": "FAIL"})
+        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
+        state = json.loads((store.dir / "state.json").read_text())
+        assert state["data_trust"] == "FAIL"
+        # outside the session: nothing evaluated -> UNKNOWN, never a fake verdict
+        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir,
+                      now=datetime(2026, 9, 2, 16, 0, tzinfo=TZ_SH))
+        state = json.loads((store.dir / "state.json").read_text())
+        assert state["data_trust"] == "UNKNOWN" and state["system_unavailable"] is False
+
+
 # ---------------------------------------------------------------------------
 # fixture isolation
 # ---------------------------------------------------------------------------
diff --git a/tools/quant_render_business_dashboard.py b/tools/quant_render_business_dashboard.py
index ef169fd..72a8b12 100755
--- a/tools/quant_render_business_dashboard.py
+++ b/tools/quant_render_business_dashboard.py
@@ -1,13 +1,18 @@
 #!/usr/bin/env python3
 """render_business_dashboard.py — ZUAEF quant business dashboard (read-only).
 
-Renders docs/quant/business.html from existing artifacts: candidate snapshot
+Renders docs/quant/business.html from existing artifacts: the M1 trading-loop
+truth (workspace/artifacts/quant/trading/ — soak.jsonl / alerts.jsonl /
+forward.json / state.json), the candidate snapshot
 (tools/quant_build_candidates.py), last live-scan snapshot, Decision Briefs,
-the observation log, the frozen active strategy and baseline/S1/S2/S3
-evidence. Answers market questions — today's decision, top value/quality
-alternatives, live triggers, why each candidate ranks, red flags, data
-freshness, and why the strategy is still unproven. Engineering proof chain
-(U0–P5.5) stays on /engineering.
+the observation log (history only), the frozen active strategy and
+baseline/S1/S2/S3 evidence. Answers market questions — today's decision, top
+value/quality alternatives, live triggers, why each candidate ranks, red
+flags, data freshness, real-run evidence trend, and why the strategy is
+still unproven. Engineering proof chain (U0–P5.5) stays on /engineering.
+
+Current M1 trading truth comes only from workspace/artifacts/quant/trading/.
+The old workspace/quant/outcomes.jsonl is no longer read.
 
 Stdlib only: runs with plain python3, no quant dependency group needed.
 
@@ -24,6 +29,7 @@ import argparse
 import json
 import re
 from datetime import UTC, datetime
+from datetime import time as dtime
 from pathlib import Path
 from zoneinfo import ZoneInfo
 
@@ -39,8 +45,11 @@ OBS_LOG_PATH = GEN1 / "OBSERVATION_LOG.md"
 STATUS_PATH = GEN1 / "STATUS.md"
 ACTIVE_PATH = GEN1 / "active.toml"
 LEGACY_PATH = GEN1 / "legacy_watchlist.toml"
-OUTCOMES_PATH = REPO_ROOT / "workspace" / "quant" / "outcomes.jsonl"
 SEMANTIC_DIR = ART / "semantic"
+TRADING_DIR = ART / "trading"
+TRADING_DIAGNOSTIC_DIR = ART / "trading-diagnostic"
+DAILY_CACHE_DIR = REPO_ROOT / "data" / "quant-cache" / "daily"
+ACTIVE_SYMBOLS_PATH = REPO_ROOT / "data" / "quant-cache" / "candidates" / "active_symbols.json"
 DEFAULT_OUT = REPO_ROOT / "docs" / "quant" / "business.html"
 
 STRATEGY_WARNING = "历史 S3 证据薄弱;盈利能力仍未证明 (NOT YET)。"
@@ -222,9 +231,165 @@ def today_decision(briefs: list[dict]) -> dict:
     }
 
 
-def settled_trade_count(outcomes_path: Path) -> int:
-    rows = read_jsonl(outcomes_path)
-    return sum(1 for r in rows if r.get("action") == "SELL")
+# --------------------------------------------------------------------------
+# M1 real-run evidence (workspace/artifacts/quant/trading/ is the only
+# current trading truth; missing data stays missing, never coerced to 0)
+# --------------------------------------------------------------------------
+
+
+# soak statuses that prove an in-session pass actually scanned the universe
+SOAK_IN_SESSION_STATUSES = {"NO_TRADE", "ALERTS", "SCANNED"}
+
+DIAGNOSTIC_EVENT_KINDS = {"NEW_NEAR": "NEAR", "NEW_READY": "READY"}
+
+
+def _d1_from_daily(daily_dir: Path, symbol: str, ref_price: float, day: str) -> dict:
+    """Diagnostic D+1 from the first cached daily close strictly after `day`.
+
+    Real cached bars only. No future bar -> stays pending (no key), never a
+    fabricated 0.
+    """
+    lines = read_text(Path(daily_dir) / f"{symbol}_qfq.csv").splitlines()
+    for line in lines[1:]:  # skip header; ISO dates sort lexicographically
+        cells = line.split(",")
+        # columns: date,symbol,open,high,low,close,...
+        if len(cells) < 6 or cells[0] <= day:
+            continue
+        try:
+            close = float(cells[5])
+        except ValueError:
+            continue
+        if ref_price <= 0:
+            return {}
+        return {"d1_day": cells[0], "d1": round(close / ref_price - 1, 6)}
+    return {}
+
+
+def load_diagnostic_evidence(
+    diagnostic_dir: Path = TRADING_DIAGNOSTIC_DIR, daily_dir: Path = DAILY_CACHE_DIR
+) -> list[dict]:
+    """9/3-style isolated diagnostic NEAR/READY records + their D+1 outcome.
+
+    These are `diagnostic forward evidence` from a `--state-dir` isolated run:
+    never formal forward observations, never strategy return/win-rate.
+    """
+    rows = []
+    for a in read_jsonl(Path(diagnostic_dir) / "alerts.jsonl"):
+        kind = DIAGNOSTIC_EVENT_KINDS.get(str(a.get("type", "")))
+        if kind is None:
+            continue
+        symbol, ref, day = a.get("symbol"), a.get("price"), str(a.get("day") or "")
+        conditions = a.get("conditions") or {}
+        row = {
+            "kind": "diagnostic",
+            "symbol": symbol,
+            "day": day,
+            "state": kind,
+            "ref_price": ref,
+            "pullback_5d": conditions.get("pullback_5d"),
+            "volume_ratio_20d": conditions.get("volume_ratio_20d"),
+            "source": "trading-diagnostic/alerts.jsonl",
+        }
+        if isinstance(ref, (int, float)) and day:
+            row.update(_d1_from_daily(daily_dir, str(symbol), float(ref), day))
+        rows.append(row)
+    return rows
+
+
+def load_real_trend(
+    trading_dir: Path = TRADING_DIR,
+    *,
+    diagnostic_dir: Path = TRADING_DIAGNOSTIC_DIR,
+    daily_dir: Path = DAILY_CACHE_DIR,
+    active_symbols_path: Path = ACTIVE_SYMBOLS_PATH,
+    semantic_dir: Path = SEMANTIC_DIR,
+) -> dict:
+    """Real trading-loop records -> real_trend for the business page.
+
+    Points come verbatim from soak.jsonl (MARKET_CLOSED / SYSTEM_UNAVAILABLE
+    stay what they are; symbols=0 while closed is a real recorded zero, and a
+    genuinely missing field stays missing). No interpolation, no backfill,
+    duplicate real records counted once.
+    """
+    soak = read_jsonl(Path(trading_dir) / "soak.jsonl")
+    alerts_by_ts: dict[str, int] = {}
+    for a in read_jsonl(Path(trading_dir) / "alerts.jsonl"):
+        ts = str(a.get("ts"))
+        alerts_by_ts[ts] = alerts_by_ts.get(ts, 0) + 1
+    universe = read_json(active_symbols_path) or {}
+    universe_size = len(universe.get("symbols") or []) or None
+
+    points: list[dict] = []
+    seen: set = set()
+    for row in soak:
+        ts = str(row.get("ts") or "")
+        key = (ts, str(row.get("status")), row.get("events"), row.get("symbols"))
+        if not ts or key in seen:  # same real record never counts twice
+            continue
+        seen.add(key)
+        points.append(
+            {
+                "ts": ts,
+                "status": row.get("status"),
+                "symbols_scanned": row.get("symbols"),
+                "universe_size": universe_size,
+                # alerts.jsonl refines the per-cycle count when it has the ts
+                "events": alerts_by_ts.get(ts, row.get("events")),
+                "source": "trading/soak.jsonl",
+            }
+        )
+    points.sort(key=lambda p: p["ts"])
+
+    forward = read_json(Path(trading_dir) / "forward.json") or {}
+    observations = forward.get("observations") or []
+    settled = sum(1 for o in observations if o.get("d8") is not None)
+
+    proof = load_latest_semantic_proof(semantic_dir)
+    in_session = [
+        p
+        for p in points
+        if p["status"] in SOAK_IN_SESSION_STATUSES and (p["symbols_scanned"] or 0) > 0
+    ]
+    if proof:
+        market_ok = proof.get("status") == "PASS" and str(
+            (proof.get("same_date_cross_check") or {}).get("status")
+        ) == "PASS"
+        market_detail = f"最新 semantic proof {proof.get('as_of', '')} · {proof.get('reason', '')}"
+    else:
+        market_ok = False
+        market_detail = "尚无 semantic proof"
+    sample = proof.get("sample_size") or 0 if proof else 0
+    single_ok = sample > 0
+    single_detail = (
+        f"单次全宇宙报价核验 {sample}/{sample} ({proof.get('as_of', '')}) — 单次验证, 不是连续监控"
+        if single_ok
+        else "尚无单次全宇宙有效数据通过记录"
+    )
+    cont_detail = (
+        f"soak 真实记录 {len(points)} 条, 其中盘中有效扫描 {len(in_session)} 条"
+        + ("" if in_session else " — 连续实时监控未证明")
+    )
+    m1 = {
+        "market_data_valid": {"ok": market_ok, "detail": market_detail},
+        "single_scan_valid": {"ok": single_ok, "detail": single_detail},
+        "continuous_monitoring": {"ok": bool(in_session), "detail": cont_detail},
+        "formal_forward_count": len(observations),
+        "formal_forward_settled": settled,
+    }
+    oks = [market_ok, single_ok, bool(in_session)]
+    m1["verdict"] = (
+        "PASS" if all(oks) and len(observations) > 0
+        else "PARTIAL" if any(oks) or len(observations)
+        else "NO_REAL_EVIDENCE"
+    )
+    return {
+        "points": points,
+        "record_count": len(points),
+        "universe_size": universe_size,
+        "forward": {"present": bool(forward), "count": len(observations), "settled": settled},
+        "m1_evidence": m1,
+        "diagnostic_rows": load_diagnostic_evidence(diagnostic_dir, daily_dir),
+    }
 
 
 # --------------------------------------------------------------------------
@@ -488,9 +653,6 @@ def data_quality(
     }
 
 
-TRADING_DIR = ART / "trading"
-
-
 def load_trading_state(trading_dir: Path = TRADING_DIR) -> dict:
     """M1 trading-loop artifacts for the attention area (spec M1 §15).
 
@@ -520,6 +682,219 @@ def load_trading_state(trading_dir: Path = TRADING_DIR) -> dict:
     }
 
 
+# --------------------------------------------------------------------------
+# NOW: bounded projection of durable trading facts (single implementation,
+# shared by the static page and GET /api/quant/now via quant_serve)
+# --------------------------------------------------------------------------
+
+SESSION_AM = (dtime(9, 30), dtime(11, 30))
+SESSION_PM = (dtime(13, 0), dtime(15, 0))
+NOW_STALE_AFTER_S = 90  # only enforced while the session clock expects a live loop
+NOW_ALERT_TAIL = 200
+NOW_SOAK_TAIL = 200
+NOW_ATTENTION_CAP = 12
+NOW_RECENT_ALERTS = 10
+NOW_MATERIAL_EVENTS = {"NEW_READY", "POSITION_EXIT_ALERT", "LIVE_CONNECTION_LOST", "DATA_UNTRUSTED"}
+NOW_HUMAN_EVENTS = {"POSITION_OPENED", "POSITION_CLOSED", "HUMAN_SKIP"}
+
+
+def in_trading_session(now: datetime) -> bool:
+    """A-share session clock. A stdlib mirror of the monitor's rule: the
+    stdlib-only renderer/server must not import the pandas-loading monitor."""
+    if now.weekday() >= 5:
+        return False
+    t = now.time()
+    return SESSION_AM[0] <= t <= SESSION_AM[1] or SESSION_PM[0] <= t <= SESSION_PM[1]
+
+
+def _parse_ts(value) -> datetime | None:
+    try:
+        dt = datetime.fromisoformat(str(value))
+    except (ValueError, TypeError):
+        return None
+    return dt if dt.tzinfo else dt.replace(tzinfo=TZ_SHANGHAI)
+
+
+def _latest_events(alerts: list[dict], types: set[str]) -> dict:
+    """{(type, symbol): alert} keeping the newest ts per key (durable stream)."""
+    out: dict = {}
+    for a in alerts:
+        if str(a.get("type")) not in types:
+            continue
+        key = (str(a.get("type")), str(a.get("symbol")))
+        ts = _parse_ts(a.get("ts"))
+        prev = out.get(key)
+        if prev is None or (ts and _parse_ts(prev.get("ts")) is None) or (
+            ts and _parse_ts(prev.get("ts")) and ts >= _parse_ts(prev.get("ts"))
+        ):
+            out[key] = a
+    return out
+
+
+def _human_action(symbol: str, human_events: dict) -> dict | None:
+    for etype, label in (
+        ("POSITION_OPENED", "HOLD(ack-buy)"),
+        ("POSITION_CLOSED", "CLOSED(ack-sell)"),
+        ("HUMAN_SKIP", "SKIP"),
+    ):
+        a = human_events.get((etype, symbol))
+        if a:
+            return {
+                "action": label,
+                "ts": a.get("ts"),
+                "venue": a.get("venue"),
+                "note": a.get("note"),
+            }
+    return None
+
+
+def _agent_action(symbol: str, event_ts: str, briefs: list[dict]) -> dict | None:
+    """Event-matched brief: only a brief recorded at/after the material event
+    may answer it — an older judgement is never projected onto a newer fact."""
+    ev_dt = _parse_ts(event_ts)
+    if ev_dt is None:
+        return None
+    best = None
+    for b in briefs:
+        if str(b.get("symbol")) != symbol:
+            continue
+        b_dt = _parse_ts(b.get("recorded_at"))
+        if b_dt is None or b_dt < ev_dt:
+            continue
+        if best is None or _parse_ts(best.get("recorded_at")) < b_dt:
+            best = b
+    if best is None:
+        return None
+    return {
+        "action": best.get("action"),
+        "decision_id": best.get("decision_id"),
+        "recorded_at": best.get("recorded_at"),
+        "why": best.get("why"),
+        "invalidation": best.get("invalidation"),
+    }
+
+
+def now_snapshot(
+    trading_dir: Path = TRADING_DIR,
+    briefs_dir: Path = BRIEFS_DIR,
+    active_symbols_path: Path = ACTIVE_SYMBOLS_PATH,
+    now: datetime | None = None,
+) -> dict:
+    """NOW view (spec workbench §3.1/§21 + amendments): heartbeat comes from
+    the soak tail, last_scan_at only from records that really scanned
+    (symbols > 0), STALE only while the session clock expects a live loop,
+    and material events come from the durable alert stream, not the
+    last-cycle state.json.events."""
+    now = now or datetime.now(TZ_SHANGHAI)
+    state = read_json(Path(trading_dir) / "state.json") or {}
+    soak = read_jsonl(Path(trading_dir) / "soak.jsonl")[-NOW_SOAK_TAIL:]
+    alerts = read_jsonl(Path(trading_dir) / "alerts.jsonl")[-NOW_ALERT_TAIL:]
+    universe = read_json(active_symbols_path) or {}
+    universe_size = len(universe.get("symbols") or []) or None
+
+    heartbeat_at = soak[-1].get("ts") if soak else None
+    last_scan_at = next((r.get("ts") for r in reversed(soak) if (r.get("symbols") or 0) > 0), None)
+    hb_dt, scan_dt = _parse_ts(heartbeat_at), _parse_ts(last_scan_at)
+    now_dt = _parse_ts(now.isoformat()) or now
+    hb_age = int((now_dt - hb_dt).total_seconds()) if hb_dt else None
+    scan_age = int((now_dt - scan_dt).total_seconds()) if scan_dt else None
+    expected_live = in_trading_session(now_dt)
+    stale = bool(expected_live and hb_age is not None and hb_age > NOW_STALE_AFTER_S)
+    if not state:
+        runtime = "UNKNOWN"
+    elif stale:
+        runtime = "STALE"
+    else:
+        runtime = "HEALTHY"
+
+    briefs = load_briefs(briefs_dir)
+    material = _latest_events(alerts, NOW_MATERIAL_EVENTS)
+    human_events = _latest_events(alerts, NOW_HUMAN_EVENTS)
+
+    def agent_for(symbol: str, ts) -> dict | None:
+        return _agent_action(symbol, ts, briefs)
+
+    def human_for(symbol: str) -> dict | None:
+        return _human_action(symbol, human_events)
+
+    attention: list[dict] = []
+    for sym in state.get("ready") or []:
+        ev = material.get(("NEW_READY", sym)) or {}
+        ts = ev.get("ts") or state.get("as_of")
+        attention.append({
+            "kind": "READY", "symbol": sym, "ts": ts, "price": ev.get("price"),
+            "conditions": ev.get("conditions"),
+            "agent": agent_for(sym, ts), "human": human_for(sym),
+        })
+    for sym in state.get("exit_alerts") or []:
+        ev = material.get(("POSITION_EXIT_ALERT", sym)) or {}
+        ts = ev.get("ts") or state.get("as_of")
+        pos = next((p for p in state.get("positions") or [] if p.get("symbol") == sym), {})
+        attention.append({
+            "kind": "EXIT", "symbol": sym, "ts": ts, "price": pos.get("price") or ev.get("price"),
+            "why": ev.get("why"), "entry_price": pos.get("entry_price"),
+            "pnl": pos.get("pnl"), "venue": pos.get("venue"),
+            "agent": agent_for(sym, ts), "human": human_for(sym),
+        })
+    if state.get("system_unavailable"):
+        ev = material.get(("LIVE_CONNECTION_LOST", "None")) or {}
+        attention.append({
+            "kind": "SYSTEM_UNAVAILABLE", "symbol": None,
+            "ts": ev.get("ts") or state.get("as_of"), "why": ev.get("why"),
+            "price": None, "conditions": None,
+            "agent": None, "human": None,
+        })
+    if state.get("data_trust") == "FAIL":
+        ev = material.get(("DATA_UNTRUSTED", "None")) or {}
+        attention.append({
+            "kind": "DATA_UNTRUSTED", "symbol": None,
+            "ts": ev.get("ts") or state.get("as_of"), "why": ev.get("why"),
+            "price": None, "conditions": None,
+            "agent": None, "human": None,
+        })
+
+    return {
+        "generated_at": now.isoformat(timespec="seconds"),
+        "present": bool(state),
+        "as_of": state.get("as_of"),
+        "day": state.get("day"),
+        "status": state.get("status"),
+        "market": "OPEN" if expected_live else "CLOSED",
+        "expected_live": expected_live,
+        "runtime": runtime,
+        "stale": stale,
+        "heartbeat_at": heartbeat_at,
+        "heartbeat_age_seconds": hb_age,
+        "last_scan_at": last_scan_at,
+        "scan_age_seconds": scan_age,
+        "symbols_scanned": state.get("symbols_scanned"),
+        "universe_size": universe_size,
+        "data_trust": state.get("data_trust") or "UNKNOWN",
+        "ready": state.get("ready") or [],
+        "near": state.get("near") or [],
+        "exit_alerts": state.get("exit_alerts") or [],
+        "positions": state.get("positions") or [],
+        "attention": attention[:NOW_ATTENTION_CAP],
+        "recent_alerts": alerts[-NOW_RECENT_ALERTS:],
+    }
+
+
+def load_timeline(trading_dir: Path = TRADING_DIR, day: str | None = None, limit: int = 100) -> list[dict]:
+    """今日事件时间线: the durable alert stream in time order (one day when
+    known). Only real persisted events — no inferred MARKET_CLOSE/START rows."""
+    rows = []
+    for a in read_jsonl(Path(trading_dir) / "alerts.jsonl"):
+        if day and str(a.get("day") or "") != day:
+            continue
+        rows.append({
+            "ts": a.get("ts"), "type": a.get("type"), "symbol": a.get("symbol"),
+            "what": a.get("what"), "why": a.get("why"), "price": a.get("price"),
+            "venue": a.get("venue"),
+        })
+    rows.sort(key=lambda r: str(r.get("ts")))
+    return rows[-limit:]
+
+
 def build_data(
     snapshot_path: Path = SNAPSHOT_PATH,
     scan_path: Path = LAST_SCAN_PATH,
@@ -528,7 +903,11 @@ def build_data(
     status_path: Path = STATUS_PATH,
     active_path: Path = ACTIVE_PATH,
     legacy_path: Path = LEGACY_PATH,
-    outcomes_path: Path = OUTCOMES_PATH,
+    trading_dir: Path = TRADING_DIR,
+    diagnostic_dir: Path = TRADING_DIAGNOSTIC_DIR,
+    daily_dir: Path = DAILY_CACHE_DIR,
+    active_symbols_path: Path = ACTIVE_SYMBOLS_PATH,
+    semantic_dir: Path = SEMANTIC_DIR,
 ) -> dict:
     snapshot = read_json(snapshot_path)
     scan = read_json(scan_path)
@@ -536,12 +915,19 @@ def build_data(
     obs = parse_obs_log(obs_path)
     proofs = parse_proof_rows(status_path)
     legacy_symbols = load_legacy_symbols(legacy_path)
-    settled = settled_trade_count(outcomes_path)
-    forward_triggers = sum(
-        int(r.get("triggers") or 0)
-        for r in obs
-        if str(r.get("triggers", "")).strip().isdigit()
+    real_trend = load_real_trend(
+        trading_dir,
+        diagnostic_dir=diagnostic_dir,
+        daily_dir=daily_dir,
+        active_symbols_path=active_symbols_path,
+        semantic_dir=semantic_dir,
+    )
+    now = now_snapshot(
+        trading_dir=trading_dir,
+        briefs_dir=briefs_dir,
+        active_symbols_path=active_symbols_path,
     )
+    settled = real_trend["forward"]["settled"]
     results = harvest_strategy_results()
     best = best_strategy_row(results)
     decision = today_decision(briefs)
@@ -550,7 +936,10 @@ def build_data(
         "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
         "warning": STRATEGY_WARNING,
         "not_a_buy_note": NOT_A_BUY_NOTE,
-        "trading": load_trading_state(),
+        "trading": load_trading_state(trading_dir),
+        "now": now,
+        "timeline": load_timeline(trading_dir, day=now.get("day")),
+        "real_trend": real_trend,
         "kpi": {
             "today_decision": decision["state"],
             "live_triggers": len((scan or {}).get("triggers") or []),
@@ -583,7 +972,7 @@ def build_data(
             "best_annualized_pct": (best or {}).get("annualized_pct"),
             "best_trades": (best or {}).get("trades"),
             "pit_bias": True,
-            "forward_triggers": forward_triggers,
+            "forward_observations": real_trend["forward"]["count"],
             "forward_settled": settled,
             "forward_hit_rate": "—" if settled < 10 else None,
             "results": results,
@@ -872,53 +1261,88 @@ TEMPLATE = """<!DOCTYPE html>
   <div class="banner-warn" id="strategy-warning"></div>
   <div class="banner-degraded" id="dq-banner" style="display:none"></div>
 
+  <div class="card" id="now-card">
+    <h2>NOW <span class="scope live">LIVE</span> <span class="cnt" id="now-meta"></span></h2>
+    <div class="nowgrid" id="now-grid"></div>
+    <div id="now-stale" class="banner-degraded" style="display:none;margin-top:10px"></div>
+  </div>
+
   <div class="card" id="attention-card">
-    <h2>现在需要我做什么？ <span class="cnt" id="att-meta">交易盯盘 · 30s 自动刷新</span></h2>
+    <h2>现在需要我做什么？ <span class="scope live">LIVE</span> <span class="cnt" id="att-meta">交易盯盘 · 30s 自动刷新</span></h2>
     <div id="att-status" style="font-weight:700;font-size:14px;margin-bottom:8px"></div>
+    <div id="att-actions"></div>
     <div id="att-items" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px"></div>
     <div style="display:flex;gap:24px;flex-wrap:wrap">
       <div style="flex:1;min-width:260px">
-        <div class="mut" style="font-weight:600;margin-bottom:4px">今天盯什么（READY / NEAR）</div>
+        <div class="mut" style="font-weight:600;margin-bottom:4px">次级 Watch（NEAR — 未到行动级）</div>
         <div id="att-watch" class="mut"></div>
       </div>
-      <div style="flex:1.4;min-width:300px">
-        <div class="mut" style="font-weight:600;margin-bottom:4px">我现在持有什么</div>
-        <div id="att-positions" class="mut"></div>
-      </div>
     </div>
     <div id="att-alerts" style="margin-top:8px;font-size:12px"></div>
   </div>
 
+  <div class="card" id="positions-card">
+    <h2>Open Positions <span class="scope live">LIVE</span> <span class="cnt">持仓生命周期独立于候选池 · 只由 ack 建立/关闭</span></h2>
+    <div id="att-positions-box"></div>
+  </div>
+
+  <div class="card" id="timeline-card">
+    <h2>今日事件时间线 <span class="scope live">LIVE</span> <span class="cnt" id="tl-meta">durable alerts · 只列真实持久化事件</span></h2>
+    <ul class="tl" id="tl-list"></ul>
+  </div>
+
+  <div class="card" id="real-trend-card">
+    <h2>真实运行数据趋势 <span class="scope live">LIVE · HISTORICAL</span> <span class="cnt" id="rt-meta">M1 trading artifacts · 缺失保持缺失, 不补曲线</span></h2>
+    <dl class="kv" id="m1-evidence" style="margin-bottom:10px"></dl>
+    <div id="rt-chart"></div>
+    <div id="rt-forward" style="margin-top:10px;font-size:13px"></div>
+    <div id="rt-diagnostic" style="margin-top:12px"></div>
+    <div class="mut" style="font-weight:600;margin:12px 0 4px;font-size:12px">真实 monitor 记录（trading/soak.jsonl · 一行 = 一次真实周期, 不去失真）</div>
+    <div style="overflow-x:auto"><table>
+      <thead><tr><th>时间</th><th>状态</th><th class="num-h">扫描数量</th><th class="num-h">universe size</th><th class="num-h">告警/事件数</th><th>来源</th></tr></thead>
+      <tbody id="rt-rows"></tbody>
+    </table></div>
+  </div>
+
   <div class="kpi">
     <div class="k"><div class="v" id="kpi-decision">—</div><div class="l">今日决策</div></div>
     <div class="k"><div class="v" id="kpi-triggers">—</div><div class="l">实时触发</div></div>
     <div class="k"><div class="v" id="kpi-candidates">—</div><div class="l">活跃候选</div></div>
-    <div class="k"><div class="v" id="kpi-settled">—</div><div class="l">前向已结算交易</div></div>
+    <div class="k"><div class="v" id="kpi-settled">—</div><div class="l">前向已结算交易（正式）</div></div>
     <div class="k"><div class="v" id="kpi-evidence">—</div><div class="l">策略证据</div></div>
   </div>
 
   <div class="card">
-    <h2>今日动作候选 <span class="cnt" id="scan-meta"></span></h2>
+    <h2>今日动作候选 <span class="scope today">TODAY · LIVE</span> <span class="cnt" id="scan-meta"></span></h2>
     <div id="trigger-box"></div>
   </div>
 
   <div class="layout-board">
   <div class="card">
-    <h2>价值 · 质量机会板 <span class="cnt" id="board-meta"></span></h2>
+    <h2>价值 · 质量机会板 <span class="scope today">TODAY</span> <span class="cnt" id="board-meta"></span>
+      <button class="btn glossary-toggle" id="glossary-open" type="button" aria-expanded="false" aria-controls="glossary-drawer">查看指标备注</button>
+    </h2>
     <div style="overflow-x:auto"><table id="board">
       <thead><tr id="board-head"></tr></thead>
       <tbody id="board-rows"></tbody>
     </table></div>
     <div class="mut" style="font-size:11.5px;margin-top:8px" id="not-a-buy"></div>
   </div>
-  <aside class="card note-side">
-    <h2>指标备注 <span class="cnt">点击任一指标 / 单元格弹出详细说明</span></h2>
-    <div class="g-list" id="glossary-list"></div>
-  </aside>
   </div>
 
+  <div class="drawer-backdrop" id="glossary-backdrop" hidden></div>
+  <aside class="drawer" id="glossary-drawer" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="glossary-title">
+    <div class="drawer-head">
+      <h2 id="glossary-title">指标备注 <span class="cnt">点击任一指标 / 单元格弹出详细说明</span></h2>
+      <button class="modal-x" id="glossary-close" type="button" title="关闭" aria-label="关闭指标备注">×</button>
+    </div>
+    <div class="drawer-body">
+      <div class="g-list" id="glossary-list"></div>
+    </div>
+  </aside>
+
   <div class="card">
-    <h2>历史持仓 · 套牢仓位 <span class="cnt" id="legacy-count">自选/持仓名单 — 诊断位, 不是机会宇宙</span></h2>
+    <h2>历史持仓 · 套牢仓位 <span class="scope hist">HISTORICAL</span> <span class="cnt" id="legacy-count">自选/持仓名单 — 诊断位, 不是机会宇宙</span></h2>
     <div class="mut question" id="legacy-question"></div>
     <div style="overflow-x:auto"><table>
       <thead><tr><th>代码</th><th>名称</th><th>现价</th><th>综合分</th><th>价值</th><th>质量</th><th>Timing</th>
@@ -929,7 +1353,7 @@ TEMPLATE = """<!DOCTYPE html>
 
   <div class="grid two">
     <div class="card">
-      <h2>策略证据</h2>
+      <h2>策略证据 <span class="scope research">RESEARCH · frozen S3</span></h2>
       <div id="strategy-box"></div>
       <details style="margin-top:12px">
         <summary>策略实验历史 (基线 / S1 / S2 / S3)</summary>
@@ -940,17 +1364,19 @@ TEMPLATE = """<!DOCTYPE html>
       </details>
     </div>
     <div class="card">
-      <h2>前向证据 <span class="cnt">只有真实前向观察, 无合成占位</span></h2>
+      <h2>前向证据 <span class="scope research">RESEARCH · FORMAL</span> <span class="cnt">正式 = trading/forward.json · 无合成占位</span></h2>
+      <div id="formal-forward" style="font-size:13px;margin-bottom:10px"></div>
+      <div class="mut" style="font-weight:600;font-size:12px;margin-bottom:4px">历史每日扫描日志（旧每日链路口径 — 仅历史兼容, 非当前 M1 truth）</div>
       <table>
         <thead><tr><th>日期</th><th>时间</th><th style="text-align:right">扫描只数</th><th style="text-align:right">触发数</th><th>决策</th><th>备注</th></tr></thead>
         <tbody id="obs-rows"></tbody>
       </table>
-      <div class="mut" style="font-size:11.5px;margin-top:8px">入场 / D+1 / D+3 / D+5 / D+8 价格路径与最大有利·不利偏移 (MFE/MAE) 在人工结算产生真实记录后展示; 当前结算笔数见 Forward Settled Trades。</div>
+      <div class="mut" style="font-size:11.5px;margin-top:8px">入场 / D+1 / D+3 / D+5 / D+8 价格路径与最大有利·不利偏移 (MFE/MAE) 在正式 forward observation 产生后展示；诊断性记录只出现在「真实运行数据趋势」卡并明确标记 diagnostic。</div>
     </div>
   </div>
 
   <div class="card">
-    <h2>数据质量</h2>
+    <h2>数据质量 <span class="scope today">TODAY</span></h2>
     <div id="dq-box"></div>
   </div>
 
@@ -960,6 +1386,21 @@ TEMPLATE = """<!DOCTYPE html>
     <a href="/engineering">工程 / 审计 → /engineering</a>。
   </footer>
 </div>
+<div class="modal" id="trade-modal" hidden>
+  <div class="modal-box" style="max-width:480px">
+    <div class="modal-head"><h3 id="tm-title"></h3><button class="modal-x" id="tm-close" title="关闭">×</button></div>
+    <div class="modal-body">
+      <div class="form-row"><label>symbol</label><input id="tm-symbol" readonly></div>
+      <div class="form-row"><label>shares</label><input id="tm-shares" type="number" min="1" step="1"></div>
+      <div class="form-row"><label>price</label><input id="tm-price" type="number" min="0.0001" step="0.0001"></div>
+      <div class="form-row"><label>venue</label><select id="tm-venue"><option value="paper">paper</option><option value="real">real</option></select></div>
+      <div class="form-row"><label>executed_at</label><input id="tm-time"></div>
+      <div class="form-row"><label>note</label><input id="tm-note" placeholder="可选备注"></div>
+      <div class="form-msg" id="tm-msg"></div>
+      <div class="btnrow"><button class="btn primary" id="tm-submit">确认记录</button></div>
+    </div>
+  </div>
+</div>
 <div class="modal" id="metric-modal" hidden>
   <div class="modal-box">
     <div class="modal-head"><h3 id="mm-title"></h3><button class="modal-x" id="mm-close" title="关闭">×</button></div>
@@ -981,6 +1422,7 @@ CSS = """\
   --acc:#4cc2ff; --green:#3fb950; --amber:#d29922; --red:#f85149;
 }
 *{box-sizing:border-box;margin:0;padding:0}
+body{overflow-x:hidden}
 body{background:var(--bg);color:var(--tx);font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,sans-serif;padding:24px 20px 60px}
 .wrap{max-width:1280px;margin:0 auto}
 a{color:var(--acc);text-decoration:none} a:hover{text-decoration:underline}
@@ -1024,18 +1466,59 @@ tr:last-child td{border-bottom:none}
 .empty .t{font-size:16px;font-weight:700;color:var(--tx);letter-spacing:.5px}
 .empty .s{font-size:12.5px;color:var(--mut);margin-top:6px}
 .question{border-left:3px solid var(--acc);padding:6px 12px;margin-bottom:12px;font-size:13px;color:#b7c2d4}
-.layout-board{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:16px;margin-top:16px;align-items:start}
+.scope{font-size:10px;font-weight:700;letter-spacing:.6px;padding:1px 8px;border-radius:10px;border:1px solid var(--line2);color:var(--dim)}
+.scope.live{color:var(--green);border-color:var(--green)}
+.scope.today{color:var(--acc);border-color:var(--acc)}
+.scope.hist{color:var(--amber);border-color:var(--amber)}
+.scope.research{color:var(--mut)}
+.nowgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
+.nowgrid .n{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
+.nowgrid .n .k{font-size:10.5px;color:var(--dim);letter-spacing:.4px}
+.nowgrid .n .v{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:2px}
+.action-card{border:1px solid var(--line2);border-radius:10px;padding:12px 14px;margin-bottom:10px;background:var(--panel2)}
+.action-card .ac-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
+.action-card .ac-kind{font-size:11px;font-weight:700;letter-spacing:.5px;padding:2px 9px;border-radius:12px}
+.ac-kind.READY{color:#163a22;background:var(--green)}
+.ac-kind.EXIT{color:#3b1110;background:var(--red)}
+.ac-kind.SYSTEM_UNAVAILABLE,.ac-kind.DATA_UNTRUSTED{color:#3b1110;background:var(--red)}
+.ac-kind.NEAR{color:#3a2c0d;background:var(--amber)}
+.threestate{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:12.5px;margin:8px 0}
+.threestate .st-k{color:var(--dim);letter-spacing:.4px;font-size:11px;padding-top:1px}
+.btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
+.btn{font-size:12px;font-weight:600;padding:4px 12px;border-radius:8px;border:1px solid var(--line2);background:var(--panel);color:var(--tx);cursor:pointer}
+.btn:hover{border-color:var(--acc);color:var(--acc)}
+.btn.primary{background:var(--acc);border-color:var(--acc);color:#062a3d}
+.btn.danger{border-color:var(--red);color:var(--red)}
+.tl{list-style:none;font-size:12.5px}
+.tl li{display:flex;gap:10px;padding:3px 0;border-bottom:1px dashed var(--line)}
+.tl li:last-child{border-bottom:none}
+.tl .ts{color:var(--dim);font-variant-numeric:tabular-nums;white-space:nowrap}
+.form-row{display:flex;gap:10px;margin-bottom:8px;align-items:center}
+.form-row label{font-size:12px;color:var(--mut);min-width:90px}
+.form-row input,.form-row select{background:var(--panel2);border:1px solid var(--line2);border-radius:6px;color:var(--tx);padding:5px 8px;font-size:13px;flex:1}
+.form-msg{font-size:12.5px;margin-top:6px;min-height:16px}
+.layout-board{display:block;margin-top:16px}
 .layout-board .card{margin-top:0}
-.note-side{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}
-@media(max-width:1080px){.layout-board{grid-template-columns:1fr}.note-side{position:static;max-height:none}}
+.glossary-toggle{margin-left:auto;white-space:nowrap}
+.drawer-backdrop{position:fixed;inset:0;background:rgba(3,6,10,.66);z-index:60;opacity:0;transition:opacity .2s ease}
+.drawer-backdrop[hidden]{display:none}
+.drawer-backdrop.is-open{opacity:1}
+.drawer{position:fixed;top:0;right:0;width:min(420px,100vw);max-width:100%;height:100vh;height:100dvh;overflow-y:auto;background:var(--panel);border-left:1px solid var(--line2);box-shadow:-18px 0 60px rgba(0,0,0,.45);z-index:61;transform:translateX(100%);transition:transform .2s ease;padding:18px}
+.drawer[hidden]{display:none}
+.drawer.is-open{transform:translateX(0)}
+.drawer-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px}
+.drawer-head h2{font-size:14px;letter-spacing:.3px;color:#b7c2d4;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
+.drawer-head .cnt{font-size:11px;color:var(--dim);font-weight:400}
+.drawer-body{padding-top:14px}
+@media(max-width:480px){.drawer{width:100vw;padding:14px}}
+@media(prefers-reduced-motion:reduce){.drawer,.drawer-backdrop{transition:none}}
 .g-list{display:flex;flex-direction:column;gap:6px}
-.g-item{display:flex;align-items:baseline;gap:8px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font-size:12.5px;background:var(--panel2)}
+.g-item{display:flex;align-items:baseline;gap:8px;width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:12.5px;text-align:left;color:var(--tx);background:var(--panel2);cursor:pointer}
 .g-item:hover{border-color:var(--acc)}
 .g-item .gk{font-weight:700;color:var(--acc);white-space:nowrap}
-.g-item .g1{color:var(--mut);font-size:11.5px;line-height:1.45}
+.g-item .g1{min-width:0;color:var(--mut);font-size:11.5px;line-height:1.45;overflow-wrap:anywhere}
 [data-m]{cursor:help}
-.g-item{cursor:pointer}
-.modal{position:fixed;inset:0;background:rgba(3,6,10,.66);display:flex;align-items:flex-start;justify-content:center;padding:6vh 16px;z-index:50;backdrop-filter:blur(2px)}
+.modal{position:fixed;inset:0;background:rgba(3,6,10,.66);display:flex;align-items:flex-start;justify-content:center;padding:6vh 16px;z-index:70;backdrop-filter:blur(2px)}
 .modal[hidden]{display:none}
 .modal-box{background:var(--panel);border:1px solid var(--line2);border-radius:14px;max-width:640px;width:100%;max-height:82vh;overflow:auto;box-shadow:0 18px 60px rgba(0,0,0,.5)}
 .modal-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel)}
@@ -1093,15 +1576,44 @@ function closeMetric(){
   $('metric-modal').hidden = true;
 }
 function renderGlossary(){
-  $('glossary-list').innerHTML = Object.entries(GLOSSARY).map(([k,g])=>`<div class="g-item" data-m="${esc(k)}" title="点击查看 ${esc(g.t)} 的详细说明"><span class="gk">${esc(g.t)}</span><span class="g1">${esc(g.h||'')}</span></div>`).join('');
+  $('glossary-list').innerHTML = Object.entries(GLOSSARY).map(([k,g])=>`<button type="button" class="g-item" data-m="${esc(k)}" title="点击查看 ${esc(g.t)} 的详细说明"><span class="gk">${esc(g.t)}</span><span class="g1">${esc(g.h||'')}</span></button>`).join('');
 }
+function setGlossaryOpen(open){
+  const trigger = $('glossary-open');
+  const drawer = $('glossary-drawer');
+  const backdrop = $('glossary-backdrop');
+  if(!trigger || !drawer || !backdrop) return;
+  trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
+  drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
+  if(open){
+    drawer.hidden = false;
+    backdrop.hidden = false;
+    drawer.classList.add('is-open');
+    backdrop.classList.add('is-open');
+    $('glossary-close').focus();
+  } else {
+    drawer.classList.remove('is-open');
+    backdrop.classList.remove('is-open');
+    drawer.hidden = true;
+    backdrop.hidden = true;
+    trigger.focus();
+  }
+}
+function openGlossary(){ setGlossaryOpen(true); }
+function closeGlossary(){ setGlossaryOpen(false); }
 document.addEventListener('click', (e)=>{
   const el = e.target.closest('[data-m]');
   if(el){ openMetric(el.dataset.m); return; }
+  if(e.target.id === 'glossary-open'){ openGlossary(); return; }
+  if(e.target.id === 'glossary-close' || e.target.id === 'glossary-backdrop'){ closeGlossary(); return; }
   if(e.target.id === 'mm-close'){ closeMetric(); return; }
   if(e.target.closest('#metric-modal') && !e.target.closest('.modal-box')){ closeMetric(); }
 });
-document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') closeMetric(); });
+document.addEventListener('keydown', (e)=>{
+  if(e.key !== 'Escape') return;
+  if(!$('glossary-drawer').hidden){ closeGlossary(); return; }
+  closeMetric();
+});
 
 function kpiColor(v){ return v==null ? 'var(--dim)' : 'var(--tx)'; }
 
@@ -1129,43 +1641,370 @@ function drawTriggers(trs, live){
       <td class="rf">${(t.red_flags&&t.red_flags.length)?esc(zhFlags(t.red_flags)):'无候选红旗记录'}</td></tr>`).join('')}</tbody></table></div>`;
 }
 
-function renderTrading(t){
-  const st = $('att-status'), items = $('att-items'), watch = $('att-watch'), pos = $('att-positions'), al = $('att-alerts');
-  if(!t || !t.present){
-    st.textContent = '盯盘监控未运行 — 启动: python tools/quant_trading_monitor.py session';
-    st.style.color = 'var(--amber)'; items.innerHTML=''; watch.textContent='—'; pos.textContent='无持仓记录'; al.innerHTML=''; return;
+/* ---- NOW / Action Queue / Positions: single fact = /api/quant/now ---- */
+const fmtAge = (s) => s==null ? '—' : (s < 90 ? s+'s' : Math.floor(s/60)+'m'+(s%60)+'s');
+const nowTs = (v) => v ? String(v).slice(11,19) : '—';
+let lastNow = null;
+
+function renderNow(n){
+  lastNow = n || lastNow;
+  n = n || {};
+  const grid = $('now-grid'), st = $('now-stale');
+  $('now-meta').textContent = n.present
+    ? `as_of ${nowTs(n.as_of)} · generated ${nowTs(n.generated_at)}`
+    : 'monitor 尚未运行 — 无 NOW 事实';
+  if(!n.present){
+    grid.innerHTML = '<div class="n"><div class="k">Runtime</div><div class="v" style="color:var(--amber)">UNKNOWN</div></div>' +
+      '<div class="n"><div class="k">说明</div><div class="v" style="font-size:12px">启动: python tools/quant_trading_monitor.py session</div></div>';
+    st.style.display = 'none';
+    renderAttention(n);
+    return;
   }
-  const s = t.state || {};
-  if (s.system_unavailable){ st.textContent = 'SYSTEM_UNAVAILABLE — 系统不可用/数据不可信（这不是 NO_TRADE）'; st.style.color = 'var(--red)'; }
-  else if (s.market_no_trade){ st.textContent = `有效 NO_TRADE — 市场已扫描 ${(s.symbols_scanned??0)} 只，当前无 READY 机会`; st.style.color = 'var(--acc)'; }
-  else if (s.status === 'MARKET_CLOSED'){ st.textContent = '已收盘 — 监控待下一交易时段（无合成活动）'; st.style.color = 'var(--mut)'; }
-  else if (s.status === 'ALERTS'){ st.textContent = `需要行动 — READY ${(s.ready||[]).length} · EXIT_ALERT ${(s.exit_alerts||[]).length}`; st.style.color = 'var(--amber)'; }
-  else { st.textContent = '监控运行中 — ' + (s.status||'?'); st.style.color = 'var(--acc)'; }
-  const chips = [];
-  (s.ready||[]).forEach(sym=>chips.push(`<span class="chip B">READY ${esc(sym)}</span>`));
-  (s.exit_alerts||[]).forEach(sym=>chips.push(`<span class="chip S">EXIT_ALERT ${esc(sym)}</span>`));
-  (s.near||[]).forEach(sym=>chips.push(`<span class="chip gray">NEAR ${esc(sym)}</span>`));
-  items.innerHTML = chips.join('') || '<span class="dim">当前无 attention 项</span>';
-  const watchList = [...(s.ready||[]), ...(s.near||[])];
-  watch.textContent = watchList.length ? watchList.join(', ') : '当前无 READY/NEAR — 快层持续扫描活跃宇宙';
-  const ps = t.open_positions || [];
-  pos.innerHTML = ps.length ? ps.map(p=>`<div><code>${esc(p.symbol)}</code> ${p.shares}股 @${p.entry_price}` +
-    (p.price!=null?` → 现价 ${p.price}`:'') + (p.pnl!=null?` · 盈亏 ${p.pnl}`:'') +
-    ` · <b>${esc(p.state||'HOLD')}</b>${p.exit_reason?` · ${esc(p.exit_reason)}`:''}</div>`).join('') : '无持仓';
-  al.innerHTML = (t.alerts||[]).slice(0,5).map(a=>
-    `<div>· <b>${esc(a.type||'')}</b> ${a.symbol?esc(a.symbol)+' — ':''}${esc(a.what||'')}${a.why?` · ${esc(a.why)}`:''}</div>`).join('');
+  const cov = (n.symbols_scanned!=null && n.universe_size) ? `${n.symbols_scanned}/${n.universe_size}`
+            : (n.universe_size ? `—/${n.universe_size}` : '—');
+  const cells = [
+    ['市场', n.market, n.market==='OPEN'?'var(--green)':'var(--mut)'],
+    ['Runtime', n.runtime, n.runtime==='HEALTHY'?'var(--green)':(n.runtime==='STALE'?'var(--red)':'var(--amber)')],
+    ['交易时段', n.expected_live?'ACTIVE':'CLOSED', n.expected_live?'var(--green)':'var(--mut)'],
+    ['最后心跳', `${nowTs(n.heartbeat_at)} · age ${fmtAge(n.heartbeat_age_seconds)}`],
+    ['最后成功扫描', n.last_scan_at ? `${nowTs(n.last_scan_at)} · age ${fmtAge(n.scan_age_seconds)}` : '无真实扫描记录'],
+    ['扫描覆盖', cov],
+    ['Data trust', n.data_trust, n.data_trust==='PASS'?'var(--green)':(n.data_trust==='FAIL'?'var(--red)':'var(--amber)')],
+    ['READY', (n.ready||[]).length, (n.ready||[]).length?'var(--green)':null],
+    ['NEAR', (n.near||[]).length, null],
+    ['EXIT', (n.exit_alerts||[]).length, (n.exit_alerts||[]).length?'var(--red)':null],
+    ['Open positions', (n.positions||[]).length, null],
+  ];
+  grid.innerHTML = cells.map(([k,v,c])=>
+    `<div class="n"><div class="k">${esc(k)}</div><div class="v"${c?` style="color:${c}"`:''}>${esc(String(v??'—'))}</div></div>`).join('');
+  // STALE fires only while the session clock expects a live loop (server-side rule)
+  if(n.stale){
+    st.className = 'banner-degraded'; st.style.display = 'block';
+    st.textContent = `RUNTIME STALE — 交易时段内心跳超龄 (>90s) · Last success ${nowTs(n.heartbeat_at)} · Age ${fmtAge(n.heartbeat_age_seconds)}`;
+  } else if(!n.expected_live){
+    st.className = ''; st.style.display = 'block';
+    st.style.cssText = 'display:block;margin-top:10px;color:var(--dim);font-size:12px';
+    st.textContent = '非交易时段 — 显示最后心跳 / 最后成功扫描，不按心跳 age 报故障';
+  } else {
+    st.style.display = 'none';
+  }
+  renderAttention(n);
+}
+
+function renderAttention(n){
+  const statusEl = $('att-status');
+  const state = n || {};
+  if(!state.present){
+    statusEl.textContent = '盯盘监控未运行 — 启动: python tools/quant_trading_monitor.py session';
+    statusEl.style.color = 'var(--amber)';
+  } else if(state.status === 'SYSTEM_UNAVAILABLE'){
+    statusEl.textContent = 'SYSTEM_UNAVAILABLE — 系统不可用/数据不可信（这不是 NO_TRADE）';
+    statusEl.style.color = 'var(--red)';
+  } else if(state.data_trust === 'FAIL'){
+    statusEl.textContent = 'DATA_UNTRUSTED — semantic gate fail-closed，触发条件被抑制（这与系统失联是两回事）';
+    statusEl.style.color = 'var(--red)';
+  } else if((state.ready||[]).length || (state.exit_alerts||[]).length){
+    statusEl.textContent = `需要行动 — READY ${(state.ready||[]).length} · EXIT ${(state.exit_alerts||[]).length}`;
+    statusEl.style.color = 'var(--amber)';
+  } else if(state.status === 'MARKET_CLOSED'){
+    statusEl.textContent = '已收盘 — 监控待下一交易时段（无合成活动）';
+    statusEl.style.color = 'var(--mut)';
+  } else {
+    statusEl.textContent = '有效扫描 · 无机会 — 市场已扫描，当前无 READY/EXIT';
+    statusEl.style.color = 'var(--acc)';
+  }
+  const items = state.attention || [];
+  $('att-actions').innerHTML = items.length ? items.map(actionCardHTML).join('')
+    : '<div class="mut" style="font-size:12.5px;margin-bottom:8px">当前无需要行动的事项（无 READY / EXIT / 系统事件）</div>';
+  const near = state.near || [];
+  $('att-watch').textContent = near.length ? near.join(', ') : '当前无 NEAR';
+  const alerts = state.recent_alerts || [];
+  $('att-alerts').innerHTML = alerts.length ? alerts.slice().reverse().slice(0,5).map(a=>
+    `<div>· <b>${esc(a.type||'')}</b> ${a.symbol?esc(a.symbol)+' — ':''}${esc(a.what||'')}${a.why?` · ${esc(a.why)}`:''}</div>`).join('') : '';
+}
+
+const agentState = (a) => a
+  ? `<span class="chip B">${esc(a.action||'?')}</span> <span class="dim">${esc(a.decision_id||'')}</span>${a.why?`<div class="mut" style="font-size:12px">为什么: ${esc(a.why)}</div>`:''}${a.invalidation?`<div class="mut" style="font-size:12px">失效: ${esc(a.invalidation)}</div>`:''}`
+  : '<span class="chip gray">尚未复核</span> <span class="dim">没有晚于本事件的 Agent brief</span>';
+const humanState = (h) => h
+  ? `<span class="chip NEAR">${esc(h.action||'?')}</span>${h.venue?` <span class="dim">venue ${esc(h.venue)}</span>`:''}${h.note?` <span class="dim">· ${esc(h.note)}</span>`:''} <span class="dim">${nowTs(h.ts)}</span>`
+  : '<span class="dim">NO ACTION YET</span>';
+
+function actionCardHTML(it){
+  const head = `<div class="ac-head">
+    <span class="ac-kind ${esc(it.kind)}">${esc(it.kind)}</span>
+    ${it.symbol?`<code>${esc(it.symbol)}</code>`:''}
+    ${it.price!=null?`<span class="num">${fmt(it.price)}</span>`:''}
+    <span class="dim">${nowTs(it.ts)}</span>
+    ${it.entry_price!=null?`<span class="dim">entry ${fmt(it.entry_price)}</span>`:''}
+    ${it.pnl!=null?`<span class="num">P&L ${fmt(it.pnl)}</span>`:''}
+    ${it.venue?`<span class="chip gray">${esc(it.venue)}</span>`:''}
+  </div>`;
+  let runtime = '', btns = '';
+  if(it.kind === 'READY'){
+    const c = it.conditions || {};
+    runtime = `<div class="mut" style="font-size:12.5px">Deterministic: pullback ${fmt(c.pullback_5d!=null?c.pullback_5d*100:null,2)}% · 量比 ${fmt(c.volume_ratio_20d)} · 1d strength ${fmt(c.strength_1d)} — 冻结入场条件全部成立</div>`;
+    btns = [['ack-buy','Paper Buy','paper','primary'],['ack-buy','Record Real Buy','real','danger'],['skip','Skip',null,''],
+            ['ask','Ask Agent',null,''],['keep','Keep Watching',null,'']];
+  } else if(it.kind === 'EXIT'){
+    runtime = `<div class="mut" style="font-size:12.5px">触发: ${esc(it.why||'冻结退出规则')}</div>`;
+    btns = [['ack-sell','Paper Sell','paper','primary'],['ack-sell','Record Real Sell','real','danger'],['ask','Ask Agent',null,'']];
+  } else {
+    runtime = `<div class="mut" style="font-size:12.5px">${esc(it.why||'系统级事件 — 需要人知晓')}</div>`;
+  }
+  const btnHTML = btns.map(([k,label,venue,cls]) =>
+    `<button class="btn ${cls}" data-act="${k}" data-symbol="${esc(it.symbol||'')}" ${venue?`data-venue="${venue}"`:''}
+      data-shares="${esc((lastNow&&((lastNow.positions||[]).find(p=>p.symbol===it.symbol))||{}).shares??'')}"
+      data-price="${esc(it.price??'')}">${esc(label)}</button>`).join('');
+  return `<div class="action-card" data-kind="${esc(it.kind)}" data-symbol="${esc(it.symbol||'')}">${head}
+    ${runtime}
+    <div class="threestate">
+      <span class="st-k">RUNTIME</span><span>${esc(it.kind)}</span>
+      <span class="st-k">AGENT</span><span>${agentState(it.agent)}</span>
+      <span class="st-k">HUMAN</span><span>${humanState(it.human)}</span>
+    </div>
+    <div class="btnrow">${btnHTML}</div>
+  </div>`;
 }
-async function pollAttention(){
+
+/* ---- Open Positions ---- */
+function renderPositions(positions){
+  const box = $('att-positions-box');
+  if(!positions || !positions.length){
+    box.innerHTML = '<div class="mut" style="font-size:12.5px">无持仓记录 — Position 只由用户 ack-buy 建立</div>';
+    return;
+  }
+  box.innerHTML = positions.map(p=>{
+    const days = p.entry_date ? Math.max(0, Math.floor((Date.now() - Date.parse(p.entry_date)) / 86400000)) : null;
+    return `<div class="action-card"><div class="ac-head">
+      <code>${esc(p.symbol)}</code><span class="chip gray">${esc(p.venue||'paper')}</span>
+      <span class="num">${fmt(p.shares,0)}股</span>
+      <span class="dim">entry ${fmt(p.entry_price)}</span>
+      ${p.price!=null?`<span class="num">现价 ${fmt(p.price)}</span>`:''}
+      ${p.pnl!=null?`<span class="num" style="color:${p.pnl>=0?'var(--green)':'var(--red)'}">P&L ${fmt(p.pnl)}</span>`:''}
+      ${days!=null?`<span class="dim">Holding D+${days}</span>`:''}
+      <span class="chip ${p.state==='EXIT_ALERT'?'EXIT':'gray'}">${esc(p.state||'?')}</span>
+    </div>
+    ${p.exit_reason?`<div class="rf">exit_rule: ${esc(p.exit_reason)}</div>`:''}
+    <div class="btnrow">
+      <button class="btn primary" data-act="ack-sell" data-symbol="${esc(p.symbol)}" data-venue="${esc(p.venue||'paper')}" data-shares="${esc(p.shares)}" data-price="${esc(p.price??'')}">Paper Sell</button>
+      <button class="btn danger" data-act="ack-sell" data-symbol="${esc(p.symbol)}" data-venue="real" data-shares="${esc(p.shares)}" data-price="${esc(p.price??'')}">Record Real Sell</button>
+      <button class="btn" data-act="ask" data-symbol="${esc(p.symbol)}">Ask Agent</button>
+    </div></div>`;
+  }).join('');
+}
+
+/* ---- trade modal (canonical ack POST; the server never invents fields) ---- */
+let tmKind = 'ack-buy';
+function openTrade(kind, symbol, venue, shares, price){
+  tmKind = kind;
+  $('tm-title').textContent = kind === 'skip' ? '记录 SKIP 决定' : (kind === 'ack-buy' ? `记录买入 — ${symbol||''}` : `记录卖出（全仓平仓）— ${symbol||''}`);
+  $('tm-symbol').value = symbol || '';
+  $('tm-shares').value = shares || '';
+  $('tm-shares').parentElement.style.display = kind === 'skip' ? 'none' : '';
+  $('tm-price').value = price || '';
+  if(venue) $('tm-venue').value = venue;
+  $('tm-venue').parentElement.style.display = kind === 'skip' ? 'none' : '';
+  $('tm-time').value = new Date().toISOString();
+  $('tm-note').value = '';
+  $('tm-msg').textContent = '';
+  $('tm-msg').style.color = '';
+  $('trade-modal').hidden = false;
+}
+async function submitTrade(){
+  const payload = {
+    symbol: $('tm-symbol').value.trim(),
+    executed_at: $('tm-time').value.trim(),
+    note: $('tm-note').value.trim(),
+  };
+  if(tmKind === 'skip'){
+    payload.price = parseFloat($('tm-price').value);
+  } else {
+    payload.shares = parseInt($('tm-shares').value, 10);
+    payload.price = parseFloat($('tm-price').value);
+    payload.venue = $('tm-venue').value;
+  }
+  const msg = $('tm-msg');
+  msg.textContent = '记录中…'; msg.style.color = 'var(--mut)';
   try{
-    const r = await fetch('/api/attention', {cache:'no-store'});
+    const r = await fetch('/api/quant/' + tmKind, {
+      method: 'POST', headers: {'Content-Type': 'application/json'},
+      body: JSON.stringify(payload),
+    });
+    const j = await r.json().catch(()=>({}));
+    if(r.ok){
+      msg.style.color = 'var(--green)';
+      msg.textContent = '已记录到 canonical trading state: ' + JSON.stringify(j);
+      pollNow();
+    } else {
+      msg.style.color = 'var(--red)';
+      msg.textContent = '拒绝: ' + (j.error || ('http ' + r.status)) + '（canonical host 规则原样返回，未被 API 覆盖）';
+    }
+  }catch(e){
+    msg.style.color = 'var(--red)';
+    msg.textContent = '无法连接 quant_serve — 记录交易需运行: python3 tools/quant_serve.py（静态文件模式不产生任何写入）';
+  }
+}
+
+/* ---- 今日事件时间线: durable alerts only ---- */
+function renderTimeline(rows){
+  rows = rows || [];
+  $('tl-meta').textContent = `durable alerts · ${rows.length} 条真实持久化事件`;
+  $('tl-list').innerHTML = rows.length ? rows.map(r=>
+    `<li><span class="ts">${esc(String(r.ts||'').slice(5,19))}</span><span><b>${esc(r.type||'')}</b>` +
+    (r.symbol?` <code>${esc(r.symbol)}</code>`:'') + ` ${esc(r.what||'')}` +
+    (r.price!=null?` · @${esc(r.price)}`:'') + (r.venue?` · ${esc(r.venue)}`:'') +
+    (r.why?` <span class="mut">— ${esc(r.why)}</span>`:'') + '</span></li>').join('')
+    : '<li class="mut">当日无持久化事件 — 无事件只是没有 material change，不是无活动</li>';
+}
+
+async function pollNow(){
+  try{
+    const r = await fetch('/api/quant/now', {cache:'no-store'});
     const j = await r.json();
-    renderTrading({present: !!j.as_of, state: j, open_positions: j.positions || [], alerts: j.events || []});
-  }catch(e){ /* keep the last good render */ }
+    renderNow(j);
+    renderPositions(j.positions || []);
+    $('now-meta').textContent += ' · 实时已连接';
+  }catch(e){
+    /* keep the embedded render-time snapshot; degrade visually, never fake live */
+    renderNow(D.now || {});
+    renderPositions((D.now||{}).positions || []);
+    $('now-meta').textContent += ' · server 未连接 — 显示生成时快照';
+  }
+}
+
+/* button wiring: action cards + position cards share data-act buttons */
+document.addEventListener('click', (e)=>{
+  const btn = e.target.closest('[data-act]');
+  if(!btn) return;
+  const act = btn.dataset.act;
+  if(act === 'ask'){
+    const sym = btn.dataset.symbol || '当前标的';
+    const promptText = `分析${sym}：先调用 get_trading_context 读取 canonical trading 事实，再解释当前 deterministic 状态（触发条件、风险、失效条件），区分 Runtime/Agent/Human 三态；不要宣称盈利能力，不要把 SYSTEM_UNAVAILABLE 说成 NO_TRADE。`;
+    (navigator.clipboard?.writeText(promptText) || Promise.reject()).then(
+      ()=>{ btn.textContent = '已复制提示词'; setTimeout(()=>{btn.textContent='Ask Agent';}, 1500); },
+      ()=>{ window.prompt('复制以下提示词发给 Agent:', promptText); });
+    return;
+  }
+  if(act === 'keep'){
+    const card = btn.closest('.action-card');
+    if(card){ card.style.opacity = '.45'; btn.disabled = true; btn.textContent = 'Watching'; }
+    return;
+  }
+  openTrade(act, btn.dataset.symbol, btn.dataset.venue,
+            btn.dataset.shares || '', btn.dataset.price || '');
+});
+document.addEventListener('click', (e)=>{
+  if(e.target.id === 'tm-close'){ $('trade-modal').hidden = true; return; }
+  if(e.target.id === 'tm-submit'){ submitTrade(); return; }
+  if(e.target.closest('#trade-modal') && !e.target.closest('.modal-box')){ $('trade-modal').hidden = true; }
+});
+document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') $('trade-modal').hidden = true; });
+setInterval(pollNow, 30000);
+
+/* ---- 真实运行数据趋势: trading artifacts 的忠实投影, 不补曲线不填 0 ---- */
+const RT_STATUS_ZH = {
+  SCANNED: '已扫描', NO_TRADE: '有效扫描 · 无机会', ALERTS: '需要行动',
+  MARKET_CLOSED: '已收盘（无扫描）', SYSTEM_UNAVAILABLE: '系统不可用（≠ NO_TRADE）',
+};
+const RT_STATUS_COLOR = {
+  SCANNED: 'var(--green)', NO_TRADE: 'var(--acc)', ALERTS: 'var(--amber)',
+  MARKET_CLOSED: '#8b96a8', SYSTEM_UNAVAILABLE: 'var(--red)',
+};
+const rtChip = (st) => `<span class="chip" style="color:${RT_STATUS_COLOR[st] || 'var(--mut)'};background:var(--panel2);border:1px solid var(--line2)" title="${esc(st)}">${esc(RT_STATUS_ZH[st] || st || '—')}</span>`;
+
+function renderM1Evidence(m1){
+  const box = $('m1-evidence');
+  const line = (label, ok, detail, forceText) => {
+    const v = forceText ?? (ok ? '有' : '未证明');
+    const color = forceText ? 'var(--amber)' : (ok ? 'var(--green)' : 'var(--amber)');
+    return `<dt style="min-width:150px">${esc(label)}</dt><dd style="color:${color};font-weight:700">${esc(v)}<span class="dim" style="font-weight:400"> — ${esc(detail||'')}</span></dd>`;
+  };
+  const fwd = m1.formal_forward_count ?? 0;
+  box.innerHTML = [
+    line('有效市场数据', !!(m1.market_data_valid||{}).ok, (m1.market_data_valid||{}).detail),
+    line('有效单次扫描', !!(m1.single_scan_valid||{}).ok, (m1.single_scan_valid||{}).detail),
+    line('连续实时监控', !!(m1.continuous_monitoring||{}).ok, (m1.continuous_monitoring||{}).detail),
+    line('正式 forward evidence', null, '正式 forward observation 计数 (trading/forward.json)', String(fwd)),
+    `<dt style="min-width:150px">M1 production evidence</dt><dd style="color:var(--amber);font-weight:700">${esc(m1.verdict || 'NO_REAL_EVIDENCE')} <span class="dim" style="font-weight:400">— 按 artifacts 真实状态投影, 不包装成 M1 PASS</span></dd>`,
+  ].join('');
 }
-setInterval(pollAttention, 30000);
+
+function renderRealTrendChart(pts){
+  const box = $('rt-chart');
+  if (!pts.length){
+    box.innerHTML = '<div class="empty"><div class="t">无真实运行记录</div><div class="s">trading/soak.jsonl 尚不存在 — monitor 从未运行, 不画任何合成曲线</div></div>';
+    return;
+  }
+  const W=1000, H=210, L=46, R=16, T=14, B=30;
+  const X = (i) => pts.length === 1 ? (L + (W-L-R)/2) : L + i*(W-L-R)/(pts.length-1);
+  const Y = (v) => T + (1-v)*(H-T-B);           // v = scanned/universe, 0..1
+  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">`;
+  for (let g=0; g<=2; g++){                     // 0% / 50% / 100% grid
+    const v=g/2, y=Y(v);
+    svg += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#1f2733" stroke-width="1"/>`+
+           `<text x="${L-6}" y="${y+4}" fill="#5c6678" font-size="10.5" text-anchor="end">${v*100}%</text>`;
+  }
+  const scanRatio = (p) => (p.symbols_scanned==null || !p.universe_size) ? null : p.symbols_scanned/p.universe_size;
+  // connect only consecutive points where a real scan happened on both sides;
+  // MARKET_CLOSED / SYSTEM_UNAVAILABLE gaps stay visually separate, no interpolation
+  for (let i=0; i+1<pts.length; i++){
+    const a=scanRatio(pts[i]), b=scanRatio(pts[i+1]);
+    if (a==null || b==null || pts[i].symbols_scanned<=0 || pts[i+1].symbols_scanned<=0) continue;
+    svg += `<line x1="${X(i)}" y1="${Y(a)}" x2="${X(i+1)}" y2="${Y(b)}" stroke="#4cc2ff" stroke-width="1.6" opacity=".85"/>`;
+  }
+  pts.forEach((p,i)=>{
+    const r = scanRatio(p);
+    const color = RT_STATUS_COLOR[p.status] || 'var(--mut)';
+    const tip = `${p.ts} · ${p.status}\n扫描 ${p.symbols_scanned ?? '缺失'}/${p.universe_size ?? '缺失'} · 事件 ${p.events ?? '缺失'}\n${p.source}`;
+    if (r == null){ return; }                   // missing stays missing: no fabricated point
+    svg += `<circle cx="${X(i)}" cy="${Y(r)}" r="${(p.events>0)?6:4.5}" fill="${color}" ${p.events>0?`stroke="var(--amber)" stroke-width="2" fill-opacity=".55"`:''}><title>${esc(tip)}</title></circle>`;
+    svg += `<text x="${X(i)}" y="${H-10}" fill="#5c6678" font-size="10" text-anchor="middle">${esc(String(p.ts).slice(5,16))}</text>`;
+  });
+  svg += '</svg>';
+  box.innerHTML = `<div class="chart-box">${svg}
+    <div class="legend" style="display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:12px;color:var(--mut)">
+      ${Object.keys(RT_STATUS_ZH).filter(s=>pts.some(p=>p.status===s)).map(s=>`<span style="display:flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:50%;display:inline-block;background:${RT_STATUS_COLOR[s]}"></i>${esc(RT_STATUS_ZH[s])}</span>`).join('')}
+      <span class="dim">折线只连接相邻两个真实扫描点；MARKET_CLOSED = 收盘无扫描, 不是扫描失败</span>
+    </div></div>`;
+}
+
+function renderRealTrend(){
+  const rt = D.real_trend || {};
+  const pts = rt.points || [];
+  $('rt-meta').textContent = `真实记录 ${rt.record_count ?? pts.length} 条 · universe ${rt.universe_size ?? '—'} 只 · M1 trading artifacts`;
+  renderM1Evidence(rt.m1_evidence || {});
+  renderRealTrendChart(pts);
+  const fwd = rt.forward || {};
+  $('rt-forward').innerHTML = fwd.count
+    ? `<b style="color:var(--green)">正式 forward observation：${fwd.count}</b>（已结算 ${fwd.settled ?? 0}）<span class="dim"> — trading/forward.json</span>`
+    : `<b style="color:var(--amber)">尚无正式 forward evidence</b><span class="dim"> — 正式 forward observation 0 条 (trading/forward.json)；不显示 0% 胜率, 不以诊断记录代替</span>`;
+  const diag = rt.diagnostic_rows || [];
+  $('rt-diagnostic').innerHTML = diag.length ? `
+    <div class="question" style="margin-bottom:6px;border-left-color:var(--amber)">以下为 <b>diagnostic forward evidence</b> — 来自隔离诊断运行（--state-dir 隔离, trading-diagnostic/），不是正式 forward observation, 不计入策略收益、胜率或已成交记录。</div>
+    <table><thead><tr><th>日期</th><th>代码</th><th>事件</th><th class="num-h">参考价</th><th class="num-h">5日回撤</th><th class="num-h">20日量比</th><th class="num-h">D+1（诊断）</th><th>标记</th></tr></thead><tbody>
+    ${diag.map(r=>`<tr>
+      <td class="num">${esc(r.day)}</td><td><code>${esc(r.symbol)}</code></td><td><span class="chip gray">${esc(r.state)}</span></td>
+      <td class="num">${fmt(r.ref_price)}</td>
+      <td class="num">${fmt(r.pullback_5d!=null?r.pullback_5d*100:null,2)}%</td>
+      <td class="num">${fmt(r.volume_ratio_20d)}</td>
+      <td class="num" style="color:var(--acc)">${r.d1!=null?`${r.d1>=0?'+':''}${(r.d1*100).toFixed(4)}% <span class="dim">(${esc(r.d1_day||'')})</span>`:'<span class="dim">待结算 — 缓存尚无后续日线</span>'}</td>
+      <td><span class="chip NEAR">diagnostic</span></td></tr>`).join('')}
+    </tbody></table>` : '';
+  $('rt-rows').innerHTML = pts.length ? pts.map(p=>`<tr>
+    <td class="num">${esc(p.ts)}</td><td>${rtChip(p.status)}</td>
+    <td class="num">${p.symbols_scanned ?? '—'}</td><td class="num">${p.universe_size ?? '—'}</td>
+    <td class="num">${p.events ?? '—'}</td><td class="mut"><code>${esc(p.source||'')}</code></td></tr>`).join('')
+    : '<tr><td colspan="6" class="mut">无真实记录 — 运行 python tools/quant_trading_monitor.py session 开始积累</td></tr>';
+}
+
 
 function renderStatic(){
-  pollAttention();
+  renderNow(D.now || {});
+  renderPositions((D.now||{}).positions || []);
+  renderTimeline(D.timeline || []);
+  pollNow();
+  renderRealTrend();
   $('gen-time').textContent = D.generated_at;
   $('strategy-warning').textContent = '⚠ ' + D.warning;
   $('not-a-buy').textContent = D.not_a_buy_note;
@@ -1264,8 +2103,8 @@ function renderStatic(){
     <dt>历史最佳年化</dt><dd>${fmt(s.best_annualized_pct,2)}% <span class="dim">(重放, 噪声内, 非已证明优势)</span></dd>
     <dt>历史交易笔数</dt><dd>${fmt(s.best_trades,0)}</dd>
     <dt>PIT / 成分偏差</dt><dd>存在 <span class="dim">(今日成员回看历史; 任何盈利声明的前置门)</span></dd>
-    <dt>前向触发累计</dt><dd>${fmt(s.forward_triggers,0)}</dd>
-    <dt>前向已结算交易</dt><dd>${fmt(s.forward_settled,0)}</dd>
+    <dt>前向观察（正式）</dt><dd>${fmt(s.forward_observations,0)} <span class="dim">(trading/forward.json)</span></dd>
+    <dt>前向已结算交易（正式）</dt><dd>${fmt(s.forward_settled,0)}</dd>
     <dt>前向胜率</dt><dd>${s.forward_hit_rate ? '积累足够结算笔数后再计算' : fmt(s.forward_hit_rate,3)}</dd>
   </dl>`;
   $('results-rows').innerHTML = (s.results||[]).map(r=>`<tr>
@@ -1273,8 +2112,11 @@ function renderStatic(){
     <td class="num">${fmt(r.trades,0)}</td><td class="num">${fmt(r.max_drawdown_pct,2)}%</td>
     <td class="mut">${esc(r.verdict)}</td></tr>`).join('') || '<tr><td colspan="5" class="mut">无评估工件</td></tr>';
 
-  // forward evidence
-  $('obs-rows').innerHTML = (D.obs_rows||[]).length ? D.obs_rows.slice().reverse().map(r=>`<tr>
+  // forward evidence: formal observations (trading/forward.json) + history log
+  const f = (D.real_trend||{}).forward || {};
+  $('formal-forward').innerHTML = f.count
+    ? `<b style="color:var(--green)">正式 forward observation：${f.count}</b>（已结算 ${f.settled??0}）— 明细随正式记录产生后在此展开`
+    : `<b style="color:var(--amber)">尚无正式 forward observation</b>（trading/forward.json 为 0 条）— 不显示 0% 胜率, 不以历史日志或诊断记录代替`;  $('obs-rows').innerHTML = (D.obs_rows||[]).length ? D.obs_rows.slice().reverse().map(r=>`<tr>
     <td class="num">${esc(r.date)}</td><td class="num">${esc(r.time)}</td>
     <td class="num">${esc(r.scanned)}</td>
     <td class="num" style="color:${r.triggers&&r.triggers!=='0'?'var(--red)':'var(--dim)'}">${esc(r.triggers)}</td>
@@ -1371,12 +2213,15 @@ def main() -> int:
     BUSINESS_ART.mkdir(parents=True, exist_ok=True)
     workspace_copy.write_text(html, encoding="utf-8")
     kpi = data["kpi"]
+    rt = data["real_trend"]
     dims = data["data_quality"].get("dimensions") or {}
     dim_summary = " ".join(f"{k}={v['status']}" for k, v in dims.items())
     print(
         f"OK -> {out} ({out.stat().st_size / 1024:.1f} KB, also {workspace_copy}); "
         f"decision={kpi['today_decision']} triggers={kpi['live_triggers']} "
         f"candidates={kpi['active_candidates']} evidence={kpi['strategy_evidence']} "
+        f"real_records={rt['record_count']} forward={rt['forward']['count']} "
+        f"m1={rt['m1_evidence']['verdict']} "
         f"dq_status={data['data_quality']['status']} ({dim_summary})"
     )
     return 0
diff --git a/tools/quant_serve.py b/tools/quant_serve.py
index aff71e7..e77da93 100755
--- a/tools/quant_serve.py
+++ b/tools/quant_serve.py
@@ -1,19 +1,29 @@
 #!/usr/bin/env python3
-"""ZUAEF-ASHARE-001 · 本地看板服务 (只读, 无交易语义, loopback-only)。
+"""ZUAEF-ASHARE-001 · 本地看板服务 (loopback-only)。
 
 GET / , /business , /index.html → docs/quant/business.html   (业务决策页, 默认)
 GET /engineering               → docs/quant/dashboard.html   (工程/审计页)
 GET /api/scan                  → 活跃候选宇宙实时扫描 JSON (确定性; quant_live_scan.py)
 GET /api/watchlist             → legacy_watchlist 显式扫描 JSON (只扫用户自选名单)
+GET /api/attention             → monitor state.json 投影 (兼容保留)
+GET /api/quant/now             → NOW: durable trading facts 有界投影 (now_snapshot)
+
+POST /api/quant/ack-buy        → 记录用户已完成/纸面买入 (canonical ack-buy)
+POST /api/quant/ack-sell       → 记录用户全仓平仓 (canonical ack-sell)
+POST /api/quant/skip           → 记录用户 SKIP 决定 (canonical skip)
+
+写接口是 canonical trading host 操作 (quant_trading_monitor.py CLI) 的薄
+HTTP adapter，不做任何 JSON 直写；且强制 loopback-only —— --host 非本机
+回环地址时 POST 一律 403 (无账号系统，Phase 1 不对 LAN 暴露写接口)。
 
 用法:
     python3 tools/quant_serve.py [--port 8787]
 打开: http://127.0.0.1:8787/            (业务页)
       http://127.0.0.1:8787/engineering (工程/审计页)
 
-Loopback-only; 只读巡检, 不产生任何交易动作。冻结期有意的最小实现
-(docs/quant/README.md §6): 页面轮询 + 确定性扫描即足够, 不建 watcher/daemon
-框架。宇宙解析失败时 /api/* 返回错误 JSON (fail closed), 绝不静默返回空宇宙。
+冻结期有意的最小实现 (docs/quant/README.md §6): 页面轮询 + 确定性扫描即
+足够, 不建 watcher/daemon 框架。宇宙解析失败时 /api/* 返回错误 JSON
+(fail closed), 绝不静默返回空宇宙。
 """
 
 from __future__ import annotations
@@ -25,6 +35,8 @@ import sys
 from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
 from pathlib import Path
 
+import quant_render_business_dashboard as biz
+
 REPO_ROOT = Path(__file__).resolve().parent.parent
 PAGES = {
     "business": REPO_ROOT / "docs" / "quant" / "business.html",
@@ -32,6 +44,16 @@ PAGES = {
 }
 SCAN_CMD = ["uv", "run", "--group", "quant", "python", "tools/quant_live_scan.py"]
 WATCHLIST_CMD = SCAN_CMD + ["--universe-file", "benchmarks/quant/gen1/legacy_watchlist.toml"]
+MONITOR_CMD = ["uv", "run", "--group", "quant", "python", "tools/quant_trading_monitor.py"]
+TRADING_STATE_DIR = "workspace/artifacts/quant/trading"
+LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
+MAX_BODY_BYTES = 4096
+
+
+def writes_enabled_for_host(host: str) -> bool:
+    """Trade-recording writes stay loopback-only: no accounts in Phase 1,
+    so an unauthenticated LAN POST must never reach the ack endpoints."""
+    return host in LOOPBACK_HOSTS
 
 
 def page_for_path(path: str) -> Path | None:
@@ -63,7 +85,68 @@ def attention_state() -> dict:
         return {"status": "UNKNOWN", "reason": "monitor has not run yet"}
 
 
+def now_state() -> dict:
+    """NOW projection — the same durable-facts builder the static page
+    embeds; reads artifacts, never recomputes the market."""
+    return biz.now_snapshot()
+
+
+ACK_KINDS = ("ack-buy", "ack-sell", "skip")
+
+
+def ack_command_for(kind: str, payload: dict) -> list[str]:
+    """Validate one human-action payload and build the canonical monitor CLI
+    argv. Pure + unit-tested; the server never writes trading JSON itself.
+
+    buy/sell require symbol/shares/price/venue/executed_at; skip requires
+    symbol/price/executed_at (note optional). Full-close and venue-match
+    rules are enforced by the monitor host op, not duplicated here.
+    """
+    if kind not in ACK_KINDS:
+        raise ValueError(f"unknown ack kind: {kind}")
+    if not isinstance(payload, dict):
+        raise TypeError("body must be a JSON object")
+    symbol = str(payload.get("symbol") or "").strip().upper()
+    if not symbol:
+        raise ValueError("symbol is required")
+    argv = MONITOR_CMD + ["--state-dir", TRADING_STATE_DIR, kind, "--symbol", symbol]
+    executed_at = str(payload.get("executed_at") or "").strip()
+    if not executed_at:
+        raise ValueError("executed_at is required (the human fact's own time)")
+    if kind == "skip":
+        price = payload.get("price")
+        if not isinstance(price, (int, float)) or price <= 0:
+            raise ValueError("price must be a positive number")
+        argv += ["--price", repr(float(price)), "--time", executed_at]
+        note = str(payload.get("note") or "").strip()
+        if note:
+            argv += ["--note", note]
+        return argv
+    venue = str(payload.get("venue") or "").strip()
+    if venue not in ("paper", "real"):
+        raise ValueError("venue must be 'paper' or 'real'")
+    shares = payload.get("shares")
+    if not isinstance(shares, int) or isinstance(shares, bool) or shares <= 0:
+        raise ValueError("shares must be a positive integer")
+    price = payload.get("price")
+    if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
+        raise ValueError("price must be a positive number")
+    argv += [
+        "--price", repr(float(price)),
+        "--shares", str(shares),
+        "--venue", venue,
+        "--time", executed_at,
+    ]
+    note = str(payload.get("note") or "").strip()
+    if note:
+        argv += ["--note", note]
+    return argv
+
+
 class Handler(BaseHTTPRequestHandler):
+    # set by main(): POST endpoints answer 403 when bound to a non-loopback host
+    writes_enabled: bool = True
+
     def log_message(self, format, *args):  # keep access logs bounded
         sys.stderr.write(f"[serve] {format % args}\n")
 
@@ -76,6 +159,10 @@ class Handler(BaseHTTPRequestHandler):
         self.end_headers()
         self.wfile.write(body)
 
+    def _send_json(self, code: int, obj: dict, no_store: bool = True) -> None:
+        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
+                   "application/json", no_store=no_store)
+
     def do_GET(self) -> None:
         page = page_for_path(self.path)
         if page is not None:
@@ -91,8 +178,10 @@ class Handler(BaseHTTPRequestHandler):
             self._send(200, body, "text/html; charset=utf-8")
             return
         if self.path == "/api/attention":
-            body = json.dumps(attention_state(), ensure_ascii=False, default=str).encode("utf-8")
-            self._send(200, body, "application/json", no_store=True)
+            self._send_json(200, attention_state())
+            return
+        if self.path == "/api/quant/now":
+            self._send_json(200, now_state())
             return
         cmd = api_command_for_path(self.path)
         if cmd is not None:
@@ -123,16 +212,62 @@ class Handler(BaseHTTPRequestHandler):
             return
         self._send(404, b"not found", "text/plain")
 
+    def do_POST(self) -> None:
+        kind = self.path.rsplit("/", 1)[-1] if self.path.startswith("/api/quant/") else ""
+        if kind not in ACK_KINDS:
+            self._send_json(404, {"error": "not found"})
+            return
+        if not self.writes_enabled:
+            self._send_json(403, {"error": "trade writes are loopback-only; rebind --host to 127.0.0.1"})
+            return
+        try:
+            length = int(self.headers.get("Content-Length") or 0)
+        except ValueError:
+            length = -1
+        if length <= 0 or length > MAX_BODY_BYTES:
+            self._send_json(400, {"error": f"Content-Length must be 1..{MAX_BODY_BYTES}"})
+            return
+        try:
+            payload = json.loads(self.rfile.read(length).decode("utf-8"))
+        except (ValueError, UnicodeDecodeError):
+            self._send_json(400, {"error": "body is not valid JSON"})
+            return
+        try:
+            cmd = ack_command_for(kind, payload)
+        except (ValueError, TypeError) as exc:
+            self._send_json(400, {"error": str(exc)})
+            return
+        try:
+            r = subprocess.run(
+                cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False,
+            )
+        except subprocess.TimeoutExpired:
+            self._send_json(504, {"error": "ack timeout"})
+            return
+        if r.returncode != 0:
+            # canonical host rejection (missing position / full-close / venue
+            # rules) surfaces verbatim as 400 — the API never overrides it
+            try:
+                err = json.loads(r.stderr.strip() or r.stdout.strip())
+            except ValueError:
+                err = {"error": (r.stderr or r.stdout)[-500:]}
+            self._send_json(400, err)
+            return
+        self._send_json(200, json.loads(r.stdout.strip() or "{}"))
+
 
 def main() -> int:
     ap = argparse.ArgumentParser(description=__doc__)
     ap.add_argument("--port", type=int, default=8787)
     ap.add_argument("--host", default="127.0.0.1")
     args = ap.parse_args()
+    Handler.writes_enabled = writes_enabled_for_host(args.host)
     srv = ThreadingHTTPServer((args.host, args.port), Handler)
+    writes = "enabled" if Handler.writes_enabled else "DISABLED (non-loopback host)"
     print(
         f"ZUAEF quant dashboards → business http://{args.host}:{args.port}/  "
-        f"engineering http://{args.host}:{args.port}/engineering  (Ctrl-C 停止)",
+        f"engineering http://{args.host}:{args.port}/engineering  "
+        f"(trade writes {writes}; Ctrl-C 停止)",
         file=sys.stderr,
     )
     try:
diff --git a/tools/quant_trading_monitor.py b/tools/quant_trading_monitor.py
index 37a1d93..90892d7 100644
--- a/tools/quant_trading_monitor.py
+++ b/tools/quant_trading_monitor.py
@@ -34,8 +34,9 @@ platform). `--state-dir` isolates fixture/replay runs from real results.
 
     .venv/bin/python tools/quant_trading_monitor.py once
     .venv/bin/python tools/quant_trading_monitor.py session --interval 45
-    .venv/bin/python tools/quant_trading_monitor.py ack-buy --symbol 600000 --price 10.5 --shares 500
+    .venv/bin/python tools/quant_trading_monitor.py ack-buy --symbol 600000 --price 10.5 --shares 500 --venue paper
     .venv/bin/python tools/quant_trading_monitor.py ack-sell --symbol 600000 --price 10.9 --shares 500
+    .venv/bin/python tools/quant_trading_monitor.py skip --symbol 600000 --price 10.5 --note "too extended"
     .venv/bin/python tools/quant_trading_monitor.py status
 """
 
@@ -80,9 +81,12 @@ EVENT_POSITION_EXIT_ALERT = "POSITION_EXIT_ALERT"
 EVENT_POSITION_EXIT_CLEARED = "POSITION_EXIT_CLEARED"
 EVENT_POSITION_OPENED = "POSITION_OPENED"
 EVENT_POSITION_CLOSED = "POSITION_CLOSED"
+EVENT_HUMAN_SKIP = "HUMAN_SKIP"
 EVENT_DATA_UNTRUSTED = "DATA_UNTRUSTED"
 EVENT_CONNECTION_LOST = "LIVE_CONNECTION_LOST"
 
+VENUES = ("paper", "real")
+
 ST_WATCH, ST_NEAR, ST_READY, ST_INVALIDATED, ST_EXECUTED = (
     "WATCH", "NEAR", "READY", "INVALIDATED", "EXECUTED",
 )
@@ -233,7 +237,7 @@ class Store:
             {"kind": kind, "symbol": symbol, "day": day, "ref_price": ref_price, "ref_id": ref_id}
         )
 
-    def open_position(self, symbol: str, price: float, shares: int, when: str, strategy: str) -> dict:
+    def open_position(self, symbol: str, price: float, shares: int, when: str, strategy: str, venue: str = "paper") -> dict:
         pid = f"p-{self.positions['next_id']:04d}"
         self.positions["next_id"] += 1
         position = {
@@ -244,6 +248,7 @@ class Store:
             "entry_time": when,
             "entry_date": when[:10],
             "strategy": strategy,
+            "venue": venue,
             "state": "HOLD",
         }
         self.positions["open"].append(position)
@@ -297,7 +302,6 @@ def run_cycle(
         status = "MARKET_CLOSED"
         _write_summary(store, status, [], now, day_str, state_dir)
         return {"status": status, "events": [], "symbols": 0}
-
     resolved = resolve_universe(None, active_path=ACTIVE_SYMBOLS_PATH)
     symbols = list(resolved["symbols"])
     position_symbols = [p["symbol"] for p in store.positions["open"]]
@@ -309,6 +313,9 @@ def run_cycle(
             expected_symbols=symbols, universe_as_of=resolved["as_of"]
         )["status"]
     suppressed = volume_gate_suppresses(semantic_status)
+    # data trust = this cycle's semantic gate verdict, fail-closed; it is a
+    # data fact and deliberately separate from runtime availability
+    data_trust = "PASS" if semantic_status == "PASS" else "FAIL"
 
     events: list[dict] = []
 
@@ -341,7 +348,7 @@ def run_cycle(
                 },
             )
         status = "SYSTEM_UNAVAILABLE"
-        _write_summary(store, status, events, now, day_str, state_dir)
+        _write_summary(store, status, events, now, day_str, state_dir, data_trust="UNKNOWN")
         return {"status": status, "events": events, "symbols": len(quote_symbols)}
     if suppressed and store.alerts_today(day_str, {EVENT_DATA_UNTRUSTED}) == 0:
         emit(
@@ -498,13 +505,14 @@ def run_cycle(
     _write_summary(
         store, status, events, now, day_str, state_dir,
         attention=attention, symbols=len(quote_symbols), positions_live=positions_live,
+        data_trust=data_trust,
     )
-    return {"status": status, "events": events, "symbols": len(quote_symbols)}
+    return {"status": status, "events": events, "symbols": len(quote_symbols), "data_trust": data_trust}
 
 
 def _write_summary(store: Store, status: str, events: list, now: datetime, day: str,
                    state_dir: Path, attention: list[dict] | None = None, symbols: int = 0,
-                   positions_live: dict | None = None) -> None:
+                   positions_live: dict | None = None, data_trust: str = "UNKNOWN") -> None:
     ready = [s for s, o in store.opportunities.items() if o.get("state") == ST_READY]
     near = [s for s, o in store.opportunities.items() if o.get("state") == ST_NEAR]
     exit_alerts = [p["symbol"] for p in store.positions["open"] if p.get("state") == "EXIT_ALERT"]
@@ -519,13 +527,16 @@ def _write_summary(store: Store, status: str, events: list, now: datetime, day:
         "watch": [s for s, o in store.opportunities.items() if o.get("state") == ST_WATCH],
         "positions": [
             {
-                **{k: p.get(k) for k in ("id", "symbol", "entry_price", "shares", "state", "exit_reason")},
+                **{k: p.get(k) for k in ("id", "symbol", "entry_price", "shares", "venue", "state", "exit_reason")},
                 **((positions_live or {}).get(p["symbol"], {})),
             }
             for p in store.positions["open"]
         ],
         "exit_alerts": exit_alerts,
         "events": events,
+        # data trust is a fact about the data gate, NOT runtime availability:
+        # PASS/FAIL only when semantics were evaluated this cycle, else UNKNOWN
+        "data_trust": data_trust,
         "market_no_trade": status == "NO_TRADE",
         "system_unavailable": status == "SYSTEM_UNAVAILABLE",
     })
@@ -570,8 +581,13 @@ def _ack_time(value: str | None) -> str:
 
 def cmd_ack_buy(args, store: Store) -> int:
     _cfg, spec = _load_strategy()
+    venue = getattr(args, "venue", None) or "paper"
+    note = getattr(args, "note", None) or ""
+    if venue not in VENUES:
+        print(json.dumps({"error": f"venue must be one of {list(VENUES)}"}), file=sys.stderr)
+        return 1
     when = _ack_time(args.time)
-    position = store.open_position(args.symbol.upper(), float(args.price), int(args.shares), when, spec.name)
+    position = store.open_position(args.symbol.upper(), float(args.price), int(args.shares), when, spec.name, venue=venue)
     opp = store.opportunities.get(position["symbol"])
     if opp and opp.get("state") in (ST_NEAR, ST_READY, ST_WATCH):
         opp["state"] = ST_EXECUTED
@@ -581,10 +597,11 @@ def cmd_ack_buy(args, store: Store) -> int:
         "day": when[:10], "type": EVENT_POSITION_OPENED, "symbol": position["symbol"],
         "price": float(args.price), "what": "user BUY acknowledged",
         "why": f"{position['id']} {args.shares} shares @ {args.price}",
+        "venue": venue, "note": note,
         "conditions": None, "invalidation": "close via ack-sell", "data_trust": "USER_CONFIRMED",
     })
     store.save()
-    print(json.dumps({"position": position["id"], "symbol": position["symbol"], "state": "HOLD"}, ensure_ascii=False))
+    print(json.dumps({"position": position["id"], "symbol": position["symbol"], "state": "HOLD", "venue": venue}, ensure_ascii=False))
     return 0
 
 
@@ -594,8 +611,26 @@ def cmd_ack_sell(args, store: Store) -> int:
     if not open_positions:
         print(json.dumps({"error": f"no open position for {symbol}"}), file=sys.stderr)
         return 1
+    position = open_positions[0]
+    # Phase 1: full close only — a partial share count would close the whole
+    # position while booking wrong P&L, so it is rejected, not silently shrunk
+    if int(args.shares) != int(position["shares"]):
+        print(json.dumps({
+            "error": f"Phase 1 closes the full position only: open {position['shares']} shares, got {args.shares}",
+        }), file=sys.stderr)
+        return 1
+    venue = getattr(args, "venue", None) or position.get("venue", "paper")
+    if venue not in VENUES:
+        print(json.dumps({"error": f"venue must be one of {list(VENUES)}"}), file=sys.stderr)
+        return 1
+    if venue != position.get("venue", "paper"):
+        print(json.dumps({
+            "error": f"venue mismatch: position opened as {position.get('venue')}, sell claimed {venue}",
+        }), file=sys.stderr)
+        return 1
+    note = getattr(args, "note", None) or ""
     when = _ack_time(args.time)
-    closed = store.close_position(open_positions[0], float(args.price), int(args.shares), when)
+    closed = store.close_position(position, float(args.price), int(args.shares), when)
     # the position is gone; the symbol's opportunity lifecycle resumes
     opp = store.opportunities.get(symbol)
     if opp and opp.get("state") == ST_EXECUTED:
@@ -605,10 +640,36 @@ def cmd_ack_sell(args, store: Store) -> int:
         "day": when[:10], "type": EVENT_POSITION_CLOSED, "symbol": symbol,
         "price": float(args.price), "what": "user SELL acknowledged",
         "why": f"{closed['id']} closed, pnl {closed['pnl']}",
+        "venue": venue, "note": note,
+        "conditions": None, "invalidation": None, "data_trust": "USER_CONFIRMED",
+    })
+    store.save()
+    print(json.dumps({"closed": closed["id"], "pnl": closed["pnl"], "venue": venue}, ensure_ascii=False))
+    return 0
+
+
+def cmd_skip(args, store: Store) -> int:
+    """Record a human SKIP decision on a live opportunity as a real fact:
+    one HUMAN_SKIP alert plus a SKIP forward observation (settles D+1/3/5/8
+    through the existing settle path, feeding future override-value research).
+    The opportunity state machine is intentionally untouched."""
+    symbol = args.symbol.upper()
+    price = float(args.price)
+    if price <= 0:
+        print(json.dumps({"error": "price must be positive"}), file=sys.stderr)
+        return 1
+    when = _ack_time(args.time)
+    note = getattr(args, "note", None) or ""
+    store.record_forward("SKIP", symbol, when[:10], price)
+    store.append_alert({
+        "day": when[:10], "type": EVENT_HUMAN_SKIP, "symbol": symbol,
+        "price": price, "what": "user skipped the opportunity",
+        "why": note or "human decided not to act",
+        "venue": None, "note": note,
         "conditions": None, "invalidation": None, "data_trust": "USER_CONFIRMED",
     })
     store.save()
-    print(json.dumps({"closed": closed["id"], "pnl": closed["pnl"]}, ensure_ascii=False))
+    print(json.dumps({"skipped": symbol, "day": when[:10]}, ensure_ascii=False))
     return 0
 
 
@@ -673,12 +734,21 @@ def main() -> int:
     p_buy.add_argument("--symbol", required=True)
     p_buy.add_argument("--price", type=float, required=True)
     p_buy.add_argument("--shares", type=int, required=True)
+    p_buy.add_argument("--venue", choices=list(VENUES), default="paper", help="paper (default) or real")
+    p_buy.add_argument("--note", default="", help="free-text human note")
     p_buy.add_argument("--time", default=None, help="ISO time; default now (Asia/Shanghai)")
-    p_sell = sub.add_parser("ack-sell", help="user-confirmed SELL -> CLOSED")
+    p_sell = sub.add_parser("ack-sell", help="user-confirmed SELL -> CLOSED (full close only)")
     p_sell.add_argument("--symbol", required=True)
     p_sell.add_argument("--price", type=float, required=True)
-    p_sell.add_argument("--shares", type=int, required=True)
+    p_sell.add_argument("--shares", type=int, required=True, help="must equal the open position's shares")
+    p_sell.add_argument("--venue", choices=list(VENUES), default=None, help="must match the position's venue")
+    p_sell.add_argument("--note", default="", help="free-text human note")
     p_sell.add_argument("--time", default=None)
+    p_skip = sub.add_parser("skip", help="record a human SKIP on an opportunity (no position change)")
+    p_skip.add_argument("--symbol", required=True)
+    p_skip.add_argument("--price", type=float, required=True, help="reference price for forward settlement")
+    p_skip.add_argument("--note", default="", help="why the opportunity was skipped")
+    p_skip.add_argument("--time", default=None)
     sub.add_parser("status", help="print current monitor state")
     args = parser.parse_args()
 
@@ -688,6 +758,7 @@ def main() -> int:
         "session": cmd_session,
         "ack-buy": cmd_ack_buy,
         "ack-sell": cmd_ack_sell,
+        "skip": cmd_skip,
         "status": cmd_status,
     }
     return handlers[args.cmd](args, store)
diff --git a/workspace/knowledge/concepts/quant-execution-truth.md b/workspace/knowledge/concepts/quant-execution-truth.md
index 1ff46e8..cc5cba9 100644
--- a/workspace/knowledge/concepts/quant-execution-truth.md
+++ b/workspace/knowledge/concepts/quant-execution-truth.md
@@ -40,7 +40,7 @@ generated:
 ## 冻结的执行规则集（quant.toml，唯一权威）
 
 | 规则 | 值 | 生效日期化 |
-|---|---|---|
+| --- | --- | --- |
 | 成交时点 | T 日信号 → **T+1 开盘成交**（next_open） | — |
 | T+1 | true（普通股当日买不可当日卖） | — |
 | 滑点 | 10bps | — |
@@ -80,7 +80,7 @@ board 差异、market_truth 开关、无未来函数）。测试真实抓出过
 **不是实现相等/NAV 相等要求**——每个实质性差异都必须被归因：
 
 | 类 | 含义 | 处置 |
-|---|---|---|
+| --- | --- | --- |
 | A EXPECTED_MARKET_RULE_DIFFERENCE | T+1 开盘成交、涨停买阻/贴稳卖延、停牌无bar、整手舍入（含 raw-vs-qfq 价格面×整手交互与前期规则差异级联进现金状态）、最低佣金、印花税、滑点 | 预期差，计入对账 |
 | B UNSUPPORTED_FOR_TRUSTED_PARITY | 跨不支持的除权（qfq/raw 调整机制切换） | 从可信对等子集隔离，绝不静默计入 |
 | C QLIB_MODEL_LIMITATION | 向量面按设计不建模涨跌停 | 已知局限 |
@@ -94,4 +94,4 @@ board 差异、market_truth 开关、无未来函数）。测试真实抓出过
 ## 与 Agent 的关系
 
 - 评估器/规则/成本/数据切分/基准是**宿主拥有的冻结配置**，Agent 不能改（P3 边界纪律）。
-- `ENTER_CANDIDATE` 永远不是订单；无候选时 NO_TRADE 合法且已实测发生（2026-09-02 盘中）。
\ No newline at end of file
+- `ENTER_CANDIDATE` 永远不是订单；无候选时 NO_TRADE 合法且已实测发生（2026-09-02 盘中）。
diff --git a/workspace/knowledge/concepts/quant-live-ops.md b/workspace/knowledge/concepts/quant-live-ops.md
index b591a81..77b33ea 100644
--- a/workspace/knowledge/concepts/quant-live-ops.md
+++ b/workspace/knowledge/concepts/quant-live-ops.md
@@ -97,7 +97,7 @@ signal timestamp、strategy name、why/invalidation/expected_holding、raw trigg
 ```
 
 同策略+同 intents（重生成 intents 元素级比对证明可复现）→ Qlib 向量面（qfq、market_truth OFF）
-+ 独立重放（raw、market_truth ON）→ 逐笔对账+聚合对比。差异归因 A–F（市场规则差/不支持对等/
+- 独立重放（raw、market_truth ON）→ 逐笔对账+聚合对比。差异归因 A–F（市场规则差/不支持对等/
 Qlib 局限/引擎 bug/无法解释）；任何无法解释的残留 = P0.5 失败。详见 quant-execution-truth。
 
 ## 快速看盘（不起 Agent）
@@ -124,6 +124,7 @@ brief JSON 自带完整字段，日志行仅供肉眼巡检；**无 DB**。
 SpendLimits、broker。唯一例外：PIT universe 仅在"准备做任何盈利声明"时作为前置门解冻。
 
 **重启开发的准入**（强规则：没有来自真实市场的新问题，不开新 feature）：
+
 - A. **≥10 个真实 trigger** → 人工结算复盘 → 决定 A/B 实验/是否自动化；
 - B. **观察期足够长仍 0 trigger** → "策略密度不足"成立 → 重启的是策略/宇宙研究（不是框架）。
 
@@ -136,7 +137,7 @@ B=Agent 有权 WATCH/NO_TRADE；比较期望值、回撤、坏交易剔除率、
 ## 故障速查（README §7.2 节选）
 
 | 症状 | 处置 |
-|---|---|
+| --- | --- |
 | EastMoney / SSL EOF | 正常（本网络被拒）；数据面已走腾讯/新浪/CSIndex |
 | 历史抓取偶发失败 | 腾讯限流；引擎内已有界重试，重跑即可 |
 | side environment missing | 确认 `.venv-quant/bin/python` 存在或设 `ZUAEF_QUANT_PYTHON` |
@@ -144,4 +145,4 @@ B=Agent 有权 WATCH/NO_TRADE；比较期望值、回撤、坏交易剔除率、
 | profile not found | 重装 profile（§5.1 第 3 步） |
 | evaluate_strategy already ran this round | 一轮守卫生效（设计行为），写完 Result 即结束 |
 | manifest 完整性失败 | `python tools/regen_manifest.py` |
-| 扫描全 0 触发 | 正常（S3 条件选择性高）；连续多周 0 触发才构成研究信号 |
\ No newline at end of file
+| 扫描全 0 触发 | 正常（S3 条件选择性高）；连续多周 0 触发才构成研究信号 |
diff --git a/workspace/knowledge/concepts/zuaef-quant-overview.md b/workspace/knowledge/concepts/zuaef-quant-overview.md
index 36d18ed..e815862 100644
--- a/workspace/knowledge/concepts/zuaef-quant-overview.md
+++ b/workspace/knowledge/concepts/zuaef-quant-overview.md
@@ -104,7 +104,7 @@ P2 独立执行重放 → P3 能力接入 → P4 三轮模型进化 → P5 实
 实现状态（STATUS.md，冻结 2026-09-02）：
 
 | Proof | State |
-|---|---|
+| --- | --- |
 | Research Engine Proof | **PASS**（P0 真实数据 + P1 Qlib 评估 + P2 一致性） |
 | Self-learning Loop Proof | **PASS**（P4：S1→S2 被否决→S3，一轮一个 mutation） |
 | Profitability Proof | **NOT YET**（最好子策略 ≈ +0.37% 年化/29 笔，噪声内，有意停止 in-sample 追寻） |
@@ -112,4 +112,4 @@ P2 独立执行重放 → P3 能力接入 → P4 三轮模型进化 → P5 实
 
 **当前阶段**：P5.5 ENGINEERING FREEZE 持续 —— 观察模式本体已由 M1 交易时段循环 v0.1 接管
 （连续盯盘 + 持仓管理 + forward 观察，见 quant-live-ops）；P0.5 双引擎对账已实现并进入可信对等路径。
-代码仍冻结：新功能必须来自真实市场派发的任务。
\ No newline at end of file
+代码仍冻结：新功能必须来自真实市场派发的任务。

diff --git a/.zcode/plans/plan-sess_50fe9cbd-311a-4fab-a818-8540d5f80d52.md b/.zcode/plans/plan-sess_50fe9cbd-311a-4fab-a818-8540d5f80d52.md
new file mode 100644
index 0000000..3942fe2
--- /dev/null
+++ b/.zcode/plans/plan-sess_50fe9cbd-311a-4fab-a818-8540d5f80d52.md
@@ -0,0 +1,35 @@
+# Quant Trading Workbench Phase 1（APPROVED_WITH_REQUIRED_CHANGES 版）
+
+Scope: T1–T6 + Spec §33 Dashboard 验收。主体设计不变（REUSE>EXTEND>NEW、canonical trading truth、薄 POST adapter、五层重排），以下 9 项必须修正已全部并入：
+
+## Required amendments（逐条落实）
+
+1. **`record_trade_outcome` = LOCAL_WRITE，不加 approval**——记录的是用户已完成/纸面事实，无券商动作；避免 Dashboard POST 不审批、Telegram 却审批的语义分裂。未来接 broker 才升级 EXTERNAL_WRITE。
+2. **Phase 1 卖出 = 仅全仓平仓**：`ack-sell --shares` 必须等于 open position.shares，否则 CLI fail / HTTP 400。不做 REDUCE。
+3. **venue 一致性**：BUY 写入 position.venue；SELL 接收 venue 但与 position venue 不一致即拒绝（paper BUY → real SELL 不可能发生）。
+4. **`data_trust` 独立字段**：monitor 每周期向 state.json 写 `data_trust = PASS | FAIL | UNKNOWN`（本周期 semantic gate 判定：PASS→PASS，非 PASS→FAIL，未评估如收盘/失联周期→UNKNOWN）。与 `system_unavailable`（runtime availability）严格分离。
+5. **heartbeat ≠ last_scan_at**：`heartbeat_at` = soak 尾行 ts；`last_scan_at` = 最近一条 `symbols > 0` 的真实扫描 ts。NOW 同时显示两者。
+6. **STALE 仅在"本应运行的交易时段"触发**：A股时段内 heartbeat age > 90s → STALE；非时段 → MARKET_CLOSED 态，显示 last heartbeat / last scan，不因 age 报故障。
+7. **NOW 读 durable 事实**：`now_state()` 读 state.json + opportunities.json + positions.json + alerts.jsonl（当日/bounded）+ soak.jsonl（bounded tail）+ briefs/ + active_symbols.json；不只读 state.json.events。
+8. **Agent Brief 事件匹配 join**：brief 仅当 `symbol 相同 且 recorded_at ≥ 该 symbol 最新 NEW_READY/POSITION_EXIT_ALERT ts` 才贴到 Action Card；否则显示"Agent：尚未复核"。绝不把 9/3 的判断贴到 9/4 的新 READY 上。
+9. **写接口强制 loopback-only**：`--host` 非 127.0.0.1/localhost/::1 时拒绝启用 POST 写接口（读接口保留）；不做账号系统。
+
+## 小调整
+- POST 字段：buy/sell 需 `symbol/shares/price/venue/executed_at`；skip 仅需 `symbol/price/executed_at/note?`。
+- BUILD_MANIFEST：现有 `test_manifest_integrity` 契约 pin 了 tools/tests/plugins 的 bytes+hash，改动文件条目必须同步（否则测试红）；仅 surgical 更新被改条目，不整册重生成。
+
+## 文件修改（不变的部分从简）
+
+1. **`tools/quant_trading_monitor.py`（极小补丁）**：ack-buy/ack-sell 加 `--venue`（paper 默认）/`--note`；sell 全仓校验 + venue 一致性校验；新增 `skip` 子命令（HUMAN_SKIP alert + forward SKIP 记录，进现有 settle_forward，不动状态机）；`_write_summary` 增 `data_trust` 字段。
+2. **`tools/quant_serve.py`**：`now_state()` 纯函数（上述 durable 读取集 + heartbeat/last_scan 分离 + 时段感知 stale + event-matched brief join）；GET `/api/quant/now`；`do_POST` 三端点 → monitor CLI subprocess（buy/sell/skip 字段要求如上）；`writes_enabled_for_host()` loopback 门。
+3. **`tools/quant_render_business_dashboard.py`**：NOW 卡（静态内嵌 now 快照 + 30s 轮询 + STALE 降级）；LIVE/TODAY/HISTORICAL/RESEARCH 徽章；Action Queue（READY/EXIT/SYSTEM_UNAVAILABLE/DATA_UNTRUSTED，三态 RUNTIME/AGENT/HUMAN，NEAR 降次级）；Open Positions 卡（venue/P&L/D+n）；今日时间线（alerts+soak 组装）；按钮表单 POST；候选池 meta 行。9/3 diagnostic 保持 HISTORICAL 徽章。
+4. **`plugins/zuaef-quant/zuaef_quant/toolset.py`**：`record_trade_outcome` → subprocess canonical ack CLI（LOCAL_WRITE、无 approval、venue/note 透传）；新增 `get_trading_context`（进程内 stdlib 只读 trading artifacts，§15.1 bounded JSON）；新增 `render_quant_business_artifact`（subprocess renderer `--out workspace/artifacts/quant/delivery/quant-business-<ts>.html`）。旧 outcomes.jsonl 写路径删除。
+5. **测试**：monitor（venue/note/skip/data_trust/全仓校验/venue 一致性）；serve（now_state fixture 测试、ack 命令构造校验、loopback 门、HTTP POST 集成 monkeypatch subprocess）；plugin（argv 捕获、无 approval 断言、get_trading_context/render）；business（NOW/timeline/action-join payload，现有 82 测试不回归）。
+6. **`docs/quant/README.md`**：顶部日期 addendum（Workbench v0.1 Phase 1）。
+7. **渲染 business.html + ruff + manifest surgical 更新。**
+
+## 延后（已确认方向）
+T7–T10 Telegram（方向：扩 zuaef-telegram 通知工具加 sendDocument，approval-gated）、Golden Path。
+
+## 不做（§30 + 修正案）
+REDUCE/部分平仓、broker 下单、Redis/Celery/Kafka/DB、第二账本、LLM 轮询、自动调参、重做视觉、模拟数据、Gateway/core 改动、非 loopback 写接口。
\ No newline at end of file

diff --git a/_bmad-output/implementation-artifacts/spec-hideable-indicator-notes.md b/_bmad-output/implementation-artifacts/spec-hideable-indicator-notes.md
new file mode 100644
index 0000000..dd1ba08
--- /dev/null
+++ b/_bmad-output/implementation-artifacts/spec-hideable-indicator-notes.md
@@ -0,0 +1,70 @@
+---
+title: '将量化看板指标备注右侧栏改为隐藏式弹出面板'
+type: 'feature'
+created: '2026-09-04'
+status: 'in-review'
+review_loop_iteration: 0
+baseline_commit: '58142afaa51b56365cb01d31251a2d14c52296c3'
+context: []
+---
+
+<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">
+
+## Intent
+
+**Problem:** 量化业务看板的“指标备注”当前作为机会板右侧常驻栏，占用首屏横向空间。用户希望默认隐藏，需要时从右侧弹出查看。
+
+**Approach:** 保留现有 glossary 内容和指标详情 modal，将常驻 aside 改为右侧 drawer；机会板提供打开按钮，drawer 支持关闭按钮、遮罩点击和 Escape 键关闭。
+
+## Boundaries & Constraints
+
+**Always:** 初始状态隐藏；打开按钮使用 `aria-expanded`/`aria-controls`；面板可键盘操作并把焦点还给打开按钮；继续使用唯一的 `GLOSSARY` 与 `data-m` 详情路径；使用现有内嵌 CSS/JS，不引入外部依赖；窄屏不产生横向溢出。
+
+**Ask First:** 无；沿用当前深色看板样式和右侧滑入交互。
+
+**Never:** 不修改指标定义、真实数据、趋势图、候选排序、扫描接口、交易状态或 API；不复制第二份 glossary 数据；不恢复常驻右栏。
+
+## I/O & Edge-Case Matrix
+
+| Scenario | Input / State | Expected Output / Behavior | Error Handling |
+|----------|--------------|---------------------------|----------------|
+| DEFAULT_VIEW | 页面初次加载 | 备注 drawer 隐藏，机会板占满可用宽度，打开按钮可见 | 不依赖 drawer 先显示 |
+| OPEN_PANEL | 点击打开按钮 | drawer 与遮罩显示，`aria-expanded=true`，焦点进入关闭按钮 | glossary 仍正常渲染 |
+| CLOSE_PANEL | 点击关闭、遮罩或按 Escape | drawer 隐藏，状态恢复，焦点回到打开按钮 | 重复关闭不报错 |
+| OPEN_METRIC | 点击 drawer 内指标 | 现有指标详情 modal 显示同一份定义数据 | 未知 key 不打开空 modal |
+
+</frozen-after-approval>
+
+## Code Map
+
+- `tools/quant_render_business_dashboard.py:1320-1333` -- 机会板和当前 `note-side` 常驻右栏模板。
+- `tools/quant_render_business_dashboard.py:1490-1511` -- 当前布局、右栏和 modal 样式；补充 drawer、遮罩、响应式规则。
+- `tools/quant_render_business_dashboard.py:1545-1567` -- `GLOSSARY`、`renderGlossary()`、指标详情事件；加入 drawer 开关并保持 `data-m` 行为。
+- `tools/quant_render_business_dashboard.py:1244-1407,1522-2147` -- 自包含 HTML/CSS/JS 模板；`render_html()` 将其内嵌输出。
+- `tests/test_quant_business.py` -- business renderer 回归测试；目标是验证默认隐藏、开关控件和 glossary modal 不回归。
+
+## Tasks & Acceptance
+
+**Execution:**
+- [x] `tools/quant_render_business_dashboard.py` -- 用右侧隐藏 drawer 替换 `note-side`，加入 ARIA、遮罩、Escape 和焦点恢复 -- 满足隐藏式弹出需求并保持现有指标说明。
+- [x] `tests/test_quant_business.py` -- 增加 HTML 结构和交互钩子断言 -- 防止备注栏重新常驻或详情入口失效。
+
+**Acceptance Criteria:**
+- Given HTML 已生成, when 首次打开, then 无常驻指标备注右栏且存在打开按钮。
+- Given drawer 隐藏, when 点击打开, then drawer、遮罩和 glossary 显示，`aria-expanded` 为 `true`。
+- Given drawer 打开, when 点击关闭、遮罩或按 Escape, then drawer 隐藏且焦点回到打开按钮。
+- Given glossary 已显示, when 点击指标, then 原有指标详情 modal 仍显示定义、计算、用法、局限和来源。
+- Given 窄屏视口, when 打开 drawer, then 面板不超过视口且机会板无横向溢出。
+
+## Spec Change Log
+
+## Design Notes
+
+drawer 与指标详情 modal 分层；glossary 只渲染到 drawer 一次。通过 `hidden`、`is-open` 和遮罩状态控制显示，不增加组件库。
+
+## Verification
+
+**Commands:**
+- `timeout 180 .venv/bin/pytest -q tests/test_quant_business.py` -- expected: 全部通过。
+- `.venv/bin/python -m ruff check tools/quant_render_business_dashboard.py tests/test_quant_business.py` -- expected: 无 lint 错误。
+- `.venv/bin/python tools/quant_render_business_dashboard.py --out docs/quant/business.html` -- expected: 成功生成含隐藏 drawer 的 HTML。


Do not invoke any skill. If the instruction file is unreadable, report that exact failure and stop. Return only the review result.
