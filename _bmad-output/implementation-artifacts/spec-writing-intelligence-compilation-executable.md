---
title: 'ZUAEF Writing Intelligence Compilation'
type: 'feature'
created: '2026-08-17'
status: 'approved'
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `zuaef-writing-learning-pack` 目前是人可读资料与 20 条技巧卡，尚未成为可检索、可验证、可按顺序接入 benchmark 的 ZUAEF 学习输入。若直接把原文送入 prompt，会丢失 provenance、混淆证据等级，并诱发表层句式模仿。

**Approach:** 先在仓库内建立显式、权威、可审计的 curated layer：

- `benchmarks/editorial-learning/curated/sources.jsonl`：声明 source 的稳定 id、pack 相对路径、URL、source 类型及 raw required/optional。
- `benchmarks/editorial-learning/curated/techniques.jsonl`：声明完整 technique 语义，不允许 compiler 从 Markdown 猜测。

然后新增离线 Pack Compiler。Compiler **只做**：输入校验、legacy candidate cross-check、exact join、hash、locator、canonical sort、serialization、transactional publish；**不做**语义推理、技巧抽取、LLM 调用或自动 promotion。

Compiler 读取外部 pack 的 `sanlian/*.md`、`research/*.md`、`raw/*.md`、`data/sources.jsonl`、`data/techniques.jsonl`，生成稳定 source nodes、统一 technique records、低权重 `corpus_observation` evidence，以及在提供现有 `benchmark.jsonl` 时生成 20-task sequential inputs。

本功能只生成文件资产；不修改 `EditorialControlCapability`、PydanticAI Agent Loop、writing toolset 或 plugin runtime。

## Boundaries & Constraints

### Always

- Compiler 不推理、不调用 LLM、不从 Markdown 反推语义字段。
- 最终 technique 语义只来自仓库内 `curated/techniques.jsonl`。
- 外部 pack 的 `data/techniques.jsonl` 仅作为 legacy candidate integrity input；只做 `id` / `name` / `source` / `maps_to` 一致性校验。
- 外部 pack 的 `data/sources.jsonl` 仅作为 source provenance integrity input；至少 exact cross-check `id` 与 `url`。
- 所有输出路径必须是 pack-relative 或 repo-relative；不得写入绝对 `/home/...` 路径。
- 所有 source node 必须保留：stable id、URL、source type、curated/raw 相对路径、SHA-256、locator/raw requirement。
- 所有 technique 必须保留完整 schema：`id`、`name`、`condition`、`action`、`instruction`、`preserve`、`anti_pattern`、`domain`、`sources`、`primary_source`、`confidence`、`activation`、`rationale`。
- `action` **始终**只能是现有五个 cognitive actions 之一；所谓 context-only 只由 `activation.mode="context"` 表示，不允许用伪 action 表示。
- Corpus evidence 固定：`source_type="corpus_observation"`、`weight=0.75`、`approved_by="pack-curation:v0.1"`。
- Corpus evidence 绝不自动提升为 `human_patch`。
- Compiled output 不含 raw/full article body、目标句式样本或自动生成的仿写文本。
- JSON/JSONL 输出使用 UTF-8、LF、sorted keys、compact separators、固定末尾换行；不得包含运行时间戳、随机 id、absolute path。
- 输入错误必须给出具体文件与 1-based 行号（能定位到 JSONL 行时）。
- `raw` 作为外部/ignored 数据宿主，不进入 git；仓库只提交 curated layer、compiled 小型机器资产、scripts、tests、README。

### Frozen allowed cognitive actions

仅允许：

1. `return_to_observation`
2. `delay_interpretation`
3. `shift_perspective`
4. `retrieve_concrete_memory`
5. `break_trajectory`

Compiler 不得新增、第六种 action 或 alias。

### Frozen allowed trigger signals

仅允许：

1. `template_connectors`
2. `summary_pressure`
3. `uniform_paragraphs`
4. `low_concrete_anchor_density`
5. `abstract_noun_density`

`activation.trigger_signals` 中出现其他值必须失败。Context signals 不受这五项限制，但必须是 curated record 中显式声明的非空字符串。

### Ask First

仅在以下情况停止并请求人确认：

- 已冻结的 curated input schema 必须改变；
- source 无法通过 stable id 唯一定位；
- 需要修改 writing plugin runtime/schema；
- 现有 `benchmark.jsonl` 缺失本 SPEC 依赖的 canonical `source` / `task_id` / `sequence` 字段。

正常实现细节、临时 fixture、staging 目录名、测试 helper 不需再次确认。

### Never

- 不把 ZIP/原文全文塞进 prompt。
- 不从文章复制目标句式来制造“技巧样本”。
- 不让 compiler 做语义总结或 technique discovery。
- 不提升 `corpus_observation` 为高权重经验。
- 不绕过 `scripts/promote_patch.py` 的严格 sequential promotion。
- 不修改 `plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py`。
- 不生成虚假的 benchmark output、blind judgment、human judgment、promotion receipt。
- 不把 `compiled/evidence.jsonl` 写入默认的 `~/.config/zuaef/editorial/evidence.jsonl`；benchmark runner 是否加载它由现有 benchmark 模式显式决定。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | 完整 pack + curated layer + 现有 `benchmark.jsonl` | 固定五文件；14 sources / 20 techniques / 20 evidence / 20 sequential inputs | N/A |
| PACK_ONLY | 完整 pack + curated layer，不给 benchmark | 生成 `sources.jsonl`、`techniques.jsonl`、`evidence.jsonl`、`manifest.json`；不创建 `sequential_inputs.jsonl` | manifest 标明 `benchmark_provided=false` |
| MISSING_SOURCE | technique 引用不存在 source，或 curated source 文件缺失 | 不发布新 output | 非零退出，指出 curated 文件/行 |
| REQUIRED_RAW_MISSING | `raw_required=true` 且 raw 不存在 | 不发布新 output | 非零退出 |
| OPTIONAL_RAW | `raw_required=false` 且 raw 不存在 | `raw_path=null`、`raw_sha256=null`、`raw_locator=null` | 成功，不伪造 hash |
| INVALID_ACTION | action 不在冻结五动作 | 不发布新 output | 非零退出 |
| INVALID_TRIGGER_SIGNAL | trigger signal 不在冻结五 sensor | 不发布新 output | 非零退出 |
| INVALID_ACTIVATION | mode 与 signal 组合不合法 | 不发布新 output | 非零退出 |
| MALFORMED_JSONL | 任一输入 JSONL 解析失败或缺 required field | 不发布新 output | 非零退出，指出文件+行号 |
| LEGACY_MISMATCH | curated technique 与 pack legacy candidate 的 `id/name/source/maps_to` 不一致 | 不发布新 output | 非零退出，列出字段差异 |
| BAD_BENCHMARK_JOIN | benchmark 缺 `source` 或 source 无 exact match | sources/techniques/evidence 可在 staging 生成，但整个命令不得发布目标目录 | 非零退出，禁止 fuzzy match |
| EXISTING_TARGET | 已有 compiled target | 完整 staging 校验后 transactional publish；成功才替换旧 target | 任一步失败恢复/保留旧 target |

</frozen-after-approval>

## Code Map

- `benchmarks/editorial-learning/curated/sources.jsonl`
  - 14 个 source 的权威 path/provenance manifest。
- `benchmarks/editorial-learning/curated/techniques.jsonl`
  - T001–T020 的权威 semantic layer。
- `benchmarks/editorial-learning/scripts/compile_learning_pack.py`
  - 离线 deterministic compiler；不调用 Agent/LLM。
- `benchmarks/editorial-learning/benchmark.jsonl`
  - 现有 20-task benchmark；sequential input 的唯一 task authority。
- `benchmarks/editorial-learning/scripts/promote_patch.py`
  - 现有 strict sequential promotion authority；compiler 不修改、不调用它完成自动 promotion。
- `benchmarks/editorial-learning/evidence/human_patches.jsonl`
  - 高权重人工 patch authority；compiler 不写。
- `benchmarks/editorial-learning/compiled/`
  - 固定 ABI 输出目录。
- `plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py`
  - 只读兼容边界：`EditorialEvidence`、`EditorialEvidenceStore`、五 cognitive actions、五 cheap sensors；禁止修改。
- `src/zuaef_agent/knowledge_store.py`
  - 只参考 file-native/atomic-write 方向，不接入 runtime。
- 外部 `zuaef-writing-learning-pack`
  - `sanlian/*.md`、`research/*.md`：curated 学习笔记。
  - `raw/*.md`：raw 快照；只 hash/locator，不写入 compiled body。
  - `data/sources.jsonl`：legacy source provenance cross-check。
  - `data/techniques.jsonl`：legacy technique candidate cross-check。
- `tests/test_editorial_benchmark.py`
  - 既有 benchmark contract。
- `tests/test_learning_pack_compiler.py`
  - 新增 compiler contract。

## Frozen Input Schemas

### 1. `curated/sources.jsonl`

每行必须是一个 object，required fields：

```json
{
  "id": "sanlian-189000",
  "source_type": "copyrighted-study-note",
  "url": "https://...",
  "curated_path": "sanlian/04-yuan-yue-writing-method.md",
  "raw_path": "raw/sanlian-189000.md",
  "raw_required": true
}
```

约束：

- `id`：非空、全局唯一。
- `source_type`：非空字符串；compiler 不解释含义。
- `url`：非空字符串，并与 pack `data/sources.jsonl` 同 id 的 URL exact match。
- `curated_path`：必须是 pack-relative，不能含 `..`，必须存在。
- `raw_path`：
  - `raw_required=true`：必须是 pack-relative 且存在。
  - `raw_required=false`：可为 `null`；若给出路径但文件不存在，compiled 时规范化为 `null`。
- `raw_required`：boolean。
- 14 条 v0.1 source 均由 curated file 显式声明；不要让 compiler 根据 source_type 猜 raw requirement。

### 2. `curated/techniques.jsonl`

每行 required fields：

```json
{
  "id": "T001",
  "name": "return_to_observation",
  "condition": ["..."],
  "action": "return_to_observation",
  "instruction": "...",
  "preserve": ["claims", "source_ledger"],
  "anti_pattern": ["fabricate_scene"],
  "domain": ["nonfiction"],
  "sources": ["sanlian-172807", "sanlian-135464"],
  "primary_source": "sanlian-172807",
  "confidence": {
    "level": "medium",
    "basis": ["curated_methodology"]
  },
  "activation": {
    "mode": "hybrid",
    "trigger_signals": ["abstract_noun_density"],
    "context_signals": ["material_observed"],
    "situation_tags": ["drafting", "nonfiction"]
  },
  "rationale": "..."
}
```

约束：

- `id`：恰好 T001–T020，一次且仅一次。
- `name`：非空。
- `condition`：非空 string array。
- `action`：冻结五动作之一。
- `instruction`：非空；必须是动作说明，不是目标成稿句式。
- `preserve`：string array，可为空但字段必须存在。
- `anti_pattern`：string array，可为空但字段必须存在。
- `domain`：非空 string array。
- `sources`：非空 source-id array；每项必须存在于 curated sources。
- `primary_source`：必须是 `sources` 成员。
- `confidence.level`：`low | medium | high`。
- `confidence.basis`：非空 string array；由 curator 声明，compiler 不推断。
- `activation.mode`：`sensor | context | hybrid`。
- `activation.trigger_signals`：
  - `sensor`：非空；
  - `context`：必须为空；
  - `hybrid`：非空。
  - 所有值必须属于冻结五 sensors。
- `activation.context_signals`：
  - `sensor`：可为空；
  - `context`：非空；
  - `hybrid`：非空。
- `activation.situation_tags`：string array，可为空但字段必须存在。
- `rationale`：非空。
- v0.1 不支持 actionless technique；context-only 指 `activation.mode=context`，不是第六种 action。

### 3. Legacy candidate cross-check

Pack `data/techniques.jsonl` 每条只作为 integrity reference。Compiler 必须按 `id` exact join，并检查：

- `legacy.id == curated.id`
- `legacy.name == curated.name`
- `sorted(legacy.source) == sorted(curated.sources)`
- `legacy.maps_to == curated.action`

不检查 `legacy.move` 是否与 curated `instruction` 文本相同；curation 允许把候选 move 正规化成更精确 instruction。

Pack `data/sources.jsonl` 必须按 `id` exact join，并检查：

- `legacy.id == curated.id`
- `legacy.url == curated.url`

## Frozen Compiled ABI

Compiled target 在有 benchmark 时恰好包含五个文件：

```text
compiled/
├── sources.jsonl
├── techniques.jsonl
├── evidence.jsonl
├── sequential_inputs.jsonl
└── manifest.json
```

PACK_ONLY 时不创建 `sequential_inputs.jsonl`，其余四个文件存在。

### 1. `sources.jsonl`

每条：

```json
{
  "id": "sanlian-189000",
  "node_id": "sources/sanlian-189000",
  "source_type": "copyrighted-study-note",
  "url": "https://...",
  "curated_path": "sanlian/04-yuan-yue-writing-method.md",
  "curated_sha256": "<64hex>",
  "curated_locator": {
    "line_start": 1,
    "line_end": 42
  },
  "raw_required": true,
  "raw_path": "raw/sanlian-189000.md",
  "raw_sha256": "<64hex>",
  "raw_locator": {
    "line_start": 1,
    "line_end": 380
  }
}
```

规则：

- locator 只表示文件可定位范围，不复制正文。
- `line_end` 是文件按 UTF-8 解码、`splitlines()` 后的行数；空文件非法。
- optional raw 缺失时 `raw_path/raw_sha256/raw_locator` 均为 `null`。
- 按 `id` 排序。

### 2. `techniques.jsonl`

每条是 curated technique 的 canonical copy，字段与语义不改变，另加入：

```json
{
  "node_id": "techniques/T001"
}
```

规则：

- `sources`、`condition`、`preserve`、`anti_pattern`、`domain`、`confidence.basis`、`activation.trigger_signals`、`activation.context_signals`、`activation.situation_tags` 均按 UTF-8 codepoint lexical sort。
- `primary_source` 显式保存，因此 array sort 不改变 primary semantics。
- 按 `id` 排序。

### 3. `evidence.jsonl`

每个 technique 恰好产生一条 evidence；共 20 条。

必须可被真实 `EditorialEvidenceStore` 加载，ABI 固定为：

```json
{
  "id": "corpus.T001",
  "source_type": "corpus_observation",
  "source_ref": "pack:sanlian-172807#technique:T001",
  "situation_tags": ["drafting", "nonfiction"],
  "trigger_signals": ["abstract_noun_density"],
  "action": "return_to_observation",
  "directive": "...",
  "rationale": "...",
  "weight": 0.75,
  "approved_by": "pack-curation:v0.1",
  "before_excerpt": "",
  "after_excerpt": ""
}
```

映射：

- `id = "corpus." + technique.id`
- `source_ref = "pack:" + technique.primary_source + "#technique:" + technique.id`
- `situation_tags = activation.situation_tags`
- `trigger_signals = activation.trigger_signals`
- `action = technique.action`
- `directive = technique.instruction`
- `rationale = technique.rationale`
- 其余固定值如上。

注意：source 的文件/line locator 在 `sources.jsonl` 与 `techniques.jsonl` provenance 中保存；`EditorialEvidence.source_ref` 使用 stable logical ref，避免因 JSONL 物理行重排导致 evidence id 漂移。

按 `id` 排序。

### 4. `sequential_inputs.jsonl`

仅在提供 benchmark 时生成。每个 benchmark task 恰好一条：

```json
{
  "task_id": "T01",
  "sequence": 1,
  "source": "iterater",
  "candidate_technique_ids": ["T011", "T012"],
  "candidate_evidence_ids": ["corpus.T011", "corpus.T012"],
  "prior_task_ids": [],
  "benchmark_record_sha256": "<64hex>"
}
```

规则：

- 只允许 `benchmark.source == compiled_source.id` exact equality join。
- `candidate_technique_ids` = 所有 `technique.sources[]` 包含该 `source` 的 technique ids。
- `candidate_evidence_ids` = 对应 `corpus.<technique_id>`。
- 如果某个 benchmark source 找不到任何 candidate technique，命令失败；禁止静默生成空候选。
- `prior_task_ids` = 当前 sequence 之前的所有 task ids，严格按 sequence 顺序。
- `prior_task_ids` **只表示可成为历史的任务集合，不表示已 promotion**；真实可用 human patch 仍由 `promote_patch.py` / benchmark state 决定。
- `benchmark_record_sha256` = 对原始 benchmark JSON object 做同一 canonical JSON serialization 后计算 SHA-256；不依赖输入文件空格。
- 记录按 `(sequence, task_id)` 排序。
- sequence 必须严格为 1..20，task_id 必须恰好 T01..T20 且唯一。

### 5. `manifest.json`

固定 schema：

```json
{
  "schema_version": "1.0",
  "benchmark_provided": true,
  "counts": {
    "sources": 14,
    "techniques": 20,
    "evidence": 20,
    "sequential_inputs": 20
  },
  "files": {
    "sources.jsonl": {
      "sha256": "<64hex>",
      "records": 14
    },
    "techniques.jsonl": {
      "sha256": "<64hex>",
      "records": 20
    },
    "evidence.jsonl": {
      "sha256": "<64hex>",
      "records": 20
    },
    "sequential_inputs.jsonl": {
      "sha256": "<64hex>",
      "records": 20
    }
  },
  "inputs": {
    "curated_sources_sha256": "<64hex>",
    "curated_techniques_sha256": "<64hex>",
    "pack_sources_sha256": "<64hex>",
    "pack_techniques_sha256": "<64hex>",
    "benchmark_sha256": "<64hex-or-null>"
  }
}
```

PACK_ONLY：

- `benchmark_provided=false`
- `counts.sequential_inputs=0`
- `files` 中无 `sequential_inputs.jsonl`
- `inputs.benchmark_sha256=null`

Manifest 不记录自身 hash，避免循环。

## Canonical Serialization

所有 JSON object：

```python
json.dumps(
    obj,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

每个 JSONL record 后恰好一个 `\n`；文件使用 UTF-8，无 BOM。

Canonical ordering：

- sources / techniques / evidence：按 `id`
- sequential inputs：按 `(sequence, task_id)`
- 除 `prior_task_ids` 外，本 SPEC 声明的 string-array 字段均 lexical sort
- `prior_task_ids` 按 benchmark sequence 保持历史顺序
- manifest file map keys 由 JSON `sort_keys=True` 处理

## Transactional Publish

“失败不得污染现有 target”是硬要求；不要求依赖不可移植的“非空目录覆盖 rename”。

固定流程：

1. Validate all input files and all cross-checks in memory.
2. 在 `--out` 同一父目录创建唯一 staging directory。
3. Render 全部目标文件到 staging。
4. 重新读取 staging，验证：
   - JSON/JSONL schema；
   - record counts；
   - real `EditorialEvidenceStore` 可加载 evidence；
   - no absolute path / no raw body fields；
   - manifest hashes 与 staging raw bytes 一致。
5. Publish：
   - target 不存在：rename staging → target。
   - target 已存在：rename target → sibling backup；rename staging → target；若第二步失败立即 rollback backup → target；成功后删除 backup。
6. 任一失败：删除 staging；旧 target 必须仍可用。
7. 不在 compiled output 中保留 backup/staging marker。

## Tasks & Acceptance

### Execution

- [ ] `benchmarks/editorial-learning/curated/sources.jsonl`
  - 固定当前 v0.1 的 14 个 source。
  - 当前 14 条均 `raw_required=true`；未来 optional raw 必须逐条显式修改 curated record。
- [ ] `benchmarks/editorial-learning/curated/techniques.jsonl`
  - T001–T020。
  - 按 Frozen Input Schema 完整人工/Agent curation。
  - 不让 compiler 推断语义。
- [ ] `benchmarks/editorial-learning/scripts/compile_learning_pack.py`
  - 实现本 SPEC 全部验证、cross-check、ABI、serialization、transactional publish。
- [ ] `benchmarks/editorial-learning/compiled/`
  - 从真实 pack 编译 snapshot。
- [ ] `benchmarks/editorial-learning/README.md`
  - 记录 compile command、pack 外部数据边界、evidence 等级、sequential promotion 边界、PACK_ONLY 行为。
- [ ] `tests/test_learning_pack_compiler.py`
  - 临时最小 fixture + 真实 compiled snapshot contract。
- [ ] 仓库既有 manifest / integrity 资产
  - 按仓库现有流程重新生成/更新；不要发明第二套 manifest 系统。

### Acceptance Criteria

1. **Source authority**
   - 完整 pack + curated layer → 恰好 14 source nodes。
   - 所有 required raw 都有 real SHA-256。
   - compiled 无原始正文。
2. **Technique authority**
   - 恰好 T001–T020。
   - 所有 action 属于冻结五动作。
   - 所有 trigger signals 属于冻结五 sensors。
   - context mode 不伪造第六种 action。
3. **Legacy integrity**
   - Pack legacy `data/sources.jsonl` / `data/techniques.jsonl` 与 curated layer exact cross-check 成功。
   - mismatch 必须 fail loud。
4. **Evidence ABI**
   - 恰好 20 条。
   - 真实 `EditorialEvidenceStore` 可加载。
   - 全部 `source_type=corpus_observation`、`weight=0.75`、`approved_by=pack-curation:v0.1`。
   - 不出现 `human_patch`。
5. **Sequential integrity**
   - 恰好 T01→T20。
   - exact source join。
   - 每 task 至少一个 candidate technique/evidence。
   - `prior_task_ids` 不等价于 promoted patches，compiler 不做 promotion。
6. **Determinism**
   - 同一输入连续编译两次，五文件逐 byte 相同。
   - 无 timestamp / random id / absolute path。
7. **Failure safety**
   - missing source/raw、invalid action/sensor、legacy mismatch、bad benchmark join、malformed JSONL 全部非零退出。
   - 失败时既有 target 不被污染。
8. **Runtime boundary**
   - `plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py`
   - `plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py`
   - `plugins/zuaef-ace-writing/zuaef_ace_writing/plugin.py`
   在本 WO 中保持未修改。
9. **Repository regression**
   - 新 compiler tests + existing editorial benchmark tests 全过。
   - full repository tests 全过。
   - ruff clean。
   - repository integrity/BUILD_MANIFEST 按既有机制更新并通过。

## Required Tests

`tests/test_learning_pack_compiler.py` 至少覆盖：

1. happy path minimal fixture
2. PACK_ONLY
3. missing curated source
4. required raw missing
5. optional raw missing
6. malformed sources JSONL
7. malformed techniques JSONL
8. duplicate source id
9. duplicate technique id
10. missing T001–T020 member
11. invalid action
12. invalid trigger signal
13. invalid activation mode/signal combination
14. unknown technique source id
15. primary_source not in sources
16. legacy source URL mismatch
17. legacy technique name mismatch
18. legacy technique source mismatch
19. legacy technique maps_to mismatch
20. bad benchmark source join
21. benchmark sequence gap/duplicate
22. benchmark task id duplicate
23. benchmark source with zero candidate techniques
24. deterministic bytes across two runs
25. evidence loads through real `EditorialEvidenceStore`
26. no `human_patch` in compiled output
27. no absolute path in compiled output
28. no raw body/full_text/raw_text field in compiled output
29. failed compile preserves existing target
30. real compiled snapshot counts 14/20/20/20

不得出现 `or True`、无条件 skip、伪 xfail 作为通过手段。

## Verification

执行至少：

```bash
uv run pytest -q tests/test_learning_pack_compiler.py tests/test_editorial_benchmark.py
uv run pytest -q
uv run ruff check .
```

Compiler real-pack proof：

```bash
uv run python benchmarks/editorial-learning/scripts/compile_learning_pack.py \
  --pack <pack> \
  --curated-sources benchmarks/editorial-learning/curated/sources.jsonl \
  --curated-techniques benchmarks/editorial-learning/curated/techniques.jsonl \
  --benchmark benchmarks/editorial-learning/benchmark.jsonl \
  --out /tmp/zuaef-writing-compiled-a
```

再次对同一输入输出到第二目录：

```bash
uv run python benchmarks/editorial-learning/scripts/compile_learning_pack.py \
  --pack <pack> \
  --curated-sources benchmarks/editorial-learning/curated/sources.jsonl \
  --curated-techniques benchmarks/editorial-learning/curated/techniques.jsonl \
  --benchmark benchmarks/editorial-learning/benchmark.jsonl \
  --out /tmp/zuaef-writing-compiled-b

diff -ru /tmp/zuaef-writing-compiled-a /tmp/zuaef-writing-compiled-b
```

Expected：`diff` 无输出。

Runtime boundary check：

```bash
git diff --exit-code -- \
  plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py \
  plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py \
  plugins/zuaef-ace-writing/zuaef_ace_writing/plugin.py
```

Manual/integrity checks：

- compiled files 不含 `/home/`。
- compiled files 不含 raw article body。
- compiled evidence 无 `human_patch`。
- `approved_by` 全部为 `pack-curation:v0.1`。
- raw pack 目录未被 git track。
- repository BUILD_MANIFEST / integrity test 按现有仓库机制通过。

## Stop Condition

满足全部 Acceptance Criteria 后停止。

**不要在本 WO 中继续：**

- 修改 EditorialControl sensors/actions；
- 自动把 compiled evidence 写入 runtime user config；
- 跑或伪造 20-task human evaluation；
- 自动 promotion；
- fine-tune / LoRA；
- 新增 reviewer Agent；
- 扩展第六个 cognitive action；
- 增加新的长期 memory subsystem。

这些属于后续 WO。

## Spec Change Log

### 2026-08-17 · review_loop_iteration 1

- 将 compiler 与 Learning/Curation 彻底分层。
- 冻结 curated source/technique schemas。
- 冻结五 cognitive actions 与五 trigger signals。
- 消除 “context-only 作为第六种 action” 的 ABI 冲突；context-only 改由 activation mode 表达。
- 修正 evidence `source_ref`：使用 stable logical ref，不依赖 legacy JSONL 物理行号。
- 冻结 sources/techniques/evidence/sequential/manifest 五类 ABI。
- 冻结 exact benchmark join 与 sequential input schema。
- 冻结 canonical JSON serialization 和 deterministic byte contract。
- 将不可移植的“覆盖非空目录原子 rename”改为 failure-safe transactional publish + rollback。
- 增加 legacy candidate exact cross-check、30 项 required tests、full-repo regression、runtime-boundary check。
- 状态改为 `approved`：可直接交给 coding agent 执行。
