from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ai.client import chat_model
from evals.retrieval_eval import eval_retrieval
from utils.logger_tool import logger

FAITHFULNESS_PROMPT = """对【回答】中的每个事实性结论，判断【参考资料】中是否有**明确依据**。

判断标准：能否从参考资料里找到直接支持该结论的原句。
- 能找到 → 计入 supported
- 找不到 → 列入 unsupported_claims，并注明「资料未提及」
- **即使该结论本身正确、符合常识或你的已有知识，只要参考资料未明确写出，就必须算 unsupported**

参考资料：
{context}

回答：
{answer}

只输出 JSON，不要解释文字：
{{"supported_ratio": 0.75, "unsupported_claims": ["1g 脂肪 = 9 kcal（资料未提及能量密度）"]}}
"""

CORRECTNESS_PROMPT = """判断【回答】与【标准答案】在语义上是否一致。不要求措辞相同，只要关键数值与结论一致即可。

标准答案：
{ground_truth}

回答：
{answer}

只输出 JSON，不要任何解释文字：
{{"consistent": true, "reason": "核心数值 1.6~2.2 g/kg 一致"}}
"""

GENERATE_PROMPT = """你是健身饮食助手。请根据以下参考资料回答用户问题。

参考资料：
{context}

问题：{question}

要求：回答简洁直接，数值与结论以参考资料为准。"""


def generate_answer(question: str, context: str) -> str:
    """基于上下文生成回答（1 次 LLM 调用）。"""
    prompt = ChatPromptTemplate.from_template(GENERATE_PROMPT)
    chain = prompt | chat_model
    return chain.invoke({"context": context, "question": question}).content


def judge_faithfulness(context: str, answer: str) -> dict:
    """返回 {"supported_ratio": float, "unsupported_claims": list[str]}。"""
    prompt = ChatPromptTemplate.from_template(FAITHFULNESS_PROMPT)
    output_parser = JsonOutputParser()
    chain = prompt | chat_model | output_parser
    return chain.invoke({"context": context, "answer": answer})


def judge_correctness(ground_truth: str, answer: str) -> dict:
    """返回 {"consistent": bool, "reason": str}。"""
    prompt = ChatPromptTemplate.from_template(CORRECTNESS_PROMPT)
    output_parser = JsonOutputParser()
    chain = prompt | chat_model | output_parser
    return chain.invoke({"ground_truth": ground_truth, "answer": answer})


FAITHFUL_THRESHOLD = 0.9


def _aggregate(details, n_cases, failures) -> dict:
    valid = [d for d in details if "error" not in d]
    if not valid:
        return {"n_cases": n_cases, "n_failures": failures, "faithfulness": 0,
                "correctness": 0, "matrix": {}, "details": details}

    matrix = {"faithful_correct": 0, "faithful_wrong": 0,
              "unfaithful_correct": 0, "unfaithful_wrong": 0}
    for d in valid:
        f = "faithful" if d["faithfulness"] >= FAITHFUL_THRESHOLD else "unfaithful"
        c = "correct" if d["consistent"] else "wrong"
        matrix[f"{f}_{c}"] += 1

    return {
        "n_cases": n_cases,
        "n_valid": len(valid),
        "n_failures": failures,
        "faithfulness": sum(d["faithfulness"] for d in valid) / len(valid),
        "correctness": sum(1 for d in valid if d["consistent"]) / len(valid),
        "matrix": matrix,
        "details": details,
    }


def _as_bool(v) -> bool:
    """judge 可能返回 true / "true" / "是"，统一成 bool。"""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "是", "yes", "1"}


def eval_generation(cases, retrieval_result) -> dict:
    """串联三者，返回聚合指标 + 每题明细。"""
    lookup = {p["id"]: p for p in retrieval_result["per_case"]}

    details = []
    failures = 0

    for i, case in enumerate(cases, 1):
        cid = case['id']
        ctx = lookup[cid]["context"]
        try:
            answer = generate_answer(case["question"], ctx)
            faith = judge_faithfulness(ctx, answer)
            corr = judge_correctness(case["ground_truth"], answer)
        except Exception as e:
            logger.warning(f"id={cid} 评测失败：{e}")
            failures += 1
            details.append({"id": cid, "error": str(e)})
            print(f"[{i}/{len(cases)}] id={cid:2} 失败")
            continue

        faith_ratio = float(faith["supported_ratio"])
        consistent = _as_bool(corr.get("consistent"))

        details.append({
            "id": cid,
            "question": case["question"],
            "answer": answer,
            "faithfulness": faith_ratio,
            "unsupported": faith.get("unsupported_claims", []),
            "consistent": consistent,
            "reason": corr.get("reason", ""),
        })
        print(f"[{i}/{len(cases)}] id={cid:2} faith={faith_ratio:.2f} correct={consistent}")

    return _aggregate(details, len(cases), failures)


if __name__ == '__main__':
    from evals.dataset import real_cases

    cases = real_cases()
    retrieval = eval_retrieval(cases)
    result = eval_generation(cases, retrieval)

    print(f"\n有效性: {result['n_valid']}/{result['n_cases']}  失败 {result['n_failures']}")
    print(f"faithfulness = {result['faithfulness']:.2f}")
    print(f"correctness  = {result['correctness']:.2f}")
    print("matrix:", result["matrix"])
    print("\n无据结论：")
    for d in result["details"]:
        for c in d.get("unsupported", []):
            print(f"  id={d['id']}  {c}")
