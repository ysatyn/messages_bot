import os
import dotenv

dotenv.load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
COST = int(os.getenv("QUANTITY", 10))

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не найден")
if not COST:
    raise ValueError("COST не найден")