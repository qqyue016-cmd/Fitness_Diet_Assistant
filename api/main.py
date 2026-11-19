from fastapi import FastAPI
from api.routes import plan

app = FastAPI(title='Fitness Plan API', version='0.1.0')
app.include_router(plan.router)

