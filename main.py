import sys
import traceback
import timeit
import time
import asyncio
from typing import Optional
from qasync import asyncSlot, QApplication, QEventLoop
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox, 
                              QProgressBar, QStatusBar, QTabWidget,QVBoxLayout, QPushButton,QWidget)

from utils.data_loader import load_parsed_blast_hits
from ui.table_window import DynamicTableWindow

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
        self.results_widget = None  # Declare results_widget here!  This was missing.
        self.current_task: Optional[asyncio.Task] = None
        self.signals = AppSignals()
        self._connect_signals()

    def _setup_ui(self):
        """Initialise l'interface utilisateur"""
        self.main_window.setWindowTitle("DataTable Interface")
        self.main_window.resize(800, 600)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        
        # Bouton d'annulation
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self.cancel_current_task)

        # Central Widget (Use a QWidget with a layout)
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        self.central_layout = QVBoxLayout()  # Make this an instance variable
        central_widget.setLayout(self.central_layout)
        # Barre d'état
        status_bar = QStatusBar()
        status_bar.addPermanentWidget(self.progress_bar)
        status_bar.addPermanentWidget(self.cancel_btn)
        self.main_window.setStatusBar(status_bar)
        
        self.main_window.show()

    def _connect_signals(self):
        """Connecte les signaux aux slots"""
        self.signals.progress_updated.connect(self.update_progress)
        self.signals.error_occurred.connect(self.show_error)
        self.signals.task_cancelled.connect(self.handle_task_cancellation)

    @asyncSlot()
    async def open_file_and_load(self):
        """Ouvre une boîte de dialogue et charge le fichier"""
        try:
            file_path = await self._show_async_file_dialog()
            if file_path:
                await self.process_file(file_path)
        except asyncio.CancelledError:
            self.signals.task_cancelled.emit()
        except Exception as e:
            self.signals.error_occurred.emit(str(e))

    async def _show_async_file_dialog(self) -> Optional[str]:
        """Affiche la boîte de dialogue de fichier de manière asynchrone"""
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

    async def process_file(self, file_path: str):
        """Charge et traite le fichier avec gestion de progression"""
        start_time = time.time()  # Record start time
        try:
            self.current_task = asyncio.current_task()
            self._show_loading_state(True)
            
            # Simulation de progression
            self.signals.progress_updated.emit(10, "Démarrage du chargement...")
            parsed_results = await load_parsed_blast_hits(
                file_path,
                progress_callback=lambda p: self.signals.progress_updated.emit(p, "Chargement...")
            )
            end_time = time.time()  # Record end time
            elapsed_time = end_time - start_time  # Calculate elapsed time

            # Format the elapsed time (example)
            elapsed_time_str = f"{elapsed_time:.2f} seconds"
            self.signals.progress_updated.emit(100, f"Chargement terminé! ({elapsed_time_str})")
            await asyncio.sleep(0.5)  # Laisse voir la progression complète
            self.show_results(parsed_results)
            
        except asyncio.CancelledError:
            self.signals.task_cancelled.emit()
        except Exception as e:
            self.signals.error_occurred.emit(f"Erreur de traitement: {str(e)}")
            traceback.print_exc()
        finally:
            self._show_loading_state(False)
            self.current_task = None

    def _show_loading_state(self, loading: bool):
        """Affiche/masque les éléments de chargement"""
        self.progress_bar.setVisible(loading)
        self.cancel_btn.setVisible(loading)
        self.app.processEvents()

    def update_progress(self, value: int, message: str):
        """Met à jour la barre de progression"""
        self.progress_bar.setValue(value)
        self.main_window.statusBar().showMessage(message)
        self.app.processEvents()

    def show_results(self, data):
        """Affiche les résultats directement dans la fenêtre principale"""
        if self.results_widget:  # Clear previous results if any
            self.central_layout.removeWidget(self.results_widget)
            self.results_widget.deleteLater()  # Important for cleanup
            self.results_widget = None  # Reset the widget

        self.results_widget = DynamicTableWindow(data) # Create a table window
        self.central_layout.addWidget(self.results_widget)  # Add table to the central layout
        # No tabs are used now, so no need to manage them

    def close_tab(self, index: int):
        """Ferme un onglet de résultats"""
        widget = self.results_tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.results_tabs.removeTab(index)

    def cancel_current_task(self):
        """Annule la tâche en cours d'exécution"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.signals.task_cancelled.emit()

    def handle_task_cancellation(self):
        """Gère l'annulation de tâche"""
        self.signals.error_occurred.emit("Tâche annulée par l'utilisateur")
        self._show_loading_state(False)

    def show_error(self, message: str):
        """Affiche une erreur dans une boîte de dialogue"""
        QMessageBox.critical(
            self.main_window,
            "Erreur",
            f"Une erreur est survenue:\n{message}",
            QMessageBox.Ok
        )

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background-color: #EAEAEA; }
        QTabBar::close-button { image: url(close_icon.png); }
    """)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    controller = AppController(app)
    controller.open_file_and_load()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()