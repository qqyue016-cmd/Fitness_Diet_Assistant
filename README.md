# 健身饮食助手 Fitness Diet Assistant

围绕「**每日营养目标 → 实际摄入 → 缺口反馈**」闭环的健身饮食管理工具。输入身体数据生成个性化营养计划，记录每日饮食，实时查看与目标的差距。

## 功能

- **个性化营养计划**：基于 Mifflin-St Jeor 公式计算 BMR / TDEE，按目标（增肌 / 减脂 / 维持）自动调整每日热量与三大营养素分配
- **饮食记录**：按日期记录摄入（食物 + 克数），支持删除回退
- **缺口分析**：实时计算「已摄入 vs 目标」差值，正数为可摄入余量、负数为超出
- **食物库**：内置 104 条常见食物的营养数据（每 100g 的热量 / 蛋白质 / 脂肪 / 碳水）

## 技术栈

Python 3 · SQLite · Streamlit · PyYAML · pytest

## 项目架构

分层设计，依赖单向向下，UI 层不直接触碰数据库与计算逻辑：

```
app.py  (UI · Streamlit)
   │
   ▼
service.py  (业务编排)
   │              │
   ▼              ▼
db.py          calc.py     (数据访问 · 纯计算)
   │              │
   ▼              ▼
      config/ (YAML 配置)
```

| 层 | 文件 | 职责 |
|---|---|---|
| UI | `app.py` | 页面渲染、交互、会话状态 |
| 服务 | `service.py` | 组合数据与计算，输出结构化结果 |
| 数据 | `db.py` | SQLite 读写、日期规范化 |
| 计算 | `calc.py` | BMR / TDEE / 宏量分配 / 汇总 / 缺口（纯函数，无 I/O） |
| 配置 | `config/*.yaml` | 数据库路径、表名、营养系数、数据源路径 |
| 工具 | `utils/` | 配置加载、日志、路径解析 |

## 快速开始

```bash
pip install -r requirements.txt
python scripts/init_db.py      # 建表并导入食物数据
streamlit run app.py
```

浏览器打开 `http://localhost:8501`。

## 目录结构

```
Fitness_Diet_Assistant/
├── app.py                  # Streamlit 应用入口（UI 层）
├── service.py              # 业务编排层
├── db.py                   # 数据访问层（SQLite）
├── calc.py                 # 计算层（纯函数）
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

共 **52 条用例**，覆盖三个层面：

- `test_calc.py`：计算公式的正常值与边界值（如碳水的负值保护）
- `test_db.py`：增删查、日期规范化、越界输入校验
- `test_service.py`：服务层编排结果的结构与字段完整性

## 设计要点

1. **数据完整性由数据库约束保证**。营养字段加 `NOT NULL`，因此计算层不做缺失值兜底——约束失效时应让错误尽早暴露，而非静默处理。
2. **日期双端规范化**。写入用 `strftime` 严格输出 `YYYY-MM-DD`，读取时也用同一格式比对，保证 `WHERE date = ?` 的字符串全等比较可靠。
3. **主键按实体身份设计**。`foods` 以食物名为主键（同名食物只保留唯一来源版本）；`intake` 用自增 `id` 作为记录身份，与「日期 + 食物 + 克数」这组属性解耦。
4. **配置外置**。数据库路径、表名、营养系数全部写在 YAML 中，调整策略无需改动代码。

## 版本

| 版本 | 阶段 | 主要内容 |
|---|---|---|
| **V1**（当前） | 确定性内核 | 食物库 · 营养计算 · 摄入记录 · 缺口分析 · Streamlit · 52 条单测 |
| V1.5 | 工程化 | FastAPI + Pydantic 校验 + 统一异常 + 日志 + Docker，前端改为调用 API |
| V2 | 智能化 | RAG 营养知识库（含引用溯源）+ 工具编排 + 自然语言解析 + 确定性护栏 + 评测脚本 |
| V3（可选） | 进阶 | 查询改写、多步 Agent 编排（LangGraph）等 |

设计思路：先用确定性代码把领域逻辑固化好，再让 LLM 承担调度层——比直接堆 prompt 更可控、可测试。
