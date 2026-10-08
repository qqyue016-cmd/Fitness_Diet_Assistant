import pytest

import calc
import service
from db import add_intake
from tests.conftest import TEST_DATE


@pytest.fixture
def target():
    """标准画像的目标字典：70kg / 175cm / 25 岁男 / moderate / 增肌。

    纯函数调用，无副作用，故用 function scope 即可（也便于各用例独立）。
    """
    return service.build_plan('male', 70, 175, 25, 'moderate', 'muscle_gain')['target']


# ── build_plan ────────────────────────────────────────
def test_build_plan_values():
    """标准画像下 BMR / TDEE / 目标热量与宏量都应等于手算结果。"""
    plan = service.build_plan('male', 70, 175, 25, 'moderate', 'muscle_gain')

    assert plan['bmr'] == pytest.approx(1673.75)
    assert plan['tdee'] == pytest.approx(2594.3125)

    t = plan['target']
    assert t['kcal'] == pytest.approx(2983.459375)
    assert t['protein_g'] == pytest.approx(126.0)
    assert t['fat_g'] == pytest.approx(63.0)
    assert t['carb_g'] == pytest.approx(478.11484375)


def test_build_plan_target_keys(target):
    """契约：target 的键必须与 calc.NUTRIENT_KEYS 完全一致。..."""
    assert sorted(target) == sorted(calc.NUTRIENT_KEYS)



# ── build_daily_report：空日期 ────────────────────────
def test_daily_report_empty_date(target):
    """无记录时不应报错：items 为空、total 全 0、gap 等于目标本身。"""
    report = service.build_daily_report(TEST_DATE, target)

    assert report['date'] == TEST_DATE
    assert report['items'] == []
    assert all(report['total'][k] == 0.0 for k in calc.NUTRIENT_KEYS)
    assert report['gap'] == pytest.approx(target)


def test_daily_report_gap_is_not_alias(target):
    """防别名回归：gap 必须是新字典，改动它不得污染 target。"""
    report = service.build_daily_report(TEST_DATE, target)

    assert report['gap'] is not target

    report['gap']['kcal'] = -1
    assert target['kcal'] == pytest.approx(2983.459375)


# ── build_daily_report：有记录 ────────────────────────
def test_daily_report_with_records(target):
    """三条记录的当日合计与缺口应与基准一致。"""
    add_intake(TEST_DATE, '鸡胸肉', 200)
    add_intake(TEST_DATE, '白米饭', 150)
    add_intake(TEST_DATE, '鸡蛋', 100)

    report = service.build_daily_report(TEST_DATE, target)

    assert report['total'] == pytest.approx({
        'kcal': 680.0,
        'protein_g': 78.65,
        'fat_g': 18.25,
        'carb_g': 43.4,
    })
    assert report['gap'] == pytest.approx({
        'kcal': 2303.459375,
        'protein_g': 47.35,
        'fat_g': 44.75,
        'carb_g': 434.71484375,
    })


def test_daily_report_items_carry_id(target):
    """契约：items 每条必须带 id 与展示所需的 name / grams。

    UI 的「今天吃了什么」列表要给每行配删除按钮，删除接口按 id 定位，
    因此 id 缺失会让删除功能无法实现。
    """
    add_intake(TEST_DATE, '鸡胸肉', 200)
    add_intake(TEST_DATE, '白米饭', 150)

    items = service.build_daily_report(TEST_DATE, target)['items']

    assert len(items) == 2
    assert all('id' in it for it in items)
    assert all(it['name'] for it in items)
    assert all(it['grams'] > 0 for it in items)
