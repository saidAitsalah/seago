import sys
from PySide6.QtWidgets import QApplication
from utils.data_loader import load_parsed_blast_hits
from ui.table_window import DynamicTableWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("QMainWindow { background-color: #EAEAEA; }")  
    parsed_results = load_parsed_blast_hits('C:/Users/saitsala/Documents/SeaGo/SeaGOcli/testData/output.json')  

    window = DynamicTableWindow(parsed_results)          
    window.show()

    sys.exit(app.exec())

