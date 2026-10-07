# 开发日志 · Fitness Diet Assistant

> 项目：健身饮食计划助手 ｜ 目标岗位：AI 应用开发 / AI Agent / Python 后端（2027 暑期实习）
> 设计文档基线：`健身饮食助手_项目设计文档.pdf`（v1.1）

---

## 2026-09-21 ｜ 阶段 V1 开工：数据地基

### 一、今日目标

完成 V1 的第一步「数据地基实验」：把食物营养数据落进 SQLite，并跑通建表与导入链路。这一步不含任何 AI，但决定项目能否成立——数据源不通，后面全是空转。

### 二、完成的事

**1. 数据源选型（关键决策，推翻了原方案）**

实测 Open Food Facts 的搜索接口（`categories_tags_en=chicken-breast`，取 50 条），观察到两个事实：

- 四项营养字段齐全率 49/50，数据质量本身不差
- 但商品名是 `Rôti de Poulet`、`Pechuga de Pollo`、`tiras pollo` 这类法语/西语**预包装食品**名

**结论：Open Food Facts 是「预包装食品条码库」，不是「食材营养成分库」**。它给的是「某品牌调味鸡胸 109 kcal/100g」，而项目需要的是「生鸡胸 165 kcal、蛋白 31g」。

据此调整数据源分层：

| 方案 | 用途 | 决策 |
|---|---|---|
| 手工种子表（USDA 网站抄录） | V1 主数据源 | **采用**：零网络依赖、数据可靠、符合「私有数据」定位 |
| USDA FoodData Central API | 食材级批量拉取 | V2 使用（需注册免费 key） |
| Open Food Facts | 包装食品 / 条码扫描场景 | V2/V3 作为补充 |

**2. 生成 104 条食物营养种子数据（`data/foods.csv`）**

- 列结构：`name, kcal, protein, fat, carb, source`（每 100g 计）
- 分类构成：谷物主食 19 ｜ 肉蛋水产 19 ｜ 豆制品乳制品 10 ｜ 蔬菜 26 ｜ 水果 14 ｜ 坚果油脂及其他 16
- `source` 列做**溯源**：`USDA`（SR Legacy 官方值）94 条、`CFCT`（中国食物成分表第 6 版）10 条、`典型值`（品牌/规格差异大）3 条
- 文件编码 UTF-8 with BOM，Excel 可直接打开

**3. 数据自洽性校验（发现并解释了一处「假异常」）**

用规则 `kcal ≈ 4×蛋白 + 9×脂肪 + 4×碳水` 校验 104 条，18 条偏差超过 12%，且**全部是蔬菜水果类**：

```
菠菜（生）   表列 23  | 按宏量算 29.6  | 偏差 +28.7%
白蘑菇（生） 表列 22  | 按宏量算 28.3  | 偏差 +28.6%
芦笋（生）   表列 20  | 按宏量算 25.3  | 偏差 +26.5%
```

**根因**：USDA 的碳水数值**包含膳食纤维**，而纤维实际只提供约 2 kcal/g。用 4 kcal/g 折算必然高估高纤维食物。
**结论**：这不是数据错误。该校验的容差应设 **20-25%**，设 12% 会产生误报。（已作为「数据自洽性测试」的设计依据。）

**4. 设计决策：食物「生熟」状态字段的处理**

最初在名称里标注状态（`鸡胸肉（生）`），后经讨论确定最终方案。讨论中确认的关键量级：

| 食物 | 生 / 干 | 熟 | 差异 |
|---|---|---|---|
| 鸡胸肉 | 120 kcal | 165 kcal | 1.4 倍 |
| 大米 / 米饭 | 365 kcal（生米） | 130 kcal（熟饭） | 2.8 倍 |
| 燕麦 | 389 kcal（干片） | 71 kcal（粥） | 5.5 倍 |

**最终方案（按「用户默认按熟重记录」的产品判断简化）**：一物一行、不设 state 列；主食与鸡蛋取熟值；干货类保留干重值；无法可靠取得熟值的 13 条肉类暂留生重值，并在 `source` 列标注「（生重值）」。

**5. 项目骨架搭建**

```
Fitness_Diet_Assistant/
├── config/
│   ├── SQLite.yaml          # DB_PATH / TABLE_NAME
│   └── foods.yaml           # foods_data_path
├── utils/
│   ├── path_tool.py         # 用 __file__ 反推项目根，统一提供绝对路径
│   └── config_tool.py       # 加载 YAML 配置
├── data/
│   ├── foods.csv            # 种子数据（104 条）
│   └── foods.db             # 由脚本生成
├── db.py                    # 数据层：连接 / 建表 / 导入
├── scripts/
│   └── init_db.py           # 初始化脚本：读 CSV → 清洗 → 调 db
└── calc.py / service.py     # 待实现
```

**6. 数据层跑通并验收**

运行 `python -m scripts.init_db` → 输出「数据插入成功」，`data/foods.db` 由 0 B 变为 20 KB。

自查与验证结果：

| 检查项 | 结果 |
|---|---|
| 导入行数 | 104 ✓ |
| 关键数据 | `鸡胸肉 = 165.0 / 31.0 / 3.6 / 0.0 / USDA` ✓ |
| BOM 污染 | name 含 BOM 的行数 = 0 ✓ |
| 空值处理 | 空字符串残留 0 条 ✓ |
| 字段类型 | `typeof`：kcal/protein = `real`，source = `text` ✓ |
| **幂等性** | 重跑后仍 104 行，无重复 ✓ |
| **upsert 更新** | 手工把鸡胸肉改成 999 → 重跑导入 → 恢复 165 ✓ |
| **异常分支** | 表名改为不存在 → 正确抛出 `RuntimeError`，`__cause__` 保留原始异常 ✓ |

---

### 三、遇到的问题与解决过程

**问题 1：`unrecognized token: ":"` —— 把绝对路径当成了表名**

- 现象：建表与插入同时报错，提示无法识别的记号 `:`
- 原因：写了 `get_abs_path(config_sqlite['TABLE_NAME'])`，生成 `D:/develop/.../foods` 并拼进 SQL，变成 `CREATE TABLE D:/develop/.../foods`，SQLite 解析到 `D:` 的冒号即报错
- 解决：表名是 **SQL 标识符**，直接用 `{config_sqlite['TABLE_NAME']}`，**不走路径工具**；`get_abs_path` 只用于文件路径
- 收获：**SQL 语句中只有「值」用 `?` 占位符；表名、列名是固定文本。** 同类错误今天犯了两次（前一次是把列清单写进 `{}`）

**问题 2：数据装载——`csv.reader` 用法 + 编码**

- 现象：直接把路径字符串传给 `csv.reader`（该 bug 被问题 1 的报错掩盖，未暴露）
- 原因：`csv.reader` 需要的是**可迭代的行序列**（通常是文件对象），传字符串会**逐字符**迭代
- 解决：先 `open(path, 'r', encoding='utf-8-sig', newline='')`，再交给 `csv.reader`
- 收获：编码必须是 **`utf-8-sig`**——CSV 带 BOM，用 `utf-8` 读会让第一条数据的名称多出 `\ufeff` 字符，静默查不到。另：读出的是 `list[str]`，空字段为 `''`，类型与空值都要手工转换

**问题 3：空值被存成空字符串，而不是 NULL**

- 现象：`''` 写入后以 TEXT 形式存在库中，而非 NULL
- 危害（实测）：三行数据 `10.0 / '' / None` 时，`SUM = 10.0` 看起来正常，但 **`AVG = 5.0`（正确值应为 10.0）**——空字符串被当成「值为 0 的有效数据」放进了分母。**不报错，但结果错一倍**
- 解决：`float(x) if x.strip() else None`，让缺失值以真正的 NULL 存储（`sqlite3` 自动把 Python 的 `None` 转成 SQL 的 `NULL`）
- 收获：**`''` 与 `NULL` 是两件事**。缺失值若存成空字符串，`WHERE x IS NULL` 判断失效，聚合函数结果被静默污染

**问题 4：`INSERT OR IGNORE` 的语义不符需求**

- 现象：重复导入不产生重复行，但**不会更新数值**
- 解决：改为 `ON CONFLICT(name, source) DO UPDATE SET kcal = excluded.kcal, ...`
- 验证：手工把鸡胸肉热量改成 999，重跑导入后恢复 165 ✓
- 收获：`OR IGNORE` 是「冲突跳过」，`DO UPDATE` 才是「冲突更新」——**面对数据修正时行为完全不同**。这也是「重复导入」这条边界用例的正确解法

**其他已修复（一行记）**

- `ModuleNotFoundError: No module named 'utils'` → 直接运行脚本时 `sys.path` 是脚本目录而非项目根 → 改用 `python -m scripts.init_db`（**命令行能跑才算跑通**，IDE 会掩盖此问题）
- 批量插入用了 `execute` → 应 `executemany`，且参数必须是**二维结构**（一维报 `ProgrammingError`）
- 营养字段声明为 `int` → 应为 `REAL`（SQLite 动态类型掩盖了这个问题，MySQL 严格类型会暴露）
- 表无主键 → 加 `PRIMARY KEY (name, source)`；营养字段 `NOT NULL` 改为允许 NULL（否则无法表达「数据缺失」，会被迫填 0，而 0 表示「确实是零」）
- 异常被 `print` 后静默继续 → 改为 `raise ... from e`，失败即中断并保留异常链

---

### 四、可迁移的规则（今天沉淀下来的）

1. **SQL 语句中只有「值」用 `?` 占位符；表名、列名是固定文本**，不要用 f-string 拼路径或对象
2. **`''` 与 `NULL` 是两件事**；缺失值必须存 NULL，否则聚合函数会静默算错
3. **SQLite 动态类型会掩盖类型错误**，MySQL 严格类型会暴露——设计表结构时要按目标数据库的真实语义来
4. **分层判据**：数据层只回答「数据怎么存、怎么取」，不回答「业务上该怎么做」。函数里出现「目标」「缺口」「推荐」这类业务词，它就不属于数据层
5. **批量写入要求二维结构**，与「元组」无关
6. **路径工具只用于文件路径**，表名/列名/键名属于标识符，不是路径
7. **命令行能跑才算跑通**，IDE 的便利会掩盖 sys.path 问题

---

### 五、今天产出的面试素材

- **为什么不让 LLM 算数**：数值计算交给确定性代码，模型负责意图理解与个性化规划
- **数据源选型判断**：为什么放弃 Open Food Facts（它是包装食品库，不是食材营养库）
- **数据质量校验**：膳食纤维导致 4/9/4 系数天然高估高纤维食物，校验容差需放宽到 20-25%
- **幂等导入设计**：主键 + `ON CONFLICT DO UPDATE`，让重复导入既能防重又能更新
- **SQLite vs MySQL**：动态类型 vs 严格类型的实际差异，以及迁移成本落在哪一层（`db.py` 内部，`service` 不受影响）

---

## 2026-09-22 ｜ V1 收尾：数据层完工 + 计算层第一批

### 一、今日目标

收尾数据层（补查询能力），并写出计算层（`calc.py`）第一批函数，跑通验收数字。目标是让 V1 的"确定性内核"成形——数据能查、热量能算。

### 二、完成的事

**1. 项目仓库独立化（凌晨完成）**

- 从父仓库 `PythonProject` 中拆出为独立 GitHub 仓库 `qqyue016-cmd/Fitness_Diet_Assistant`
- 父仓库停止跟踪本项目（`git rm -r --cached`），根 `.gitignore` 加入该目录
- 清理远程无关历史后推送成功，共 **12 个文件**入库
- **顺带修复**：父仓库 `.gitignore` 被记事本保存成 **UTF-16 编码**（文件头 `fffe`，每个字符后跟 `00` 字节），Git 按字节匹配导致忽略规则完全失效 → 重写为 UTF-8 后生效
- 验证：`.venv` / `.idea` / `__pycache__` / `data/*.db` **均未入库**

**2. 数据层收尾：补两个查询函数**

| 函数 | 用途 |
|---|---|
| `query_food(name) -> dict \| None` | 精确查询，用于记录摄入时取营养值 |
| `search_foods(keyword) -> list[dict]` | 模糊查询（`LIKE`），供 UI 搜索框 |

契约：统一返回 `dict`，不返回 `sqlite3.Row`——上层不感知底层用的是 SQLite。

**3. 配置层扩展**

- 新增 `config/calc.yaml`：活动系数表 / 目标热量倍数 / 蛋白系数 / 脂肪系数
- `config_tool` 新增 `load_calc_config`

**4. 计算层第一批 4 个函数（`calc.py`，零依赖）**

| 函数 | 职责 |
|---|---|
| `calc_bmr` | Mifflin-St Jeor 基础代谢 |
| `calc_tdee` | BMR × 活动系数 |
| `calc_target_kcal` | 按增肌 / 减脂 / 维持调整热量 |
| `calc_macro_target` | 拆分为蛋白 / 脂肪 / 碳水克数，含碳水为负保护 |

**验收结果（70kg / 175cm / 25 岁男 / 中等活动量 / 增肌）**

```
BMR 1673.75 → 1674 ｜ TDEE 2594.31 → 2594 ｜ 目标热量 2983.46 → 2983
蛋白 126.0 g ｜ 脂肪 63.0 g ｜ 碳水 478.11 g
```

### 三、遇到的问题与解决过程

**问题 1：`finally` 引用了未绑定的变量，把真实错误吃掉了**

- 现象：调用 `search_foods` 报 `UnboundLocalError: cannot access local variable 'cur'`
- 排查：打印完整 traceback 后发现是**三层异常链**——真实的 `OperationalError`（SQL 写错）被包装成 `RuntimeError`，又被 `finally` 里的 `cur.close()` 覆盖
- 原因：`cur` 只在 `try` 内部赋值；`execute` 抛错时它从未被绑定，`finally` 再调用它的方法就报错
- 解决：把 cursor 的创建**移到 `try` 之前**（与 `create_table` / `insert_data` 统一）
- 收获：**`finally` 里只关闭在 try 之前就已创建的资源**。否则资源创建失败时会制造第二个错误，把第一个错误掩盖掉——排查成本翻倍

**问题 2：静默兜底导致 38% 数值误差且不报错**

- 现象：`calc_tdee(bmr, 'light')` 返回 3180.125，正确值应为 2301.41
- 原因：分支写成了 `elif activity_level == 'lightl'`（多一个 `l`），判断不成立后落入 `else`，取了 `extreme`（1.9）
- 解决：改用**查表 + 成员校验**——`if x not in TABLE: raise ValueError(...)`，再取 `TABLE[x]`
- 收获：**`if/elif` 链里的重复字符串字面量是拼写风险的温床**。查表写法让「写错选项名」必然报错，而不是静默返回错误值；新增选项也只需改配置

**问题 3：`calc_macro_target` 的取值与返回契约都是错的**

- 现象：返回 `[1.15, 1.8, 1.8]`，正确结果应为 `{'protein_g': 126.0, 'fat_g': 63.0, 'carb_g': 478.11}`
- 原因：碳水位取了「热量倍数」、脂肪位取了「蛋白系数」、都没有乘体重、也没有用碳水公式；且**返回 `list` 而函数签名声明 `-> dict`**
- 解决：对照公式重写，并明确**输入输出契约**（声明的返回类型必须与实现一致）
- 收获：**单位与量纲错误不会报错，只会算错**。「每 kg 系数」和「倍数」必须在命名上区分清楚

**问题 4：`dict(None)` 导致查询不存在的食物直接崩溃**

- 现象：`query_food('火鸡胸肉')` → `TypeError: 'NoneType' object is not iterable`
- 原因：查不到时 `fetchone()` 返回 `None`，被直接送进 `dict()`
- 附带问题：这个 `TypeError` **不被 `except sqlite3.Error` 捕获**（它不属于 sqlite 异常族）
- 解决：先判空再转换——`return dict(row) if row else None`
- 收获：**「查不到」是正常分支，不是异常**；异常捕获范围要与实际可能抛出的异常匹配

**其他已修复（一行记）**

- `search_foods` 的 SQL 漏写 `WHERE name` → `near "?": syntax error`
- 函数名拼写 `calca_target_kcal` → `calc_target_kcal`
- `calc_target_kcal` 内部硬编码 1.15 / 0.85，配置里的系数表形同摆设 → 改为从配置读取
- 所有 `else` 静默兜底统一改为抛错

### 四、可迁移的规则（今天沉淀下来的）

1. **枚举 / 分类参数用「查表 + 成员校验」**，不用 `if/elif` 链——从结构上消除拼写导致的静默错误
2. **`finally` 只关闭在 `try` 之前创建的资源**，否则清理动作会制造第二个错误
3. **异常捕获范围要与可能抛出的异常匹配**（`TypeError` 不在 `sqlite3.Error` 族里）
4. **静默兜底是最危险的一类 bug**：不报错，但结果错。宁可抛错
5. **函数签名声明的返回类型必须与实现一致**——声明 `-> dict` 就不能 `return list`
6. **取整只放在展示层**：内部全程 float，提前取整会让误差传播
7. **系数与阈值一律外置到配置**，代码里不出现魔法数字

### 五、今天产出的面试素材

- **一个 38% 误差的静默 bug 及其结构性修法**：从「拼错分支名 → 静默取默认值」到「查表 + 校验 → 必然报错」。讲的是**如何用结构消灭一类 bug**，而不只是修一个 bug
- **`finally` 与异常链**：三层异常链如何掩盖真实错误，以及资源清理的正确位置
- **分层契约**：数据层返回 `dict` 而非 `sqlite3.Row`，使上层不依赖具体数据库实现——这是"将来换 MySQL 只改一层"的依据
- **数值与模型隔离**：`calc.py` 零依赖（不碰数据库、不调模型），既保证数值准确，也为 V2 把它当作 Agent 工具调用做准备

---

## 2026-09-27 ｜ V1 基础设施：日志系统接入

### 一、今日目标

给项目接入日志系统：写 `utils/logger_tool.py`，把脚本里的 `print` 换成日志，并**明确日志应该打在哪一层**。目的是让后续的 `service` / API / UI 有一致的异常出口和可观测性基础，而不是等到出问题才补。

### 二、完成的事

**1. 新增 `utils/logger_tool.py`（日志基础设施）**

| 设计点 | 做法 | 理由 |
|---|---|---|
| 双 handler | 控制台 `INFO` / 文件 `DEBUG` | 控制台看进度，文件留全量用于排查 |
| 日志格式 | `时间 - 级别 - 文件名 - 行号 - 消息` | 带 `filename` + `lineno`，输出直接定位到代码行 |
| 防重复 | `if logger.handlers: return logger` | 同一 logger 被多次 `get_logger` 会叠加 handler，导致同一条日志重复输出 |
| 单例导出 | 模块级 `logger = get_logger()` | 其他模块 `from utils.logger_tool import logger` 直接用 |
| 落盘位置 | `logs/Diet_Assistant_YYYYMMDD.log` | 按日期分文件；目录用 `os.makedirs(..., exist_ok=True)` 自动创建 |

**2. 接入运行边界：`scripts/init_db.py`**

- `print('数据导入成功...')` → `logger.info('数据导入成功，共 %d 条', n)`
- 包 `try / except`：`logger.error('数据导入失败', exc_info=True)`，随后保留 `raise`
- 用 `%d` 而非 f-string —— 日志级别被过滤时不会白白拼字符串（延迟格式化）

**3. `.gitignore` 补 `logs/*.log`**

- 实测 `git check-ignore -v logs/test.log` → 命中 `.gitignore:6:logs/*.log`
- 不忽略的后果：每跑一次程序就产生一个新日志 → `git status` 永远是脏的，仓库体积持续膨胀

**4. 确立「日志分层」约定（本层只 raise，不 log）**

| 层 | 动作 | 原因 |
|---|---|---|
| `db.py` | 只 `raise`，不 `log` | 底层不知道调用方是谁、会不会处理 |
| `calc.py` | 只 `raise`，不 `log` | 输入校验失败是**预期路径**，不是故障 |
| `scripts/init_db.py` | **边界**：捕获 + 记录 + 终止 | 这里才知道这次失败意味着什么 |

**5. 实测验证**

| 场景 | 控制台 | 日志文件 |
|---|---|---|
| 正常导入 | 1 条 INFO | 1 条 INFO |
| 故障（临时移走 CSV 制造 `FileNotFoundError`） | **2 份堆栈**（见问题 3） | 1 条 ERROR + 1 份完整堆栈 ✓ |

### 三、遇到的问题与解决过程

**问题 1：日志该打在哪一层——「每条报错都记」是错的**

- 疑惑：既然有了日志，是不是每处报错都要记一条？
- 实测对比（模拟 db → service → 边界三层各自记录）：

  ```
  方案 A｜每层都记 → 3 条 ERROR：
      [ERROR] 查询数据失败：目标热量不足以满足最低蛋白与脂肪需求   ← 无堆栈
      [ERROR] 生成计划失败：查询数据失败                        ← 无堆栈
      [ERROR] 数据库初始化失败                                ← 含完整堆栈

  方案 B｜只在边界记 → 1 条 ERROR：
      [ERROR] 数据库初始化失败                                ← 含完整堆栈
  ```

- 结论：方案 A 里前两条是纯噪音——**信息量比第三条少，却占了 2/3 版面**
- 原则：**同一条异常只记一次，记在边界**。`raise` 本身就是"向上汇报"，异常一路传递到边界时，`exc_info=True` 一次性写下完整堆栈与异常链
- 三个必须"就地记录"的例外：
  1. **异常被吞掉**（catch 后不再 `raise`）——不在当场记，信息永久丢失
  2. **需要补充异常本身没有的上下文**（哪个用户、哪个文件、哪次请求）——只有这一层知道
  3. **重试 / 降级发生**——属预期内可恢复事件，记 `warning` 留痕
- 收获：**日志的价值在精准，不在数量**。顺便反思：之前那个 `OperationalError` 被 `UnboundLocalError` 掩盖的例子，如果每层都记，日志里会出现两条独立 ERROR，很容易误判成"有两个问题"

**问题 2：`print` 能换成日志，`raise` 不能**

- 两者职责不同：`logger.xxx()` **记录**发生了什么，不改变流程；`raise` **改变控制流**，交给调用方处理
- 若把 `raise` 换成 `logger.error()`：异常消失 → 调用方（`service` / UI）再也捕获不到 → 用户输入非法时程序会带着错误结果继续跑
- 这正是前几天刚修掉的"静默错误"模式，只是换了个马甲
- 结论：本次只替换了 **1 处 print**（`scripts/init_db.py`）；`calc.py` 5 处 `ValueError`、`db.py` 4 处 `RuntimeError` **全部保持不动**

**问题 3：故障时控制台出现两份堆栈**

- 现象：制造 `FileNotFoundError` 后，控制台打印了**两份完全相同的 traceback**
- 原因：边界处 `logger.error(..., exc_info=True)` 打印一份（日志 handler 输出到控制台）；随后 `raise` 继续往上抛，`__main__` 处无人捕获，**Python 默认的 `excepthook` 又打印一份**
- 修法：把 `try/except` 移到 `__main__` 块，记录后 `sys.exit(1)`，**不再往上抛**：

  ```python
  def init_table():
      create_table()
      data = get_data()
      n = insert_data(data)
      logger.info('数据导入成功，共 %d 条', n)

  if __name__ == '__main__':
      try:
          init_table()
      except Exception:
          logger.error('数据导入失败', exc_info=True)
          sys.exit(1)
  ```

- 收获：**"记录 + 抛出"放在同一处，就会和 Python 默认输出重复**。顶层边界的职责是「记录并终止」，不是「记录并继续抛」；顺带 `sys.exit(1)` 让脚本给出正确的退出码，便于将来接入 CI

### 四、可迁移的规则（今天沉淀下来的）

1. **同一条异常只记一次，记在边界**——底层只 `raise`，不 `log`
2. **异常被吞掉时必须就地记录**：一旦不再抛出，栈上没人能记它了
3. **输入校验失败（`ValueError`）是预期路径**，不落 `ERROR`，否则日志噪音会淹没真正的故障
4. **同一异常在不同调用方的级别不同**（CLI 是致命、Web 是单请求失败），所以级别由边界决定，不由底层决定
5. **`logger.error` 后面要有 `exc_info=True`**，否则日志里只有一行 message，看不到堆栈
6. **日志用 `%` 延迟格式化**（`logger.info('...%d', n)`），不要 f-string
7. **顶层边界「记录 + 终止」用 `sys.exit`**，不要「记录 + 再抛」，否则和默认异常输出重复
8. **`finally` / 资源清理之外的运行产物（日志、数据库文件）一律进 `.gitignore`**

### 五、今天产出的面试素材

- **日志分层原则**：为什么不是每条报错都记——用「3 条日志 vs 1 条日志」的实测对比讲清"精准优于数量"
- **`print` / `raise` / `logger` 三者职责区分**：记录不改变流程，抛出改变控制流，混淆会导致静默错误
- **`exc_info=True` 的作用**：不加参数时日志只有一行字，排查时等于没有
- **边界层的职责设计**：顶层负责"记录并终止"（`sys.exit`），而不是"记录并继续抛"——这一条同时解决了日志重复与退出码缺失
- **边界处理的推进顺序**：先抛错（可测试），再补降级策略（先保蛋白 → 降脂肪至 0.6 g/kg 下限 → 调碳水）

---

## 2026-10-05 ｜ V1 补课：日志边界收尾 + 单元测试落地

### 一、今日目标

两件事：① 补齐 9-27 遗留的日志边界缺陷；② 建立 pytest 测试套件（V1 验收的硬指标，已欠两周）。

②的目的不是"勾掉一个待办"，而是**给后续改动装回归防护**——V1 剩下的工作要动 `db.py`（加 `intake` 表），没有测试就是盲改：改完只能靠"手动跑一下好像还行"来判断，而手工验证太贵，你不会每次都做。

### 二、完成的事

**1. 修日志边界的两处缺陷**

9-27 把 `try/except` 移到 `__main__` 后，控制台的重复堆栈消失了——**但代价是堆栈也没了**。当时是用"删掉堆栈"换来了"删掉重复打印"，做了错误的交易。本次补回：

```python
except Exception as e:
    logger.error('数据库创建失败：%s', e, exc_info=True)   # 给人看：完整堆栈
    sys.exit(1)                                            # 给机器看：非零退出码
```

实测（临时移走 `data/foods.csv`）：日志含完整 traceback，`echo $?` 返回 **1**。

**2. 建立测试套件：22 条用例**

| 文件 | 条数 | 覆盖内容 |
|---|---|---|
| `tests/test_calc.py` | 15 | BMR 男/女、TDEE 五档（参数化）、目标热量三档、宏量分配，加 4 条非法输入 |
| `tests/test_db.py` | 7 | `query_food` 命中/未命中/空串/返回类型/参数化查询，`search_foods` 命中/空结果 |

**断言写的是「契约」而不是「当前输出」**：

| 断言 | 守的契约 |
|---|---|
| `isinstance(query_food('鸡蛋'), dict)` | 数据层不把 `sqlite3.Row` 泄漏给上层 |
| `query_food("' OR '1'='1") is None` | SQL 用 `?` 占位符，不用字符串拼接 |
| `all('鸡' in n for n in names)` | 模糊查询的每条结果都符合匹配规则 |
| `search_foods('火鸡') == []` | 无结果返回空列表，返回类型稳定 |

**3. 三项验证（没有只跑绿就收工）**

| 验证 | 结果 |
|---|---|
| 全量测试 | **22 passed in 0.09s** |
| **幂等性** | 连跑两次均 22 passed，库内仍 **104 行**，无重复 |
| **变异测试** | 故意植入缺陷后 **21 passed / 1 failed**，失败的正是该失败的那条 |

**变异测试的做法**：临时把 `db.py` 的 `return dict(result)` 改成 `return result`，看测试能否抓住：

```
____________________ test_query_food_contract_returns_dict ____________________
>       assert isinstance(query_food('鸡蛋'), dict)
E       AssertionError: assert False
E        +  where False = isinstance(<sqlite3.Row object at 0x000002A3C517E890>, dict)
```

**恰好 1 条失败，且正是该失败的那条**——说明断言与契约是一对一的，定位精度正确。随后立即还原，`git diff db.py` 为空。

**4. 依赖声明**

| 文件 | 内容 | 说明 |
|---|---|---|
| `requirements.txt` | `PyYAML==6.0.3` | 唯一的**运行依赖**（`utils/config_tool.py` 读 YAML 用） |
| `requirements-dev.txt` | `-r requirements.txt` + `pytest==9.1.1` | **开发依赖**，终端用户不需要 |

确认项目第三方依赖**只有 2 个**，其余全部使用标准库（`sqlite3` / `csv` / `os` / `logging` / `datetime` / `sys`）。

### 三、遇到的问题与解决过程

**问题 1：`parametrize` 声明了参数，函数签名却没接收**

- 现象：`collected 0 items / 1 error`，报错 `In tests/test_calc.py::test_tdee_all_level: function uses no argument 'level'`，**一个用例都没跑**
- 原因：`@pytest.mark.parametrize('level,expected', [...])` 是把每组数据**当作实参传进测试函数**，所以签名必须接得住这两个名字；写完装饰器忘了改签名
- 解决：`def test_tdee_all_level(level, expected):`
- 收获：**学会区分两类报错**——「收集阶段错误」（`collected 0 items / N error`，属签名/导入/语法问题，报错常不带行号）与「运行阶段失败」（`N failed`，给出 `Obtained` / `Expected`）。看到 `collected 0 items` 就该知道问题在结构层，与期望值算得对不对无关

**问题 2：修日志时用"删掉堆栈"换"删掉重复打印"**

- 现象：改完重复堆栈没了，但失败时日志里只剩一行 message，看不到任何调用链
- 根因：`logger.error('...：%s', e)` 缺了 `exc_info=True`。`str(e)` 只给"是什么错"，traceback 才给出"在哪、怎么走到那的"
- 附带缺陷：异常被 `except` 吞掉后没有 `sys.exit(1)`，**失败时退出码仍是 0**，CI / 自动化会误判为成功
- 解决：补 `exc_info=True` 与 `sys.exit(1)`
- 收获：**日志是给人看的，退出码是给机器看的**。只写日志等于只通知了人，程序链上的下一步（`cmd && 后续`、CI、cron、Docker healthcheck）仍以为一切正常

**问题 3：断言该写"快照"还是"契约"**

- 起初的想法是 `assert len(search_foods('鸡')) == 4`——结果数量对得上就行
- 问题：**"4 条"是当前 104 条数据的副产品**，以后新增食物它就会挂，而你会误以为查询逻辑坏了
- 对比验证：模拟"`WHERE` 失效、返回了全部数据"的坏实现（`['白米饭','鸡胸肉','西兰花','橄榄油']`）——`'鸡胸肉' in names` **仍然通过**（发现不了问题），`all('鸡' in n for n in names)` **失败**（抓住了）
- 解决：断言语义（每条结果都含关键词），不断言数量
- 收获：**测试要断言"规则"，不要断言"当前快照"**

**其他已确认（一行记）**

- `sqlite3.Row` 无 `.get()` 方法、`json.dumps()` 报 `TypeError`，故 `dict(result)` 那一步转换是必要的
- `pytest.approx` **支持 dict 整体比较**且语义严格：键缺失/多余均判 False，浮点微小误差判 True
- `assert` 在 `python -O` 优化模式下**会被整条删除**，因此绝不可用于输入校验（校验一律 `raise ValueError`）
- `.pytest_cache/` 自带内部 `.gitignore`（内容为 `*`），无需加入项目 `.gitignore`
- 运行测试必须用 `python -m pytest`：直接运行脚本时 `sys.path[0]` 是脚本所在目录，`import calc` 会失败

### 四、可迁移的规则（今天沉淀下来的）

1. **测试断言契约，不断言快照**——断言返回类型、查询语义、失败形态，而不是具体条数或数值
2. **跑绿不等于有效**：用变异测试（故意改坏关键实现，看测试是否抓住）验证测试不是空壳
3. **区分「收集阶段错误」与「运行阶段失败」**：前者 `collected 0 items`，问题在签名/导入
4. **fixture 复用既有初始化函数的三个前提**：无参数、幂等、无交互。缺任一条就必须自己写准备步骤
5. **`assert` 不能用于输入校验**（`-O` 会删除）；输入校验用 `raise`，内部不变量用 `assert`
6. **日志给人、退出码给机器**：边界层负责"记录并终止"，不是"记录并继续抛"
7. **`exc_info=True` 才有堆栈**；不加参数时日志只有一行字，排查时等于没有
8. **依赖清单手写，不用 `pip freeze`**：前者是"依赖声明"，后者是"环境快照"（会带上别人的间接依赖）
9. **幂等性要写成可验证的事实**——连跑两次测试、检查行数不变，比"应该没问题"可靠

### 五、今天产出的面试素材

- **如何证明测试有效**：讲变异测试——"我把 `dict(result)` 改成 `result`，22 条里恰好 1 条失败，且正是那条契约测试"。这个回答比"我写了 22 个单元测试"有分量得多
- **契约测试 vs 快照测试**：为什么 `len(...) == 4` 是坏断言，`all('鸡' in n)` 是好断言
- **`assert` / `raise` / `logger` 三者的语义分工**：断言内部不变量 / 报告外部输入非法 / 记录事实。附带 `-O` 会删除 assert 这个细节
- **日志与退出码的双通道设计**：为什么"记录 + 终止"必须成对出现，只做一半会怎样
- **无第三方运行时依赖**：除 PyYAML 外全部标准库，部署只需一个文件——这是工程简洁性的加分项
- **fixture 的复用判断**：为什么能直接复用 `init_table()`，以及什么情况下必须拆开（加参数 / 需要临时库 / 不再幂等）

---

## 2026-10-07 ｜ 摄入计算链路 + 数据完整性策略定案

### 一、今日目标

补齐 10-06 欠下的摄入记录链路（`calc` 三个函数）。过程中牵出一个横跨 **schema / 计算层 / 数据源** 三处的策略问题——**数据完整性由谁保证**——一并定案。

### 二、完成的事

**1. `calc.py` 新增三个函数（摄入链路）**

| 函数 | 职责 |
|---|---|
| `calc_food_intake(food, grams)` | 单条记录：每 100g 值 × `grams/100` |
| `sum_intake(items)` | 汇总一天的摄入 |
| `calc_gap(target, intake)` | 缺口 = 目标 − 已摄入（正数=还能吃，负数=超出） |

同时统一了营养字典的键名与形状：`{'kcal', 'protein_g', 'fat_g', 'carb_g'}`，并由常量 `NUTRIENT_KEYS` 收口，供 `sum_intake` / `calc_gap` 共用。

**2. 关键决策：数据完整性交给数据库约束，而不是上层约定**

| 层 | 动作 |
|---|---|
| 数据库 | `foods` 表四个营养字段加 **`NOT NULL`** |
| 计算层 | **删掉全部缺失值处理**（`_scale` 的 None 分支、`sum_intake` 的 `unknown_items`、`calc_gap` 的 None 判断） |
| 导入层 | 不做空值校验（`NOT NULL` 已覆盖） |
| 数据源 | 不做自动准确性校验脚本（见下） |

**决策依据**：

- 数据无人工录入环节 → 不存在"打错一位数"类风险
- "缺失"与"为零"语义不同。鸡胸肉的碳水确实是 `0`，把它和"数据未知"混起来会污染统计
- **完整性必须由约束保证，而不是靠"我们保证"**：约束比自律可靠，且失败时机在入库（有人看着），不在用户查询时

**关于"不做准确性校验脚本"**：已评估并否决。除了无人工录入，还有一个理由——该类自洽性校验（`kcal ≈ 4P+9F+4C`）**存在已知误报**：实测现有数据中偏差超 20% 的 5 条全是高纤维蔬菜（菠菜 28.7%、白蘑菇 28.6%、芦笋 26.5%…），它们是**正确数据**，只是膳食纤维按 4 kcal/g 折算必然偏高。**一个会误报的检查比没有检查更糟——它会训练人忽略告警。** 准确性改为依赖 `source` 字段的**可追溯性**。

**3. 数据完整性从"约定"变成"约束"（实测）**

```
PRAGMA table_info(foods) → name / kcal / protein / fat / carb / source  全部 NOT NULL = 是
插入 protein = NULL      → sqlite3.IntegrityError: NOT NULL constraint failed: foods.protein
库里 104 条数据完整重建，字段完整性得到强制保证
```

**4. 测试：22 → 32 条**

| 新增 | 内容 |
|---|---|
| `test_calc.py` +10 | 单条缩放、100g 边界、碳水为 0 保持 0、非法克数、缺失值快速失败、空列表汇总、双条汇总、缺口正负值、缺字段报错 |
| `test_db.py` +1 | **NOT NULL 约束生效**（营养字段为空时拒绝写入） |

**并做了变异测试**：临时去掉四个 `NOT NULL` 重建表 → **恰好 1 条失败**，正是 `test_foods_rejects_null_nutrient`（`Failed: DID NOT RAISE IntegrityError`）；还原后 32 passed。

**5. 设计文档升级 v1.2（已重新生成 PDF）**

- 2.4 节「营养值字段缺失」策略改写（原 `unknown_fields` 方案作废，改为入库拦截）
- **新增 4.1 节「当前数据现状与已知局限」**：13 条生值、3 条典型值、核验状态说明、以及面试话术
- 测试章节的「字段缺失」改为「NOT NULL 约束生效」

### 三、遇到的问题与解决过程

**问题 1：`calc_gap` 把三种营养素的克数相加当成了热量（量纲错误）**

- 现象：`total_kcal = protein_g + fat_g + carb_g` → `126 + 63 + 478.11 = 667.11`，而正确目标热量是 **2983.46**，相差 4.47 倍
- **后果是结论反向**：缺口显示 `kcal = -12.89`（看起来已超标），真实是 `+2303.46`（今天还能吃 2303 kcal）
- 根因：热量目标本就由 `calc_target_kcal` 提供、由 service 组装进 `target`；发现 target 里没有 `kcal` 时，应追问"谁该放进去"，而不是自己算一个
- 收获：**变量名带单位后缀（`protein_g` vs `kcal`）就是为了让你读等式时发现量纲不一致**。读一遍"126 克 + 63 克 + 478 克 = 667 千卡"，错误立刻可见

**问题 2：`sum_intake` 输出全 0.0 —— `else` 缩进绑错了 `if`**

- 现象：数据完整的情况下，四项合计全是 `0.0`
- 根因：`else` 与**内层** `if item['name'] not in unknown_items` 同缩进 → 绑定到内层。于是正常情况（`value is not None`）两个 `if` 都不进，**什么都不做**
- 附带：那个 `else` 分支唯一能进入的路径是"值为 None 且名字已在列表"，里面执行 `total[key] += None` —— 一个待爆的雷（实测 `TypeError`）
- 解决：不是把 `else` 挪回外层，而是**减少嵌套**——拆成两个平级的单层 `if`（一个记缺失、一个累加）
- 收获：**Python 的 `else` 绑定最近的、同缩进的 `if`；改缩进即改语义，且没有语法错误可依赖。** 根本对策是让嵌套消失

**问题 3：传参类型错——`sum_intake(dict)` 而不是 `list[dict]`**

- 现象：`TypeError: string indices must be integers, not 'str'`
- 根因：`for x in dict` 拿到的是 **key（字符串）**，所以 `food['kcal_g']` 实际是 `'name'['kcal_g']`
- **附带发现**：这个 bug 的报错行更靠前，**把问题 2 完全挡住了**——修好一个才看到下一个
- 收获：调试要**从外往里修**，一次只改最靠前的那处。另外**自测代码本身也是代码**，`__main__` 里传错参数一样要审

**问题 4：改契约后测试立刻失败——这次是好事**

- 现象：删掉 None 处理后，`test_calc_food_intake` 失败（它断言的是旧契约：`gram` / `kcal_g` / None 降级）
- **意义：这正是测试的价值。** 契约一变就报警，强迫你做显式决策（改测试还是改代码），而不是让行为悄悄漂移
- 处理：重写为新契约的 10 条用例，并**新增一条 `test_food_intake_missing_value_fails_fast`**，把"不处理缺失"这个决定固化成可执行的断言

**其他已确认（一行记）**

- **不能用 `and`/`or` 短路求值替代 None 判断**：`0.0 or None → None`，会把真值为 0 的营养素（鸡胸肉的碳水）静默吃掉
- `pytest.approx` 支持 dict 整体比较且语义严格（键缺失/多余均判 False，浮点微差判 True）
- 改 schema 时用 `DROP TABLE` + 重跑 `init_db` 比移动 `.db` 文件省事（文件可能被进程占用）
- SQLite **不支持直接修改列约束**，加 `NOT NULL` 后若将来要改回允许 NULL，需重建表

### 四、可迁移的规则（今天沉淀下来的）

1. **数据完整性交给约束，不交给约定**：`NOT NULL` 比"我们会保证"可靠，失败时机也更早
2. **上游保证的事，下游不重复防御**——但要先确认上游**真的**保证了（靠约束，而非口头承诺）
3. **不写不存在的分支**：留着"可能有用"的缺失值处理，会误导后来者以为数据可能缺失；代码本身就是文档
4. **单位运算前先读一遍等式两边的量纲**是否一致
5. **`else` 必须与配对的 `if` 左对齐**；更根本的是减少嵌套（平级单层 if / continue）
6. **`for x in dict` 得到 key，`for x in list` 得到元素**——同一语法两种语义
7. **改契约时测试失败是功能不是故障**；失败后要显式决策，并把决策写成用例
8. **会误报的检查比没有检查更糟**——它会训练人忽略告警
9. **调试从外往里**：一次只修最靠前的错误，因为后面的错误常被前面的掩盖

### 五、今天产出的面试素材

- **数据完整性策略的完整推理链**：为什么用 `NOT NULL` 而不是上层校验、为什么据此删掉计算层的缺失处理、**这个策略的前提是什么、前提何时会失效**（V2 接入允许字段缺失的外部 API 时）。能讲清"策略 + 前提 + 前提失效怎么办"，比讲"我加了非空约束"有分量
- **量纲错误的杀伤力**：`protein_g + fat_g + carb_g` 当成 kcal——格式合法、数值看似合理，**结论完全反向**（告诉用户"已超标"而实际还能吃 2303 kcal）
- **测试作为契约守门人**：改契约 → 测试失败 → 显式决策 → 决策固化成用例。这条比"我有 32 个测试"有说服力
- **变异测试**：去掉 `NOT NULL`，恰好 1 条失败且正是那条约束测试——证明测试不是空壳
- **不做某个检查的理由**：主动说"我评估过自洽性校验，但因为它有已知误报而放弃，改为依赖 source 字段的可追溯性"——**知道为什么不做什么，和知道做什么同样重要**
- **数据局限的诚实表述**（配合设计文档 4.1 的话术）：13 条只有生重值、3 条典型值、未逐条核验原文 → **"知道数据哪里不准，比声称数据都准更有说服力"**

---

## 2026-10-07（续）｜ 摄入记录数据层：intake 表 + 三个函数 + 测试

### 一、今日目标

在 `db` 层打通「记录摄入」的读写能力，为后续 `service.build_daily_report` 提供数据入口。范围：intake 表结构、三个数据层函数、配套测试。另外顺手修正 `foods` 表一个遗留的主键设计问题。

### 二、完成的事

**1. `foods` 主键修正：`PRIMARY KEY (name, source)` → `PRIMARY KEY (name)`**

原复合键预设了「同一食物可存多个来源版本」，但该能力从未被需求验证（104 条数据 `name` 全部唯一），且应用层根本用不了——`query_food(name) -> dict | None` 只能返回一行，`calc_food_intake` 也只需要一组确定性数字。改为 `name` 单主键后，唯一性由数据库保证，`query_food` 的语义变得明确。

连带修改两处（否则直接报错）：
- upsert 冲突目标：`ON CONFLICT(name, source)` → `ON CONFLICT(name)`
- `DO UPDATE SET` 列表补上 `source = excluded.source`——`source` 从主键成员变成普通列后，不放进 SET 就意味着「修正来源标签」会被静默丢弃

**2. intake 表**

```sql
CREATE TABLE IF NOT EXISTS intake (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT NOT NULL,
    food      TEXT NOT NULL,
    grams     REAL NOT NULL
)
```

设计取舍：
- **不存营养值快照**，只存「吃了什么、多少克」。营养值读 `foods` 表计算 → `db` 不依赖 `calc`，两层平行；且修正 `foods` 数值后历史记录自动跟随（单一事实来源）
- **`id` 保留**：用途不是「数据库规范要求」，而是**删除/定位单条记录**。实测两条完全相同的记录（同日同食物同克数），无 id 时 `DELETE WHERE date=? AND food=? AND grams=?` 会一次删掉两条
- **去掉 `meal`**：V1 的核心闭环是「当天摄入合计 vs 目标」，全天加总，从不按餐次分组
- **去掉 `created_at`**：`date` 回答「哪天」、`id` 回答「先后」，信息重合

**3. 三个函数 + 一个共用辅助函数**

| 函数 | 签名 | 职责 |
|---|---|---|
| `_normalize_date` | `(date: str) -> str` | 校验并规范化为 `YYYY-MM-DD`；`add_intake` 与 `list_intake_by_date` 共用 |
| `add_intake` | `(date, food_name, grams) -> int` | 三道校验（日期、克数 > 0、食物须在库中）后插入，返回新记录 id |
| `list_intake_by_date` | `(date) -> list[dict]` | 取某日全部记录，`ORDER BY id` 保证顺序稳定 |
| `delete_intake` | `(intake_id) -> int` | 按 id 删除，返回受影响行数 |

**4. 测试：22 → 46 条**

新增 14 条摄入用例，含三条**回归防线**：
- `test_add_intake_normalizes_date`（写入侧规范化）
- `test_list_intake_normalizes_date`（查询侧规范化）
- `test_delete_intake_only_removes_target`（重复记录下按 id 只删一条）

测试隔离用专属日期 `TEST_DATE = '1900-01-01'` + function scope 的 `clean_intake` fixture，**只删自己那天，绝不清空整表**（保护将来录入的真实数据）。

**5. 变异测试（验证测试不是空壳）**

| 植入的缺陷 | 结果 |
|---|---|
| `list_intake_by_date` 跳过规范化 | 恰好 1 条失败：`test_list_intake_normalizes_date` ✓ |
| `delete_intake` 把 `WHERE id = ?` 改成 `WHERE id >= ?` | 恰好 1 条失败：`test_delete_intake_only_removes_target` ✓ |
| 还原后 | 46 passed ✓ |

**6. 端到端联调（提前验证块 3 的链路）**

用 3 条记录跑通 `list_intake_by_date → query_food → calc_food_intake → sum_intake → calc_gap`：

```
鸡胸肉 200g + 白米饭 150g + 鸡蛋 100g
当天合计：kcal 680.0  | 蛋白 78.65g | 脂肪 18.25g | 碳水 43.4g
目标    ：kcal 2983.46| 蛋白 126.0g | 脂肪 63.0g  | 碳水 478.11g
缺口    ：kcal 2303.46| 蛋白 47.35g | 脂肪 44.75g | 碳水 434.71g
```

结论：`db` 层与 `calc` 层的接口完全对齐（键名、量纲、单位均一致）。

### 三、遇到的问题与解决过程

**问题 1：一个字符串里写两条 `CREATE TABLE` 跑不通**

- 现象：`sqlite3.OperationalError: near "CREATE": syntax error`
- 三个叠加的问题：
  1. 两条语句之间**缺分隔符 `;`**
  2. 列定义末尾多了**尾逗号**（`grams REAL NOT NULL,` 后直接 `)`）→ SQL 不允许，与 Python 元组的习惯相反
  3. **即使补上分号也不行**——Python `sqlite3` 的 `cursor.execute()` **一次只能执行一条语句**，加 `;` 后报 `ProgrammingError: You can only execute one statement at a time.`
- 解决：拆成**两个字符串 + 两次 `cursor.execute()`**（`conn.executescript()` 也可行，但它会隐式 commit 且不返回 cursor，与现有 `try/finally + cursor.close()` 结构不合）
- 收获：**`cursor.execute` 是「执行一条语句」，不是「执行一段脚本」**

**问题 2：改了 schema 却直接跑 `init_db`，报 `ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint`**

- 现象：代码里主键已改成 `(name)`，但插入时报冲突目标不存在
- 原因：`CREATE TABLE IF NOT EXISTS` **见到表已存在就整段跳过、不做任何结构变更** → 库里仍是旧主键 `(name, source)`，而 `ON CONFLICT(name)` 找不到对应约束
- 解决：`DROP TABLE IF EXISTS foods` → 重跑 `init_db` 重建
- 收获：**`CREATE TABLE IF NOT EXISTS` 不是迁移工具**。它只保证「表存在」，不保证「表结构正确」。改 schema 必须显式 `DROP`（重建）或 `ALTER`（改列）。这个坑当天在 intake 表和 foods 表上各踩了一次

**问题 3：`delete_intake` 里的 `if cursor.execute(...) is not None:` 是死分支**

- 现象：删不到记录时也能正常返回 0，看起来没问题
- 原因：`cursor.execute()` 返回的是**游标本身**，永远不是 `None` → `if` 恒为真，`else` 分支一次都不会执行；而且两个分支做的事完全相同
- 解决：删掉 if/else，直接 `cursor.execute(...)` + `conn.commit()` + `return cursor.rowcount`（无匹配时 rowcount 自然为 0）
- 收获：**不需要判断「执行是否成功」**——失败会抛异常，走不到 return；成功与否看 `rowcount` 就够了

**问题 4：`__main__` 自测块硬编码删除 id 1~8**

- 原因：`for r in range(1, 9): delete_intake(r)`——写死了记录 id
- 风险：当前因 `AUTOINCREMENT` 已推进到 10 而无实际删除，但**数据库一旦重建（id 从头开始）就会删掉刚录入的前 8 条真实记录**
- 解决：改为非破坏性演示（专属日期 + 自己造自己删）
- 收获：**自测块也是会写数据库的代码**，任何「删除/清空」操作都不该写死在脚本里

**一行记**

- **`DO UPDATE SET` 漏列**：`source` 从主键降为普通列后忘了加进 SET 列表——不报错，但会使该列的修正静默失效
- **复合键的来源**：`(name, source)` 是我早期给的示例里带进来的，理由（支持多来源）从未被验证；`source` 是**属性**不是**身份**，本就不该进主键
- **变异测试自身要验证**：第一次做变异时替换串没匹配上（变量已改名），脚本仍打印「已植入」，测试显示 46 passed，**看起来像「测试没抓住」，实际是变异没生效**。变异测试的第一步必须是「确认缺陷真的植入」
- **多行命令不要跨行粘贴**：终端会把首行 `python.exe -c "` 与后续代码拆开，导致参数被当成命令执行

### 四、可迁移的规则（本段沉淀）

1. **主键 = 实体的身份标识，属性不进主键。** 定主键的标准动作是自问「这个实体靠什么唯一区分」
2. **`CREATE TABLE IF NOT EXISTS` 不是迁移工具**——改 schema 必须显式 DROP 或 ALTER
3. **`cursor.execute()` 一次只能执行一条语句**，多条要用多次 execute 或 `executescript`
4. **同一格式契约要在两端都做**：写入侧规范化保证库内格式唯一，读取侧规范化保证查询串能对上——只做一端不成立
5. **`finally` 里只关闭在 try 之前就已创建的资源**（沿用自 9-22）
6. **自测块不得包含破坏性操作**（硬编码 id 的删除、清空整表）
7. **变异测试的第一步是确认缺陷真的植入**，否则会得出反向结论
8. **不存快照 = 单一事实来源**：intake 只记事实，营养值查 `foods` 计算，避免两处数字

### 五、今天产出的面试素材

- **「为什么表里需要 id」**：不是因为「数据库规范」，而是**删除/定位单条记录**需要。用「两条完全相同的记录，无 id 时删一条会删掉两条」这个具体场景回答，比背主键定义有说服力
- **「主键怎么定」**：先问「这个实体靠什么唯一区分」。食物靠名称唯一 → `PRIMARY KEY (name)`；`source`（数值来源）是属性不是身份。**反例**：把属性塞进主键，会让「属性变了」变成「这是一条新记录」，并让「按名称取一条」的调用方面临「该取哪条」的无解问题
- **「数据库表结构怎么维护/迁移」**：V1 用 DROP + 重导（数据源是 CSV，可完全重建）；生产环境会用 Alembic 这类迁移工具，因为不能丢数据。可以补一句**踩过的坑**：「`CREATE TABLE IF NOT EXISTS` 不是迁移工具，它连结构不一致都不会告诉你」
- **「为什么不存营养值快照」**：单一事实来源——改 `foods` 数值后历史记录自动跟随；同时避免 `db` 依赖 `calc`（破坏分层）。生产环境（如 MyFitnessPal）倾向存快照以求「历史不可变」，切换成本很低（加几个字段即可）
- **日期为什么既校验又规范化**：数据库 `date` 是 TEXT，`WHERE date = ?` 是**字符串全等比较**。只校验不规范化 → 传 `'2026-1-1'` 时静默返回空列表，调用方无法区分「这天没记录」和「格式传错」——**静默错误比报错难查得多**
- **测试作为设计的固化**：`test_delete_intake_only_removes_target` 把一个架构决策（为什么需要 id）固化成了断言；将来有人想删掉 id，这条测试会告诉他删了会出什么问题
