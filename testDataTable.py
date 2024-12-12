import sys
import json, csv
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QMenuBar, QGroupBox, QLineEdit, QLabel, QHBoxLayout, QPushButton, QComboBox, QDialog, QTextEdit
)
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView


class DataTableManager:
    @staticmethod
    def style_table_headers(table):
        """Style the table headers with custom colors."""
        header = table.horizontalHeader()
        header.setStyleSheet(
            "QHeaderView::section {"
            "background-color: #4CAF50;" 
            "color: white;"               
            "font-weight: bold;"          
            "font-size: 12px;"           
            "}"
        )
        header.setFont(QFont("Arial", 10, QFont.Bold))
        table.setStyleSheet("QTableWidget { background-color: #F0F0F0; }")
        header.setSectionResizeMode(QHeaderView.Stretch)  
    @staticmethod
    def populate_table(table, parsed_results):
        if not isinstance(parsed_results, list) or not all(isinstance(result, dict) for result in parsed_results):
            raise ValueError("parsed_results should be a list of dictionaries.")

        table.setColumnCount(8)  
        table.setHorizontalHeaderLabels([
            "Protein ID", "Protein Length", "Annotation", "Manual Annotation ",
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
            go_count = len(eggnog_annotations[0].get("GOs", "").split(',')) if eggnog_annotations else 0
            classification_tag = "classified" if  go_count >10 else "unclassified"

            row_data = [
                prot_id, prot_length, eggnog_annotation, "",
                hits_count, interpro_domains, go_count, classification_tag
            ]

            for col_idx, value in enumerate(row_data):
                if col_idx == 3: 
                    text_input = QLineEdit()
                    text_input.setText(value)
                    text_input.setPlaceholderText("Add your annotation")
                    table.setCellWidget(row_idx, col_idx, text_input)
                
                elif col_idx == 7:  
                    badge_widget = QWidget()
                    badge_layout = QHBoxLayout()
                    badge_layout.setContentsMargins(7, 7, 7, 7)

                    #text with color
                    badge_label = QLabel("classified" if classification_tag == "classified" else "unclassified")
                    badge_label.setAlignment(Qt.AlignCenter)
                    if (classification_tag == "classified" ):
                        badge_label.setStyleSheet(
                            "background-color: green; color: white; font-size: 11px; font-weight: bold; border-radius: 10px;"
                        )
                    else:
                        badge_label.setStyleSheet(
                            "background-color: red; color: white; font-size: 11px; font-weight: bold; border-radius: 10px;"
                        )
                    badge_layout.addWidget(badge_label)
                    badge_widget.setLayout(badge_layout)
                    table.setCellWidget(row_idx, col_idx, badge_widget)



                else:
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)

        """ initial_column_widths = [150, 150, 150, 220, 150, 150, 150, 150]
        for col, width in enumerate(initial_column_widths):
            table.setColumnWidth(col, width)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) """

    



class DynamicTableWindow(QMainWindow):
    def __init__(self, parsed_results):
        super().__init__()
        self.setWindowTitle("SeaGo")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('C:/Users/saitsala/Desktop/image.png'))

        # Setup the table
        self.table = QTableWidget()
        DataTableManager.style_table_headers(self.table)
        DataTableManager.populate_table(self.table, parsed_results)

        # Create a menu bar
        self.create_menu_bar()

        # Create a filter bar
        self.create_filter_bar()
        

        # Row count label
        self.row_count_label = QLabel()
        self.update_row_count()  # Set initial row count

        # Group box to encapsulate the table
        table_group_box = QGroupBox("Annotation Table")
        table_group_box_layout = QVBoxLayout()
        table_group_box_layout.addLayout(self.filter_layout)
        table_group_box_layout.addWidget(self.table)
        table_group_box_layout.addWidget(self.row_count_label)  
        table_group_box.setLayout(table_group_box_layout)

        # Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(table_group_box)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connect signals
        self.table.itemChanged.connect(self.update_row_count)
        self.table.cellClicked.connect(self.show_annotation_dialog)

    def update_row_count(self):
        """Update the row count label to display the number of visible rows."""
        visible_rows = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        self.row_count_label.setText(f"Rows displayed: {visible_rows}")

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Add File menu
        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Add Help menu
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_filter_bar(self):
        self.prot_id_filter = QLineEdit()
        self.prot_id_filter.setPlaceholderText("Protein ID")
        self.prot_id_filter.setMaximumWidth(150)
        self.prot_id_filter.textChanged.connect(self.apply_filter)

        self.prot_length_filter = QLineEdit()
        self.prot_length_filter.setPlaceholderText("Protein Length")
        self.prot_length_filter.setMaximumWidth(150)
        self.prot_length_filter.textChanged.connect(self.apply_filter)

        self.export_button = QPushButton("Export to JSON")
        self.export_button.clicked.connect(self.export_to_json)
        
        
        self.export_button_csv = QPushButton("Export to CSV")
        self.export_button_csv.clicked.connect(self.export_to_csv)

        self.export_button_tsv = QPushButton("Export to TSV")
        self.export_button_tsv.clicked.connect(self.export_to_tsv)

        self.filter_layout = QHBoxLayout()
        self.filter_layout.addWidget(self.prot_id_filter)
        self.filter_layout.addWidget(self.prot_length_filter)
        self.filter_layout.addStretch(1)
        self.filter_layout.addWidget(self.export_button)
        self.filter_layout.addWidget(self.export_button_csv)
        self.filter_layout.addWidget(self.export_button_tsv)

    def apply_filter(self):
        """Filter rows based on the text input."""
        prot_id_text = self.prot_id_filter.text().lower()
        prot_length_text = self.prot_length_filter.text().lower()
        for row_idx in range(self.table.rowCount()):
            prot_id_item = self.table.item(row_idx, 0)
            prot_length_item = self.table.item(row_idx, 1)
            if (prot_id_item and prot_id_text in prot_id_item.text().lower()) and \
               (prot_length_item and prot_length_text in prot_length_item.text().lower()):
                self.table.setRowHidden(row_idx, False)
            else:
                self.table.setRowHidden(row_idx, True)
        self.update_row_count()  

    def export_to_json(self):
        """Export the table data to a JSON file."""
        table_data = []
        for row in range(self.table.rowCount()):
            row_data = {
                "PROTID": self.table.item(row, 0).text(),
                "Prot Length": self.table.item(row, 1).text(),
                "Annot": self.table.item(row, 2).text(),
                "Annot SEAGO": self.table.cellWidget(row, 3).text(),
                "Hits": self.table.item(row, 4).text(),
                "InterPro Domain": self.table.item(row, 5).text(),
                "GOs": self.table.item(row, 6).text(),
                "Classification": self.table.cellWidget(row, 7).windowIconText()
            }
            table_data.append(row_data)
        with open('table_data.json', 'w') as file:
            json.dump(table_data, file, indent=4)
        print("Table data has been exported to table_data.json")

    def export_to_csv(self):
        """Export the table data to a CSV file."""
        with open('table_data.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write headers
            writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())])

            # Write rows
            for row in range(self.table.rowCount()):
                row_data = [self.table.item(row, col).text() if self.table.item(row, col) else '' for col in range(self.table.columnCount())]
                writer.writerow(row_data)

    def export_to_tsv(self):
        """Export the table data to a TSV file."""
        with open('table_data.tsv', mode='w', newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            # Write headers
            writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())])

            # Write rows
            for row in range(self.table.rowCount()):
                row_data = [self.table.item(row, col).text() if self.table.item(row, col) else '' for col in range(self.table.columnCount())]
                writer.writerow(row_data)

    def show_about_dialog(self):
        print("BLAST Table Example Application for testing performance and UI.")

    def show_annotation_dialog(self, row, column):
        if column == 2:
            content = self.table.item(row, column).text()

            # Calculer la taille dynamique
            width = min(600, max(300, len(content) * 6))  # Largeur proportionnelle à la taille du texte
            height = min(400, max(100, len(content.splitlines()) * 20))  # Hauteur selon les lignes du texte

            dialog = QDialog(self)
            dialog.setWindowTitle("Annotation Details")
            dialog.resize(width, height)

            text_edit = QTextEdit(dialog)
            text_edit.setText(content)
            text_edit.setReadOnly(True)
            dialog.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
                border: 2px solid #cccccc;
            }
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                font-size: 14px;
                font-family: 'Arial';
                padding: 5px;
                border: none;
            }
        """)
            #close_button = QPushButton("Fermer", dialog)
            #close_button.clicked.connect(dialog.close)

            layout = QVBoxLayout()
            layout.addWidget(text_edit)
            #layout.addWidget(close_button)

            dialog.setLayout(layout)

            dialog.exec()        



def load_parsed_blast_hits(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
    if 'results' in data:
        return data['results']
    else:
        raise ValueError("Le fichier JSON ne contient pas la clé 'results'.")




if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set the Fusion style 
    app.setStyle("Fusion")

    # Load the parsed BLAST hits data (assuming you have the JSON file ready)
    parsed_results = load_parsed_blast_hits('C:/Users/saitsala/Documents/SeaGo/SeaGOcli/output.json')  # Path to your JSON file

    # Create the window and pass the parsed results
    window = DynamicTableWindow(parsed_results)
    window.show()

    sys.exit(app.exec())
