import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from evals.dataset import real_cases
from evals.generation_eval import eval_generation, FAITHFUL_THRESHOLD
from evals.retrieval_eval import eval_retrieval
from utils.path_tool import get_abs_path

KEYWORDS = {
    "9 kcal": "脂肪能量密度（9 kcal/g）",
    "能量密度": "脂肪能量密度（9 kcal/g）",
    "激素": "激素/内分泌机制",
    "饱腹": "饱腹感机制",
    "gi": "升糖指数",
    "1.6": "蛋白质摄入量",
}


def aggregate_unsupported(details) -> list[dict]:
    counter = Counter()
    for d in details:
        for claim in d.get("unsupported", []):
            key = next((v for k, v in KEYWORDS.items() if k in claim.lower()), "其他")
            counter[key] += 1
    return [{"claim": k, "count": v} for k, v in counter.most_common()]


def merge_details(cases: list[dict], retrieval: dict, generation: dict) -> list[dict]:
    """按 id 合并检索层与生成层的结果，每题一条。"""
    c_map = {c["id"]: c for c in cases}
    r_map = {p["id"]: p for p in retrieval["per_case"]}
    g_map = {d["id"]: d for d in generation["details"]}

    merged = []
    for cid, r in r_map.items():
        c = c_map[cid]
        g = g_map.get(cid, {})          # 生成层可能缺题（失败时会记 error）
        merged.append({
            "id": cid,
            "question": c["question"],
            "type": c.get("type"),
            "difficulty": c.get("difficulty"),
            "gold": r["gold"],
            "retrieved": r["retrieved"],
            "hit_rank": r["hit_rank"],
            "faithfulness": g.get("faithfulness"),
            "unsupported": g.get("unsupported", []),
            "consistent": g.get("consistent"),
            "reason": g.get("reason", ""),
            "answer": g.get("answer", ""),
            "error": g.get("error"),
        })
    return sorted(merged, key=lambda x: x["id"])


def run(limit: int | None = None) -> dict:
    """跑完整评测（检索 + 生成），返回汇总结果。"""
    cases = real_cases()
    if limit:
        cases = cases[:limit]

    retrieval = eval_retrieval(cases)
    generation = eval_generation(cases, retrieval)

    return {
        "meta": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": "qwen-plus",
            "embedding": "text-embedding-v3",
            "k": retrieval["k"],
            "n_cases": len(cases),
            "faithful_threshold": FAITHFUL_THRESHOLD,
        },
        "retrieval": {key: retrieval[key] for key in ("r@1", "r@3", "mrr")},
        "generation": {key: generation[key] for key in ("faithfulness", "correctness", "matrix")},
        "misses": retrieval["misses"],
        "top_unsupported": aggregate_unsupported(generation["details"]),
        "per_case": merge_details(cases, retrieval, generation),
    }


def save(result: dict) -> Path:
    out_dir = Path(get_abs_path("evals/results"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def report(result: dict) -> None:
    m, r, g = result["meta"], result["retrieval"], result["generation"]
    print(f"模型 {m['model']} | embedding {m['embedding']} | k={m['k']} | {m['n_cases']} 题")
    print(f"\n检索层  R@3={r['r@3']:.1%}  R@1={r['r@1']:.1%}  MRR={r['mrr']:.4f}")
    print(f"生成层  faithfulness={g['faithfulness']:.2f}  correctness={g['correctness']:.2f}")
    print(f"\n矩阵    {g['matrix']}")
    print(f"未命中  {len(result['misses'])} 题")
    print(f"\n最常缺失的知识点：")
    for u in result["top_unsupported"]:
        print(f"  ×{u['count']}  {u['claim']}")


if __name__ == '__main__':
    import sys

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    result = run(limit=limit)
    report(result)
    print(f"\n结果已保存：{save(result)}")
