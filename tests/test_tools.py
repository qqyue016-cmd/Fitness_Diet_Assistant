"""工具层测试：add_meal / delete_meal 的参数校验与写入结果。

用轻量替身模拟 ToolRuntime，只需提供 context 属性。
"""
from ai.tools import UserCtx, add_meal, delete_meal
from db import add_intake, list_intake_by_date

# 与 conftest.py 中的 TEST_DATE 保持一致（clean_intake 会自动清理）
TEST_DATE = "1900-01-01"
TARGET = {"kcal": 2983.46, "protein_g": 126.0, "fat_g": 63.0, "carb_g": 478.11}


class _Runtime:
    def __init__(self, today: str = TEST_DATE):
        self.context = UserCtx(target=TARGET, today=today)


def test_add_meal_ambiguous():
    """'米饭' 命中白米饭/糙米饭，应返回候选而不是写入。"""
    result = add_meal.func("米饭", 150, _Runtime())
    assert "无法唯一确定" in result
    assert list_intake_by_date(TEST_DATE) == []


def test_add_meal_not_found():
    result = add_meal.func("水果", 150, _Runtime())
    assert "未找到" in result
    assert list_intake_by_date(TEST_DATE) == []


def test_add_meal_rejects_invalid_grams():
    result = add_meal.func("鸡蛋", -5, _Runtime())
    assert "克数" in result
    assert list_intake_by_date(TEST_DATE) == []


def test_add_meal_writes_and_reports_kcal():
    result = add_meal.func("鸡蛋", 100, _Runtime())
    assert "已记录" in result
    assert "kcal" in result                      # 键名写成 kacl 会在这里崩
    assert len(list_intake_by_date(TEST_DATE)) == 1


def test_add_meal_is_idempotent():
    add_meal.func("鸡蛋", 100, _Runtime())
    result = add_meal.func("鸡蛋", 100, _Runtime())
    assert "请勿重复" in result
    assert len(list_intake_by_date(TEST_DATE)) == 1


def test_delete_meal_missing_id():
    result = delete_meal.func(999999, _Runtime())
    assert "没有找到" in result


def test_delete_meal_removes_and_reports_kcal():
    new_id = add_intake(TEST_DATE, "鸡蛋", 100)
    result = delete_meal.func(new_id, _Runtime())
    assert "已删除" in result
    assert "kcal" in result                      # 同上，抓键名拼错
    assert list_intake_by_date(TEST_DATE) == []
