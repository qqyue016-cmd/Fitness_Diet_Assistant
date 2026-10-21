import os
from langchain_openai import ChatOpenAI

chat_model = ChatOpenAI(
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0,
    streaming=True,
    max_retries=2,
)

