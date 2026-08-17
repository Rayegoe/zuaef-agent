# Editorial Learning Benchmark

20 个真实写作任务（四公开数据集确定性抽取），证明 `EditorialControlCapability`
的 Gate E（A/B/C）与 Gate F（顺序学习）。**本目录是实验资产；plugin 是运行时机制**
（`plugins/zuaef-ace-writing` 不 import 本目录，本目录 import plugin）。

## 布局（git 政策）

```text
committed（git）                     local only（data/，gitignored）
----------------------------------  ------------------------------------
tasks/T01..T20.json                 data/raw/            四源完整数据集
  bounded excerpts (<=1500 chars)   data/derived/tasks_full/  任务全文
  sha256 of FULL texts              data/derived/materials/   ACE 摄入材料
  record id / license / selection
evidence/seed_snapshot.jsonl        由 fetch_sources.py 下载 / build_tasks.py 派生
evidence/human_patches.jsonl
provenance/sources.jsonl + licenses.md
benchmark.jsonl
results/{base,static,adaptive}/
scripts/
```

## 顺序学习协议（Gate F 核心）

human patches **永不一次性灌入**运行时证据文件：

```text
T01  仅 seed 运行 → promote T01
T02  seed + T01   → promote T02
...
T20  seed + T01..T19
```

`promote_patch.py` 强制该顺序（乱序拒绝、重复幂等、每次写入后过
EditorialEvidenceStore 校验）。由此 `Agent@T01 ≠ Agent@T20`，模型权重零变化。

## 三模式（Gate E）

| mode | editorial_control | 运行时证据 | 回答 |
|------|-------------------|-----------|------|
| base | OFF | — | 模型自己写成什么样 |
| static | ON | 仅内置 seed | capability 本身有没有用 |
| adaptive | ON | seed + 逐任务晋升 | 学习有没有增量价值 |

## 使用

```bash
# 1) 数据（或 --reuse 一个既有 raw 树）
uv run python benchmarks/editorial-learning/scripts/fetch_sources.py

# 2) 构建（确定性，重跑可复现）
uv run python benchmarks/editorial-learning/scripts/build_tasks.py

# 3) 环境自检（模型凭证不要求）
uv run python benchmarks/editorial-learning/scripts/run_benchmark.py --check

# 4) 真实运行（需 ZUAEF_MODEL / provider env / ACE_ROOT）
uv run python benchmarks/editorial-learning/scripts/run_benchmark.py --mode adaptive --limit 1

# 5) 报告（机器侧 KPI；盲评为人工字段，读 results/judgments.jsonl）
uv run python benchmarks/editorial-learning/scripts/report.py
```

## 诚实规则

- meaning-changed / Fact / Evidence / Claim 编辑**永不**入证据（事实漂移风险）。
- 只有可防御映射到 v0.1 冻结五动作的 intent 入证据；rationale 标映射置信度。
- WP_bench 仅当 rejected 触发某传感器而 chosen 不触发时入证据；T16（主观风格）
  永不产证据（sensor ≠ truth）。
- 盲评/人工编辑距离为空即未测，不伪造。

许可见 `provenance/licenses.md`；下载哈希见 `provenance/sources.jsonl`。
