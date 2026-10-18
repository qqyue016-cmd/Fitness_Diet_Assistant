from langchain.agents import create_agent
from ai.client import chat_model
from ai.tools import UserCtx, today_report, report_by_date, search_foods_tool, query_food_tool

TOOLS = [today_report, report_by_date, search_foods_tool, query_food_tool]

SYSTEM_PROMPT = """你是健身饮食助手，帮用户查询食物营养和当日摄入情况。

今天日期：{today}

规则：
1. 凡涉及营养数值、摄入记录、目标缺口，必须调用工具查询，禁止凭记忆或常识作答。
2. 工具返回空或查不到时，如实说“库里没有”，不要编造数值。
3. 用户说“今天/目前/还剩多少”用 today_report；说出具体日期用 report_by_date。
4. 食物名不完整用 search_foods_tool；名称确定用 query_food_tool。
5. 不要自行计算营养数值，一律以工具返回为准。
6. 用中文回答，简洁直接。
"""

def _make_agent(today: str):
    """构建 agent。每次新建（实测约 1.7ms），确保提示词里的日期不会过期。"""
    return create_agent(
        model=chat_model,
        tools=TOOLS,
        context_schema=UserCtx,
        system_prompt=SYSTEM_PROMPT.format(today=today),
    )

def chat_stream(text: str, target: dict, today: str):
    """流式产出事件，供 UI 边收边渲染。

    {"type": "text",        "content": "鸡"}                 模型输出的文字片段
    {"type": "tool",        "name": "query_food_tool", "id": "call_xxx"}
    {"type": "tool_result", "content": "[{...}]", "id": "call_xxx"}
    """
    agent = _make_agent(today)

    for chunk, meta in agent.stream(
        {"messages": [{"role": "user", "content": text}]},
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
    for ev in chat_stream("鸡胸肉多少卡", {"kcal": 2983.46, "protein_g": 126, "fat_g": 63, "carb_g": 478}, "2026-10-18"):
        if ev["type"] == "text":
            print(ev["content"], end="", flush=True)
        else:
            print(f"\n[{ev['type']} {ev.get('name', '')}]")


