from PySide6.QtWidgets import QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QFont

class CustomHeader(QHeaderView):
    def __init__(self, orientation: Qt.Orientation, parent=None, target_column=None):
        super().__init__(orientation, parent)
        self.target_column = target_column

    def paintSection(self, painter, rect, logicalIndex):
        if logicalIndex == self.target_column:
            painter.save()
            painter.fillRect(rect, QColor("orange"))  # Background color
            painter.setPen(Qt.white)  # Text color
            font = QFont("Roboto", 12, QFont.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self.model().headerData(logicalIndex, self.orientation(), Qt.DisplayRole))
            painter.restore()
        else:
            super().paintSection(painter, rect, logicalIndex)
