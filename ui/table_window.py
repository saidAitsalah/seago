from PySide6.QtWidgets import (
    QMainWindow, QScrollArea, QApplication, QTableWidget, QSplitter,
    QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QMenuBar, QSpacerItem, QSizePolicy,
    QMessageBox, QDialog, QStatusBar, QTextEdit, QTabWidget, QComboBox,QHeaderView,QTableView,
    QTableWidgetItem, QProgressBar,QSpinBox
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
from model.data_model import VirtualTableModel
from utils.loading.BatchJsonLoaderThread import BatchJsonLoaderThread
import logging
from model.data_model import MAIN_HEADERS
from utils.loading.StreamingJsonLoader import StreamingJsonLoader

logging.basicConfig(level=logging.DEBUG)

class DynamicTableWindow(QMainWindow):
    data_loaded = Signal()
    request_more_data = Signal(int)  # Signal emitted when we need more data

    def __init__(self, parsed_results, file_path, config=None):
        super().__init__()
        self.file_path = file_path
        self.parsed_results = parsed_results
        self.config = config if config is not None else {}
        self.go_definitions = {}
        self.detail_tabs = {}
        self.loader_thread = None  # Initialize loader_thread
        self.large_data_handler = None
    request_more_data = Signal(int)  # Signal emitted when we need more data

    def __init__(self, parsed_results, file_path, config=None):
        super().__init__()
        self.file_path = file_path
        self.parsed_results = parsed_results
        self.config = config if config is not None else {}
        self.go_definitions = {}
        self.detail_tabs = {}
        self.loader_thread = None  # Initialize loader_thread
        self.large_data_handler = None
        
        self.load_config()
        self.init_ui()

    def load_config(self):
        """Load configuration and GO definitions"""
        """Load configuration and GO definitions"""
        obo_file_path = self.config.get("obo_file_path", "./ontologies/go-basic.obo")
        self.go_definitions = obo.load_go_definitions(obo_file_path)

    def init_ui(self):
        """Initialize main UI components"""
        self.setWindowTitle(f"Results - {self.file_path}")
        
        # Create main layout
        main_widget = QWidget()
        self.main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        self.create_main_table()
        self.create_menu_bar()
        self.create_filter_bar()
        self.create_tab_system()
        self.create_status_bar()
        self.create_pagination_controls()
        self.connect_signals()
        
        # Initialize large data handler
        from ui.large_data_handler import LargeDataHandler
        self.large_data_handler = LargeDataHandler(self)

        # Set memory monitoring timer
        self._memory_monitor_timer = QTimer(self)
        self._memory_monitor_timer.timeout.connect(self._check_memory_usage)
        self._memory_monitor_timer.start(5000)  # Check every 5 seconds

    def _check_memory_usage(self):
        """Monitor memory usage and clean up if necessary"""
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        if memory_mb > 1000:  # Over 1GB
            logging.warning(f"Memory usage high: {memory_mb:.2f} MB, forcing cleanup")
            # Force aggressive cleanup
            if hasattr(self, 'model') and hasattr(self.model, '_cleanup_memory'):
                self.model._cleanup_memory(force_cleanup=True)
            # Force garbage collection
            import gc
            gc.collect()

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
                # Use MAIN_HEADERS instead of VirtualTableModel.HEADERS
                col_idx = MAIN_HEADERS.index(col)
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
        if hasattr(self, 'request_more_data'):
            self.request_more_data.connect(self.on_request_more_data)

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
        # ...existing code...
            return None

    def on_scroll_change(self, value):
        """Handle scroll events for dynamic loading"""
        # Use QTimer to delay widget creation which prevents UI freezing
        QTimer.singleShot(10, self.create_visible_widgets)
        
        # Check if we're near the end of our data
        model = self.table.model()
        if not model:
            return
            
        scrollbar = self.table.verticalScrollBar()
        # If we're more than 80% through the loaded data, request more
        if scrollbar.value() > scrollbar.maximum() * 0.8:
            self.request_more_data.emit(model.rowCount())

    def create_visible_widgets(self):
        """Create widgets ONLY for visible rows with ultra-efficient recycling"""
        model = self.table.model()
        if not model:
            return
            
        # Get visible rows
        visible_rect = self.table.viewport().rect()
        first_visible = self.table.rowAt(visible_rect.top())
        last_visible = self.table.rowAt(visible_rect.bottom())
        
        if first_visible < 0:
            first_visible = 0
        if last_visible < 0:
            last_visible = min(first_visible + 10, model.rowCount() - 1)
        
        # Extreme optimization: process even fewer widgets per frame
        widgets_created = 0
        max_widgets_per_frame = 3  # Create only 3 widgets per frame
        
        # Update model's visible range
        model.setVisibleRows(first_visible, last_visible)
        
        # Try to recycle widgets first
        if hasattr(model, 'recycle_widgets'):
            model.recycle_widgets(first_visible, last_visible)
        
        # Create only essential widgets in visible area
        for row in range(first_visible, last_visible + 1):
            if widgets_created >= max_widgets_per_frame:
                # Delay next widget creation to next frame
                QTimer.singleShot(1, self.create_visible_widgets)
                return
                
            if row >= model.rowCount() or row in model.loaded_rows:
                continue
                
            # Mark as processed
            model.loaded_rows.add(row)
            
            # Only process most important columns
            essential_cols = ["Protein ID", "Description"]
            for col_name in essential_cols:
                try:
                    col = model.HEADERS.index(col_name)
                    # Create only if needed and doesn't exist
                    if (row, col) in model.widget_cells and (row, col) not in model.widgets:
                        self.create_widget_for_cell(row, col)
                        widgets_created += 1
                except ValueError:
                    pass
        
        # Process pending events to keep UI responsive
        QApplication.processEvents()

    def on_request_more_data(self, current_count):
        """Request more data to be loaded when scrolling near the end"""
        # Initialize loader if needed
        if not hasattr(self, 'streaming_loader') or self.streaming_loader is None:
            # Show loading indicator in status bar
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("Loading data from file...")
                
            # Use the memory-efficient loader with smaller batches
            try:
                from utils.loading.memory_efficient_loader import MemoryEfficientLoader
                self.streaming_loader = MemoryEfficientLoader(
                    self.file_path, 
                    batch_size=25  # Smaller batches for more responsive UI
                )
            except ImportError:
                # Fall back to regular loader if memory efficient one isn't available
                self.streaming_loader = StreamingJsonLoader(
                    self.file_path, 
                    batch_size=25
                )
                
            self.streaming_loader.batch_loaded.connect(self.on_data_batch_loaded)
            self.streaming_loader.error_occurred.connect(self.on_loader_error)
            self.streaming_loader.progress_updated.connect(self.on_load_progress)
            self.streaming_loader.completed.connect(self.on_load_completed)
            
            # Start the streaming loader
            self.streaming_loader.start()
        else:
            # Already loading - do nothing to avoid overwhelming the system
            pass

    def create_pagination_controls(self):
        """Create pagination controls"""
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_widget)
        
        self.page_info_label = QLabel("Page 1")
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500", "1000"])
        self.page_size_combo.setCurrentIndex(1)  # Default to 100
        self.page_jump = QSpinBox()
        self.page_jump.setMinimum(1)
        self.page_jump.setMaximum(1)
        self.page_jump_button = QPushButton("Go")
        
        pagination_layout.addWidget(QLabel("Items per page:"))
        pagination_layout.addWidget(self.page_size_combo)
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addWidget(QLabel("Jump to:"))
        pagination_layout.addWidget(self.page_jump)
        pagination_layout.addWidget(self.page_jump_button)
        pagination_layout.addStretch()
        
        self.main_layout.addWidget(self.pagination_widget)
        

        # Connect signals
        self.prev_button.clicked.connect(self.on_prev_page)
        self.next_button.clicked.connect(self.on_next_page)
        self.page_jump_button.clicked.connect(self.on_page_jump)
        self.page_size_combo.currentIndexChanged.connect(self.on_page_size_changed)
        
        # Add scroll event handling
        self.table.verticalScrollBar().valueChanged.connect(self.on_scroll_change)
        
        # Hide until data is loaded
        self.pagination_widget.setVisible(False)

    def on_prev_page(self):
        model = self.table.model()
        if model and model.current_page > 0:
            model.setPage(model.current_page - 1)
            self.update_pagination_info()
            self.create_visible_widgets()
    
    def on_next_page(self):
        model = self.table.model()
        if model:
            max_page = max(0, (model.rowCount() - 1) // model.PAGE_SIZE)
            if model.current_page < max_page:
                model.setPage(model.current_page + 1)
                self.update_pagination_info()
                self.create_visible_widgets()
    
    def on_page_jump(self):
        model = self.table.model()
        if model:
            page = self.page_jump.value() - 1  # 0-based indexing internally
            max_page = max(0, (model.rowCount() - 1) // model.PAGE_SIZE)
            page = max(0, min(page, max_page))
            model.setPage(page)
            self.update_pagination_info()
    def on_page_size_changed(self):
        model = self.table.model()
        if model:
            size = int(self.page_size_combo.currentText())
            model.PAGE_SIZE = size
            model.setPage(0)  # Reset to first page
            self.update_pagination_info()
            self.create_visible_widgets()
    
    def update_pagination_info(self):
        model = self.table.model()
        if model:
            total_rows = model.rowCount()
            page_size = model.PAGE_SIZE
            current_page = model.current_page + 1  # 1-based for display
            max_page = max(1, (total_rows + page_size - 1) // page_size)
            
            start_row = model.current_page * page_size + 1
            end_row = min(start_row + page_size - 1, total_rows)
            
            self.page_info_label.setText(f"Page {current_page}/{max_page} (rows {start_row}-{end_row} of {total_rows})")
            self.page_jump.setMaximum(max_page)
            self.page_jump.setValue(current_page)
            
            self.prev_button.setEnabled(current_page > 1)
            self.next_button.setEnabled(current_page < max_page)
    
    def create_visible_widgets(self):
        """Create widgets only for visible rows with throttling"""
        model = self.table.model()
        if not model:
            return
            
        # Get visible rows
        from_data_mgr = hasattr(model, "widgets") and hasattr(model, "widget_cells")
        if not from_data_mgr:
            return
        
        visible_rect = self.table.viewport().rect()
        first_visible = self.table.rowAt(visible_rect.top())
        last_visible = self.table.rowAt(visible_rect.bottom())
        
        if first_visible < 0:
            first_visible = 0
        if last_visible < 0:
            last_visible = min(first_visible + 20, model.rowCount() - 1)
        
        # Update model's visible range
        model.setVisibleRows(first_visible, last_visible)
        
        # Limit the number of widgets to create per call to prevent freezing
        widgets_created = 0
        max_widgets_per_call = 10
        
        # Create widgets only for visible rows
        for row in range(first_visible, last_visible + 1):
            if widgets_created >= max_widgets_per_call:
                # Schedule another call to continue creating widgets
                QTimer.singleShot(50, self.create_visible_widgets)
                return
                
            if row >= model.rowCount():
                continue
                
            if row in model.loaded_rows:
                continue  # Skip already processed rows
                
            model.loaded_rows.add(row)
            
            for col in range(model.columnCount()):
                # Only process widget cells
                if (row, col) in model.widget_cells and (row, col) not in model.widgets:
                    self.create_widget_for_cell(row, col)
                    widgets_created += 1
                    
                    if widgets_created >= max_widgets_per_call:
                        break

    def create_widget_for_cell(self, row, col):
        """Create a widget for the specified cell if needed"""
        model = self.table.model()
        if not model or row >= len(model._data):
            return
            
        row_data = model._data[row]
        if "widgets" not in row_data:
            return
            
        widgets_data = row_data["widgets"]
        header = model.HEADERS[col]
        
        # Find matching widget info
        matching_key = None
        for key in widgets_data.keys():
            if key.lower() == header.lower():
                matching_key = key
                break
                
        if not matching_key:
            return
            
        widget_info = widgets_data[matching_key]
        widget_type = widget_info.get("type")
        widget_data = widget_info.get("data")
        
        if widget_type and widget_data is not None:
            try:
                from utils.table_manager import DataTableManager
                widget = DataTableManager.create_widget(widget_type, widget_data, model.go_definitions)
                if widget:
                    model.widgets[(row, col)] = widget
                    self.table.setIndexWidget(model.index(row, col), widget)
            except Exception as e:
                logging.error(f"Error creating widget for cell ({row}, {col}): {str(e)}")

    def on_scroll_change(self, value):
        """Handle scroll events to load widgets for newly visible rows"""
        self.create_visible_widgets()
        
        # Check if we're near the end of our data
        model = self.table.model()
        if not model:
            return
            
        scrollbar = self.table.verticalScrollBar()
        # If we're more than 80% through the loaded data, request more
        if scrollbar.value() > scrollbar.maximum() * 0.8:
            self.request_more_data.emit(model.rowCount())

    def on_data_batch_loaded(self, batch, start_index, total_count):
        """Handle loaded data batch"""
        from utils.table_manager import DataTableManager
        
        # Process batch
        processed_data = DataTableManager.process_batch(batch, self.go_definitions)
        
        # Add to model
        model = self.table.model()
        if model:
            first_new_row = model.rowCount()
            model.beginInsertRows(QModelIndex(), first_new_row, first_new_row + len(processed_data) - 1)
        # Show progress in status bar
            model._data.extend(processed_data)
            model.endInsertRows()
            
            # Update UI
            self.update_pagination_info()

    def on_loader_error(self, error_msg):
        """Handle loader errors"""
        self.handle_error(error_msg)
        self.process_events()  # Keep UI responsive

    def on_load_progress(self, current, total):
        """Update UI with loading progress"""
        # Show progress in status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Loading data: {current}/{total} records ({current*100//total}%)")
            
        # Update progress bar
        if hasattr(self, 'progress_bar'):
            self.progress_bar.show()
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)

    def on_load_completed(self, total):
        """Handle load completion"""
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Loaded {total} records")
            
        if hasattr(self, 'progress_bar'):
            self.progress_bar.hide()
            
        # Make pagination visible
        if hasattr(self, 'pagination_widget'):
            try:
                self.pagination_widget.setVisible(True)
            except RuntimeError:
                # Widget was deleted - recreate it
                logging.warning("Pagination widget was deleted, recreating it")
                self.create_pagination_controls()
                if hasattr(self, 'pagination_widget'):
                    self.pagination_widget.setVisible(True)





