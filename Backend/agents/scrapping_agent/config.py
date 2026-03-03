import os
from dotenv import load_dotenv

load_dotenv()

# Your canonical taxonomy
ALLOWED_CATEGORIES = [
    "Plumbing",
    "Electrical",
    "Appliance",
    "Walls",
    "Doors",
    "Toilet",
    "Paint",
    "Exterior",
    "Flooring",
    "HVAC",
]

# WikiHow seeds for each category (you can tweak)
CATEGORY_SEEDS = {
    "Plumbing": "https://www.wikihow.com/Category:Plumbing",
    "Electrical": "https://www.wikihow.com/Category:Electrical",
    "Appliance": "https://www.wikihow.com/Category:Home-Appliances",
    "Walls": "https://www.wikihow.com/Category:Walls",
    "Doors": "https://www.wikihow.com/Category:Doors",
    "Toilet": "https://www.wikihow.com/Category:Toilets",
    "Paint": "https://www.wikihow.com/Category:Painting",
    "Exterior": "https://www.wikihow.com/Category:Exterior-Home-Improvement",
    "Flooring": "https://www.wikihow.com/Category:Flooring",
    "HVAC": "https://www.wikihow.com/Category:Heating-and-Cooling",
}

SOURCE_DOMAIN = "wikihow.com"
ALLOWED_HOSTS = ["www.wikihow.com", "wikihow.com"]

DISCOVERY_MAX_PAGES_PER_CATEGORY = 120
DISCOVERY_RPS = 0.25

CLASSIFY_BATCH_LIMIT = 200

INGEST_MAX_ARTICLES_PER_RUN = 40
INGEST_CONCURRENCY = 2
FETCH_RPS = 0.15
FETCH_TIMEOUT_MS = 45000

OPENAI_MODEL_CLASSIFIER = os.getenv("OPENAI_MODEL_CLASSIFIER", "gpt-5-nano")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "myhandyai_kb")

COL_DISCOVERED = "discovered_urls"
COL_DOCS = "kb_documents"
COL_STATE = "source_discovery_state"