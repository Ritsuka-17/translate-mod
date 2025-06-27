import mod200_translate
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QCursor, QPixmap
import sys


class Snipper(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # 設置視窗屬性
        self.setWindowTitle("ScreenShot Tool")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

        # 獲取當前螢幕
        self._screen = QApplication.screenAt(QCursor.pos())

        # 設置背景
        palette = self.palette()
        palette.setBrush(self.backgroundRole(), QBrush(self.getWindow()))
        self.setPalette(palette)

        # 設置鼠標為十字形
        QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))

        # 初始化變數
        self.start = QPoint()
        self.end = QPoint()
        self.preview_window = None

    def getWindow(self):
        return self._screen.grabWindow(0)

    def paintEvent(self, event):
        painter = QPainter(self)
        # 設置半透明黑色背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.drawRect(0, 0, self.width(), self.height())

        if self.start != self.end:
            # 繪製選取區域
            painter.setPen(QPen(QColor(60, 240, 240), 3))
            painter.setBrush(painter.background())
            painter.drawRect(QRect(self.start, self.end))

    def mousePressEvent(self, event):
        self.start = self.end = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return

        self.hide()
        QApplication.processEvents()

        # 計算截圖區域，增加一些邊距以避免切割
        x1 = min(self.start.x(), self.end.x())
        y1 = min(self.start.y(), self.end.y())
        width = abs(self.start.x() - self.end.x()) + 5  # 增加邊距
        height = abs(self.start.y() - self.end.y()) + 5  # 增加邊距

        # 進行截圖
        screenshot = self.getWindow().copy(x1, y1, width, height)
        
        # 儲存截圖
        screenshot.save("screenshot.png")  # 儲存截圖為 PNG 格式
        input_image = "screenshot.png"
        output_image = "screenshot00.png"
        result_info = mod200_translate.remove_text(input_image, output_image)

        # 從檔案載入翻譯後的圖片為 QPixmap
        translated_pixmap = QPixmap(output_image)
        
        # 顯示預覽視窗
        self.show_preview(translated_pixmap, x1, y1, width, height, result_info)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.quit()

    def show_preview(self, screenshot, x, y, width, height, result_info):
        # 取得翻譯後圖片的實際大小
        actual_width = screenshot.width()
        actual_height = screenshot.height()
        
        self.preview_window = PreviewWindow(screenshot, x, y, actual_width, actual_height, result_info)
        self.preview_window.show()

class PreviewWindow(QWidget):
    def __init__(self, screenshot, x, y, width, height, result_info):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        
        # 設置預覽視窗位置
        preview_y = max(0, y - height - 10)
        self.setGeometry(x, preview_y, width, height)
        
        # 設置視窗背景為透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 建立主要佈局容器
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 建立容器 widget
        self.container = QWidget()
        self.container.setObjectName("container")
        
        # 分析截圖背景色並設置相應的光暈效果
        is_dark_background = result_info['lightdeck'] < 145
        
        # 設置光暈效果
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        # 根據背景色設置光暈顏色
        if is_dark_background:
            self.shadow.setColor(QColor(255, 255, 255, 150))  # 亮色光暈
        else:
            self.shadow.setColor(QColor(0, 0, 0, 150))  # 暗色光暈
        self.shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(self.shadow)
        
        # 在容器中顯示截圖
        self.label = QLabel(self.container)
        self.label.setPixmap(screenshot)
        self.label.setGeometry(0, 0, width, height)
        
        # 設置容器大小
        self.container.setFixedSize(width, height)
        
        # 更新容器樣式
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: white;
                border-radius: 5px;
                border: 1px solid rgba(0, 0, 0, 0.2);
            }
        """)
        
        self.layout.addWidget(self.container)
        
        # 用於追蹤滑鼠拖曳
        self.dragging = False
        self.offset = QPoint()
        
        # 儲存背景色資訊
        self.is_dark_background = is_dark_background

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            # 點選時改變光暈效果
            if self.is_dark_background:
                self.shadow.setColor(QColor(60, 240, 240, 150))
            else:
                self.shadow.setColor(QColor(0, 120, 120, 150))
            self.shadow.setBlurRadius(25)
            self.container.setGraphicsEffect(self.shadow)

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = event.globalPos() - self.offset
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # 釋放時恢復原本的光暈
            if self.is_dark_background:
                self.shadow.setColor(QColor(255, 255, 255, 150))
            else:
                self.shadow.setColor(QColor(0, 0, 0, 100))
            self.shadow.setBlurRadius(20)
            self.container.setGraphicsEffect(self.shadow)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            QApplication.quit()

def main():
    app = QApplication(sys.argv)
    snipper = Snipper()
    snipper.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
