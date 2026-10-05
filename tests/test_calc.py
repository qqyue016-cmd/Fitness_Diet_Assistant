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
