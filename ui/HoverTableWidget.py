from PySide6.QtWidgets import  QTableWidget
from PySide6.QtGui import QColor


class HoverTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)  # Activer le tracking de la souris
        self.previous_item = None  # Sauvegarde de la dernière cellule survolée

    def mouseMoveEvent(self, event):
        """Gérer le survol des cellules"""
        index = self.indexAt(event.pos())  # Récupérer l'index sous la souris
        if index.isValid():
            current_item = self.item(index.row(), index.column())

            if current_item:
                # Restaurer la couleur de l'ancienne cellule
                if self.previous_item and self.previous_item != current_item:
                    self.previous_item.setBackground(QColor(255, 255, 255))  # Blanc

                # Appliquer la couleur de survol
                current_item.setBackground(QColor(255, 255, 0))  # Jaune

                # Sauvegarder la cellule actuelle
                self.previous_item = current_item

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Remettre la couleur d'origine quand la souris quitte la table"""
        if self.previous_item:
            self.previous_item.setBackground(QColor(255, 255, 255))  # Blanc
            self.previous_item = None
        super().leaveEvent(event)
