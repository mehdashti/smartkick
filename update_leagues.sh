#!/bin/bash

# --- تنظیمات ---
API_BASE_URL="http://localhost:8001" # پورت را تنظیم کنید
ADMIN_USERNAME="admin" # نام کاربری ادمین
ADMIN_PASSWORD="Derakht@2519" # رمز عبور ادمین

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

# --- مرحله ۲: صدا زدن اندپوینت ادمین ---
echo "Calling /admin/leagues/update-leagues..."
curl -X POST "$API_BASE_URL/admin/teams/update-by-country/allcountries" \
   -H "Authorization: Bearer $ACCESS_TOKEN"

echo # Newline for clarity
echo "Script finished."