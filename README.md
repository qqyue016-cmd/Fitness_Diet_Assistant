# 健身饮食助手 Fitness Diet Assistant

围绕「**每日营养目标 → 实际摄入 → 缺口反馈**」闭环的健身饮食管理工具。支持**一句话自然语言记录**（LLM 解析 + 确定性护栏校验），也保留传统表单录入。

## 功能

- **个性化营养计划**：基于 Mifflin-St Jeor 公式计算 BMR / TDEE，按目标（增肌 / 减脂 / 维持）自动调整每日热量与三大营养素分配
- **自然语言记录**：一句话描述饮食 → LLM 解析为结构化数据 → 护栏做库内匹配与范围校验 → 分级结果经用户确认后写库
- **手动记录**：按日期选择食物 + 克数，支持删除回退
- **缺口分析**：实时计算「已摄入 vs 目标」差值，正数为可摄入余量、负数为超出
- **食物库**：内置 104 条常见食物的营养数据（每 100g 的热量 / 蛋白质 / 脂肪 / 碳水）

## 技术栈

Python 3 · SQLite · Streamlit · PyYAML · pytest

**AI 部分**：LangChain（LCEL）· 通义千问（阿里百炼 DashScope，`qwen-plus`）

## 项目架构

分层设计，依赖单向向下：

```
app.py  (UI · Streamlit)
   │
   ├────────────────┐
   ▼                ▼
service.py         ai/   (AI 能力层)
   │                │  通过 service / db 落库
   ▼                ▼
db.py  ·  calc.py ──┘
   │         │
   ▼         ▼
      config/ (YAML 配置)
```

**依赖方向的铁律**：`ai/` 可以依赖 `service` / `db` / `calc`，**反向绝不成立**。这保证了「把 `ai/` 整个删掉，项目照样能跑」——确定性内核不感知 AI 的存在。

| 层 | 文件 | 职责 |
|---|---|---|
| UI | `app.py` | 页面渲染、交互、会话状态 |
| AI | `ai/` | 自然语言解析、确定性护栏、链路编排 |
| 服务 | `service.py` | 组合数据与计算，输出结构化结果 |
| 数据 | `db.py` | SQLite 读写、日期规范化 |
| 计算 | `calc.py` | BMR / TDEE / 宏量分配 / 汇总 / 缺口（纯函数，无 I/O） |
| 配置 | `config/*.yaml` | 数据库路径、表名、营养系数、数据源路径 |
| 工具 | `utils/` | 配置加载、日志、路径解析 |

### `ai/` 模块组成

| 文件 | 职责 |
|---|---|
| `client.py` | LLM 客户端（`ChatTongyi`，`qwen-plus`，`temperature=0`） |
| `parser.py` | 口语 → 结构化 JSON（LCEL 管道：Prompt → Model → JsonOutputParser） |
| `guard.py` | 确定性护栏：库内匹配（精确 → 模糊 → 歧义）+ 克数校验 |
| `pipeline.py` | 串联 `parser → guard`，对 UI 暴露单一入口 |

## 快速开始

```bash
pip install -r requirements.txt
python scripts/init_db.py      # 建表并导入食物数据
streamlit run app.py
```

浏览器打开 `http://localhost:8501`。

> 使用自然语言记录功能，需配置环境变量 `DASHSCOPE_API_KEY`（阿里百炼）。未配置时手动记录与营养计划功能仍可正常使用。

## 目录结构

```
Fitness_Diet_Assistant/
├── app.py                  # Streamlit 应用入口（UI 层）
├── service.py              # 业务编排层
├── db.py                   # 数据访问层（SQLite）
├── calc.py                 # 计算层（纯函数）
├── ai/                     # AI 能力层
│   ├── client.py           # LLM 客户端
│   ├── parser.py           # 口语 → 结构化
│   ├── guard.py            # 确定性护栏
│   └── pipeline.py         # parser → guard 编排
├── config/
│   ├── SQLite.yaml         # 数据库路径与表名
│   ├── calc.yaml           # 营养计算系数
│   └── foods.yaml          # 食物数据源路径
├── utils/
│   ├── config_tool.py      # 配置加载
│   ├── path_tool.py        # 绝对路径解析
│   └── logger_tool.py      # 日志
├── scripts/
│   └── init_db.py          # 建表 + 导入食物数据
├── tests/                  # pytest 测试
├── data/
│   ├── foods.csv           # 食物营养数据（104 条）
│   └── foods.db            # SQLite 数据库
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

共 **64 条用例**，覆盖四个层面：

- `test_calc.py`（20）：计算公式的正常值与边界值（如碳水的负值保护）
- `test_db.py`（22）：增删查、日期规范化、越界输入校验
- `test_service.py`（6）：服务层编排结果的结构与字段完整性
- `test_guard.py`（12）：护栏的分级匹配、边界输入、规范名替换

护栏的测试经过**变异测试**验证：故意在实现中植入缺陷，确认对应用例会失败——确保测试本身是有效的，而非摆设。

## 设计要点

1. **数据完整性由数据库约束保证**。营养字段加 `NOT NULL`，因此计算层不做缺失值兜底——约束失效时应让错误尽早暴露，而非静默处理。
2. **日期双端规范化**。写入用 `strftime` 严格输出 `YYYY-MM-DD`，读取时也用同一格式比对，保证 `WHERE date = ?` 的字符串全等比较可靠。
3. **主键按实体身份设计**。`foods` 以食物名为主键（同名食物只保留唯一来源版本）；`intake` 用自增 `id` 作为记录身份，与「日期 + 食物 + 克数」这组属性解耦。
4. **配置外置**。数据库路径、表名、营养系数全部写在 YAML 中，调整策略无需改动代码。
5. **模型只负责转录，代码负责校验**。prompt 中明确「不要判断数值是否合理，只按原话转录」，所有权值与存在性判断都交给 `guard.py`——模型没有数据源的访问权，指望它在 prompt 里"输出库里的名字"是不可能实现的。
6. **护栏输出分级结果**。`ok` / `ambiguous` / `not_found` / `invalid` 四级，把"这条能不能写库"翻译成用户可操作的四种决策，任何不确定的状态都**不静默写入**。
7. **写操作必须由动作触发**。Streamlit 的 rerun 模型下，任何副作用（写库、调 API）都不能放在渲染路径上，否则每次交互都会重放一遍。

## 已知局限

- **模型对极端数值存在"合理化"倾向**：如输入 `-50克` 时，模型可能输出 `50`。这类错误发生在理解阶段，输出本身合法，护栏无法检出。缓解手段是 prompt 约束（只转录不判断）；根本解法需引入原文数值对账，当前版本未实现。
- **食物名匹配只覆盖"库名包含输入"**：模型输出 `水煮鸡胸肉` 而库中为 `鸡胸肉` 时无法命中（反向包含未实现），会落入 `not_found` 由用户手动修正。

## 版本

| 版本 | 状态 | 主要内容 |
|---|---|---|
| **V1** | 已完成 | 确定性内核：食物库 · 营养计算 · 摄入记录 · 缺口分析 · Streamlit · 52 条单测 |
| **V2** | 进行中 | 已完成：自然语言解析 · 确定性护栏 · 分级确认 UI；待做：Tool Calling · 营养知识 RAG · 评测脚本 |
| V1.5 | 待开始 | FastAPI + Pydantic 校验 + MySQL + Redis + 认证 |
| V3 | 待开始 | 对话流 + 结构化卡片 · 多步 Agent（LangGraph） |

设计思路：先用确定性代码把领域逻辑固化好，再让 LLM 承担调度层——比直接堆 prompt 更可控、可测试。
