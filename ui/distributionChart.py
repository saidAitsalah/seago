from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QPainter


class TagDistributionChart(QWidget):
    def __init__(self, parsed_results):
        super().__init__()

        # Calcul des distributions de tags
        self.tag_counts = {
            "blast": 0,
            "interpro": 0,
            "eggnog": 0
        }

        # Remplir les comptages avec les résultats parsés
        for result in parsed_results:
            if len(result.get("blast_hits", [])) > 0:
                self.tag_counts["blast"] += 1
            if len(result.get("InterproScan_annotation", [])) > 0:
                self.tag_counts["interpro"] += 1
            if len(result.get("eggNOG_annotations", [])) > 0:
                self.tag_counts["eggnog"] += 1

        # Créer un graphique
        self.chart = QChart()
        self.chart.setTitle("Distribution des Tags")
        
        # Créer des séries de barres pour chaque tag
        self.bar_set = QBarSet("Protéines")
        self.bar_set.append([self.tag_counts["blast"], self.tag_counts["interpro"], self.tag_counts["eggnog"]])
        
        # Créer la série
        self.series = QBarSeries()
        self.series.append(self.bar_set)
        
        # Ajouter la série au graphique
        self.chart.addSeries(self.series)
        
        # Créer un axe X avec les noms des tags
        categories = ["BLAST", "InterPro", "EGGNOG"]
        self.axis_x = QBarCategoryAxis()
        self.axis_x.append(categories)
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)
        
        # Créer un axe Y pour la plage des valeurs
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, max(self.tag_counts.values()) + 1)  # Plage dynamique
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_y)

        # Créer la vue du graphique
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        # Ajouter le graphique à l'interface
        layout = QVBoxLayout()
        layout.addWidget(self.chart_view)
        self.setLayout(layout)
