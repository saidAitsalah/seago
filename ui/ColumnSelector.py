from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton,
    QDialog, QCheckBox, QDialogButtonBox, QMainWindow, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt

class ColumnSelectorDialog(QDialog):
    def __init__(self, parent=None, column_headers=None):
        super().__init__(parent)
        self.setWindowTitle("Select Columns to Display")
        self.column_headers = column_headers
        self.checkboxes = []

        layout = QVBoxLayout()
        for header in column_headers:
            checkbox = QCheckBox(header)
            checkbox.setChecked(True)  # All columns are shown by default
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_selected_columns(self):
        """Return a list of booleans indicating which columns are selected."""
        return [checkbox.isChecked() for checkbox in self.checkboxes]    