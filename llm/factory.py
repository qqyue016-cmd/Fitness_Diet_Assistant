import os
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from utils.config_tool import config_llm

def _get_api_key() -> str:
    env_name = config_llm["provider"]["api_key_env"]
    key = os.getenv(env_name)
    if not key:
        raise RuntimeError(f"环境变量 {env_name} 未设置，无法初始化模型")
    return key

@lru_cache(maxsize=None)
def get_chat_model(role: str='default'):
    if role not in config_llm['chat']:
        raise RuntimeError(f"未定义角色 {role},可用 {list(config_llm['chat'])}")
    cfg = config_llm["chat"][role]
    return ChatOpenAI(
        model=cfg["model"],
        base_url=config_llm["provider"]["base_url"],
        api_key=_get_api_key(),
        temperature=cfg.get("temperature", 0),
        streaming=cfg.get("streaming", True),
        max_retries=cfg.get("max_retries", 2),
    )

@lru_cache(maxsize=None)
def get_embedding_model():
    cfg = config_llm["embedding"]
    return OpenAIEmbeddings(
        model=cfg["model"],
        base_url=config_llm["provider"]["base_url"],
        api_key=_get_api_key(),
        chunk_size=cfg["chunk_size"],
        check_embedding_ctx_length=False,  # 非 OpenAI 服务必须关掉
    )


