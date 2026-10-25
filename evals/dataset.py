import json

from rag.vector_store import VectorStoreService
from utils.path_tool import get_abs_path
from utils.config_tool import config_evals

_existing_ids = None

def _get_existing_ids() -> set[str]:
    global _existing_ids
    if _existing_ids is None:
        raw = VectorStoreService().chroma.get(include=["metadatas"])
        _existing_ids = {m["chunk_id"] for m in raw["metadatas"]}
    return _existing_ids


def load_cases(path: str | None = None) -> list[dict]:
    """加载评测集，并校验必填字段与 gold_chunk 是否存在。"""
    path = path or get_abs_path(config_evals["data_path"])
    cases = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        out = json.load(f)
        for case in out['cases']:
            cases.append(case)
        return cases


def check_dataset(cases: list[dict], valid_chunk_ids: set[str]) -> list[str]:
    """返回问题列表，空列表表示校验通过。"""
    problem = []

    # 1. 必填字段
    for c in cases:
        for field in {'id', 'question', 'gold_chunk', 'ground_truth'}:
            if not c.get(field):
                problem.append(f"{c.get('id')}字段 {field} 缺失")

    # 2. id 唯一
    ids = [c['id'] for c in cases]
    if len(ids) != len(set(ids)):
        problem.append("id 不唯一\n")
    # 3. gold_chunk 必须真实存在
    for c in cases:
        if c['gold_chunk'] not in valid_chunk_ids:
            problem.append(f"id={c.get('id')}的gold_chunk={c.get('gold_chunk')}不在向量库中")

    return problem

def real_cases():
    cases = load_cases()
    problems = check_dataset(cases, _get_existing_ids())
    if not problems:
        return cases
    else:
        raise ValueError(f"评测集校验失败: {problems}")


if __name__ == '__main__':
    cases = load_cases()
    print(f"评测集: {len(cases)} 题")
    print(f"首题: {cases[0]['id']} | {cases[0]['question'][:20]}")

    problems = check_dataset(cases, _get_existing_ids())
    print(f"校验: {'通过' if not problems else problems}")