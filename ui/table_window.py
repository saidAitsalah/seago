from PySide6.QtWidgets import (
    QMainWindow, QScrollArea, QSplitter,QSpinBox,QDockWidget,
    QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QLineEdit, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QMenuBar, QInputDialog,
    QMessageBox, QDialog,QFileDialog, QStatusBar, QTabWidget,QTableWidgetItem, QComboBox,QHeaderView,QTableView, QProgressBar,QTableWidget, QTextEdit
)
from PySide6 import QtWidgets
from PySide6.QtGui import (
    QAction, QIcon,QColor, QKeySequence, QShortcut,QFont, QPainter
)
from PySide6.QtCore import (
    Qt, QTimer, QModelIndex, Signal,QItemSelectionModel
)
from PySide6.QtCharts import QChart, QChartView, QPieSeries 
from PySide6.QtWebEngineWidgets import QWebEngineView
from pyvis.network import Network
import os
import traceback
from utils.table_manager import DataTableManager
from utils.export_utils import export_to_json, export_to_csv, export_to_tsv
from utils.OBO_handler import obo
from ui.donut_widget import Widget
from model.data_model import VirtualTableModel
import logging
from model.data_model import MAIN_HEADERS
from utils.loading.StreamingJsonLoader import StreamingJsonLoader
from utils.Debugging.TableDebugger import TableDebugger
from ui.FilterManager import FilterManager
import datetime
import json


logging.basicConfig(level=logging.DEBUG)

class DynamicTableWindow(QMainWindow):
    data_loaded = Signal()
    request_more_data = Signal(int)  

    def __init__(self, parsed_results, file_path, config=None):
        super().__init__()
        self.file_path = file_path
        self.parsed_results = parsed_results
        self.config = config if config is not None else {}
        self.go_definitions = {}
        self.detail_tabs = {}
        self.loader_thread = None  # Initialize loader_thread
        self.large_data_handler = None  # Initialize large_data_handler
        self.modified_rows = set()  # Set of row indices that have been modified
        self.original_values = {}   # Dictionary to store original values {(row, col): original_value}
        self.change_log = []        # List to store all changes for audit/export
        self._processing_data_change = False  

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

            # Create filter layout FIRST - before trying to use it
        self.filter_layout = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filtrer toutes les colonnes...")
        self.filter_layout.addWidget(self.filter_edit)
        self.table_debugger = TableDebugger(self) 

        
        self.create_main_table()

        self.filter_manager = FilterManager(self, self.table, self.model)
        self.proxy_model = self.filter_manager.setup_filter(self.filter_edit, self.filter_layout)

        self.complete_filter_setup()

        self.create_menu_bar()
        self.create_tab_system()
        self.create_tabs(self.parsed_results)  
        self.add_debug_panel()
        #self.add_debug2_panel()


        # Add Export with Changes to File menu
        if hasattr(self.model, 'dataChanged'):
            self.model.dataChanged.connect(self.on_data_changed) 

        self.table.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed)
        self.table.setTabKeyNavigation(True)
        self.table.doubleClicked.connect(self.handle_cell_double_clicked)
        

        self.create_status_bar()
 
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
        self.table.verticalScrollBar().valueChanged.connect(self.on_scroll_change)
        
        # Show pagination debug info in status bar
        #self.status_bar.showMessage("Press F3 to force refresh filter if results don't update correctly")
        #self.status_bar.showMessage("Press F5 to reveal pagination controls if they're hidden")

        """    # Add a change tracking indicator to the status bar
        self.change_indicator = QLabel("No changes")
        self.statusBar().addPermanentWidget(self.change_indicator) """

        QTimer.singleShot(3000, lambda: self.force_selection_with_retry(0))

    def handle_cell_double_clicked(self, index):
        self.force_edit_cell(index.row(), index.column())    

    def add_debug2_panel(self):
        """Add debug panel to help diagnose issues"""
        debug_dock = QDockWidget("Debug Tools", self)
        debug_widget = QWidget()
        debug_layout = QVBoxLayout(debug_widget)
        
        # Add direct edit test
        edit_test_group = QGroupBox("Direct Edit Test")
        edit_layout = QHBoxLayout()
        edit_test_group.setLayout(edit_layout)
        
        # Row and column inputs
        row_input = QSpinBox()
        row_input.setMinimum(0)
        row_input.setMaximum(100)
        col_input = QSpinBox()
        col_input.setMinimum(0)
        col_input.setMaximum(10)
        
        # Button to trigger edit
        test_edit_button = QPushButton("Test Edit")
        test_edit_button.clicked.connect(lambda: self.force_edit_cell(row_input.value(), col_input.value()))
        
        # Arrange layout
        edit_layout.addWidget(QLabel("Row:"))
        edit_layout.addWidget(row_input)
        edit_layout.addWidget(QLabel("Col:"))
        edit_layout.addWidget(col_input)
        edit_layout.addWidget(test_edit_button)
        
        # Add to debug panel
        debug_layout.addWidget(edit_test_group)
        
        # Set widget and add dock
        debug_dock.setWidget(debug_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, debug_dock)

    def force_edit_cell(self, row, col):
        """Force an edit operation on a specific cell"""
        try:
            # Create index for the cell
            source_model = self.model
            proxy_model = self.proxy_model
            
            # Convert from table coordinates to source model coordinates
            if hasattr(proxy_model, 'mapToSource'):
                proxy_index = proxy_model.index(row, col)
                source_index = proxy_model.mapToSource(proxy_index)
                source_row = source_index.row()
                source_col = source_index.column()
            else:
                source_row = row
                source_col = col
                
            logging.debug(f"Forcing edit on cell: table({row},{col}) -> source({source_row},{source_col})")
            
            # Get the current value
            current_value = self.table.model().index(row, col).data()
            logging.debug(f"Current value: {current_value}")
            
            # Create a simple edit dialog
            new_value, ok = QInputDialog.getText(
                self, "Edit Cell Value", 
                f"Edit value for cell ({row}, {col}):",
                text=str(current_value) if current_value else ""
            )
            
            if ok and new_value:
                # Apply the edit directly to the model (bypass delegate)
                result = self.table.model().setData(
                    self.table.model().index(row, col), 
                    new_value, 
                    Qt.EditRole
                )
                logging.debug(f"Edit result: {result}")
                
                # Trigger update if needed
                if result:
                    try:
                        # Try to update visuals - CRITICAL: Wrap this in try/except
                        self._highlight_modified_row(row)
                        
                        # Safely update status indicator if it exists
                        if hasattr(self, 'change_indicator') and self.change_indicator is not None:
                            try:
                                self.change_indicator.setText(f"  Cell ({row}, {col}) modified *")
                                self.change_indicator.setStyleSheet("color: white; font-weight: bold;")
                            except Exception as ui_err:
                                logging.error(f"UI update error: {ui_err}")
                        else:
                            # Fallback to status bar
                            self.statusBar().showMessage(f"  Cell ({row},{col}) modified *")
                            
                    except Exception as highlight_err:
                        logging.error(f"Error highlighting modified row: {highlight_err}")
                        # Continue even if highlighting fails
                        self.statusBar().showMessage(f"Cell modified but couldn't highlight row: {str(highlight_err)}")
        except Exception as e:
            logging.error(f"Error forcing edit: {e}")
            traceback.print_exc()
    
    
    def on_data_changed(self, topLeft, bottomRight, roles=None):
        """Handle when data in the model changes"""
        if self._processing_data_change:
            return
        try:
            self._processing_data_change = True 
            # Initialize modified collections if they don't exist
            if not hasattr(self, 'modified_rows'):
                self.modified_rows = set()
                
            if not hasattr(self, 'original_values'):
                self.original_values = {}
                
            if not hasattr(self, 'change_log'):
                self.change_log = []
            
            # Process each changed cell
            for row in range(topLeft.row(), bottomRight.row() + 1):
                for col in range(topLeft.column(), bottomRight.column() + 1):
                    # Track the change
                    self.modified_rows.add(row)
                    
                    # Get column name and values for logging
                    model = self.table.model()
                    index = model.index(row, col)
                    column_name = model.headerData(col, Qt.Horizontal, Qt.DisplayRole) 
                    current_value = model.data(index, Qt.DisplayRole)
                    
                    # Add to change log with timestamp
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.change_log.append({
                        'timestamp': timestamp,
                        'row': row,
                        'column': column_name,
                        'original_value': self.original_values.get((row, col), ""),
                        'new_value': current_value
                    })
                    
                    # Update UI safely
                    if hasattr(self, '_highlight_modified_row'):
                        self._highlight_modified_row(row)
                    
                    # Update status indicator if it exists
                    if hasattr(self, 'change_indicator'):
                        self.change_indicator.setText(f"{len(self.modified_rows)} rows modified")
                        self.change_indicator.setStyleSheet("color: red; font-weight: bold;")
                    else:
                        # Use status bar directly if no indicator
                        self.statusBar().showMessage(f"Cell ({row},{col}) modified")
                        
                    logging.debug(f"Processed change for row {row}, col {col}")
                    
        except Exception as e:
            logging.error(f"Error handling data change: {str(e)}")
            traceback.print_exc()
        finally:
        # Always reset the flag when done
            self._processing_data_change = False    


    def _highlight_modified_row(self, row):
        """Highlight a modified row in a QTableView"""
        try:
            logging.debug(f"Highlighting modified row {row}")
            
            # Get the actual source model (not proxy)
            source_model = self.model
            while hasattr(source_model, 'sourceModel') and source_model.sourceModel():
                source_model = source_model.sourceModel()
            
            # Add row to highlighted set in the source model
            if not hasattr(source_model, '_highlighted_rows'):
                source_model._highlighted_rows = set()
            
            # Map the view row to source row
            source_row = row
            proxy = self.table.model()
            if hasattr(proxy, 'mapRowToSource'):
                mapped_row = proxy.mapRowToSource(row)
                if mapped_row != -1:
                    source_row = mapped_row
                    logging.debug(f"Mapped view row {row} to source row {source_row}")
            
            # Add to the source model's highlighted rows set
            source_model._highlighted_rows.add(source_row)
            logging.debug(f"Added source row {source_row} to _highlighted_rows")
            
            # Force a refresh of the entire row in the view
            self.table.update(self.table.model().index(row, 0))
            self.table.update(self.table.model().index(row, self.table.model().columnCount()-1))
            self.table.viewport().update()
            
        except Exception as e:
            logging.error(f"Error in _highlight_modified_row: {e}")
            traceback.print_exc()


    def on_export_with_changes(self):
        """Handle export with changes action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data with Change Tracking", "", "JSON Files (*.json)"
        )
        
        if file_path:
            self.export_data_with_changes(file_path)    


    def on_item_changed(self, item):
        """Handle when a cell value is changed by the user"""
        try:
            row = item.row()
            col = item.column()
            current_value = item.text()
            
            # Get column name
            column_name = self.table.horizontalHeaderItem(col).text() if self.table.horizontalHeaderItem(col) else f"Column {col}"
            
            # Store original value if this is the first edit for this cell
            if (row, col) not in self.original_values:
                # Try to get the original value from the data model
                if hasattr(self.model, '_loaded_data'):
                    page = row // self.model.PAGE_SIZE
                    page_index = row % self.model.PAGE_SIZE
                    
                    if page in self.model._loaded_data and page_index < len(self.model._loaded_data[page]):
                        item_data = self.model._loaded_data[page][page_index]
                        # This depends on how your data is structured
                        # You may need to adjust this to get the correct original value
                        if hasattr(self.model, 'headerData'):
                            field_name = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
                            if field_name in item_data:
                                self.original_values[(row, col)] = str(item_data[field_name])
                                logging.error(f"on_item_changed called with {type(item).__name__}, but we have a QTableView")

                        else:
                            # Fallback if we can't determine the original value
                            self.original_values[(row, col)] = "Unknown"
                else:
                    # If we can't get from model, use empty string as original
                    self.original_values[(row, col)] = ""
            
            # Add row to the modified set
            self.modified_rows.add(row)
            
            # Add to change log
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.change_log.append({
                'timestamp': timestamp,
                'row': row,
                'column': column_name, 
                'original_value': self.original_values.get((row, col), ""),
                'new_value': current_value
            })
            
            # Highlight the modified row
            self.highlight_modified_row(row)
            
            # Update status bar to show number of modified rows
            self.statusBar().showMessage(f"{len(self.modified_rows)} rows modified")
            self.change_indicator.setText(f"{len(self.modified_rows)} rows modified")

            self.change_indicator.setStyleSheet("color: red; font-weight: bold;")
            
        except Exception as e:
            logging.error(f"Error tracking item change: {e}")
            traceback.print_exc()    
        

    def debug_force_first_selection(self):
        """Force la sélection du premier élément pour déboguer"""
        logging.debug("Tentative de sélection forcée pour déboguer")
        self.force_selection(0)
        
        # Vérifier également si on a des données BLAST
        if hasattr(self, 'model') and self.model:
            page = 0
            if page in self.model._loaded_data and len(self.model._loaded_data[page]) > 0:
                item = self.model._loaded_data[page][0]
                if 'display' in item and 'blast_hits' in item['display']:
                    hits = item['display']['blast_hits']
                    logging.debug(f"Premier élément contient {len(hits)} blast_hits")
                    
                    # Forcer la mise à jour du tab BLAST
                    QTimer.singleShot(100, lambda: self.update_blast_tab(hits))    


    def export_data_with_changes(self, file_path):
        """Export data including change tracking information"""
        try:
            # First, prepare the main data
            export_data = []
            
            # Loop through all rows
            for row in range(self.table.model().rowCount()):
                row_data = {}
                
                # Add column data
                for col in range(self.table.model().columnCount()):
                    header = self.table.horizontalHeaderItem(col).text()
                    index = self.table.model().index(row, col)
                    value = self.table.model().data(index, Qt.DisplayRole)
                    row_data[header] = value
                
                # Mark row as modified if it's in our tracking set
                row_data['_modified'] = row in self.modified_rows
                
                # Add to export data
                export_data.append(row_data)
            
            # Create the export object
            full_export = {
                'data': export_data,
                'change_log': self.change_log,
                'export_date': datetime.datetime.now().isoformat(),
                'modified_rows_count': len(self.modified_rows)
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(full_export, f, indent=2, ensure_ascii=False)
                
            self.statusBar().showMessage(f"Data exported with change tracking to {file_path}")
            return True
                
        except Exception as e:
            logging.error(f"Error exporting data with changes: {e}")
            traceback.print_exc()
            self.statusBar().showMessage(f"Error exporting data: {str(e)}")
            return False                

    """     def highlight_modified_row(self, row):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    # Set yellow background to indicate modified
                    item.setBackground(QColor(255, 255, 200))  # Light yellow    """             


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


    def complete_filter_setup(self):
        """Connect filter to the table model after both exist"""
        from model.data_model import CustomFilterProxyModel
        
        # Create ONE proxy model and store it as instance variable
        self.proxy_model = CustomFilterProxyModel(self,identifier="table_filter")
        self.proxy_model.setSourceModel(self.model)
        
        # Set proxy model on table
        self.table.setModel(self.proxy_model)

        self.filter_edit.textChanged.connect(self.filter_manager.on_filter_text_changed)
        self.proxy_model.filterProgressChanged.connect(self.filter_manager.update_filter_status)


        print(f"TABLE MODEL IS: {type(self.table.model()).__name__}")
        print(f"PROXY MODEL IS: {type(self.proxy_model).__name__}")
        print(f"SOURCE MODEL IS: {type(self.model).__name__}")
        
        # Add a clear button to the filter box
        self.filter_edit.setClearButtonEnabled(True)
        
        # Add a delayed update to ensure UI refreshes properly
        def delayed_update():
            # Force complete refresh of the view
            self.table.viewport().update()
            
            # Force layout update
            self.table.updateGeometry()
            
            current_filter = self.filter_edit.text()
            if current_filter:
                logging.debug(f"Applying filter: '{current_filter}' - refreshing view")
                # Verify status on first few rows
                self.filter_manager.check_filter_status(current_filter)
            
            # Scroll to top to make filtered results visible
            self.table.scrollToTop()
        
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(delayed_update)
        
            
    def filter_changed(self,text):
        # Apply filter immediately to model
        self.proxy_model.setFilterText(text)
        TableDebugger.debug_filter_counts(text)
        
        # Reset the model completely to force update
        self.proxy_model.beginResetModel()
        self.proxy_model.endResetModel()
            
            # Force update visible rows
        self.filter_manager.force_complete_view_update()
            
            # Show "Filtering..." in status bar immediately
        if text:
                self.status_bar.showMessage(f"Filtering for '{text}'...")
        else:
                self.status_bar.showMessage("Filter cleared")
                
        # Connect filter signal (disconnect first to avoid duplicates)
        self.filter_edit.textChanged.disconnect()
        self.filter_edit.textChanged.connect(self.filter_changed)
        
        # Add keyboard shortcut to force refresh filter (F3)
        self.refresh_filter_shortcut = QShortcut(QKeySequence("F3"), self)
        self.refresh_filter_shortcut.activated.connect(lambda: self.filter_manager.force_refresh_filter())     
            
    def force_selection_with_retry(self, row=0, retry_count=0, max_retries=10):
        """Force selection with retry mechanism that waits for data to be loaded"""
        try:
            if retry_count >= max_retries:
                logging.debug(f"Abandon après {retry_count} tentatives")
                return
                
            # Vérifier si le modèle existe et a des données
            if not self.table.model() or self.table.model().rowCount() == 0:
                logging.debug("Modèle pas prêt, nouvelle tentative dans 1 seconde...")
                QTimer.singleShot(1000, lambda: self.force_selection_with_retry(row, retry_count + 1))
                return
                
            # Vérifier si la page nécessaire est chargée
            page = row // VirtualTableModel.PAGE_SIZE
            if not hasattr(self.model, '_loaded_data') or page not in self.model._loaded_data:
                logging.debug(f"Page {page} non chargée, chargement en cours...")
                # Charger la page explicitement et réessayer plus tard
                try:
                    self.model.current_page = page
                    # Appel à _load_page modifié
                    if hasattr(self.model, '_load_page'):
                        self.model._load_page(page)
                    QTimer.singleShot(1500, lambda: self.force_selection_with_retry(row, retry_count + 1))
                except Exception as e:
                    logging.error(f"Erreur lors du chargement de la page: {e}")
                    traceback.print_exc()
                    # Réessayer quand même
                    QTimer.singleShot(3000, lambda: self.force_selection_with_retry(row, retry_count + 1))
                return
                
            # La page est chargée, on peut sélectionner
            logging.debug(f"Page {page} chargée, sélection de la ligne {row}")
            
            # Sélectionner la ligne avec les bons paramètres
            index = self.table.model().index(row, 0)
            self.table.selectionModel().select(
                index, 
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            self.table.setCurrentIndex(index)
            
            # Assurer la visibilité de la ligne sélectionnée
            self.table.scrollTo(index)
            
            # Appeler le gestionnaire manuellement
            self.handle_row_selection(row)
            
            return True  # Succès
        except Exception as e:
            logging.error(f"Erreur pendant la sélection: {e}")
            traceback.print_exc()
            # Réessayer
            QTimer.singleShot(2000, lambda: self.force_selection_with_retry(row, retry_count + 1))
            return False

    def create_main_table(self):
        """Create and configure main table with virtual model"""
        self.table = QTableView()
        self.table_group_box = QGroupBox("")

        # Set up virtual model
        self.model = VirtualTableModel(self.parsed_results, self.go_definitions,self)
        #self.table.setModel(self.model)

        from model.data_model import WidgetDelegate
        self.widget_delegate = WidgetDelegate()
        self.table.setItemDelegate(self.widget_delegate)

        from model.data_model import CustomFilterProxyModel

        proxy_model= CustomFilterProxyModel(self,identifier="main_proxy")
        proxy_model.setSourceModel(self.model)    


        # Configure table
        self.table.setObjectName("MainResultsTable")
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        #set stylesheet for headers
        header.setStyleSheet(DataTableManager.STYLES["header"])

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
        layout.addLayout(self.filter_layout)

        layout.addWidget(self.table)

        self.create_pagination_controls(layout)
        self.table_group_box.setLayout(layout)

        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)

        self.table.setStyleSheet("""
        QTableView {
            alternate-background-color: #F0F0F0;
            background-color: white;
            selection-background-color: #0078D7;
            selection-color: white;
        }
        
        /* This is the critical part that makes highlights visible */
        QTableView::item { 
            border: none;
            background-color: transparent;
        }
        
        /* This ensures selected cells don't hide your highlights */
        QTableView::item:selected {
            color: white;
            background-color: rgba(0, 120, 215, 180);
        }
        """)
        
        # Ensure background colors from the model are shown
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)

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

    
    
    def create_filter_bar(self):
            self.filter_layout = QHBoxLayout()

            filter_edit = QLineEdit()
            filter_edit.setPlaceholderText("Filtrer toutes les colonnes...")
            self.filter_layout.addWidget(filter_edit)


            """ self.open_dialog_button = QPushButton("Filter")
            self.open_dialog_button.setIcon(QIcon("./assets/dialog-icon.png"))
            self.open_dialog_button.clicked.connect(self.open_dialog)
            self.filter_layout.addWidget(self.open_dialog_button) """

            # Style
            self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D3D3D3;
                border-radius: 3px;
                padding: 3px;
            }
            """)


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
            help_menu.addAction(about_action)

            #to-complete
            # other menu 
            tools_menu = menu_bar.addMenu("Tools")
            view_menu = menu_bar.addMenu("View")

            return menu_bar  


    def update_time(self):
        """Update the clock in the status bar."""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.setText(f"Time: {current_time}")


    def create_status_bar(self):
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)

            self.change_indicator = QLabel()
            
            # Create icon pixmap
            icon = QIcon("./assets/branch.png")  # Replace with your icon path
            if not icon.isNull():
                # Save the pixmap for later use
                self.edit_icon_pixmap = icon.pixmap(16, 16)
                
                # Save icon to temporary file for HTML embedding
                temp_icon_path = "./assets/temp_icon.png"
                self.edit_icon_pixmap.save(temp_icon_path, "PNG")
                
                # Set HTML text with embedded image
                self.change_indicator.setText(
                    f'<img src="{temp_icon_path}" width="16" height="16" style="vertical-align: middle"> No changes'
                )
            else:
                # Fallback if icon not found
                self.change_indicator.setText("✏️ No changes")
            
            # Add to status bar
            self.status_bar.addWidget(self.change_indicator)

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
            self.progress_bar.hide()


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


    def create_tabs(self, parsed_results):
        """tabs for hits, graphs, metadata .."""
        #self.tabs.addTab(self.create_tables_tab(parsed_results), "Hits")
        self.tabs.addTab(self.create_Iprscan_tab(parsed_results), "Domains")
        self.tabs.addTab(self.create_details_tab(), "Details")
        self.tabs.addTab(self.create_GO_tab(), "GO")
        self.tabs.addTab(self.create_graphs_tab(), "Donut")
        self.tabs.addTab(self.create_chart_tab(), "Chart")
        self.tabs.addTab(self.create_MetaD_tab(), "Metadata")
        # Set tab styling
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                color: #333333;
                font : Lato;
                font-weight: bold;
                font-size: 12px ;
            }
        """)

    def update_blast_tab(self, blast_hits):
        """
        Update the BLAST hits tab with sequence alignment details from the selected item.
        
        Args:
            blast_hits: List of BLAST hit dictionaries containing alignment information
        """
        # If no blast hits tab exists yet, create one
        if "BLAST" not in self.detail_tabs:
            blast_tab = self.create_blast_tab(blast_hits)
            self.tabs.addTab(blast_tab, "BLAST")
            self.detail_tabs["BLAST"] = blast_tab
            tab_index = self.tabs.count() - 1
        else:
            # Tab already exists, get its index and update it
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "BLAST":
                    tab_index = i
                    break
        
        # Define column headers for BLAST hits table
        hits_table_column_headers = [
            "Hit ID", "Definition", "Accession", "Identity (%)", "Alignment Length", "E-value", "Bit-score",
            "Query Start", "Query End", "Subject Start", "Subject End", "HSP Bit-score"
        ]
        
        # Get the table widget from the tab
        if "BLAST" in self.detail_tabs and hasattr(self.detail_tabs["BLAST"], "findChild"):
            # Find the table widget within the tab
            table = self.detail_tabs["BLAST"].findChild(QTableWidget)
            if not table:
                # Create a new table if not found
                table = QTableWidget()
                table.setColumnCount(len(hits_table_column_headers))
                table.setHorizontalHeaderLabels(hits_table_column_headers)
                self.detail_tabs["BLAST"].layout().addWidget(table)
        else:
            # Create a new table if the tab doesn't exist or doesn't have findChild
            table = QTableWidget()
            table.setColumnCount(len(hits_table_column_headers))
            table.setHorizontalHeaderLabels(hits_table_column_headers)
        
        # Set row count based on number of hits
        total_hits = len(blast_hits)
        table.setRowCount(total_hits)
        logging.debug(f"Updating BLAST tab with {total_hits} hits")
        
        # Populate the table row by row
        for row_idx, hit in enumerate(blast_hits):
            # Extract data with safe defaults
            query_start = hit.get("query_positions", {}).get("start", "N/A")
            query_end = hit.get("query_positions", {}).get("end", "N/A")
            subject_start = hit.get("subject_positions", {}).get("start", "N/A")
            subject_end = hit.get("subject_positions", {}).get("end", "N/A")
            hit_accession = hit.get("accession", "N/A")
            hit_definition = hit.get("hit_def", "N/A")
            
            # Get first HSP bit score or default
            hsps = hit.get("hsps", [{}])
            hsp_bit_score = hsps[0].get("bit_score", "N/A") if hsps else "N/A"
            
            # Calculate identity percentage with safe conversion
            alignment_length = hit.get("alignment_length", 1)
            if alignment_length == 0:
                alignment_length = 1  # Prevent division by zero
                
            percent_identity = hit.get("percent_identity", 0)
            try:
                identity = (float(percent_identity) / float(alignment_length)) * 100
                identity = min(100, max(0, identity))  # Ensure it's between 0-100
            except (ValueError, TypeError):
                identity = 0
            
            # Row data, matching the number of columns
            row_data = [
                hit.get("hit_id", ""),       # Hit ID
                hit_definition,              # Definition
                hit_accession,               # Accession
                identity,                    # Identity percentage
                alignment_length,            # Alignment length
                hit.get("e_value", "N/A"),   # E-value
                hit.get("bit_score", "N/A"), # Bit-score
                query_start,                 # Query Start
                query_end,                   # Query End
                subject_start,               # Subject Start
                subject_end,                 # Subject End
                hsp_bit_score                # HSP bit score
            ]
            
            # Add data to the table
            for col_idx, value in enumerate(row_data):
                if col_idx == 3:  # Identity column with progress bar
                    progress = QProgressBar()
                    try:
                        progress.setValue(int(identity))
                    except (ValueError, TypeError):
                        progress.setValue(0)
                        
                    progress.setAlignment(Qt.AlignCenter)
                    
                    # Color coding based on identity percentage
                    if int(identity) > 90:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #8FE388;}")
                    elif int(identity) < 70:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #E3AE88;}")
                    else:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #88BCE3;}")
                        
                    table.setCellWidget(row_idx, col_idx, progress)
                else:
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)
        
        # Set column widths for better readability
        column_widths = {
            0: 120,  # Hit ID
            1: 200,  # Definition
            2: 120,  # Accession
            3: 100,  # Identity
            4: 120,  # Alignment length
            5: 100,  # E-value
            6: 100,  # Bit-score
            7: 80,   # Query Start
            8: 80,   # Query End
            9: 80,   # Subject Start
            10: 80,  # Subject End
            11: 100  # HSP bit score
        }
        
        for col, width in column_widths.items():
            table.setColumnWidth(col, width)
        
        # Show the BLAST tab
        self.tabs.setCurrentIndex(tab_index)
        
        # Add summary information at the bottom if many hits
        if total_hits > 10:
            summary_label = QLabel(f"Showing {total_hits} BLAST hits. Top hits are most significant.")
            summary_label.setStyleSheet("color: #555; font-style: italic;")
            if self.detail_tabs["BLAST"].layout().count() == 1:  # Only the table exists
                self.detail_tabs["BLAST"].layout().addWidget(summary_label)    

    def create_details_tab(self):
        """Create a details tab with a text area for displaying annotation details"""
        self.description_widget = QTextEdit()
        self.description_widget.setReadOnly(True)
        self.description_widget.setPlaceholderText("Select a cell to view annotation details...")
        
        tab_details = QWidget()
        tab_details_layout = QVBoxLayout()
        tab_details_layout.addWidget(self.description_widget)
        tab_details.setLayout(tab_details_layout)
        
        return tab_details

    def create_MetaD_tab(self):
        """Create a metadata tab for displaying dataset metadata"""
        description_widget = QLabel("Metadata will be displayed here...")
        description_widget.setAlignment(Qt.AlignCenter)
        
        tab_metadata = QWidget()
        tab_metadata_layout = QVBoxLayout()
        tab_metadata_layout.addWidget(description_widget)
        tab_metadata.setLayout(tab_metadata_layout)
        
        return tab_metadata

    def create_graphs_tab(self):
        """Create a donut chart visualization tab"""
        donut_chart_widget = Widget() 
        donut_chart_widget.setMinimumSize(600, 600) 
        donut_chart_widget.setMaximumSize(900, 600) 

        # Create a scroll area for the chart
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

    def create_chart_tab(self):
        """Create a pie chart visualization of query distribution"""
        chart = QChart() 
        series = QPieSeries()

        series.append("With Blast Hits", 60)
        series.append("With GO Mapping", 20)
        series.append("Manually Annotated", 10)
        series.append("Blasted Without hits", 10)

        chart.addSeries(series)
        chart.setTitle("Query distribution")
        
        # Set chart styling
        chart.setTitleBrush(QColor("#4F518C")) 
        chart.setTitleFont(QFont("Roboto", 14, QFont.Bold)) 

        # Set slice colors
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
        """Create a table showing hit results"""
        self.additional_table = QTableWidget()
        DataTableManager.style_AdditionalTable_headers(self.additional_table)
        self.additional_table.setColumnCount(12)
        DataTableManager.populate_additional_table(self.additional_table, parsed_results)

        tab_tables = QWidget()
        tab_tables_layout = QVBoxLayout()
        tab_tables_layout.addWidget(self.additional_table)
        tab_tables.setLayout(tab_tables_layout)

        return tab_tables

    def create_Iprscan_tab(self, parsed_results):
        """Create IPRscan Table tab"""
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
        """Create a Gene Ontology terms table tab"""
        obo_file_path = "./ontologies/go-basic.obo"  # TO-DO: move to config.json
        
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
        logging.debug(f"Selection changed: {len(indexes)} indices sélectionnés")

        if indexes:
            row = indexes[0].row()
            column = indexes[0].column()
            logging.debug(f"Sélection: ligne={row}, colonne={column}")
            
            # Vérifier la correspondance entre modèles
            proxy_index = indexes[0]
            if hasattr(self.table.model(), 'mapToSource'):
                source_index = self.table.model().mapToSource(proxy_index)
                logging.debug(f"Mappage: proxy({row},{column}) -> source({source_index.row()},{source_index.column()})")
            
            # Force update with additional logging
            try:
                # This will force debugging info for every selection
                logging.debug(f"Forcing update for row {row}")
                self.handle_row_selection(row)
            except Exception as e:
                logging.error(f"Error in selection changed: {e}")
                traceback.print_exc()
        else:
            logging.debug("Aucune ligne sélectionnée")

    def handle_row_selection(self, row):
        try:
            # Obtain the proxy index
            proxy_index = self.table.model().index(row, 0)
            
            # Map to the source model - FIX MAPPING ISSUE
            if hasattr(self.table.model(), 'mapToSource'):
                source_index = self.table.model().mapToSource(proxy_index)
                source_row = source_index.row()
            else:
                source_row = row
            
            # Record this critical value
            logging.debug(f"IMPORTANT - source_row = {source_row}")
            
            # Calculate page and index - ENSURE CORRECT VALUES
            page_size = VirtualTableModel.PAGE_SIZE
            page = source_row // page_size
            page_index = source_row % page_size
            
            logging.debug(f"Selected row {row} maps to source_row={source_row} (page={page}, index={page_index})")
            
            # Ensure the page is loaded - FIX POTENTIAL RACE CONDITION
            if (hasattr(self.model, '_loaded_data') and 
                page not in self.model._loaded_data):
                logging.debug(f"Page {page} not loaded, loading now...")
                self.model._load_page(page)
                # Give a small delay to ensure loading completes
                QTimer.singleShot(50, lambda: self._continue_row_selection(source_row, page, page_index))
                return
            
            # Continue with the loaded page
            self._continue_row_selection(source_row, page, page_index)
                
        except Exception as e:
            logging.error(f"Error handling row selection: {str(e)}")
            traceback.print_exc()

    def _continue_row_selection(self, source_row, page, page_index):
        """Continue row selection after ensuring page is loaded"""
        try:
            # Extra check to ensure page is loaded
            if not hasattr(self.model, '_loaded_data') or page not in self.model._loaded_data:
                logging.error(f"Page {page} still not loaded after waiting!")
                return
                
            # Get the item data
            if page_index < len(self.model._loaded_data[page]):
                item_data = self.model._loaded_data[page][page_index]
                logging.debug(f"Item data found for row {source_row}, keys: {list(item_data.keys())}")
                
                # EXPLICITLY check for 'blast_hits' in the data 
                if 'blast_hits' in item_data:
                    logging.debug(f"Found {len(item_data['blast_hits'])} BLAST hits - updating tab...")
                    # Update tabs - IMPORTANT: use refresh_blast_tab
                    self.update_detail_tabs(item_data)
                else:
                    logging.debug(f"No blast_hits found in item_data!")
                    # Clear the BLAST tab if it exists
                    self.clear_blast_tab()
            else:
                logging.debug(f"Index {page_index} out of bounds for page {page}")
        except Exception as e:
            logging.error(f"Error in _continue_row_selection: {str(e)}")
            traceback.print_exc()

    def clear_blast_tab(self):
        """Clear the BLAST tab if it exists"""
        if "BLAST" in self.detail_tabs:
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "BLAST":
                    self.tabs.removeTab(i)
                    del self.detail_tabs["BLAST"]
                    logging.debug("BLAST tab removed")
                    break

    def force_selection(self, row=0):
        """Force selection of the specified row with proper error handling"""
        try:
            if self.table.model() and self.table.model().rowCount() > 0:
                # Obtenir le vrai nombre de lignes
                available_rows = self.table.model().rowCount()
                if row < available_rows:
                    logging.debug(f"Forcing selection of row {row}")
                    index = self.table.model().index(row, 0)
                    
                    # Configurer la sélection
                    self.table.setSelectionBehavior(QTableView.SelectRows)
                    self.table.setSelectionMode(QTableView.SingleSelection)
                    
                    # Sélectionner la ligne
                    self.table.selectionModel().select(
                        index, 
                        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
                    )
                    self.table.setCurrentIndex(index)
                    
                    # Appeler directement le gestionnaire
                    self.handle_row_selection(row)
                    
                    # Scrroller pour voir la ligne sélectionnée
                    self.table.scrollTo(index)
                else:
                    logging.debug(f"Cannot select row {row}: model has only {available_rows} rows")
            else:
                logging.debug("Cannot force selection: no model or empty model")
        except Exception as e:
            logging.error(f"Error forcing selection: {str(e)}")
            traceback.print_exc()        

    def update_detail_tabs(self, item_data):
        """Update detail tabs with selected item data"""
        try:
            # Log item structure for debugging
            logging.debug(f"Updating tabs with item keys: {list(item_data.keys())}")
            
            # Update BLAST tab
            if 'blast_hits' in item_data:
                logging.debug(f"Found blast_hits: {len(item_data['blast_hits'])} hits")
                self.refresh_blast_tab(item_data['blast_hits'])
            else:
                logging.debug("No blast_hits found in this item")

            # Update InterPro tab (commented out in original)
            if 'InterproScan_annotation' in item_data:
                logging.debug(f"Found InterproScan data: {len(item_data['InterproScan_annotation'])}")
                # Uncomment this when ready to implement
                # self.update_interpro_tab(item_data['InterproScan_annotation'])

            # Update Details text tab
            if hasattr(self, 'description_widget'):
                # Format details nicely
                details = "<h3>Selected Item Details</h3><hr/>"
                
                # Access top-level keys directly instead of using 'display'
                for key, value in item_data.items():
                    if key not in ['blast_hits', 'InterproScan_annotation', 'eggNOG_annotations']:
                        details += f"<p><b>{key}:</b> {value}</p>"
                        
                # Add eggNOG details separately if they exist
                if 'eggNOG_annotations' in item_data and item_data['eggNOG_annotations']:
                    details += "<h4>eggNOG Annotations</h4>"
                    for annotation in item_data['eggNOG_annotations']:
                        if isinstance(annotation, dict):
                            for key, value in annotation.items():
                                details += f"<p><b>{key}:</b> {value}</p>"
                        
                self.description_widget.setHtml(details)
        except Exception as e:
            logging.error(f"Error updating detail tabs: {str(e)}")
            traceback.print_exc()

    def on_data_loaded(self):
        """Handle completed data loading"""
        self.progress_bar.hide()
        self.status_bar.showMessage("Data loaded successfully")
        self.update_row_count()

        # Ajouter plus de logs
        if self.table.model():
            logging.debug(f"Modèle existe avec {self.table.model().rowCount()} lignes")
        else:
            logging.debug("Modèle n'existe pas!")

        QTimer.singleShot(100, lambda: self.force_selection(0))


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

    """******************************Filers*********************************************************************"""
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

    """********** TABS ***************************************************************************"""

    def create_blast_tab(self, data):
        """Create Blast results tab"""
        # Create the table with proper headers
        table = QTableWidget()
        table.setColumnCount(len(DataTableManager.BLAST_HEADERS))
        table.setHorizontalHeaderLabels(DataTableManager.BLAST_HEADERS)
        logging.debug(f"BLAST table column count after creation: {table.columnCount()}")

        self.populate_blast_table(table, data)
        
        # Create and return a tab with the table
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(table)
        tab.setLayout(layout)
        return tab
    
    def refresh_blast_tab(self, blast_hits):
        """Completely recreate the BLAST tab for the selected item"""
        # First, check if the BLAST tab exists and remove it
        if "BLAST" in self.detail_tabs:
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "BLAST":
                    self.tabs.removeTab(i)
                    del self.detail_tabs["BLAST"]
                    break
        
        # Now create a new BLAST tab
        blast_tab = self.create_blast_tab(blast_hits)
        self.tabs.addTab(blast_tab, "BLAST")
        self.detail_tabs["BLAST"] = blast_tab
        
        # Show the BLAST tab
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "BLAST":
                self.tabs.setCurrentIndex(i)
                break
    
    def populate_blast_table(self, table, blast_hits):
        """
        Populate a table with BLAST hit data
        
        Args:
            table: QTableWidget to populate
            blast_hits: List of BLAST hit dictionaries
        """
        # Set row count based on number of hits
        total_hits = len(blast_hits)
        table.setRowCount(total_hits)
        logging.debug(f"Populating BLAST table with {total_hits} hits")
           # DEBUG: Add this to check the first hit's structure
        if total_hits > 0:
            logging.debug(f"First BLAST hit keys: {list(blast_hits[0].keys())}")
            logging.debug(f"First BLAST hit sample data: {blast_hits[0]}")


        # Populate the table row by row
        for row_idx, hit in enumerate(blast_hits):
            # Extract data with safe defaults
            query_start = hit.get("query_positions", {}).get("start", "N/A")
            query_end = hit.get("query_positions", {}).get("end", "N/A")
            subject_start = hit.get("subject_positions", {}).get("start", "N/A")
            subject_end = hit.get("subject_positions", {}).get("end", "N/A")
            hit_accession = hit.get("accession", "N/A")
            hit_definition = hit.get("hit_def", "N/A")
            
            # Get first HSP bit score or default
            hsps = hit.get("hsps", [{}])
            hsp_bit_score = hsps[0].get("bit_score", "N/A") if hsps else "N/A"
            
            # Calculate identity percentage with safe conversion
            alignment_length = hit.get("alignment_length", 1)
            if alignment_length == 0:
                alignment_length = 1  # Prevent division by zero
                
            percent_identity = hit.get("percent_identity", 0)
            try:
                identity = (float(percent_identity) / float(alignment_length)) * 100
                identity = min(100, max(0, identity))  # Ensure it's between 0-100
            except (ValueError, TypeError):
                identity = 0
            
            # Row data, matching the number of columns
            row_data = [
                hit.get("hit_id", ""),       # Hit ID
                hit_definition,              # Definition
                hit_accession,               # Accession
                identity,                    # Identity percentage
                alignment_length,            # Alignment length
                hit.get("e_value", "N/A"),   # E-value
                hit.get("bit_score", "N/A"), # Bit-score
                query_start,                 # Query Start
                query_end,                   # Query End
                subject_start,               # Subject Start
                subject_end,                 # Subject End
                hsp_bit_score                # HSP bit score
            ]
            
            # Add data to the table
            for col_idx, value in enumerate(row_data):
                if col_idx == 3:  # Identity column with progress bar
                    progress = QProgressBar()
                    try:
                        progress.setValue(int(identity))
                    except (ValueError, TypeError):
                        progress.setValue(0)
                        
                    progress.setAlignment(Qt.AlignCenter)
                    
                    # Color coding based on identity percentage
                    if int(identity) > 90:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #8FE388;}")
                    elif int(identity) < 70:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #E3AE88;}")
                    else:
                        progress.setStyleSheet("QProgressBar::chunk {background-color: #88BCE3;}")
                        
                    table.setCellWidget(row_idx, col_idx, progress)
                else:
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)
        
        # Set column widths for better readability
        column_widths = {
            0: 120,  # Hit ID
            1: 200,  # Definition
            2: 120,  # Accession
            3: 100,  # Identity
            4: 120,  # Alignment length
            5: 100,  # E-value
            6: 100,  # Bit-score
            7: 80,   # Query Start
            8: 80,   # Query End
            9: 80,   # Subject Start
            10: 80,  # Subject End
            11: 100  # HSP bit score
        }
        
        for col, width in column_widths.items():
            table.setColumnWidth(col, width)
        
        # Add debug logging to check headers
        logging.debug(f"BLAST table column count after populate: {table.columnCount()}")
        headers = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else "None" for i in range(table.columnCount())]
        logging.debug(f"BLAST table headers: {headers}")

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
            return None
        
    """*************************************************************************************************"""    

    def add_debug_panel(self):
        """Add debug panel with tools to diagnose BLAST tab updates"""
        debug_dock = QDockWidget("BLAST Debug Panel", self)
        debug_widget = QWidget()
        debug_layout = QVBoxLayout(debug_widget)
        
        # Row selection tester
        row_selection_group = QGroupBox("Test Row Selection")
        row_layout = QHBoxLayout()
        row_selection_group.setLayout(row_layout)
        
        row_input = QSpinBox()
        row_input.setMinimum(0)
        row_input.setMaximum(100)
        row_layout.addWidget(QLabel("Row:"))
        row_layout.addWidget(row_input)
        
        select_button = QPushButton("Select & Debug")
        select_button.clicked.connect(lambda: self.debug_row_selection(row_input.value()))
        row_layout.addWidget(select_button)
        
        debug_layout.addWidget(row_selection_group)
        
        # Direct BLAST update
        blast_group = QGroupBox("Force BLAST Update")
        blast_layout = QHBoxLayout()
        blast_group.setLayout(blast_layout)
        
        row_blast = QSpinBox()
        row_blast.setMinimum(0)
        row_blast.setMaximum(100)
        blast_layout.addWidget(QLabel("Row:"))
        blast_layout.addWidget(row_blast)
        
        update_blast_button = QPushButton("Update BLAST")
        update_blast_button.clicked.connect(lambda: self.debug_blast_update(row_blast.value()))
        blast_layout.addWidget(update_blast_button)
        
        debug_layout.addWidget(blast_group)
        
        # Memory inspection
        memory_button = QPushButton("Check Memory Management")
        memory_button.clicked.connect(self.debug_memory_state)
        debug_layout.addWidget(memory_button)
        
        # Add current BLAST tab info
        blast_info_button = QPushButton("Show Current BLAST Info")
        blast_info_button.clicked.connect(self.debug_show_blast_info)
        debug_layout.addWidget(blast_info_button)
        
        debug_dock.setWidget(debug_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, debug_dock)
    
    
    def on_scroll_change(self, value):
        """Handle scroll events for dynamic loading"""
        # Use QTimer to delay widget creation which prevents UI freezing
        QTimer.singleShot(10, self.create_visible_widgets)
        
        # Check if we're near the end of our data
        model = self.table.model()
        if model:
            scrollbar = self.table.verticalScrollBar()
            if scrollbar.value() > scrollbar.maximum() * 0.8:
                self.request_more_data.emit(model.rowCount())

    def debug_row_selection(self, row):
        """Debug the row selection process"""
        logging.debug(f"===== DEBUG ROW SELECTION: {row} =====")
        
        # First select the row
        self.force_selection(row)
        
        # Now trace through the process
        if not hasattr(self, 'model') or not self.model:
            logging.debug("No model available!")
            return
            
        # Calculate page and index
        page_size = VirtualTableModel.PAGE_SIZE
        page = row // page_size
        page_index = row % page_size
        
        # Check if page is loaded
        logging.debug(f"Checking if page {page} is loaded...")
        if hasattr(self.model, '_loaded_data'):
            if page in self.model._loaded_data:
                logging.debug(f"Page {page} is loaded with {len(self.model._loaded_data[page])} items")
            else:
                logging.debug(f"Page {page} is NOT loaded!")
                return
        else:
            logging.debug("Model has no _loaded_data attribute!")
            return
            
        # Get item data
        if page_index < len(self.model._loaded_data[page]):
            item_data = self.model._loaded_data[page][page_index]
            logging.debug(f"Item data found with keys: {list(item_data.keys())}")
            
            # Check BLAST data
            if 'blast_hits' in item_data:
                blast_hits = item_data['blast_hits']
                logging.debug(f"Found {len(blast_hits)} blast hits")
                
                # Debug the update process
                logging.debug("Forcing BLAST tab update...")
                self.refresh_blast_tab(blast_hits)
                logging.debug("BLAST tab update completed")
            else:
                logging.debug("No 'blast_hits' found in item data!")
        else:
            logging.debug(f"Index {page_index} is out of bounds for page {page}!")

    def debug_blast_update(self, row):
        """Directly update the BLAST tab for a specific row"""
        logging.debug(f"===== DEBUG FORCE BLAST UPDATE: {row} =====")
        
        # Calculate page and index
        page_size = VirtualTableModel.PAGE_SIZE
        page = row // page_size
        page_index = row % page_size
        
        # Force page load if needed
        if hasattr(self.model, '_load_page') and (not hasattr(self.model, '_loaded_data') or page not in self.model._loaded_data):
            logging.debug(f"Loading page {page}...")
            self.model._load_page(page)
        
        # Get data and update
        if hasattr(self.model, '_loaded_data') and page in self.model._loaded_data:
            if page_index < len(self.model._loaded_data[page]):
                item_data = self.model._loaded_data[page][page_index]
                logging.debug(f"Found item data with keys: {list(item_data.keys())}")
                
                if 'blast_hits' in item_data:
                    blast_hits = item_data['blast_hits']
                    logging.debug(f"Found {len(blast_hits)} blast hits, forcing refresh...")
                    
                    # Force refresh to a new BLAST tab
                    self.refresh_blast_tab(blast_hits)
                    logging.debug("BLAST tab refresh completed")
                else:
                    logging.debug("No blast_hits found in item_data")
            else:
                logging.debug(f"Index {page_index} out of bounds for page {page}")
        else:
            logging.debug(f"Page {page} not available in model data")

    def debug_memory_state(self):
            """Check memory management and model state"""
            if not hasattr(self, 'model'):
                logging.debug("No model available")
                return
                
            logging.debug("===== MEMORY STATE DEBUG =====")
            
            # Check loaded pages
            if hasattr(self.model, '_loaded_data'):
                loaded_pages = list(self.model._loaded_data.keys())
                logging.debug(f"Loaded pages: {loaded_pages}")
                
                # Check current page
                current_page = getattr(self.model, 'current_page', None)
                logging.debug(f"Current page: {current_page}")
                
                # Check if current page is loaded
                if current_page in self.model._loaded_data:
                    logging.debug(f"Current page has {len(self.model._loaded_data[current_page])} items")
                    
                    # Check first item
                    if len(self.model._loaded_data[current_page]) > 0:
                        first_item = self.model._loaded_data[current_page][0]
                        logging.debug(f"First item keys: {list(first_item.keys())}")
                        
                        if 'blast_hits' in first_item:
                            logging.debug(f"First item has {len(first_item['blast_hits'])} blast hits")
                        else:
                            logging.debug("First item has NO blast hits")
                else:
                    logging.debug("Current page is NOT loaded")
            else:
                logging.debug("Model has no _loaded_data attribute")

    def debug_show_blast_info(self):
        """Show information about the current BLAST tab"""
        logging.debug("===== BLAST TAB DEBUG =====")
        
        # Check if BLAST tab exists
        if "BLAST" in self.detail_tabs:
            logging.debug("BLAST tab exists")
            
            # Find the tab
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "BLAST":
                    logging.debug(f"BLAST tab found at index {i}")
                    
                    # Check for the table
                    tab_widget = self.detail_tabs["BLAST"]
                    table = tab_widget.findChild(QTableWidget)
                    
                    if table:
                        logging.debug(f"BLAST table found with {table.rowCount()} rows")
                        
                        # Check table content
                        for row in range(min(3, table.rowCount())):
                            hit_id = table.item(row, 0).text() if table.item(row, 0) else "N/A"
                            logging.debug(f"Row {row}: Hit ID = {hit_id}")
                    else:
                        logging.debug("No QTableWidget found in BLAST tab")
                    break
        else:
            logging.debug("No BLAST tab exists")

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

    def create_pagination_controls(self, parent_layout=None):
        """Create pagination controls for navigating through large datasets with centered alignment"""
        try:
            # Clean up old pagination widget if it exists
            if hasattr(self, 'pagination_widget') and self.pagination_widget is not None:
                try:
                    if self.pagination_widget.parent():
                        self.pagination_widget.parent().layout().removeWidget(self.pagination_widget)
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
                    margin-top: 4px;
                }
                QPushButton {
                    min-width: 60px;
                    padding: 4px;
                }
            """)
            
            # Create inner layout for pagination controls
            pagination_layout = QHBoxLayout(self.pagination_widget)
            pagination_layout.setContentsMargins(4, 4, 4, 4)
            pagination_layout.setSpacing(4)
            
            # Create pagination controls
            self.prev_button = QPushButton("< Prev")
            self.page_info_label = QLabel("Page 1/1")
            self.next_button = QPushButton("Next >")
            self.page_size_combo = QComboBox()
            self.page_size_combo.addItems(["100", "200", "500"])
            self.page_size_combo.setCurrentIndex(0)  # Default to 100
            
            # Add widgets to layout with auto-centering
            pagination_layout.addStretch(1)  # Add stretching space on the left
            pagination_layout.addWidget(QLabel("Items per page:"))
            pagination_layout.addWidget(self.page_size_combo)
            pagination_layout.addWidget(self.prev_button)
            pagination_layout.addWidget(self.page_info_label)
            pagination_layout.addWidget(self.next_button)
            pagination_layout.addStretch(1)  # Add stretching space on the right
            
            # Add to parent layout if provided, with centering alignment
            if parent_layout:
                # Create a container wrapper for horizontal centering
                container = QHBoxLayout()
                container.addStretch(1)
                container.addWidget(self.pagination_widget)
                container.addStretch(1)
                parent_layout.addLayout(container)
            
            # Connect signals
            self.prev_button.clicked.connect(self.on_prev_page)
            self.next_button.clicked.connect(self.on_next_page)
            self.page_size_combo.currentIndexChanged.connect(self.on_page_size_changed)
            
            # Widget persistence settings
            self.pagination_widget.setAttribute(Qt.WA_DeleteOnClose, False)
            
            # Hide until data is loaded
            self.pagination_widget.setVisible(False)
            return True
            
        except Exception as e:
            logging.error(f"Failed to create pagination controls: {str(e)}")
            traceback.print_exc()
            return False


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
        """Create a widget for a specific cell with proper page awareness"""
        try:
            model = self.table.model()
            page = model.current_page
            page_size = model.PAGE_SIZE
            
            # Get page-relative row index
            page_row = row % page_size
            
            logging.debug(f"Creating widget for cell ({row},{col}) - page row {page_row} on page {page+1}")
            
            if page in model._loaded_data and page_row < len(model._loaded_data[page]):
                row_data = model._loaded_data[page][page_row]
                
                if "widgets" in row_data:
                    header = model.HEADERS[col]
                    header_key = header.lower()
                    
                    for key, widget_info in row_data["widgets"].items():
                        if key.lower() == header_key:
                            widget_type = widget_info.get("type")
                            widget_data = widget_info.get("data")
                            
                            if widget_type and widget_data is not None:
                                widget = DataTableManager.create_widget(widget_type, widget_data, model.go_definitions)
                                if widget:
                                    model.widgets[(row, col)] = widget
                                    logging.debug(f"Successfully created {widget_type} widget for row {row} with data: {widget_data}")
                                    return widget
                                else:
                                    # Important: If widget creation failed, remove from widget_cells
                                    if (row, col) in model.widget_cells:
                                        model.widget_cells.remove((row, col))
                                    logging.warning(f"Failed to create widget for cell ({row},{col})")
        except Exception as e:
            logging.error(f"Error creating widget for cell ({row},{col}): {str(e)}")
            traceback.print_exc()
        
        return None

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
            if hasattr(model, 'sourceModel'):
                # Access source model for data operations
                source_model = model.sourceModel()
                source_model._data.extend(processed_data)
                source_model._total_rows = len(source_model._data)
            else:
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

        QTimer.singleShot(500, self.try_load_first_item_blast)        

        self.data_loaded.emit()       


    def on_page_loaded(self, page_index):
        """Appelée après qu'une page a été chargée"""
        logging.debug(f"Page {page_index} chargée correctement")
        
        # Si c'est la première page, essayez de charger les données BLAST du premier élément
        if page_index == 0:
            QTimer.singleShot(100, self.try_load_first_item_blast)

    def try_load_first_item_blast(self):
        """Tente à nouveau de charger l'onglet BLAST après le chargement complet de la page"""
        if hasattr(self, 'model') and hasattr(self.model, '_loaded_data'):
            page = 0
            if page in self.model._loaded_data and len(self.model._loaded_data[page]) > 0:
                # Afficher la structure complète du premier élément pour debug
                item = self.model._loaded_data[page][0]
                logging.debug(f"Structure premier élément chargé: {list(item.keys())}")
                
                # Look directly for blast_hits at top level (no 'display' key)
                if 'blast_hits' in item:
                    hits = item['blast_hits']  # Direct access, no 'display' key
                    logging.debug(f"Premier élément contient {len(hits)} blast_hits")
                    QTimer.singleShot(100, lambda: self.update_blast_tab(hits))
                else:
                    logging.debug("Aucun 'blast_hits' trouvé dans item")
                    
    def reveal_pagination(self):
        """Force reveal pagination controls and show debugging info"""
        try:
            # Check if pagination widget exists and is valid
            has_valid_widget = (hasattr(self, 'pagination_widget') and 
                        self.pagination_widget is not None and 
                        self.is_widget_valid(self.pagination_widget))
            
            # If widget doesn't exist or is invalid, create a new one
            if not has_valid_widget:
                logging.warning("No pagination widget exists or widget was deleted - creating new one")
                # Get the table group box's layout to add pagination to
                layout = self.table_group_box.layout()
                success = self.create_pagination_controls(layout)
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


    def navigate_to_page(self, page_num):
        """Navigate to the specified page"""
        model = self.table.model()
        if not model:
            return
        
        # Before page change debugging
        logging.debug(f"=== BEFORE page change (Page {model.current_page + 1}) ===")
        logging.debug(f"Widget count before: {len(model.widgets)}")
        logging.debug(f"Widget cells before: {len(model.widget_cells)}")
        
        # Update page number in model 
        model.current_page = page_num
        
        # Load the page data
        model._load_page(page_num)
        
        # Clear and recreate widgets
        logging.debug("Clearing widget cache...")
        model.clear_widget_cache()
        
        # Log after clearing
        logging.debug(f"Widget count after clearing: {len(model.widgets)}")
        
        # Recreate widgets
        logging.debug("Recreating widgets...")
        self.recreate_all_visible_widgets()
        
        # After page change debugging
        logging.debug(f"=== AFTER page change (Page {page_num + 1}) ===")
        logging.debug(f"Widget count after: {len(model.widgets)}")
        logging.debug(f"Widget cells after: {len(model.widget_cells)}")
        
        # Update pagination and UI
        self.update_pagination_info()
        QTimer.singleShot(10, self.recreate_all_visible_widgets)  # Extra recreation call
        self.table.viewport().update()

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
            
            # Recreate widget cells mapping - PRIORITIZE PFAMs and other special widgets
            priority_headers = ["PFAMs", "GO", "Results", "InterPro", "Classification"] 
            regular_headers = [h for h in model.HEADERS if h not in priority_headers]
            all_headers_ordered = priority_headers + regular_headers
            
            # First pass: mark all cells that need widgets
            for row in range(len(page_data)):
                row_data = page_data[row]
                if "widgets" in row_data:
                    for col, header in enumerate(model.HEADERS):
                        header_key = header.lower()
                        for key in row_data["widgets"].keys():
                            if key.lower() == header_key:
                                widget_info = row_data["widgets"][key]
                                if widget_info.get("type") != "text":
                                    model.widget_cells.add((row, col))
                                    break
            
            # Second pass: create widgets in priority order
            for header in all_headers_ordered:
                try:
                    col = model.HEADERS.index(header)
                    for row in range(first_visible, last_visible + 1):
                        if row >= len(page_data):
                            continue
                        
                        if (row, col) in model.widget_cells:
                            self.create_widget_for_cell(row, col)
                except ValueError:
                    # Header not found
                    continue
            
            # Force the view to update
            self.table.viewport().update()
            
        except Exception as e:
            logging.error(f"Error recreating widgets: {str(e)}")
            traceback.print_exc()

    

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
            

            
    def create_debug_tools(self):
        """Create debugging tools for pagination issues"""
        debug_panel = QWidget()
        debug_layout = QHBoxLayout(debug_panel)
        debug_layout.setContentsMargins(2, 2, 2, 2)
        
        # Bouton pour comparer les pages
        compare_btn = QPushButton("Compare Pages")
        compare_btn.clicked.connect(TableDebugger.debug_compare_pages)
        
        # Bouton pour forcer le rechargement de la page
        reload_btn = QPushButton("Reload Current")
        reload_btn.clicked.connect(TableDebugger.debug_force_reload_page)
        
        # Bouton pour afficher les cellules actives
        cells_btn = QPushButton("Show Cell Info")
        cells_btn.clicked.connect(TableDebugger.debug_show_cell_info)
        widgets_btn = QPushButton("Debug Widgets")
        widgets_btn.clicked.connect(self.show_widget_debug)
        debug_layout.addWidget(widgets_btn)
        
        # Ajouter les boutons
        debug_layout.addWidget(compare_btn)
        debug_layout.addWidget(reload_btn)
        debug_layout.addWidget(cells_btn)
        
        return debug_panel
    
    def show_widget_debug(self):
        """Show widget debugging information"""
        debug_info = TableDebugger.debug_widget_state()
        QMessageBox.information(self, "Widget Debug", debug_info)

    
            
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


    



