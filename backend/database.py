"""
database.py
===========
MongoDB connection management with Motor (async driver) and automatic
local JSON persistence fallback when MongoDB is offline.

Usage:
    from backend.database import (
        connect_db, disconnect_db, is_connected, get_collection,
        save_inspection_record, get_inspection_record,
        query_inspections, get_dashboard_summary_data,
        get_defect_distribution_data, get_inspection_trends_data
    )
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import DESCENDING

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state — set by lifespan events in main.py
# ---------------------------------------------------------------------------
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

# Local persistence file path
LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LOCAL_DATA_FILE = os.path.join(LOCAL_DATA_DIR, "inspections.json")

_DEFECT_CLASSES = ["open", "short", "mousebite", "spur", "spurious_copper", "pin_hole"]


def _ensure_local_data_dir() -> None:
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    if not os.path.exists(LOCAL_DATA_FILE):
        with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_local_inspections() -> List[Dict[str, Any]]:
    _ensure_local_data_dir()
    try:
        with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not read local inspections file: %s", exc)
        return []


def _save_local_inspections(records: List[Dict[str, Any]]) -> None:
    _ensure_local_data_dir()
    try:
        with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not write local inspections file: %s", exc)


async def connect_db(uri: str, db_name: str) -> bool:
    """
    Open a MongoDB connection.
    Returns True on success, False if the connection could not be established.
    """
    global _client, _db
    _ensure_local_data_dir()
    try:
        _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=1500)
        await _client.admin.command("ping")
        _db = _client[db_name]
        await _ensure_indexes()
        logger.info("MongoDB connected: %s / %s", uri, db_name)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("MongoDB unavailable (%s). Falling back to local storage (%s).", exc, LOCAL_DATA_FILE)
        _client = None
        _db = None
        return False


async def disconnect_db() -> None:
    """Close the MongoDB connection."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB disconnected.")


def get_db() -> Optional[AsyncIOMotorDatabase]:
    """Return the active database instance, or None if not connected."""
    return _db


def is_connected() -> bool:
    """Return True if MongoDB is connected."""
    return _db is not None


def get_collection(name: str):
    """Return a collection from the active database."""
    if _db is None:
        raise RuntimeError("MongoDB is not connected.")
    return _db[name]


async def _ensure_indexes() -> None:
    """Create necessary indexes for efficient querying."""
    if _db is None:
        return
    inspections = _db["inspections"]
    try:
        await inspections.create_index([("timestamp", DESCENDING)])
        await inspections.create_index([("decision", 1)])
        await inspections.create_index([("pcb_id", 1)])
        await inspections.create_index([("defects.class_name", 1)])
        logger.debug("MongoDB indexes ensured.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not create MongoDB indexes: %s", exc)


# ---------------------------------------------------------------------------
# High-Level Storage Operations with Graceful Local Fallback
# ---------------------------------------------------------------------------

async def save_inspection_record(doc: Dict[str, Any]) -> bool:
    """
    Save an inspection record to MongoDB or local storage fallback.
    """
    record = dict(doc)
    # Ensure serializable timestamp
    ts = record.get("timestamp")
    if isinstance(ts, datetime):
        iso_ts = ts.isoformat()
    elif isinstance(ts, str):
        iso_ts = ts
    else:
        iso_ts = datetime.now(timezone.utc).isoformat()
    record["timestamp"] = iso_ts

    if is_connected():
        try:
            db_doc = dict(record)
            if isinstance(ts, datetime):
                db_doc["timestamp"] = ts
            await get_collection("inspections").replace_one(
                {"_id": db_doc["_id"]}, db_doc, upsert=True
            )
            logger.info("Inspection %s saved to MongoDB.", record["_id"])
        except Exception as exc:
            logger.warning("MongoDB save failed (%s), saving to local store.", exc)

    # Always persist to local file as backup & fallback
    records = _load_local_inspections()
    records = [r for r in records if r.get("_id") != record.get("_id") and r.get("inspection_id") != record.get("_id")]
    records.insert(0, record)
    _save_local_inspections(records)
    return True


async def get_inspection_record(inspection_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an inspection record by ID."""
    if is_connected():
        try:
            doc = await get_collection("inspections").find_one({"_id": inspection_id})
            if doc:
                doc["inspection_id"] = doc.pop("_id")
                if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                return doc
        except Exception as exc:
            logger.warning("MongoDB lookup failed: %s", exc)

    # Local store fallback
    records = _load_local_inspections()
    for r in records:
        if r.get("_id") == inspection_id or r.get("inspection_id") == inspection_id:
            item = dict(r)
            item["inspection_id"] = item.pop("_id", item.get("inspection_id"))
            return item
    return None


async def query_inspections(
    page: int = 1,
    limit: int = 20,
    decision: Optional[str] = None,
    defect: Optional[str] = None,
    severity: Optional[str] = None,
    pcb_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    """Query inspections with filtering and pagination."""
    if is_connected():
        try:
            query: dict = {}
            if decision:
                query["decision"] = decision.upper()
            if defect:
                query["defects.class_name"] = defect.lower()
            if severity:
                query["defects.severity"] = severity.upper()
            if pcb_id:
                query["pcb_id"] = {"$regex": pcb_id, "$options": "i"}
            if date_from or date_to:
                ts_filter = {}
                if date_from:
                    ts_filter["$gte"] = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if date_to:
                    ts_filter["$lte"] = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                query["timestamp"] = ts_filter

            col = get_collection("inspections")
            total = await col.count_documents(query)
            skip = (page - 1) * limit
            cursor = col.find(query).sort("timestamp", -1).skip(skip).limit(limit)

            items = []
            async for doc in cursor:
                doc["inspection_id"] = doc.pop("_id")
                if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                items.append(doc)
            return total, items
        except Exception as exc:
            logger.warning("MongoDB query failed (%s), using local store.", exc)

    # Local query fallback
    records = _load_local_inspections()
    filtered = []
    for r in records:
        if decision and r.get("decision", "").upper() != decision.upper():
            continue
        if pcb_id and pcb_id.lower() not in r.get("pcb_id", "").lower():
            continue
        if defect:
            has_defect = any(d.get("class_name", "").lower() == defect.lower() for d in r.get("defects", []))
            if not has_defect:
                continue
        if severity:
            has_sev = (r.get("highest_severity", "").upper() == severity.upper() or
                       any(d.get("severity", "").upper() == severity.upper() for d in r.get("defects", [])))
            if not has_sev:
                continue
        if date_from or date_to:
            r_ts = r.get("timestamp", "")
            if date_from and r_ts < date_from:
                continue
            if date_to and r_ts > date_to + "T23:59:59":
                continue
        item = dict(r)
        item["inspection_id"] = item.pop("_id", item.get("inspection_id"))
        filtered.append(item)

    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    return total, filtered[start:end]


async def get_dashboard_summary_data() -> Dict[str, Any]:
    """Compute KPI metrics across all inspections."""
    if is_connected():
        try:
            col = get_collection("inspections")
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_inspections":      {"$sum": 1},
                        "pass_count":             {"$sum": {"$cond": [{"$eq": ["$decision", "PASS"]}, 1, 0]}},
                        "rework_count":           {"$sum": {"$cond": [{"$eq": ["$decision", "REWORK"]}, 1, 0]}},
                        "reject_count":           {"$sum": {"$cond": [{"$eq": ["$decision", "REJECT"]}, 1, 0]}},
                        "defect_count":           {"$sum": "$defect_count"},
                        "avg_processing_time_ms": {"$avg": "$processing_time_ms"},
                    }
                }
            ]
            docs = await col.aggregate(pipeline).to_list(length=1)
            if docs:
                doc = docs[0]
                return {
                    "total_inspections": doc.get("total_inspections", 0),
                    "pass_count": doc.get("pass_count", 0),
                    "rework_count": doc.get("rework_count", 0),
                    "reject_count": doc.get("reject_count", 0),
                    "defect_count": doc.get("defect_count", 0),
                    "average_processing_time_ms": round(doc.get("avg_processing_time_ms") or 0, 1),
                }
        except Exception as exc:
            logger.warning("MongoDB summary failed (%s), using local data.", exc)

    records = _load_local_inspections()
    total = len(records)
    if total == 0:
        return {
            "total_inspections": 0, "pass_count": 0, "rework_count": 0,
            "reject_count": 0, "defect_count": 0, "average_processing_time_ms": 0.0,
        }

    pass_c = sum(1 for r in records if r.get("decision") == "PASS")
    rework_c = sum(1 for r in records if r.get("decision") == "REWORK")
    reject_c = sum(1 for r in records if r.get("decision") == "REJECT")
    defect_c = sum(r.get("defect_count", 0) for r in records)
    total_time = sum(r.get("processing_time_ms", 0.0) for r in records)

    return {
        "total_inspections": total,
        "pass_count": pass_c,
        "rework_count": rework_c,
        "reject_count": reject_c,
        "defect_count": defect_c,
        "average_processing_time_ms": round(total_time / total, 1),
    }


async def get_defect_distribution_data() -> List[Dict[str, Any]]:
    """Compute frequency counts for each defect class."""
    if is_connected():
        try:
            col = get_collection("inspections")
            pipeline = [
                {"$unwind": "$defects"},
                {"$group": {"_id": "$defects.class_name", "count": {"$sum": 1}}},
            ]
            counts = {c: 0 for c in _DEFECT_CLASSES}
            async for doc in col.aggregate(pipeline):
                cls = doc["_id"]
                if cls in counts:
                    counts[cls] = doc["count"]
            return [{"class_name": c, "count": counts[c]} for c in _DEFECT_CLASSES]
        except Exception as exc:
            logger.warning("MongoDB defect distribution failed (%s), using local data.", exc)

    records = _load_local_inspections()
    counts = {c: 0 for c in _DEFECT_CLASSES}
    for r in records:
        for d in r.get("defects", []):
            c_name = d.get("class_name")
            if c_name in counts:
                counts[c_name] += 1
    return [{"class_name": c, "count": counts[c]} for c in _DEFECT_CLASSES]


async def get_inspection_trends_data(days: int = 30) -> List[Dict[str, Any]]:
    """Return daily inspection totals for the past N days."""
    records = _load_local_inspections()
    day_map: Dict[str, Dict[str, int]] = {}
    now = datetime.now(timezone.utc)
    for i in range(days - 1, -1, -1):
        d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        day_map[d_str] = {"date": d_str, "total": 0, "pass_count": 0, "rework_count": 0, "reject_count": 0}

    for r in records:
        ts_str = r.get("timestamp", "")
        d_key = ts_str[:10]
        if d_key in day_map:
            day_map[d_key]["total"] += 1
            dec = r.get("decision")
            if dec == "PASS":
                day_map[d_key]["pass_count"] += 1
            elif dec == "REWORK":
                day_map[d_key]["rework_count"] += 1
            elif dec == "REJECT":
                day_map[d_key]["reject_count"] += 1

    return list(day_map.values())


LOCAL_SETTINGS_FILE = os.path.join(LOCAL_DATA_DIR, "settings.json")

_DEFAULT_SETTINGS = {
    "confidence_threshold": 0.50,
    "iou_threshold": 0.45,
    "station_id": "QC-01",
    "line_id": "Line A",
    "input_resolution": "416x416",
    "alert_sound": True,
    "conveyor_interval_sec": 3,
}


async def get_settings_record() -> Dict[str, Any]:
    """Retrieve system settings from MongoDB or local JSON fallback."""
    if is_connected():
        try:
            doc = await get_collection("system_settings").find_one({"_id": "global_config"})
            if doc:
                doc.pop("_id", None)
                return {**_DEFAULT_SETTINGS, **doc}
        except Exception as exc:
            logger.warning("MongoDB settings fetch failed (%s), using local settings.", exc)

    if os.path.exists(LOCAL_SETTINGS_FILE):
        try:
            with open(LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                return {**_DEFAULT_SETTINGS, **loaded}
        except Exception as exc:
            logger.warning("Could not read local settings: %s", exc)

    return dict(_DEFAULT_SETTINGS)


async def save_settings_record(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Save system settings to MongoDB and local JSON fallback."""
    current = await get_settings_record()
    current.update(new_settings)

    if is_connected():
        try:
            db_doc = {"_id": "global_config", **current}
            await get_collection("system_settings").replace_one(
                {"_id": "global_config"}, db_doc, upsert=True
            )
            logger.info("System settings updated in MongoDB.")
        except Exception as exc:
            logger.warning("MongoDB save settings failed: %s", exc)

    _ensure_local_data_dir()
    try:
        with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except Exception as exc:
        logger.warning("Could not save local settings: %s", exc)

    return current


async def get_severity_distribution_data() -> List[Dict[str, Any]]:
    """Compute defect frequency grouped by severity level (LOW, MEDIUM, HIGH, CRITICAL)."""
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    counts = {s: 0 for s in severities}

    if is_connected():
        try:
            col = get_collection("inspections")
            pipeline = [
                {"$unwind": "$defects"},
                {"$group": {"_id": "$defects.severity", "count": {"$sum": 1}}},
            ]
            async for doc in col.aggregate(pipeline):
                s = str(doc["_id"]).upper()
                if s in counts:
                    counts[s] = doc["count"]
            return [{"severity": s, "count": counts[s]} for s in severities]
        except Exception as exc:
            logger.warning("MongoDB severity distribution failed (%s), using local.", exc)

    records = _load_local_inspections()
    for r in records:
        for d in r.get("defects", []):
            s = str(d.get("severity", "")).upper()
            if s in counts:
                counts[s] += 1

    return [{"severity": s, "count": counts[s]} for s in severities]


async def get_all_inspections_for_export(
    decision: Optional[str] = None,
    defect: Optional[str] = None,
    severity: Optional[str] = None,
    pcb_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all matching inspections for report generation and CSV audit exports."""
    total, items = await query_inspections(
        page=1,
        limit=10000,
        decision=decision,
        defect=defect,
        severity=severity,
        pcb_id=pcb_id,
        date_from=date_from,
        date_to=date_to,
    )
    return items
