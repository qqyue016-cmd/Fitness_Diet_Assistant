from langchain.agents import create_agent

from ai.client import chat_model
from ai.tools import UserCtx, today_report, report_by_date, search_foods_tool, query_food_tool

TOOLS = [today_report, report_by_date, search_foods_tool, query_food_tool]

SYSTEM_PROMPT = """你是健身饮食助手，帮用户查询食物营养和当日摄入情况。

今天日期：{today}

用户配置（系统已提供，直接采用，不要再询问）：
- 目标类型：{goal}
- 每日目标：热量 {kcal} kcal、蛋白质 {protein_g} g、脂肪 {fat_g} g、碳水 {carb_g} g

规则：
1. 凡涉及营养数值、摄入记录、目标缺口，必须调用工具查询，禁止凭记忆或常识作答。
2. 工具返回空或查不到时，如实说“库里没有”，不要编造数值。
3. 用户说“今天/目前/还剩多少”用 today_report；说出具体日期用 report_by_date。
4. 食物名不完整用 search_foods_tool；名称确定用 query_food_tool。
5. 不要自行计算。即使你知道目标值，也不能用目标减去“印象中的摄入量”——摄入量必须来自工具。
6. 用户说“我的目标是上面”“按上面的来”时，指的是上述已配置的配置，直接据此回答，不要让用户重复填写任何画像信息。
7. 需要调用工具时直接调用，不要输出“我来查一下”“请稍等”这类过渡语。
8. 用中文回答，简洁直接。
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
