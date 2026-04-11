from __future__ import annotations

import os
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ai_dev_team")
RUNS_COLLECTION = os.getenv("MONGO_RUNS_COLLECTION", "runs")
AGENT_PROFILES_COLLECTION = os.getenv("MONGO_AGENT_PROFILES_COLLECTION", "agent_profiles")
AGENT_MEMORIES_COLLECTION = os.getenv("MONGO_AGENT_MEMORIES_COLLECTION", "agent_memories")


def get_mongo_client() -> MongoClient:
    return MongoClient(MONGO_URI)


def get_database() -> Database:
    client = get_mongo_client()
    return client[MONGO_DB_NAME]


def get_runs_collection() -> Collection:
    collection = get_database()[RUNS_COLLECTION]
    _ensure_indexes(collection)
    return collection




def get_agent_profiles_collection() -> Collection:
    collection = get_database()[AGENT_PROFILES_COLLECTION]
    _ensure_agent_profile_indexes(collection)
    return collection


def get_agent_memories_collection() -> Collection:
    collection = get_database()[AGENT_MEMORIES_COLLECTION]
    _ensure_agent_memory_indexes(collection)
    return collection


def _ensure_indexes(collection: Collection) -> None:
    collection.create_index("run_id", unique=True)
    collection.create_index("created_at")
    collection.create_index("task")
    collection.create_index("final_decision")
    collection.create_index("release_status")
    collection.create_index("severity")


def _ensure_agent_profile_indexes(collection: Collection) -> None:
    collection.create_index("agent_id", unique=True)
    collection.create_index("updated_at")


def _ensure_agent_memory_indexes(collection: Collection) -> None:
    collection.create_index([("agent_id", 1), ("title", 1), ("project_mode", 1)], unique=True)
    collection.create_index("importance")
    collection.create_index("created_at")
    collection.create_index("tags")

