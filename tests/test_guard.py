from ai.guard import match_food, validate_meal, MAX_GRAMS

# —————————— match_food ——————————
def test_match_food_exact():
    result = match_food("鸡蛋")
    assert result['status'] == "matched"
    assert result['candidates'][0]['name'] == "鸡蛋"


def test_match_food_ambiguous():
    result = match_food("米饭")
    assert result['status'] == "ambiguous"
    assert result['candidates'][0]['name'] == "白米饭"
    assert result['candidates'][1]['name'] == "糙米饭"


def test_match_food_not_found():
    assert match_food("水果")['status'] == "not_found"


def test_match_food_empty():
    assert match_food("")['status'] == "not_found"


def test_match_food_whitespace():
    assert match_food("  ")['status'] == "not_found"

# —————————— validate_meal ——————————
def test_validate_meal_ambiguous():
    result = validate_meal([{"food": "米饭", "grams": 100}])
    assert result['ambiguous'][0]['candidates'][0] == "白米饭"
    assert result['ambiguous'][0]['candidates'][1] == "糙米饭"


def test_validate_meal_grams_is_None():
    result = validate_meal([{"food": "鸡蛋", "grams": None}])
    assert result['ok'][0]['raw'] == "鸡蛋"
    assert result['ok'][0]['food'] == "鸡蛋"
    assert result['ok'][0]['grams'] is None


def test_invalid_len_is_1():
    assert len(validate_meal([{"food": "鸡蛋", "grams": 0}])['invalid']) == 1


def test_grams_greater_than_MAX():
    assert validate_meal([{"food": "鸡蛋", "grams": 5000}])['invalid'][0]['reason'] == f'克数不能超过{MAX_GRAMS}克'


def test_input_empty():
    assert validate_meal([]) == {'ok': [],'ambiguous': [],'not_found': [],'invalid': []}


def test_format_name():
    result = validate_meal([{"food": "鸡胸", "grams": 200}])
    assert result['ok'][0]['raw'] == "鸡胸"
    assert result['ok'][0]['food'] == "鸡胸肉"



def test_exact_priority(monkeypatch):
    fake = [
        {"name": "鸡蛋",   "kcal": 155, "protein": 12.6, "fat": 10.6, "carb": 1.1,  "source": "test"},
        {"name": "鸡蛋羹", "kcal": 60,  "protein": 5.0,  "fat": 3.0,  "carb": 2.0,  "source": "test"},
    ]
    monkeypatch.setattr("db.search_foods", lambda kw: fake)
    result = match_food("鸡蛋")
    assert result["status"] == "matched"
    assert result["candidates"][0]["name"] == "鸡蛋"
