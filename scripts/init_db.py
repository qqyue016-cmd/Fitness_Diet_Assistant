from utils.path_tool import get_abs_path
from utils.config_tool import config_foods_data
from db import create_table, insert_data
import csv

def get_data():
    data = []
    with open(get_abs_path(config_foods_data['foods_data_path']),'r',encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        # 跳过表头
        next(reader)
        for r in reader:
            data.append((
                r[0],
                float(r[1]) if r[1].strip() else None,
                float(r[2]) if r[2].strip() else None,
                float(r[3]) if r[3].strip() else None,
                float(r[4]) if r[4].strip() else None,
                r[5],
            ))
    return data

def init_table():
    create_table()
    data = get_data()
    n = insert_data(data)
    print(f'数据导入成功,导入了{n}条数据')

if __name__ == '__main__':
    init_table()