from langchain.agents import create_agent

from ai.client import chat_model
from ai.tools import UserCtx, today_report, report_by_date, search_foods_tool, query_food_tool,add_meal, delete_meal

TOOLS = [today_report, report_by_date, search_foods_tool, query_food_tool, add_meal, delete_meal]

SYSTEM_PROMPT =  """你是健身饮食助手，帮用户查询与记录饮食。

今天日期：{today}

用户配置（系统已提供，不要询问）：
- 目标类型：{goal}
- 每日目标：热量 {kcal} kcal、蛋白质 {protein_g} g、脂肪 {fat_g} g、碳水 {carb_g} g

【最高优先级】
1. 收到任何食物名称，第一步必须调用工具查询，禁止在查询前向用户反问或作答。
   - 食物名 → search_foods_tool 或 query_food_tool
   - 当天摄入/缺口 → today_report；指定日期 → report_by_date
2. 查询结果决定下一步：
   - 唯一命中 → 直接给出数据或记录建议
   - 多命中 → 列出候选让用户选
   - 未命中 → 明确说「库里没有 X，无法记录」，不要用相近食物替代
3. 食物名称以库中条目为准，不要引入库里没有的维度（做法、品种、品牌、生熟）。
4. 不要自行计算营养数值，一律以工具返回为准。
5. 克数缺失时再问克数；克数已给出时不要再问做法或品种。
6. 当用户输入不明确克数与食物名字，如‘一碗’米饭，优先调用search_foods_tool 或 query_food_tool确定准确的食物名称，
   再询问是否记得具体克数，如不记得，则给用户三个选项：
    小碗（150g）
    中碗（200g）
    大碗（250g）
7. 需要调用工具就直接调用，不要输出「正在查询…」这类过渡语。
8. 写入记录前确认：食物唯一命中、克数已知、用户明确要求记录。任一不确定先问。
9. 删除记录前必须先调 today_report 查出当天明细并取得 id；多条同名记录必须让用户确认。
10. 中文回答，简洁直接，一定不要提及内部 id。
"""

def _make_agent(today: str, target: dict, goal: str):
    """构建 agent。每次新建（实测约 1.7ms），确保提示词里的日期不会过期。"""
    return create_agent(
        model=chat_model,
        tools=TOOLS,
        context_schema=UserCtx,
        system_prompt=SYSTEM_PROMPT.format(today=today, goal=goal, **target),
    )


def chat_stream(messages: list[dict], target: dict, today: str, goal: str = ""):
    """流式产出事件，供 UI 边收边渲染。

    {"type": "text",        "content": "鸡"}                 模型输出的文字片段
    {"type": "tool",        "name": "query_food_tool", "id": "call_xxx"}
    {"type": "tool_result", "content": "[{...}]", "id": "call_xxx"}
    """
    agent = _make_agent(today, target, goal)

    for chunk, meta in agent.stream(
            {"messages": messages},
            context=UserCtx(target=target, today=today),
            stream_mode="messages",
    ):
        node = meta.get("langgraph_node")

        if node == "model":
            # 模型输出的文字（工具调用轮次 content 为空，自动跳过）
            if chunk.content:
                yield {"type": "text", "content": chunk.content}

            # 工具调用决定（分片到达，只有首片带 name）
            for c in (getattr(chunk, "tool_call_chunks", None) or []):
                if c.get("name"):
                    yield {"type": "tool", "name": c["name"], "id": c.get("id")}

        elif node == "tools":
            yield {
                "type": "tool_result",
                "content": chunk.content,
                "id": getattr(chunk, "tool_call_id", None),
            }


if __name__ == '__main__':
    TARGET = {"kcal": 2983.46, "protein_g": 126.0, "fat_g": 63.0, "carb_g": 478.11}
    TODAY = "2026-10-18"


    def run(msgs, label):
        print(f"\n{'=' * 8} {label}")
        buf = ""
        for ev in chat_stream(msgs, TARGET, TODAY, goal="增肌"):
            if ev["type"] == "text":
                buf += ev["content"]
                print(ev["content"], end="", flush=True)
        print()
        return buf


    # 第一轮
    history = [{"role": "user", "content": "鸡胸肉多少卡"}]
    ans1 = run(history, "第 1 轮：鸡胸肉多少卡")

    # 第二轮：带上历史，问“它”
    history += [{"role": "assistant", "content": ans1},
                {"role": "user", "content": "那它蛋白质多少？"}]
    run(history, "第 2 轮（带历史）：那它蛋白质多少？")

    # 对照组：不带历史，直接问同一句
    run([{"role": "user", "content": "那它蛋白质多少？"}], "对照组（无历史）：那它蛋白质多少？")
