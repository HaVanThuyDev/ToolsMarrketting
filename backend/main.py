"""
FastAPI Backend for Facebook Marketing Tool.

Provides REST API endpoints for:
- Firebase Auth verification
- Facebook Cookie login & validation
- Group management
- Campaign posting
- History management & Excel export
"""

import os
import sys
import json
import time
import uuid
import threading
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from firebase_admin_init import (
    verify_firebase_token,
    save_user_session,
    get_user_session,
    save_campaign_history,
    get_campaign_history,
    clear_campaign_history,
    _load_local_db,
    db,
)
from facebook_service import FacebookService
from excel_service import export_results

# =====================================================
# APP INITIALIZATION
# =====================================================

app = FastAPI(
    title="Facebook Marketing Tool API",
    version="2.0.0",
    description="Backend API for Facebook Group auto-posting tool",
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://toolmarketting.online",
        "https://www.toolmarketting.online",
        "https://api.toolmarketting.online"
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for active Facebook services per user
# Key: uid -> FacebookService instance
_active_sessions: dict[str, FacebookService] = {}

# Campaign status tracking per user
_campaign_status: dict[str, dict] = {}


# =====================================================
# HELPER: Clean Unicode
# =====================================================

def clean_unicode(obj):
    """Recursively clean invalid UTF-8 characters from strings in objects."""
    if isinstance(obj, str):
        return obj.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
    elif isinstance(obj, dict):
        return {k: clean_unicode(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_unicode(item) for item in obj]
    else:
        return obj


# =====================================================
# SESSION HELPER
# =====================================================

def _get_or_restore_fb_session(uid: str) -> Optional[FacebookService]:
    """Get active Facebook session or auto-restore from saved cookie."""
    fb = _active_sessions.get(uid)
    if fb and fb.is_logged_in():
        return fb

    # Try restoring from saved session in Firestore / local_db
    sess = get_user_session(uid)
    cookie = sess.get("fbCookie")

    # Fallback: check local_db if any saved cookie exists
    if not cookie:
        local_db = _load_local_db()
        for u_data in local_db.get("users", {}).values():
            if u_data.get("fbCookie"):
                cookie = u_data.get("fbCookie")
                break

    if cookie:
        try:
            new_fb = FacebookService()
            new_fb.login_with_cookie(cookie)
            _active_sessions[uid] = new_fb
            return new_fb
        except Exception as e:
            print(f"Error auto-restoring Facebook session: {e}")
            return None

    return None


# =====================================================
# REQUEST / RESPONSE MODELS
# =====================================================

class CookieLoginRequest(BaseModel):
    cookie: str


class CampaignStartRequest(BaseModel):
    group_ids: List[str]
    group_names: List[str]
    content: str
    delay_seconds: int = 10
    images: List[str] = []


class AuthResponse(BaseModel):
    uid: str
    email: str
    name: str


class CookieLoginResponse(BaseModel):
    success: bool
    user_id: str = ""
    user_name: str = ""
    message: str = ""


# =====================================================
# DEPENDENCY: Extract & verify Firebase token
# =====================================================

async def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and verify Firebase ID token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    try:
        user_info = verify_firebase_token(token)
        return user_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# =====================================================
# AUTH ENDPOINTS
# =====================================================

@app.post("/api/auth/verify", response_model=AuthResponse)
async def verify_auth(authorization: str = Header(...)):
    """Verify Firebase ID token and return user info."""
    user = await get_current_user(authorization)
    return AuthResponse(**user)


# =====================================================
# COOKIE LOGIN ENDPOINTS
# =====================================================

@app.post("/api/cookie/login", response_model=CookieLoginResponse)
async def cookie_login(
    request: CookieLoginRequest,
    authorization: str = Header(...)
):
    """
    Validate Facebook cookie and create a session.
    Saves cookie + FB user info to Firestore/local_db.
    """
    user = await get_current_user(authorization)
    uid = user["uid"]

    fb = FacebookService()
    try:
        me = fb.login_with_cookie(request.cookie)
    except Exception as e:
        return CookieLoginResponse(
            success=False,
            message=str(e)
        )

    # Store active session in memory
    _active_sessions[uid] = fb

    # Save to storage
    save_user_session(uid, {
        "email": user["email"],
        "fbCookie": request.cookie,
        "fbUserId": str(me.get("id", "")),
        "fbUserName": me.get("name", ""),
        "lastLogin": datetime.now().isoformat(),
    })

    return CookieLoginResponse(
        success=True,
        user_id=str(me.get("id", "")),
        user_name=me.get("name", ""),
        message="Đăng nhập Facebook thành công!"
    )
@app.post("/api/cookie/browser-login", response_model=CookieLoginResponse)
async def browser_login(authorization: str = Header(...)):
    """
    Launch a headed browser, let the user log in on Facebook,
    and capture the cookie string automatically.
    """
    user = await get_current_user(authorization)
    uid = user["uid"]

    try:
        from playwright.sync_api import sync_playwright
    except (ImportError, ModuleNotFoundError):
        return CookieLoginResponse(
            success=False,
            message="❌ Thiếu thư viện 'playwright'! Vui lòng mở Terminal chạy: pip install playwright && playwright install chromium"
        )

    captured_cookies = {}
    error_message = None

    def run_browser():
        nonlocal error_message
        try:
            # Fix for Windows asyncio + threading + Playwright
            if sys.platform == 'win32':
                import asyncio
                try:
                    asyncio.get_event_loop()
                except RuntimeError:
                    asyncio.set_event_loop(asyncio.new_event_loop())
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=["--start-maximized"]
                )
                
                context = browser.new_context(
                    no_viewport=True,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    )
                )
                
                page = context.new_page()
                try:
                    page.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=45000)
                except Exception:
                    pass
                
                login_detected = False
                for _ in range(150):  # Wait up to 2.5 minutes
                    try:
                        if not browser.is_connected() or page.is_closed():
                            break
                        
                        cookies = context.cookies()
                        cookies_dict = {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}
                        
                        if "c_user" in cookies_dict and "xs" in cookies_dict:
                            login_detected = True
                            for c in cookies:
                                captured_cookies[c["name"]] = c["value"]
                            break
                    except Exception:
                        # Context might be briefly busy or navigating
                        pass
                    
                    time.sleep(1)
                
                try:
                    if browser.is_connected():
                        browser.close()
                except Exception:
                    pass
                
                if not login_detected and not ("c_user" in captured_cookies and "xs" in captured_cookies):
                    error_message = "Trình duyệt đã đóng hoặc chưa hoàn tất đăng nhập Facebook."
        except Exception as e:
            if not ("c_user" in captured_cookies and "xs" in captured_cookies):
                err_str = str(e)
                if any(x in err_str.lower() for x in ["closed", "connection", "target", "driver"]):
                    error_message = "Đăng nhập thất bại: Trình duyệt đã bị đóng."
                else:
                    error_message = f"Lỗi trình duyệt: {err_str}"

    import threading
    t = threading.Thread(target=run_browser)
    t.start()
    t.join()

    # If we successfully captured cookies, clear any transient error
    if "c_user" in captured_cookies and "xs" in captured_cookies:
        error_message = None

    if error_message:
        return CookieLoginResponse(
            success=False,
            message=error_message
        )

    if not captured_cookies:
        return CookieLoginResponse(
            success=False,
            message="Không lấy được cookie Facebook."
        )

    # Format cookie string
    cookie_parts = []
    for k, v in captured_cookies.items():
        cookie_parts.append(f"{k}={v}")
    cookie_str = "; ".join(cookie_parts)

    fb = FacebookService()
    try:
        me = fb.login_with_cookie(cookie_str)
    except Exception as e:
        return CookieLoginResponse(
            success=False,
            message=f"Cookie lấy được không hợp lệ: {str(e)}"
        )

    _active_sessions[uid] = fb

    fb_name = str(me.get("name", "")).encode("utf-8", "ignore").decode("utf-8")
    fb_uid = str(me.get("id", ""))

    save_user_session(uid, {
        "email": user["email"],
        "fbCookie": cookie_str,
        "fbUserId": fb_uid,
        "fbUserName": fb_name,
        "lastLogin": datetime.now().isoformat(),
    })

    return CookieLoginResponse(
        success=True,
        user_id=fb_uid,
        user_name=fb_name,
        message="Tự động lấy Cookie & Đăng nhập thành công!"
    )


@app.get("/api/cookie/status")
async def get_cookie_status(authorization: str = Header(...)):
    """Check if the authenticated Firebase user has an active or saved FB session."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    fb = _get_or_restore_fb_session(uid)
    if fb and fb.is_logged_in():
        return {
            "logged_in": True,
            "user_id": str(fb.user_id or ""),
            "user_name": fb.user_name or ""
        }
    return {"logged_in": False}


@app.post("/api/cookie/logout")
async def cookie_logout(authorization: str = Header(...)):
    """Logout from Facebook (clear session)."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    if uid in _active_sessions:
        _active_sessions[uid].logout()
        del _active_sessions[uid]

    # Also clear fbCookie in Firestore/local db
    save_user_session(uid, {
        "fbCookie": "",
        "fbUserId": "",
        "fbUserName": "",
    })

    return {"success": True, "message": "Đã đăng xuất Facebook"}


# =====================================================
# GROUP ENDPOINTS
# =====================================================

@app.get("/api/groups")
async def get_groups(authorization: str = Header(...)):
    """Fetch all Facebook groups the user has joined."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    fb = _get_or_restore_fb_session(uid)
    if not fb or not fb.is_logged_in():
        raise HTTPException(
            status_code=401,
            detail="Chưa đăng nhập Facebook hoặc Cookie đã hết hạn. Vui lòng quay lại nạp Cookie mới."
        )

    try:
        groups = fb.get_groups()
        # Clean Unicode data to avoid encoding issues
        groups = clean_unicode(groups)
        return {"success": True, "groups": groups, "total": len(groups)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách nhóm: {str(e)}")


# =====================================================
# IMAGE UPLOAD ENDPOINT
# =====================================================

@app.post("/api/upload/images")
async def upload_images(
    files: List[UploadFile] = File(...),
    authorization: str = Header(...),
):
    """Upload up to 10 images and return temporary local paths for browser posting."""
    await get_current_user(authorization)

    if not files:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 ảnh.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Bạn chỉ được chọn tối đa 10 ảnh.")

    saved_paths = []
    for file in files:
        filename = file.filename or f"upload_{uuid.uuid4().hex}.png"
        safe_name = ''.join(ch for ch in filename if ch.isalnum() or ch in "._- ")
        temp_dir = os.path.join(tempfile.gettempdir(), "facebook_tool_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        target_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{safe_name}")

        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
        saved_paths.append(target_path)

    return {"success": True, "images": saved_paths}


# =====================================================
# CAMPAIGN ENDPOINTS
# =====================================================

@app.post("/api/campaign/start")
async def start_campaign(
    request: CampaignStartRequest,
    authorization: str = Header(...)
):
    """Start a posting campaign to selected groups."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    fb = _get_or_restore_fb_session(uid)
    if not fb or not fb.is_logged_in():
        raise HTTPException(status_code=401, detail="Chưa đăng nhập Facebook.")

    if uid in _campaign_status and _campaign_status[uid].get("in_progress"):
        raise HTTPException(status_code=409, detail="Chiến dịch đang chạy. Vui lòng đợi.")

    if not request.group_ids:
        raise HTTPException(status_code=400, detail="Hãy chọn ít nhất 1 Group.")
    if not request.content:
        raise HTTPException(status_code=400, detail="Hãy nhập nội dung bài viết.")

    campaign_id = str(uuid.uuid4())[:8]
    now_dt = datetime.now()
    now_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")

    items = []
    image_paths = list(request.images or [])
    for i, (gid, gname) in enumerate(zip(request.group_ids, request.group_names)):
        items.append({
            "index": i,
            "group": gname,
            "groupId": gid,
            "content": request.content,
            "images": ", ".join(image_paths[:10]) if image_paths else "",
            "timestamp": now_dt.isoformat(),
            "time": now_str,
            "status": "⏳ Đang chờ...",
            "postUrl": f"https://www.facebook.com/groups/{gid}/",
        })

    _campaign_status[uid] = {
        "in_progress": True,
        "campaign_id": campaign_id,
        "items": items,
        "completed": 0,
        "total": len(items),
    }

    def campaign_worker():
        delay = max(1, request.delay_seconds)

        for i, item in enumerate(items):
            item["status"] = "⏳ Đang đăng bài..."

            try:
                fb.join_group(item["groupId"])
            except Exception:
                pass

            try:
                out = fb.publish_post(item["groupId"], item["content"], image_paths[:10])
                if out.get("success"):
                    item["status"] = "✓ Thành công"
                    item["postUrl"] = out.get("url", item["postUrl"])
                else:
                    item["status"] = f"❌ {out.get('status', 'Thất bại')}"
            except Exception as e:
                item["status"] = f"❌ Lỗi: {str(e)}"

            _campaign_status[uid]["completed"] = i + 1

            save_campaign_history(uid, [{
                "group": item["group"],
                "groupId": item["groupId"],
                "content": item["content"],
                "images": item["images"],
                "timestamp": item["timestamp"],
                "time": item["time"],
                "status": item["status"],
                "postUrl": item["postUrl"],
            }])

            if i < len(items) - 1:
                time.sleep(delay)

        _campaign_status[uid]["in_progress"] = False

    thread = threading.Thread(target=campaign_worker, daemon=True)
    thread.start()

    return {
        "success": True,
        "campaign_id": campaign_id,
        "total_groups": len(items),
        "message": f"Đã bắt đầu chiến dịch đăng bài tới {len(items)} group!"
    }


@app.get("/api/campaign/status")
async def get_campaign_status(authorization: str = Header(...)):
    """Get current campaign progress."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    status = _campaign_status.get(uid, {
        "in_progress": False,
        "items": [],
        "completed": 0,
        "total": 0,
    })

    return status


@app.get("/api/campaign/history")
async def get_history(authorization: str = Header(...)):
    """Get campaign history from storage (last 24 hours)."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    try:
        history = get_campaign_history(uid)
        history = clean_unicode(history)
        return {"success": True, "history": history}
    except Exception as e:
        return {"success": True, "history": []}


@app.delete("/api/campaign/history")
async def delete_history(authorization: str = Header(...)):
    """Clear all campaign history."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    try:
        clear_campaign_history(uid)
        return {"success": True, "message": "Đã xóa toàn bộ lịch sử."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/campaign/export")
async def export_history(authorization: str = Header(...)):
    """Export campaign history to Excel file."""
    user = await get_current_user(authorization)
    uid = user["uid"]

    try:
        history = get_campaign_history(uid)
        if not history:
            raise HTTPException(status_code=404, detail="Không có dữ liệu lịch sử.")

        rows = []
        for item in history:
            item = clean_unicode(item)
            rows.append({
                "Group": item.get("group", ""),
                "Nội dung": item.get("content", ""),
                "Hình ảnh": item.get("images", ""),
                "Thời gian": item.get("time", ""),
                "Trạng thái": item.get("status", ""),
                "Link bài đăng": item.get("postUrl", ""),
            })

        tmp_path = os.path.join(tempfile.gettempdir(), f"campaign_report_{uid[:8]}.xlsx")
        export_results(rows, tmp_path)

        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="facebook_marketing_results.xlsx"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ROOT & HEALTH CHECK
# =====================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Facebook Marketing Tool Backend API is running!",
        "frontend": "http://localhost:5173",
        "docs": "http://localhost:8000/docs"
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


# =====================================================
# RUN SERVER
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
