from rag.rag_service import search,parse_sources,build_context

def test_parse_sources_roundtrip():
    """build_context 的产物必须能被 parse_sources 完整还原。"""
    hits = search("减脂期蛋白质吃多少")
    parsed = parse_sources(build_context(hits))
    assert len(parsed) == len(hits)
    assert parsed[0]["doc"] and parsed[0]["source"]
