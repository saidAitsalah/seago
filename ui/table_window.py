from PySide6.QtWidgets import QMainWindow,QScrollArea, QTableWidget,QSplitter ,QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton, QWidget,QGraphicsDropShadowEffect, QMenuBar, QSpacerItem, QSizePolicy, QMessageBox, QDialog,QStatusBar, QTextEdit, QTabWidget, QComboBox   ,QTableWidgetItem,QProgressBar, QRadioButton
from PySide6.QtGui import QAction, QIcon, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer
from PySide6 import QtWidgets
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from utils.table_manager import DataTableManager
from utils.export_utils import export_to_json, export_to_csv, export_to_tsv
from ui.donut_widget import Widget
from PySide6.QtWebEngineWidgets import QWebEngineView
from pyvis.network import Network
from utils.OBO_handler import obo
import json
import os


class DynamicTableWindow(QMainWindow):

    def __init__(self, parsed_results):

        super().__init__()
        self.setWindowTitle("seaGo")
        self.setGeometry(100, 100, 1400, 850)
        self.setWindowIcon(QIcon('./assets/image.png'))
        self.parsed_results = parsed_results  

        self.load_config()

        """main Table"""
        self.table = QTableWidget()
        DataTableManager.style_table_headers(self.table,target_column=6)
        obo_file_path = self.config.get("obo_file_path", "./ontologies/go-basic.obo")
        go_definitions = obo.load_go_definitions(obo_file_path)
        DataTableManager.populate_table(self.table, parsed_results,go_definitions)
        self.table.itemSelectionChanged.connect(self.on_protein_selection_changed)

        """Components"""
        self.create_menu_bar()
        self.create_filter_bar()
        self.row_count_label = QLabel()
        self.update_row_count()

        # Group box to encapsulate the table
        table_group_box = QGroupBox("")
        table_group_box_layout = QVBoxLayout()
        table_group_box_layout.addLayout(self.filter_layout)
        table_group_box_layout.addWidget(self.table)
        table_group_box.setLayout(table_group_box_layout)
        table_group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        #Tabs creation
        self.tabs = QTabWidget()
        self.create_tabs(parsed_results)
        

        #QSplitter
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)  # verticale Orientation 
        splitter.addWidget(table_group_box)  
        splitter.addWidget(self.tabs)  
        # initial sizes
        splitter.setSizes([600, 250]) 

        # main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Filters
        self.dynamic_filters = []
        self.filter_fields = []
        self.filter_logic_dropdown = QComboBox()  
        self.filter_logic_dropdown.addItem('AND')
        self.filter_logic_dropdown.addItem('OR')

        # status Bar
        self.create_status_bar()

        # Connect signals
        self.table.itemChanged.connect(self.update_row_count)
        self.table.cellClicked.connect(self.update_description)
        self.table.cellClicked.connect(self.on_cell_selected)


    def generate_go_graph(self):
        """Generate Pyvis graph in QWebEngine widget dynamically from GO list."""
        file_path = "go_graph.html"  # Temp file
        
        # Liste of go terms to test
        go_terms = "GO:0000981,GO:0003674,GO:0003700,GO:0006355,GO:0006357,GO:0008150,GO:0009889,GO:0010468,GO:0010556,GO:0019219,GO:0019222,GO:0031323,GO:0031326,GO:0050789,GO:0050794,GO:0051171,GO:0051252,GO:0060255,GO:0065007,GO:0080090,GO:0140110,GO:1903506,GO:2000112,GO:2001141"
        go_list = go_terms.split(",")

        #graphe Pyvis
        net = Network(height="750px", width="100%", directed=True)

        # nodes
        for go in go_list:
            net.add_node(go, label=go)

        # simple edges
        for i in range(len(go_list) - 1):
            net.add_edge(go_list[i], go_list[i + 1])

        # HTML generation
        net.write_html(file_path)

        # read
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # display QWebEngineView
        web_view = QWebEngineView()
        web_view.setHtml(html_content)

        graph_tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(web_view)
        graph_tab.setLayout(layout)

        self.tabs.addTab(graph_tab, "GO Graph")

    def on_protein_selection_changed(self):
        """Updates the hits table based on the selected protein."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return  

        selected_row = selected_items[0].row()

        selected_protein = self.parsed_results[selected_row]  
        print(f"Selected protein: {selected_protein}") 

        blast_hits = selected_protein.get("blast_hits", [])
        
        self.update_hits_table(blast_hits)


    def update_hits_table(self, blast_hits):
        # Define column headers as in the 'populate_additional_table' function
        hits_table_column_headers = [
            "Hit id", "Definition", "Accession", "Identity", "Alignment length", "E-value", "Bit-score",
            "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
        ]
        
        self.additional_table.setHorizontalHeaderLabels(hits_table_column_headers)
        
        total_hits = len(blast_hits)
        self.additional_table.setRowCount(total_hits)

        # Populate the table row by row
        for row_idx, hit in enumerate(blast_hits):
            query_start = hit.get("query_positions", {}).get("start", "N/A")
            query_end = hit.get("query_positions", {}).get("end", "N/A")
            subject_start = hit.get("subject_positions", {}).get("start", "N/A")
            subject_end = hit.get("subject_positions", {}).get("end", "N/A")
            hit_accession = hit.get("accession", "N/A")
            hsp_bit_score = hit.get("hsps", [{}])[0].get("bit_score", "N/A")
            identity = (float(hit.get("percent_identity", 0)) / float(hit.get("alignment_length", 1))) * 100

            # row data
            row_data = [
                hit["hit_id"],  # hit_id
                hit["hit_def"],  # hit_def
                hit_accession,  # accession
                identity,  # identity
                hit["alignment_length"],  # alignment_length
                hit["e_value"],  # e_value
                hit["bit_score"],  # bit_score
                query_start,  # Query Start
                query_end,  # Query End
                subject_start,  # Subject Start
                subject_end,  # Subject End
                hsp_bit_score  # Hsp bit score
            ]

            for col_idx, value in enumerate(row_data):
                if col_idx == 3:  # Identity column with progress bar
                    progress = QProgressBar()
                    progress.setValue(int(value))
                    progress.setAlignment(Qt.AlignCenter)
                    if int(value) > 90:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #8FE388;}")
                    elif int(value) < 70:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #E3AE88;}")
                    else:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #88BCE3;}")
                    self.additional_table.setCellWidget(row_idx, col_idx, progress)
                else:
                    item = QTableWidgetItem(str(value))
                    self.additional_table.setItem(row_idx, col_idx, item)

        # column widths
        for col_idx, header in enumerate(hits_table_column_headers):
            if header == "Identity":
                self.additional_table.setColumnWidth(col_idx, 120)
            elif header == "hit_id":
                self.additional_table.setColumnWidth(col_idx, 100)
            else:
                self.additional_table.setColumnWidth(col_idx, 120)



    def create_tabs(self, parsed_results):
        """tabs for hits, graphs, metadata .."""
        self.tabs.addTab(self.create_tables_tab(parsed_results), "Hits")
        self.tabs.addTab(self.create_Iprscan_tab(parsed_results), "Domains")
        self.tabs.addTab(self.create_details_tab(), "Details")
        self.tabs.addTab(self.create_GO_tab(), "GO")
        self.tabs.addTab(self.create_graphs_tab(), "Donut")
        self.tabs.addTab(self.create_chart_tab(), "Chart")
        self.tabs.addTab(self.create_MetaD_tab(), "Metadata")
        self.generate_go_graph() # Temp
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                color: #333333;
                font : Lato;
                font-weight: bold;
                font-size: 12px ;
            }
        """)


    def create_details_tab(self):
            self.description_widget = QTextEdit()
            self.description_widget.setReadOnly(True)
            self.description_widget.setPlaceholderText("Select a cell to view annotation details...")
            tab_details = QWidget()
            tab_details_layout = QVBoxLayout()
            tab_details_layout.addWidget(self.description_widget)
            tab_details.setLayout(tab_details_layout)
            return tab_details
            



    def create_MetaD_tab(self):
            description_widget = QLabel("Metadata will be displayed here...")
            description_widget.setAlignment(Qt.AlignCenter)
            tab_graphs = QWidget()
            tab_graphs_layout = QVBoxLayout()
            tab_graphs_layout.addWidget(description_widget)
            tab_graphs.setLayout(tab_graphs_layout)
            self.tabs.addTab(tab_graphs, "Graphs")
            return tab_graphs
    

    def create_graphs_tab(self):
        donut_chart_widget = Widget() 
        donut_chart_widget.setMinimumSize(600, 600) 
        donut_chart_widget.setMaximumSize(900, 600) 

        #  scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(donut_chart_widget)  
        scroll_area.setWidgetResizable(True) 

        tab_graphs = QWidget()
        tab_graphs_layout = QVBoxLayout()

        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(scroll_area)  
     

        tab_graphs_layout.addLayout(scroll_layout)  
        tab_graphs.setLayout(tab_graphs_layout)

        tab_graphs.setMinimumSize(800, 300)  
   

        return tab_graphs

    #temp
    def create_chart_tab(self):
        """distribution graph to test"""
        chart = QChart() 
        series = QPieSeries()

        series.append("With Blast Hits", 60)
        series.append("With GO Mapping", 20)
        series.append("Manually Annotated", 10)
        series.append("Blasted Without hits", 10)

        chart.addSeries(series)
        chart.setTitle("Query distrubition")
        
        #title
        chart.setTitleBrush(QColor("#4F518C")) 
        chart.setTitleFont(QFont("Roboto", 14, QFont.Bold)) 

        series.slices()[0].setBrush(QColor("#077187")) 
        series.slices()[1].setBrush(QColor("#4F518C")) 
        series.slices()[2].setBrush(QColor("#ED7D3A"))  
        series.slices()[3].setBrush(QColor("#D0D0D0"))  

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        scroll_area = QScrollArea()
        scroll_area.setWidget(chart_view)
        scroll_area.setWidgetResizable(True)

        tab_graphs = QWidget()
        tab_graphs_layout = QVBoxLayout()


        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(scroll_area)

        tab_graphs_layout.addLayout(scroll_layout)

        tab_graphs_layout.setContentsMargins(10, 10, 10, 10)  
        tab_graphs_layout.setSpacing(10) 
        tab_graphs.setLayout(tab_graphs_layout)


        return tab_graphs


    def create_tables_tab(self, parsed_results):
            """hits table"""
            self.additional_table = QTableWidget()
            DataTableManager.style_AdditionalTable_headers(self.additional_table)
            self.additional_table.setColumnCount(12)
            DataTableManager.populate_additional_table(self.additional_table, parsed_results)

            tab_tables = QWidget()
            tab_tables_layout = QVBoxLayout()
            tab_tables_layout.addWidget(self.additional_table)
            tab_tables.setLayout(tab_tables_layout)


            tab_tables.setStyleSheet("""
                QTabBar::tab {
                    background: #077187;       /* Couleur de l'onglet par défaut */
                    color: black;                /* Couleur du texte */
                    padding: 5px;                /* Marges intérieures */
                }
                QTabBar::tab:hover {
                    background: lightgreen;      /* Couleur au survol */
                }
            """)
            return tab_tables

    def create_Iprscan_tab(self, parsed_results):
            """IPRscan Table tab'"""
            self.Iprsca_table = QTableWidget()
            DataTableManager.style_IprscanTable_headers(self.Iprsca_table)
            self.Iprsca_table.setColumnCount(12)
            DataTableManager.populate_interproscan_table(self.Iprsca_table, parsed_results)

            tab_Iprscan = QWidget()
            tab_Iprscan_layout = QVBoxLayout()
            tab_Iprscan_layout.addWidget(self.Iprsca_table)
            tab_Iprscan.setLayout(tab_Iprscan_layout)
            return tab_Iprscan
                
    def create_GO_tab(self):
            obo_file_path = "./ontologies/go-basic.obo"  #TO-DO obo file should be moved to config.Json !!

            go_data = obo.load_go_terms(obo_file_path)
            self.GO_table = QTableWidget()
            DataTableManager.style_IprscanTable_headers(self.GO_table)
            self.GO_table.setColumnCount(9)
            DataTableManager.populate_GO_table(self.GO_table, go_data)

            tab_go = QWidget()
            tab_go_layout = QVBoxLayout()
            tab_go_layout.addWidget(self.GO_table)
            tab_go.setLayout(tab_go_layout)
            return tab_go
                

    def update_description(self, row, column):
        """Update the description widget with details from the selected cell."""
        if column == 2: 
            annotation_text = self.table.item(row, column).text()
            self.description_widget.setText(annotation_text)
            self.tabs.setCurrentIndex(0)  # Switch to the Details tab
        else:
            self.description_widget.clear()  


   

    """****************************************** Bar components *********************************************"""

    def create_menu_bar(self):
        # menu bar creation
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)  

        # style CSS
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #D7D7D7; 
                color: #333333;
                font-family: Roboto;
                font-weight: bold;
                font-size: 12px;               
            }

            QMenuBar::item {
                background-color: transparent; 
                padding: 5px 10px; 
            }

            QMenuBar::item:selected {
                background-color: #7393B3; 
                border-radius: 4px; 
            }

            QMenu {
                background-color: #D7D7D7; 
                color: #333333; 
                border: 1px solid #444444; 
                margin: 2px;
            }

            QMenu::item {
                background-color: transparent;
                padding: 5px 20px; 
                font-size: 13px; 
            }

            QMenu::item:selected {
                background-color: #7393B3;
                color: #FFD700;
            }

            QMenu::separator {
                height: 2px; 
                background-color: #444444;
                margin: 4px 10px; 
            }
        """)

        # shaddow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10) 
        shadow.setXOffset(0)
        shadow.setYOffset(3)  
        shadow.setColor(QColor(0, 0, 0, 80)) 

        menu_bar.setGraphicsEffect(shadow)

        ### --- MENU ITEMS --- ###
        
        # Menu File
        file_menu = menu_bar.addMenu("File")
        open_action = QAction("Open", self)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(open_action)
        file_menu.addAction(exit_action)

        # Menu Export
        export_menu = menu_bar.addMenu("Export")
        export_json_action = QAction("Export to JSON", self)
        export_json_action.triggered.connect(lambda: export_to_json(self.table))
        export_menu.addAction(export_json_action)

        export_csv_action = QAction("Export to CSV", self)
        export_csv_action.triggered.connect(lambda: export_to_csv(self.table))
        export_menu.addAction(export_csv_action)

        export_tsv_action = QAction("Export to TSV", self)
        export_tsv_action.triggered.connect(lambda: export_to_tsv(self.table))
        export_menu.addAction(export_tsv_action)

        # Menu Help
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        #to-complete
        # other menu 
        tools_menu = menu_bar.addMenu("Tools")
        view_menu = menu_bar.addMenu("View")

        return menu_bar  


    def create_filter_bar(self):
        self.filter_layout = QHBoxLayout()

        self.open_dialog_button = QPushButton("Filter")
        self.open_dialog_button.setIcon(QIcon("./assets/dialog-icon.png"))
        self.open_dialog_button.clicked.connect(self.open_dialog)
        self.filter_layout.addWidget(self.open_dialog_button)

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
    

    def create_status_bar(self):
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)

            # Row count label
            #self.row_count_label = QLabel(self.row_count_label)
            self.status_bar.addPermanentWidget(self.row_count_label)

            # Clock
            self.clock_label = QLabel()
            self.status_bar.addPermanentWidget(self.clock_label)
            self.update_time()  # Initial time update
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_time)
            self.timer.start(1000)

            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setMaximumWidth(200)
            self.progress_bar.setVisible(False)
            self.status_bar.addPermanentWidget(self.progress_bar)

            # Status bar style
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #0B4F6C;
                    color: #FFFFFF;
                    font-weight: bold;
                    font-size: 12px;
                    border-top: 2px solid #86BBD8;
                }
                QLabel {
                    color: #93FF96;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)


    """************************************** Dialogs  *********************************************"""
    
    def show_about_dialog(self):
        """Todo : a informative about section !!"""
        print("BLAST Table Example Application for testing UI.")

    #to review
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


            layout = QVBoxLayout()
            layout.addWidget(text_edit)

            dialog.setLayout(layout)

            dialog.exec()     


    def open_dialog(self):
        dialog = QDialog()
        #to review
        dialog.deleteLater()  # Marks the widget for deletion
        dialog.setWindowTitle("Filter options")
        dialog.setWindowIcon(QIcon('./assets/image.png'))

        dialog.setFixedSize(400, 300)  

        dialog.setStyleSheet("""
            QDialog {
                background-color: #D7D7D7; 
                color: white;              
                border-radius: 10px;       
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #077187;
                border-radius: 5px;
                padding: 5px;
                color: #000;
            }
            QPushButton {
                background-color: #077187;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ED7D3A;
            }
            QPushButton:pressed {
                background-color: #4F518C;
            }
        """)

        dialog_layout = QVBoxLayout()

        dialog_input = QLineEdit()
        dialog_input.setPlaceholderText("Enter your filter value")
        dialog_layout.addWidget(dialog_input)

        add_filter_button = QPushButton("Add Filter")
        add_filter_button.setIcon(QIcon("./assets/filter.png"))
        add_filter_button.clicked.connect(self.add_filter_field)
        dialog_layout.addWidget(add_filter_button)

        clear_button = QPushButton("Clear All Filters")
        clear_button.setIcon(QIcon("./assets/clear-filter.png"))
        clear_button.clicked.connect(self.clear_filters)
        dialog_layout.addWidget(clear_button)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)  
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_filter_button)
        button_layout.addWidget(clear_button)
        button_layout.addWidget(ok_button)

        dialog_layout.addWidget(add_filter_button)
        dialog_layout.addWidget(clear_button)
        dialog_layout.addWidget(ok_button)

        dialog_layout.addLayout(button_layout)

       
        dialog.setLayout(dialog_layout)

        dialog.exec()


    """************************************** Gestion des filters  **********************************"""

    def add_filter_field(self):
        """dynamique filter based on table headers"""
        filter_row_layout = QHBoxLayout()  

        column_dropdown = QComboBox()
        column_headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        column_dropdown.addItems(column_headers)

        filter_input = QLineEdit()
        filter_input.setPlaceholderText("Enter filter value...")

        remove_button = QPushButton("Remove")
        remove_button.setIcon(QIcon("./assets/trash.png"))
        remove_button.clicked.connect(lambda: self.remove_filter_field(filter_row_layout))

        filter_row_layout.addWidget(QLabel("Column:"))
        filter_row_layout.addWidget(column_dropdown)
        filter_row_layout.addWidget(filter_input)
        filter_row_layout.addWidget(remove_button)

        self.filter_layout.addLayout(filter_row_layout)

        # stocking widget to apply filter after
        self.filter_fields.append((column_dropdown, filter_input))

        filter_input.textChanged.connect(self.apply_dynamic_filters)

    def remove_filter_field(self, filter_layout):
        """delete an input of dynamique filter."""
        # deleting all the widgets of the layout
        for i in reversed(range(filter_layout.count())):
            widget = filter_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)  # detaching from the layout=
                widget.deleteLater()   # Planning the supression

        # Remove the layout itself
        parent_widget = filter_layout.parentWidget()
        if parent_widget and isinstance(parent_widget.layout(), QtWidgets.QLayout):
            parent_layout = parent_widget.layout()
            parent_layout.removeItem(filter_layout)
        
        # Clean dynamic filter list
        self.filter_fields = [
            (column_dropdown, filter_input)
            for column_dropdown, filter_input in self.filter_fields
            if filter_input and filter_input.parent() is not None
        ]



    def apply_dynamic_filters(self):
        """Applies all dynamic filters to the table."""
        logic = self.filter_logic_dropdown.currentText()  # 'AND' or 'OR'

        # List to store valid filters
        valid_filter_fields = []

        # itering all rows in the table
        for row in range(self.table.rowCount()):
            row_matches = []
            
            for column_dropdown, filter_input in self.filter_fields[:]:  #Iterate over a copy of the list
                # Check if filter_input still exists and is valid
                if filter_input and filter_input.isVisible() and filter_input.parent() is not None:
                    filter_value = filter_input.text().strip().lower()
                    if not filter_value:
                        continue

                    column_index = column_dropdown.currentIndex()
                    item = self.table.item(row, column_index)
                    row_matches.append(item and filter_value in item.text().strip().lower())
                else:
                    # If filter_input is deleted, we remove it from filter_fields
                    if (column_dropdown, filter_input) in self.filter_fields:
                        self.filter_fields.remove((column_dropdown, filter_input))

            # Filter logique
            if logic == "AND":
                row_visible = all(row_matches) if row_matches else True
            else:
                row_visible = any(row_matches) if row_matches else True

            self.table.setRowHidden(row, not row_visible)

        # updating status bar
        visible_count = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        if visible_count == 0:
            self.statusBar().showMessage("No results found.")
        else:
            self.statusBar().showMessage(f"{visible_count} rows visible.")


    def clear_filters(self):
        """Clears all filters from the table."""
        for column_dropdown, filter_input in self.filter_fields[:]:
            if filter_input and filter_input.parent() is not None:
                filter_input.clear()
            else:
                self.filter_fields.remove((column_dropdown, filter_input))

        #display
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)

        # status bar
        self.statusBar().showMessage("Filters cleared.")


    #to review
    def reset_table_visibility(self):
        """Reset the visibility of all rows in the table."""
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)


    
    """************************************** Gestion de la status bar **********************************"""
    
    def on_cell_selected(self, row, column):
        """updating status bar whith selected element"""
        item = self.table.item(row, column)
        if item:  # verifying if the cell is not empty
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

    #to-review            
    def update_row_count(self):
        """Update the row count label to display the number of visible rows."""
        visible_rows = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        self.row_count_label.setText(f"Rows displayed: {visible_rows}")


    """***************************** utils  *********************************************"""   
    
    def load_config(self):
        """Charger la configuration depuis le fichier JSON"""
        config_file = "./config.json"
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                self.config = json.load(f)
        else:
            print(f"Le fichier de configuration {config_file} est introuvable.")
            self.config = {}

        
