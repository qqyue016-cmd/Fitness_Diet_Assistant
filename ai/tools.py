from db import query_food, search_foods,add_intake,delete_intake,list_intake_by_date
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from service import build_daily_report
from ai.guard import match_food,MAX_GRAMS
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


@tool
def add_meal(food: str, grams: float, runtime: ToolRuntime[UserCtx]) -> str:
    """把一条饮食记录写入今天。

    调用前必须同时满足：
    1. 食物名称已在库中唯一确定（先调 search_foods_tool 确认）
    2. 克数由用户明确给出或明确同意
    3. 用户已明确表达“记一下 / 帮我记”

    以上任一条件不确定时，不要调用，先向用户确认。
    """
    match = match_food(food)

    if match['status'] == 'ambiguous':
        names = "、".join(c["name"] for c in match['candidates'])
        return f"「{food}」无法唯一确定，候选有：{names}。请先与用户确认。"

    if match['status']  == 'not_found':
        return f"「{food}」未找到。请先与用户确认。"

    if grams is None or grams<=0:
        return f"「{food}」的克数未给出。请先与用户确认。"

    if grams>MAX_GRAMS:
        return f"「{food}」的克数 {grams} 超出限制。请先与用户确认。"

    name = match['candidates'][0]['name']

    # 防重复：最后一条若完全相同，视为重复提交
    row = list_intake_by_date(runtime.context.today)
    if row and str(row[-1]['food']) == name and abs(row[-1]['grams'] - grams) < 0.01 :
        return f"「{name} {grams:g}」已记录，请勿重复提交。"

    new_id = add_intake(runtime.context.today, name, grams)
    report = build_daily_report(runtime.context.today, runtime.context.target)
    return (f"已记录：{name} {grams:g}g。今天共 {len(report['items'])} 条，"
            f"已摄入 {report['total']['kcal']:.0f} kcal。"
            f"（内部 id={new_id}，回复用户时不要提及）")

@tool
def delete_meal(record_id: int, runtime: ToolRuntime[UserCtx]) -> str:
    """删除一条饮食记录。

    record_id 必须来自 today_report / report_by_date 返回的 items[].id，
    禁止自己编造数字。

    调用前必须：
    1. 先调用 today_report 查出当天的记录明细
    2. 若有多条同名食物，先向用户确认具体是哪一条
    3. 目标唯一确定后才能调用
    """
    rows = list_intake_by_date(runtime.context.today)
    target = next((r for r in rows if r['id'] == record_id), None)

    delete = delete_intake(record_id)
    if delete == 0:
        return "没有找到对应记录，可能已被删除。"

    report = build_daily_report(runtime.context.today, runtime.context.target)
    name = f"{target['food']} {target['grams']:g}g" if target else "该记录"
    return (f"已删除: {name}，今日还剩{len(report['items'])}条记录。"
            f"已摄入{report['total']['kcal']:.0f}kcal。")