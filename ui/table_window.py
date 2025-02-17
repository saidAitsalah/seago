from PySide6.QtWidgets import (
    QMainWindow, QScrollArea, QApplication, QTableWidget, QSplitter,
    QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QMenuBar, QSpacerItem, QSizePolicy,
    QMessageBox, QDialog, QStatusBar, QTextEdit, QTabWidget, QComboBox,
    QTableWidgetItem, QProgressBar
)
from PySide6.QtGui import (
    QAction, QIcon, QPainter, QColor, QFont, QPixmap
)
from PySide6.QtCore import (
    Qt, QTimer, QMetaObject, Slot, Signal, QObject, QThread
)
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtWebEngineWidgets import QWebEngineView
from pyvis.network import Network
import json
import os
import traceback
from typing import List, Dict, Any, Tuple

from utils.table_manager import DataTableManager
from utils.export_utils import export_to_json, export_to_csv, export_to_tsv
from utils.OBO_handler import obo
from ui.donut_widget import Widget
from utils.loading.DataLoader import FileLoaderThread

class DynamicTableWindow(QMainWindow):
    data_loaded = Signal(object)
    
    def __init__(self, parsed_results, file_path, parent=None,config=None):
            # Initialisation correcte de la classe parente
            super().__init__(parent)
            
            # Configuration de la fenêtre
            self.setWindowTitle("seaGo")
            self.setGeometry(100, 100, 1400, 850)
            self.setWindowIcon(QIcon('./assets/image.png'))
            
            # Initialisation des variables
            self.file_path = file_path
            self.parsed_results = parsed_results
            self.load_config()
            obo_file_path = self.config.get("obo_file_path", "./ontologies/go-basic.obo")
            self.go_definitions = obo.load_go_definitions(obo_file_path)
            
            self.config = config if config is not None else {}  # Initialize config
            self.init_thread()
            # Configuration de l'interface
            self.init_ui()

    def init_ui(self):
        """Initialize main UI components"""
        self.create_main_table()
        self.create_menu_bar()
        self.create_filter_bar()
        self.create_tab_system()
        self.create_status_bar()
        self.connect_signals()

    def create_main_table(self):
        """Create and configure main table"""
        self.main_table = DataTableManager.create_table('main')
        self.table_group_box = QGroupBox("")
        self.main_table.setObjectName("MainResultsTable")  # Pour le CSS
        self.main_table.horizontalHeader().setStretchLastSection(True)
        layout = QVBoxLayout()
        layout.addWidget(self.main_table)
        self.table_group_box.setLayout(layout)

    def create_tab_system(self):
        """Initialize tab system with splitter"""
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

    def connect_signals(self):
        """Connect UI signals"""
        self.main_table.itemChanged.connect(self.update_row_count)
        self.main_table.cellClicked.connect(self.on_cell_selected)
        self.main_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.data_loaded.connect(self.on_data_loaded)

    def init_thread(self):
        """Initialize data loading thread"""
        self.file_loader_thread = FileLoaderThread(
            self.file_path,
            self.config.get("obo_file_path", "./ontologies/go-basic.obo")
        )
        self.file_loader_thread.data_loaded.connect(self.handle_data_loaded)
        self.file_loader_thread.error_occurred.connect(self.handle_error)
        self.file_loader_thread.start()

    @Slot(object)
    def handle_data_loaded(self, data):
        """Handle loaded data and update UI"""
        self.parsed_results = data
        self.data_loaded.emit(data)

    @Slot(object)
    def on_data_loaded(self, data):
        """Update UI with new data"""
        DataTableManager.populate_table(self.main_table, data,self.go_definitions)
        self.create_dynamic_tabs(data)
        self.main_table.resizeColumnsToContents()

    def create_dynamic_tabs(self, data):
        """Create dynamic tabs based on data"""
        self.tabs.clear()
        go_terms = data.get('go_terms', []) if isinstance(data, dict) else []
        tabs = [
            ('Blast Hits', 'blast', data),
            ('InterPro Domains', 'interpro', data),
           # ('GO Terms', 'go', data.get(go_terms)),
            ('Analysis', 'charts', data)
        ]
        
        for title, tab_type, tab_data in tabs:
            tab = self.create_tab(tab_type, tab_data)
            if tab:
                self.tabs.addTab(tab, title)

    def create_tab(self, tab_type, data):
        """Create individual tab based on type"""
        if tab_type == 'blast':
            return self.create_blast_tab(data)
        elif tab_type == 'interpro':
            return self.create_interpro_tab(data)
        elif tab_type == 'go':
            return self.create_go_tab(data)
        elif tab_type == 'charts':
            return self.create_analysis_tab(data)
        return None

    def create_blast_tab(self, data):
        """Create Blast results tab"""
        table = DataTableManager.create_table('blast')
        DataTableManager.populate_table(table, data, self.go_definitions)
        return self.wrap_table_in_tab(table)

    def create_interpro_tab(self, data):
        """Create InterPro domains tab"""
        table = DataTableManager.create_table('interpro')
        DataTableManager.populate_table(table, data, self.go_definitions)
        return self.wrap_table_in_tab(table)

    def create_go_tab(self, data):
        """Create GO terms tab"""
        table = DataTableManager.create_table('go')
        DataTableManager.populate_table(table, data, self.go_definitions)
        return self.wrap_table_in_tab(table)

    def create_analysis_tab(self, data):
        """Create analysis charts tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Add charts and visualizations here
        layout.addWidget(self.create_donut_chart(data))
        layout.addWidget(self.create_go_graph(data))
        
        tab.setLayout(layout)
        return tab

    def wrap_table_in_tab(self, table):
        """Wrap table in scrollable tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(table)
        
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(scroll)
        tab.setLayout(layout)
        return tab

    def create_donut_chart(self, data):
        """Create donut chart visualization"""
        donut = Widget()
        donut.setMinimumSize(600, 400)
        return donut

    def create_go_graph(self, data):
        """Generate Pyvis graph in QWebEngine widget dynamically from GO list."""
        file_path = "go_graph.html"  # Temp file

        # Liste of go terms to test
        go_terms = "GO:0000981,GO:0003674,GO:0003700,GO:0006355,GO:0006357,GO:0008150,GO:0009889,GO:0010468,GO:0010556,GO:0019219,GO:0019222,GO:0031323,GO:0031326,GO:0050789,GO:0050794,GO:0051171,GO:0051252,GO:0060255,GO:0065007,GO:0080090,GO:0140110,GO:1903506,GO:2000112,GO:2001141"
        go_list = go_terms.split(",")

        try:
            # Pyvis graph
            net = Network(height="750px", width="100%", directed=True)

            # Add nodes
            for go in go_list:
                net.add_node(go, label=go)

            # Add simple edges
            for i in range(len(go_list) - 1):
                net.add_edge(go_list[i], go_list[i + 1])

            # Generate HTML content
            net.write_html(file_path)

            # Check if file was created
            if not os.path.exists(file_path):
                print("Error: The HTML file was not created successfully.")
                return None

            # Read the generated HTML file
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            if not html_content:
                print("Error: HTML content is empty.")
                return None

            # Display in QWebEngineView
            web_view = QWebEngineView()
            web_view.setHtml(html_content)

            # Create and set up the widget layout
            graph_tab = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(web_view)
            graph_tab.setLayout(layout)

            self.tabs.addTab(graph_tab, "GO Graph")
            
            return graph_tab  # Ensure the graph tab is returned

        except Exception as e:
            print(f"Error generating or displaying the GO graph: {e}")
            return None


    def create_menu_bar(self):
        """Create main menu bar"""
        menu_bar = QMenuBar(self)
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(QAction("Open", self))
        file_menu.addAction(QAction("Exit", self, triggered=self.close))

        # Export menu
        export_menu = menu_bar.addMenu("Export")
        export_types = [
            ("JSON", export_to_json),
            ("CSV", export_to_csv),
            ("TSV", export_to_tsv)
        ]
        for name, handler in export_types:
            export_menu.addAction(
                QAction(f"Export to {name}", self, triggered=lambda: handler(self.main_table))
            )

        # Help menu
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(QAction("About", self, triggered=self.show_about))
        
        self.setMenuBar(menu_bar)

    def create_filter_bar(self):
        """Create dynamic filter bar"""
        filter_bar = QWidget()
        layout = QHBoxLayout()
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter results...")
        
        self.filter_type = QComboBox()
        self.filter_type.addItems(["Protein ID", "Description", "GO Terms"])
        
        layout.addWidget(QLabel("Filter by:"))
        layout.addWidget(self.filter_type)
        layout.addWidget(self.filter_input)
        layout.addWidget(QPushButton("Apply", clicked=self.apply_filters))
        
        filter_bar.setLayout(layout)
        self.table_group_box.layout().insertWidget(0, filter_bar)

    def apply_filters(self):
        """Apply dynamic filters to table"""
        column = self.filter_type.currentIndex()
        text = self.filter_input.text().lower()
        DataTableManager.apply_filter(self.main_table, column, text)

    def create_status_bar(self):
        """Create application status bar"""
        status = QStatusBar()
        self.progress = QProgressBar()
        self.progress.hide()
        
        status.addPermanentWidget(QLabel("Status:"))
        status.addPermanentWidget(self.progress)
        self.setStatusBar(status)

    @Slot(int)
    def update_progress(self, value):
        """Update progress bar"""
        self.progress.show()
        self.progress.setValue(value)
        if value >= 100:
            self.progress.hide()

    @Slot(int, int)
    def on_cell_selected(self, row, column):
        """Handle cell selection"""
        if item := self.main_table.item(row, column):
            self.show_details(item.text())

    def show_details(self, content):
        """Show details in dedicated tab"""
        if not hasattr(self, 'details_tab'):
            self.details_tab = QTextEdit()
            self.details_tab.setReadOnly(True)
            self.tabs.addTab(self.details_tab, "Details")
        self.details_tab.setText(content)
        self.tabs.setCurrentWidget(self.details_tab)

    @Slot()
    def on_selection_changed(self):
        """Handle row selection changes"""
        if selected := self.main_table.selectedItems():
            row = selected[0].row()
            self.update_blast_results(row)

    def update_blast_results(self, row):
        """Update Blast results for selected row"""
        if not self.parsed_results:
            return
            
        protein_data = self.parsed_results[row]
        if blast_hits := protein_data.get('blast_hits'):
            if blast_tab := self.tabs.findChild(QTableWidget, 'blast'):
                DataTableManager.populate_table(blast_tab, blast_hits, self.go_definitions)

    def load_config(self):
        """Load application configuration"""
        config_file = "./config.json"
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}
            print(f"Config file {config_file} not found")

    @Slot(str)
    def handle_error(self, message):
        """Show error message dialog"""
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(f"Data loading failed: {message}")
        error_dialog.exec()

    def show_about(self):
        """Show about dialog"""
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About seaGo")
        about_dialog.setText("Bioinformatics data visualization tool")
        about_dialog.exec()

    def update_row_count(self):
            row_count = self.main_table.rowCount()
            print(f"Row count updated: {row_count}")

    """   def init_thread(self):
        # Access config safely
        obo_file_path = self.config.get("obo_file_path", "./ontologies/go-basic.obo")
        print(f"OBO file path: {obo_file_path}")
        # Add other initialization logic here """
    
    def closeEvent(self, event):
        """Ensure the thread is stopped before closing the application."""
        if hasattr(self, 'file_loader_thread') and self.file_loader_thread.isRunning():
            self.file_loader_thread.quit()
            self.file_loader_thread.wait()  # Ensure thread stops before exiting
        event.accept()

       
    def load_config(self):
        """Charger la configuration depuis le fichier JSON"""
        config_file = "./config.json"
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                self.config = json.load(f)
        else:
            print(f"Le fichier de configuration {config_file} est introuvable.")
            self.config = {}

    