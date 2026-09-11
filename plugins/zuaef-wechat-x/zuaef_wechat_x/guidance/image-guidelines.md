# 公众号配图规范

配图不是文字的复读机。一篇文章的插图，是读者停下来喘口气的地方。

好的配图和好的文字一样，懂得到什么时候就不说了。

---

## 整体风格

参考"设计思维书籍式小人插画"——那种翻开一本 IDEO 或斯坦福 d.school 的书时看到的插图：清淡，不抢戏，但让人记住。

### 配色

| 元素 | 颜色值 | 存在感 |
|------|--------|--------|
| 背景 | 白 `#FFFFFF` 或暖白 `#FAFAF8` | 80% 的页面应该是空的 |
| 线条 | 黑 `#1A1A1A` | 手绘感，像用笔画出来的 |
| 主点缀 | 青绿 `#0EA5A0` | 箭头、高亮线、小元素的颜色 |
| 副点缀 | 珊瑚红 `#E86A5C` | 只用于"需要注意"的东西，不多 |

### 不能做的事

- PPT 风格。渐变背景、图标堆砌、大号数字标号 —— 这些让图看起来像一个汇报文档的截图。
- 信息图。每张图只说一句话，不要试图用一张图讲一个完整的数据故事。
- 科技感。电路板、芯片、全息投影 —— 这些东西不帮助理解。
- 章鱼形象。旧风格遗留，已弃用。
- 复杂背景。噪点、纹理、多色渐变 —— 留白比填满更难，也更值得。
- 3D 渲染。平面的就够了。
- 真实照片。照片和手绘插画混在一起，视觉语言是错乱的。
- 通用 AI 机器人、发光大脑、蓝色科技仪表盘、廉价创业 pitch deck 风格。
- 密集流程图、信息过载、商用素材图库感。
- 图中出现需要模型渲染的中文正文。中文 caption 由后期叠加，不要让图像模型生成。

### 必须做的事

- 白底或暖白底。让画面透气。
- 黑色手绘线条。看起来像是用粗笔在纸上画的。
- 青绿色做点缀，但不要多。
- 珊瑚红只用一次、两处，让它成为注意力焦点。
- 简笔画小人，2-4 个，在协作场景中。小人的表情不需要太精细，姿态就够了。
- 大量留白。一张图里的大部分面积不应该是内容，应该是空气。
- 手机竖屏友好。宽高比 3:4 或 9:16。

---

## 图片上的文字

每张图最多一句话。中文不超过 12 个字，英文不超过 8 个词。

文字放在下方或角落，不和画面主体抢视线。字体用简洁的无衬线体，不要太粗，也不要太花哨。

文字是图画的注脚。不是正文的摘要。不要把"本文核心观点"写在图上——正文里已经有了。

---

## 图片规格

| 类型 | 尺寸 | 出现位置 |
|------|------|---------|
| 封面 | 900×383 px (2.35:1) | 文章最前面 |
| 正文插图 | 1080×1440 px (3:4) | 正文段落之间 |
| 收尾海报 | 1080×1440 px (3:4) | 文章最后的品牌画面 |

---

## 12 张图的角色

| 编号 | 文件名 | 画面 | 配文 |
|------|--------|------|------|
| cover | cover.png | 文章标题的画面化——一个简练的视觉符号 | 无（封面不需要文字） |
| fig_01 | figure-01-{slug}.png | 从 A 到 B 的状态变化 | "从XX，走向XX" |
| fig_02 | figure-02-{slug}.png | 当前的位置——不是 A，不是 B，是 C | "能XX，但还不能XX" |
| fig_03 | figure-03-{slug}.png | 场景清单的画面呈现 | "最适合先做的事" |
| fig_04 | figure-04-{slug}.png | 困境的画面——散落、找不到、靠人猜 | "越散，越容易靠猜" |
| fig_05 | figure-05-{slug}.png | 第一个观察的画面 | "先找XX，再谈XX" |
| fig_06 | figure-06-{slug}.png | 第二个观察的画面 | "不是堆给XX，是整理给XX" |
| fig_07 | figure-07-{slug}.png | 第三个观察的画面 | "先做一个能跑通的XX" |
| fig_08 | figure-08-{slug}.png | 核心判断的画面总结 | "真正要准备的，是XX" |
| closing | closing-poster.png | 品牌标语 + 干净的画面收束 | 标语文字，不加其他 |

---

## 生产规范模板（v2：文章视觉论证生成器）

每张图不是插图，是**视觉论证**。它的任务是支撑文章的一个判断，不是装饰正文。

每张图必须输出以下 8 个字段：

```text
1. Purpose（用途）
   这张图在文章中承担什么论证角色？
   是开场锚点、困境画面、方法示意、还是结论收束？
   正面声明：这张图帮助读者理解什么？

2. Business meaning（业务判断）
   这张图要让读者（中小企业老板）明白的一个具体判断。
   用一句话说清，不用隐喻，不用"体现""展示"。
   例："没有权限边界和确认节点的 AI，能力越强风险越大"

3. Style（风格）
   暖白底(#FAFAF8)、黑色手绘线条、青绿(#0EA5A0)点缀、珊瑚红(#E86A5C)仅用于警告标记。
   设计思维笔记本插图风格，清爽透气，严肃但可亲近。

4. Composition（构图）
   竖图 3:4，一个清晰焦点，大量留白，2-4 个简笔小人（如需）。
   底部留 18% 空白区域供后期叠加中文 caption。
   图中不生成可读中文文字（除非明确要求）。

5. Scene（场景）
   画面中具体出现什么物件、什么动作。
   不只描述隐喻（如"马在跑道上"），还要描述业务物件（如"竞品网页、价格标签、客户评论气泡、关键词卡片"）。

6. Series consistency（系列一致性）
   同篇文章所有图保持：
   - 相同线宽
   - 相同马的造型（如有）
   - 相同青绿用量
   - 相同视觉密度
   - 相同底部留白区

7. Avoid（禁忌）
   通用 AI 机器人、发光大脑、蓝色科技仪表盘、PPT 幻灯片感、
   密集信息图、照片写实、3D 渲染、商用素材感、畸形的中文文字。

8. Text policy（文字策略）
   是否允许图中包含文字？
   默认：不允许。中文 caption 由后期叠加。
   例外：验收章、品牌标语等固定元素可以在图中。
```

## 给 AI 绘图工具的 prompt 模板

```text
Create an editorial hand-drawn business explainer illustration for a WeChat article.

Purpose:
{这张图的论证角色}

Style:
warm off-white background (#FAFAF8), rough black hand-drawn line art,
minimal teal accents (#0EA5A0), very small coral red highlights (#E86A5C) only for warning marks,
design-thinking notebook illustration style, clean and airy, serious but approachable.

Composition:
vertical 3:4, one clear focal point, generous whitespace, simple objects,
no more than 2-4 stick figures, leave the bottom 18% blank for Chinese caption overlay,
no readable text inside the image unless explicitly required.

Scene:
{具体场景——不只描述隐喻，要描述业务物件}

Business meaning:
{这张图要表达的商业判断——一句话}

Series consistency:
keep the same line weight, same horse shape if a horse appears,
same teal accent usage, same visual density as the rest of the article illustrations.

Avoid:
generic AI robot, glowing brain, blue tech dashboard, dense PPT slide,
crowded infographic, photo realism, 3D rendering, stock illustration feeling, malformed Chinese text.
--ar 3:4
```

**场景描述要具体**。写"两个人把散落的资料装进不同颜色文件夹"，不写"知识管理概念"。写"竞品网页截图、产品价格标签、客户评论气泡、关键词卡片排在一条手绘跑道上"，不写"数据变成报告"。
