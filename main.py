from PySide6.QtWidgets import QApplication, QFileDialog
import sys
import timeit
from utils.data_loader import load_parsed_blast_hits
from ui.table_window import DynamicTableWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("QMainWindow { background-color: #EAEAEA; }")  

    file_dialog = QFileDialog()
    file_path, _ = file_dialog.getOpenFileName(None, "Select a Json File", "", "JSON Files (*.json)")

    if file_path:
        start_time = timeit.default_timer()
        parsed_results = load_parsed_blast_hits(file_path)  
        window = DynamicTableWindow(parsed_results)          
        window.show()
        end_time = timeit.default_timer()
        print(f"Temps de chargement : {end_time - start_time:.6f} secondes")
        sys.exit(app.exec())
    else:
        print("No file Selected.")