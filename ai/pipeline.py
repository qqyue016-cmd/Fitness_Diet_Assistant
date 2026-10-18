from ai.guard import validate_meal
from ai.parser import meal_parser

class AIServiceError(Exception):
    """AI 服务不可用：超时 / 网络 / 限流"""
    

def parse_and_validate(text: str) -> dict:
    """口语文本 → 校验后的结构化结果（UI 层只调这一个入口）"""
    try:
        item = meal_parser(text)
    except Exception as e:
        raise AIServiceError(str(e)) from e
    return validate_meal(item)

if __name__ == '__main__':
    print(parse_and_validate("我中午吃了一碗米饭和两个鸡蛋"))
