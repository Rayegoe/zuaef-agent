# Machine & Soul KB — Agent Usage Guide

This file is read by AI agents when they enter this knowledge base.
It tells them: what this contains, when to use it, and how to generate content from it.

## What This Knowledge Base Contains

A structured content engine for producing Chinese-language articles (微信公众号)
and X/Twitter threads about the human condition in the age of AI, drawing on
Eastern wisdom and Western philosophy.

**This is NOT a passive archive. It is a content production machine.**

## When to Use This KB

Trigger conditions:
- wechat-x-publish skill is invoked with a topic matching any ai-age-theme
- wechat-x-publish skill is invoked for a business/strategy article for SME owners (→ use business-articles/)
- User asks to write about AI + human condition / philosophy / meaning
- User asks to write about AI adoption, AI tools, AI strategy for business owners
- User asks for content in the voice of 坐驰未来 / 片言
- Daily content generation from the 10-theme rotation

## Context Injection Strategy

When primed for content generation, inject in this order:

### Level 0: Business Article Detection (check first)
If the topic is AI adoption, AI tools, AI strategy for SME owners:
Read `business-articles/_index.md` first.
Read `business-articles/craft-lessons.md` for writing patterns.
Read `business-articles/examples/ai-saddle-runway.md` for the standard.
Then proceed to Level 5 (Template) only.
Skip Levels 1-4 (they are for philosophy content).

### Level 1: Manifest (always first)
Read `_index.md` — the 5 core questions and 10 daily topics.
This determines WHAT to write.

### Level 2: Theme Page
Read the specific `ai-age-themes/ai-and-{topic}.md` — it contains:
- The core tension (东西方张力)
- Which sources/bridges/concepts to pull from
- Key angles and hooks
- What NOT to do for this topic

### Level 3: Bridge + Concepts + Sources
Read the bridge page referenced by the theme page.
Then read the specific concept pages.
Then read specific source pages for quotable material.

### Level 4: Style Calibration
Read `sources/_alan-watts-style-reference.md` for tone calibration.
Read the 坐驰未来 brand parameters from `_index.md` frontmatter.

### Level 5: Template
Read `../assets/wechat-template.md` for article structure.
Read `../assets/x-thread-template.md` for thread structure.

## File Structure (for agents)

```
knowledge/
├── _index.md              ← START HERE: routing + 5 core questions + 10 daily topics
├── _manifest.yaml          ← Machine-readable full registry
├── AGENTS.md               ← This file
│
├── sources/                ← Original text sources (scaffolded, fill-in-progress)
│   ├── _alan-watts-style-reference.md  ← How to use Watts (CRITICAL)
│   ├── east/ (8 files)
│   └── west/ (8 files)
│
├── concepts/               ← Atomic concepts serve as writing primitives
│   Each concept: definition, source mapping, AI-age usage hooks
│
├── bridges/                ← THE CORE: East-West pairings produce content
│   Each bridge: two traditions, one tension, 3-5 writing angles
│
├── ai-age-themes/          ← Daily topic templates
│   Each theme: points to bridges + concepts + sources
│
├── characters/             ← Supplementary figures for British-observer voice
│
└── x-posts/                ← Output
    ├── README.md
    ├── drafts/
    └── published/
```

## Content Generation Workflow

```
1. Pick topic from _index.md daily_topics rotation
2. Read ai-age-themes/{topic}.md → get bridge+concept references
3. Read bridges/{bridge}.md → get East-West tension
4. Read concepts/{concept}.md → get writing primitives
5. Read sources/{east|west}/{source}.md → get quotable depth
6. Generate article following ../assets/wechat-template.md
7. Generate X thread following ../assets/x-thread-template.md
8. Save drafts to x-posts/drafts/ with date slug
9. After publishing, move to x-posts/published/
```

## Brand Parameters

- Account: 坐驰未来
- Author: 片言
- Slogan: 片言以通百意，坐驰以驭万景
- Target reader: 中小企业老板 / 业务负责人
- Voice: 面向老板，讲业务结果，用短句，强节奏，有现实判断
- Style reference: Alan Watts (bridging East-West for Western audience, but in Chinese context)
- Observer stance: 英式怀疑 + 东方智慧 + 不做玄学

## Content Rules

### Do:
- Start with a real question a business owner would ask
- Give a clear judgment in the first 3 paragraphs
- Use East-West pairing (one concept from each tradition per article)
- Keep each paragraph under 100 characters
- End with brand POV + call to action
- Output 1500-3000 characters for WeChat

### Don't:
- Academic definitions as opening
- Mystical/occult framing
- AI news aggregation
- Pure philosophy without AI-age hook
- Expose system internals to readers
- Use markdown in WeChat body (no `**`, `*`, `![alt]()`)

## Copyright Enforcement

Agents MUST check copyright status before using any source material beyond
public domain texts and own summaries. The `_manifest.yaml` copyright_policy
section is authoritative.

Flagged for per-source check:
- Russell: check copyright per source
- Wittgenstein: check copyright per source
- Any modern translation: check copyright per source
