from utils.config_tool import config_calc


# 计算基础代谢bmr
def calc_bmr(gender: str,weight_kg: float,height_cm: float,age: int) ->float:
    if gender not in ('male', 'female'):
        raise ValueError(f'无效的性别：{gender}')
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == 'male' else base - 161

# 计算每日总消耗热量tdee
def calc_tdee(bmr: float,activity_level = 'moderate') ->float:
    factors = config_calc['ACTIVITY_FACTORS']
    if activity_level not in factors:
        raise ValueError(f'无效的活动量：{activity_level}，可选 {list(factors)}')
    return bmr * factors[activity_level]

# 计算目标热量
def calc_target_kcal(tdee: float,goal='maintain') ->float:
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

if __name__ == '__main__':
    bmr = calc_bmr('male',65,165,19)
    tdee = calc_tdee(bmr,'moderate')
    target_kcal = calc_target_kcal(tdee,'maintain')
    print(calc_macro_target(target_kcal,65,'maintain'))