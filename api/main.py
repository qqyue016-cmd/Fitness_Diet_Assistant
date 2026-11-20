from fastapi import FastAPI
from api.routes import plan,foods
from api.errors import register_error_handlers

app = FastAPI(title='Fitness Plan API', version='0.1.0')
app.include_router(plan.router)
app.include_router(foods.router)

register_error_handlers(app)

