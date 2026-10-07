import sqlite3
from utils.config_tool import config_sqlite
from utils.path_tool import get_abs_path
from datetime import datetime

# 获取数据库连接
def get_connect():
    conn = sqlite3.connect(get_abs_path(config_sqlite['DB_PATH']))
    conn.row_factory = sqlite3.Row
    return conn

# 创建数据库表
def create_table():
    conn = get_connect()
    cursor = conn.cursor()
    try:
        # 四个营养字段均为 NOT NULL：
        # 数据完整性由本约束（而非上层校验）保证，因此 calc 层不做缺失值处理。
        # 若将来数据源变更（如接入外部 API 且允许字段缺失），需同步放开此处并恢复上层处理。
        food_table = f'''
        CREATE TABLE IF NOT EXISTS {config_sqlite['TABLE_NAME']} (
            name    TEXT NOT NULL,
            kcal    REAL NOT NULL,
            protein REAL NOT NULL,
            fat     REAL NOT NULL,
            carb    REAL NOT NULL,
            source  TEXT NOT NULL,
            PRIMARY KEY (name)
        );
        '''
        intake_table =f'''
        CREATE TABLE IF NOT EXISTS {config_sqlite['INTAKE_TABLE']} (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            date    TEXT NOT NULL,
            food    TEXT NOT NULL,
            grams   REAL NOT NULL
        );
        '''

        cursor.execute(food_table)
        cursor.execute(intake_table)
        conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f'创建数据库失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

#—————————— food_table ——————————————————————
# 插入数据
def insert_data(data):
    conn = get_connect()
    cursor = conn.cursor()
    try:
        sql_text = f'''
        INSERT INTO {config_sqlite['TABLE_NAME']} (name, kcal, protein, fat, carb, source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            kcal = excluded.kcal,
            protein = excluded.protein,
            fat = excluded.fat, 
            carb = excluded.carb,
            source  = excluded.source
        '''
        cursor.executemany(sql_text, data)
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        raise RuntimeError(f'插入数据失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

# 精确查询，返回一条或 None
def query_food(name: str) ->dict | None:
    """按名称精确查询单个食物。

        foods.name 为主键，同一名称只存在一行（来源版本唯一），
        故本函数最多返回一条记录。
    """
    conn = get_connect()
    cursor = conn.cursor()

    try:
        sql_text=f'''
        SELECT * FROM {config_sqlite['TABLE_NAME']}
        WHERE name = ?
        '''
        cursor.execute(sql_text, (name,))
        result = cursor.fetchone()
    except sqlite3.Error as e:
        raise RuntimeError(f'查询数据失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

    if result:
        return dict(result)
    else:
        return None

# 模糊查询，给 UI 搜索用
def search_foods(keyword: str) -> list[dict]:
    conn = get_connect()
    cursor = conn.cursor()

    try:
        sql_text = f'''
        SELECT * FROM {config_sqlite['TABLE_NAME']}
        WHERE name LIKE ? ORDER BY name
        '''
        result = cursor.execute(sql_text,(f"%{keyword}%",))
        return [dict(r) for r in result]
    except sqlite3.Error as e:
        raise RuntimeError(f'查询数据失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

#—————————— intake_table ——————————————————————
# 规范记录时间‘YYYY-MM-DD’
def _normalize_date(date: str) -> str:
    try:
        return datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError as e:
        raise ValueError('日期格式错误，应为 YYYY-MM-DD') from e

# 插入数据
def add_intake(date: str, food_name: str, grams: float) -> int:
    norm_date = _normalize_date(date)

    if grams <=0:
        raise ValueError(f'克数必须大于 0，收到：{grams}')
    if not query_food(food_name):
        raise ValueError('食品不存在')

    conn = get_connect()
    cursor = conn.cursor()
    try:
        sql_text = f'''
        INSERT INTO {config_sqlite['INTAKE_TABLE']} (date, food, grams)
        VALUES (?, ?, ?)
        '''
        cursor.execute(sql_text, (norm_date, food_name, grams))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        raise RuntimeError(f'插入数据失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

# 根据时间列出数据
def list_intake_by_date(date: str) -> list[dict]:
    norm_date = _normalize_date(date)

    conn = get_connect()
    cursor = conn.cursor()
    try:
        sql_text = f'''
        SELECT * FROM {config_sqlite['INTAKE_TABLE']}
        WHERE date = ?
        ORDER BY id
        '''
        result = cursor.execute(sql_text, (norm_date,))
        return [dict(r) for r in result]
    except sqlite3.Error as e:
        raise RuntimeError(f'列出数据失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

# 删除数据
def delete_intake(intake_id: int) -> int:
    conn = get_connect()
    cursor = conn.cursor()
    try:
        sql_text = f'''
        DELETE FROM {config_sqlite['INTAKE_TABLE']}
        WHERE id = ?
        '''
        cursor.execute(sql_text, (intake_id,))
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        raise RuntimeError(f'删除数据失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    today = '2000-01-01'  # 专属日期，不碰真实数据
    i = add_intake(today, '鸡胸肉', 200)
    print('新增:', i, list_intake_by_date(today))
    print('删除:', delete_intake(i))