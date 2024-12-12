from PySide6.QtWidgets import QTableWidgetItem, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

def populate_table_with_blast_data(table, parsed_results):
    total_hits = sum(len(result["blast_hits"]) for result in parsed_results)  
    table.setRowCount(total_hits)  

    row_idx = 0  
    for result in parsed_results:

        for hit in result["blast_hits"]:
            row_data = [
                row_idx + 1,  # No.
                result["sequence_id"],  # Query
                hit["alignment_length"],  # Length
                "OK",  
                100,  
                len(result["blast_hits"]),  
                hit["hit_id"],  
                hit["alignment_length"], 
                "Unclassified",  
                hit["bit_score"],  
                hit["e_value"], 
                "N/A"  
            ]

            for col_idx, value in enumerate(row_data):
                if col_idx == 4:  
                    progress = QProgressBar()
                    progress.setValue(value)
                    progress.setAlignment(Qt.AlignCenter)
                    if value > 90:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #00ff00;}")
                    else:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #ffcc00;}")
                    table.setCellWidget(row_idx, col_idx, progress)
                else:
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)

            row_idx += 1  

    for col in range(table.columnCount()):
        table.setColumnWidth(col, 100)

    table.horizontalHeader().setStretchLastSection(True)
    table.horizontal