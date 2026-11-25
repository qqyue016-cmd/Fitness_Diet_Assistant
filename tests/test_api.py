import datetime

import pytest
from fastapi.testclient import TestClient

from api.main import app

TEST_DATE = '1900-01-01'
P = '/api/v1'

BODY = {'gender': 'male', 'weight_kg': 70, 'height_cm': 175, 'age': 22,
        'activity_level': 'moderate', 'goal': 'muscle_gain'}

TARGET = {'kcal': 3010.196875, 'protein_g': 126.0, 'fat_g': 63.0, 'carb_g': 484.8}


@pytest.fixture(scope='module')
def client():
    return TestClient(app)


def assert_422(r):
    assert r.status_code == 422, r.text
    body = r.json()
    assert body['error']['code'] == 'VALIDATION_ERROR'
    assert body['error']['message'], 'message 为空'



# plan
class TestPlan:
    def test_plan_ok(self, client):
        r = client.post(f'{P}/plan', json=BODY)
        assert r.status_code == 200
        b = r.json()

        assert b['bmr'] == pytest.approx(1688.75)
        assert b['tdee'] == pytest.approx(2617.5625)
        assert b['target']['kcal'] == pytest.approx(3010.196875)
        assert b['target']['protein_g'] == pytest.approx(126.0)
        assert b['target']['fat_g'] == pytest.approx(63.0)
        assert b['target']['carb_g'] == pytest.approx(484.799)

    def test_plan_invalid_gender(self, client):
        r = client.post(f'{P}/plan', json={**BODY, 'gender': 'x'})
        assert_422(r)

    def test_plan_missing_field(self, client):
        payload = {k: v for k, v in BODY.items() if k != 'weight_kg'}
        r = client.post(f'{P}/plan', json=payload)
        assert_422(r)


# foods
class TestFoods:
    def test_foods_ok(self, client):
        r = client.get(f'{P}/foods', params={'name': '鸡胸肉'})
        assert r.status_code == 200
        b = r.json()

        assert b['name'] == '鸡胸肉'
        assert b['kcal'] == pytest.approx(165.0)
        assert b['protein'] == pytest.approx(31.0)
        assert b['fat'] == pytest.approx(3.6)
        assert b['carb'] == pytest.approx(0.0)
        assert b['source'] == 'USDA'

    def test_foods_NOT_FOUND(self, client):
        r = client.get(f'{P}/foods', params={'name': '榴莲'})
        assert r.status_code == 404
        assert r.json()['error']['code'] == 'FOOD_NOT_FOUND'


class TestFoodsSearch:
    def test_search_hit(self, client):
        r = client.get(f'{P}/foods/search', params={'keyword': '鸡'})
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        assert all({'name', 'kcal', 'protein', 'fat', 'carb'} <= set(i) for i in items)

    def test_search_no_result_is_200_not_404(self, client):
        r = client.get(f'{P}/foods/search', params={'keyword': 'zzz不存在'})
        assert r.status_code == 200
        assert r.json() == []

    def test_search_blank_keyword(self, client):
        r = client.get(f'{P}/foods/search', params={'keyword': ' '})
        assert_422(r)

    def test_search_limit_out_of_range(self, client):
        r = client.get(f'{P}/foods/search', params={'keyword': '鸡', 'limit': 99})
        assert_422(r)


# intake
class TestIntake:
    def test_intake_post_ok(self, client):
        r = client.post(f'{P}/intake', json={'date': TEST_DATE, 'food_name': '鸡胸肉', 'grams': 100})
        assert r.status_code == 201
        b = r.json()
        assert isinstance(b['id'], int)
        assert b['date'] == TEST_DATE
        assert b['food_name'] == '鸡胸肉'
        assert b['grams'] == pytest.approx(100.0)

    def test_intake_post_NOT_FOUND(self, client):
        r = client.post(f'{P}/intake', json={'date': TEST_DATE, 'food_name': '不存在的食物', 'grams': 100})
        assert r.status_code == 404
        assert r.json()['error']['code'] == 'FOOD_NOT_FOUND'

    def test_intake_post_invalid_grams(self, client):
        r = client.post(f'{P}/intake', json={'date': TEST_DATE, 'food_name': '鸡胸肉', 'grams': -1})
        assert_422(r)

    def test_intake_post_limit_out_of_range(self, client):
        r = client.post(f'{P}/intake', json={'date': TEST_DATE, 'food_name': '鸡胸肉', 'grams': 10000})
        assert_422(r)

    def test_intake_post_date_format_error(self, client):
        r = client.post(f'{P}/intake', json={'date': '2020-1-1', 'food_name': '鸡胸肉', 'grams': 100})
        assert_422(r)


class TestIntakeGet:
    def test_intake_get_ok(self, client):
        client.post(f'{P}/intake', json={'date': TEST_DATE, 'food_name': '鸡胸肉', 'grams': 100})
        r = client.get(f'{P}/intake', params={'date': TEST_DATE})
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1  # 先锁非空，再断言内容
        assert items[0]['food'] == '鸡胸肉'
        assert items[0]['grams'] == pytest.approx(100.0)
        assert items[0]['date'] == TEST_DATE

    def test_intake_get_not_date(self, client):
        today = datetime.date.today().isoformat()
        r = client.get(f'{P}/intake')
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        # 空列表也算通过；非空时每条的 date 必须是今天
        assert all(i['date'] == today for i in items)


class TestIntakeDelete:
    def test_intake_delete_ok(self, client):
        iid = client.post(f'{P}/intake', json={
            'date': TEST_DATE, 'food_name': '鸡胸肉', 'grams': 100,
        }).json()['id']
        r = client.delete(f'{P}/intake/{iid}')
        assert r.status_code == 204, r.text
        assert r.content == b''  # 204 不允许有 body

    def test_intake_delete_not_found(self, client):
        r = client.delete(f'{P}/intake/999999')
        assert r.status_code == 404, r.text
        assert r.json()['error']['code'] == 'INTAKE_NOT_FOUND'

# summary
def test_summary_numbers(client):
    for food, g in [('鸡胸肉', 200), ('白米饭', 150)]:
        client.post(f'{P}/intake', json={'date': TEST_DATE, 'food_name': food, 'grams': g})
    r = client.post(f'{P}/summary', json={'date': TEST_DATE, 'target': TARGET})
    assert r.status_code == 200
    b = r.json()
    assert len(b['items']) == 2
    assert b['total']['kcal'] == pytest.approx(525.0)
    assert b['total']['protein_g'] == pytest.approx(66.05)
    assert b['total']['fat_g'] == pytest.approx(7.65)
    assert b['total']['carb_g'] == pytest.approx(42.3)
