import sqlite3

import pytest

from db import get_connect, query_food, search_foods
from scripts.init_db import init_table


@pytest.fixture(scope='module', autouse=True)
def ensure_db():
    """把库准备到可用状态。init_table 无参数、幂等（upsert），可反复执行。"""
    init_table()


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
