from langchain_community.chat_models.tongyi import ChatTongyi

chat_model = ChatTongyi(model='qwen-plus', temperature=0, max_retries=2, streaming=True)

