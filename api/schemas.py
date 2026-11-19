from pydantic import BaseModel, Field
from typing import Literal

activity_level = ['sedentary', 'light', 'moderate', 'high', 'extreme']
goal = ['muscle_gain', 'fat_loss', 'maintain']
gender = ['male', 'female']


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
