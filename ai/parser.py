from ai.client import chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         "你是一个饮食记录助手，把用户的口语描述转成结构化数据。\n"
         '输出契约：只输出 JSON 数组，每个元素形如 [{{"food": "食物名", "grams": 克数}}]，不要任何解释文字。\n'
         "份量规则：能按常识估算就估算（一碗米饭≈150g，一个鸡蛋≈50g）；完全无法判断时 grams 填 null。\n"
         "禁令：- 严格按用户原话转录数值，包括负数、0、以及看起来不合理的值\n"
         "- 即使数值明显不合常理，也不要自行修正、取绝对值或省略符号\n"
         "- 你的任务是'转录'，不是'判断数值是否合理'——合理性校验由后续程序负责"),
        ("human", "{text}"),
    ]
)


chain = prompt | chat_model | JsonOutputParser()

def meal_parser(text: str) -> list[dict]:
    return chain.invoke({"text":text})

if __name__ == '__main__':
    a = meal_parser('我中午吃了一碗米饭和两个鸡蛋')
    b = meal_parser('早餐吃了一个鸡蛋、200克鸡胸肉')
    c = meal_parser('刚才吃了点水果')
    print(a)
    print(b)
    print(c)
    print(ai.guard.validate_meal(a),
          ai.guard.validate_meal(b),
          ai.guard.validate_meal(c))
