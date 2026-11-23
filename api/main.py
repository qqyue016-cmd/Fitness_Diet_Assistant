from fastapi import FastAPI

from api.errors import register_error_handlers
from api.routes import plan, foods, intake, summary, ai_parse, ai_chat

app = FastAPI(title='Fitness Plan API', version='0.1.0')
app.include_router(plan.router)
app.include_router(foods.router)
app.include_router(intake.router)
app.include_router(summary.router)
app.include_router(ai_parse.router)
app.include_router(ai_chat.router)

register_error_handlers(app)
