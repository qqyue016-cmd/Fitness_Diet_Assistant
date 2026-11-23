import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ai.guard import MAX_GRAMS


# 计划
class ProfileIn(BaseModel):
    gender: Literal['male', 'female'] = Field(..., description='性别')
    weight_kg: float = Field(..., gt=0, le=300, description='体重')
    height_cm: float = Field(..., gt=50, le=250, description='身高')
    age: int = Field(..., ge=10, le=100, description='年龄')
    activity_level: Literal['sedentary', 'light', 'moderate', 'high', 'extreme'] = Field(..., description='活动水平')
    goal: Literal['muscle_gain', 'fat_loss', 'maintain'] = Field(..., description='目标')


class TargetOut(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


class PlanOut(BaseModel):
    bmr: float
    tdee: float
    target: TargetOut = Field(..., description='目标')


class FoodOut(BaseModel):
    name: str
    kcal: float
    protein: float
    fat: float
    carb: float
    source: str


# 饮食记录
class IntakeCreate(BaseModel):
    date: datetime.date
    food_name: str = Field(..., min_length=1)
    grams: float = Field(..., gt=0, le=MAX_GRAMS)


class IntakeCreateOut(BaseModel):
    id: int
    date: datetime.date
    food_name: str
    grams: float


class IntakeRecordOut(BaseModel):
    id: int
    date: datetime.date
    food: str
    grams: float


# 每日总结
class DailySummaryIn(BaseModel):
    date: datetime.date
    target: TargetOut


class IntakeItemOut(BaseModel):
    id: int
    name: str
    grams: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


class NutrientTotal(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


class NutrientGap(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


class DailySummaryOut(BaseModel):
    date: datetime.date
    items: list[IntakeItemOut]
    total: NutrientTotal
    gap: NutrientGap


# parse
class ParseIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=200, description='口语描述，如「中午吃了一碗米饭和两个鸡蛋」')


class ParsedOKOut(BaseModel):
    raw: str
    food: str
    grams: float | None


class ParsedAmbiguousOut(BaseModel):
    raw: str
    candidates: list[str]
    grams: float | None


class ParsedNotFoundOut(BaseModel):
    raw: str
    grams: float | None


class ParsedInvalidOut(BaseModel):
    raw: str
    grams: float | None
    reason: str


class ParseOut(BaseModel):
    ok: list[ParsedOKOut]
    ambiguous: list[ParsedAmbiguousOut]
    not_found: list[ParsedNotFoundOut]
    invalid: list[ParsedInvalidOut]


# chat
class ChatMessage(BaseModel):
    role: Literal['user', 'assistant'] = Field(..., description='角色')
    content: str = Field(..., min_length=1, max_length=2000, description='内容')

class ChatIn(BaseModel):
    messages: list[ChatMessage]= Field(..., min_length=1, max_length=50, description='全量对话历史')
    target: TargetOut = Field(..., description='目标')
    goal: str = Field('', max_length=20, description='目标类型，如「增肌」')

