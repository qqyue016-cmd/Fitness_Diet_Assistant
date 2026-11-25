# 健身饮食助手 Fitness Diet Assistant

围绕「**每日营养目标 → 实际摄入 → 缺口反馈**」闭环的健身饮食管理工具。支持**一句话自然语言记录**（LLM 解析 + 确定性护栏校验）、**AI 对话助手**（查营养、算缺口、直接帮记、答营养原理并标注出处），也保留传统表单录入。核心原则：**确定性计算全部交给代码，AI 只做意图理解、参数抽取与解释**。

## 功能

- **个性化营养计划**：Mifflin-St Jeor 公式算 BMR / TDEE，按目标（增肌 / 减脂 / 维持）调整每日热量与三大营养素分配
- **自然语言记录**：一句话描述饮食 → LLM 解析为结构化数据 → 护栏做库内匹配与范围校验 → 分级结果经用户确认后写库
- **AI 对话助手**：多轮对话、SSE 流式输出；模型自主调用 7 个工具完成「查营养 / 查摄入缺口 / 写记录 / 撤销记录 / 检索营养知识」
- **营养知识问答（RAG）**：9 篇中文营养学语料（35 个知识块），向量检索后基于材料作答，界面展示「参考资料」——文档、小节与原始出处
- **手动记录与缺口分析**：按日期选食物 + 克数，支持删除回退；实时计算「已摄入 vs 目标」差值
- **REST API**：9 个端点，确定性端点 7 个 + AI 端点 2 个（含 SSE 流式对话）
- **食物库**：内置 104 条常见食物（每 100g 的热量 / 蛋白质 / 脂肪 / 碳水）
- **可复现评测**：30 题标注集，检索层算 R@3 / R@1 / MRR

## 技术栈

Python 3 · SQLite · Streamlit · FastAPI · Pydantic · PyYAML · pytest

**AI**：LangChain / LangGraph（`create_agent` 工具编排）· `langchain-openai` 接入通义千问（阿里百炼 OpenAI 兼容模式，`qwen-plus`）· 自建模型工厂（`llm/factory.py`：配置驱动 + 按角色分档 + 单例缓存）

**RAG**：Chroma（cosine）· 百炼 `text-embedding-v3`（1024 维）· 按 Markdown 标题的结构感知切分

## 项目架构

四层，引用只能向下，不反向：

```
入口  api/        REST 层（FastAPI，9 个端点 / SSE 流式）
      app.py      Streamlit UI（我的计划 / 今日记录）
      pages/      AI 对话助手页
                    │
                    ▼
编排  service.py  业务编排：计划生成 / 每日汇总
      ai/         口语解析 · 确定性护栏 · 工具编排 · 对话流
                    │
                    ▼
能力  rag/        检索 · 上下文拼装 · 出处解析
      llm/        模型工厂（配置驱动 · 角色分档 · 单例）
                    │
                    ▼
基础  db.py       SQLite 读写与日期规范化
      calc.py     BMR / TDEE / 宏量 / 汇总 / 缺口（纯函数）
      config/*.yaml · utils/
```

这条约束的目的**不是**把 AI 做成可删除的插件（本项目 AI 与后端一体交付），而是**限制变更的传导范围**：换模型、换检索方案、重构 Agent 编排，都不需要动 `db` / `calc` / `service`。

| 层 | 文件 | 职责 |
|---|---|---|
| 入口 | `api/` | 路由、请求响应模型、统一错误契约 |
| 入口 | `app.py` / `pages/*.py` | 页面渲染、交互、会话状态 |
| 编排 | `service.py` | 组合数据与计算，输出结构化结果 |
| 编排 | `ai/` | 自然语言解析、护栏、工具编排、链路编排 |
| 能力 | `rag/` | 语料切片、向量建库、检索与上下文拼装、出处解析 |
| 能力 | `llm/` | 按角色构造 `ChatOpenAI` / `OpenAIEmbeddings` |
| 基础 | `db.py` · `calc.py` | 数据访问 / 纯计算 |
| 基础 | `config/*.yaml` · `utils/` | 配置、路径解析、日志 |

### `ai/`

| 文件 | 职责 |
|---|---|
| `parser.py` | 口语 → 结构化 JSON（LCEL 管道：Prompt → Model → JsonOutputParser） |
| `guard.py` | 确定性护栏：库内匹配（精确 → 模糊 → 歧义）+ 克数校验 |
| `pipeline.py` | 串联 `parser → guard`，对 UI 暴露单一入口 |
| `tools.py` | 7 个工具（5 只读 + 2 写）+ `UserCtx` 上下文（`ToolRuntime` 注入） |
| `agent.py` | `create_agent` 构建 + `chat_stream` 流式事件流 |
| `error.py` | `AIServiceError`：AI 层对外唯一的异常类型，供 `agent` 与 `pipeline` 共用 |

**工具清单**：

| 工具 | 参数 | 用途 |
|---|---|---|
| `search_foods_tool` | `keyword` | 名称不完整时模糊搜索 |
| `query_food_tool` | `name` | 名称确定时精确查询 |
| `today_report` | 无 | 今天的摄入与缺口（含明细 id） |
| `report_by_date` | `date` | 指定日期 |
| `search_knowledge` | `query` | 检索营养知识库，返回带编号与出处的段落 |
| `add_meal` | `food`, `grams` | 写入记录（复用护栏 + 幂等检查） |
| `delete_meal` | `record_id` | 撤销记录（id 必须来自查询结果） |

分工原则：**数据类问题走数据库，知识类问题走向量库**。prompt 明确「用户自身的目标值、摄入量必须走数据工具，不得用知识库中的通用数值替代」——否则模型会拿语料里的 BMR 公式自己算，而不是查实际记录。

### `rag/`

| 文件 | 职责 |
|---|---|
| `vector_store.py` | 读 CSV 语料 → 按 `##` 二级标题切分 → 建 Chroma 索引 |
| `rag_service.py` | `search` 检索 → `build_context` 拼装编号上下文 → `parse_sources` 反解析出处 |

### `llm/` 模型工厂

`get_chat_model(role)` / `get_embedding_model()` 从 `config/llm.yaml` 取参数构造客户端，`lru_cache` 保证同角色单例。三点约束：**换模型只改 YAML**（模型名、地址、温度、重试次数只有一个来源）；**按角色分档**（`default` 服务对话与解析，`judge` 服务评测判分，避免自我偏袒）；**`api_key` 缺失在构造期报错**（否则拖到首次调用才返回 401，离根因太远）。

`check_embedding_ctx_length=False` 刻意不放进 YAML：它是「非 OpenAI 官方端点必须关闭」的服务约束，属代码不属配置。

## 快速开始

```bash
pip install -r requirements.txt
python scripts/init_db.py          # 建表并导入食物数据
python -m rag.vector_store         # 建向量索引（35 个知识块）

streamlit run app.py               # UI，默认 8501
uvicorn api.main:app --reload      # REST API，默认 8000
```

浏览器打开 `http://localhost:8501`（UI）或 `http://localhost:8000/docs`（API 文档）。两个进程独立启动——Streamlit 的重跑模型会反复触发 FastAPI 启动，不要塞进同一个进程。

需要环境变量 `DASHSCOPE_API_KEY`（阿里百炼）。`ai/parser.py` 在模块级构造模型，缺该变量时应用无法启动。

## API

`api/` 采用 `api → service / db / calc` 与 `api → ai` 的单向依赖。

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/v1/plan` | 由身体信息生成 BMR / TDEE / 宏量目标 |
| GET | `/api/v1/foods?name=` | 按名称精确查询单个食物 |
| GET | `/api/v1/foods/search?keyword=&limit=` | 关键词模糊搜索（下拉补全） |
| POST | `/api/v1/intake` | 记录一笔摄入 |
| GET | `/api/v1/intake?date=` | 查某日摄入明细（`date` 缺省为今天） |
| DELETE | `/api/v1/intake/{id}` | 删除一笔摄入，成功返回 204 |
| POST | `/api/v1/summary` | 某日汇总：明细 / 已摄入 / 缺口 |
| POST | `/api/v1/parse` | 口语描述 → 结构化食物列表（调用 LLM，2~5s） |
| POST | `/api/v1/chat` | AI 对话，SSE 流式（调用 LLM） |

### `/chat` 的 SSE 帧

`Content-Type: text/event-stream`，每帧一个 `data:` 行，事件类型放在 JSON 的 `type` 里：

| type | 字段 | 说明 |
|---|---|---|
| `text` | `content` | 模型输出的文字片段 |
| `tool` | `name`, `id` | 工具调用开始 |
| `tool_result` | `content`, `name`, `id` | 工具返回，`content` 是引用溯源的来源 |
| `done` | 无 | 正常结束哨兵 |
| `error` | `code`, `message` | 流内异常。**出错时不发 `done`**，客户端据此区分「说完」与「断了」 |

```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"鸡胸肉多少卡"}],"target":{"kcal":3010.2,"protein_g":126,"fat_g":63,"carb_g":484.8},"goal":"增肌"}'
```

### 错误契约

统一错误体，`code` 给机器分支，`message` 给人看：

```json
{"error": {"code": "FOOD_NOT_FOUND", "message": "食物不存在：榴莲", "detail": null}}
```

| HTTP | code | 场景 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | 字段类型错 / 越界 / 枚举非法 / 日期格式非法 / 空白关键词 |
| 404 | `FOOD_NOT_FOUND` | 食物名不存在 |
| 404 | `INTAKE_NOT_FOUND` | 删除的 id 不存在 |
| 502 | `AI_UPSTREAM_ERROR` | AI 上游不可用（超时 / 限流） |
| 500 | `DATABASE_ERROR` | 数据访问失败 |
| 500 | `INTERNAL_ERROR` | 未预期异常 |

三个关键做法：

- **`response_model` 是白名单不是注解**：`db` 层 `SELECT *` 返回全部列，响应模型只声明对外字段，多出来的自动裁掉——表加列或加敏感字段都自动安全。
- **输入约束只放在请求模型**：响应模型加 `gt/le` 会让「库里有一条超范围的旧记录」变成「接口 500」。
- **端点用普通 `def`**：`db` 是同步 `sqlite3`、`ai` 是同步 LangChain，全程无 `await`。写成 `async def` 会让请求在事件循环里串行排队，`def` 由 FastAPI 自动丢进线程池。

## 目录结构

```
Fitness_Diet_Assistant/
├── app.py                  # Streamlit 应用入口（我的计划 / 今日记录）
├── api/                    # REST 层
│   ├── main.py             # 应用装配 + 路由注册
│   ├── deps.py             # 依赖（日期参数）
│   ├── errors.py           # 统一错误契约 + 4 个处理器
│   ├── schemas.py          # 请求 / 响应模型
│   └── routes/
│       ├── plan.py         # POST /plan
│       ├── foods.py        # GET /foods · /foods/search
│       ├── intake.py       # POST / GET / DELETE /intake
│       ├── summary.py      # POST /summary
│       ├── ai_parse.py     # POST /parse
│       └── ai_chat.py      # POST /chat（SSE）
├── pages/
│   └── 1_AI_Mode.py        # AI 对话助手
├── service.py              # 业务编排层
├── db.py                   # 数据访问层（SQLite）
├── calc.py                 # 计算层（纯函数）
├── ai/                     # AI 能力层
│   ├── parser.py           # 口语 → 结构化
│   ├── guard.py            # 确定性护栏
│   ├── pipeline.py         # parser → guard 编排
│   ├── tools.py            # 工具定义 + UserCtx 上下文
│   ├── agent.py            # Agent 构建 + 流式事件流
│   └── error.py            # AIServiceError
├── rag/                    # 知识检索层
│   ├── vector_store.py     # 语料切分 + 向量建库 + 检索
│   └── rag_service.py      # 上下文拼装 + 出处解析
├── llm/                    # 模型工厂
│   └── factory.py          # get_chat_model(role) / get_embedding_model()
├── evals/                  # 评测（不参与运行时）
│   ├── dataset.py          # 加载评测集 + 标注校验
│   ├── retrieval_eval.py   # 检索层：R@1 / R@3 / MRR
│   ├── generation_eval.py  # 生成层：faithfulness / correctness
│   ├── run_eval.py         # 串联、报告、落盘
│   └── results/            # 每次运行的明细 JSON
├── config/
│   ├── SQLite.yaml         # 数据库路径与表名
│   ├── calc.yaml           # 营养计算系数
│   ├── foods.yaml          # 食物数据源路径
│   ├── chroma.yaml         # 向量库参数
│   ├── llm.yaml            # 模型供应商、各角色模型与参数
│   └── evals.yaml          # 评测集路径
├── utils/                  # 配置加载 · 路径解析 · 日志
├── scripts/init_db.py      # 建表 + 导入食物数据
├── tests/                  # pytest
├── data/
│   ├── foods.csv           # 食物营养数据（104 条）
│   ├── foods.db            # SQLite 数据库
│   ├── knowledge/          # 营养知识语料（9 篇 CSV）
│   ├── eval_data/          # 评测集（30 题）
│   └── chroma/             # 向量索引（可由语料重建，不入版本库）
├── logs/
├── requirements.txt
├── requirements-dev.txt
└── DEVLOG.md               # 开发日志
```

## 测试

```bash
pip install -r requirements-dev.txt
pytest          # 93 passed
```

| 文件 | 条数 | 覆盖 |
|---|---|---|
| `test_calc.py` | 24 | 计算公式的正常值与边界值（如碳水的负值保护） |
| `test_db.py` | 23 | 增删查、日期规范化、越界输入、`LIKE` 通配符字面化 |
| `test_guard.py` | 13 | 护栏的分级匹配、边界输入、规范名替换 |
| `test_tools.py` | 7 | 工具写入前置校验、幂等、删除与回显字段 |
| `test_service.py` | 6 | 服务层编排结果的结构与字段完整性 |
| `test_rag_service.py` | 1 | `build_context` 与 `parse_sources` 的契约往返 |
| `test_api.py` | 19 | 6 个确定性端点的状态码、错误码、数值与状态变更 |

测试经过**变异测试**验证：故意在实现中植入缺陷（改公式系数、注释路由注册、改字段名），确认对应用例会失败。只断言 `status_code == 200` 的测试通不过这一关——它拦不住任何实现变化。

## 评测

RAG 效果不能靠「读起来还行」判断。项目内置双层评测：**检索层**衡量「该召回的资料有没有召回」，**生成层**衡量「回答是否被材料支持、是否与标准答案一致」。评测代码不参与运行时，删掉不影响应用。

评测集 `data/eval_data/eval_set_v1.json`，30 题，每题标注 `gold_chunk` 与 `ground_truth`。题型分布：事实型 11 · 误区判断型 7 · 应用型 6 · 换算型 2 · 对比型 2；难度 easy 11 / medium 14 / hard 5。`check_dataset()` 运行前三项校验：必填字段、`id` 唯一、`gold_chunk` 必须真实存在于向量库。

| 层 | 指标 | 定义 |
|---|---|---|
| 检索 | Recall@3 | top-3 中包含 `gold_chunk` 的题目占比 |
| 检索 | Recall@1 | `gold_chunk` 排在首位的题目占比 |
| 检索 | MRR | 命中排名倒数的均值，未命中记 0 |
| 生成 | faithfulness | 回答中的事实性断言被检索材料支持的比例 |
| 生成 | correctness | 与 `ground_truth` 结论是否一致 |

两层分开测的原因：**召回成功不等于答对**——存在「忠实于检索材料、但与标准答案不一致」的样本，问题出在 top-3 里的干扰块。

检索层结果（30 题，k=3，cosine）：

| 指标 | 值 |
|---|---|
| Recall@3 | **96.7%**（29/30） |
| Recall@1 | 90.0%（27/30） |
| MRR | 0.9333 |

复现：

```bash
python -m evals.retrieval_eval     # 只跑检索层：30 次 embedding，不消耗生成额度
python -m evals.run_eval           # 全量：每题 1 次生成 + 2 次判分
python -m evals.run_eval 5         # 只跑前 5 题，调 prompt 时用
```

结果落到 `evals/results/eval_YYYYMMDD_HHMM.json`，`meta` 记录模型、embedding、k、阈值。

## 关键约定

1. **模型只负责转录，代码负责校验**。prompt 明确「只按原话转录，不判断数值是否合理」，所有权值与存在性判断交给 `guard.py`——模型没有数据源的访问权。
2. **护栏输出分级结果**。`ok` / `ambiguous` / `not_found` / `invalid` 四级，任何不确定状态都**不静默写入**。
3. **写操作必须由动作触发**。Streamlit 的 rerun 模型下，副作用不能放在渲染路径上，否则每次交互都会重放。
4. **引用出处由系统附带，不依赖模型标注**。实测在 prompt 要求「标注 `[1]`」后模型一次都没写；改为从工具返回值反解析 `parse_sources`，UI 独立展示「参考资料」，确定性 100%。
5. **metadata 不参与 embedding**。想让标题影响检索必须拼进 `page_content`；实测带前缀使 R@1 从 86.7% 提升到 96.7%。语料有 `##` 二级标题时按结构切（35 块），不用按长度兜底切（会切出 79 块，其中 15 处数字被切断）。

## 版本

| 版本 | 主要内容 |
|---|---|
| **V1** | 确定性内核：食物库 · 营养计算 · 摄入记录 · 缺口分析 · Streamlit |
| **V2** | 自然语言解析 · 确定性护栏 · 分级确认 UI · Tool Calling（7 个工具）· 流式多轮对话 · 对话式写库 · 营养知识 RAG（含引用溯源）· 双层评测框架 · 模型工厂 · 93 条测试（含 API 层） |
| **V1.5** | REST 层：9 个端点（含 SSE 流式对话）· Pydantic 校验 · 统一错误契约 · 全链路数值验收 |

设计思路：先用确定性代码把领域逻辑固化好，再让 LLM 承担调度层——比直接堆 prompt 更可控、可测试。
