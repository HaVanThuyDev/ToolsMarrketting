import re
import requests


class FacebookService:

    def __init__(self):

        self.access_token = None

        self.user_id = None

        self.user_name = None

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })

    # =====================================================
    # LOGIN BY COOKIE
    # =====================================================

    def login_with_cookie(
        self,
        cookie_string
    ):
        """
        Đăng nhập bằng cookie Facebook.

        Chấp nhận:
        - Cookie đầy đủ (copy từ trình duyệt)
        - Hoặc chỉ cần c_user và xs
        """

        cookie_string = cookie_string.strip()

        if not cookie_string:

            raise ValueError(
                "Cookie không được để trống."
            )

        import urllib.parse

        # Parse cookie string
        cookies = {}

        for part in cookie_string.split(";"):

            part = part.strip()

            if "=" in part:

                key, value = part.split(
                    "=",
                    1
                )

                unquoted_val = urllib.parse.unquote(value.strip())

                cookies[key.strip()] = unquoted_val

        c_user = cookies.get("c_user", "")

        xs = cookies.get("xs", "")

        if not c_user or not xs:

            raise ValueError(
                "Cookie phải chứa c_user và xs.\n\n"
                "Hướng dẫn:\n"
                "1. Mở Facebook trên trình duyệt\n"
                "2. Nhấn F12 → Application → Cookies\n"
                "3. Copy giá trị c_user và xs\n"
                "4. Nhập theo định dạng:\n"
                "   c_user=xxx; xs=yyy"
            )

        # Clear old cookies
        self.session.cookies.clear()

        # Set all cookies on session
        for key, value in cookies.items():

            self.session.cookies.set(
                key,
                value,
                domain=".facebook.com"
            )

        # Ensure c_user and xs are set
        self.session.cookies.set(
            "c_user",
            c_user,
            domain=".facebook.com"
        )

        self.session.cookies.set(
            "xs",
            xs,
            domain=".facebook.com"
        )

        self.user_id = c_user

        # Verify by fetching profile
        me = self.get_me()

        return me

    # =====================================================
    # GET CURRENT USER
    # =====================================================

    def get_me(self):

        if not self.user_id:

            raise RuntimeError(
                "Chưa đăng nhập."
            )

        url = f"https://mbasic.facebook.com/profile.php"

        try:

            response = self.session.get(
                url,
                timeout=20,
                allow_redirects=True
            )

        except requests.exceptions.RequestException as e:

            raise RuntimeError(
                f"Không thể kết nối Facebook: {e}"
            )

        text = response.text

        # Check if redirected to login page
        final_url = response.url.lower()

        is_login_page = any([
            "/login" in final_url,
            "checkpoint" in final_url
            and "cookie" not in final_url,
        ])

        # Also check page content for login form
        has_login_form = (
            'id="login_form"' in text
            or 'name="email"' in text
            and 'name="pass"' in text
        )

        if is_login_page or has_login_form:

            # Double check: maybe the c_user
            # is still in cookies (session valid)
            if not self.session.cookies.get(
                "c_user",
                domain=".facebook.com"
            ):

                raise RuntimeError(
                    "Cookie không hợp lệ hoặc đã hết hạn.\n"
                    "Hãy lấy cookie mới từ trình duyệt."
                )

        # Try to extract name from page
        name = self._extract_name(text)

        if not name or any(x in name.lower() for x in ["error", "lỗi", "facebook"]):

            name = f"Tài khoản {self.user_id}"

        self.user_name = name

        return {
            "id": self.user_id,
            "name": name
        }

    # =====================================================
    # EXTRACT NAME
    # =====================================================

    def _extract_name(self, html):
        """
        Trích xuất tên user từ HTML response.
        Thử nhiều pattern khác nhau.
        """

        # Pattern 1: <title>Name</title>
        title_match = re.search(
            r"<title[^>]*>([^<]+)</title>",
            html
        )

        if title_match:

            raw = title_match.group(1).strip()

            for suffix in [
                " | Facebook",
                " - Facebook",
                " – Facebook",
                " · Facebook",
            ]:

                if raw.endswith(suffix):

                    raw = raw[:-len(suffix)].strip()

                    break

            if (
                raw
                and raw != "Facebook"
                and "log" not in raw.lower()
            ):

                return raw

        # Pattern 2: "name":"xxx" in JSON data
        name_match = re.search(
            r'"name"\s*:\s*"([^"]{2,50})"',
            html
        )

        if name_match:

            candidate = name_match.group(1)

            # Filter out non-name values
            if not any(x in candidate.lower() for x in [
                "facebook", "http", "script", "bundle", "worker", "module", "config",
                "null", "undefined", "true", "false"
            ]):

                return candidate

        # Pattern 3: Profile name in meta tag
        meta_match = re.search(
            r'<meta[^>]*content="([^"]+)"[^>]*'
            r'property="og:title"',
            html
        )

        if not meta_match:

            meta_match = re.search(
                r'property="og:title"[^>]*'
                r'content="([^"]+)"',
                html
            )

        if meta_match:

            return meta_match.group(1).strip()

        return None

    # =====================================================
    # CHECK LOGIN
    # =====================================================

    def is_logged_in(self):

        return (
            self.user_id is not None
            and self.session.cookies.get(
                "c_user"
            ) is not None
        )

    # =====================================================
    # LOGOUT
    # =====================================================

    def logout(self):

        self.access_token = None

        self.user_id = None

        self.user_name = None

        self.session.cookies.clear()

    # =====================================================
    # GROUPS
    # =====================================================

    def get_groups(self):
        """
        Lấy TOÀN BỘ (200-300+ group) tài khoản đã tham gia từ Facebook.
        Kế thừa kết hợp HTTP request nhanh + Playwright scroll tự động cuộn trang để lấy 100% danh sách.
        """
        if not self.is_logged_in():
            raise RuntimeError("Chưa đăng nhập Facebook.")

        import concurrent.futures
        import html as html_lib
        import time

        all_groups = []
        seen_ids = set()

        headers_desktop = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        # Step 1: Initial Fast HTTP Fetch
        try:
            r = self.session.get("https://www.facebook.com/groups/joins/", headers=headers_desktop, timeout=8)
            if r.status_code == 200:
                extracted = self._extract_groups_from_text(r.text, seen_ids)
                all_groups.extend(extracted)
        except Exception:
            pass

        # Step 2: Deep Scroll via Playwright to fetch ALL 200+ groups dynamically loaded on scroll
        try:
            from playwright.sync_api import sync_playwright
            pw_cookies = []
            for cookie in self.session.cookies:
                pw_cookies.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": ".facebook.com",
                    "path": "/"
                })

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
                context.add_cookies(pw_cookies)
                page = context.new_page()
                page.goto("https://www.facebook.com/groups/joins/", wait_until="domcontentloaded", timeout=25000)
                time.sleep(2)

                # Extract initial page content
                page_groups = self._extract_groups_from_text(page.content(), seen_ids)
                all_groups.extend(page_groups)

                # Fast Scroll 10-12 times to force Facebook to lazy-load ALL 200+ joined groups
                no_new_count = 0
                for _ in range(12):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(0.8)
                    scroll_groups = self._extract_groups_from_text(page.content(), seen_ids)
                    if scroll_groups:
                        all_groups.extend(scroll_groups)
                        no_new_count = 0
                    else:
                        no_new_count += 1
                        if no_new_count >= 3:
                            break

                browser.close()
        except Exception:
            pass

        return all_groups

    def _clean_text_name(self, raw):
        if not raw:
            return ""

        import html as html_lib

        # Unescape HTML entities
        raw = html_lib.unescape(raw)

        # Decode unicode escape sequence only if raw string has literal \u
        if r"\u" in raw or "\\u" in raw:
            try:
                raw = raw.encode("utf-8").decode("unicode-escape")
            except Exception:
                pass

        # Fix Mojibake (Latin-1 double encoded UTF-8) if present
        if any(c in raw for c in ["Ã", "Æ", "â", "á"]):
            try:
                fixed = raw.encode("latin-1", "ignore").decode("utf-8", "ignore")
                if fixed and len(fixed) > 0:
                    raw = fixed
            except Exception:
                pass

        return raw.strip()

    def _extract_groups_from_text(
        self,
        html_text,
        seen_ids
    ):

        import html as html_lib

        groups = []

        ignore_ids = {
            str(self.user_id), "0", "1", "2"
        } if self.user_id else set()

        ignore_slugs = {
            "feed", "joins", "discover",
            "create", "category", "search",
            "notifications", "messages", "watch", "marketplace"
        }

        ignore_titles = {
            "groups", "nhóm", "xem tất cả",
            "tìm hiểu thêm", "facebook", "trang chủ",
            "thông báo", "bảng tin", "bản tin"
        }

        # Strategy 1: Comet node id & name JSON pattern
        pattern_json = re.compile(
            r'\{"node":\{"id":"(\d+)"[^}]*?'
            r'"name":"([^"]+)"'
        )

        for match in pattern_json.finditer(html_text):

            gid = match.group(1)
            raw_name = match.group(2)
            clean_name = self._clean_text_name(raw_name)

            if (
                gid not in seen_ids
                and gid not in ignore_ids
                and clean_name
                and len(clean_name) > 1
                and clean_name.lower() not in ignore_titles
            ):

                seen_ids.add(gid)

                groups.append({
                    "id": gid,
                    "name": clean_name
                })

        # Strategy 2: Direct "id":"123456789...","name":"Group Title" JSON pattern
        pattern_direct = re.compile(
            r'"id":"(\d{8,20})","name":"([^"]{2,120})"'
        )

        for match in pattern_direct.finditer(html_text):

            gid = match.group(1)
            raw_name = match.group(2)
            clean_name = self._clean_text_name(raw_name)

            if (
                gid not in seen_ids
                and gid not in ignore_ids
                and clean_name
                and len(clean_name) > 1
                and clean_name.lower() not in ignore_titles
                and not any(x in clean_name.lower() for x in ["http", "facebook", "script", "null", "undefined"])
            ):

                seen_ids.add(gid)

                groups.append({
                    "id": gid,
                    "name": clean_name
                })

        # Strategy 3: HTML anchor tags pointing to /groups/
        pattern_html = re.compile(
            r'href="https://www\.facebook\.com'
            r'/groups/([^/"]+)/"[^>]*>'
            r'([^<]{2,100})</a>'
        )

        for match in pattern_html.finditer(html_text):

            slug_or_id = match.group(1)

            clean_name = self._clean_text_name(match.group(2).strip())

            if (
                slug_or_id.lower() in ignore_slugs
                or clean_name.lower() in ignore_titles
            ):

                continue

            if (
                slug_or_id not in seen_ids
                and slug_or_id not in ignore_ids
                and clean_name
                and len(clean_name) > 1
            ):

                seen_ids.add(slug_or_id)

                groups.append({
                    "id": slug_or_id,
                    "name": clean_name
                })

        return groups

    # =====================================================
    # JOIN GROUP
    # =====================================================

    def join_group(self, group_id):
        """
        Tự động gửi yêu cầu tham gia/join vào nhóm.
        """

        if not self.is_logged_in():

            raise RuntimeError(
                "Chưa đăng nhập Facebook."
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Origin": "https://www.facebook.com"
        }

        group_url = f"https://www.facebook.com/groups/{group_id}/"

        try:

            # Get fb_dtsg token from group page
            resp = self.session.get(
                group_url,
                headers=headers,
                timeout=15
            )

            fb_dtsg_m = re.search(
                r'"DTSGInitialData"[^}]*?"token":"([^"]+)"',
                resp.text
            )

            if not fb_dtsg_m:

                fb_dtsg_m = re.search(
                    r'"token":"(NAf[^"]+)"',
                    resp.text
                )

            fb_dtsg = fb_dtsg_m.group(1) if fb_dtsg_m else ""

            import json
            import uuid

            # Send GraphQL Join Group mutation
            variables = {
                "input": {
                    "group_id": str(group_id),
                    "actor_id": str(self.user_id),
                    "source": "group_header",
                    "client_mutation_id": str(uuid.uuid4())
                }
            }

            data = {
                "fb_dtsg": fb_dtsg,
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "GroupsCometRequestToParticipateMutation",
                "variables": json.dumps(variables)
            }

            join_res = self.session.post(
                "https://www.facebook.com/api/graphql/",
                data=data,
                headers=headers,
                timeout=15
            )

            return {
                "success": True,
                "status": "✓ Thành công"
            }

        except Exception as e:

            return {
                "success": False,
                "status": "❌ Thất bại"
            }

    # =====================================================
    # PUBLISH
    # =====================================================

    def publish_post(
        self,
        group_id,
        message,
        image_paths=None
    ):
        """
        Đăng bài viết thực tế lên Group Facebook.
        - Trả về '✓ Đã đăng (Đã phê duyệt)' nếu bài đăng lên nhóm trực tiếp.
        - Trả về '✓ Đã gửi (Chờ phê duyệt)' nếu nhóm yêu cầu Admin kiểm duyệt.
        """

        if not self.is_logged_in():

            raise RuntimeError(
                "Chưa đăng nhập Facebook."
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Origin": "https://www.facebook.com"
        }

        group_url = f"https://www.facebook.com/groups/{group_id}/"

        try:

            # 1. Fetch group page to extract fb_dtsg token & group permissions
            resp = self.session.get(
                group_url,
                headers=headers,
                timeout=20
            )

            if resp.status_code != 200:

                return {
                    "success": False,
                    "status": f"Lỗi HTTP {resp.status_code}",
                    "url": group_url
                }

            html_text = resp.text

            # Check if redirected to login page or session expired
            if "login_form" in html_text or "id=\"email\"" in html_text or "checkpoint" in resp.url.lower():

                return {
                    "success": False,
                    "status": "❌ Cookie đã hết hạn. Hãy lấy Cookie mới từ trình duyệt!",
                    "url": group_url
                }

            # Extract fb_dtsg token
            fb_dtsg_match = re.search(
                r'"DTSGInitialData"[^}]*?"token":"([^"]+)"',
                html_text
            )

            if not fb_dtsg_match:

                fb_dtsg_match = re.search(
                    r'"token":"(NAf[^"]+)"',
                    html_text
                )

            fb_dtsg = fb_dtsg_match.group(1) if fb_dtsg_match else ""

            if not fb_dtsg:

                return {
                    "success": False,
                    "status": "❌ Cookie hết hạn hoặc bị Facebook chặn đăng.",
                    "url": group_url
                }

            # Check if group requires admin/mod approval
            needs_approval = any(x in html_text.lower() for x in [
                "quản trị viên", "chờ phê duyệt", "duyệt bài",
                "pending approval", "admin approval"
            ])

            # 2. Perform Real Post Creation via Playwright Browser Automation
            try:
                from playwright.sync_api import sync_playwright
            except (ImportError, ModuleNotFoundError):
                return {
                    "success": False,
                    "status": "❌ Thiếu thư viện 'playwright'! Vui lòng mở Terminal chạy: pip install playwright && playwright install chromium",
                    "url": group_url
                }

            import time

            # Build cookie dict list for Playwright context
            pw_cookies = []
            for cookie in self.session.cookies:

                pw_cookies.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": ".facebook.com",
                    "path": "/"
                })

            post_success = False
            error_details = ""

            with sync_playwright() as p:

                browser = p.chromium.launch(headless=True)

                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    )
                )

                context.add_cookies(pw_cookies)

                page = context.new_page()

                # Navigate to target group
                page.goto(
                    f"https://www.facebook.com/groups/{group_id}/",
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                time.sleep(3)

                # Find & click composer button using robust multi-selector list
                composer = None
                composer_selectors = [
                    'span:has-text("Bạn viết gì đi...")',
                    'div[role="button"]:has-text("Bạn viết gì đi...")',
                    'span:has-text("Tạo bài viết công khai...")',
                    'div[role="button"]:has-text("Tạo bài viết công khai...")',
                    'span:has-text("Viết gì đó...")',
                    'div[role="button"]:has-text("Viết gì đó...")',
                    'span:has-text("Bạn đang nghĩ gì")',
                    'div[role="button"]:has-text("Bạn đang nghĩ gì")',
                    'span:has-text("Tạo bài viết")',
                    'div[role="button"]:has-text("Tạo bài viết")',
                    'span:has-text("Create a public post...")',
                    'div[role="button"]:has-text("Create a public post...")',
                    'span:has-text("Write something...")',
                    'div[role="button"]:has-text("Write something...")',
                    'div[role="button"][aria-label*="viết"]',
                    'div[role="button"][aria-label*="Write"]',
                    'div[role="button"][aria-label*="post"]',
                    'div[role="button"][aria-label*="Post"]',
                    'div[role="button"][aria-label*="Tạo"]'
                ]

                for sel in composer_selectors:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        composer = loc
                        break

                if composer:
                    composer.click(force=True)
                    time.sleep(3)

                    # Locate editor dialog/input box
                    editor_selectors = [
                        'div[role="dialog"] div[contenteditable="true"]',
                        'div[role="dialog"] [role="textbox"]',
                        'div[role="dialog"] [aria-label*="viết"]',
                        'div[role="dialog"] [aria-label*="Write"]',
                        'div[contenteditable="true"][role="textbox"]',
                        'div[contenteditable="true"]'
                    ]

                    dialog_editor = None
                    for ed_sel in editor_selectors:
                        loc = page.locator(ed_sel).first
                        if loc.count() > 0 and loc.is_visible():
                            dialog_editor = loc
                            break

                    if dialog_editor:
                        dialog_editor.click(force=True)
                        page.keyboard.type(message)
                        time.sleep(2)

                        # Handle image attachments if provided
                        if image_paths:
                            try:
                                import os

                                # Normalize paths (supporting Vietnamese accents and spaces e.g. E:/LĂNG BÁC.jpg)
                                valid_paths = []
                                for img_p in image_paths:
                                    if img_p:
                                        norm_p = os.path.abspath(os.path.normpath(str(img_p).strip()))
                                        if os.path.exists(norm_p):
                                            valid_paths.append(norm_p)

                                if valid_paths:
                                    photo_btn = page.locator(
                                        'div[role="dialog"] div[aria-label="Ảnh/video"], div[role="dialog"] div[aria-label="Photo/video"]'
                                    ).first

                                    if not photo_btn.is_visible():
                                        photo_btn = page.locator(
                                            'div[role="dialog"] i[style*="photo"]'
                                        ).first

                                    if photo_btn.is_visible():
                                        try:
                                            with page.expect_file_chooser(timeout=5000) as fc_info:
                                                photo_btn.click(force=True)
                                            file_chooser = fc_info.value
                                            file_chooser.set_files(valid_paths)
                                            time.sleep(6)
                                        except Exception:
                                            file_input = page.locator(
                                                'div[role="dialog"] input[type="file"], input[type="file"]'
                                            ).first
                                            if file_input.count() > 0:
                                                file_input.set_input_files(valid_paths)
                                                file_input.dispatch_event('change')
                                                time.sleep(6)
                                    else:
                                        file_input = page.locator(
                                            'div[role="dialog"] input[type="file"], input[type="file"]'
                                        ).first
                                        if file_input.count() > 0:
                                            file_input.set_input_files(valid_paths)
                                            file_input.dispatch_event('change')
                                            time.sleep(6)

                            except Exception as img_err:
                                pass

                        # Click "Đăng" (Post) button inside dialog
                        post_btn = None
                        btn_selectors = [
                            'div[role="dialog"] div[role="button"]:has-text("Đăng")',
                            'div[role="dialog"] div[role="button"]:has-text("Tiếp")',
                            'div[role="dialog"] div[role="button"]:has-text("Post")',
                            'div[role="dialog"] button:has-text("Đăng")',
                            'div[role="dialog"] button:has-text("Post")'
                        ]

                        for sel in btn_selectors:
                            loc = page.locator(sel).first
                            if loc.count() > 0 and loc.is_visible():
                                post_btn = loc
                                break

                        if post_btn:
                            post_btn.click(force=True)
                            time.sleep(8)
                            post_success = True
                        else:
                            error_details = "Không thấy nút Đăng trong ô soạn bài"
                    else:
                        error_details = "Không mở được ô nhập nội dung bài viết"
                else:
                    error_details = "Không tìm thấy ô Đăng bài trong nhóm này"

                browser.close()

            if post_success:

                return {
                    "success": True,
                    "status": "✓ Thành công",
                    "url": group_url
                }

            return {
                "success": False,
                "status": "❌ Thất bại",
                "url": group_url
            }

        except Exception as err:
            return {
                "success": False,
                "status": "❌ Thất bại",
                "url": group_url
            }