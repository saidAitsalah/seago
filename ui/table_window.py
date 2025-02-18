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
    Qt, QTimer, QMetaObject, Slot,QAbstractTableModel,QModelIndex, Signal, QObject, QThread
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

from PySide6.QtWidgets import (
    QMainWindow, QTableView, QVBoxLayout, QGroupBox, QSplitter, QTabWidget,
    QHeaderView, QWidget, QStatusBar, QProgressBar, QLineEdit, QComboBox, QPushButton, QLabel, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from utils.table_manager import DataTableManager
from utils.OBO_handler import obo

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

        # Set up virtual model
        self.model = VirtualTableModel(self.parsed_results, self.go_definitions)
        self.table.setModel(self.model)

        # Configure table
        self.table.setObjectName("MainResultsTable")
        header = self.table.horizontalHeader()
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

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.table_group_box.setLayout(layout)

    def create_filter_bar(self):
        """Create filter bar for table"""
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

    def create_menu_bar(self):
        """Create menu bar"""
        self.menuBar().clear()
        # Add menu items here

    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()

    def connect_signals(self):
        """Connect UI signals"""
        if self.table.model():
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.data_loaded.connect(self.on_data_loaded)

    def on_selection_changed(self):
        """Handle table selection changes"""
        indexes = self.table.selectionModel().selectedIndexes()
        if indexes:
            row = indexes[0].row()
            self.handle_row_selection(row)

    def handle_row_selection(self, row):
        """Update detail views for selected row"""
        page = row // VirtualTableModel.PAGE_SIZE
        if page in self.model._loaded_data:
            item_data = self.model._loaded_data[page][row % VirtualTableModel.PAGE_SIZE]
            self.update_detail_tabs(item_data)

    def update_detail_tabs(self, item_data):
        """Update detail tabs with selected item data"""
        # Update BLAST tab
        if 'blast_hits' in item_data['display']:
            self.update_blast_tab(item_data['display']['blast_hits'])

        # Update InterPro tab
        if 'InterPro' in item_data['display']:
            self.update_interpro_tab(item_data['display']['InterPro'])

        # Update GO tab
        if 'GO' in item_data['display']:
            self.update_go_tab(item_data['display']['GO'])

    def on_data_loaded(self):
        """Handle completed data loading"""
        self.progress_bar.hide()
        self.status_bar.showMessage("Data loaded successfully")
        self.update_row_count()

    def update_row_count(self):
        """Update status bar with row count"""
        row_count = self.model.rowCount()
        self.status_bar.showMessage(f"Total rows: {row_count}")

    def handle_error(self, error_msg):
        """Handle errors"""
        QMessageBox.critical(self, "Error", error_msg)
        self.progress_bar.hide()

    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'file_loader_thread'):
            self.file_loader_thread.quit()
            self.file_loader_thread.wait()
        event.accept()

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

    def apply_filters(self):
        """Apply dynamic filters to table"""
        column = self.filter_type.currentIndex()
        text = self.filter_input.text().lower()
        DataTableManager.apply_filter(self.table, column, text)

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

        # List of go terms to test
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


class VirtualTableModel(QAbstractTableModel):
    HEADERS = ["Protein ID", "Description", "Length", "Results",
               "PFAMs", "GO", "Classification",
               "Preferred name", "COG", "Enzyme", "InterPro"]
    PAGE_SIZE = 100

    def __init__(self, data, go_definitions=None):
        super().__init__()
        self._data = data  # Directly assign the list of results
        self._loaded_data = {}
        self._go_definitions = go_definitions or {}
        self._table_manager = DataTableManager()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        # Load page if needed
        page = row // self.PAGE_SIZE
        if page not in self._loaded_data:
            self._load_page(page)

        row_data = self._loaded_data[page][row % self.PAGE_SIZE]
        
        if role == Qt.DisplayRole:
            return str(row_data['display'].get(self.HEADERS[col], ""))
            
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.HEADERS[section]
            return str(section + 1)
        return None

    def _load_page(self, page):
        start = page * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(self._data))
        
        page_data = []
        for item in self._data[start:end]:
            processed = DataTableManager._process_main_row(item, self._go_definitions)
            page_data.append(processed)
            
        self._loaded_data[page] = page_data