# main.py
from fastapi import FastAPI
from .routers import players, teams, metadata


# ساخت نمونه اصلی FastAPI
app = FastAPI()

app.include_router(players.router)
app.include_router(teams.router)
app.include_router(metadata.router)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "سلام، خوش آمدید به API ما!"}
# اگر از uvicorn استفاده می‌کنید، این خط را فعال کنید
# تا سرور به طور خودکار اجرا شود
# این خط را می‌توانید برای تست محلی استفاده کنید
# از uvicorn import run
# از fastapi import FastAPI
# از routers import players 


# برای اجرای محلی (اگرچه معمولاً uvicorn از خط فرمان اجرا می‌شود)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)