import sys
import traceback
import time
import asyncio
import json
from typing import Optional

from qasync import asyncSlot, QApplication, QEventLoop
from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox,
                               QProgressBar, QStatusBar, QVBoxLayout,
                               QPushButton, QWidget, QTableWidget, QTableWidgetItem)

from ui.table_window import DynamicTableWindow
from utils.table_manager import DataTableManager
import timeit
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class AppSignals(QObject):
    progress_updated = Signal(int, str)
    error_occurred = Signal(str)
    task_cancelled = Signal()
    data_loaded = Signal(list)

class DataLoaderThread(QThread):
    data_loaded = Signal(list)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        print(f"DataLoaderThread initialized with file path: {file_path}")  # Log file path

    def run(self):
        try:
            print(f"Loading data from file: {self.file_path}")  # Log file path
            with open(self.file_path, 'r') as file:
                data = json.load(file)
            results = data.get("results", [])
            self.data_loaded.emit(results)
        except Exception as e:
            print(f"Error loading data: {e}")

class AppController(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.main_window = QMainWindow()
        self._setup_ui()
        self.results_widget = None
        self.current_task: Optional[asyncio.Task] = None
        self.signals = AppSignals()
        self._connect_signals()
        self.start_time = None
        self.data = []

    def _setup_ui(self):
        self.main_window.setWindowTitle("SEAGO")
        self.main_window.resize(1200, 900)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self.cancel_current_task)
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        self.central_layout = QVBoxLayout()
        central_widget.setLayout(self.central_layout)
        status_bar = QStatusBar()
        status_bar.addPermanentWidget(self.progress_bar)
        status_bar.addPermanentWidget(self.cancel_btn)
        self.main_window.setStatusBar(status_bar)
        self.main_window.show()

    def _connect_signals(self):
        self.signals.progress_updated.connect(self.update_progress)
        self.signals.error_occurred.connect(self.show_error)
        self.signals.task_cancelled.connect(self.handle_task_cancellation)
        self.signals.data_loaded.connect(self.on_data_loaded)

    @asyncSlot()
    async def open_file(self):
        try:
            file_path = await self._show_async_file_dialog()
            print(f"Selected file path: {file_path}")  # Log file path
            if file_path:
                self.load_data_in_background(file_path)
            else:
                self.signals.error_occurred.emit("No file selected.")
        except asyncio.CancelledError:
            self.signals.task_cancelled.emit()
        except Exception as e:
            self.signals.error_occurred.emit(str(e))
            traceback.print_exc()

    def load_data_in_background(self, file_path: str):
        self.start_time = time.time()
        self._show_loading_state(True)
        self.signals.progress_updated.emit(1, "Loading file...")
        self.loader_thread = DataLoaderThread(file_path)
        self.loader_thread.data_loaded.connect(self.on_data_loaded)
        self.loader_thread.start()

    def on_data_loaded(self, data):
        try:
            print("Data loaded:", len(data) if data else "No data")  # Log data size
            self.data = data
            self._show_loading_state(False)
            
            if data:
                # Pass the actual file path that was used to load the data
                current_file_path = getattr(self.loader_thread, 'file_path', '')
                self.show_results(data, current_file_path)
                
            end_time = time.time()
            total_time = end_time - self.start_time
            print(f"Total execution time: {total_time:.2f} seconds")
        except Exception as e:
            print(f"Error in on_data_loaded: {str(e)}")
            traceback.print_exc()
            self.signals.error_occurred.emit(str(e))

    async def process_data_in_batches(self, data):
        batch_size = 10  # Adjust batch size as needed
        total_items = len(data)
        for start in range(0, total_items, batch_size):
            end = min(start + batch_size, total_items)
            batch = data[start:end]
            # Process the batch (e.g., update the UI)
            await self.process_batch(batch)
            progress = (end / total_items) * 100
            self.signals.progress_updated.emit(progress, f"Processing data... ({progress:.1f}%)")
            await asyncio.sleep(0)  # Yield control to the event loop

    async def process_batch(self, batch):
        # Implement batch processing logic here
        # For example, update the UI with the batch data
        print(f"Processing batch of size {len(batch)}")
        for item in batch:
            # Process each item in the batch
            print("Processing item:", item)  # Log the item being processed
            if self.results_widget:
                table = self.results_widget.table
                base_data, widgets = DataTableManager._process_main_row(item, go_definitions={})
                print("Base data:", base_data)  # Log the base data
                print("Widgets:", widgets)  # Log the widgets
                row_position = table.rowCount()
                table.insertRow(row_position)
                for col, value in enumerate(base_data):
                    if isinstance(value, str) or isinstance(value, int):
                        table.setItem(row_position, col, QTableWidgetItem(str(value)))
                    elif value is None and col in widgets:
                        table.setCellWidget(row_position, col, widgets[col])

    async def _show_async_file_dialog(self) -> Optional[str]:
        dialog = QFileDialog(self.main_window)
        dialog.setWindowModality(Qt.ApplicationModal)
        future = asyncio.Future()
        dialog.accepted.connect(lambda: future.set_result(dialog.selectedFiles()))
        dialog.rejected.connect(lambda: future.set_result(None))
        dialog.show()
        try:
            files = await future
            return files[0] if files else None
        finally:
            dialog.deleteLater()

    def handle_progress_update(self, progress: int):
        message = f"Traitement des données... ({progress:.1f}%)"
        self.signals.progress_updated.emit(progress, message)
        self.app.processEvents()

    def _show_loading_state(self, loading: bool):
        self.progress_bar.setVisible(loading)
        self.cancel_btn.setVisible(loading)
        self.app.processEvents()

    def update_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.main_window.statusBar().showMessage(message)
        self.app.processEvents()

    def show_results(self, parsed_results, file_path: str):
        try:
            if self.results_widget:
                self.central_layout.removeWidget(self.results_widget)
                self.results_widget.deleteLater()
                self.results_widget = None
                    
            # Ensure we have valid data before creating the widget
            if parsed_results:
                #logging.debug(f"Parsed results: {parsed_results}")

                self.results_widget = DynamicTableWindow(parsed_results, file_path)
                self.central_layout.addWidget(self.results_widget)
                
                # Appelez populate_table ici
                DataTableManager.populate_table(self.results_widget.table, parsed_results, self.results_widget.go_definitions)
                
                end_time = time.time()
                if self.start_time:
                    total_time = end_time - self.start_time
                    print(f"Total execution time: {total_time:.2f} seconds")
                else:
                    print("Start time not recorded.")
            else:
                raise ValueError("No data available to display")
                    
        except Exception as e:
            print(f"Error in show_results: {str(e)}")
            traceback.print_exc()

    def cancel_current_task(self):
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.signals.task_cancelled.emit()

    def handle_task_cancellation(self):
        self.signals.error_occurred.emit("Tâche annulée par l'utilisateur")
        self._show_loading_state(False)

    def show_error(self, message: str):
        QMessageBox.critical(
            self.main_window, "Erreur", f"Une erreur est survenue:\n{message}", QMessageBox.Ok
        )

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = AppController(app)
    start_time = timeit.default_timer()
    asyncio.ensure_future(controller.open_file())  # Start the process asynchronously
    end_time = timeit.default_timer()
    print(f"Temps de chargement : {end_time - start_time:.6f} secondes")

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()