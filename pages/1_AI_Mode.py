import streamlit as st
from datetime import datetime

from ai.agent import chat_stream
from ai.pipeline import AIServiceError
from utils.logger_tool import logger

st.title("问问 AI")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

plan = st.session_state.get("plan")
if plan is None:
    st.info("请先在主页生成计划")
else:
    history = st.session_state["chat_history"]

    for m in history:
        st.chat_message(m["role"]).write(m["content"])

    prompt = st.chat_input("问点什么…")
    if prompt:
        history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            box = st.empty()
            buf = ""
            try:
                for ev in chat_stream(history, plan["target"],
                                      datetime.now().strftime("%Y-%m-%d"),
                                      st.session_state.get("goal_label", "")):
                    if ev["type"] == "text":
                        buf += ev["content"]
                        box.markdown(buf)
            except Exception:
                logger.exception("chat_stream failed")
                box.error("AI 服务出错了，请稍后重试。")
                history.pop()
            else:
                history.append({"role": "assistant", "content": buf})
