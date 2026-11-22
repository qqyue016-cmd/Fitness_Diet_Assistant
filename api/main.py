from fastapi import FastAPI

from api.errors import register_error_handlers
from api.routes import plan, foods, intake, summary

app = FastAPI(title='Fitness Plan API', version='0.1.0')
app.include_router(plan.router)
app.include_router(foods.router)
app.include_router(intake.router)
app.include_router(summary.router)

register_error_handlers(app)
