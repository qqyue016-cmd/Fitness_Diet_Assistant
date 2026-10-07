from utils.config_tool import config_calc


# 计算基础代谢bmr
def calc_bmr(gender: str,weight_kg: float,height_cm: float,age: int) ->float:
    if gender not in ('male', 'female'):
        raise ValueError(f'无效的性别：{gender}')
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == 'male' else base - 161

# 计算每日总消耗热量tdee
def calc_tdee(bmr: float,activity_level: str) ->float:
    factors = config_calc['ACTIVITY_FACTORS']
    if activity_level not in factors:
        raise ValueError(f'无效的活动量：{activity_level}，可选 {list(factors)}')
    return bmr * factors[activity_level]

# 计算目标热量
def calc_target_kcal(tdee: float,goal: str) ->float:
    factors = config_calc['GOAL_KCAL_FACTOR']
    if goal not in factors:
        raise ValueError(f'无效的目标：{goal}，可选 {list(factors)}')
    return tdee * factors[goal]

# 计算宏量分配
def calc_macro_target(target_kcal: float,weight_kg: float,goal: str) ->dict:
    p_table = config_calc['PROTEIN_G_PER_KG']
    f_table = config_calc['FAT_G_PER_KG']
    if goal not in p_table or goal not in f_table:
        raise ValueError(f'无效的目标：{goal}，可选 {list(p_table)}')
    protein_g = weight_kg*p_table[goal]
    fat_g = weight_kg*f_table[goal]
    carb_g = (target_kcal - protein_g * 4 - fat_g * 9) / 4
    if carb_g < 0:
        raise ValueError('目标热量不足以满足最低蛋白与脂肪需求')

    return {'protein_g': protein_g, 'fat_g': fat_g, 'carb_g': carb_g}

# 把「每 100g 的数值」按实际克数缩放
def _scale(value: float, ratio: float) -> float:
    return value * ratio

def calc_food_intake(food: dict, grams: float) -> dict:
    if grams <= 0:
        raise ValueError(f'摄入量必须大于0，收到 {grams}')

    ratio = grams / 100
    return {'name':food['name'],
          'grams':grams,
          'kcal':_scale(food['kcal'],ratio),
          'protein_g':_scale(food['protein'],ratio),
          'fat_g':_scale(food['fat'],ratio),
          'carb_g':_scale(food['carb'],ratio)
          }

# 汇总多条食物摄入数据（一天的摄入）
NUTRIENT_KEYS = ('kcal', 'protein_g', 'fat_g', 'carb_g')

def sum_intake(items: list[dict]) -> dict:
    total = {k: 0.0 for k in NUTRIENT_KEYS}
    for item in items:
        for key in NUTRIENT_KEYS:
            total[key] += item[key]
    return total

# 计算计划与实际摄入差值（正数=还可摄入，负数=已超出）
def calc_gap(target: dict, intake: dict) -> dict:
    result = {}
    for key in NUTRIENT_KEYS:
        if key not in target:
            raise ValueError(f'target 缺少字段：{key}（应由 calc_target_kcal 与 calc_macro_target 组装）')
        if key not in intake:
            raise ValueError(f'intake 缺少字段：{key}（应为 sum_intake 的输出）')
        result[key] = target[key] - intake[key]
    return result


if __name__ == '__main__':
    # 目标：70kg / 175cm / 25 岁男 / moderate / 增肌
    bmr = calc_bmr('male', 70, 175, 25)
    tdee = calc_tdee(bmr, 'moderate')
    kcal_target = calc_target_kcal(tdee, 'muscle_gain')
    target = {'kcal': kcal_target, **calc_macro_target(kcal_target, 70, 'muscle_gain')}

    # 一天吃了三样
    foods = [('鸡胸肉', 200, 165.0, 31.0, 3.6, 0.0),
             ('白米饭', 150, 130.0, 2.7, 0.3, 28.2),
             ('鸡蛋', 100, 155.0, 12.6, 10.6, 1.1)]
    items = [calc_food_intake({'name': n, 'kcal': k, 'protein': p, 'fat': f, 'carb': c}, g)
             for n, g, k, p, f, c in foods]
    intake = sum_intake(items)

    print('target =', {k: round(v, 2) for k, v in target.items()})
    print('intake =', {k: round(v, 2) for k, v in intake.items()})
    print('gap    =', {k: round(v, 2) for k, v in calc_gap(target, intake).items()})
