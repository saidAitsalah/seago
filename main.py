import sys
import traceback
import time
import asyncio
from typing import Optional

from qasync import asyncSlot, QApplication, QEventLoop
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox,
                                 QProgressBar, QStatusBar, QVBoxLayout,
                                 QPushButton, QWidget)

from utils.data_loader import load_parsed_blast_hits  # Make sure this path is correct
from ui.table_window import DynamicTableWindow  # And this one

class AppSignals(QObject):
    progress_updated = Signal(int, str)
    error_occurred = Signal(str)
    task_cancelled = Signal()

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

    @asyncSlot()
    async def open_file(self):  # Simplified
        try:
            file_path = await self._show_async_file_dialog()
            if file_path:
                await self.load_and_show_results(file_path)
        except asyncio.CancelledError:
            self.signals.task_cancelled.emit()
        except Exception as e:
            self.signals.error_occurred.emit(str(e))
            traceback.print_exc()

    async def load_and_show_results(self, file_path: str):
        self.start_time = time.time()
        try:
            self.current_task = asyncio.current_task()
            self._show_loading_state(True)
            self.signals.progress_updated.emit(1, "Loading file...")

            parsed_results = await load_parsed_blast_hits(
                file_path, progress_callback=self.handle_progress_update
            )

            self.show_results(parsed_results, file_path)  # Pass parsed_results and file_path

            end_time = time.time()
            if self.start_time:
                total_time = end_time - self.start_time
                print(f"Total execution time: {total_time:.2f} seconds")
                self.signals.progress_updated.emit(100, f"Loading complete! ({total_time:.2f}s)")
            else:
                print("Start time not recorded.")

        except asyncio.CancelledError:
            self.signals.task_cancelled.emit()
        except Exception as e:
            self.signals.error_occurred.emit(f"Error processing: {str(e)}")
            traceback.print_exc()
        finally:
            self._show_loading_state(False)
            self.current_task = None

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
        self.app.processEvents()  # Use with caution

    def _show_loading_state(self, loading: bool):
        self.progress_bar.setVisible(loading)
        self.cancel_btn.setVisible(loading)
        self.app.processEvents()

    def update_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.main_window.statusBar().showMessage(message)
        self.app.processEvents()

    def show_results(self, parsed_results, file_path: str): # Accept parsed_results
        if self.results_widget:
            self.central_layout.removeWidget(self.results_widget)
            self.results_widget.deleteLater()
            self.results_widget = None

        self.results_widget = DynamicTableWindow(parsed_results, file_path)  # Pass parsed_results!
        self.central_layout.addWidget(self.results_widget)

        end_time = time.time()
        if self.start_time:
            total_time = end_time - self.start_time
            print(f"Total execution time: {total_time:.2f} seconds")
        else:
            print("Start time not recorded.")


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
    app.setStyle("Fusion")  # or other styles

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = AppController(app)
    controller.open_file()  # Start the process

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()