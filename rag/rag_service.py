import re
from rag.vector_store import VectorStoreService

vector = VectorStoreService()

def search(query: str) -> list[dict]:
    """调 retriever，返回 [{chunk_id, content, doc_title, section, source}]"""
    result = vector.get_retriever().invoke(query)
    result_list = []
    for hit in result:
        result_list.append({
            "chunk_id": hit.metadata["chunk_id"],
            "content": hit.page_content,
            "doc_title": hit.metadata["doc_title"],
            "section": hit.metadata["section"],
            "source": hit.metadata["source"].splitlines()[0].strip(),
        })
    return result_list

def build_context(hits: list[dict]) -> str:
    """拼成带编号的上下文"""
    context = ""
    for i, hit in enumerate(hits,1):
        context += f"[{i}] {hit['content']}\n来源：{hit['source']}\n"
    return context

def parse_sources(context: str) -> list[dict]:
    """从 build_context 的产物中提取参考资料。

    与 build_context 是同一个契约的两端，修改格式时必须同处更新。
    返回：[{"idx": 1, "doc": "...", "section": "...", "source": "..."}]
    """
    out = []
    for line in context.splitlines():
        line = line.strip()
        m = re.match(r"\[(\d+)\]\s*【(.+?)】",line)
        if m:
            doc, _, section = m.group(2).partition(" > ")
            out.append({
                "idx": int(m.group(1)),
                "doc": doc.strip(),
                "section": section.strip(),
                "source": "",
            })
        elif line.startswith("来源：") and out:
            out[-1]["source"] = line[len("来源："):].strip()
    return out

def search_nutrition_knowledge(query: str) -> str:
    """search + build_context 的对外入口，返回 str"""
    return build_context(search(query))

if __name__ == '__main__':
    hits = search("减脂期蛋白质吃多少")
    print(len(hits), len(build_context(hits)))
    print(search_nutrition_knowledge("减脂期脂肪供能比多少")[:200])