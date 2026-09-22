'''
配置处理工具
'''

import yaml
from utils.path_tool import get_abs_path


def load_sqlite_config(config_path: str=get_abs_path('config/SQLite.yaml'),encoding: str='utf-8'):
    with open(config_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

def load_foods_config(config_path: str=get_abs_path('config/foods.yaml'),encoding: str='utf-8'):
    with open(config_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

def load_calc_config(config_path: str=get_abs_path('config/calc.yaml'),encoding: str='utf-8'):
    with open(config_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

config_sqlite = load_sqlite_config()
config_foods_data = load_foods_config()
config_calc = load_calc_config()
