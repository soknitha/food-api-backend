import os
import sys
from dotenv import load_dotenv

# --------------------------------------------------------------------------
#  Centralized Configuration & Environment Variable Management
# --------------------------------------------------------------------------
# This script is the single source of truth for all configuration.
# It validates required environment variables and terminates the app if
# any are missing, ensuring a fail-fast and predictable environment.
# --------------------------------------------------------------------------

load_dotenv()

# 1. Define and Validate Required Environment Variables
# ----------------------------------------------------
REQUIRED_VARS = [
    "BOT_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_KEY"
]
missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]

if missing_vars:
    error_message = f"❌ Critical Error: Missing required environment variables: {', '.join(missing_vars)}"
    print(error_message, file=sys.stderr)
    sys.exit(f"Application cannot start due to missing configuration. Please set: {', '.join(missing_vars)}")

# 2. Fetch Configuration from Environment
# ---------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ប្រព័ន្ធធានាភាពត្រឹមត្រូវនៃ URL (Auto-Clean): កាត់ចោល https:// និង / ដែលលើសដើម្បីការពារការគាំង
RAW_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "web-production-88028.up.railway.app").strip()
DOMAIN = RAW_DOMAIN.replace("https://", "").replace("http://", "").split("/")[0]
PORT = int(os.getenv("PORT", 8000))

# 3. Define Derived and Static Configuration
# ------------------------------------------
APP_NAME = "Food E-Commerce Admin System"

# --- URLs ---
# Public facing URLs derived from the Railway domain
WEBHOOK_URL = f"https://{DOMAIN}/webhook"
MINI_APP_URL = f"https://{DOMAIN}/miniapp"

# Internal API URL 
# ប្រើ Localhost ជាលំនាំដើម, ប៉ុន្តែអ្នកអាចភ្ជាប់វាទៅ Live Server បានតាមរយៈការថែម API_BASE_URL ក្នុងឯកសារ .env
API_BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{PORT}/api")

# --- Asset Paths ---
# Path to the Khmer font for receipt generation
KHMER_FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "NotoSansKhmer-Regular.ttf")

print("✅ Configuration loaded and validated successfully.")
