#!/bin/bash

# --- تنظیمات ---
API_BASE_URL="http://localhost:8001" # پورت را تنظیم کنید
ADMIN_USERNAME="admin" # نام کاربری ادمین
ADMIN_PASSWORD="Derakht@2519" # رمز عبور ادمین
LEAGUE_ID=61 # شناسه لیگ
SEASON=2022 # فصل

# --- مرحله ۱: گرفتن توکن ---
echo "Requesting access token..."
ACCESS_TOKEN=$(curl -s -X POST "$API_BASE_URL/auth/token" \
   -H "Content-Type: application/x-www-form-urlencoded" \
   -d "username=$ADMIN_USERNAME&password=$ADMIN_PASSWORD" | \
   jq -r .access_token)

# بررسی توکن
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
  echo "Error: Failed to retrieve access token. Check credentials or server logs."
  exit 1
fi
echo "Access Token obtained."

# --- مرحله ۲: ارسال تسک به Celery ---
echo "Sending task to Celery..."
TASK_RESPONSE=$(curl -s -X POST "$API_BASE_URL/admin/coaches/update-all" \
   -H "Authorization: Bearer $ACCESS_TOKEN" \
   -H "Content-Type: application/json")

# استخراج Task ID
TASK_ID=$(echo "$TASK_RESPONSE" | jq -r .task_id)

if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
  echo "Error: Failed to send task to Celery. Response: $TASK_RESPONSE"
  exit 1
fi
echo "Task sent to Celery. Task ID: $TASK_ID"

# --- مرحله ۳: بررسی وضعیت تسک ---
echo "Checking task status..."
while true; do
  TASK_STATUS=$(curl -s -X GET "$API_BASE_URL/admin/tasks/$TASK_ID" \
     -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r .status)

  echo "Task Status: $TASK_STATUS"

  if [ "$TASK_STATUS" = "SUCCESS" ]; then
    echo "Task completed successfully."
    break
  elif [ "$TASK_STATUS" = "FAILURE" ]; then
    echo "Task failed. Check Celery logs for details."
    break
  else
    echo "Task is still running. Checking again in 1 seconds..."
    sleep 1
  fi
done

echo "Script finished."