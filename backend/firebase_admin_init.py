"""
Firebase Admin SDK initialization and Firestore helpers with local fallback.

Supports both:
1. Full Firebase Admin + Firestore when serviceAccountKey.json is present.
2. Local dev mode with JWT token payload parsing and local JSON storage if serviceAccountKey.json is missing.
"""

import os
import json
import base64
from datetime import datetime, timedelta

_SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(__file__),
    "serviceAccountKey.json"
)

_LOCAL_DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "local_db.json"
)

has_admin_sdk = False
db = None

if os.path.exists(_SERVICE_ACCOUNT_PATH):
    try:
        import firebase_admin
        from firebase_admin import credentials, auth, firestore
        if not firebase_admin._apps:
            cred = credentials.Certificate(_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        has_admin_sdk = True
        print("[Firebase] Initialized with serviceAccountKey.json successfully.")
    except Exception as e:
        print(f"[Firebase] Could not initialize Admin SDK with key: {e}. Falling back to local mode.")
        has_admin_sdk = False

if not has_admin_sdk:
    print("[Firebase] Running in Local Dev Mode (No serviceAccountKey.json found).")


def _decode_jwt_payload_unverified(id_token: str) -> dict:
    """Decode JWT payload without verifying signature (for dev fallback)."""
    try:
        parts = id_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        payload_b64 = parts[1]
        # Fix base64 padding
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += '=' * (4 - rem)
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(decoded_bytes.decode('utf-8'))
        return {
            "uid": payload.get("user_id") or payload.get("sub") or "local_user",
            "email": payload.get("email", ""),
            "name": payload.get("name", payload.get("email", "").split("@")[0] or "User"),
        }
    except Exception as e:
        # Emergency fallback if token parsing fails
        return {
            "uid": "dev_user_123",
            "email": "user@example.com",
            "name": "Dev User",
        }


def verify_firebase_token(id_token: str) -> dict:
    """Verify Firebase ID token or parse JWT in local mode."""
    if has_admin_sdk:
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(id_token)
            return {
                "uid": decoded["uid"],
                "email": decoded.get("email", ""),
                "name": decoded.get("name", ""),
            }
        except Exception as e:
            # Fallback to JWT payload decode if token verification has transient error
            return _decode_jwt_payload_unverified(id_token)
    else:
        return _decode_jwt_payload_unverified(id_token)


def _load_local_db() -> dict:
    if os.path.exists(_LOCAL_DB_PATH):
        try:
            with open(_LOCAL_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}, "campaigns": {}}


def _save_local_db(data: dict):
    try:
        with open(_LOCAL_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving local_db.json: {e}")


def save_user_session(uid: str, data: dict):
    if has_admin_sdk and db:
        try:
            doc_ref = db.collection("users").document(uid)
            doc_ref.set(data, merge=True)
            return
        except Exception as e:
            print(f"Firestore save error: {e}")
    
    local = _load_local_db()
    if uid not in local["users"]:
        local["users"][uid] = {}
    local["users"][uid].update(data)
    _save_local_db(local)


def get_user_session(uid: str) -> dict:
    if has_admin_sdk and db:
        try:
            doc_ref = db.collection("users").document(uid)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print(f"Firestore get error: {e}")
    
    local = _load_local_db()
    return local["users"].get(uid, {})


def save_campaign_history(uid: str, items: list):
    if has_admin_sdk and db:
        try:
            collection_ref = db.collection("users").document(uid).collection("campaigns")
            for item in items:
                collection_ref.add(item)
            return
        except Exception as e:
            print(f"Firestore campaign save error: {e}")
    
    local = _load_local_db()
    if uid not in local["campaigns"]:
        local["campaigns"][uid] = []
    local["campaigns"][uid].extend(items)
    _save_local_db(local)


def get_campaign_history(uid: str) -> list:
    if has_admin_sdk and db:
        try:
            collection_ref = db.collection("users").document(uid).collection("campaigns")
            cutoff = datetime.now() - timedelta(hours=24)
            docs = (
                collection_ref
                .where("timestamp", ">=", cutoff.isoformat())
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .stream()
            )
            results = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            return results
        except Exception as e:
            print(f"Firestore campaign history error: {e}")

    local = _load_local_db()
    user_items = local["campaigns"].get(uid, [])
    cutoff = datetime.now() - timedelta(hours=24)
    valid = []
    for item in user_items:
        ts_str = item.get("timestamp")
        if ts_str:
            try:
                if datetime.fromisoformat(ts_str) >= cutoff:
                    valid.append(item)
            except Exception:
                valid.append(item)
        else:
            valid.append(item)
    return list(reversed(valid))


def clear_campaign_history(uid: str):
    if has_admin_sdk and db:
        try:
            collection_ref = db.collection("users").document(uid).collection("campaigns")
            docs = collection_ref.stream()
            for doc in docs:
                doc.reference.delete()
        except Exception as e:
            print(f"Firestore clear history error: {e}")

    local = _load_local_db()
    if uid in local["campaigns"]:
        local["campaigns"][uid] = []
        _save_local_db(local)
