import sys
import time
import os
import json
import threading
import random
from datetime import datetime, timedelta

from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QUrl,
    QTimer
)

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QFrame,
    QDialog,
    QSpinBox
)

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtNetwork import QNetworkCookie

from facebook_service import FacebookService
from excel_service import export_results

HISTORY_FILE = "history.json"


class PostingSignals(QObject):
    """Signals for background posting worker."""
    item_started = Signal(int)
    item_finished = Signal(int, dict)
    item_waiting = Signal(int, int)
    campaign_finished = Signal()


class BrowserLoginDialog(QDialog):
    """Interactive browser window to log into Facebook and auto-extract cookies."""
    cookie_captured = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đăng nhập Facebook - Tự động trích xuất Cookie")
        self.resize(1050, 750)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.info_lbl = QLabel(
            "📌 Vui lòng đăng nhập tài khoản Facebook của bạn trong cửa sổ bên dưới (nhập Email, Mật khẩu, Mã 2FA nếu có).\n"
            "⚡ Sau khi đăng nhập thành công, hệ thống sẽ tự động bắt chuỗi Cookie và hoàn tất đăng nhập ứng dụng!"
        )
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet(
            "color: #38bdf8; font-weight: bold; font-size: 13px; "
            "background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #1e293b;"
        )
        layout.addWidget(self.info_lbl)

        self.web_view = QWebEngineView()
        self.web_profile = self.web_view.page().profile()
        self.cookie_store = self.web_profile.cookieStore()

        layout.addWidget(self.web_view, 1)

        self.captured_cookies = {}
        self.is_done = False

        self.cookie_store.cookieAdded.connect(self.on_cookie_added)

        # Timer to check login completion
        self.check_timer = QTimer(self)
        self.check_timer.setInterval(1000)
        self.check_timer.timeout.connect(self.check_login_status)
        self.check_timer.start()

        # Load Facebook login URL
        self.web_view.setUrl(QUrl("https://www.facebook.com/login"))

    def on_cookie_added(self, cookie):
        domain = cookie.domain()
        if "facebook.com" in domain:
            name = cookie.name().data().decode("utf-8", errors="ignore")
            val = cookie.value().data().decode("utf-8", errors="ignore")
            self.captured_cookies[name] = val
            if name == "c_user" and not self.is_done:
                self.check_login_status()

    def check_login_status(self):
        if self.is_done:
            return

        if "c_user" in self.captured_cookies and "xs" in self.captured_cookies:
            self.is_done = True
            self.check_timer.stop()

            # Format full cookie string
            cookie_parts = []
            for k, v in self.captured_cookies.items():
                cookie_parts.append(f"{k}={v}")

            cookie_str = "; ".join(cookie_parts)

            self.info_lbl.setText("🎉 Đã lấy thành công Cookie Facebook! Đang đăng nhập vào ứng dụng...")
            self.info_lbl.setStyleSheet(
                "color: #10b981; font-weight: bold; font-size: 14px; "
                "background: #064e3b; padding: 12px; border-radius: 8px; border: 1px solid #059669;"
            )

            self.cookie_captured.emit(cookie_str)
            QTimer.singleShot(1200, self.accept)



class FacebookMarketingApp(QMainWindow):

    login_success = Signal(dict)
    login_error = Signal(str)
    groups_loaded = Signal(list)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tools")
        self.resize(1300, 880)

        self.facebook = FacebookService()
        self.images = []
        self.results = []
        self.posting_in_progress = False
        self.raw_cookie_string = ""

        self.build_ui()

        # Connect signals
        self.login_success.connect(self.on_login_success)
        self.login_error.connect(self.on_login_error)
        self.groups_loaded.connect(self.on_groups_loaded)

        # Load history saved in the last 24 hours
        self.load_saved_history()

    # =====================================================
    # UI SETUP
    # =====================================================

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Embedded WebEngine Browser (Hidden background worker engine)
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(1)
        self.web_profile = self.web_view.page().profile()
        self.cookie_store = self.web_profile.cookieStore()

        # Top-level Stacked Widget (Page 0: Login, Page 1: Dashboard)
        self.main_stack = QStackedWidget()
        main_layout.addWidget(self.main_stack, 1)

        # Build Page 0: Login
        self.login_widget = self.build_login_screen()
        self.main_stack.addWidget(self.login_widget)

        # Build Page 1: Dashboard
        self.dashboard_widget = self.build_dashboard_screen()
        self.main_stack.addWidget(self.dashboard_widget)

        # Show Login Screen initially
        self.main_stack.setCurrentIndex(0)

    # =====================================================
    # SCREEN 1: REDESIGNED PREMIUM LOGIN SCREEN
    # =====================================================

    def build_login_screen(self):
        screen = QWidget()
        screen.setObjectName("loginScreen")
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignCenter)

        # Card Container
        card = QFrame()
        card.setFixedWidth(560)
        card.setObjectName("loginCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(18)

        # Brand Badge & Title
        brand_badge = QLabel("⚡ Tools")
        brand_badge.setObjectName("loginBrandBadge")
        brand_badge.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Hệ thống Tự động hóa đăng bài")
        subtitle.setObjectName("loginSubTitle")
        subtitle.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(brand_badge)
        card_layout.addWidget(subtitle)

        # Instructions Group Box
        guide_box = QGroupBox("📌 Hướng dẫn nạp Cookie đăng nhập")
        guide_layout = QVBoxLayout(guide_box)

        guide = QLabel(
            "1. Mở trình duyệt Chrome/Edge và đăng nhập tài khoản Facebook.\n"
            "2. Nhấn phím F12 → chọn Tab Application → Cookies → facebook.com.\n"
            "3. Tìm và sao chép toàn bộ chuỗi Cookie .\n"
            "4. Dán chuỗi vào khung bên dưới và nhấn nút Đăng Nhập."
        )
        guide.setWordWrap(True)
        guide.setObjectName("guideText")
        guide_layout.addWidget(guide)

        card_layout.addWidget(guide_box)

        # Auto Browser Login Button
        self.auto_login_btn = QPushButton("🌐 ĐĂNG NHẬP TRỰC TIẾP QUA TRÌNH DUYỆT (TỰ ĐỘNG LẤY COOKIE)")
        self.auto_login_btn.setCursor(Qt.PointingHandCursor)
        self.auto_login_btn.setObjectName("autoLoginBtn")
        self.auto_login_btn.setStyleSheet("""
            QPushButton#autoLoginBtn {
                background-color: #059669;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#autoLoginBtn:hover {
                background-color: #047857;
            }
        """)
        self.auto_login_btn.clicked.connect(self.open_browser_login)
        card_layout.addWidget(self.auto_login_btn)

        # Divider Label
        or_label = QLabel("─── HOẶC DÁN CHUỖI COOKIE THỦ CÔNG ───")
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: bold;")
        card_layout.addWidget(or_label)

        # Input Area
        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText("Nhập cookies của bạn (nếu có nhấp nút Đăng Nhập bên dưới)")
        self.cookie_input.setFixedHeight(75)
        self.cookie_input.setObjectName("cookieInput")
        card_layout.addWidget(self.cookie_input)

        # Login Status Label
        self.login_status_lbl = QLabel("")
        self.login_status_lbl.setAlignment(Qt.AlignCenter)
        self.login_status_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        card_layout.addWidget(self.login_status_lbl)

        # Login Button
        self.login_btn = QPushButton("🔑 ĐĂNG NHẬP BẰNG COOKIE THỦ CÔNG")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setObjectName("loginPrimaryBtn")
        self.login_btn.clicked.connect(self.start_login)
        card_layout.addWidget(self.login_btn)

        layout.addWidget(card)
        return screen

    def open_browser_login(self):
        dialog = BrowserLoginDialog(self)
        dialog.cookie_captured.connect(self.on_browser_cookie_captured)
        dialog.exec()

    def on_browser_cookie_captured(self, cookie_str):
        self.cookie_input.setText(cookie_str)
        self.start_login()

    # =====================================================
    # SCREEN 2: REDESIGNED DASHBOARD SCREEN
    # =====================================================

    def build_dashboard_screen(self):
        screen = QWidget()
        screen.setObjectName("dashScreen")
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Top Header Bar
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)

        # Brand Title
        brand_logo = QLabel("⚡ Tools")
        brand_logo.setObjectName("headerLogo")

        # User Info Badge
        self.user_info_lbl = QLabel("🟢 Chưa xác định tài khoản")
        self.user_info_lbl.setObjectName("userInfoBadge")

        # Logout Button
        logout_btn = QPushButton(" Log out")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setObjectName("logoutBtn")
        logout_btn.clicked.connect(self.logout)

        header_layout.addWidget(brand_logo)
        header_layout.addSpacing(20)
        header_layout.addWidget(self.user_info_lbl)
        header_layout.addStretch()
        header_layout.addWidget(logout_btn)

        layout.addWidget(header_frame)

        # Navigation Pill Bar (3 Tabs)
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(10)

        self.tab_buttons = []
        tabs = [
            ("List", 0),
            ("Post", 1),
            ("History", 2)
        ]

        for text, index in tabs:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setObjectName("navTabBtn")
            if index == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, i=index: self.switch_dash_tab(i))
            nav_layout.addWidget(btn, 1)
            self.tab_buttons.append(btn)

        layout.addWidget(nav_frame)

        # Stacked Widget for Dashboard Tabs
        self.dash_stack = QStackedWidget()
        layout.addWidget(self.dash_stack, 1)

        # Build Sub-Tabs
        self.dash_stack.addWidget(self.build_group_tab())
        self.dash_stack.addWidget(self.build_post_tab())
        self.dash_stack.addWidget(self.build_history_tab())

        return screen

    # =====================================================
    # DASHBOARD TAB 1: GROUP MANAGEMENT
    # =====================================================

    def build_group_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 5, 0, 0)

        box = QGroupBox("Danh sách các Nhóm Facebook đã gia nhập")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(12)

        # Search Bar
        self.group_search = QLineEdit()
        self.group_search.setPlaceholderText("🔎 Nhập tên Group để tìm kiếm nhanh...")
        self.group_search.setObjectName("searchInput")
        self.group_search.textChanged.connect(self.filter_groups)
        box_layout.addWidget(self.group_search)

        # List Widget
        self.group_list = QListWidget()
        self.group_list.setObjectName("groupListWidget")
        self.group_list.itemChanged.connect(lambda _: self.update_selected_info())
        box_layout.addWidget(self.group_list, 1)

        # Info & Controls Bar
        controls = QHBoxLayout()

        self.group_status_lbl = QLabel("Chưa tải nhóm nào.")
        self.group_status_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")

        select_all_btn = QPushButton("☑ Chọn tất cả")
        clear_btn = QPushButton("☐ Bỏ chọn")
        refresh_btn = QPushButton("🔄 Tải lại danh sách")

        select_all_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setCursor(Qt.PointingHandCursor)

        select_all_btn.clicked.connect(self.select_all_groups)
        clear_btn.clicked.connect(self.clear_groups)
        refresh_btn.clicked.connect(self.load_real_groups)

        controls.addWidget(self.group_status_lbl)
        controls.addStretch()
        controls.addWidget(select_all_btn)
        controls.addWidget(clear_btn)
        controls.addWidget(refresh_btn)

        box_layout.addLayout(controls)
        layout.addWidget(box)

        return tab

    # =====================================================
    # DASHBOARD TAB 2: POST CREATION
    # =====================================================

    def build_post_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 5, 0, 0)

        box = QGroupBox("Soạn nội dung & Đính kèm hình ảnh Marketing")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(14)

        box_layout.addWidget(QLabel("📝 Nội dung bài đăng văn bản:"))

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Soạn nội dung quảng cáo, bài viết marketing cần đăng lên các Group...")
        self.content_edit.setObjectName("contentEdit")
        box_layout.addWidget(self.content_edit, 1)

        # Image Selection Bar
        img_card = QFrame()
        img_card.setObjectName("imgCard")
        img_layout = QHBoxLayout(img_card)
        img_layout.setContentsMargins(12, 10, 12, 10)

        choose_img_btn = QPushButton("🖼 Chọn hình ảnh từ máy tính")
        choose_img_btn.setCursor(Qt.PointingHandCursor)
        choose_img_btn.setObjectName("chooseImgBtn")
        choose_img_btn.clicked.connect(self.choose_images)

        self.image_label = QLabel("Chưa chọn hình ảnh nào")
        self.image_label.setStyleSheet("color: #94a3b8; font-weight: 500;")

        img_layout.addWidget(choose_img_btn)
        img_layout.addSpacing(10)
        img_layout.addWidget(self.image_label, 1)

        box_layout.addWidget(img_card)

        # Delay Config Card
        delay_card = QFrame()
        delay_card.setObjectName("delayCard")
        delay_main_layout = QHBoxLayout(delay_card)
        delay_main_layout.setContentsMargins(14, 10, 14, 10)
        delay_main_layout.setSpacing(8)

        delay_icon_lbl = QLabel("⏱ Khoảng cách giữa các bài đăng:")
        delay_icon_lbl.setStyleSheet("font-weight: bold; color: #38bdf8; font-size: 13px;")

        self.delay_min_spin = QSpinBox()
        self.delay_min_spin.setRange(0, 60)
        self.delay_min_spin.setValue(0)
        self.delay_min_spin.setSuffix(" phút")
        self.delay_min_spin.setFixedWidth(95)
        self.delay_min_spin.setObjectName("delaySpinBox")

        self.delay_sec_spin = QSpinBox()
        self.delay_sec_spin.setRange(0, 59)
        self.delay_sec_spin.setValue(10)
        self.delay_sec_spin.setSuffix(" giây")
        self.delay_sec_spin.setFixedWidth(95)
        self.delay_sec_spin.setObjectName("delaySpinBox")

        def on_delay_changed():
            total = self.delay_min_spin.value() * 60 + self.delay_sec_spin.value()
            if total < 1:
                self.delay_sec_spin.setValue(1)

        self.delay_min_spin.valueChanged.connect(on_delay_changed)
        self.delay_sec_spin.valueChanged.connect(on_delay_changed)

        note_lbl = QLabel("💡 Mỗi bài đăng sẽ cách nhau đúng khoảng thời gian này")
        note_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")

        delay_main_layout.addWidget(delay_icon_lbl)
        delay_main_layout.addWidget(self.delay_min_spin)
        delay_main_layout.addWidget(self.delay_sec_spin)
        delay_main_layout.addSpacing(10)
        delay_main_layout.addWidget(note_lbl, 1)

        box_layout.addWidget(delay_card)

        # Summary Info Badge
        self.post_info_lbl = QLabel("Số Group đã chọn: 0")
        self.post_info_lbl.setObjectName("summaryBadge")
        box_layout.addWidget(self.post_info_lbl)

        # Action Buttons Layout
        actions = QHBoxLayout()
        actions.setSpacing(12)

        reset_btn = QPushButton("🔄 Reset / Làm mới")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_post_form)

        preview_btn = QPushButton("👁 Xem trước bài đăng")
        preview_btn.setCursor(Qt.PointingHandCursor)
        preview_btn.clicked.connect(self.preview_post)

        self.publish_btn = QPushButton("🚀 BẮT ĐẦU ĐĂNG BÀI BÀI VIẾT")
        self.publish_btn.setCursor(Qt.PointingHandCursor)
        self.publish_btn.setObjectName("publishPrimaryBtn")
        self.publish_btn.clicked.connect(self.start_campaign)

        actions.addWidget(reset_btn)
        actions.addWidget(preview_btn)
        actions.addWidget(self.publish_btn, 1)

        box_layout.addLayout(actions)
        layout.addWidget(box)

        return tab

    # =====================================================
    # DASHBOARD TAB 3: HISTORY & RESULTS
    # =====================================================

    def build_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 5, 0, 0)

        box = QGroupBox("Báo cáo lịch sử kết quả chiến dịch đăng bài (Tự động lưu 24 giờ)")
        box_layout = QVBoxLayout(box)

        self.history_table = QTableWidget(0, 6)
        self.history_table.setObjectName("historyTable")
        self.history_table.setHorizontalHeaderLabels([
            "Group",
            "Nội dung",
            "Hình ảnh",
            "Thời gian",
            "Trạng thái",
            "Link bài đăng"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setDefaultSectionSize(44)
        box_layout.addWidget(self.history_table, 1)

        hist_actions = QHBoxLayout()
        hist_actions.setSpacing(12)

        reset_hist_btn = QPushButton("🗑 Reset / Xóa lịch sử chiến dịch")
        reset_hist_btn.setCursor(Qt.PointingHandCursor)
        reset_hist_btn.setObjectName("clearHistoryBtn")
        reset_hist_btn.clicked.connect(self.clear_campaign_history)

        export_btn = QPushButton("📤 Xuất báo cáo kết quả ra File Excel")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setObjectName("exportBtn")
        export_btn.clicked.connect(self.export_excel)

        hist_actions.addWidget(reset_hist_btn)
        hist_actions.addWidget(export_btn, 1)

        box_layout.addLayout(hist_actions)

        layout.addWidget(box)
        return tab

    # =====================================================
    # DASHBOARD NAVIGATION
    # =====================================================

    def switch_dash_tab(self, index):
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)
        self.dash_stack.setCurrentIndex(index)
        if index == 1:
            self.update_selected_info()

    # =====================================================
    # LOGIN LOGIC & COOKIE INJECTION
    # =====================================================

    def start_login(self):
        cookie = self.cookie_input.toPlainText().strip()
        if not cookie:
            QMessageBox.warning(self, "Thiếu Cookie", "Vui lòng nhập chuỗi Cookie Facebook.")
            return

        self.raw_cookie_string = cookie
        self.login_status_lbl.setText("● Đang xác thực Cookie với hệ thống Facebook...")
        self.login_status_lbl.setStyleSheet("color: #f59e0b; font-weight: bold;")
        self.login_btn.setEnabled(False)

        def worker():
            try:
                me = self.facebook.login_with_cookie(cookie)
                self.login_success.emit(me)
            except Exception as e:
                self.login_error.emit(str(e))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_login_success(self, user):
        self.login_btn.setEnabled(True)
        self.login_status_lbl.setText("")

        name = user.get("name", "Facebook User")
        uid = str(user.get("id", ""))
        self.current_user_id = uid
        self.user_info_lbl.setText(f"🟢 Tài khoản: {name} (ID: {uid})")

        # Clear previous account group list
        self.group_list.clear()
        self.group_status_lbl.setText("⏳ Đang kết nối tải danh sách nhóm từ Facebook...")
        self.group_status_lbl.setStyleSheet("color: #f59e0b;")

        # Sync cookies to Chromium WebEngine
        self.sync_cookies_to_webengine()

        # Load account-specific history (24h)
        self.load_saved_history()

        # Switch to Dashboard
        self.main_stack.setCurrentIndex(1)
        self.switch_dash_tab(0)

        # Auto load groups
        self.load_real_groups()

    def sync_cookies_to_webengine(self):
        if not self.raw_cookie_string:
            return

        import urllib.parse
        try:
            cookie_store = self.web_view.page().profile().cookieStore()
            for part in self.raw_cookie_string.split(";"):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    unquoted_val = urllib.parse.unquote(v.strip())
                    cookie = QNetworkCookie(k.strip().encode(), unquoted_val.encode())
                    cookie.setDomain(".facebook.com")
                    cookie.setPath("/")
                    cookie_store.setCookie(cookie)
        except Exception:
            pass

    def on_login_error(self, message):
        self.login_btn.setEnabled(True)
        self.login_status_lbl.setText(f"❌ {message}")
        self.login_status_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")

    def logout(self):
        self.facebook.logout()
        self.cookie_input.clear()
        self.group_list.clear()
        self.current_user_id = ""
        self.results.clear()
        self.history_table.setRowCount(0)
        self.main_stack.setCurrentIndex(0)

    # =====================================================
    # GROUP LOGIC
    # =====================================================

    def load_real_groups(self):
        if not self.facebook.is_logged_in():
            return

        self.group_status_lbl.setText("⏳ Đang kết nối tải danh sách nhóm từ Facebook...")
        self.group_status_lbl.setStyleSheet("color: #f59e0b;")

        def worker():
            try:
                groups = self.facebook.get_groups()
                self.groups_loaded.emit(groups)
            except Exception as e:
                self.groups_loaded.emit([])

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def on_groups_loaded(self, groups):
        self.group_list.clear()

        if not groups:
            self.group_status_lbl.setText("⚠ Không tìm thấy nhóm nào hoặc Cookie bị lỗi.")
            self.group_status_lbl.setStyleSheet("color: #ef4444;")
            return

        for group in groups:
            item = QListWidgetItem(group["name"])
            item.setData(Qt.UserRole, group["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.group_list.addItem(item)

        count = len(groups)
        self.group_status_lbl.setText(f"✓ Đã tải {count} nhóm thành công.")
        self.group_status_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
        self.update_selected_info()

    def filter_groups(self, text):
        query = text.lower().strip()
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            item.setHidden(query not in item.text().lower())

    def select_all_groups(self):
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked)
        self.update_selected_info()

    def clear_groups(self):
        for i in range(self.group_list.count()):
            self.group_list.item(i).setCheckState(Qt.Unchecked)
        self.update_selected_info()

    def selected_groups(self):
        selected = []
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item)
        return selected

    def update_selected_info(self):
        sel_count = len(self.selected_groups())
        tot_count = self.group_list.count()
        info_text = f"Đã chọn: {sel_count} / {tot_count} Group"
        self.post_info_lbl.setText(info_text)

    # =====================================================
    # POST & CAMPAIGN LOGIC (HISTORY ACCUMULATION & PERSISTENCE)
    # =====================================================

    def choose_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn hình ảnh từ máy tính", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if paths:
            self.images = paths
            self.image_label.setText(f"✓ Đã đính kèm {len(paths)} hình ảnh từ máy tính")
            self.image_label.setStyleSheet("color: #10b981; font-weight: bold;")

    def reset_post_form(self):
        """Reset ô soạn bài và danh sách hình ảnh nhập vào về ban đầu."""
        self.content_edit.clear()
        self.images = []
        self.image_label.setText("Chưa chọn hình ảnh nào")
        self.image_label.setStyleSheet("color: #94a3b8; font-weight: 500;")

    def preview_post(self):
        groups = self.selected_groups()
        content = self.content_edit.toPlainText().strip()

        if not groups:
            QMessageBox.warning(self, "Thiếu Group", "Hãy chọn ít nhất 1 Group trong tab '1. Danh sách Group'.")
            return
        if not content:
            QMessageBox.warning(self, "Thiếu nội dung", "Hãy nhập nội dung bài viết.")
            return

        QMessageBox.information(
            self,
            "Xem trước bài đăng",
            f"Số Group chọn: {len(groups)}\n"
            f"Số ảnh kèm theo: {len(self.images)}\n\n"
            f"--- NỘI DUNG ---\n{content}"
        )

    def start_campaign(self):
        if self.posting_in_progress:
            QMessageBox.warning(self, "Đang đăng", "Chiến dịch đăng bài đang chạy.")
            return

        groups = self.selected_groups()
        content = self.content_edit.toPlainText().strip()

        if not groups:
            QMessageBox.warning(self, "Thiếu Group", "Hãy chọn ít nhất 1 Group trong tab '1. Danh sách Group'.")
            return
        if not content:
            QMessageBox.warning(self, "Thiếu nội dung", "Hãy nhập nội dung bài viết.")
            return

        reply = QMessageBox.question(
            self,
            "Xác nhận đăng bài",
            f"Bạn có chắc chắn muốn xuất bản bài viết tới {len(groups)} Group đã chọn?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.posting_in_progress = True
        self.publish_btn.setEnabled(False)

        now_dt = datetime.now()
        now_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")

        start_index = len(self.results)
        new_batch = []

        # ACCUMULATE ROWS (Do NOT clear existing history rows)
        for item in groups:
            g_name = item.text()
            g_id = item.data(Qt.UserRole) or g_name
            row_data = {
                "timestamp": now_dt.isoformat(),
                "Group": g_name,
                "Group_ID": g_id,
                "Nội dung": content,
                "Hình ảnh": "; ".join(self.images),
                "Thời gian": now_str,
                "Trạng thái": "⏳ Đang chờ...",
                "Link bài đăng": f"https://www.facebook.com/groups/{g_id}/"
            }
            self.results.append(row_data)
            new_batch.append(row_data)

            # Insert row into table widget
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            vals = [
                g_name,
                content,
                "; ".join(self.images),
                now_str,
                "⏳ Đang chờ...",
                f"https://www.facebook.com/groups/{g_id}/"
            ]
            for col, val in enumerate(vals):
                self.history_table.setItem(row, col, QTableWidgetItem(val))

        # Save updated history file
        self.save_history()

        # Switch to History tab immediately
        self.switch_dash_tab(2)

        # Read fixed delay value from GUI (phút + giây → tổng giây)
        delay_seconds = self.delay_min_spin.value() * 60 + self.delay_sec_spin.value()
        if delay_seconds < 1:
            delay_seconds = 1

        # Instantiate Posting Signals
        self.signals = PostingSignals()
        self.signals.item_started.connect(self.on_item_started)
        self.signals.item_finished.connect(self.on_item_finished)
        self.signals.item_waiting.connect(self.on_item_waiting)
        self.signals.campaign_finished.connect(self.on_campaign_finished)

        # Snapshot images for thread safety
        batch_images = list(self.images)

        # Run posting thread for the new batch
        def campaign_worker():
            for i, res in enumerate(new_batch):
                actual_row = start_index + i
                self.signals.item_started.emit(actual_row)

                # Step 1: Auto Join / Request Join Group
                join_out = self.facebook.join_group(res["Group_ID"])

                # Step 2: Publish Post with text content & images
                out = self.facebook.publish_post(
                    res["Group_ID"],
                    res["Nội dung"],
                    batch_images
                )

                self.signals.item_finished.emit(actual_row, out)

                # Wait fixed delay before next group (if not the last post in batch)
                if i < len(new_batch) - 1:
                    next_row = actual_row + 1
                    for rem in range(delay_seconds, 0, -1):
                        self.signals.item_waiting.emit(next_row, rem)
                        time.sleep(1)

            self.signals.campaign_finished.emit()

        thread = threading.Thread(target=campaign_worker, daemon=True)
        thread.start()

    def on_item_started(self, row):
        self.history_table.setItem(row, 4, QTableWidgetItem("⏳ Đang đăng bài..."))

    def on_item_waiting(self, row, remaining):
        if row < self.history_table.rowCount():
            if remaining >= 60:
                mins = remaining // 60
                secs = remaining % 60
                time_str = f"{mins}p{secs:02d}s"
            else:
                time_str = f"{remaining}s"
            self.history_table.setItem(row, 4, QTableWidgetItem(f"⏳ Chờ đăng ({time_str})..."))

    def on_item_finished(self, row, out):
        status = "✓ Thành công" if out.get("success") else "❌ Thất bại"
        url = out.get("url", "")

        if row < len(self.results):
            self.results[row]["Trạng thái"] = status
            self.results[row]["Link bài đăng"] = url

        self.history_table.setItem(row, 4, QTableWidgetItem(status))
        self.history_table.setItem(row, 5, QTableWidgetItem(url))
        self.save_history()

    def on_campaign_finished(self):
        self.posting_in_progress = False
        self.publish_btn.setEnabled(True)
        QMessageBox.information(self, "Hoàn thành", "Đã hoàn thành chiến dịch đăng bài tới các Group!")

    # =====================================================
    # HISTORY PERSISTENCE (LƯU LỊCH SỬ THẦN TỐC THEO TỪNG TÀI KHOẢN 24H)
    # =====================================================

    def get_history_filename(self):
        if hasattr(self, 'current_user_id') and self.current_user_id:
            return f"history_{self.current_user_id}.json"
        return "history_default.json"

    def save_history(self):
        filename = self.get_history_filename()
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_saved_history(self):
        filename = self.get_history_filename()
        self.results = []
        self.history_table.setRowCount(0)

        if not os.path.exists(filename):
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            now = datetime.now()
            valid_items = []

            # Keep items created within the last 24 hours (1 day) for this specific account
            for item in data:
                ts_str = item.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if now - ts <= timedelta(hours=24):
                            valid_items.append(item)
                    except Exception:
                        valid_items.append(item)
                else:
                    valid_items.append(item)

            self.results = valid_items

            for item in self.results:
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)

                vals = [
                    item.get("Group", ""),
                    item.get("Nội dung", ""),
                    item.get("Hình ảnh", ""),
                    item.get("Thời gian", ""),
                    item.get("Trạng thái", ""),
                    item.get("Link bài đăng", "")
                ]
                for col, val in enumerate(vals):
                    self.history_table.setItem(row, col, QTableWidgetItem(val))

        except Exception:
            pass

    def clear_campaign_history(self):
        """Xóa toàn bộ lịch sử chiến dịch hiện tại và file dữ liệu lưu trữ."""
        if self.posting_in_progress:
            QMessageBox.warning(
                self,
                "Đang đăng bài",
                "Không thể reset lịch sử khi chiến dịch đăng bài đang chạy!"
            )
            return

        if not self.results and self.history_table.rowCount() == 0:
            QMessageBox.information(
                self,
                "Lịch sử trống",
                "Lịch sử chiến dịch hiện tại đang trống."
            )
            return

        reply = QMessageBox.question(
            self,
            "Xác nhận reset lịch sử",
            "Bạn có chắc chắn muốn xóa toàn bộ lịch sử kết quả chiến dịch đăng bài?\n"
            "Hành động này sẽ làm sạch bảng báo cáo và file lưu trữ trên máy tính.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.results = []
        self.history_table.setRowCount(0)

        filename = self.get_history_filename()
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception:
            pass

        QMessageBox.information(
            self,
            "Đã reset lịch sử",
            "Đã xóa toàn bộ lịch sử chiến dịch đăng bài thành công."
        )

    # =====================================================
    # EXCEL EXPORT
    # =====================================================

    def export_excel(self):
        if not self.results:
            QMessageBox.warning(self, "Không có dữ liệu", "Chưa có dữ liệu lịch sử đăng bài.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất Excel", "facebook_marketing_results.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            export_results(self.results, path)
            QMessageBox.information(self, "Thành công", f"Đã xuất file kết quả tại:\n{path}")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi xuất file", str(error))


# =========================================================
# APPLICATION ENTRYPOINT & PREMIUM STYLESHEET (AnhThuy-MTP)
# =========================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        /* GLOBAL DESIGN SYSTEM */
        QWidget {
            background-color: #0f172a;
            color: #f8fafc;
            font-size: 14px;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        }

        /* LOGIN SCREEN STYLING */
        #loginScreen {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:0.5 #1e1b4b, stop:1 #0f172a);
        }

        #loginCard {
            background: rgba(30, 41, 59, 0.95);
            border: 1px solid #334155;
            border-radius: 18px;
        }

        #loginBrandBadge {
            font-size: 32px;
            font-weight: 900;
            color: #38bdf8;
            letter-spacing: 1px;
        }

        #loginSubTitle {
            font-size: 14px;
            color: #94a3b8;
        }

        #guideText {
            color: #cbd5e1;
            line-height: 1.5;
            font-size: 13px;
        }

        #cookieInput {
            background: #090d16;
            border: 1.5px solid #334155;
            border-radius: 10px;
            padding: 10px;
            color: #f1f5f9;
        }

        #cookieInput:focus {
            border: 1.5px solid #38bdf8;
        }

        #loginPrimaryBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #4f46e5);
            color: #ffffff;
            font-weight: bold;
            font-size: 16px;
            padding: 14px;
            border: none;
            border-radius: 10px;
        }

        #loginPrimaryBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #4338ca);
        }

        /* DASHBOARD SCREEN STYLING */
        #dashScreen {
            background: #0f172a;
        }

        #headerFrame {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 14px;
        }

        #headerLogo {
            font-size: 22px;
            font-weight: 900;
            color: #38bdf8;
        }

        #userInfoBadge {
            background: #064e3b;
            color: #34d399;
            border: 1px solid #059669;
            border-radius: 8px;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 13px;
        }

        #logoutBtn {
            background: #451a03;
            color: #f97316;
            border: 1px solid #7c2d12;
            border-radius: 8px;
            padding: 6px 14px;
            font-weight: bold;
        }

        #logoutBtn:hover {
            background: #7c2d12;
            color: #ffffff;
        }

        /* NAVIGATION TAB BUTTONS */
        #navFrame {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
        }

        #navTabBtn {
            background: transparent;
            color: #94a3b8;
            font-size: 15px;
            font-weight: bold;
            padding: 12px;
            border: none;
            border-radius: 8px;
        }

        #navTabBtn:hover {
            background: #334155;
            color: #f8fafc;
        }

        #navTabBtn:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        }

        /* GROUP BOX & INPUT CONTROLS */
        QGroupBox {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 14px;
            margin-top: 8px;
            padding-top: 18px;
            font-weight: bold;
            font-size: 15px;
            color: #38bdf8;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            color: #38bdf8;
        }

        #searchInput {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px;
            color: #f8fafc;
        }

        #groupListWidget {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 6px;
        }

        #groupListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #1e293b;
            border-radius: 6px;
        }

        #groupListWidget::item:hover {
            background: #1e293b;
        }

        #contentEdit {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px;
            color: #f8fafc;
        }

        #imgCard {
            background: #0f172a;
            border: 1px dashed #475569;
            border-radius: 10px;
        }

        #delayCard {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
        }

        QSpinBox#delaySpinBox {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px 8px;
            color: #38bdf8;
            font-weight: bold;
            font-size: 13px;
        }

        QSpinBox#delaySpinBox::up-button, QSpinBox#delaySpinBox::down-button {
            background: #334155;
            border: none;
            width: 16px;
        }

        QSpinBox#delaySpinBox::up-button:hover, QSpinBox#delaySpinBox::down-button:hover {
            background: #475569;
        }

        #chooseImgBtn {
            background: #334155;
            color: #f8fafc;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 8px;
        }

        #chooseImgBtn:hover {
            background: #475569;
        }

        #summaryBadge {
            font-size: 14px;
            font-weight: bold;
            color: #38bdf8;
        }

        #publishPrimaryBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
            color: #ffffff;
            font-weight: bold;
            font-size: 16px;
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
        }

        #publishPrimaryBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
        }

        /* TABLE & EXPORT BUTTON */
        #historyTable {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            gridline-color: #334155;
        }

        QHeaderView::section {
            background: #1e293b;
            color: #94a3b8;
            font-weight: bold;
            border: 1px solid #334155;
            padding: 10px;
            font-size: 13px;
        }

        #clearHistoryBtn {
            background: #450a0a;
            color: #fca5a5;
            border: 1px solid #991b1b;
            font-weight: bold;
            padding: 10px 16px;
            border-radius: 8px;
        }

        #clearHistoryBtn:hover {
            background: #991b1b;
            color: #ffffff;
        }

        #exportBtn {
            background: #1e293b;
            color: #34d399;
            border: 1px solid #059669;
            font-weight: bold;
            padding: 10px;
            border-radius: 8px;
        }

        #exportBtn:hover {
            background: #064e3b;
            color: #ffffff;
        }

        QPushButton {
            background: #334155;
            color: #f8fafc;
            border: none;
            border-radius: 8px;
            padding: 9px 16px;
        }

        QPushButton:hover {
            background: #475569;
        }
    """)

    window = FacebookMarketingApp()
    window.show()
    sys.exit(app.exec())