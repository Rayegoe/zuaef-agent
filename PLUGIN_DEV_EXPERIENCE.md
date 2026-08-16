# ZUAEF Plugin 开发经验（Stage 5 → 6A 实录）

> 本文档是从 `ace-writing`（Stage 5，第一插件）与 `zuaef-emtb-budget`
> （Stage 6A，第二插件）两次真实构建中沉淀的经验。目标是让第三个插件
> 的构建从"摸索"变成"照单执行"。所有结论均来自真实运行与真实失败，
> 不是设计假设。

## 一句话

一个业务插件 = **一个独立 Python 发行版 + 一个 `zuaef.plugins` entry point
工厂 + 一个 profile**；核心三件（`core.py` / `runtime.py` / `composition.py`）
全程零改动，宿主负责 artifact 验证与 receipt 结算。

## 插件契约速览（composition.py 已实现，无需新机制）

```text
发行版 pyproject  [project.entry-points."zuaef.plugins"]
   zuaef-emtb-budget = "zuaef_emtb_budget:create_plugin"
        │
        ▼ 工厂
create_plugin(env: PluginEnv, config: dict) -> PluginBundle
   PluginEnv  = id/version/workspace_root/state_root（薄，无隐藏 DI）
   PluginBundle = toolsets + skill_dirs + capabilities（capabilities 需 profile 授权）
        │
        ▼ profile（<config_root>/profiles/<name>.toml, schema 1）
        │   安装插件 ≠ 启用；只在 profile 里命名才启用；config 只允许非 secret 键
        ▼
resolve_profile → CompositionSnapshot（composition_id = 规范化 JSON 的 SHA-256）
        │
        ▼
build_agent_from_snapshot（resume 的权威，忽略当前 profile，版本漂移即 pre-run 错误）
        │
        ▼
execute_run(..., composition=snapshot) → receipt.composition 可见
```

## 第三个插件照单执行（六个步骤）

1. **建发行版** `plugins/<domain>/`：`pyproject.toml`（name/version/deps/entry
   point）+ 包目录。entry point 名 = 你要在 `plugin list` 里看到的 id。
2. **写工厂**：`create_plugin(env, config) -> PluginBundle`，只返回 toolset
   （默认）；需要 capability 才在 profile 开 `allow_capabilities`。config 无
   可配项就直接忽略（域不该有 secret/endpoint 设置）。
3. **装进 venv**：`uv pip install -e plugins/<domain>`。**`plugin list` 只认
   真实安装的 entry point**，测试里的 hermetic discover 不能替代安装。
   `uv run --frozen` 不会卸载 pip 装的插件（实测）。
4. **写 profile**：`profiles/<name>.toml`，`schema = 1`，`name` 必须等于文件
   名，插件 config 键**绝不能长得像 secret**（api_key/password/token…）——
   profile 会序列化进 receipt。
5. **case 驱动**：`examples/<domain>_case.py` 加 `--profile` 路径
   （`build_profile_agent` → snapshot 进 receipt），保留无 profile 直连路径
   作 parity 基线（用**同一个** toolset，保证工具面逐一对等）。
6. **验收**：`plugin list` / `plugin inspect` / `profile check`（真实验证，
   无模型请求）→ 真实 run（completed + CompositionSnapshot present +
   artifact verified）→ 全量 pytest。约束：`git diff` 确认核心三件零改动。

## 真实踩坑清单（全部实测）

### 契约 / 流程坑

- **`plugin list` 前必须装**：只写发行版文件不 `pip install -e`，CLI 看不到。
- **manifest globs 要泛化**：`regen_manifest.py` 的 globs 从按插件列举改为
  `plugins/**/*.py` + `plugins/*.toml` + `plugins/**/*.csv`，否则新插件文件
  触发 `test_manifest_integrity` 失败（每次改文件后都要 regen）。
- **pytest pythonpath**：`import examples` 依赖仓库根在 sys.path。`from
  examples.x import ...` 在字母序先收集的测试模块里会炸
  （`test_ace_writing_plugin` < `test_budget_slice`）。修法：pyproject
  `pythonpath` 显式加插件目录 + `"."`（仓库根）。
- **并行工作目录**：`git add` 精确指定自己的文件，不要把别人的未提交
  目录（如并行会话的 `plugins/zuaef-client-service/`）卷进 commit。

### Python / PydanticAI 坑

- **`FunctionToolset.tools` 是 dict**（name → Tool 对象），不是 list；
  直接调用测试用 `toolset.tools[name].function(ctx, **args)`。
- **`from module import x` 值绑定**：测试想观察工厂写入的模块级状态
  （`last_env`）必须 `import module as m; m.last_env`——`from m import x`
  绑定的是 import 时刻的旧值（None），看不到更新。
- **模型没有 tool_call_id 可引用**：`RunSummary.evidence` 只教模型写
  `artifact:<path>`，**绝不写 `tool-effect:`**。模型会写
  `tool-effect:<工具名>`（它拿不到 call id）→ host 判不可验证 → degraded →
  `completed` 降级 `partial`。这不是 host 的 bug，是指令没教对。

### 保真搬移（从 zesenticai 拆资产）

- 搬确定性业务代码要**逐行保真** + docstring 注明 provenance（来源仓库、
  拆解日期）+ 单元测试把行为钉死。连"看似是 bug 的行为"也要保真：
  EMTB variance 对 `current_period_change` 求和（14300）而 summary 用
  end−start（14800），差 500 = 不一致科目的 gap——**这个差异被保留并写成
  测试断言**，因为它是有信息量的业务语义。
- 源仓库的防御性 catch（`except Exception`）原样保留，加 `noqa` 注明
  "保真搬移"，不要顺手"改进"。
- 双语列名别名表（中英 CSV 列头）是这类工具的隐藏价值，搬的时候别精简。

### 环境坑（真实运行前提）

- 本机 TUN 透明代理 + 系统 DNS SERVFAIL：`trust_env=False` 直连必挂
  （Connection error, usage=0）。`providers.py` 已修：只认 `HTTP(S)_PROXY`
  的 http(s) scheme，忽略 `socks://`（httpx 无 socksio 会直接 ValueError）。
  新插件若遇到同样报错，先查 `.env` 的 `LLM_API_BASE` 与代理连通性。

### 模型行为观察（非验收项，但影响报告质量）

- 模型会主动解释库输出之外的信息（如"期末合计受软件订阅 +500 不一致
  影响，修正后约 175,300"）——这是加分项，不要写进机器检查。
- 判断留给模型、品味留给人：库里只有确定性计算，健康度/一致性/显著
  变动是机器事实，是否合理由人裁决。

## 验收清单（Stage 6A 原样，第三个插件照抄）

```text
plugin list / inspect             PASS      （真实 CLI 可见 + 元数据正确）
profile check                     PASS      （factory 加载 + bundle 校验 + 无冲突）
real EMTB run                     completed （真实模型）
CompositionSnapshot               present   （receipt 内 plugins=[<id>]）
artifact verified                 PASS      （SHA-256 归属）
existing deterministic tests      PASS      （120 全过）
core.py / runtime.py / composition.py      unchanged（git diff 无输出）
```

## 边界（不做什么）

- 不新增平台机制：插件 = 现有原语（Toolset/Skill/Capability）的打包，
  `PluginBundle` 没有 hooks/middleware/events/services 字段，别想加。
- 不给 composition.py 加 domain branch：第二插件与第一插件走同一条无分支
  代码，这正是"泛化证明"的意义。
- 不把 ACE 之类外部引擎的逻辑复制进插件（`ace-writing` 只做 config wiring，
  域逻辑归引擎）。budget 插件同理：域逻辑全在 `budget_lib`，插件只是装配。
