import sys
import os
import subprocess
import keyboard
import threading
import json
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, QMainWindow, 
                            QLabel, QVBoxLayout, QWidget, QPushButton, QLineEdit, 
                            QHBoxLayout, QGroupBox, QGridLayout, QFrame, QMessageBox, 
                            QStackedWidget, QCheckBox)
from PyQt5.QtGui import QIcon, QKeySequence, QFont
from PyQt5.QtCore import Qt

class TrayApp(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        # 設定默認快捷鍵
        self.default_hotkeys = {
            "截圖翻譯": "alt+g",
            "複製翻譯": "shift+c",
            "複製原文": "ctrl+c",
            "智慧濾鏡": "alt+f",
            # "快速保存": "ctrl+shift+s"
        }
        
        # 設定配置文件路徑
        config_dir = os.path.join(os.path.dirname(__file__), "files", "config")
        os.makedirs(config_dir, exist_ok=True)  # 確保配置目錄存在
        
        self.config_file = os.path.join(config_dir, "hotkey_config.json")
        self.api_config_file = os.path.join(config_dir, "api_config.json")
        
        # 初始化狀態變數
        self.current_hotkeys = self.load_hotkey_config()
        self.api_keys = self.load_api_config()
        self.current_editing = None
        self.is_executing = False
        self.current_process = None
        self.is_editing_hotkey = False
        self.hotkey_inputs = {}
        
        # 設定應用圖標
        self.app_icon = QIcon("files/icons/mod300_icon.png")
        self.setWindowIcon(self.app_icon)
        
        # 初始化UI
        self.init_ui()
        
        # 設定系統托盤
        self.setup_tray_icon()
        
        # 註冊快捷鍵
        self.register_screenshot_hotkey()

    def setup_tray_icon(self):
        """設定系統托盤圖示"""
        self.tray_icon = QSystemTrayIcon(self.app_icon, self.app)
        self.tray_menu = QMenu()
        
        # 設定托盤圖示點擊事件
        self.tray_icon.activated.connect(self.show_window)
        
        # 添加選單項目
        show_action = QAction("顯示設定", self.tray_menu)
        show_action.triggered.connect(self.show)
        self.tray_menu.addAction(show_action)
        
        # "退出" 選單
        exit_action = QAction("退出", self.tray_menu)
        exit_action.triggered.connect(self.exit_app)
        self.tray_menu.addAction(exit_action)
        
        # 設定托盤圖示的右鍵選單
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # 顯示系統托盤圖示
        self.tray_icon.show()

    def init_ui(self):
        """初始化 UI 窗口"""
        self.setWindowTitle("截圖翻搜")
        self.setGeometry(100, 100, 500, 400)  # 增加窗口尺寸
        #self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 視窗置頂
        
        # 主佈局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 創建左側選單和右側內容區域的水平佈局
        h_layout = QHBoxLayout()
        
        # 左側選單
        self.menu_widget = QWidget()
        self.menu_widget.setFixedWidth(100)  # 設定固定寬度
        menu_layout = QVBoxLayout(self.menu_widget)
        menu_layout.setSpacing(0)  # 移除按鈕之間的間距
        menu_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加選單按鈕 - 參考圖片樣式
        self.hotkey_btn = QPushButton(" 快 捷 鍵")
        self.hotkey_btn.setFont(QFont("Arial", 10))
        self.hotkey_btn.setMinimumHeight(40)
        self.hotkey_btn.setIcon(QIcon("files/icons/01_key.png"))  # 假設有圖標
        self.hotkey_btn.setStyleSheet("""
            QPushButton {
                border: none;
                text-align: left;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.hotkey_btn.clicked.connect(lambda: self.show_page("hotkey"))
        menu_layout.addWidget(self.hotkey_btn)
        
        self.api_btn = QPushButton(" 翻譯設定")
        self.api_btn.setFont(QFont("Arial", 10))
        self.api_btn.setMinimumHeight(40)
        self.api_btn.setIcon(QIcon("files/icons/02_text.png"))  # 假設有圖標
        self.api_btn.setStyleSheet("""
            QPushButton {
                border: none;
                text-align: left;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.api_btn.clicked.connect(lambda: self.show_page("api"))
        menu_layout.addWidget(self.api_btn)
        
        # 添加更多選單按鈕
        menu_buttons = [
            (" 智慧濾鏡", None, "files/icons/screenshot.png"),
            (" 圖　　網", None, "files/icons/paste.png"),
        ]
        
        for btn_text, callback, icon_path in menu_buttons:
            btn = QPushButton(btn_text)
            btn.setFont(QFont("Arial", 10))
            btn.setMinimumHeight(40)
            if icon_path:
                btn.setIcon(QIcon(icon_path))
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    text-align: left;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)
            if callback:
                btn.clicked.connect(callback)
            else:
                btn.setEnabled(False)  # 暫時禁用沒有功能的按鈕
            menu_layout.addWidget(btn)
        
        menu_layout.addStretch()
        h_layout.addWidget(self.menu_widget)
        
        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #e0e0e0;")
        h_layout.addWidget(line)
        
        # 右側內容區域 - 使用堆疊佈局
        self.content_stack = QStackedWidget()
        
        # 創建組合鍵頁面
        self.hotkey_page = QWidget()
        self.setup_hotkey_page()
        self.content_stack.addWidget(self.hotkey_page)
        
        # 創建API設定頁面
        self.api_page = QWidget()
        self.setup_api_page()
        self.content_stack.addWidget(self.api_page)
        
        h_layout.addWidget(self.content_stack)
        h_layout.setStretch(0, 1)  # 左側選單佔比
        h_layout.setStretch(2, 4)  # 右側內容區域佔比
        
        main_layout.addLayout(h_layout)
        
        # 設置主容器
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # 默認顯示組合鍵頁面
        self.show_page("hotkey")
        
        # 安裝事件過濾器以捕獲按鍵事件
        self.installEventFilter(self)

    def setup_hotkey_page(self):
        """設置組合鍵頁面"""
        layout = QVBoxLayout(self.hotkey_page)
        layout.setSpacing(15)
        
        # 標題
        title_label = QLabel("快捷鍵設定")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 快捷鍵設定區域
        hotkey_group = QGroupBox("")
        hotkey_layout = QGridLayout()
        hotkey_layout.setVerticalSpacing(15)
        hotkey_layout.setHorizontalSpacing(10)
        
        # 創建快捷鍵輸入框和清除按鈕
        self.clear_buttons = {}
        self.hotkey_inputs = {}
        
        row = 0
        for action, default_key in self.current_hotkeys.items():
            # 動作標籤
            action_label = QLabel(action)
            action_label.setFont(QFont("Arial", 10))
            hotkey_layout.addWidget(action_label, row, 0)
            
            # 快捷鍵輸入框
            hotkey_input = QLineEdit()
            hotkey_input.setText(default_key)
            hotkey_input.setReadOnly(True)
            hotkey_input.setAlignment(Qt.AlignCenter)
            hotkey_input.setFont(QFont("Arial", 10))
            hotkey_input.setMinimumHeight(30)
            hotkey_input.setMinimumWidth(200)
            hotkey_input.setFixedWidth(200)  # 固定寬度為200像素
            hotkey_input.installEventFilter(self)
            hotkey_input.setObjectName(action)  # 用於識別哪個動作的輸入框
            self.hotkey_inputs[action] = hotkey_input
            hotkey_layout.addWidget(hotkey_input, row, 1)
            
            # 清除按鈕
            clear_button = QPushButton("×")
            clear_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 15px;
                    font-weight: bold;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            clear_button.clicked.connect(lambda checked, a=action: self.clear_hotkey(a))
            self.clear_buttons[action] = clear_button
            hotkey_layout.addWidget(clear_button, row, 2)
            
            row += 1
        
        # 設置列寬比例
        hotkey_layout.setColumnStretch(0, 1)  # 動作標籤
        hotkey_layout.setColumnStretch(1, 2)  # 快捷鍵輸入框
        hotkey_layout.setColumnStretch(2, 0)  # 清除按鈕
        
        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)
        
        # 狀態提示
        self.status_label = QLabel("點擊輸入框設定新的快捷鍵")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 按鈕區域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 恢復默認按鈕
        self.default_btn = QPushButton("恢復默認")
        self.default_btn.setMinimumHeight(40)
        self.default_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.default_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.default_btn.clicked.connect(self.restore_default_hotkeys)
        button_layout.addWidget(self.default_btn)
        
        # 隱藏視窗按鈕
        self.hide_btn = QPushButton("隱藏視窗")
        self.hide_btn.setMinimumHeight(40)
        self.hide_btn.setFont(QFont("Arial", 10))
        self.hide_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.hide_btn.clicked.connect(self.hide)
        button_layout.addWidget(self.hide_btn)
        
        layout.addLayout(button_layout)

    def setup_api_page(self):
        """設置API設定頁面"""
        layout = QVBoxLayout(self.api_page)
        layout.setSpacing(15)
        
        # 標題
        title_label = QLabel("API 設定")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # API 选择说明
        api_info_label = QLabel("請勾選一個要使用的API")
        api_info_label.setFont(QFont("Arial", 10))
        layout.addWidget(api_info_label)
        
        # API 設定區域 - 使用單一框架
        api_group = QGroupBox("")
        api_layout = QGridLayout()
        api_layout.setVerticalSpacing(15)
        api_layout.setHorizontalSpacing(10)
        
        # Gemini API 設定
        self.gemini_enabled = QCheckBox("Gemini API")
        self.gemini_enabled.setFont(QFont("Arial", 10, QFont.Bold))
        self.gemini_enabled.setChecked(self.api_keys.get("gemini_enabled", False))
        self.gemini_enabled.stateChanged.connect(lambda state: self.toggle_api_selection("gemini", state))
        api_layout.addWidget(self.gemini_enabled, 0, 0)
        
        # Gemini API Key 輸入
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.Password)  # 密碼模式
        self.gemini_key_input.setText(self.api_keys.get("gemini", ""))
        self.gemini_key_input.setMinimumWidth(250)
        api_layout.addWidget(self.gemini_key_input, 0, 1)
        
        # 顯示/隱藏密碼按鈕
        self.gemini_show_btn = QPushButton("顯示")
        self.gemini_show_btn.setFixedWidth(60)
        self.gemini_show_btn.clicked.connect(lambda: self.toggle_password_visibility(self.gemini_key_input, self.gemini_show_btn))
        api_layout.addWidget(self.gemini_show_btn, 0, 2)
        
        # GPT API 設定
        self.gpt_enabled = QCheckBox("GPT API")
        self.gpt_enabled.setFont(QFont("Arial", 10, QFont.Bold))
        self.gpt_enabled.setChecked(self.api_keys.get("gpt_enabled", False))
        self.gpt_enabled.stateChanged.connect(lambda state: self.toggle_api_selection("gpt", state))
        api_layout.addWidget(self.gpt_enabled, 1, 0)
        
        # GPT API Key 輸入
        self.gpt_key_input = QLineEdit()
        self.gpt_key_input.setEchoMode(QLineEdit.Password)  # 密碼模式
        self.gpt_key_input.setText(self.api_keys.get("gpt", ""))
        self.gpt_key_input.setMinimumWidth(250)
        api_layout.addWidget(self.gpt_key_input, 1, 1)
        
        # 顯示/隱藏密碼按鈕
        self.gpt_show_btn = QPushButton("顯示")
        self.gpt_show_btn.setFixedWidth(60)
        self.gpt_show_btn.clicked.connect(lambda: self.toggle_password_visibility(self.gpt_key_input, self.gpt_show_btn))
        api_layout.addWidget(self.gpt_show_btn, 1, 2)
        
        # 設置列寬比例
        api_layout.setColumnStretch(0, 1)  # 勾選框
        api_layout.setColumnStretch(1, 4)  # 輸入框
        api_layout.setColumnStretch(2, 0)  # 顯示按鈕
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 保存按鈕
        save_layout = QHBoxLayout()
        self.api_save_btn = QPushButton("保存設定")
        self.api_save_btn.setMinimumHeight(40)
        self.api_save_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.api_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.api_save_btn.clicked.connect(self.save_api_settings)
        save_layout.addWidget(self.api_save_btn)
        
        layout.addLayout(save_layout)
        layout.addStretch()

    def toggle_password_visibility(self, input_field, button):
        """切換密碼顯示/隱藏"""
        if input_field.echoMode() == QLineEdit.Password:
            input_field.setEchoMode(QLineEdit.Normal)
            button.setText("隱藏")
        else:
            input_field.setEchoMode(QLineEdit.Password)
            button.setText("顯示")

    def toggle_api_selection(self, api_name, state):
        """確保只有一個API被選中"""
        if state == Qt.Checked:
            if api_name == "gemini":
                self.gpt_enabled.setChecked(False)
            else:
                self.gemini_enabled.setChecked(False)

    def show_page(self, page_name):
        """顯示指定的頁面"""
        # 重置所有按鈕樣式
        for btn in [self.hotkey_btn, self.api_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    text-align: left;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)
        
        if page_name == "hotkey":
            self.content_stack.setCurrentWidget(self.hotkey_page)
            self.hotkey_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    text-align: left;
                    padding: 8px;
                    border-radius: 4px;
                    background-color: #4285f4;
                    color: white;
                }
            """)
        elif page_name == "api":
            self.content_stack.setCurrentWidget(self.api_page)
            self.api_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    text-align: left;
                    padding: 8px;
                    border-radius: 4px;
                    background-color: #4285f4;
                    color: white;
                }
            """)

    def save_api_settings(self):
        """保存API設定"""
        # 檢查是否至少選擇了一個API
        if not self.gemini_enabled.isChecked() and not self.gpt_enabled.isChecked():
            QMessageBox.warning(self, "設定錯誤", "請至少選擇一個API！")
            return
            
        # 檢查選中的API是否有輸入key
        if self.gemini_enabled.isChecked() and not self.gemini_key_input.text().strip():
            QMessageBox.warning(self, "設定錯誤", "請輸入Gemini API Key！")
            return
            
        if self.gpt_enabled.isChecked() and not self.gpt_key_input.text().strip():
            QMessageBox.warning(self, "設定錯誤", "請輸入GPT API Key！")
            return
        
        self.api_keys = {
            "gemini": self.gemini_key_input.text().strip(),
            "gemini_enabled": self.gemini_enabled.isChecked(),
            "gpt": self.gpt_key_input.text().strip(),
            "gpt_enabled": self.gpt_enabled.isChecked()
        }
        
        if self.save_api_config():
            QMessageBox.information(self, "保存成功", "API設定已成功保存！")
        else:
            QMessageBox.warning(self, "保存失敗", "保存API設定時發生錯誤！")

    def load_api_config(self):
        """從JSON文件加載API配置"""
        try:
            if os.path.exists(self.api_config_file):
                with open(self.api_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果文件不存在，創建默認配置
                default_config = {
                    "gemini": "",
                    "gemini_enabled": False,
                    "gpt": "",
                    "gpt_enabled": False
                }
                
                # 確保目錄存在
                config_dir = os.path.dirname(self.api_config_file)
                os.makedirs(config_dir, exist_ok=True)
                
                # 保存默認配置到文件
                with open(self.api_config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=4)
                return default_config
        except Exception as e:
            print(f"加載API配置文件時出錯: {e}")
            return {
                "gemini": "",
                "gemini_enabled": False,
                "gpt": "",
                "gpt_enabled": False
            }
    
    def save_api_config(self):
        """保存API配置到JSON文件"""
        try:
            # 確保目錄存在
            config_dir = os.path.dirname(self.api_config_file)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(self.api_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.api_keys, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存API配置文件時出錯: {e}")
            return False

    def show_window(self, reason):
        """當點擊系統托盤圖示時顯示 UI"""
        if reason == QSystemTrayIcon.Trigger:  # 左鍵點擊
            self.show()
            self.activateWindow()  # 確保視窗獲得焦點

    def register_screenshot_hotkey(self):
        """註冊所有快捷鍵"""
        # 設置編輯狀態為False
        self.is_editing_hotkey = False
        
        # 定義功能與對應的腳本路徑
        hotkey_functions = {
            "截圖翻譯": {"function": self.execute_script, "args": ["mod203_translate_ocr.py"]},
            "智慧濾鏡": {"function": self.execute_script, "args": ["mod204_filter_image.py"]},
            # 可以在這裡添加更多功能
            # "複製翻譯": {"function": self.some_function, "args": [...]},
            # "複製原文": {"function": self.some_function, "args": [...]},
        }
        
        # 註冊所有快捷鍵
        for action, hotkey in self.current_hotkeys.items():
            if hotkey and action in hotkey_functions:
                try:
                    func = hotkey_functions[action]["function"]
                    args = hotkey_functions[action]["args"]
                    keyboard.add_hotkey(hotkey, func, args=args)
                except Exception as e:
                    self.status_label.setText(f"註冊快捷鍵錯誤 ({action}): {e}")
                    self.status_label.setStyleSheet("color: #f44336;")

    def execute_script(self, script_name):
        """執行指定的腳本"""
        # 如果正在編輯快捷鍵或已經在執行中，不執行功能
        if self.is_editing_hotkey or self.is_executing:
            return
            
        # 設置執行狀態為True
        self.is_executing = True
        
        try:
            # 執行腳本
            script_path = os.path.join(os.path.dirname(__file__), script_name)
            self.current_process = subprocess.Popen([sys.executable, script_path], shell=True)
            
            # 創建監控線程
            monitor_thread = threading.Thread(target=self.monitor_process, args=(self.current_process,))
            monitor_thread.daemon = True
            monitor_thread.start()
            
        except Exception as e:
            print(f"執行腳本 {script_name} 時發生錯誤: {e}")
            self.is_executing = False

    def monitor_process(self, process):
        """監控進程，當進程結束時重置執行狀態"""
        process.wait()  # 等待進程結束
        self.is_executing = False
        self.current_process = None

    def eventFilter(self, obj, event):
        """事件過濾器，用於捕獲按鍵事件"""
        # 檢查是否是輸入框的點擊事件
        if event.type() == event.MouseButtonPress and isinstance(obj, QLineEdit):
            action = obj.objectName()
            if action in self.current_hotkeys:
                # 先重置所有輸入框的樣式
                self.reset_all_input_styles()
                
                # 設置當前編輯的快捷鍵
                self.current_editing = action
                
                # 設置選中樣式
                self.hotkey_inputs[action].setStyleSheet("background-color: #e3f2fd; border: 1px solid #2196F3;")
                self.status_label.setText(f"請按下新的快捷鍵組合 ({action})，當前: {self.hotkey_inputs[action].text()}")
                self.status_label.setStyleSheet("color: #2196F3;")
                
                # 設置編輯狀態為True並暫時移除快捷鍵註冊
                self.is_editing_hotkey = True
                if self.current_hotkeys["截圖翻譯"]:
                    try:
                        keyboard.remove_hotkey(self.current_hotkeys["截圖翻譯"])
                    except:
                        pass
                
                return True
        
        # 如果有正在編輯的快捷鍵，捕獲按鍵事件
        if self.current_editing and event.type() == event.KeyPress:
            # 獲取按鍵組合
            new_hotkey = self.get_hotkey_from_event(event)
            if not new_hotkey:
                return True
            
            # 檢查是否與其他快捷鍵重複
            duplicate_action = self.check_duplicate_hotkey(new_hotkey)
            if duplicate_action and duplicate_action != self.current_editing:
                # 詢問是否取代
                reply = QMessageBox.question(
                    self, 
                    "快捷鍵重複", 
                    f"快捷鍵 '{new_hotkey}' 已被 '{duplicate_action}' 使用！\n是否取代？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # 清除重複的快捷鍵
                    self.hotkey_inputs[duplicate_action].clear()
                    self.current_hotkeys[duplicate_action] = ""
                    
                    # 更新當前編輯的快捷鍵
                    self.update_hotkey(self.current_editing, new_hotkey)
                else:
                    # 用戶選擇不取代，重置當前編輯狀態
                    self.hotkey_inputs[self.current_editing].setStyleSheet("")
                    self.current_editing = None
                    
                    # 重新註冊截圖翻譯的快捷鍵
                    self.register_screenshot_hotkey()
                return True
            
            # 更新輸入框並自動儲存
            if self.current_editing:
                self.update_hotkey(self.current_editing, new_hotkey)
                return True
        
        return super().eventFilter(obj, event)
    
    def get_hotkey_from_event(self, event):
        """從按鍵事件獲取快捷鍵字符串"""
        modifiers = event.modifiers()
        key = event.key()
        
        # 組合快捷鍵字符串
        hotkey_parts = []
        
        if modifiers & Qt.ControlModifier:
            hotkey_parts.append("ctrl")
        if modifiers & Qt.ShiftModifier:
            hotkey_parts.append("shift")
        if modifiers & Qt.AltModifier:
            hotkey_parts.append("alt")
            
        # 添加主鍵
        if key == Qt.Key_Escape:
            key_name = "esc"
        elif key == Qt.Key_Control or key == Qt.Key_Shift or key == Qt.Key_Alt:
            # 忽略單獨的修飾鍵
            return None
        else:
            key_name = chr(key).lower() if key < 256 else QKeySequence(key).toString().lower()
        
        hotkey_parts.append(key_name)
        
        # 組合成完整的快捷鍵
        return "+".join(hotkey_parts)
    
    def update_hotkey(self, action, new_hotkey):
        """更新快捷鍵並自動儲存"""
        # 清空並設置新的快捷鍵
        self.hotkey_inputs[action].clear()
        self.hotkey_inputs[action].setText(new_hotkey)
        self.hotkey_inputs[action].setStyleSheet("")
        
        # 更新快捷鍵字典
        self.current_hotkeys[action] = new_hotkey
        
        # 保存配置到文件
        self.save_hotkey_config()
        
        # 重置編輯狀態
        self.current_editing = None
        
        # 重新註冊截圖翻譯的快捷鍵
        self.register_screenshot_hotkey()
        
        self.status_label.setText(f"已設定並儲存 {action} 的快捷鍵為: {new_hotkey}")
        self.status_label.setStyleSheet("color: #4CAF50;")

    def check_duplicate_hotkey(self, new_hotkey):
        """檢查快捷鍵是否重複，返回重複的動作名稱，如果沒有重複則返回None"""
        if not new_hotkey:
            return None
            
        for action, hotkey in self.current_hotkeys.items():
            if hotkey == new_hotkey:
                return action
        return None

    def reset_all_input_styles(self):
        """重置所有輸入框的樣式為默認樣式"""
        for input_field in self.hotkey_inputs.values():
            input_field.setStyleSheet("")

    def clear_hotkey(self, action):
        """清除特定動作的快捷鍵"""
        # 清空輸入框
        self.hotkey_inputs[action].clear()
        
        # 如果是截圖翻譯的快捷鍵，移除註冊
        if action == "截圖翻譯" and self.current_hotkeys[action]:
            try:
                keyboard.remove_hotkey(self.current_hotkeys[action])
            except:
                pass
        
        # 更新快捷鍵字典
        self.current_hotkeys[action] = ""
        
        # 保存配置到文件
        self.save_hotkey_config()
        
        self.status_label.setText(f"已清除 {action} 的快捷鍵")
        self.status_label.setStyleSheet("color: #f44336;")

    def restore_default_hotkeys(self):
        """恢復默認快捷鍵設定"""
        try:
            # 先重置所有輸入框的樣式，取消藍色狀態
            self.reset_all_input_styles()
            
            # 重置編輯狀態
            self.current_editing = None
            
            # 詢問用戶是否確定要恢復默認設定
            reply = QMessageBox.question(
                self, 
                "恢復默認設定", 
                "確定要恢復所有快捷鍵為默認設定嗎？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
                
            # 移除截圖翻譯的快捷鍵
            if self.current_hotkeys["截圖翻譯"]:
                try:
                    keyboard.remove_hotkey(self.current_hotkeys["截圖翻譯"])
                except:
                    pass
            
            # 恢復默認快捷鍵
            self.current_hotkeys = self.default_hotkeys.copy()
            
            # 保存配置到文件
            self.save_hotkey_config()
            
            # 更新所有輸入框
            for action, hotkey in self.current_hotkeys.items():
                self.hotkey_inputs[action].setText(hotkey)
            
            # 重新註冊截圖翻譯的快捷鍵
            self.register_screenshot_hotkey()
            
            self.status_label.setText("已恢復所有快捷鍵為默認設定！")
            self.status_label.setStyleSheet("color: #4CAF50;")
        except Exception as e:
            self.status_label.setText(f"錯誤: {e}")
            self.status_label.setStyleSheet("color: #f44336;")

    def exit_app(self):
        """退出應用程式"""
        self.tray_icon.hide()
        self.app.quit()

    def load_hotkey_config(self):
        """從JSON文件加載快捷鍵配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 確保所有默認快捷鍵都存在於加載的配置中
                config = self.default_hotkeys.copy()
                for key, value in loaded_config.items():
                    if key in config:
                        config[key] = value
                
                return config
            else:
                # 如果文件不存在，創建默認配置
                config_dir = os.path.dirname(self.config_file)
                os.makedirs(config_dir, exist_ok=True)  # 確保目錄存在
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.default_hotkeys, f, ensure_ascii=False, indent=4)
                return self.default_hotkeys.copy()
        except Exception as e:
            print(f"加載配置文件時出錯: {e}")
            return self.default_hotkeys.copy()
    
    def save_hotkey_config(self):
        """保存快捷鍵配置到JSON文件"""
        try:
            # 確保目錄存在
            config_dir = os.path.dirname(self.config_file)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_hotkeys, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件時出錯: {e}")
            return False

if __name__ == "__main__":
    # 先建立 QApplication
    app = QApplication(sys.argv)
    
    # 設置全局樣式表
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f8f8f8;
        }
        QGroupBox {
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLineEdit {
            background-color: #f0f0f0;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 5px;
        }
        QLineEdit:focus {
            border: 1px solid #4CAF50;
        }
        QLineEdit:read-only {
            color: black;
        }
    """)
    
    # 再建立 TrayApp
    tray_app = TrayApp(app)
    # 隱藏 UI
    tray_app.hide()
    # 執行應用程式
    sys.exit(app.exec_())
