from uuid import main
from utils.config_tool import config_chroma
from rag.rag_service import search,build_context
from evals.dataset import real_cases

def eval_retrieval(cases: list) -> dict:
    """
        计算r@1, r@3, mrr

    返回 {
        "r@3": 0.967, "r@1": 0.900, "mrr": 0.9333,
        "per_case": [{"id":1, "gold":"01_s2", "retrieved":["01_s2",...], "hit_rank":1}, ...],
        "misses": [{"id":6, "gold":"02_s2", "retrieved":[...]}],
    }"""
    k = config_chroma['k']
    r1 = r3 = mrr = 0
    per_case = []
    misses = []

    for c in cases:
        hits = search(c['question'])
        retrieved = [h['chunk_id'] for h in hits]

        hit_rank = retrieved.index(c['gold_chunk']) + 1 if c['gold_chunk'] in retrieved else None

        r1 += 1 if hit_rank == 1 else 0
        r3 += 1 if hit_rank and hit_rank <= k else 0
        mrr += 1 / hit_rank if hit_rank else 0

        per_case.append({"id": c['id'], "gold": c['gold_chunk'],
                         "retrieved": retrieved, "hit_rank": hit_rank,
                         "context": build_context(hits)})
        if hit_rank is None:
            misses.append({"id": c['id'], "gold": c['gold_chunk'], "retrieved": retrieved})

    return {"k": k, "n_cases": len(cases),
            "r@1": r1/len(cases),
            "r@3": r3/len(cases),
            "mrr": mrr/len(cases),
            "per_case": per_case,
            "misses": misses
            }

if __name__ == '__main__':
    cases = real_cases()
    result = eval_retrieval(cases)
    print(f"k={result['k']}  n={result['n_cases']}")
    print(f"R@3  = {result['r@3']:.1%}")
    print(f"R@1  = {result['r@1']:.1%}")
    print(f"MRR  = {result['mrr']:.4f}")
    print(f"未命中 {len(result['misses'])} 题：")
    for m in result["misses"]:
        print(f"  id={m['id']}  gold={m['gold']}  got={m['retrieved']}")