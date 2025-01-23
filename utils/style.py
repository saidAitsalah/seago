from PySide6.QtGui import QFont

def style_table_headers(table):
    """Style the table headers with custom colors."""
    header = table.horizontalHeader()
    header.setStyleSheet(
        "QHeaderView::section {"
        "background-color: #4CAF50;"  # Green 
        "color: white;"               # White text
        "font-weight: bold;"          
        "font-size: 12px;"            
        "}"
    )
    header.setFont(QFont("Arial", 10, QFont.Bold))
