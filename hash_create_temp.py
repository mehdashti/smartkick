# یک فایل موقت یا در مفسر پایتون اجرا کنید
from app.core.security import get_password_hash

# رمز عبور قوی مورد نظر خود را اینجا وارد کنید
plain_password = "Derakht@2519"
hashed_password = get_password_hash(plain_password)

print("Password:", plain_password)
print("Hashed Password:", hashed_password)
# ---> مقدار هش شده را کپی کنید <---