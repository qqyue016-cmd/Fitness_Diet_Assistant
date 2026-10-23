import os
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

chat_model = ChatOpenAI(
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0,
    streaming=True,
    max_retries=2,
)

embedding_model = OpenAIEmbeddings(
    model="text-embedding-v3",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    chunk_size=10,
    check_embedding_ctx_length=False,    # 非 OpenAI 服务必须关掉
)