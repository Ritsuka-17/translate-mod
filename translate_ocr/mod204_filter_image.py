from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QCursor
import sys

import mod204_window_filter

class Snipper(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # 設置視窗屬性
        self.setWindowTitle("ScreenShot Tool")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
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
        width = abs(self.start.x() - self.end.x()) + 10  # 增加邊距
        height = abs(self.start.y() - self.end.y()) + 10  # 增加邊距

        # 進行截圖
        screenshot = self.getWindow().copy(x1, y1, width, height)
        
        # 將截圖複製到剪貼簿
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(screenshot)
        
        # 啟動智慧濾鏡視窗
        self.filter_window = mod204_window_filter.BrowserWindow()
        self.filter_window.show()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.quit()

    def show_preview(self, screenshot, x, y, width, height):
        self.preview_window = PreviewWindow(screenshot, x, y, width, height)
        self.preview_window.show()

class PreviewWindow(QWidget):
    def __init__(self, screenshot, x, y, width, height):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 設置預覽視窗位置（在選取區域上方）
        preview_y = max(0, y - height - 10)
        self.setGeometry(x, preview_y, width, height)
        
        # 設置視窗背景為透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 建立主要佈局容器
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 建立一個容器 widget 來顯示圖片和陰影
        self.container = QWidget()
        self.container.setObjectName("container")
        
        # 設置陰影效果 - 將 shadow 設為類的屬性
        self.shadow = QGraphicsDropShadowEffect(self)  # 使用 self.shadow
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(255, 255, 255, 150))  # 預設白色陰影
        self.shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(self.shadow)
        
        # 在容器中顯示截圖
        label = QLabel(self.container)
        label.setPixmap(screenshot)
        
        # 設置樣式
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: white;
                border-radius: 5px;
                border: 2px solid rgba(0, 0, 0, 0.5);
            }
        """)
        
        self.layout.addWidget(self.container)

        # 用於追蹤滑鼠拖曳
        self.dragging = False
        self.offset = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            # 點選時改變陰影顏色為藍色
            self.shadow.setColor(QColor(60, 240, 240, 255))

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = event.globalPos() - self.offset
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # 釋放時恢復原本的白色陰影
            self.shadow.setColor(QColor(255, 255, 255, 150))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            QApplication.instance().quit()

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    snipper = Snipper(window)
    snipper.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
