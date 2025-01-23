from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QPainter

#to Review
class TagDistributionChart(QWidget):
    def __init__(self, parsed_results):
        super().__init__()

        self.tag_counts = {
            "blast": 0,
            "interpro": 0,
            "eggnog": 0
        }

        #filling with parsed result 
        for result in parsed_results:
            if len(result.get("blast_hits", [])) > 0:
                self.tag_counts["blast"] += 1
            if len(result.get("InterproScan_annotation", [])) > 0:
                self.tag_counts["interpro"] += 1
            if len(result.get("eggNOG_annotations", [])) > 0:
                self.tag_counts["eggnog"] += 1

        # graph
        self.chart = QChart()
        self.chart.setTitle("Distribution des Tags")
        
       # bar series
        self.bar_set = QBarSet("Protéines")
        self.bar_set.append([self.tag_counts["blast"], self.tag_counts["interpro"], self.tag_counts["eggnog"]])
        
        # serie
        self.series = QBarSeries()
        self.series.append(self.bar_set)
        
        
        self.chart.addSeries(self.series)
        
        # x AXE
        categories = ["BLAST", "InterPro", "EGGNOG"]
        self.axis_x = QBarCategoryAxis()
        self.axis_x.append(categories)
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)
        
        # y AXE
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, max(self.tag_counts.values()) + 1)  # Plage dynamique
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_y)

        # graphique view
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)


        layout = QVBoxLayout()
        layout.addWidget(self.chart_view)
        self.setLayout(layout)
