from PySide6.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton, QWidget, QMenuBar, QDialog, QTextEdit, QTabWidget, QTableWidgetItem,QProgressBar, QRadioButton
from PySide6.QtGui import QAction, QIcon, QPainter, QBrush, QColor, QFont,QPixmap
import csv, json
from PySide6.QtCore import Qt, QTimer
from utils.table_manager import DataTableManager
from utils.export_utils import export_to_json, export_to_csv


class DynamicTableWindow(QMainWindow):
    def __init__(self, parsed_results):
        super().__init__()
        self.setWindowTitle("SeaGo")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('C:/Users/saitsala/Desktop/image.png'))

        self.table = QTableWidget()
        DataTableManager.style_table_headers(self.table)
        DataTableManager.populate_table(self.table, parsed_results)

        self.create_menu_bar()
        self.create_filter_bar()

        self.row_count_label = QLabel()
        self.update_row_count()

        # Group box pour encapsuler la table
        table_group_box = QGroupBox("Annotation Table")
        table_group_box_layout = QVBoxLayout()
        table_group_box_layout.addLayout(self.filter_layout)
        table_group_box_layout.addWidget(self.table)
        table_group_box_layout.addWidget(self.row_count_label)
        table_group_box.setLayout(table_group_box_layout)

        # Création du QTabWidget pour les détails d'annotation
        self.tabs = QTabWidget()

        # Onglet Détails
        self.description_widget = QTextEdit()
        self.description_widget.setReadOnly(True)
        self.description_widget.setPlaceholderText("Select a cell to view annotation details...")
        tab_details = QWidget()
        tab_details_layout = QVBoxLayout()
        tab_details_layout.addWidget(self.description_widget)
        tab_details.setLayout(tab_details_layout)
        self.tabs.addTab(tab_details, "Details")

        # Onglet Graphes
        self.graph_widget = QLabel("Graphs will be displayed here...")
        self.graph_widget.setAlignment(Qt.AlignCenter)
        tab_graphs = QWidget()
        tab_graphs_layout = QVBoxLayout()
        tab_graphs_layout.addWidget(self.graph_widget)
        tab_graphs.setLayout(tab_graphs_layout)
        self.tabs.addTab(tab_graphs, "Graphs")

        # Onglet Tables
        self.additional_table = QTableWidget()
        DataTableManager.style_table_headers(self.additional_table)
        self.additional_table.setColumnCount(9)  
        self.additional_table.setHorizontalHeaderLabels([
            "Hit id", "% Percent identity", "Alignment length", "E_value", "Bit_score",
            "Start (Query)", "End (Query)", "Start (Subject)", "End (Subject)"
        ])

        """  example_data = [
            ["Hit1", "Domain1", "GO1"],
            ["Hit2", "Domain2", "GO2"],
            ["Hit3", "Domain3", "GO3"],
        ] """
        self.populate_additional_table(parsed_results)


        tab_tables = QWidget()
        tab_tables_layout = QVBoxLayout()
        tab_tables_layout.addWidget(self.additional_table)
        tab_tables.setLayout(tab_tables_layout)
        self.tabs.addTab(tab_tables, "Tables")

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.addWidget(table_group_box)
        main_layout.addWidget(self.tabs)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

         # Ajout du bouton radio "SuperSayan"
        self.super_sayan_button = QRadioButton("Best Hit ?")
        self.super_sayan_button.setChecked(False)
        self.super_sayan_button.toggled.connect(self.toggle_super_sayan_style)
        main_layout.addWidget(self.super_sayan_button)

        # Connect signals
        self.table.itemChanged.connect(self.update_row_count)
        self.table.cellClicked.connect(self.update_description)

    def update_description(self, row, column):
        """Update the description widget with details from the selected cell."""
        if column == 2:  # Assurez-vous que cette colonne contient les descriptions
            annotation_text = self.table.item(row, column).text()
            self.description_widget.setText(annotation_text)
            self.tabs.setCurrentIndex(0)  # Switch to the Details tab
        else:
            self.description_widget.clear()

    """  def populate_additional_table(self, data):
        self.additional_table.setRowCount(len(data))
        self.additional_table.setColumnCount(len(data[0]))
        self.additional_table.setHorizontalHeaderLabels(["Hit", "Domain", "GO"]) 

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                self.additional_table.setItem(row_idx, col_idx, QTableWidgetItem(value))    """ 

    def populate_additional_table(self, parsed_results):
        total_hits = sum(len(result["blast_hits"]) for result in parsed_results) 
        self.additional_table.setRowCount(total_hits)  

        row_idx = 0  # Initialisez l'index de ligne pour ajouter les hits
        for result in parsed_results:
            # Itérez à travers chaque hit de chaque résultat
            for hit in result["blast_hits"]:
                query_start = hit["query_positions"]["start"]
                query_end = hit["query_positions"]["end"]
                subject_start = hit["subject_positions"]["start"]
                subject_end = hit["subject_positions"]["end"]

                row_data = [
                    hit["hit_id"],  # hit_id
                    hit["percent_identity"],  # percent_identity
                    hit["alignment_length"],  # alignment_length
                    hit["e_value"],  # e_value
                    hit["bit_score"],  # bit_score
                    query_start,  # Query Start
                    query_end,    # Query End
                    subject_start,  # Subject Start
                    subject_end    # Subject End
                ]

                for col_idx, value in enumerate(row_data):
                    if col_idx == 1:  
                        progress = QProgressBar()
                        progress.setValue(value)
                        progress.setAlignment(Qt.AlignCenter)
                        if value > 90:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #8FE388;}")
                        elif value < 70:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #FAA613;}")
                        else:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #5BC0EB ;}")
                        self.additional_table.setCellWidget(row_idx, col_idx, progress)
                    else:
                        item = QTableWidgetItem(str(value))
                        self.additional_table.setItem(row_idx, col_idx, item)

                """  if row_idx == 0:
                    self.additional_table.setStyleSheet(
                            QTableWidget::item {
                                border: 2px solid qlineargradient(
                                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #FF4500, stop:1 #FFD700
                                );
                                background-color: rgba(255, 245, 238, 0.8);
                            }
                    ) """

                row_idx += 1
                

                
    def update_row_count(self):
        """Update the row count label to display the number of visible rows."""
        visible_rows = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        self.row_count_label.setText(f"Rows displayed: {visible_rows}")

    def update_description(self, row, column):
        """Update the description widget with details from the selected cell."""
        if column == 2:  # Assurez-vous que cette colonne contient les descriptions
            annotation_text = self.table.item(row, column).text()
            self.description_widget.setText(annotation_text)
        else:
            self.description_widget.clear()



    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

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

        self.export_button.setStyleSheet(
            "background-color: #D7D7D7 ;" # A9E5BB Best one so far
            "color: #333333;" #or white ?
            "font : Roboto ; "
            "font-weight: bold;"
            "font-size: 12px;"
            "}"
        )
        
        
        self.export_button_csv = QPushButton("Export to CSV")
        self.export_button_csv.clicked.connect(self.export_to_csv)

        self.export_button_csv.setStyleSheet(
            "background-color: #D7D7D7;" # 4CAF50 /BLUE CAROLINA: 86BBD8 / NZYANZA :DAF7DC
            "color: #333333;" #or white ?
            "font : Roboto ; "
            "font-weight: bold;"
            "font-size: 12px;"
            "}"
        )

        self.export_button_tsv = QPushButton("Export to TSV")
        self.export_button_tsv.clicked.connect(self.export_to_tsv)

        self.export_button_tsv.setStyleSheet(
            "background-color:  #D7D7D7 ;" # 4CAF50 /BLUE CAROLINA: 86BBD8 / NZYANZA :DAF7DC
            "color: #333333;" #or white ?
            "font : Roboto ; "
            "font-weight: bold;"
            "font-size: 12px;"
            "}"
        )

        self.filter_layout = QHBoxLayout()
        self.filter_layout.addWidget(self.prot_id_filter)
        self.filter_layout.addWidget(self.prot_length_filter)
        self.filter_layout.addStretch(1)
        self.filter_layout.addWidget(self.export_button)
        self.filter_layout.addWidget(self.export_button_csv)
        self.filter_layout.addWidget(self.export_button_tsv)

    def apply_filter(self):
        """Filter based on the text input."""
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
        #Export the table data to a JSON file.
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
        with open('table_data.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            # headers
            writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())])

            #  rows
            for row in range(self.table.rowCount()):
                row_data = [self.table.item(row, col).text() if self.table.item(row, col) else '' for col in range(self.table.columnCount())]
                writer.writerow(row_data)

    def export_to_tsv(self):
        with open('table_data.tsv', mode='w', newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            # headers
            writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())])

            # rows
            for row in range(self.table.rowCount()):
                row_data = [self.table.item(row, col).text() if self.table.item(row, col) else '' for col in range(self.table.columnCount())]
                writer.writerow(row_data)

    def show_about_dialog(self):
        print("BLAST Table Example Application for testing performance and UI.")

    def show_annotation_dialog(self, row, column):
        if column == 2:
            content = self.table.item(row, column).text()

            width = min(300, max(150, len(content) * 6)) 
            height = min(200, max(50, len(content.splitlines()) * 20))

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

    def toggle_super_sayan_style(self, checked):
                        if checked:  # Si le bouton est activé
                            self.additional_table.setStyleSheet("""
                                QTableWidget::item {
                                    border: 2px solid qlineargradient(
                                        spread:pad, x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #FF4500, stop:1 #FFD700
                                    );
                                    background-color: rgba(255, 245, 238, 0.8);
                                }
                            """)
                        else:  # Si le bouton est désactivé
                            self.additional_table.setStyleSheet("")  #              

    