from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, QWidget, QHeaderView, QVBoxLayout
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt


class DataTableManager:
    @staticmethod
    def style_table_headers(table: QTableWidget):
        """Style the table headers."""
        header = table.horizontalHeader()
        header.setStyleSheet(
            "QHeaderView::section {"
            "background-color: #D7D7D7;" # 4CAF50 # carolina blue #86BBD8 ?? #2FBF71
            "color: #333333;" #or white ?
            "font : Roboto ; "
            "font-weight: bold;"
            "font-size: 12px;"
            "}"
        )
        #header.setFont(QFont("Arial", 10, QFont.Bold))
        table.setStyleSheet("QTableWidget { background-color: #F0F0F0; }")
        header.setSectionResizeMode(QHeaderView.Stretch)

    @staticmethod
    def populate_table(table: QTableWidget, parsed_results: list):
        """Populate the table with data."""
        if not isinstance(parsed_results, list) or not all(isinstance(result, dict) for result in parsed_results):
            raise ValueError("parsed_results should be a list of dictionaries.")

        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Protein ID", "Protein Length", "Annotation", "tags",
            "Hits", "InterPro Domain", "GOs", "Classification"
        ])
        table.setRowCount(len(parsed_results))

        for row_idx, result in enumerate(parsed_results):
            prot_id = result.get("sequence_id", "N/A")
            prot_length = result.get("blast_hits", [{}])[0].get("alignment_length", 0)
            eggnog_annotations = result.get("eggNOG_annotations", [])
            eggnog_annotation = eggnog_annotations[0].get("Description", "N/A") if eggnog_annotations else "N/A"
            hits_count = len(result.get("blast_hits", []))
            interpro_domains = len(result.get("InterproScan_annotation", []))
            Blasts = len(result.get("blast_hits", []))

            go_count = len(eggnog_annotations[0].get("GOs", "").split(',')) if eggnog_annotations else 0
            classification_tag = "classified" if go_count > 10 else "unclassified"
      
            tags = []
            if eggnog_annotations:  
                tags.append("E")
            if interpro_domains != 0:  
                tags.append("I")
            if Blasts != 0:  
                tags.append("B")

            tags_display = tags if tags else ["N/A"]

            row_data = [
                prot_id, prot_length, eggnog_annotation, tags_display,
                hits_count, interpro_domains, go_count, classification_tag
            ]

            for col_idx, value in enumerate(row_data):
                if col_idx == 3:  
                    #horizental layout for tags
                    tag_layout = QHBoxLayout()
                    tag_widget = QWidget()  

                    for tag in value:
                        label = QLabel(tag)
                        label.setAlignment(Qt.AlignCenter)

                     
                        label.setFixedHeight(18)  
                        label.setFixedWidth(35)  
                        
                        if tag == "I":
                            label.setStyleSheet("QLabel { background-color: #077187 ; color: white; font-weight : bold; border-radius: 5px; padding: 3px; }")
                        elif tag == "B":
                            label.setStyleSheet("QLabel { background-color: #4F518C ; color: white; font-weight : bold; border-radius: 5px; padding: 3px; }")    
                        else:
                            label.setStyleSheet("QLabel { background-color: #ED7D3A ; color: white; font-weight : bold; border-radius: 5px; padding: 3px; }")

                        tag_layout.addWidget(label)

                    tag_widget.setLayout(tag_layout)
                    table.setCellWidget(row_idx, col_idx, tag_widget)

                    #the row height based on the number of tags 
                    #row_height = max(15, len(value) * 15)  # Ensure row height is sufficient
                    table.setRowHeight(row_idx, 35)

                elif col_idx == 7:  # Classification
                    # Add icon for classification
                    icon_widget = QWidget()
                    icon_layout = QHBoxLayout()
                    icon_layout.setContentsMargins(0, 0, 0, 0)

                    icon_label = QLabel()
                    icon_label.setAlignment(Qt.AlignCenter)
                    if classification_tag == "classified":
                        icon_label.setPixmap(QPixmap("C:/Users/saitsala/Desktop/check.png").scaled(18, 18, Qt.KeepAspectRatio))
                    else:
                        icon_label.setPixmap(QPixmap("C:/Users/saitsala/Desktop/close.png").scaled(14, 14, Qt.KeepAspectRatio))

                    icon_layout.addWidget(icon_label)
                    icon_widget.setLayout(icon_layout)
                    table.setCellWidget(row_idx, col_idx, icon_widget)
                else:
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)
