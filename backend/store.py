"""
store.py
Persistence layer for the Student Arsenal.
Uses MongoDB (motor) when MONGO_URL is set; otherwise falls back to a local
JSON file so the app runs out of the box with zero external services.
"""
from __future__ import annotations
import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional

MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "resume_arsenal")
_DATA_DIR = Path(__file__).parent / "data"
_DATA_DIR.mkdir(exist_ok=True)
_JSON_PATH = _DATA_DIR / "arsenal.json"


class JsonStore:
    """Minimal async-compatible JSON store (fallback when no MongoDB)."""
    def __init__(self, path: Path):
        self.path = path
        self._lock = asyncio.Lock()
        if not path.exists():
            path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write(self, rows: List[dict]):
        self.path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    async def insert(self, record: dict):
        async with self._lock:
            rows = self._read()
            rows.append(record)
            self._write(rows)

    async def list_all(self) -> List[dict]:
        async with self._lock:
            rows = self._read()
        rows.sort(key=lambda r: r.get("createdAt", ""), reverse=True)
        return rows

    async def get(self, rec_id: str) -> Optional[dict]:
        for r in self._read():
            if r.get("id") == rec_id:
                return r
        return None


class MongoStore:
    def __init__(self, url: str, db_name: str):
        from motor.motor_asyncio import AsyncIOMotorClient
        self.client = AsyncIOMotorClient(url)
        self.col = self.client[db_name]["candidates"]

    async def insert(self, record: dict):
        await self.col.insert_one({**record, "_id": record["id"]})

    async def list_all(self) -> List[dict]:
        rows = await self.col.find({}, {"_id": 0}).sort("createdAt", -1).to_list(1000)
        return rows

    async def get(self, rec_id: str) -> Optional[dict]:
        return await self.col.find_one({"id": rec_id}, {"_id": 0})


def get_store():
    if MONGO_URL:
        try:
            return MongoStore(MONGO_URL, DB_NAME), "mongodb"
        except Exception as e:  # pragma: no cover
            print(f"[store] MongoDB init failed ({e}); using JSON fallback")
    return JsonStore(_JSON_PATH), "json-file"
