---
title: Machine & Soul Knowledge Base
type: sub-wiki-index
classification: HUM.PHILOSOPHY
created: 2026-05-25
status: active
account: 坐驰未来
author: 片言
slogan: 片言以通百意，坐驰以驭万景
---

# Machine & Soul Knowledge Base

> Eastern wisdom, Western thought, and the human question in the age of AI.

**这是生产容器，不是哲学资料馆。** 所有语料围绕一个目的：每天稳定生成微信公众
号文章和 X/Twitter 线程，主题是 AI 时代的人类精神与文明观察。

---

## Agent Routing（按任务导航）

### 我想生成一篇公众号文章（wechat-x-publish）
1. 从 `ai-age-themes/` 选一个主题
2. 读该主题页 → 它会指向具体的 `bridges/`、`concepts/`、`sources/`
3. 读相关 bridge 页 → 获取东西方对话视角
4. 读相关 source 页 → 提取可引用素材
5. 按 `../assets/wechat-template.md` 结构输出

### 我想选今天该写什么
→ 看 [[_manifest.yaml]] 的 `daily_topics` 循环列表
→ 或看 `ai-age-themes/` 索引

### 我想了解某个东方/西方思想怎么用于 AI 时代写作
→ 先去 `bridges/` 找对应的东西方桥接

### 我想查某个核心概念的定义和用法
→ 去 `concepts/`

### 我想了解某本原典可用于写作的素材
→ 去 `sources/east/` 或 `sources/west/`

### 我想写一篇面向老板的 AI 落地文章（非哲学类）
→ 去 `business-articles/` 
→ 读 `craft-lessons.md` 获取写作经验
→ 读 `examples/ai-saddle-runway.md` 看 8.5 分定稿范例

### 我想了解 Alan Watts 的正确用法
→ 读 `sources/_alan-watts-style-reference.md`
→ **Watts 是风格参考，不是全文语料**

### 我想补充新的原典素材
→ 在 `sources/` 对应目录下创建文件
→ 更新 `_manifest.yaml` 的 sources 列表
→ 在相关 concepts/bridges/themes 中建立引用

---

## 目录结构

```
knowledge/
├── _index.md                          ← 本文件：路由索引
├── _manifest.yaml                     ← 机器可读元数据
├── AGENTS.md                          ← Agent 使用指南
│
├── sources/                           ← 原典素材（按东西方分）
│   ├── _alan-watts-style-reference.md ← Watts 正确用法
│   ├── east/                          ← 东方 8 本
│   │   ├── laozi.md                   ← 道德经
│   │   ├── zhuangzi.md                ← 庄子
│   │   ├── huineng.md                 ← 六祖坛经
│   │   ├── wang-yangming.md           ← 传习录
│   │   ├── su-dongpo.md               ← 苏东坡诗文选
│   │   ├── analects.md                ← 论语
│   │   ├── heart-diamond-sutra.md     ← 心经 / 金刚经
│   │   └── art-of-war.md              ← 孙子兵法
│   └── west/                          ← 西方 8 本
│       ├── marcus-aurelius.md         ← 沉思录
│       ├── epictetus.md               ← 手册
│       ├── montaigne.md               ← 随笔集
│       ├── hume.md                    ← 人类理解研究
│       ├── nietzsche.md               ← 快乐的科学 / 查拉图斯特拉
│       ├── william-james.md           ← 实用主义
│       ├── plato.md                   ← 苏格拉底的申辩 / 理想国
│       └── mill.md                    ← 论自由
│
├── concepts/                          ← 核心概念（可产出主题的原子单元）
│   ├── wu-wei.md                      ← 无为
│   ├── shi.md                         ← 势
│   ├── emptiness.md                   ← 空
│   ├── non-self.md                    ← 无我
│   ├── practical-wisdom.md            ← 实践智慧
│   ├── autonomy.md                    ← 自主
│   ├── meaning.md                     ← 意义
│   ├── attention.md                   ← 注意力
│   ├── control.md                     ← 控制
│   └── anxiety.md                     ← 焦虑
│
├── bridges/                           ← 东西方桥接（核心内容生成器）
│   ├── laozi-heidegger-control.md     ← 老子 × 海德格尔 × 控制
│   ├── zhuangzi-alan-watts-freedom.md ← 庄子 × Watts × 自由
│   ├── huineng-wittgenstein-clarity.md← 慧能 × 维特根斯坦 × 清明
│   ├── su-dongpo-montaigne-suffering.md← 苏东坡 × 蒙田 × 苦难
│   └── wang-yangming-william-james-action.md ← 王阳明 × James × 行动
│
├── ai-age-themes/                     ← AI 时代主题（日更 10 个方向）
│   ├── ai-and-control.md              ← AI 与控制
│   ├── ai-and-work.md                 ← AI 与工作
│   ├── ai-and-meaning.md              ← AI 与意义
│   ├── ai-and-attention.md            ← AI 与注意力
│   ├── ai-and-selfhood.md             ← AI 与自我
│   └── ai-and-civilisation.md         ← AI 与文明
│
├── characters/                        ← 英式气质补充人物
│   ├── shakespeare.md                 ← 莎士比亚
│   ├── william-blake.md               ← William Blake
│   ├── edmund-burke.md                ← Edmund Burke
│   ├── bertrand-russell.md            ← Bertrand Russell
│   └── wittgenstein.md                ← Wittgenstein
│
├── business-articles/                  ← AI 落地商业文章
│   ├── _index.md                      ← 路由索引
│   ├── craft-lessons.md               ← 写作经验与风格总结
│   └── examples/
│       └── ai-saddle-runway.md        ← 8.5 分定稿范例
│
└── x-posts/                           ← 内容产出目录
    ├── README.md                      ← 发布记录索引
    ├── drafts/                        ← 草稿
    └── published/                     ← 已发布
```

---

## 五个核心问题（决定一切内容方向）

本知识库不追求全，只围绕这五个问题组织：

1. **人如何面对技术控制欲？** → `ai-and-control` / `wu-wei` / `laozi-heidegger-control`
2. **人如何面对身份和工作被 AI 改写？** → `ai-and-work` / `ai-and-selfhood` / `zhuangzi-alan-watts-freedom`
3. **人如何在信息噪音中保持清明？** → `ai-and-attention` / `huineng-wittgenstein-clarity`
4. **人如何把认知转化为行动？** → `ai-and-work` / `practical-wisdom` / `wang-yangming-william-james-action`
5. **人如何在机器时代保留精神出处？** → `ai-and-meaning` / `ai-and-civilisation` / `su-dongpo-montaigne-suffering`

---

## 日更 10 主题循环

| # | 主题 | 核心桥接 | 产出节奏 |
|---|------|---------|---------|
| 1 | AI and control | 老子 × 海德格尔 × 技术控制欲 | 每 10 天一轮 |
| 2 | AI and identity | 庄子 × 尼采 × 职业身份焦虑 | 每 10 天一轮 |
| 3 | AI and attention | 慧能 × 维特根斯坦 × 信息噪音 | 每 10 天一轮 |
| 4 | AI and work | 王阳明 × William James × 知行合一 | 每 10 天一轮 |
| 5 | AI and suffering | 苏东坡 × 蒙田 × 苦难中的自由 | 每 10 天一轮 |
| 6 | AI and freedom | 庄子 × Mill × 个人自由 | 每 10 天一轮 |
| 7 | AI and judgement | 孙子兵法 × Aristotle × 实践智慧 | 每 10 天一轮 |
| 8 | AI and meaning | 帕斯卡 × 尼采 × 意义危机 | 每 10 天一轮 |
| 9 | AI and civilisation | Burke × 老子 × 现代性反思 | 每 10 天一轮 |
| 10 | AI and the soul | Plato × 慧能 × 人是否只是信息系统 | 每 10 天一轮 |

---

## 版权红线

- ✅ 公版原典（Project Gutenberg 确认）
- ✅ 自己的摘要和桥接分析
- ✅ Alan Watts 作为风格参考（不存全文）
- ❌ 现代译本全文
- ❌ Alan Watts 书籍/演讲稿全文
- ❌ SEP 整站抓取
- ❌ 当代哲学书全文
- ⚠️ Russell、Wittgenstein 逐本检查版权

---

## 关联资源

- Skill: `../SKILL.md` — wechat-x-publish 全平台发布引擎
- 模板: `../assets/wechat-template.md` — 公众号文章模板
- 模板: `../assets/x-thread-template.md` — X 线程模板
- 配图: `../references/image-guidelines.md` — 配图风格指南
