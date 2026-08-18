# WCASE-2 — Multi-material Selection（多材料选择智能）

**目标**：8–10 份材料，其中 2–3 份核心、2–3 份次要、2–3 份无关、1 份冲突/存疑。
Host 不告诉模型哪些重要。评价：读了什么、没读什么、为什么、成稿用了什么、
有没有把无关材料硬写进去。核心证明：**Selection Intelligence**（SPEC §25 WCASE-2）。

## 任务契约

- article_id: `wcase-2-multi-material`
- assignment: 根据素材写一篇关于"山野品牌一支新露营灯产品"的公众号文章。
- audience: 露营爱好者
- constraints:
  - 约 1200–1600 字
  - 只使用素材里的事实；无关材料不得硬写进文章
  - 素材间冲突的数据不得同时当作确定事实呈现

## 材料（raw/，共 9 份）

| 文件 | 类型 |
| --- | --- |
| `interview-founder.md` | 核心：创始人采访（产品诞生缘由、人物、引语） |
| `product-spec.md` | 核心：产品规格与参数 |
| `field-test-notes.md` | 核心：一次露营实测记录（场景、细节、评价） |
| `pricing-channels.md` | 次要：定价与渠道 |
| `brand-history.md` | 次要：品牌历史背景 |
| `office-lunch-menu.md` | 无关：公司附近餐厅菜单 |
| `staff-travel-log.md` | 无关：员工个人旅行日志 |
| `old-product-line.md` | 无关：另一条旧产品线说明（20 年前的煤油灯） |
| `conflicting-spec-draft.md` | 冲突：与 product-spec.md 数据冲突的早期规格草稿 |

## 评价（人评）

- 是否读了核心材料并用于成稿
- 是否把无关材料写进文章（禁止）
- 是否处理了冲突数据（不得把草稿数字当确定事实）
- 成稿质量（结构、场景、人物、语言）

## 反作弊（WRITE-3 / WRITE-8）

- Host 不得提供 selected material ids
- 材料中不存在的数字/引语/场景不得出现