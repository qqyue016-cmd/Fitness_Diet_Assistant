from langchain_community.chat_models.tongyi import ChatTongyi

chat_model = ChatTongyi(model='qwen3.8-flash', temperature=0, max_retries=2)

