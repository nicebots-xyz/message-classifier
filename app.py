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

load_dotenv()

app = FastAPI()

# auth with a bearer api key, whoose hash is stored in the environment variable API_KEY_HASH
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
API_KEY_HASH = os.getenv("API_KEY_HASH")
assert API_KEY_HASH, "API_KEY_HASH environment variable must be set"

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

DEFAULT_LABELS: list[str] = [
    "programming",
    "politics",
    "sports",
    "science",
    "technology",
    "video games",
]

pool = ThreadPoolExecutor(max_workers=1)

logging.basicConfig(level=logging.INFO)


class Classification(BaseModel):
    sequence: str = "The text to classify"
    labels: list[str] = DEFAULT_LABELS
    scores: list[float] = [0.0] * len(DEFAULT_LABELS)


def classify_sync(message: str, labels: list[str]) -> dict:
    result = classifier(message, candidate_labels=labels)
    return result


# setup auth
def verify_api_key(token: str):
    token_hash: str = hashlib.sha256(token.encode()).hexdigest()
    return secrets.compare_digest(token_hash, API_KEY_HASH)


async def authenticate_user(token: str = Depends(oauth2_scheme)):
    if not verify_api_key(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


classification_lock = asyncio.Lock()  # Ensure only one classification at a time


@app.get("/v1/classify")
async def classify(
    message: str, labels: list[str] = None, token: str = Depends(authenticate_user)
) -> Classification:
    """
    Classify the message into one of the labels
    :param message: The message to classify
    :type message: str
    :param labels: The labels to classify the message into
    :type labels: list[str]
    :return: The classification result
    :rtype: Classification
    """
    labels = labels or DEFAULT_LABELS
    async with classification_lock:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, classify_sync, message, labels)
        result = Classification(**result)
        return result


@app.get("/v1/health")
async def health() -> dict:
    return {"status": "ok"}
