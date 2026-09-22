import sqlite3
from utils.config_tool import config_sqlite
from utils.path_tool import get_abs_path

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
        sql_text = f'''
        CREATE TABLE IF NOT EXISTS {config_sqlite['TABLE_NAME']} (
            name    TEXT NOT NULL,
            kcal    REAL,
            protein REAL,
            fat     REAL,
            carb    REAL,
            source  TEXT NOT NULL,
            PRIMARY KEY (name, source)
        )
        '''

        cursor.execute(sql_text)
        conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f'创建数据库失败：{str(e)}') from e
    finally:
        cursor.close()
        conn.close()

# 插入数据
def insert_data(data):
    conn = get_connect()
    cursor = conn.cursor()
    try:
        sql_text = f'''
        INSERT INTO {config_sqlite['TABLE_NAME']} (name, kcal, protein, fat, carb, source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(name, source) DO UPDATE SET
            kcal = excluded.kcal,
            protein = excluded.protein,
            fat = excluded.fat, 
            carb = excluded.carb
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

if __name__ == '__main__':
    print(query_food("鸡胸肉"))
    print(search_foods("鸡"))