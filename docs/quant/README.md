# ZUAEF A股决策 Agent — 实现总结与实操指南

**Spec:** `ZUAEF-ASHARE-001` v2.0-final(2026-09-03, 基线 main; 见 zuaef-quant-final-spec-v2.0-optimized/) · v1.0-final 为历史
**状态:** ENGINEERING FREEZE(P5.5 观察模式,2026-09-02 起生效)
**当前阶段判断:** 工程链路已足够完整;最大的未知数已从"软件能不能工作"变成"它在真实市场里有没有用"。下一张 task 由真实市场派发,不由排期派发。

**2026-09-02 增补 · 业务看板与候选发现(Quant Business Dashboard + Candidate Discovery v1.0):**
新增业务决策页 `docs/quant/business.html`(默认页)与确定性候选发现管线
`tools/quant_build_candidates.py`,把产品重心从"软件进度证明"转向"市场/策略证据"。工程/审计页保留为
`docs/quant/dashboard.html`(经 `/engineering` 访问)。三个宇宙分离:`legacy_watchlist`(用户自选/持仓名单,
只诊断不自动晋级; 2026-09-02 起含截图追加的 11 只自选股, 名单由用户提名扩充)/ `candidate_pool`(CSI300∪CSI500 筛出的 20–50 只证据排名)/ `action_candidates`
(活跃策略在候选池上的确定性触发,0–10 只)。**候选排名不是买入建议;盈利能力仍未证明**;实时动作依旧
必须来自既有确定性触发证据。详见 §5.7 与 `benchmarks/quant/gen1/candidates_policy.toml`。

**2026-09-04 增补 · M1 交易时段循环 + P0.5 双引擎对账 + Final Spec v2.0:**
① `tools/quant_trading_monitor.py`(M1 Live Trading Loop v0.1):交易时段内连续盯盘循环(30–60s),
机会状态机 WATCH→NEAR→READY→INVALIDATED,`EXECUTED` 仅由用户 `ack-buy` 置位;持仓为一等公民
(仅 ack-buy 创建/ack-sell 关闭,按冻结 S3 退出规则监控);forward 观察(D+1/3/5/8、MFE/MAE)只从缓存
日线对真实记录累积,绝不 mock/回填。状态落 `workspace/artifacts/quant/trading/`。**Agent 不轮询**:
循环全确定性,实质状态变化进告警流后由 Agent 事后解读(详见 spec 02)。
② `tools/quant_p05_reconcile.py`(P0.5):同一冻结策略+同一冻结 intents 双引擎逐笔对账——Qlib 研究面
(qfq, market_truth OFF)vs 独立 A 股重放(raw, market_truth ON),差异必归因(A 市场规则差/B 不支持对等/
C Qlib 局限/D-E bug/F 无法解释),**任何 UNEXPLAINED 残留 = P0.5 失败**。验证通过后无需每日跑。
③ 权威 spec 升级为 `zuaef-quant-final-spec-v2.0-optimized/`(EXECUTABLE);`zuaef-quant-final-spec-v2.0-clean/`
为可读精校版;产品北星=`select → monitor → decide → manage → observe → learn`。
另:评估/审计工具(quant_core/live_scan/anti_leakage/pit_audit/eval_qlib/validate_semantics)随冻结期
修订同步更新;business/dashboard 快照刷新。日常操作索引见 `workspace/knowledge/concepts/quant-live-ops.md`。

---

## 目录

1. [项目定位](#1-项目定位)
2. [开发链路全程复盘](#2-开发链路全程复盘)
3. [系统架构](#3-系统架构)
4. [实现情况清单(诚实版)](#4-实现情况清单诚实版)
5. [实操指南:观察模式日常运行](#5-实操指南观察模式日常运行)
6. [重启开发的准入规则](#6-重启开发的准入规则)
7. [命令速查与故障排查](#7-命令速查与故障排查)

---

## 1. 项目定位

用最小的可靠 Agent 循环,帮小资金 A 股散户做更快、更有依据的决策:

```text
真实行情 + 历史大样本 + 确定性策略评估 + LLM 策略搜索/反思 + 模拟/实盘反馈
        ↓
减少直觉交易 → 更有依据的资金决策
```

最高优先级规则(贯穿全程):**不造量化平台。** 接通真实数据与成熟引擎,诚实地证明一个完整策略可被评估,然后让 Agent 从证据中迭代。盈利是实证目标,不是软件保证。

四行冻结状态(证据见 §4):

```text
Research Engine Proof    PASS
Self-learning Loop Proof PASS
Profitability Proof      NOT YET(有意停止 in-sample 追寻)
Live Decision Product    FIRST PROOF PASS(交互式;watcher 有意未建)
```

---

## 2. 开发链路全程复盘

每个阶段以"可用证明"收尾,而非类层次结构。所有关键失败都是真实复现后修复的,无一处是预设架构。

### U0 — 上游兼容刷新 ✅

- 基线先证明绿:pydantic-ai 2.30.0 / harness 0.20.0 下 759 tests 全过。
- 升级到 **pydantic-ai 2.35.3 / harness 0.27.0**,零代码改动,759/759 通过;`tools/probe_upstream_baseline.py` 全部 REQUIRED 原语 READY(含 CodeMode 元数据选择器)。
- Harness 小版本锁定 `>=0.27,<0.28`;`docs/upstream-baseline.md` 更新;`BUILD_MANIFEST` 再生成。
- U005(上下文阈值):源码中不存在固定数值阈值,无需迁移——按证据记为 no-op。

### P0 — 真实数据证明 ✅

- akshare **1.18.94** 隔离在 uv 依赖组 `quant`(`uv sync --frozen` 的生产安装永不携带,Spec D001)。
- 实测:600519 日线(qfq+raw,2018 起 2101 行,当日 bar);qfq 与 raw 确认不同(复权真实生效);CSI500 成分 500 只(CSIndex,生效日 2026-08-28);全市场快照 5550 只;日历新鲜度 0 天。
- **真实失败①:EastMoney 端点在本部署网络被传输层拒绝**(SSL EOF)。按数据面替换为同版本 akshare 的腾讯(历史)/新浪(快照)/中证指数(成分)路径,来源写进每份缓存 sidecar。
- 证据:`workspace/artifacts/quant/p0-data-proof-2026-08-28.log`;缓存 `data/quant-cache/`。

### P1 — 一个固定策略 + Qlib 评估 ✅

- 宇宙:当前 CSI500 成分排序 stride 采样 **37 只**(12 只因 2018-06-30 前无足够回溯被排除,逐只记录)。PIT 局限(今日成员回看历史)显式记录于所有 Strategy Result。
- 冻结基准配置 `benchmarks/quant/gen1/{quant.toml,strategy.toml}`:research 2018–2022(Agent 可见)/ promotion 2023–2024(host-only)/ holdout 2025+(隐藏,从未触碰)。
- **真实失败②:pyqlib 0.9.7 无 cp313 wheel**(Cython 包)。 qlib 是研究内核、永不进 Agent 运行时 → 建 gitignored 的 **Python 3.12 侧环境 `.venv-quant`**(akshare+pyqlib 共存)。
- wheel 不带 `scripts/dump_bin.py` → 从**已审计上游 commit** vendor 到 `tools/quant/upstream/`(MIT,来源注明),调用其公开的 `DumpDataAll(...).dump()`。
- 基线 `volume_pullback_reversal`(5 日回撤 ≤ −6% + 20 日量比 ≥ 1.8 + 收盘强度 ≥ 0;出场:持有天数/MA5/止损/止盈):**24 笔 / 5 年 / 年化 +0.20% / 最大回撤 −2.1% / 成本拖累 0.44%** —— 真实的、不 attractive 的基线。

### P2 — 独立重放 + A股执行真相 ✅

- `tools/quant_core.py` 事件循环引擎:**只消费冻结 intents + raw 可执行价格 + 冻结规则**,永不读 Qlib NAV。规则生效日期化(T+1、板块涨跌停(创业板 2020-08-24 起 20%)、涨停买/跌停卖 block、停牌递延、整手、佣金+最低佣金、印花税有效日期(2023-08-28 下调)、滑点)。
- **14 个防伪 alpha 测试**(T+1、涨跌停、停牌、整手、成本、board 差异、market_truth 开关、无未来函数)。**测试抓出一个真 bug:intent 在决策日当天成交**——修复为"次日开盘成交"。
- 双引擎一致性:年化差 **0.02pp**(容忍 3pp)。vector 阶段(qfq 面板、关市场真相)vs 独立重放(raw 价格、开市场真相)消费**同一份冻结 intents**。

### P3 — QuantDecision 接入 ZUAEF ✅

- `plugins/zuaef-quant`(workspace 成员,`zuaef.plugins` 入口点 `quant`):轻量 `Capability(id="quant-decision")` + 领域指令(证据层级/真相来源/报告语义/操作守则)+ 六个确定性工具,**Core 零业务改动**。重活在侧环境 subprocess 执行,插件包自身不背 akshare/qlib。
- 工具(6 个):`evaluate_strategy`(纯数值参数、白名单校验、返回有界证据)/ `get_live_signals`(确定性扫描,LLM 永不扫全市场)/ `record_decision_brief`(六种 action 枚举,实测 signal→brief 延迟)/ `record_trade_outcome`(canonical ack,仅记录人类已成交事实、不下单;venue=paper/real;Phase 1 仅全仓平仓)/ `get_trading_context`(只读 canonical trading 上下文,不重算市况、不重推触发)/ `render_quant_business_artifact`(确定性渲染业务 HTML 到 `artifacts/quant/delivery/`)。
- **真实失败③:首个版本让模型提交整段 TOML 字符串,弱模型不会调** → 改为普通数值参数(默认值即基线),一次工具调用即可完成 mutation。
- Profile `profiles/quant-decision.toml`(`allow_capabilities = true`);22 个插件契约测试(白名单越界、canonical ack 路由与宿主拒绝原样透传、get_trading_context 只读投影、渲染落点等)。

### P4 — 三轮真实模型进化 ✅

三轮全新 `zuaef-agent run --profile quant-decision`,每轮**一个实质 mutation**,读上轮证据、调一次 evaluate_strategy、自写 Strategy Result:

| 轮次 | 变更 | 年化(replay) | 笔数 | 结论 |
| --- | --- | --- | --- | --- |
| 基线 | — | +0.20% | 24 | 平进平出 |
| S1 | 回撤 −0.06→−0.05 | **+0.34%** | 29 | 改善 |
| S2 | 量比 1.8→2.2 | +0.01% | 9 | **被证据否决** |
| S3 | 持有 5→8 天 | **+0.37%** | 29 | 最优;纯出场侧收益,零新增成本 |

- Agent 的 S2 Result 自己写了 "hypothesis not supported",S3 换杠杆 —— **evidence → mutation → fresh evaluation → next decision 循环为真**,不是预写 workflow。
- 诚实记录:前两次 run 在业务产出完成后仍探索、撞 tool-call limit 收尾(execution_state failed 但产物完整);收紧 prompt 后 S2/S3 干净完成。
- 环境注记:两次运行中模型把结果文件写到 `workspace/workspace/`(相对路径叠加 workspace 根),产物真实但路径嵌套 → P4.5 修复。

### P4.5 — 三项修复 + 冻结 ✅

1. **workspace/workspace 根因**:插件路径无误(child 目录一直落对);是 prompt 让 Agent 写了带 `workspace/` 前缀的相对路径,FileSystem 再拼一次根。修复在插件侧:`evaluate_strategy` 返回 workspace 相对 `result_file`,指令写明"原样使用返回路径";Core 未动。
2. **单轮 clean exit**:宿主硬守卫——每轮第二次 `evaluate_strategy` 直接报错;能力指令固化轮次形状(读父结果 → 一个 mutation → evaluate 一次 → 写结果 → END)。无 workflow engine。
3. **S3 冻结为 `DEMO_ACTIVE_STRATEGY`**(`benchmarks/quant/gen1/active.toml`,含证据出处);`STATUS.md` 落盘四行证明状态。**停止 S4 及一切历史调参**——29 笔交易上的继续搜索就是 p-hacking。

### P5 — 实时决策链路首次验证 ✅

- **扫描提速 16×**:akshare 可用的两个 spot 接口均全市场(新浪 48s / 腾讯 74s),对 37 只不成比例 → 按 spec 04 §9 替换条款,scan 直接使用 `qt.gtimg.cn` 批量报价(与历史数据同一腾讯数据面,GBK 字段解析,手→股换算):**37/37 只 2.9 秒**。数据源显式记录在输出。
- scan 只读 `active.toml`,输出 ≤10 候选,含 quote_time / pullback_5d / volume_ratio / scan_ms / latest_quote_time。
- 新工具 `record_decision_brief`:校验六种 action 枚举,以 scan 返回的 signal_timestamp 实测端到端延迟,brief 存结构化 JSON(P6 结算可直接消费)。
- **真实盘中验证(2026-09-02 11:30)**:37 只 0 触发 → Agent 独立给 **NO_TRADE**(没有因为"用户启动了助手"就硬找推荐——V007 通过)→ brief 落盘,**signal→brief 延迟实测 86 秒**,本次 run `execution_state: completed` 干净退出。
- 证据:`workspace/artifacts/quant/briefs/brief-live-*.json`。

### P5.5 — 观察模式(当前阶段,2026-09-02 起)

**代码冻结。** U0–P5 全部 PASS;不再开发 P6/P7 框架、dashboard、watcher、PIT platform、10-run A/B、SpendLimits、broker、S4 调参。转入"run → observe → record → judge":用现有系统在真实未来市场里自然积累 forward evidence。详见 §5、§6。

---

## 3. 系统架构

### 3.1 分层与数据流

```text
ZUAEF Agent Core(业务域中立,零量化改动)
      │  既有上游能力:StepPersistence / approval / FileSystem / ToolSearch
      ▼
zuaef-quant Plugin                     ← plugins/zuaef-quant(workspace 成员,入口点 quant)
      │  Profile: quant-decision(allow_capabilities = true)
      ▼
QuantDecision Capability               ← 10 条稳定领域指令 + 1 个 QuantToolset
      │
      ├── evaluate_strategy            ─┐
      ├── get_live_signals              ├─ subprocess(.venv-quant/bin/python)
      ├── record_decision_brief        ─┤     ↑ 隔离:重依赖永不进 Agent 环境
      └── record_trade_outcome(纯本地)─┘
                │
                ▼
      tools/quant_core.py(确定性机制:缓存/规则/重放/指标)
      tools/quant_eval_qlib.py(Qlib 面板表达式 → 冻结 intents → 双引擎 → artifacts)
      tools/quant_live_scan.py(子集批量报价 → 确定性触发)
      tools/quant_p0_data_proof.py / quant_fetch_universe.py(数据证明/宇宙准备)
                │
                ▼
数据面:akshare 1.18.94
  ├─ 历史:stock_zh_a_hist_tx(腾讯,qfq/raw,2018 起,含有界重试)
  ├─ 成分:index_stock_cons_csindex(CSIndex)
  ├─ 实时:qt.gtimg.cn 批量报价(37 只一次请求,~2.9s;替换决策见 §2 P5)
  └─ 本地缓存:data/quant-cache/{daily,universe,qlib_data}/ CSV+meta.json sidecar
```

### 3.2 评估流水线(evaluate_strategy 内部,全宿主确定性)

```text
validate spec(白名单数值字段;任意 Python 永不越过边界)
→ 读冻结 gen1 配置 + 宇宙 manifest
→ stage CSV → dump_bin → qlib bin 库
→ D.features 表达式(Ref/Mean)→ 信号面板
→ 确定性意图构建(T 日决策、T+1 开盘成交、按代码排序取候选)
→ 双引擎跑同一份冻结 intents:
     vector 阶段(qfq 面板,market_truth=OFF)
     独立重放(raw 价格,market_truth=ON:T+1/涨跌停/停牌/整手/成本)
→ evidence.json(+trades/blocked/equity CSV)+ result.md
→ 一致性判定:年化差 ≤ 3pp(冻结于 quant.toml)
```

### 3.3 冻结权威与工件地图

| 路径 | 角色 |
| --- | --- |
| `benchmarks/quant/gen1/quant.toml` | 冻结市场规则/成本/基准窗口(生效日期化) |
| `benchmarks/quant/gen1/strategy.toml` | gen1 基线策略(默认参数的出处) |
| `benchmarks/quant/gen1/active.toml` | **DEMO_ACTIVE_STRATEGY = s3_longer_hold(冻结)** |
| `benchmarks/quant/gen1/legacy_watchlist.toml` | legacy 用户自选/持仓名单(只诊断, 非机会宇宙; 按用户提名扩充) |
| `benchmarks/quant/gen1/candidates_policy.toml` | 候选发现 v1 政策(权重/阈值, 阈值在政策不在代码) |
| `workspace/artifacts/quant/business/candidate_snapshot.json` | 候选池审计工件(评分/理由/红旗/来源/coverage) |
| `data/quant-cache/candidates/active_symbols.json` | 候选池 → live scan 的确定性 handoff(gitignored) |
| `tools/quant_build_candidates.py` | 确定性候选发现(CSI300∪CSI500 → 评分 → 行业封顶) |
| `tools/quant_render_business_dashboard.py` | 业务页渲染器(纯 stdlib) |
| `workspace/artifacts/quant/business/last_scan.json` | 最近一次活跃宇宙扫描快照(quant_daily.sh 落盘) |
| `benchmarks/quant/gen1/STATUS.md` | 四行证明状态 + 冻结决策 + 已知局限 |
| `benchmarks/quant/gen1/OBSERVATION_LOG.md` | 观察模式每日一行日志 |
| `workspace/artifacts/quant/gen1/` | 基线评估工件(evidence/trades/equity/result) |
| `workspace/artifacts/quant/children/` | S1/S2/S3 子策略工件;Agent 自写的 `S*-result.md` 在 `workspace/workspace/artifacts/quant/children/`(路径嵌套为运行环境行为,产物真实) |
| `workspace/artifacts/quant/briefs/` | Decision Brief JSON(含实测延迟) |
| `data/quant-cache/` | 行情缓存+sidecar、qlib bin 库(gitignored,可随时重建) |
| `.venv-quant/` | Python 3.12 侧环境(akshare+pyqlib;gitignored) |
| `tools/quant/upstream/dump_bin.py` | vendored qlib 上游脚本(已审计 commit,MIT) |
| `tests/test_quant_replay.py` | 14 个防伪 alpha 测试 |
| `tests/test_quant_plugin.py` | 16 个插件契约测试 |

### 3.4 边界纪律(实现期实际遵守的)

- Core 零业务改动;一切业务行为在 Toolset/插件层。
- Agent 不能改评估器/规则/成本/数据切分/基准;不能提交任意 Python;一次评估守卫宿主强制。
- `ENTER_CANDIDATE` 永远不是订单;无候选时 NO_TRADE 合法且已实测发生。
- 环境变量:`ZUAEF_QUANT_PYTHON`(侧环境解释器)、`ZUAEF_QUANT_REPO_ROOT`(仓库根;agent 须从仓库根运行或显式设置),缺失即响亮组合错误。

---

## 4. 实现情况清单(诚实版)

### 已证明(全部有工件证据)

| 能力 | 证据 |
| --- | --- |
| 真实行情接入(历史/成分/快照/新鲜度) | `workspace/artifacts/quant/p0-data-proof-2026-08-28.log` |
| 确定性策略评估(Qlib + 双引擎 + 成本) | `workspace/artifacts/quant/gen1/evidence.json` |
| A股执行真相重放(T+1/涨跌停/停牌/整手/成本) | `tests/test_quant_replay.py` 14 项全绿 |
| 跨引擎一致性 | 基线 0.02pp / S1 0.18pp / S3 0.18pp(容忍 3pp) |
| 证据驱动的自学习循环 | `S1/S2/S3-result.md`(S2 被否决,S3 换杠杆) |
| 实时子集扫描(确定性,2.9s) | scan 输出(universe_size=37, scan_ms≈2900) |
| NO_TRADE 不强迫候选 | `briefs/brief-live-*.json`(2026-09-02 盘中实测) |
| 端到端延迟测量 | signal→brief 86s(含模型推理;scan 仅 ~3s) |
| 回归门禁 | 默认套件 810 passed;quant 组 30 passed;ruff 干净 |

### 未构建 / 已知限制(冻结期内不解决,除非 §6 触发)

- **PIT universe 未建**:今日 CSI500 成员回看历史(幸存者/成分偏差)。所有历史数字只能读作"这 37 只股票历史轨迹上的实验结果"。**它必须成为任何盈利声明的前置门。**
- **绝对优势微弱 + 小样本**:最优 +0.37% 年化、29 笔,远在噪声内;当前定位是"验证产品链路的演示工具",不是交易建议。
- promotion/holdout 窗口已冻结、从未触碰(host-only;留给未来晋级测试)。
- 86s 延迟未优化:**先等真实 trigger 判定信号有效窗口**(分钟级还是半小时级),再决定是否值得优化——现在优化就是无证据工程。
- watcher/轮询守护有意未建(交互式优先,spec V008);paper 结算引擎有意未建(前几笔 trigger 人工结算,让市场告诉我们需要记什么字段);broker 接入永不在 v1。
- EastMoney 数据面在本网络不可达(腾讯/新浪/中证指数替代,已记录);雪球报价需 token 不可用。
- 观察期若连续无触发,"策略密度不足"本身是有价值结论(见 §6)。

---

## 5. 实操指南:观察模式日常运行

### 5.1 一次性准备(已就绪,换机时对照)

```bash
# 1) 主环境(Agent + 测试;Python 3.13)
uv sync                          # 生产安装,不带 quant 组
uv sync --group quant            # 若要在主环境跑 quant 测试/数据工具

# 2) 侧环境(评估 + 扫描;Python 3.12)
uv venv --python 3.12 .venv-quant
uv pip install -p .venv-quant/bin/python "akshare==1.18.94" "pyqlib==0.9.7"

# 3) profile 安装(组合发现)
mkdir -p ~/.config/zuaef/profiles
cp profiles/quant-decision.toml ~/.config/zuaef/profiles/

# 4) 模型环境(.env):LLM_API_BASE / LLM_API_KEY / LLM_MODEL 必须有效
```

### 5.2 每个交易日:跑一次决策(唯一日常动作)

交易时段内,从仓库根目录:

```bash
ZUAEF_QUANT_PYTHON=$PWD/.venv-quant/bin/python \
ZUAEF_QUANT_REPO_ROOT=$PWD \
.venv/bin/zuaef-agent run \
  --profile quant-decision --request-limit 10 --tool-calls-limit 12 \
  "Live decision check for the A-share active strategy. FIRST tool call: get_live_signals(). Then: (1) decide the verdict NO_TRADE or ENTER_CANDIDATE strictly from the returned trigger evidence (empty trigger list means NO_TRADE — do not force a candidate); (2) call record_decision_brief once with decision_id 'brief-live-<unixseconds>', the signal timestamp and strategy name from the scan output, your why/invalidation/expected_holding, and the raw trigger facts (or 'none'); (3) stop. No other tools, no file writes."
```

只想快速看盘而不起 Agent(不产生 brief,不消耗模型):

```bash
uv run --group quant python tools/quant_live_scan.py
```

### 5.3 每日一行观察日志(唯一记录动作)

向 `benchmarks/quant/gen1/OBSERVATION_LOG.md` 追加一行:

```text
| 2026-09-02 | 11:30 | 37 | 0 | NO_TRADE | 2.9s | 86s | — |
```

列:日期 / 时间 / 扫描只数 / 触发数 / Agent action / scan 耗时 / brief 延迟 / 备注。
brief 文件本身已含完整字段,日志行只为肉眼巡检;无 DB。

### 5.4 出现真实 trigger 时(这是整个观察期的目的)

**不要开发任何东西。** Agent 会产出 ENTER_CANDIDATE/WATCH brief;人工追加记录到观察日志(或旁注),字段从简:

```text
signal time / signal price
brief time / brief price(→ price drift)
next open 成交价(假设按规则进)
D+1 / D+3 / D+5 / D+8 收盘
MFE(期间最大有利偏移)/ MAE(最大不利偏移)
实际可成交性(是否一字板/停牌/流动性异常)
```

这几行就是第一笔 forward evidence。前几笔**人工结算**,不要写结算程序——等市场告诉你真正重要的字段是什么(可能是 latency drift、可能是一字板不可得、可能是密度太低)。

### 5.5 观察期只看五个指标

| 指标 | 回答的问题 |
| --- | --- |
| Trigger frequency | 有没有足够交易机会 |
| Signal→Brief latency | Agent 是否赶得上 |
| Signal→Brief price drift | 延迟是否造成真实经济损失 |
| Subsequent return path | 信号本身是否有意义 |
| Agent veto/增量判断 | LLM 相对"裸扫描器"到底有没有增益 |

最后一条是产品核心:目前尚未证明 "scanner+LLM" 优于 "scanner alone"。积累 30–50 个真实 trigger 后的唯一重要 A/B:A = 每个 trigger 直接 paper enter;B = Agent 有权 WATCH/NO_TRADE;比较期望值、回撤、坏交易剔除率、错失的好交易。

### 5.6 周期性维护(与观察无冲突,可低频执行)

```bash
# 每周或数据面报错时:重跑数据证明(应保持 PASS)
uv run --group quant python tools/quant_p0_data_proof.py

# 改动任何代码后(冻结期内应极少):全量门禁
uv run pytest -q && uv run --group quant pytest tests/test_quant_replay.py tests/test_quant_plugin.py tests/test_quant_business.py -q
.venv/bin/python -m ruff check .
.venv/bin/python tools/regen_manifest.py && .venv/bin/python -m pytest tests/test_manifest_integrity.py -q

# 缓存可随时重建(gitignored);重建后需重跑 P0 证明 + 一次基线评估核对一致性
```

### 5.7 业务看板与候选发现(2026-09-02 增补)

#### 三个宇宙(不得混用)

```text
legacy_watchlist          benchmarks/quant/gen1/legacy_watchlist.toml
  用户自选/持仓名单        只在 Legacy Holdings 卡诊断 + /api/watchlist 显式扫描;
  (601233/002460/          不再是隐式默认活跃宇宙; 名单按用户提名扩充
  002415/000009 + 11 只          ↓ 不自动晋级
  2026-09-02 截图追加)
candidate_pool            workspace/artifacts/quant/business/candidate_snapshot.json
  CSI300∪CSI500 筛选       盘后/手动刷新, 目标 20–50 只, 证据排名(价值/质量/可交易/时序)
  + 评分 + 行业封顶             ↓ 确定性 handoff
active_candidates         data/quant-cache/candidates/active_symbols.json
  活跃策略触发的输入        quant_live_scan.py 默认宇宙 → 0–10 触发 → Agent
```

关键规则:

- **候选排名不是买入建议**——它只是"值得研究/关注"的注意力排序;实际动作仍需确定性触发 + Agent 判定 + 人工决策。
- 空/失败宇宙必须响亮失败:空 `active_symbols.json` 会让 `quant_daily.sh` 与 `/api/scan` 报错,绝不能把 `0 scanned / 0 trigger` 当成合法的 `NO_TRADE` 市场结论。
- 评分每个成分都透明(原始指标 + 百分位 + 缺失字段 + 理由 + 红旗),权重与阈值全部在 `benchmarks/quant/gen1/candidates_policy.toml`,不在代码里。负 PE 按缺失处理,不是"很便宜"。
- top30 内每个一级行业最多 4 只;行业数据缺失时如实标记 `unknown`,不假装分散。
- essential coverage < 80% ⇒ 快照 `DEGRADED`,页面挂 `DATA DEGRADED` 横幅,不声称 A 级完整。
- 银行/券商/保险走金融部门模型(跳过工业 CFO/杠杆规则并显式标注 `sector_model=financial`);行业数据缺失时标记 `unsupported`。

#### 刷新与运行

```bash
# 盘后/手动:候选池刷新(确定性, 无 LLM; 首次约 5-8 分钟, 之后吃缓存)
uv run --group quant python tools/quant_build_candidates.py

# 本地看板(默认业务页; 工程页在 /engineering)
python3 tools/quant_serve.py
#   http://127.0.0.1:8787/              → 业务决策页 docs/quant/business.html
#   http://127.0.0.1:8787/engineering   → 工程/审计页 docs/quant/dashboard.html
#   /api/scan      → 活跃候选宇宙实时扫描
#   /api/watchlist → legacy watchlist 显式扫描

# 只重渲页面(不起服务)
python3 tools/quant_render_business_dashboard.py
```

数据面(全部已在本部署网络实测可用,无 EastMoney 依赖):成分 CSIndex(CSI300/CSI500,单指数失败回退
上次缓存并标注新鲜度)、快照/估值腾讯 qt.gtimg.cn 批量报价(PE/PB/股息率/成交额)、财报新浪
`stock_financial_analysis_indicator`、行业巨潮申万门类、3Y 估值史百度。每个数据集带
source/retrieved_at/freshness/fallback 标注;财报新鲜度按"报告期"计(缓存回退不掩盖真过期)。

#### 冻结纪律(增补后依旧有效)

本增补属观察期内的业务面扩展(spec 授权),不是重启开发。再次冻结:下一张代码 task 需要真实市场/数据失败
(覆盖率持续过低、排名被明显价值陷阱支配、金融部门误判、触发密度长期不可用、刷新过慢/不可靠、forward
结算暴露系统性问题)。"想要更好看的页面"不构成重启理由(完整规则见 spec pack 10 §4)。

---

## 6. 重启开发的准入规则

**强规则:没有来自真实市场的新问题,不开新 feature。** 观察期退出条件(二选一,均为有效结果):

- **A. ≥10 个真实 trigger 事件** → 进入人工结算复盘,决定:A/B 实验、是否值得自动化;
- **B. 观察期足够长仍 0 trigger** → "策略密度不足"成立,重启的是**策略/宇宙研究**(不是框架)。

具体触发映射(真实问题 → 才允许做的事):

| 观察到的真实问题 | 才允许开发 |
| --- | --- |
| 每天手动跑 N 次太烦 | watch scheduler |
| brief 积累到几十个、人工结算吃力 | paper settlement(按当时真正需要的字段设计) |
| 行情延迟/失败率影响判断 | 更换付费/broker 数据源 |
| 连续多周 0 触发 | 扩宇宙/调条件/换策略族(研究,非框架) |
| price drift 明显(如 >1%) | 优化 prompt/工具轮次/模型(压缩 86s 中的推理部分) |
| 要做晋级测试 | host-only promotion 评估 + 隐藏 holdout(已冻结窗口) |

冻结期**禁改清单**:S4 及后续调参、P6/P7 框架、dashboard、watcher、PIT platform、10-run A/B、SpendLimits、broker。PIT universe 是唯一提前解冻的例外条件:仅当出现"准备做任何盈利声明"时,它作为前置门解冻。

---

## 7. 命令速查与故障排查

### 7.1 速查

```bash
# 数据证明(P0)
uv run --group quant python tools/quant_p0_data_proof.py

# 宇宙准备(仅首次/换宇宙)
uv run --group quant python tools/quant_fetch_universe.py

# 基线评估(命令行直接跑,不经 Agent)
.venv-quant/bin/python tools/quant_eval_qlib.py \
  --config benchmarks/quant/gen1/quant.toml \
  --strategy benchmarks/quant/gen1/strategy.toml \
  --out workspace/artifacts/quant/gen1 --window research

# 实时扫描(无 LLM; 默认宇宙 = 候选池 handoff → 37 只子集回退 → 否则响亮失败)
uv run --group quant python tools/quant_live_scan.py

# 显式 watchlist 扫描(只扫 legacy 名单)
uv run --group quant python tools/quant_live_scan.py --universe-file benchmarks/quant/gen1/legacy_watchlist.toml

# 候选池刷新(盘后/手动, 无 LLM)
uv run --group quant python tools/quant_build_candidates.py

# 业务页渲染(纯 stdlib)
python3 tools/quant_render_business_dashboard.py

# 本地看板服务(loopback; / 业务页, /engineering 工程页)
python3 tools/quant_serve.py

# 日常决策(经 Agent,见 §5.2; 一键版 bash tools/quant_daily.sh)

# 测试
uv run pytest -q                                                  # 默认套件(836)
uv run --group quant pytest tests/test_quant_replay.py tests/test_quant_plugin.py tests/test_quant_business.py -q
```

### 7.2 故障排查

| 症状 | 原因 | 处置 |
| --- | --- | --- |
| `EastMoney / SSL EOF / RemoteDisconnected` | 本网络对 EastMoney 被拒 | 正常;数据面已是腾讯/新浪/CSIndex。若腾讯报价也失败,检查 `qt.gtimg.cn` 可达性 |
| 历史抓取偶发 SSL 失败 | 腾讯限流 | 引擎内已有有界重试(2s/8s);重跑即可 |
| `quant plugin side environment missing` | 侧环境不存在或路径错 | 确认 `.venv-quant/bin/python` 存在,或设 `ZUAEF_QUANT_PYTHON` 绝对路径 |
| `quant plugin cannot locate the repository quant tooling` | agent 不在仓库根运行 | 从仓库根运行,或设 `ZUAEF_QUANT_REPO_ROOT` |
| `profile not found` | profile 未安装 | 见 §5.1 第 3 步 |
| `evaluate_strategy already ran this round` | 一轮守卫生效(设计行为) | 写完 Strategy Result 即结束任务 |
| Agent run `execution_state: failed` 但产物已落盘 | 撞 tool-call limit(探索过头) | 检查产物;prompt 已收紧;必要时再降 limit |
| manifest 完整性测试失败 | 改了受管文件未再生成 | `python tools/regen_manifest.py` |
| 扫描全是 0 触发 | 正常(S3 条件选择性高) | 记日志;连续多周 0 触发才构成 §6 的研究信号 |

### 7.3 版本锁定(当前执行基线)

| 组件 | 版本 | 位置 |
| --- | --- | --- |
| pydantic-ai | 2.35.3 | uv.lock |
| pydantic-ai-harness[skills,code-mode] | 0.27.0(`>=0.27,<0.28`) | uv.lock |
| akshare | 1.18.94 | uv 依赖组 quant |
| pyqlib | 0.9.7 | .venv-quant(py3.12) |
| 主环境 Python | 3.13 | .venv |
