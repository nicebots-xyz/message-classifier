import asyncio
import hashlib
import secrets
import logging
import os
from pydantic import BaseModel
from transformers import pipeline
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from cachier import cachier

# ------------------ SETUP ------------------

# Load environment variables
load_dotenv()

# Create FastAPI instance
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ AUTHENTICATION ------------------

# Auth with a bearer api key, whose hash is stored in the environment variable API_KEY_HASH
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
API_KEY_HASH = os.getenv("API_KEY_HASH")
if not API_KEY_HASH and os.path.exists("/run/secrets/api_key_hash"):
    with open("/run/secrets/api_key_hash", "r") as f:
        API_KEY_HASH = f.read().strip()
    logger.info("API key hash loaded from secret")
else:
    logger.info("API key hash loaded from environment variable")

assert API_KEY_HASH, "API_KEY_HASH must be set"


# Function to verify API key
def verify_api_key(token: str):
    token_hash: str = hashlib.sha256(token.encode()).hexdigest()
    return secrets.compare_digest(token_hash, API_KEY_HASH)


# Dependency to authenticate user
async def authenticate_user(token: str = Depends(oauth2_scheme)):
    if not verify_api_key(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# ------------------ CLASSIFICATION ------------------

# Setup classifier
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Default labels
DEFAULT_LABELS: list[str] = [
    "programming",
    "politics",
    "sports",
    "science",
    "technology",
    "video games",
]


# Classification model
class Classification(BaseModel):
    sequence: str = "The text to classify"
    labels: list[str] = DEFAULT_LABELS
    scores: list[float] = [0.0] * len(DEFAULT_LABELS)


# Function to classify message
@cachier(cache_dir="./cache")
def classify_sync(message: str, labels: list[str]) -> dict:
    result = classifier(message, candidate_labels=labels)
    return result


# ------------------ ROUTES ------------------

# Lock to ensure only one classification at a time
classification_lock = asyncio.Lock()


# Route to classify message
@app.get("/v1/classify")
async def classify(
    message: str, labels: list[str] = None, token: str = Depends(authenticate_user)
) -> Classification:
    labels = labels or DEFAULT_LABELS
    async with classification_lock:  # Ensure only one classification at a time
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, classify_sync, message, labels)
        result = Classification(**result)
        return result


# Health check route
@app.get("/v1/health")
async def health() -> dict:
    return {"status": "ok"}
