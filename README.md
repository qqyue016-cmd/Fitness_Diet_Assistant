# 健身饮食助手 Fitness Diet Assistant

围绕「**每日营养目标 → 实际摄入 → 缺口反馈**」闭环的健身饮食管理工具。支持**一句话自然语言记录**（LLM 解析 + 确定性护栏校验）、**AI 对话助手**（查食物营养、算缺口、直接帮记、答营养原理并标注出处），也保留传统表单录入。

## 功能

- **个性化营养计划**：基于 Mifflin-St Jeor 公式计算 BMR / TDEE，按目标（增肌 / 减脂 / 维持）自动调整每日热量与三大营养素分配
- **自然语言记录**：一句话描述饮食 → LLM 解析为结构化数据 → 护栏做库内匹配与范围校验 → 分级结果经用户确认后写库
- **AI 对话助手**：支持多轮对话，流式输出；模型自主选择工具完成「查食物营养 / 查当日摄入与缺口 / 写入记录 / 撤销记录 / 检索营养知识」
- **营养知识问答（RAG）**：内置 9 篇中文营养学主题语料（35 个知识块），向量检索后基于材料作答，并在界面展示「参考资料」——文档、小节与原始出处
- **可复现评测**：30 题标注集（含 `gold_chunk` 与标准答案），检索层算 R@3 / R@1 / MRR，生成层用 LLM-as-judge 算 faithfulness / correctness，结果按时间戳落盘
- **手动记录**：按日期选择食物 + 克数，支持删除回退
- **缺口分析**：实时计算「已摄入 vs 目标」差值，正数为可摄入余量、负数为超出
- **食物库**：内置 104 条常见食物的营养数据（每 100g 的热量 / 蛋白质 / 脂肪 / 碳水）

## 技术栈

Python 3 · SQLite · Streamlit · PyYAML · pytest

**AI 部分**：LangChain / LangGraph（`create_agent` 工具编排）· `langchain-openai` 接入通义千问（阿里百炼 OpenAI 兼容模式，`qwen-plus`）

**RAG 部分**：Chroma（向量库，cosine）· 百炼 `text-embedding-v3`（1024 维）· 按 Markdown 标题的结构感知切分

## 项目架构

分层设计，依赖单向向下：

```
app.py / pages/*.py  (UI · Streamlit)
   │
   ├──────────────┬──────────────┐
   ▼              ▼              ▼
service.py       ai/            rag/   (知识检索层)
   │             │  工具调用      │
   ▼             ▼              ▼
db.py  ·  calc.py ─────────── Chroma（向量索引）
   │         │
   ▼         ▼
      config/ (YAML 配置)
```

**依赖方向的铁律**：`ai/` 可以依赖 `service` / `db` / `calc` / `rag`，**反向绝不成立**。这保证了「把 `ai/` 和 `rag/` 整个删掉，项目照样能跑」——确定性内核不感知 AI 的存在。

| 层 | 文件 | 职责 |
|---|---|---|
| UI | `app.py` / `pages/*.py` | 页面渲染、交互、会话状态（多页面：主页 + AI 助手） |
| AI | `ai/` | 自然语言解析、确定性护栏、工具编排、链路编排 |
| RAG | `rag/` | 语料切片、向量建库、检索与上下文拼装、出处解析 |
| 服务 | `service.py` | 组合数据与计算，输出结构化结果 |
| 数据 | `db.py` | SQLite 读写、日期规范化 |
| 计算 | `calc.py` | BMR / TDEE / 宏量分配 / 汇总 / 缺口（纯函数，无 I/O） |
| 配置 | `config/*.yaml` | 数据库路径、表名、营养系数、数据源路径 |
| 工具 | `utils/` | 配置加载、日志、路径解析 |

### `ai/` 模块组成

| 文件 | 职责 |
|---|---|
| `client.py` | LLM 客户端（`ChatOpenAI` 兼容模式，`qwen-plus`，`streaming=True`） |
| `parser.py` | 口语 → 结构化 JSON（LCEL 管道：Prompt → Model → JsonOutputParser） |
| `guard.py` | 确定性护栏：库内匹配（精确 → 模糊 → 歧义）+ 克数校验 |
| `pipeline.py` | 串联 `parser → guard`，对 UI 暴露单一入口 |
| `tools.py` | 7 个工具（5 只读 + 2 写）+ `UserCtx` 上下文（`ToolRuntime` 注入） |
| `agent.py` | `create_agent` 构建 + `chat_stream` 流式事件流（text / tool / tool_result，`tool_result` 带工具名） |

**工具清单**：

| 工具 | 参数 | 用途 |
|---|---|---|
| `search_foods_tool` | `keyword` | 名称不完整时模糊搜索 |
| `query_food_tool` | `name` | 名称确定时精确查询 |
| `today_report` | 无 | 今天的摄入与缺口（含明细 id） |
| `report_by_date` | `date` | 指定日期 |
| `search_knowledge` | `query` | 检索营养知识库，返回带编号与出处的段落 |
| `add_meal` | `food`, `grams` | 写入记录（内部复用护栏 + 幂等检查） |
| `delete_meal` | `record_id` | 撤销记录（id 必须来自查询结果） |

工具的分工原则：**数据类问题走数据库（SQL），知识类问题走向量库（RAG）**。prompt 中明确「用户自身的目标值、摄入量必须走数据工具，不得用知识库中的通用数值替代」——否则模型会拿语料里的 BMR 公式自己算，而不是查实际记录。

### `rag/` 模块组成

| 文件 | 职责 |
|---|---|
| `vector_store.py` | 读 CSV 语料 → 按 `##` 二级标题切分 → 建 Chroma 索引（`search` / `build` / `get_retriever`） |
| `rag_service.py` | `search` 检索 → `build_context` 拼装编号上下文 → `parse_sources` 反解析出处 → `search_nutrition_knowledge` 对 AI 层暴露 |

## 快速开始

```bash
pip install -r requirements.txt
python scripts/init_db.py          # 建表并导入食物数据
python -m rag.vector_store         # 建向量索引（35 个知识块）
streamlit run app.py
```

评测（需要 `DASHSCOPE_API_KEY`）：

```bash
python -m evals.retrieval_eval     # 只跑检索层，不消耗生成额度
python -m evals.run_eval           # 全量 30 题（检索 + 生成），结果落盘到 evals/results/
```

浏览器打开 `http://localhost:8501`。

> 使用自然语言记录功能，需配置环境变量 `DASHSCOPE_API_KEY`（阿里百炼）。未配置时手动记录与营养计划功能仍可正常使用。

## 目录结构

```
Fitness_Diet_Assistant/
├── app.py                  # Streamlit 应用入口（我的计划 / 今日记录）
├── pages/
│   └── 1_AI_Mode.py        # AI 对话助手（独立页面）
├── service.py              # 业务编排层
├── db.py                   # 数据访问层（SQLite）
├── calc.py                 # 计算层（纯函数）
├── ai/                     # AI 能力层
│   ├── client.py           # LLM 客户端
│   ├── parser.py           # 口语 → 结构化
│   ├── guard.py            # 确定性护栏
│   ├── pipeline.py         # parser → guard 编排
│   ├── tools.py            # 工具定义 + UserCtx 上下文
│   └── agent.py            # Agent 构建 + 流式事件流
├── rag/                    # 知识检索层
│   ├── vector_store.py     # 语料切分 + 向量建库 + 检索
│   └── rag_service.py      # 上下文拼装 + 出处解析
├── evals/                  # 评测（不参与运行时）
│   ├── dataset.py          # 加载评测集 + 标注校验
│   ├── retrieval_eval.py   # 检索层：R@1 / R@3 / MRR
│   ├── generation_eval.py  # 生成层：faithfulness / correctness 双 judge
│   ├── run_eval.py         # 两层串联、报告、落盘
│   └── results/            # 每次运行的明细 JSON（含 meta，可跨版本对比）
├── config/
│   ├── SQLite.yaml         # 数据库路径与表名
│   ├── calc.yaml           # 营养计算系数
│   ├── foods.yaml          # 食物数据源路径
│   ├── chroma.yaml         # 向量库参数（collection / k / 距离度量）
│   └── evals.yaml          # 评测集路径
├── utils/
│   ├── config_tool.py      # 配置加载
│   ├── path_tool.py        # 绝对路径解析
│   └── logger_tool.py      # 日志
├── scripts/
│   └── init_db.py          # 建表 + 导入食物数据
├── tests/                  # pytest 测试
├── data/
│   ├── foods.csv           # 食物营养数据（104 条）
│   ├── foods.db            # SQLite 数据库
│   ├── knowledge/          # 营养知识语料（9 篇 CSV）
│   ├── eval_data/          # 评测集（30 题，含 gold_chunk 与标准答案）
│   └── chroma/             # 向量索引（可由语料重建，不入版本库）
├── logs/                   # 运行日志
├── requirements.txt
├── requirements-dev.txt
└── DEVLOG.md               # 开发日志
```

## 测试

```bash
pip install -r requirements-dev.txt
pytest
```

共 **73 条用例**，覆盖六个层面：

- `test_calc.py`（24）：计算公式的正常值与边界值（如碳水的负值保护）
- `test_db.py`（22）：增删查、日期规范化、越界输入校验
- `test_service.py`（6）：服务层编排结果的结构与字段完整性
- `test_guard.py`（13）：护栏的分级匹配、边界输入、规范名替换
- `test_tools.py`（7）：Agent 工具的写入前置校验、幂等、删除与回显字段
- `test_rag_service.py`（1）：`build_context` 与 `parse_sources` 的契约往返一致性

护栏的测试经过**变异测试**验证：故意在实现中植入缺陷，确认对应用例会失败——确保测试本身是有效的，而非摆设。

## 评测

RAG 的效果不能靠「读起来还行」判断。项目内置双层评测：**检索层**衡量「该召回的资料有没有召回」，**生成层**衡量「回答是否被材料支持、是否与标准答案一致」。评测代码不参与运行时，删掉不影响应用。

### 评测集

`data/eval_data/eval_set_v1.json`，30 题，每题标注 `gold_chunk`（对应向量库中的知识块）与 `ground_truth`：

| 维度 | 分布 |
|---|---|
| 题型 | 事实型 11 · 误区判断型 7 · 应用型 6 · 换算型 2 · 对比型 2 · 机制型 2 |
| 难度 | easy 11 · medium 14 · hard 5 |

`check_dataset()` 在运行前做三项校验：必填字段、`id` 唯一、`gold_chunk` 必须真实存在于向量库。**标注错误的评测集比没有评测集更危险**——它会让指标看起来合理但毫无意义。

### 指标定义

| 层 | 指标 | 定义 |
|---|---|---|
| 检索 | Recall@3 | top-3 中包含 `gold_chunk` 的题目占比 |
| 检索 | Recall@1 | `gold_chunk` 排在首位的题目占比 |
| 检索 | MRR | 命中排名倒数的均值，未命中记 0 |
| 生成 | faithfulness | 回答中的事实性断言被检索材料支持的比例（≥ 0.9 记为忠实） |
| 生成 | correctness | 与 `ground_truth` 结论是否一致（LLM 判断并给出理由） |

两层分开测的原因：**召回成功不等于答对**。实测存在「忠实于检索材料、但与标准答案不一致」的样本，问题出在 top-3 里的干扰块，而不是没召回。

### 结果

检索层（30 题，k=3，2026-10-27 复测）：

| 指标 | 值 |
|---|---|
| Recall@3 | **96.7%**（29/30） |
| Recall@1 | 90.0%（27/30） |
| MRR | 0.9333 |

唯一未命中：id=6，`gold=02_s2`（减脂期宏量配比），实际召回 `09_s4` / `09_s1` / `02_s1`——同一主题被两篇文档覆盖导致的语义竞争，是后续 rerank / 查询改写的靶子。

生成层**暂不公布基线**：当前判分器存在缺陷（见「已知局限」第 4 条），两次运行的 faithfulness / correctness 为 0.97 / 0.80 与 0.93 / 0.73，组间差值已落在判分噪声量级，不足以判断改动是否有效。修复后重跑再填。**不公布未经验证的数字，比公布一个好看的数字更重要。**

### 复现

```bash
python -m evals.retrieval_eval     # 只跑检索层：30 次 embedding，不消耗生成额度
python -m evals.run_eval           # 全量：每题 1 次生成 + 2 次判分，约 3 分钟
python -m evals.run_eval 5         # 只跑前 5 题，调 prompt 时用
```

结果落到 `evals/results/eval_YYYYMMDD_HHMM.json`，`meta` 里记录模型、embedding、k、阈值——**数据不可比就等于没有数据**。

## 设计要点

1. **数据完整性由数据库约束保证**。营养字段加 `NOT NULL`，因此计算层不做缺失值兜底——约束失效时应让错误尽早暴露，而非静默处理。
2. **日期双端规范化**。写入用 `strftime` 严格输出 `YYYY-MM-DD`，读取时也用同一格式比对，保证 `WHERE date = ?` 的字符串全等比较可靠。
3. **主键按实体身份设计**。`foods` 以食物名为主键（同名食物只保留唯一来源版本）；`intake` 用自增 `id` 作为记录身份，与「日期 + 食物 + 克数」这组属性解耦。
4. **配置外置**。数据库路径、表名、营养系数全部写在 YAML 中，调整策略无需改动代码。
5. **模型只负责转录，代码负责校验**。prompt 中明确「不要判断数值是否合理，只按原话转录」，所有权值与存在性判断都交给 `guard.py`——模型没有数据源的访问权，指望它在 prompt 里"输出库里的名字"是不可能实现的。
6. **护栏输出分级结果**。`ok` / `ambiguous` / `not_found` / `invalid` 四级，把"这条能不能写库"翻译成用户可操作的四种决策，任何不确定的状态都**不静默写入**。
7. **写操作必须由动作触发**。Streamlit 的 rerun 模型下，任何副作用（写库、调 API）都不能放在渲染路径上，否则每次交互都会重放一遍。
8. **Agent 的写操作复用护栏，不裸调 DAO**。`add_meal` 内部依次判断「分配是否歧义 → 食物是否存在 → 克数是否合法 → 是否重复」，任一项不通过都返回说明字符串而非抛异常；`delete_meal` 的 `record_id` 必须来自查询结果，禁止模型编造。
9. **事实由代码提供，模型只做理解与调度**。当前日期、用户目标、库内食物都通过 `ToolRuntime.context` 或工具查询获得，不依赖模型记忆；prompt 只负责约束行为，不承担事实存储。
10. **切分策略取决于语料形状**。语料自带 `##` 二级标题时按结构切（35 块），不用按长度兜底切（会切出 79 块，其中 29 个碎片、15 处数字被切断，如 `1.6~2.2` 变成 `1.` + `6~2.2`）。`chunk_overlap` 是"怕切断"的补丁，结构切不需要。
11. **metadata 不参与 embedding**。想让标题影响检索，必须把 `【文档 > 小节】` 拼进 `page_content`；写进 metadata 只能用于展示与过滤。实测带前缀使首位命中率（R@1）从 86.7% 提升到 96.7%。
12. **RAG 上下文不进 system_prompt，而是作为工具返回值**。检索结果是动态材料，不是静态规则；塞进提示词会强制每轮携带、挤占对话空间，还会让模型混淆"必须遵守的约束"与"可引用的参考"。
13. **引用出处由系统附带，不依赖模型标注**。实测在 prompt 明确要求"标注 `[1]`"后，模型一次都没写——引用不是模型的自然行为。改为从工具返回值中反解析 `parse_sources`，UI 独立展示「参考资料」，确定性 100%。

## 已知局限

- **模型对极端数值存在"合理化"倾向**：如输入 `-50克` 时，模型可能输出 `50`。这类错误发生在理解阶段，输出本身合法，护栏无法检出。缓解手段是 prompt 约束（只转录不判断）；根本解法需引入原文数值对账，当前版本未实现。
- **食物名匹配只覆盖"库名包含输入"**：模型输出 `水煮鸡胸肉` 而库中为 `鸡胸肉` 时无法命中（反向包含未实现），会落入 `not_found` 由用户手动修正。
- **回答会混入知识库外的内容**：知识库覆盖的是"量"与"配比"，模型仍可能用自身背景补充机制解释（如 `CCK/GLP-1` 饱腹激素），这部分没有出处。它读起来合理，但无法用检索材料核实——属于「正确但无据」，比编造错误数字更难发现。
- **判分器会被 prompt 示例锚定**：`FAITHFULNESS_PROMPT` 的示例里写了一则具体的真实断言 `1g 脂肪 = 9 kcal（资料未提及能量密度）`。实测在长上下文下 judge 会把这句**原样抄进输出**：id=21 / id=30 的 top-3 明确包含 `9 kcal/g`、回答里却根本没有出现这个说法，仍被判为无据；把示例替换成与语料无关的中性占位后，同一份上下文与回答的判分从「抄示例」变为指出真实问题（`10% 属于过低脂肪摄入`）。**因此 `top_unsupported` 的聚合计数当前不能作为「语料缺口」的证据**——那可能是示例泄漏造成的伪信号。
- **`faithfulness` / `correctness` 是估计值，不是真值**：同一套配置两次运行，correctness 从 0.80 变为 0.73，2×2 矩阵的单个格子变动 4 题。任何小于该幅度的改动都不足以判定有效，需要多次运行取均值，并人工抽检 3~5 题核对。

## 版本

| 版本 | 状态 | 主要内容 |
|---|---|---|
| **V1** | 已完成 | 确定性内核：食物库 · 营养计算 · 摄入记录 · 缺口分析 · Streamlit |
| **V2** | 进行中 | 已完成：自然语言解析 · 确定性护栏 · 分级确认 UI · Tool Calling（7 个工具）· 流式多轮对话 · 对话式写库 · **营养知识 RAG（含引用溯源）** · **双层评测框架（检索 R@3 96.7%）** · 73 条单测<br>待做：修复判分器示例泄漏并重跑生成层基线 · Rerank（需先有稳定的对照数据） |
| V1.5 | 待开始 | FastAPI + Pydantic 校验 + MySQL + Redis + 认证 |
| V3 | 待开始 | 查询改写（口语 → 检索式表达）· 多步编排（LangGraph，跨工具的组合任务） |

设计思路：先用确定性代码把领域逻辑固化好，再让 LLM 承担调度层——比直接堆 prompt 更可控、可测试。

技术选型原则：**每引入一项技术（RAG / Rerank / 查询改写）都用对照实验量化收益，并且先确定指标能反映问题**。检索层 R@3 = 96.7%（29/30），35 个知识块的规模下已接近上限，单看 R@3 无法给 Rerank 留下空间；但「忠实于资料却答错」的样本说明**干扰块会误导模型**，而 R@3 只衡量「有没有召回」，不衡量「排得对不对」——所以 Rerank 的对照实验应看 `faithful_wrong` 的数量变化，而不是 R@3。该实验的前提是判分器先修复，否则测量的是噪声。
