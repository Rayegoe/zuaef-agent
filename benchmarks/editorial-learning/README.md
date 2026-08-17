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
curated/sources.jsonl + techniques.jsonl    （pack compiler 权威层，见下节）
compiled/{sources,techniques,evidence,
  sequential_inputs}.jsonl + manifest.json   （确定性重建的机器资产）
evidence/seed_snapshot.jsonl        由 fetch_sources.py 下载 / build_tasks.py 派生
evidence/human_patches.jsonl
provenance/sources.jsonl + licenses.md
benchmark.jsonl
results/{base,static,adaptive}/
scripts/
```

## Pack Compiler（offline — SPEC: writing-intelligence-compilation）

仓库提交 curated layer + compiled 机器资产；**外部学习 pack 是外部产物，不进入 git**。
Compiler 只做输入校验、legacy cross-check、exact join、hash、locator、canonical sort、
serialization、transactional publish；不推理、不调用 LLM、不自动 promotion。

### 权威层级（authority 顺序）

1. `curated/` — 仓库内权威层。`sources.jsonl`（14 个 source 的 path/provenance manifest）、
   `techniques.jsonl`（T001–T020 完整语义）。**compiler 不从 Markdown 反推语义字段**，
   technique 语义只来自这里。
2. 外部 pack（`zuaef-writing-learning-pack`）— `sanlian/*.md`、`research/*.md`（curated
   学习笔记）；`raw/*.md`（raw 快照，只 hash/locator，不写入 compiled body）；
   `data/sources.jsonl` / `data/techniques.jsonl`（legacy integrity cross-check 输入，
   `id/url` 与 `id/name/source/maps_to` 不一致必须 fail loud）。
3. `compiled/` — 固定 ABI 输出，由 1 + 2 + `benchmark.jsonl` 确定性重建。

### Compile command

```bash
uv run python benchmarks/editorial-learning/scripts/compile_learning_pack.py \
  --pack <外部 pack 路径> \
  --curated-sources benchmarks/editorial-learning/curated/sources.jsonl \
  --curated-techniques benchmarks/editorial-learning/curated/techniques.jsonl \
  --benchmark benchmarks/editorial-learning/benchmark.jsonl \
  --out benchmarks/editorial-learning/compiled
```

- 省略 `--benchmark` = **PACK_ONLY**：只产出 `sources.jsonl` / `techniques.jsonl` /
  `evidence.jsonl` / `manifest.json` 四文件，不创建 `sequential_inputs.jsonl`，
  manifest 标明 `benchmark_provided=false`。
- 确定性：同一输入两次编译逐 byte 相同（无 timestamp / random id / absolute path）；
  `test_real_pack_recompile_is_byte_identical` 用真实 pack 对已提交快照验证。
- 失败安全：任何校验失败非零退出，既有 compiled target 不被污染
  （staging → backup → rename → rollback）。

### Compiled ABI

五文件：`sources.jsonl`（14，SHA-256 + line locator）、`techniques.jsonl`（20，
canonical copy + `node_id`）、`evidence.jsonl`（20）、`sequential_inputs.jsonl`（20，
仅 benchmark 模式）、`manifest.json`（counts + 各文件 hash + 输入 hash）。

- Evidence 固定：`source_type=corpus_observation`、`weight=0.75`、
  `approved_by=pack-curation:v0.1`；**绝不自动提升为 `human_patch`**。
- compiled 不含 raw/full article body、不含目标句式样本。

### Raw / 数据边界（clone 后重建）

- 外部 pack 的 `raw/*.md` 是外部宿主，不进仓库、不进 compiled；compiled 只带 hash/locator。
- 仓库根 `data/`（四公开数据集 raw + derived）gitignored，clone 后重建：

  ```bash
  uv run python benchmarks/editorial-learning/scripts/fetch_sources.py   # 或 --reuse <既有 raw 树>
  uv run python benchmarks/editorial-learning/scripts/build_tasks.py
  ```

  committed 的 `tasks/T01..T20.json` 只带 bounded excerpts + sha256 + license/provenance。

### Sequential promotion 边界

- promotion 属于 benchmark flow（`scripts/promote_patch.py`，严格 T01→T20 顺序），
  **不是 compiler 的职责**；`sequential_inputs.jsonl` 的 `prior_task_ids` 只是
  "可能成为历史的任务集合"，不代表已 promotion。
- compiler 不写 `evidence/human_patches.jsonl`、不调用 `promote_patch.py`、
  不触碰 `~/.config/zuaef/editorial/evidence.jsonl`。

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
