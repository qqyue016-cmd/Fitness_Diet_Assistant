import db, calc

def build_plan(gender, weight_kg, height_cm, age, activity_level, goal) -> dict:
    bmr = calc.calc_bmr(gender,weight_kg,height_cm,age)
    tdee = calc.calc_tdee(bmr,activity_level)
    kcal = calc.calc_target_kcal(tdee,goal)
    macro_target = calc.calc_macro_target(kcal,weight_kg,goal)
    return {
        'bmr': bmr,
        'tdee': tdee,
        'target': {'kcal': kcal,
                   'protein_g': macro_target['protein_g'],
                   'fat_g': macro_target['fat_g'],
                   'carb_g': macro_target['carb_g']
                   }
    }

def build_daily_report(date: str, target: dict) -> dict:
    rows = db.list_intake_by_date(date)
    items = []
    for r in rows:
        food = db.query_food(r['food'])
        item = calc.calc_food_intake(food, r['grams'])
        item['id'] = r['id']
        items.append(item)

    total = calc.sum_intake(items)
    gap = calc.calc_gap(target, total)

    return {'date': date, 'items': items, 'total': total, 'gap': gap}

if __name__ == '__main__':
    p = build_plan('male', 70, 175, 25, 'moderate', 'muscle_gain')

    r = build_daily_report('2000-01-01', p['target'])
    print(r)

