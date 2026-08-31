# 多轮对话测试集说明（dialogue_test_cases.json）

本文档说明 `data/dialogue_test_cases.json` 是什么、每个字段什么意思、评测时怎么用，以及如何做人工标注。

**相关文件**

| 文件 | 说明 |
|------|------|
| `dialogue_test_cases.json` | **当前正式测试集**（66 套多轮对话，notebook E3/E5 默认读这个） |
| `dialogue_test_cases.v1.json` | 早期 10 套备份，**评测默认不用** |
| `questions.csv` | 单轮 10 题（E4 用），多轮 legacy 十题可与之对照 |

---

## 1. 文件整体结构

`dialogue_test_cases.json` 最外层是一个对象，主要分四块：

```
{
  "version":        版本号（当前 "2.0"）
  "description":    一句话介绍这个文件是干什么的
  "generation":     生成时的统计数据（给人看，评测程序不读）
  "scenarios":      ★ 真正的测试用例列表（66 条）
}
```

### `generation` 里有什么？

记录当初扩成 66 套时的统计，例如：

- 一共多少套、其中 legacy 10 套 + 新生成 56 套
- 各对话模板（`classic_3` 等）各有多少套
- 评分策略说明：**有 `relevant_mp_ids` 就用固定标准算分，没有就让 LLM 临时判断**

**改测试内容时一般不用动 `generation`。**

### 一套测试 = 一个 scenario

`scenarios` 数组里每一项就是 **一套完整的多轮对话考题**。

系统会按顺序执行 Turn1 → Turn2 → Turn3…，状态和检索结果在轮次之间传递（Stateful 模式）。

**重要**：JSON 里的标注是 **考完试对答案用的标准**，不会在检索时自动塞进系统（例如系统检索时 **不会** 读取 `relevant_mp_ids` 去帮忙找路径）。

---

## 2. `scenarios` 下各字段说明

### 2.1 场景级字段（scenario 根上）

| 字段 | 是否必填 | 评测会不会用 | 通俗说明 |
|------|----------|--------------|----------|
| `name` | 必填 | 会 | 这套题的名字，要唯一。`q01_`…`q10_` 开头的是 legacy 十题 |
| `archetype` | 建议填 | **不会** | 对话套路模板，决定有几轮、每轮期望的 κ/l 序列（见下表） |
| `expected_modules_turn1` | 必填 | 只记录 | Turn1 期望去哪些顶层模块检索：`MPU` / `EEM` / `EBM`（可多选） |
| `turns` | 必填 | 会 | 每一轮的用户提问和标注，数组 |
| `source_no` | 可选 | **不会** | 对应 `questions.csv` 第几题，方便和旧版对照 |
| `topic_en` | 可选 | **不会** | 英文主题（`gen_*` 场景常见） |
| `researcher_notes` | 可选 | **不会** | 备注，给自己看的 |

#### `archetype` 五种模板（改 κ/l 时要对上）

| archetype | 几轮 | 每轮期望的 κ / l |
|-----------|------|------------------|
| `classic_3` | 3 | 概览 → 下钻细节 → 再收拢概览 |
| | | first_turn/mid → drill_down/low → roll_up/mid |
| `sibling_3` | 3 | 概览 → 换相关模块 → 收拢 |
| | | first_turn/mid → sibling_nav/mid → roll_up/mid |
| `drill_across_3` | 3 | 概览 → 跨模块下钻 → 收拢 |
| | | first_turn/mid → drill_across/low → roll_up/mid |
| `two_turn_drill` | 2 | 概览 → 下钻 |
| | | first_turn/mid → drill_down/low |
| `four_turn_mix` | 4 | 概览 → 下钻 → 换模块 → 收拢 |

**κ（expected_kappa）五种取值**

| 值 | 大白话 |
|----|--------|
| `first_turn` | 首轮：没有上一轮结果，不建结构子图 G_sub |
| `drill_down` | 在同一主题里往下看更细的路径 |
| `roll_up` | 从细节回到更概括的中层 |
| `sibling_nav` | 不换深浅，换到相关另一个模块/视角 |
| `drill_across` | 先上卷再换模块再下钻到细节 |

**l（expected_l）两种取值**

| 值 | 大白话 |
|----|--------|
| `mid` | 中层 / 概览类路径（如 `MPU_MID_xxxxx`） |
| `low` | 低层 / 细节类路径（如 `MPU_001153`） |

---

### 2.2 每一轮 `turns[]` 里的字段

| 字段 | 是否必填 | 评测会不会用 | 通俗说明 |
|------|----------|--------------|----------|
| `query` | 必填 | **会** | 这一轮用户真正问的问题，**系统就用这个去检索和回答** |
| `expected_kappa` | 必填 | **会** | 这一轮 **应该** 判成哪种导航方式；用来算 κ 命中率 |
| `expected_l` | 必填 | **会** | 这一轮 **应该** 用 mid 还是 low；用来算 l 命中率 |
| `expected_modules` | 可选 | 只记录 | 这一轮期望检索哪些模块；不写则 Turn1 用 `expected_modules_turn1` |
| `relevant_mp_ids` | 强烈建议 | **会** | **标准答案路径列表**：Top-10 里应该出现哪些 `mp_id`；用来算 Recall@10 / Precision@10 |
| `relevance_criteria` | 可选 | **不会** | 用文字写清「怎样算相关」——**给标注员自己看**，程序打分时不读 |
| `qrels_source` | 可选 | **不会** | 记录 `relevant_mp_ids` 是怎么来的（机器还是人工） |
| `intent_note` | 可选 | **不会** | 这一轮用户意图的一句话备注 |

#### 三个容易混的字段，分开记

| 字段 | 一句话 |
|------|--------|
| `relevance_criteria` | 给人看的「评分 rubric」，程序不用 |
| `relevant_mp_ids` | 给程序用的「标准路径 id 列表」，**最重要** |
| `qrels_source` | 备注这批 id 是机器凑的还是人手标的 |

`qrels_source` 常见值：

- `neo4j_hybrid_judge`：检索一批候选，LLM 挑相关的
- `neo4j_hybrid_top_score_fallback`：挑不够，**直接用检索分数最高的几条凑数**（质量往往一般，建议人工复查）
- `manual`：人工标注（自己改完后可写上）

---

## 3. 实例备注：q01 一套对话

下面用文件里第一条 `q01_mercury_methylation_factors` 举例（汞甲基化影响因素，经典 3 轮）。

```
场景名：q01_mercury_methylation_factors
套路：classic_3（概览 → 下钻 → 收拢）
Turn1 期望模块：MPU + EEM
来源题号：questions.csv 第 1 题（source_no: 1）
```

### Turn 1 — 首轮概览

| 项目 | 内容 |
|------|------|
| 用户问 | 水稻田里，哪些生物地球化学/微生物因素控制 Hg 甲基化？氧化还原怎么调节？ |
| expected_kappa | `first_turn` → 首轮，不建 G_sub |
| expected_l | `mid` → 期望中层路径 |
| relevant_mp_ids | 一串 `MPU_MID_xxxxx` → 标准答案应是 **中层** MetaPath |
| qrels_source | `top_score_fallback` → **机器凑的**，建议人工核对 |

`relevance_criteria` 大意：必须谈至少两个驱动因素，且场景是水稻田，不能泛泛而谈。

### Turn 2 — 下钻要实验证据

| 项目 | 内容 |
|------|------|
| 用户问 | 针对每个驱动因素，要有微宇宙/野外核心的实验证据（同位素、hgcAB、地球化学同步测定…） |
| expected_kappa | `drill_down` → 相对 Turn1 **往下看细节** |
| expected_l | `low` → 期望低层路径 |
| relevant_mp_ids | 一串 `MPU_xxxxxx`（无 MID）→ 标准答案应是 **细节层** 路径 |

### Turn 3 — 收拢成框架

| 项目 | 内容 |
|------|------|
| 用户问 | 把机制归纳成框架：水文管理（如干湿交替）如何影响甲基化潜势与籽粒风险 |
| expected_kappa | `roll_up` → **从细节回到概括** |
| expected_l | `mid` → 又回到中层 |
| relevant_mp_ids | 又是 `MPU_MID_xxxxx` |
| qrels_source | `neo4j_hybrid_judge` → LLM 参与挑过，仍建议抽查 |

### 跑完评测后比什么？

```
每一轮：
  系统实际输出的 kappa、path_level  →  对比 expected_kappa、expected_l
  系统 Top-10 里的 mp_id            →  对比 relevant_mp_ids（有几条撞上）
Turn2 额外：
  Turn1 的 Top-10 与 Turn2 Top-10 有多少重复  →  anchor_overlap
```

---

## 4. 人工标注：改哪些字段？步骤是什么？

### 4.1 建议优先标注的字段（按重要性）

| 优先级 | 字段 | 为什么 |
|--------|------|--------|
| ★★★ | `relevant_mp_ids` | 直接决定 Recall@10 / Precision@10 准不准；有它就用固定标准，没有每次跑分可能飘 |
| ★★☆ | `query` | 问法一变，系统检索和回答全变 |
| ★★☆ | `expected_kappa`、`expected_l` | 决定你怎么考「多轮导航对不对」 |
| ★☆☆ | `expected_modules_turn1`、`expected_modules` | 目前多轮评测**不单独给模块路由打分**，但有助于你自己设计题目 |
| ★☆☆ | `relevance_criteria` | 给自己看的说明，写清楚以后维护 qrels 更轻松 |
| ☆☆☆ | `qrels_source` | 改完 id 后标 `manual` 即可 |
| ☆☆☆ | `source_no`、`researcher_notes` | 档案备注，不影响分数 |

### 4.2 标注步骤（推荐流程）

**第 0 步：备份**

```
复制 dialogue_test_cases.json → dialogue_test_cases.backup.json
```

**第 1 步：定题目**

- 改或写 `query`（用户每轮真实会问的话）
- 确认 `archetype` 和每轮 `expected_kappa` / `expected_l` 对得上（见上文表格）
- 填 `expected_modules_turn1`（Turn1 该去 MPU/EEM/EBM 哪些）

**第 2 步：写清「怎样算相关」（可选但推荐）**

- 填 `relevance_criteria`（中文英文都行，给自己看）
- 例如：「必须提到硫酸盐还原菌 + 水稻田场景」

**第 3 步：找标准路径 id（核心）**

对每一轮的 `query`：

1. 在 Neo4j 里用 hybrid 检索或浏览图，找出 **真能回答这个问题** 的 MetaPath
2. 记下它们的 `mp_id`（Turn1/3 多为 `*_MID_*`，Turn2 下钻多为无 MID 的 low 路径）
3. 在 Neo4j 确认 id 存在，例如：
   ```cypher
   MATCH (mp:MetaPath {mp_id: 'MPU_MID_00083'}) RETURN mp.mp_id, mp.path_level
   ```
4. 把确认过的 id 写入该轮的 `relevant_mp_ids`（一般每轮 3～12 条）
5. 把 `qrels_source` 改成 `"manual"`

**第 4 步：小范围试跑**

在 notebook `3_0_2 Retevie.ipynb` 的 E3 cell，或命令行：

```bash
# 只跑 legacy 十题
python utilities/run_retrieval_eval.py --e3-only --test-set legacy10 --olap-modes core
```

看日志里：

- `kappa_ok` / `l_ok` 是否符合预期
- `retrieval_metric_source` 是否为 `qrels`（说明在用你标的 id 算分）

**第 5 步：再跑完整对比（可选）**

```bash
python utilities/run_retrieval_eval.py --olap-compare --test-set legacy10 --olap-modes core
```

### 4.3 常见注意点

1. **legacy 十题**：名字必须是 `q01_` … `q10_` 开头，评测选 `test_set=legacy10` 时正好 10 条。
2. **OLAP 模式 `core`**：只保留全程不含 `sibling_nav`、`drill_across` 的场景；含这两种 κ 的题会被整套过滤掉。
3. **不要乱改 archetype 却不改 κ/l**：例如 `classic_3` 第二轮必须是 `drill_down` + `low`。
4. **评测读的是 `dialogue_test_cases.json`**，不是 `dialogue_test_cases.v1.json`，除非你自己改代码传 `json_path`。
5. **`relevant_mp_ids` 为空或删掉**：Recall/Precision 会改成 LLM 临时判断，**不适合写进论文的稳定评测**。

---

## 5. 评测时怎么加载这个文件？

| 入口 | 默认文件 | 常用筛选 |
|------|----------|----------|
| Notebook E3 / E5 | `dialogue_test_cases.json` | `DIALOGUE_TEST_SET = "legacy10"` 或 `"all"` |
| `utilities/run_retrieval_eval.py` | 同上 | `--test-set legacy10` / `--test-set all` |
| 代码 | `load_dialogue_test_cases()` | 见 `utilities/test_evaluation.py` |

| test_set | 含义 |
|----------|------|
| `legacy10`（默认） | 只跑 q01–q10，共 10 套 |
| `all` | 跑 JSON 里全部 66 套 |
| `first` | 按文件顺序取前 N 套（需指定 `max_scenarios`） |

---

## 6. 一张图总结

```
dialogue_test_cases.json
│
├── version / description / generation   ← 说明与统计
│
└── scenarios[]                          ← 每一套多轮考题
      ├── name, archetype, expected_modules_turn1, source_no, …
      └── turns[]
            ├── query              → 系统真的用这个问
            ├── expected_kappa/l   → 考完对比导航对不对
            ├── relevant_mp_ids    → 考完对比检索到没（★人工最该改）
            ├── relevance_criteria → 给自己看的说明
            └── qrels_source       → 备注 id 谁标的
```

如有疑问，可先只改 **q01–q10** 的 `relevant_mp_ids` 练手，再扩到全量 66 套。
