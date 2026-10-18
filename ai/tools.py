from db import query_food, search_foods
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from service import build_daily_report
import json




@dataclass
class UserCtx:
    target: dict
    today: str

@tool
def today_report(runtime: ToolRuntime[UserCtx]) -> str:
    """查询【今天】的已摄入营养与目标缺口。用户问“今天/目前/还剩多少”时使用。无参数。"""
    r = build_daily_report(runtime.context.today, runtime.context.target)
    return json.dumps(r, ensure_ascii=False)

@tool
def report_by_date(date: str, runtime: ToolRuntime[UserCtx]) -> str:
    """查询【某个指定日期】的摄入与缺口。仅当用户明确说出日期时使用。date 必须是 YYYY-MM-DD。"""
    try:
        r = build_daily_report(date, runtime.context.target)
    except ValueError:
        return f"日期 {date} 格式不合法，请转换为 YYYY-MM-DD 后重试。"
    return json.dumps(r, ensure_ascii=False)

@tool
def search_foods_tool(keyword: str) -> str:
    """按关键词模糊搜索食物库，返回名称包含关键词的食物及营养数据。
    当用户提到不完整的食物名称时使用；已知完整名称请改用 query_food_tool。"""
    return json.dumps(search_foods(keyword), ensure_ascii=False)

@tool
def query_food_tool(name: str) -> str:
    """按完整名称精确查询单个食物的营养数据。仅在已知确切名称时使用。"""
    return json.dumps(query_food(name), ensure_ascii=False)



