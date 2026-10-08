import sqlite3

import pytest

from db import (
    add_intake,
    delete_intake,
    get_connect,
    list_intake_by_date,
    query_food,
    search_foods,
)
from scripts.init_db import init_table

from tests.conftest import TEST_DATE


# ── query_food：精确查询 ──────────────────────────────
def test_query_food_hit():
    r = query_food('鸡胸肉')
    assert r['kcal'] == pytest.approx(165.0)
    assert r['protein'] == pytest.approx(31.0)


def test_query_food_miss_returns_none():
    assert query_food('火鸡胸肉') is None


def test_query_food_empty_string():
    assert query_food('') is None


def test_query_food_contract_returns_dict():
    assert isinstance(query_food('鸡蛋'), dict)


def test_query_food_is_parameterized():
    """SQL 用 ? 占位符：注入串只被当作普通查询值，不影响查询结构。"""
    assert query_food("' OR '1'='1") is None


# ── search_foods：模糊查询 ────────────────────────────
def test_search_foods_hit():
    names = [x['name'] for x in search_foods('鸡')]
    assert names
    assert '鸡胸肉' in names
    assert all('鸡' in n for n in names)


def test_search_foods_no_result():
    assert search_foods('火鸡') == []


# ── 数据完整性约束 ────────────────────────────────────
def test_foods_rejects_null_nutrient():
    """营养字段的 NOT NULL 约束必须生效。

    这是 calc 层不做缺失值处理的前提：完整性由数据库约束保证，
    而非靠上层「约定」或人工把关。
    """
    conn = get_connect()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                'INSERT INTO foods (name, kcal, protein, fat, carb, source) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                ('约束测试食物', 100.0, None, 1.0, 1.0, 'TEST'),
            )
    finally:
        conn.rollback()
        conn.close()

# ── add_intake：新增摄入 ──────────────────────────────
def test_add_intake_returns_id():
    """新增返回自增 id（正整数）。"""
    new_id = add_intake(TEST_DATE, '鸡胸肉', 200)
    assert isinstance(new_id, int)
    assert new_id > 0


def test_add_intake_then_list_contains_it():
    """新增后能查回来，食物、克数、日期一致。"""
    add_intake(TEST_DATE, '鸡胸肉', 200)
    rows = list_intake_by_date(TEST_DATE)
    assert len(rows) == 1
    assert rows[0]['food'] == '鸡胸肉'
    assert rows[0]['grams'] == pytest.approx(200.0)
    assert rows[0]['date'] == TEST_DATE


def test_add_intake_normalizes_date():
    """回归防线：不补零的日期必须被规范化存储。

    若只校验不规范化，'1900-1-1' 会原样入库，
    导致按 TEST_DATE 查询查不到——同一条记录、两种查法两种结果。
    """
    add_intake('1900-1-1', '鸡胸肉', 200)
    assert len(list_intake_by_date(TEST_DATE)) == 1


def test_add_intake_invalid_date():
    with pytest.raises(ValueError):
        add_intake('2026-13-45', '鸡胸肉', 200)


def test_add_intake_zero_grams():
    with pytest.raises(ValueError):
        add_intake(TEST_DATE, '鸡胸肉', 0)


def test_add_intake_negative_grams():
    with pytest.raises(ValueError):
        add_intake(TEST_DATE, '鸡胸肉', -5)


def test_add_intake_unknown_food():
    """库中不存在的食物应被拒绝，否则后续汇总取不到营养值会崩。"""
    with pytest.raises(ValueError):
        add_intake(TEST_DATE, '火鸡胸肉', 100)


# ── list_intake_by_date：按日查询 ─────────────────────
def test_list_intake_empty():
    """无记录返回空列表，而不是 None。"""
    assert list_intake_by_date(TEST_DATE) == []


def test_list_intake_returns_dict():
    """契约：返回 dict，不是 sqlite3.Row。"""
    add_intake(TEST_DATE, '鸡胸肉', 200)
    assert isinstance(list_intake_by_date(TEST_DATE)[0], dict)


def test_list_intake_order_by_id():
    """返回顺序须按 id 升序，否则 UI 里记录会乱跳。"""
    add_intake(TEST_DATE, '鸡胸肉', 200)
    add_intake(TEST_DATE, '白米饭', 150)
    rows = list_intake_by_date(TEST_DATE)
    assert [r['food'] for r in rows] == ['鸡胸肉', '白米饭']
    assert rows[0]['id'] < rows[1]['id']


def test_list_intake_normalizes_date():
    """查询侧同样要规范化，否则 UI 传 '1900-1-1' 会静默返回空列表。"""
    add_intake(TEST_DATE, '鸡胸肉', 200)
    assert len(list_intake_by_date('1900-1-1')) == 1


# ── delete_intake：删除 ───────────────────────────────
def test_delete_intake_removes_one():
    """删除返回受影响行数：删到为 1，再删为 0。"""
    new_id = add_intake(TEST_DATE, '鸡胸肉', 200)
    assert delete_intake(new_id) == 1
    assert list_intake_by_date(TEST_DATE) == []


def test_delete_intake_not_found():
    """不存在的 id 返回 0，不抛异常。"""
    assert delete_intake(999999) == 0


def test_delete_intake_only_removes_target():
    """重复记录下按 id 删只删一条——这就是 id 存在的意义。"""
    id1 = add_intake(TEST_DATE, '鸡胸肉', 200)
    id2 = add_intake(TEST_DATE, '鸡胸肉', 200)
    assert delete_intake(id1) == 1
    rows = list_intake_by_date(TEST_DATE)
    assert len(rows) == 1
    assert rows[0]['id'] == id2
