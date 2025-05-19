# Dockerfile

# 1. Base Image
FROM python:3.12-slim

# 2. Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# نام کاربری و گروه (می‌توانید تغییر دهید)
ARG APP_USER=football724
ARG APP_GROUP=football724
ARG APP_UID=1001
ARG APP_GID=1001

# 3. Install System Dependencies (در صورت نیاز uncomment و تکمیل کنید)
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     # پکیج‌های مورد نیاز مثل gcc, libpq-dev و ... را اینجا اضافه کنید
#     # gcc \
#     # libpq-dev \
#     && apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# 4. Create Non-Root User and Group
# ایجاد گروه با GID مشخص
RUN groupadd -g ${APP_GID} ${APP_GROUP}
# ایجاد کاربر با UID و GID مشخص، همراه با دایرکتوری خانگی (-m) و پوسته (-s)
RUN useradd -u ${APP_UID} -g ${APP_GROUP} -m -s /bin/bash ${APP_USER}

# 5. Set Work Directory
WORKDIR /app

# 6. Install Python Dependencies
# اول pip و setuptools را آپگرید/نصب کن
# اضافه کردن setuptools برای رفع مشکل distutils در Python 3.12
#RUN python -m pip install --no-cache-dir --upgrade pip setuptools # <--- 'setuptools' اضافه شد

# فقط requirements.txt را کپی کن تا از کش استفاده شود
COPY --chown=${APP_USER}:${APP_GROUP} requirements.txt .
# پکیج‌ها را نصب کن
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy Application Code
# بقیه کد برنامه را کپی کن و مالکیت را به کاربر برنامه بده
COPY --chown=${APP_USER}:${APP_GROUP} . .

# 8. Switch to Non-Root User
# به کاربر غیر root سوئیچ کن
USER ${APP_USER}

# 9. Expose Port (for FastAPI app)
EXPOSE 8000

# 10. Default Command (runs FastAPI app)
# این دستور توسط سرویس‌های worker و beat در docker-compose.yml بازنویسی خواهد شد.
# برای پروداکشن، --reload را حذف کنید.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]