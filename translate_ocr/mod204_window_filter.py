from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QTimer
import sys

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 設置視窗
        self.setWindowTitle("智慧濾鏡")
        self.setWindowFlags(Qt.FramelessWindowHint)
        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(screen.width() - 800, 0, 800, screen.height()-50)
        
        # 創建瀏覽器
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.google.com/?olud"))
        
        # 設置佈局
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        layout.setContentsMargins(0, 0, 0, 0)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # 初始化變數
        self.done = False  # 只使用一個標記來追踪是否完成
        # 連接信號
        self.browser.loadFinished.connect(self.on_page_loaded)
        
    def on_page_loaded(self, ok):
        if not ok or self.done:
            return
        # 延遲貼上圖片
        QTimer.singleShot(1500, self.paste_image)
        
    def paste_image(self):
        if self.done:
            return
        # 獲取剪貼簿並貼上
        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasImage():
            self.browser.page().triggerAction(QWebEnginePage.Paste)
            print("貼上動作完成")
            # 延遲查找元素
            QTimer.singleShot(1500, self.check_element)
            
    def check_element(self):
        if self.done:
            return       
        # 簡單的 JS 查找元素
        js = """
        (function() {
            var el = document.querySelector('.I9S4yc');
            return el ? el.textContent : null;
        })();
        """
        self.browser.page().runJavaScript(js, self.on_element_found)
        
    def on_element_found(self, result):
        if self.done or not result:
            return
        # 找到元素，顯示結果並標記完成
        print(f"找到元素內容: {result}")
        self.done = True
        # 斷開信號連接，防止重複執行
        self.browser.loadFinished.disconnect(self.on_page_loaded)
        # 禁用 JavaScript
        settings = self.browser.settings()
        settings.setAttribute(settings.JavascriptEnabled, False)
        
    def keyPressEvent(self, event):
        # ALT+D 關閉視窗
        if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_D:
            self.close() # 關閉視窗
            QApplication.instance().quit() # 關閉視窗
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())
