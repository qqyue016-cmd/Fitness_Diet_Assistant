"""确定性护栏：把模型的输出（不可信）转换为可写入数据库的记录（可信）。

职责边界：
- 不调用任何 LLM
- 只做「库内匹配」+「克数校验」
- 输出分级结果，交给 UI 决定如何呈现与交互
"""

import db

MAX_GRAMS = 3000   # 单条记录克数上限（产品决策，可调整）

def match_food(name: str) -> dict:
    """把模型输出的食物名解析为库中的确定食物。

        返回统一形状（三种状态的键结构一致，调用方无需分支取键）：
            {"status": "matched",   "candidates": [food], ...}   唯一命中
            {"status": "ambiguous", "candidates": [food, ...]}   多命中，需用户选择
            {"status": "not_found", "candidates": []}            库中无此食物
    """
    # 空输入防护
    if not name or not name.strip():
        return {"status": "not_found", "candidates": []}

    candidates = db.search_foods(name)

    # 精确优先：库中存在与输入完全同名的记录时直接命中，不再判歧义。
    # 例：库里同时有「鸡蛋」「鸡蛋羹」，输入「鸡蛋」应命中「鸡蛋」本身。
    exact = [c for c in candidates if c["name"] == name]
    if exact:
        return {"status": "matched", "candidates": exact}

    if len(candidates) == 1:
        return {"status": "matched", "candidates": candidates}
    if len(candidates) > 1:
        return {'status': 'ambiguous',"candidates": candidates}
    return {"status": "not_found", "candidates": []}

def validate_meal(items: list[dict]) -> dict:
    """校验并规范化一批解析结果。

    输入：[{"food": "米饭", "grams": 150}, ...]        ← parser 的输出
    输出：{
        "ok":        [{"raw", "food", "grams"}],       # 唯一命中，可直接写库（grams 可能为 None，待用户补）
        "ambiguous": [{"raw", "candidates", "grams"}],          # 需用户从候选中选
        "not_found": [{"raw", "grams"}],               # 库中无，需用户确认或换词
        "invalid":   [{"raw", "grams", "reason"}],     # 克数非法
    }
    """
    reslut = {'ok': [],'ambiguous': [],'not_found': [],'invalid': []}

    for item in items:
        raw = item.get('food','')
        grams = item.get('grams')

        # 第一步：克数校验。非法的直接归入 invalid，不再做名称匹配
        if grams is not None:
            if grams <= 0:
                reslut['invalid'].append(
                    {'raw': raw, 'grams': grams, 'reason': '克数必须大于0'}
                )
                continue
            if grams > MAX_GRAMS:
                reslut['invalid'].append(
                    {'raw': raw, 'grams': grams, 'reason': f'克数不能超过{MAX_GRAMS}克'}
                )
                continue

        # 第二步：库内匹配
        match = match_food(raw)

        if match["status"] == "matched":
            reslut['ok'].append(
                {'raw': raw, 'food': match['candidates'][0]['name'], 'grams': grams}
            )
        elif match["status"] == "ambiguous":
            reslut['ambiguous'].append(
                {'raw': raw, 'candidates': [c['name'] for c in match['candidates']], 'grams': grams}
            )
        else:
            reslut['not_found'].append(
                {'raw': raw, 'grams': grams}
            )
    return reslut

if __name__ == '__main__':
    print(match_food("鸡蛋"))
    print(validate_meal([
        {"food": "鸡蛋", "grams": 100},      # 期望 ok
        {"food": "米饭", "grams": 150},      # 期望 ambiguous（白米饭/糙米饭）
        {"food": "水果", "grams": 200},      # 期望 not_found
        {"food": "鸡蛋", "grams": -5},       # 期望 invalid
        {"food": "鸡胸肉", "grams": None},   # 期望 ok，grams=None
    ]))
