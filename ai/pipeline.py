from ai.guard import validate_meal
from ai.parser import meal_parser

def parse_and_validate(text: str) -> dict:
    """口语文本 → 校验后的结构化结果（UI 层只调这一个入口）"""
    return validate_meal(meal_parser(text))

if __name__ == '__main__':
    print(parse_and_validate("我中午吃了一碗米饭和两个鸡蛋"))
