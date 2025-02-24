from PySide6.QtWidgets import QMainWindow, QHeaderView, QTableView, QScrollArea, QTableWidget, QSplitter, QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton, QWidget, QGraphicsDropShadowEffect, QMenuBar, QSpacerItem, QSizePolicy, QMessageBox, QDialog, QStatusBar, QTextEdit, QTabWidget, QComboBox, QTableWidgetItem, QProgressBar, QRadioButton
from PySide6.QtGui import QAction, QIcon, QPainter, QColor, QFont, QPixmap
from PySide6.QtCore import Qt, QTimer, QAbstractTableModel, Signal, QModelIndex, QThread
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
import logging
from model.data_model import VirtualTableModel

class DataLoaderThread(QThread):
    data_loaded = Signal(list)

    def __init__(self, parsed_results, go_definitions):
        super().__init__()
        self.parsed_results = parsed_results
        self.go_definitions = go_definitions

    def run(self):
        processed_data = DataTableManager.process_batch(self.parsed_results, self.go_definitions)
        self.data_loaded.emit(processed_data)

class DynamicTableWindow(QMainWindow):
    data_loaded = Signal()

    def __init__(self, parsed_results, file_path, config=None):
        super().__init__()
        self.file_path = file_path
        self.parsed_results = parsed_results
        self.config = config if config is not None else {}
        self.go_definitions = {}
        self.detail_tabs = {}

        self.load_config()
        self.init_ui()

        self.file_loader_thread = DataLoaderThread(self.parsed_results, self.go_definitions)
        self.file_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.file_loader_thread.start()

    def load_config(self):
        """Load configuration and GO definitions"""
        obo_file_path = self.config.get("obo_file_path", "./ontologies/go-basic.obo")
        self.go_definitions = obo.load_go_definitions(obo_file_path)

    def init_ui(self):
        """Initialize main UI components"""
        self.setWindowTitle(f"Results - {self.file_path}")
        self.create_main_table()
        self.create_menu_bar()
        self.create_filter_bar()
        self.create_tab_system()
        self.create_status_bar()
        self.connect_signals()

    def create_main_table(self):
        """Create and configure main table with virtual model"""
        self.table = QTableView()
        self.table_group_box = QGroupBox("")
        header = self.table.horizontalHeader()

        # Set up virtual model
        self.model = VirtualTableModel(self.parsed_results, header, self.go_definitions)
        self.table.setModel(self.model)

        # Configure table
        self.table.setObjectName("MainResultsTable")
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Optimize scrolling
        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)

        # Set column widths
        for col, width in DataTableManager.COLUMN_CONFIG["main"].items():
            try:
                col_idx = VirtualTableModel.HEADERS.index(col)
                self.table.setColumnWidth(col_idx, width)
            except ValueError:
                print(f"Column {col} not found in headers")
                logging.error(f"Column {col} not found in headers")

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.table_group_box.setLayout(layout)

        # Populate the table
        DataTableManager.populate_table(self.table, self.parsed_results, self.go_definitions)

    def create_filter_bar(self):
        self.filter_bar = QWidget()
        layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter results...")
        self.filter_type = QComboBox()
        self.filter_type.addItems(["Protein ID", "Description", "GO Terms"])
        layout.addWidget(QLabel("Filter by:"))
        layout.addWidget(self.filter_type)
        layout.addWidget(self.filter_input)
        layout.addWidget(QPushButton("Apply", clicked=self.apply_filters))
        self.filter_bar.setLayout(layout)
        self.table_group_box.layout().insertWidget(0, self.filter_bar)


    def connect_signals(self):
        if self.table.model():
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.data_loaded.connect(self.on_data_loaded)

    def on_selection_changed(self):
        indexes = self.table.selectionModel().selectedIndexes()
        if indexes:
            row = indexes[0].row()
            self.handle_row_selection(row)

    def handle_row_selection(self, row):
        page = row // VirtualTableModel.PAGE_SIZE
        if page in self.model._loaded_data:
            item_data = self.model._loaded_data[page][row % VirtualTableModel.PAGE_SIZE]
            self.update_detail_tabs(item_data)

    def update_detail_tabs(self, item_data):
        pass
        """         if 'blast_hits' in item_data['display']:
                    self.update_blast_tab(item_data['display']['blast_hits'])
                if 'InterPro' in item_data['display']:
                    self.create_interpro_tab(item_data['display']['InterPro'])
                if 'GO' in item_data['display']:
                    self.update_go_tab(item_data['display']['GO']) """

    def on_data_loaded(self, processed_data):
        #self.model.update_data(processed_data)
        self.progress_bar.hide()
        self.status_bar.showMessage("Data loaded successfully")
        self.update_row_count()

    """     def update_row_count(self):
            row_count = self.model.rowCount()
            self.status_bar.showMessage(f"Total rows: {row_count}") """

    def handle_error(self, error_msg):
        QMessageBox.critical(self, "Error", error_msg)
        self.progress_bar.hide()

    def closeEvent(self, event):
        if hasattr(self, 'file_loader_thread'):
            self.file_loader_thread.quit()
            self.file_loader_thread.wait()
        event.accept()

    def create_tab_system(self):
        self.tabs = QTabWidget()
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.table_group_box)
        splitter.addWidget(self.tabs)
        splitter.setSizes([600, 250])
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def apply_filters(self):
        column = self.filter_type.currentIndex()
        text = self.filter_input.text().lower()
        DataTableManager.apply_filter(self.table, column, text)


    def wrap_table_in_tab(self, table):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(table)
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(scroll)
        tab.setLayout(layout)
        return tab

    def create_donut_chart(self, data):
        donut = Widget()
        donut.setMinimumSize(600, 400)
        return donut

    def create_go_graph(self, data):
        file_path = "go_graph.html"
        go_terms = "GO:0000981,GO:0003674,GO:0003700,GO:0006355,GO:0006357,GO:0008150,GO:0009889,GO:0010468,GO:0010556,GO:0019219,GO:0019222,GO:0031323,GO:0031326,GO:0050789,GO:0050794,GO:0051171,GO:0051252,GO:0060255,GO:0065007,GO:0080090,GO:0140110,GO:1903506,GO:2000112,GO:2001141"
        go_list = go_terms.split(",")

        try:
            net = Network(height="750px", width="100%", directed=True)
            for go in go_list:
                net.add_node(go, label=go)
            for i in range(len(go_list) - 1):
                net.add_edge(go_list[i], go_list[i + 1])
            net.write_html(file_path)

            if not os.path.exists(file_path):
                print("Error: The HTML file was not created successfully.")
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            if not html_content:
                print("Error: HTML content is empty.")
                return None

            web_view = QWebEngineView()
            web_view.setHtml(html_content)

            graph_tab = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(web_view)
            graph_tab.setLayout(layout)
            self.tabs.addTab(graph_tab, "GO Graph")
            return graph_tab

        except Exception as e:
            print(f"Error generating or displaying the GO graph: {e}")
            return None

    def on_protein_selection_changed(self, selected, deselected):
        """Updates the hits table based on the selected protein."""
        selected_indexes = self.table.selectionModel().selectedIndexes()
        if not selected_indexes:
            return  

        selected_row = selected_indexes[0].row()

        selected_protein = self.parsed_results[selected_row]  
        logging.debug(f"Selected protein: {selected_protein}") 

        blast_hits = selected_protein.get("blast_hits", [])
        
        #todoo
        # self.update_hits_table(blast_hits)


    """     def update_hits_table(self, blast_hits):
            headers = ["Hit id", "Definition", "Accession", "Identity", "Alignment length", "E-value", "Bit-score", "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"]
            data = [[hit.get(header, "") for header in headers] for hit in blast_hits]
            self.additional_model = CustomTableModel(data, headers)
            self.additional_table.setModel(self.additional_model) """

    def create_tabs(self, parsed_results):
        """tabs for hits, graphs, metadata .."""
        self.tabs.addTab(self.create_tables_tab(parsed_results), "Hits")
        self.tabs.addTab(self.create_Iprscan_tab(parsed_results), "Domains")
        self.tabs.addTab(self.create_details_tab(), "Details")
        self.tabs.addTab(self.create_GO_tab(), "GO")
        self.generate_go_graph() # Temp
        self.tabs.addTab(self.create_chart_tab(), "Chart")
        self.tabs.addTab(self.create_graphs_tab(), "Chart2")
        self.tabs.addTab(self.create_MetaD_tab(), "Metadata")
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                color: #333333;
                font : Lato;
                font-weight: bold;
                font-size: 12px ;
            }
        """)
        logging.debug("Tabs created")



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

        # Spacer item before the logo
        spacer = QLabel(" ")
        self.status_bar.addWidget(spacer)

        # Logo SeaGo
        self.logo_label = QLabel()
        pixmap = QPixmap("./assets/seago_logo_rounded.png")  
        self.logo_label.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio))
        self.status_bar.addWidget(self.logo_label)

        # Version
        self.version_label = QLabel(" Version 1.0.0  |")
        self.status_bar.addWidget(self.version_label)

        # Copyright
        self.copyright_label = QLabel("© IFREMER 2024-2025 - Tous droits réservés")
        self.status_bar.addWidget(self.copyright_label)

        # Row count label
        self.row_count_label = QLabel()
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
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
        """)
#93FF96

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
            model = self.table.model()
            if model:
                visible_rows = sum(not self.table.isRowHidden(row) for row in range(model.rowCount()))
                self.row_count_label.setText(f"Rows displayed: {visible_rows}")


    """***************************** utils  *********************************************"""   
    

