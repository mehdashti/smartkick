# app/routers/admin/admin_base.py
from fastapi import APIRouter, Depends
# ---> وارد کردن وابستگی امنیتی شما <---
# from ..dependencies import get_admin_user # فرض وجود فایل dependencies

# تعریف یک روتر پایه با تنظیمات مشترک ادمین
admin_router_base = APIRouter(
    prefix="/admin",
    tags=["Admin Operations"],
    # ---> اعمال امنیت در سطح پایه <---
    # dependencies=[Depends(get_admin_user)]
)