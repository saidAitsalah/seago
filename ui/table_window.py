from PySide6.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton, QWidget, QMenuBar, QDialog,QStatusBar, QTextEdit, QTabWidget, QComboBox   ,QTableWidgetItem,QProgressBar, QRadioButton
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
        table_group_box = QGroupBox("")
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
        self.additional_table.setColumnCount(12) 

        #col..

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
        main_layout.addWidget(self.filter_group)  

        main_layout.addWidget(table_group_box)
        main_layout.addWidget(self.tabs)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.dynamic_filters = [] 

        #status bar
         # Ajout de la barre de statut
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Row count label
        self.row_count_label = QLabel("Rows displayed: 0")
        self.status_bar.addPermanentWidget(self.row_count_label)

        # Clock (dynamic system time)
        self.clock_label = QLabel()
        self.status_bar.addPermanentWidget(self.clock_label)
        self.update_time()  # Initial time update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second

        # Progress bar for long tasks
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)  # Initially hidden
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Status messages
        """  self.status_message = QLabel(" Welcome to SeaGO ")
        self.status_bar.addWidget(self.status_message) """


        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #0B4F6C;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                border-top: 2px solid #86BBD8 ;
            }
            QLabel {
                color: #93FF96;
                font-weight: bold;
                font-size: 12px;
            }
        """)
       
         # Ajout du bouton radio "SuperSayan"
        self.super_sayan_button = QRadioButton("Best Hit ?")
        self.super_sayan_button.setChecked(False)
        self.super_sayan_button.toggled.connect(self.toggle_super_sayan_style)
        main_layout.addWidget(self.super_sayan_button)

        # Connect signals
        self.table.itemChanged.connect(self.update_row_count)
        self.table.itemChanged.connect(self.update_row_count)
        self.table.cellClicked.connect(self.update_description)
        self.table.cellClicked.connect(self.on_cell_selected)


        

    def update_description(self, row, column):
        """Update the description widget with details from the selected cell."""
        if column == 2: 
            annotation_text = self.table.item(row, column).text()
            self.description_widget.setText(annotation_text)
            self.tabs.setCurrentIndex(0)  # Switch to the Details tab
        else:
            self.description_widget.clear()

    def populate_additional_table(self, parsed_results):

        addTable_column_headers = [
            "Hit id","definition","accession", "identity", "Alignment length", "E_value", "Bit_score",
            "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
        ] 
        self.additional_table.setHorizontalHeaderLabels(addTable_column_headers)

        total_hits = sum(len(result["blast_hits"]) for result in parsed_results) 
        self.additional_table.setRowCount(total_hits)  

        row_idx = 0  
        for result in parsed_results:
            for hit in result["blast_hits"]:
                query_start = hit["query_positions"]["start"]
                query_end = hit["query_positions"]["end"]
                subject_start = hit["subject_positions"]["start"]
                subject_end = hit["subject_positions"]["end"]
                hit_accession = result.get("hit_accession", "N/A")
                chunked_value = hit_accession.split("[[taxon")[0].strip()
                hsp = hit.get("hsps", [])
                hsp_bitScore = hsp[0].get("bit_score", "N/A")
                

                row_data = [
                    hit["hit_id"],  # hit_id
                    hit["hit_def"],  # hit_def
                    chunked_value,  # accession
                    hit["percent_identity"],  # percent_identity
                    hit["alignment_length"],  # alignment_length
                    hit["e_value"],  # e_value
                    hit["bit_score"],  # bit_score
                    query_start,  # Query Start
                    query_end,    # Query End
                    subject_start,  # Subject Start
                    subject_end,    # Subject End
                    hsp_bitScore
                ]

                for col_idx, value in enumerate(row_data):
                    if col_idx == 3:  
                        progress = QProgressBar()

                        progress.setValue(int(value))
                        progress.setAlignment(Qt.AlignCenter)
                        if int(value) > 90:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #8FE388;}")
                        elif int(value) < 70:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #FAA613;}")
                        else:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #5BC0EB ;}")
                        self.additional_table.setCellWidget(row_idx, col_idx, progress)
                    else:
                        item = QTableWidgetItem(str(value))
                        self.additional_table.setItem(row_idx, col_idx, item)

                row_idx += 1

        for col_idx, header in enumerate(addTable_column_headers):
            if header == "percent_identity":
                self.additional_table.setColumnWidth(col_idx, 100)
            elif header == "hit_id":
                self.additional_table.setColumnWidth(col_idx, 100)
            else:
                self.additional_table.setColumnWidth(col_idx, 100)        

                
    def update_row_count(self):
        """Update the row count label to display the number of visible rows."""
        visible_rows = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        self.row_count_label.setText(f"Rows displayed: {visible_rows}")

    def update_description(self, row, column):
        """Update the description widget with details from the selected cell."""
        if column == 2: 
            annotation_text = self.table.item(row, column).text()
            self.description_widget.setText(annotation_text)
        else:
            self.description_widget.clear()



    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Menu File
        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        open_action = QAction("Open", self)
        #exit_action.triggered.connect(self.close)
        file_menu.addAction(open_action)

        # Menu Export
        export_menu = menu_bar.addMenu("Export")
        export_json_action = QAction("Export to JSON", self)
        export_json_action.triggered.connect(self.export_to_json)
        export_menu.addAction(export_json_action)

        export_csv_action = QAction("Export to CSV", self)
        export_csv_action.triggered.connect(self.export_to_csv)
        export_menu.addAction(export_csv_action)

        export_tsv_action = QAction("Export to TSV", self)
        export_tsv_action.triggered.connect(self.export_to_tsv)
        export_menu.addAction(export_tsv_action)

        # Menu Help
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_filter_bar(self):
        self.filter_layout = QHBoxLayout()
        self.filter_fields = []  # Liste pour stocker les widgets de filtres ajoutés

        # Bouton pour ajouter un filtre
        self.add_filter_button = QPushButton("Add Filter")
        self.add_filter_button.setIcon(QIcon("C:/Users/saitsala/Desktop/filter.png"))
        self.add_filter_button.clicked.connect(self.add_filter_field)



        self.clear_button = QPushButton("Clear All Filters") 
        self.clear_button.setIcon(QIcon("C:/Users/saitsala/Desktop/clear-filter.png"))
        self.clear_button.clicked.connect(self.clear_filters)
        self.filter_layout.addWidget(self.clear_button)


        # Placez le bouton dans un QHBoxLayout pour une meilleure structure
        add_filter_layout = QHBoxLayout()
        add_filter_layout.addWidget(self.add_filter_button)
        self.filter_layout.addLayout(add_filter_layout)

        # Placez les filtres dans un QGroupBox
        self.filter_group = QGroupBox("Filters")
        self.filter_group.setCheckable(True)
        self.filter_group.setChecked(True)  # Initially visible

        self.filter_logic_dropdown = QComboBox()
        self.filter_logic_dropdown.addItems(["AND", "OR"])
        self.filter_logic_dropdown.currentIndexChanged.connect(self.apply_dynamic_filters)

        from PySide6.QtWidgets import QSpacerItem, QSizePolicy

        # Add a spacer before the label
        spacer = QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.filter_layout.addItem(spacer)

        self.filter_layout.addWidget(QLabel("Filter Logic:"))
        self.filter_layout.addWidget(self.filter_logic_dropdown)

         # Style
        self.setStyleSheet("""
        QLineEdit {
            border: 1px solid #D3D3D3;
            border-radius: 3px;
            padding: 3px;
        }
        QPushButton {
            background-color: #C0C0C0;
            color: black;
            border-radius: 3px;
            font-weight: bold ;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #7393B3;
        }
        QLabel {
            font-weight: bold;
        }
        """)


        self.filter_group.setLayout(self.filter_layout)
        

    def apply_filter(self):
        """Applique les filtres dynamiquement pour toutes les colonnes."""
        for row_idx in range(self.table.rowCount()):
            row_visible = True  # On suppose que la ligne est visible par défaut

            # Vérifie chaque filtre dynamique
            for col_idx, filter_input in enumerate(self.dynamic_filters):
                if filter_input:  # Assurez-vous que l'entrée existe
                    filter_value = filter_input.text().strip().lower()
                    cell_item = self.table.item(row_idx, col_idx)

                    # Si la valeur du filtre ne correspond pas, cache la ligne
                    if filter_value and cell_item:
                        cell_text = cell_item.text().strip().lower()
                        if filter_value not in cell_text:
                            row_visible = False
                            break  # Pas besoin de vérifier les autres filtres pour cette ligne

            # Affiche ou cache la ligne
            self.table.setRowHidden(row_idx, not row_visible)

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



    """************************************** Gestion des filters  **********************************"""

    
    def add_filter_field(self):
        """Ajoute un champ de filtre dynamique basé sur les en-têtes de la table."""
        filter_row_layout = QHBoxLayout()  # Un layout horizontal pour chaque ligne de filtre

        # Dropdown pour sélectionner la colonne (en-têtes de table)
        column_dropdown = QComboBox()
        column_headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        column_dropdown.addItems(column_headers)

        # Champ de texte pour la valeur du filtre
        filter_input = QLineEdit()
        filter_input.setPlaceholderText("Enter filter value...")

        # Bouton pour supprimer le filtre
        remove_button = QPushButton("Remove")
        remove_button.setIcon(QIcon("C:/Users/saitsala/Desktop/trash.png"))
        remove_button.clicked.connect(lambda: self.remove_filter_field(filter_row_layout))

        # Ajoutez les widgets au layout de la ligne
        filter_row_layout.addWidget(QLabel("Column:"))
        filter_row_layout.addWidget(column_dropdown)
        filter_row_layout.addWidget(filter_input)
        filter_row_layout.addWidget(remove_button)

        # Ajoutez le layout de la ligne au layout principal des filtres
        self.filter_layout.addLayout(filter_row_layout)

        # Stockez les widgets pour appliquer les filtres plus tard
        self.filter_fields.append((column_dropdown, filter_input))

        # Connecter le changement de texte à la fonction de filtrage
        filter_input.textChanged.connect(self.apply_dynamic_filters)

    def remove_filter_field(self, filter_layout):
        """Supprime un champ de filtre dynamique."""
        for i in reversed(range(filter_layout.count())):
            widget = filter_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.filter_layout.removeItem(filter_layout)
        filter_layout.setParent(None)

        # Nettoyer la liste des filtres dynamiques
        if filter_layout in self.dynamic_filters:
            self.dynamic_filters.remove(filter_layout)
        
        # Remove from filter_fields
        for col_dropdown, filter_input in self.filter_fields:
            if filter_layout in (col_dropdown, filter_input):
                self.filter_fields.remove((col_dropdown, filter_input))
                break



    def apply_dynamic_filters(self):
        """Applies all dynamic filters to the table."""
        logic = self.filter_logic_dropdown.currentText()  # 'AND' or 'OR'
        
        for row in range(self.table.rowCount()):
            row_matches = []
            for column_dropdown, filter_input in self.filter_fields:
                # Check if filter_input is still valid
                if filter_input and filter_input.parent() is not None:
                    filter_value = filter_input.text().strip().lower()
                    if not filter_value:
                        continue

                    column_index = column_dropdown.currentIndex()
                    item = self.table.item(row, column_index)
                    row_matches.append(item and filter_value in item.text().strip().lower())

            if logic == "AND":
                row_visible = all(row_matches) if row_matches else True
            else:
                row_visible = any(row_matches) if row_matches else True
                    
            self.table.setRowHidden(row, not row_visible)

        visible_count = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        if visible_count == 0:
            self.statusBar().showMessage("No results found.")
        else:
            self.statusBar().showMessage(f"{visible_count} rows visible.")




    def clear_filters(self):
        for column_dropdown, filter_input in self.filter_fields:
            if filter_input and filter_input.parent() is not None:
                filter_input.clear()
        self.reset_table_visibility()  # Call a method to reset visibility
        self.apply_dynamic_filters()

    def reset_table_visibility(self):
        """Reset the visibility of all rows in the table."""
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)




    
    """************************************** Gestion de la status bar **********************************"""
    
    def on_cell_selected(self, row, column):
        """Met à jour la status bar avec l'élément sélectionné."""
        item = self.table.item(row, column)
        if item:  # Vérifie que la cellule n'est pas vide
            selected_text = item.text()
            self.status_bar.showMessage(f"Élément sélectionné : {selected_text}")
        else:
            self.status_bar.showMessage("Aucun élément sélectionné.")

    def update_time(self):
        """Update the clock in the status bar."""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.setText(f"Time: {current_time}")

    def start_progress_bar(self, maximum):
        """Display and initialize the progress bar."""
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setVisible(True)

    def update_progress_bar(self, value):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
        if value == self.progress_bar.maximum():
            self.progress_bar.setVisible(False)
            self.status_message.setText("Task completed successfully!")

    def update_row_count(self):
        """Update the row count in the status bar."""
        visible_rows = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        self.row_count_label.setText(f"Rows displayed: {visible_rows}")


        



        
