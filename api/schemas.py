import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ai.guard import MAX_GRAMS


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