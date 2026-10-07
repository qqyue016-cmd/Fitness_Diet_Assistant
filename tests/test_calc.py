import pytest
import calc


# ── BMR ──────────────────────────────────────────────
def test_bmr_male():
    assert calc.calc_bmr('male', 70, 175, 25) == pytest.approx(1673.75)


def test_bmr_female():
    assert calc.calc_bmr('female', 55, 162, 23) == pytest.approx(1286.5)


def test_bmr_invalid_gender():
    with pytest.raises(ValueError):
        calc.calc_bmr('other', 70, 175, 25)

# ── TDEE ─────────────────────────────────────────────
@pytest.mark.parametrize('level,expected',[
    ('sedentary', 2008.5),
    ('light', 2301.40625),
    ('moderate', 2594.3125),
    ('high', 2887.21875),
    ('extreme', 3180.125),
])
def test_tdee_all_levels(level,expected):
    assert calc.calc_tdee(1673.75,level) == pytest.approx(expected)

def test_tdee_invalid_level():
    with pytest.raises(ValueError):
        calc.calc_tdee(1673.75, 'lightt')

# ── TARGET_KCAL ──────────────────────────────────────
def test_target_kcal_muscle_gain():
    assert calc.calc_target_kcal(2594.3125,'muscle_gain') == pytest.approx(2983.459375)

def test_target_kcal_fat_loss():
    assert calc.calc_target_kcal(2594.3125,'fat_loss') == pytest.approx(2205.165625)

def test_target_kcal_maintain():
    assert calc.calc_target_kcal(2594.3125,'maintain') == pytest.approx(2594.3125)

def test_target_kcal_invalid_goal():
    with pytest.raises(ValueError):
        calc.calc_target_kcal(2594.3125, 'maintainn')

# ── MACRO_TARGET ─────────────────────────────────────
def test_macro_target():
    assert calc.calc_macro_target(2983.459375, 70, 'muscle_gain') == pytest.approx(
            {'protein_g': 126.0, 'fat_g': 63.0, 'carb_g': 478.11484375})

def test_macro_target_invalid_data():
    with pytest.raises(ValueError):
        calc.calc_macro_target(1800, 120, 'fat_loss')

# ── calc_food_intake：单条摄入 ────────────────────────
def test_food_intake_100g():
    """100g 时各项应与「每 100g」原值一致。"""
    assert calc.calc_food_intake(
        {'name': '白米饭', 'kcal': 130.0, 'protein': 2.7, 'fat': 0.3, 'carb': 28.2}, 100
    ) == pytest.approx({'name': '白米饭', 'grams': 100, 'kcal': 130.0,
                        'protein_g': 2.7, 'fat_g': 0.3, 'carb_g': 28.2})


def test_food_intake_scaled_200g():
    """200g 时各项应为原值的 2 倍。"""
    r = calc.calc_food_intake(
        {'name': '鸡胸肉', 'kcal': 165.0, 'protein': 31.0, 'fat': 3.6, 'carb': 0.0}, 200
    )
    assert r['kcal'] == pytest.approx(330.0)
    assert r['protein_g'] == pytest.approx(62.0)
    assert r['fat_g'] == pytest.approx(7.2)


def test_food_intake_zero_carb_stays_zero():
    """碳水真值为 0 的食物必须返回 0，不能变成缺失。"""
    r = calc.calc_food_intake(
        {'name': '鸡胸肉', 'kcal': 165.0, 'protein': 31.0, 'fat': 3.6, 'carb': 0.0}, 100
    )
    assert r['carb_g'] == 0.0


def test_food_intake_invalid_grams():
    with pytest.raises(ValueError):
        calc.calc_food_intake(
            {'name': '白米饭', 'kcal': 130.0, 'protein': 2.7, 'fat': 0.3, 'carb': 28.2}, 0
        )


def test_food_intake_missing_value_fails_fast():
    """契约：营养字段由 foods 表的 NOT NULL 保证非空，calc 层不做缺失值降级。
    传入 None 属违反契约，应直接失败而非静默降级。"""
    with pytest.raises(TypeError):
        calc.calc_food_intake(
            {'name': '白米饭', 'kcal': 130.0, 'protein': None, 'fat': 0.3, 'carb': 28.2}, 100
        )


# ── sum_intake：汇总 ─────────────────────────────────
def test_sum_intake_empty():
    """空列表 → 全 0（空集合求和为 0，不是 None）。"""
    assert calc.sum_intake([]) == pytest.approx(
        {'kcal': 0.0, 'protein_g': 0.0, 'fat_g': 0.0, 'carb_g': 0.0})


def test_sum_intake_two_items():
    items = [
        calc.calc_food_intake({'name': '白米饭', 'kcal': 130.0, 'protein': 2.7,
                               'fat': 0.3, 'carb': 28.2}, 100),
        calc.calc_food_intake({'name': '糙米饭', 'kcal': 123.0, 'protein': 2.7,
                               'fat': 1.0, 'carb': 25.6}, 100),
    ]
    assert calc.sum_intake(items) == pytest.approx(
        {'kcal': 253.0, 'protein_g': 5.4, 'fat_g': 1.3, 'carb_g': 53.8})


# ── calc_gap：与目标的缺口 ───────────────────────────
def test_calc_gap():
    """逐键求差；负值表示已超出。"""
    target = {'kcal': 2000.0, 'protein_g': 150.0, 'fat_g': 70.0, 'carb_g': 200.0}
    intake = {'kcal': 1800.0, 'protein_g': 120.0, 'fat_g': 80.0, 'carb_g': 150.0}
    assert calc.calc_gap(target, intake) == pytest.approx(
        {'kcal': 200.0, 'protein_g': 30.0, 'fat_g': -10.0, 'carb_g': 50.0})


def test_calc_gap_missing_field():
    """缺少预期字段时显式报错，不静默按 0 处理。"""
    with pytest.raises(ValueError):
        calc.calc_gap(
            {'protein_g': 150.0, 'fat_g': 70.0, 'carb_g': 200.0},
            {'kcal': 0.0, 'protein_g': 0.0, 'fat_g': 0.0, 'carb_g': 0.0},
        )
