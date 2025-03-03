from PySide6.QtWidgets import (
    QMainWindow, QScrollArea, QApplication, QTableWidget, QSplitter,
    QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QMenuBar, QSpacerItem, QSizePolicy,
    QMessageBox, QDialog, QStatusBar, QTextEdit, QTabWidget, QComboBox,QHeaderView,QTableView,
    QTableWidgetItem, QProgressBar,QSpinBox
)
from PySide6.QtGui import (
    QAction, QIcon, QPainter, QColor, QFont, QPixmap, QKeySequence, QShortcut
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
        self.large_data_handler = None  # Initialize large_data_handler
        self.load_config()
        self.init_ui()

    def load_config(self):
        """Load configuration and GO definitions"""
        obo_file_path = self.config.get("obo_file_path", "./ontologies/go-basic.obo")
        self.go_definitions = obo.load_go_definitions(obo_file_path)

    def init_ui(self):
        """Initialize main UI components"""
        self.setWindowTitle(f"Results - {self.file_path}")
        
        # Create main layout with a more persistent parent
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)

        # Reserve space for pagination at the bottom
        self.pagination_container = QWidget()
        self.pagination_container_layout = QVBoxLayout(self.pagination_container)
        self.pagination_container_layout.setContentsMargins(0, 0, 0, 0)
        self.pagination_container.setMinimumHeight(60)  # Reserve space

        self.create_main_table()
        self.create_menu_bar()
        self.create_filter_bar()
        self.create_tab_system()
        self.create_status_bar()
        
        # Add pagination container to the bottom of the main layout
        self.main_layout.addWidget(self.pagination_container)
        
        # Now create pagination controls inside the container
        self.create_pagination_controls()
        self.connect_signals()
        
        # Initialize large data handler
        from ui.large_data_handler import LargeDataHandler
        self.large_data_handler = LargeDataHandler(self)

        # Set memory monitoring timer
        self._memory_monitor_timer = QTimer(self)
        self._memory_monitor_timer.timeout.connect(self._check_memory_usage)
        self._memory_monitor_timer.start(5000)  # Check every 5 seconds

        # Add keyboard shortcut to reveal pagination
        self.show_pagination_shortcut = QShortcut(QKeySequence("F5"), self)
        self.show_pagination_shortcut.activated.connect(self.reveal_pagination)
        
        # Show pagination debug info in status bar
        self.status_bar.showMessage("Press F5 to reveal pagination controls if they're hidden")

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

    def create_tab_system(self):
        """Initialize tab system with splitter"""
        self.tabs = QTabWidget()
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.table_group_box)
        self.splitter.addWidget(self.tabs)
        self.splitter.setSizes([600, 250])

        # Add splitter to main layout, but keep pagination at bottom
        self.main_layout.insertWidget(0, self.splitter, 1)  # Add with stretch factor 1

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
        """Update status bar with row count and pagination info"""
        model = self.table.model()
        if model:
            row_count = model.rowCount()
            page_size = model.PAGE_SIZE
            total_pages = max(1, (row_count + page_size - 1) // page_size)
            current_page = model.current_page + 1  # 1-based for display
            
            # Show comprehensive info in status bar
            self.status_bar.showMessage(
                f"Total rows: {row_count} | "
                f"Page {current_page} of {total_pages} | "
                f"Use pagination controls below or press F5 to show them"
            )

    def handle_error(self, error_msg):
        """Handle errors"""
        QMessageBox.critical(self, "Error", error_msg)
        self.progress_bar.hide()
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
            pass
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
        """Create pagination controls for navigating through large datasets"""
        try:
            # If old pagination widget exists but is invalid, clean it up safely
            if hasattr(self, 'pagination_widget') and self.pagination_widget is not None:
                try:
                    if self.pagination_widget.parent():
                        self.pagination_container_layout.removeWidget(self.pagination_widget)
                    self.pagination_widget.deleteLater()
                except (RuntimeError, AttributeError) as e:
                    logging.debug(f"Cleanup of old pagination widget: {str(e)}")
            
            # Create new pagination widget with styling
            self.pagination_widget = QWidget()
            self.pagination_widget.setObjectName("permanent_pagination_widget")
            self.pagination_widget.setStyleSheet("""
                QWidget { 
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 4px;
                }
                QPushButton {
                    min-width: 60px;
                    padding: 4px;
                }
            """)
            
            # Create layout
            pagination_layout = QHBoxLayout(self.pagination_widget)
            pagination_layout.setContentsMargins(4, 4, 4, 4)
            pagination_layout.setSpacing(4)
            
            # Create all the necessary pagination controls
            self.prev_button = QPushButton("< Prev")
            self.page_info_label = QLabel("Page 1/1")
            self.next_button = QPushButton("Next >")
            self.page_jump = QSpinBox()
            self.page_jump.setMinimum(1)
            self.page_jump.setMaximum(1)
            self.page_jump_button = QPushButton("Go")
            self.page_size_combo = QComboBox()
            self.page_size_combo.addItems(["100", "200", "500"])
            self.page_size_combo.setCurrentIndex(0)  # Default to 100
            
            # Add debug button
            self.debug_button = QPushButton("Debug")
            self.debug_button.setStyleSheet("background-color: #ffcc66;")
            self.debug_button.clicked.connect(self.debug_pagination)
            
            # Create debug tools
            debug_tools = self.create_debug_tools()
            
            # Add widgets to layout
            pagination_layout.addWidget(QLabel("Items per page:"))
            pagination_layout.addWidget(self.page_size_combo)
            pagination_layout.addWidget(self.prev_button)
            pagination_layout.addWidget(self.page_info_label)
            pagination_layout.addWidget(self.next_button)
            pagination_layout.addWidget(QLabel("Jump to:"))
            pagination_layout.addWidget(self.page_jump)
            pagination_layout.addWidget(self.page_jump_button)
            pagination_layout.addWidget(self.debug_button)  # Add debug button
            pagination_layout.addWidget(debug_tools)
            pagination_layout.addStretch()
            
            # Add to dedicated pagination container layout
            self.pagination_container_layout.addWidget(self.pagination_widget)
            
            # Connect signals with try/except blocks
            self.prev_button.clicked.connect(self.on_prev_page)
            self.next_button.clicked.connect(self.on_next_page)
            self.page_jump_button.clicked.connect(self.on_page_jump)
            self.page_size_combo.currentIndexChanged.connect(self.on_page_size_changed)
            
            # Make pagination widget persist even during cleanup
            self.pagination_widget.setAttribute(Qt.WA_DeleteOnClose, False)
            
            # Hide until data is loaded
            self.pagination_widget.setVisible(False)
            return True
            
        except Exception as e:
            logging.error(f"Failed to create pagination controls: {str(e)}")
            traceback.print_exc()
            return False

    def on_prev_page(self):
        """Go to the previous page"""
        model = self.table.model()
        if model and model.current_page > 0:
            self.navigate_to_page(model.current_page)  # Current page is 0-based internally

    def on_next_page(self):
        """Go to the next page"""
        model = self.table.model()
        if not model:
            return
            
        max_page = max(0, (model._total_rows - 1) // model.PAGE_SIZE)
        if model.current_page < max_page:
            self.navigate_to_page(model.current_page + 2)  # +2 because current_page is 0-based

    @staticmethod
    def is_widget_valid(widget):
        """Safely check if a widget is valid and hasn't been deleted"""
        if widget is None:
            return False
            
        try:
            # Try multiple properties to ensure widget is valid
            widget.isVisible()  # Less likely to crash than objectName()
            return True
        except (RuntimeError, AttributeError, ReferenceError):
            # Handle various types of errors that can occur if widget is deleted
            return False
    
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
        """Update pagination information with robust widget checking"""
        # First check if model exists
        model = self.table.model()
        if not model:
            return
        
        # Get the true total count
        model._calculating_pages = True  # Set flag for total count
        total_rows = model._total_rows  # Use stored total rows
        model._calculating_pages = False
        
        # Get pagination values
        page_size = model.PAGE_SIZE
        current_page = model.current_page + 1  # 1-based for display
        max_page = max(1, (total_rows + page_size - 1) // page_size)
        
        start_row = model.current_page * page_size + 1
        end_row = min(start_row + page_size - 1, total_rows)
        
        # Check if pagination widgets exist and are valid
        if hasattr(self, 'page_info_label'):
            self.page_info_label.setText(f"Page {current_page}/{max_page} ({start_row}-{end_row} of {total_rows})")
            
        if hasattr(self, 'page_jump'):
            self.page_jump.setMaximum(max_page)
            self.page_jump.setValue(current_page)
            
        if hasattr(self, 'prev_button'):
            self.prev_button.setEnabled(current_page > 1)
            
        if hasattr(self, 'next_button'):
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
        try:
            # Update our streaming loader's total count for pagination
            if hasattr(self, 'streaming_loader'):
                self.streaming_loader.total_count = max(
                    getattr(self.streaming_loader, 'total_count', 0), 
                    total_count
                )
            
            from utils.table_manager import DataTableManager
            
            # Process batch
            processed_data = DataTableManager.process_batch(batch, self.go_definitions)
            
            # Add to model
            model = self.table.model()
            if model:
                first_new_row = model.rowCount()
                model.beginInsertRows(QModelIndex(), first_new_row, first_new_row + len(processed_data) - 1)
                model._data.extend(processed_data)
                
                # IMPORTANT: Update the total rows count for pagination
                model._total_rows = max(model._total_rows, total_count)
                
                model.endInsertRows()
                
                # Update UI safely
                try:
                    self.update_pagination_info()
                except Exception as e:
                    logging.error(f"Error updating pagination: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Error in batch processing: {str(e)}")
            traceback.print_exc()

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
        """Handle load completion with robust widget checking"""
        # Update status message if status bar exists
        if hasattr(self, 'status_bar') and DynamicTableWindow.is_widget_valid(self.status_bar):
            self.status_bar.showMessage(f"Loaded {total} records")
        
        # Hide progress bar if it exists
        if hasattr(self, 'progress_bar') and DynamicTableWindow.is_widget_valid(self.progress_bar):
            self.progress_bar.hide()
        
        # Handle pagination widget with extra care
        if hasattr(self, 'pagination_widget'):
            try:
                # Try to make pagination widget visible
                if DynamicTableWindow.is_widget_valid(self.pagination_widget):
                    self.pagination_widget.setVisible(True)
                else:
                    # If invalid but main_layout is valid, recreate pagination
                    if hasattr(self, 'main_layout') and DynamicTableWindow.is_widget_valid(self.main_layout.parentWidget()):
                        logging.warning("Pagination widget was deleted, recreating it")
                        self.create_pagination_controls()
            except Exception as e:
                # Last resort - log the error but don't crash
                logging.error(f"Failed to handle pagination widget: {str(e)}")

    def reveal_pagination(self):
        """Force reveal pagination controls and show debugging info"""
        try:
            # First make sure the container is valid
            if not hasattr(self, 'pagination_container') or not self.is_widget_valid(self.pagination_container):
                logging.warning("Pagination container is missing or invalid - recreating UI components")
                self.init_ui()  # Recreate the entire UI as a last resort
                return
                
            # Check if pagination widget exists and is valid
            has_valid_widget = (hasattr(self, 'pagination_widget') and 
                           self.pagination_widget is not None and 
                           self.is_widget_valid(self.pagination_widget))
            
            # If widget doesn't exist or is invalid, create a new one
            if not has_valid_widget:
                logging.warning("No pagination widget exists or widget was deleted - creating new one")
                success = self.create_pagination_controls()
                if not success:
                    logging.error("Failed to create pagination controls")
                    QMessageBox.warning(self, "Error", "Could not create pagination controls")
                    return
            
            # Make sure we have a valid widget now
            if hasattr(self, 'pagination_widget') and self.pagination_widget is not None:
                try:
                    self.pagination_widget.setVisible(True)
                    self.pagination_widget.show()  # Force show
                    self.pagination_widget.raise_()  # Bring to front
                    
                    # Debug info
                    # ...existing code...
                except RuntimeError as e:
                    logging.error(f"Widget validation failed: {str(e)}")
                    
                    # Create a new temporary pagination as a last resort
                    self.emergency_create_pagination()
        except Exception as e:
            logging.error(f"Error in reveal_pagination: {str(e)}")
            traceback.print_exc()
            
    def emergency_create_pagination(self):
        """Create a simplified emergency pagination control when all else fails"""
        try:
            # Create minimal pagination in a new popup window as a last resort
            popup = QDialog(self)
            popup.setWindowTitle("Emergency Pagination Controls")
            
            layout = QVBoxLayout(popup)
            
            # Create simple controls
            info_label = QLabel("Table Navigation")
            prev_btn = QPushButton("< Previous Page")
            next_btn = QPushButton("Next Page >")
            
            # Add to layout
            layout.addWidget(info_label)
            layout.addWidget(prev_btn)
            layout.addWidget(next_btn)
            
            # Connect signals
            prev_btn.clicked.connect(self.on_prev_page)
            next_btn.clicked.connect(self.on_next_page)
            
            # Show dialog
            popup.setMinimumWidth(300)
            popup.show()
            
        except Exception as e:
            logging.error(f"Even emergency pagination failed: {str(e)}")

    def on_last_page(self):
        """Jump to the last page of results"""
        model = self.table.model()
        if model:
            max_page = max(0, (model.rowCount() - 1) // model.PAGE_SIZE)
            model.setPage(max_page)
            self.update_pagination_info()
            self.create_visible_widgets()
            
            # Highlight to user that we're on the last page
            QMessageBox.information(self, "Navigation", f"Showing last page ({max_page+1})")

    def navigate_to_page(self, page_number):
        """Navigate to the specified page with improved view update"""
        try:
            model = self.table.model()
            if not model:
                return False
                
            # Get pagination values
            total_pages = max(1, (model._total_rows + model.PAGE_SIZE - 1) // model.PAGE_SIZE)
            
            # Ensure page number is within bounds
            page_number = max(1, min(page_number, total_pages))
            
            # Convert to 0-based for internal use
            page_idx = page_number - 1
            
            logging.debug(f"Navigating to page {page_number}/{total_pages}")
            
            # Debug: Log first few items before page change
            self._debug_log_current_page_data("Before page change")
            
            # FORCE COMPLETE MODEL RESET
            model.beginResetModel()
            
            # Remove page from cache to force reload with fresh data
            if page_idx in model._loaded_data:
                del model._loaded_data[page_idx]
                
            # Set current page BEFORE loading data
            model.current_page = page_idx
            
            # Clear all widgets to avoid stale data
            old_widgets = model.widgets.copy() if hasattr(model, 'widgets') else {}
            model.widgets = {}
            model.loaded_rows = set() if hasattr(model, 'loaded_rows') else set()
            model.widget_cells = set() if hasattr(model, 'widget_cells') else set()
            
            # Load data for the new page explicitly
            model._load_page(page_idx)
            
            # Complete the model reset
            model.endResetModel()
            
            # Clean up old widgets safely after reset completes
            for key, widget in old_widgets.items():
                try:
                    if widget:
                        widget.setParent(None)
                        widget.deleteLater()
                except Exception as e:
                    pass
            
            # Debug: Log data after page change to confirm correct data
            self._debug_log_current_page_data("After page change")
            
            # FORCE VIEW TO UPDATE - This is crucial!
            self.table.setModel(None)  # Remove model temporarily
            self.table.setModel(model)  # Re-set model to force complete refresh
            
            # Force the view to refresh completely
            self.table.viewport().update()
            self.table.reset()  # Reset view to ensure it repaints completely
            
            # Recreate all visible widgets
            QTimer.singleShot(50, self.recreate_all_visible_widgets)
            QTimer.singleShot(100, self.update_pagination_info)
            
            # Message in status bar
            self.status_bar.showMessage(f"Navigated to page {page_number}/{total_pages}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error navigating to page {page_number}: {str(e)}")
            traceback.print_exc()
            return False

    def recreate_all_visible_widgets(self):
        """Force recreate all visible widgets after page change"""
        try:
            model = self.table.model()
            if not model:
                return
                
            # Get visible area
            visible_rect = self.table.viewport().rect()
            first_visible = max(0, self.table.rowAt(visible_rect.top()))
            last_visible = self.table.rowAt(visible_rect.bottom())
            
            if last_visible < 0:
                last_visible = first_visible + 20
            
            # Recalculate which cells need widgets
            page = model.current_page
            if page not in model._loaded_data:
                return
                
            page_data = model._loaded_data[page]
            
            # Clear widget cells set before rebuilding it
            model.widget_cells = set()
            
            # Recreate widget cells mapping
            for row in range(len(page_data)):
                row_data = page_data[row]
                if "widgets" in row_data:
                    for col, header in enumerate(model.HEADERS):
                        # Look for matching widget info (case-insensitive)
                        header_key = header.lower()
                        for key in row_data["widgets"].keys():
                            if key.lower() == header_key:
                                widget_info = row_data["widgets"][key]
                                if widget_info.get("type") != "text":
                                    # This cell needs a widget
                                    model.widget_cells.add((row, col))
                                    break
            
            # Create widgets only for visible cells
            for row in range(first_visible, last_visible + 1):
                if row >= len(page_data):
                    continue
                    
                for col in range(model.columnCount()):
                    if (row, col) in model.widget_cells:
                        self.create_widget_for_cell(row, col)
            
            # Force the view to update
            self.table.viewport().update()
            
        except Exception as e:
            logging.error(f"Error recreating widgets: {str(e)}")

    def _debug_log_current_page_data(self, message):
        """Log the first few items from the current page for debugging"""
        model = self.table.model()
        if not model:
            return
            
        page = model.current_page
        logging.debug(f"=== {message} (Page {page+1}) ===")
        
        if page in model._loaded_data:
            page_data = model._loaded_data[page]
            # Log first 3 items
            for i in range(min(3, len(page_data))):
                item = page_data[i]
                protein_id = item.get("display", {}).get("Protein ID", "N/A")
                description = item.get("display", {}).get("Description", "N/A")
                logging.debug(f"Item {i}: ID={protein_id}, Desc={description[:30]}...")
        else:
            logging.debug(f"No data loaded for page {page+1}")
            
    def debug_pagination(self):
        """Debug function to print current pagination state"""
        try:
            model = self.table.model()
            if not model:
                QMessageBox.information(self, "Debug", "No model loaded")
                return
                
            # Gather debugging info
            debug_info = [
                f"Current page: {model.current_page + 1}",
                f"Page size: {model.PAGE_SIZE}",
                f"Total rows: {model._total_rows}",
                f"Max pages: {(model._total_rows + model.PAGE_SIZE - 1) // model.PAGE_SIZE}",
                f"Loaded pages: {list(model._loaded_data.keys())}",
                f"Memory usage: {model._memory_usage:.2f} MB"
            ]
            
            # Show debug info
            info = "\n".join(debug_info)
            QMessageBox.information(self, "Pagination Debug", info)
            
            # Force reload current page data
            current_page = model.current_page
            if current_page in model._loaded_data:
                del model._loaded_data[current_page]
            model._load_page(current_page)
            
            # Force update
            self.table.viewport().update()
            
        except Exception as e:
            logging.error(f"Error in debug_pagination: {str(e)}")
            traceback.print_exc()
            
    def create_debug_tools(self):
        """Create debugging tools for pagination issues"""
        debug_panel = QWidget()
        debug_layout = QHBoxLayout(debug_panel)
        debug_layout.setContentsMargins(2, 2, 2, 2)
        
        # Bouton pour comparer les pages
        compare_btn = QPushButton("Compare Pages")
        compare_btn.clicked.connect(self.debug_compare_pages)
        
        # Bouton pour forcer le rechargement de la page
        reload_btn = QPushButton("Reload Current")
        reload_btn.clicked.connect(self.debug_force_reload_page)
        
        # Bouton pour afficher les cellules actives
        cells_btn = QPushButton("Show Cell Info")
        cells_btn.clicked.connect(self.debug_show_cell_info)
        
        # Ajouter les boutons
        debug_layout.addWidget(compare_btn)
        debug_layout.addWidget(reload_btn)
        debug_layout.addWidget(cells_btn)
        
        return debug_panel

    def debug_compare_pages(self):
        """Compare current page data with next page data"""
        model = self.table.model()
        if not model:
            QMessageBox.information(self, "Debug", "No model loaded")
            return
            
        current_page = model.current_page
        next_page = current_page + 1
        
        # Charger les pages si nécessaire
        if current_page not in model._loaded_data:
            model._load_page(current_page)
        if next_page not in model._loaded_data:
            model._load_page(next_page)
        
        # Comparer les premiers éléments
        comparison = []
        comparison.append(f"Current Page: {current_page + 1}")
        
        if current_page in model._loaded_data:
            page_data = model._loaded_data[current_page]
            for i in range(min(5, len(page_data))):
                item = page_data[i]
                protein_id = item.get("display", {}).get("Protein ID", "N/A")
                debug_id = item.get("display", {}).get("_debug_id", "No ID")
                comparison.append(f"Item {i}: ID={protein_id}, Debug ID={debug_id}")
        
        comparison.append(f"\nNext Page: {next_page + 1}")
        
        if next_page in model._loaded_data:
            page_data = model._loaded_data[next_page]
            for i in range(min(5, len(page_data))):
                item = page_data[i]
                protein_id = item.get("display", {}).get("Protein ID", "N/A")
                debug_id = item.get("display", {}).get("_debug_id", "No ID")
                comparison.append(f"Item {i}: ID={protein_id}, Debug ID={debug_id}")
        
        # Afficher la comparaison
        QMessageBox.information(self, "Page Comparison", "\n".join(comparison))

        QMessageBox.information(self, "Page Comparison", "\n".join(comparison))

    def debug_force_reload_page(self):
        """Force reload current page data"""
        model = self.table.model()
        if not model:
            QMessageBox.information(self, "Debug", "No model loaded")
            return
            
        current_page = model.current_page
        
        # Supprimer les données de la page actuelle
        if current_page in model._loaded_data:
            del model._loaded_data[current_page]
        
        # Recharger les données
        model._load_page(current_page)
        
        # Effacer les widgets pour forcer la recréation
        model.widgets = {}
        model.loaded_rows = set()
        
        # Forcer la mise à jour
        self.table.viewport().update()
        
        QMessageBox.information(self, "Debug", f"Page {current_page + 1} reloaded")

    def debug_show_cell_info(self):
        """Show information about selected cells"""
        model = self.table.model()
        if not model:
            QMessageBox.information(self, "Debug", "No model loaded")
            return
            
        # Obtenir la sélection actuelle
        indexes = self.table.selectionModel().selectedIndexes()
        if not indexes:
            QMessageBox.information(self, "Debug", "No cell selected")
            return
            
        index = indexes[0]
        row = index.row()
        col = index.column()
        
        # Calculer l'index absolu
        true_row = model.current_page * model.PAGE_SIZE + row
        
        # Obtenir l'information sur la cellule
        page = model.current_page
        if page in model._loaded_data:
            try:
                item = model._loaded_data[page][row]
                
                # Préparer les infos
                info = []
                info.append(f"Cell: ({row}, {col})")
                info.append(f"True Row: {true_row}")
                info.append(f"Header: {model.HEADERS[col]}")
                
                if "display" in item:
                    display_data = item["display"]
                    info.append("\nDisplay Data:")
                    for key, value in display_data.items():
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            info.append(f"  {key}: {value}")
                        else:
                            info.append(f"  {key}: <complex type>")
                
                # Vérifier si la cellule a un widget
                info.append("\nWidget Info:")
                has_widget = (true_row, col) in model.widget_cells
                info.append(f"  Has Widget Cell: {has_widget}")
                widget_created = (row, col) in model.widgets
                info.append(f"  Widget Created: {widget_created}")
                
                # Afficher les informations
                QMessageBox.information(self, "Cell Info", "\n".join(info))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error getting cell info: {str(e)}")
        else:
            QMessageBox.warning(self, "Error", f"Page {page} not loaded")
            
    def on_prev_page(self):
        """Go to the previous page"""
        model = self.table.model()
        if model and model.current_page > 0:
            # Navigate directly to the previous page
            self.navigate_to_page(model.current_page)  # Current page is 0-based internally

    def on_next_page(self):
        """Go to the next page"""
        model = self.table.model()
        if not model:
            return
            
        max_page = max(0, (model._total_rows - 1) // model.PAGE_SIZE)
        if model.current_page < max_page:
            # Navigate directly to the next page
            self.navigate_to_page(model.current_page + 2)  # +2 because current_page is 0-based

    def _force_page_reload(self):
        """Force reload and redisplay of current page"""
        model = self.table.model()
        if not model:
            return
            
        # Get current page
        page = model.current_page
        
        # Remove from cache
        if page in model._loaded_data:
            del model._loaded_data[page]
            
        # Clear widgets
        model.widgets = {}
        model.loaded_rows = set()
        
        # Reload data
        model._load_page(page)
        
        # Reset model to force redraw
        model.beginResetModel()
        model.endResetModel()
        
        # Force update
        self.table.viewport().update()
        
        # Debug output
        logging.debug(f"Forced reload of page {page+1}")

    def _verify_page_data(self, expected_page=None):
        """Verify that correct page data is actually displayed"""
        model = self.table.model()
        if not model:
            return False
        
        # Get expected page
        page = expected_page if expected_page is not None else model.current_page
        
        # Check if data loaded
        if page not in model._loaded_data:
            logging.warning(f"Page {page+1} data not loaded!")
            return False
        
        # Log first few items for verification
        page_data = model._loaded_data[page]
        
        logging.debug(f"Verifying page {page+1} data:")
        for i in range(min(3, len(page_data))):
            item = page_data[i]
            protein_id = item.get("display", {}).get("Protein ID", "N/A")
            debug_id = item.get("display", {}).get("_debug_id", "No ID")
            logging.debug(f"Item {i}: ID={protein_id}, Debug ID={debug_id}")
        
        # Force view update if not showing correct data
        if model.rowCount() < 1 and len(page_data) > 0:
            logging.warning("Model reports zero rows but data exists! Forcing update.")
            model.beginResetModel()
            model.endResetModel()
            self.table.viewport().update()
            return False
            
        return True

    def emergency_page_fix(self):
        """Emergency fix for page display issues without causing loops"""
        model = self.table.model()
        if not model:
            return
        
        # Get current page
        page = model.current_page
        
        # Use a static flag to prevent recursive calls
        if hasattr(self, '_currently_fixing') and self._currently_fixing:
            logging.warning("Already fixing page - preventing recursive calls")
            return
            
        try:
            # Set flag to prevent recursion
            self._currently_fixing = True
            
            # Force clean reload
            if page in model._loaded_data:
                page_data = model._loaded_data[page].copy()  # Make a copy
                del model._loaded_data[page]  # Delete from cache
                
                # Reset model
                model.beginResetModel()
                model._loaded_data[page] = page_data  # Restore the data
                model.endResetModel()
                
                # Force update
                self.table.viewport().update()
                self._debug_log_current_page_data("After emergency fix")
                
                logging.debug("Emergency page fix applied")
                
                # Schedule additional updates
                QTimer.singleShot(10, self.table.viewport().update)
                QTimer.singleShot(10, self.update_pagination_info)
                
        finally:
            # Always clear flag when done
            self._currently_fixing = False

    def _verify_page_data_matches(self, page_idx):
        """Verify that the displayed page data matches the loaded data"""
        model = self.table.model()
        if not model or page_idx not in model._loaded_data:
            return False
        
        # Compare cached data with what's being shown
        page_data = model._loaded_data[page_idx]
        
        # Check first few visible rows


        # Check first few visible rows
        visible_rect = self.table.viewport().rect()
        first_visible = self.table.rowAt(visible_rect.top())
        
        if first_visible < 0:
            first_visible = 0
            
        # Compare a sample row
        if first_visible < len(page_data):
            cached_item = page_data[first_visible]
            displayed_item = None
            
            # Get the displayed data for this row
            try:
                protein_id_idx = model.HEADERS.index("Protein ID")
                displayed_id = model.data(model.index(first_visible, protein_id_idx), Qt.DisplayRole)
                
                # Get expected protein ID from cached data
                expected_id = cached_item.get("display", {}).get("Protein ID", "N/A")
                
                if displayed_id != expected_id:
                    logging.warning(f"Data mismatch! Row {first_visible}: Displayed={displayed_id}, Expected={expected_id}")
                    
                    # Attempt emergency fix - force data synchronization
                    self.emergency_page_fix()
                    return False
            except Exception as e:
                logging.error(f"Error verifying data match: {str(e)}")
        
        return True





