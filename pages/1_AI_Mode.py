import streamlit as st
from datetime import datetime
from ai.agent import chat_stream
from ai.pipeline import AIServiceError
from utils.logger_tool import logger
from rag.rag_service import parse_sources

st.title("问问 AI")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

plan = st.session_state.get("plan")
if plan is None:
    st.info("请先在主页生成计划")
else:
    history = st.session_state["chat_history"]

    for m in history:
        with st.chat_message(m["role"]):
            st.write(m["content"])
            if m.get("sources"):
                with st.expander(f"📖 参考资料（{len(m['sources'])} 条）"):
                    for s in m["sources"]:
                        st.markdown(f"**[{s['idx']}] {s['doc']} · {s['section']}**　\n{s['source']}")


    prompt = st.chat_input("问点什么…")
    if prompt:
        history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            box = st.empty()
            hint = st.empty()
            buf = ""
            source = []
            try:
                for ev in chat_stream(history, plan["target"],
                                      datetime.now().strftime("%Y-%m-%d"),
                                      st.session_state.get("goal_label", "")):
                    if ev["type"] == "text":
                        buf += ev["content"]
                        box.markdown(buf)

                    elif ev["type"] == "tool":
                        label = {"search_knowledge": "📚 查询营养知识库",
                                 "today_report": "📊 查询今日摄入",
                                 "search_foods_tool": "🔍 搜索食物库"}.get(ev["name"], f"调用 {ev['name']}")
                        hint.caption(label)
                    elif ev['type'] == "tool_result":
                        if ev["name"] == "search_knowledge":
                            source.append(ev["content"])
                hint.empty()

                if source:
                    sources = parse_sources("\n".join(source))
                    with st.expander("📖 参考资料"):
                        for s in sources:
                            st.markdown(f"**[{s['idx']}] {s['doc']} · {s['section']}**　\n{s['source']}")

            except Exception:
                logger.exception("chat_stream failed")
                box.error("AI 服务出错了，请稍后重试。")
                history.pop()
            else:
                history.append({"role": "assistant", "content": buf, "sources": parse_sources("\n".join(source))})
