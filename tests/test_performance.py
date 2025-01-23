import timeit
from PySide6.QtWidgets import QTableWidget, QLabel, QApplication
from PySide6.QtCore import Qt
import sys
from ..utils.table_manager import DataTableManager

parsed_results = [
    {
        "query_id": "P12345",
        "query_len": 300,
        "eggNOG_annotations": [{
            "Description": "Sample protein",
            "PFAMs": "PF001",
            "Preferred_name": "Sample",
            "COG_category": "C",
            "EC": "1.1.1.1",
            "GOs": "GO:0008150,GO:0003674"
        }],
        "InterproScan_annotation": [{
            "interpro": "IPR001234",
        }],
        "blast_hits": [{"hit_id": "H12345"}]
    },
    # to update
]

go_definitions = {
    "GO:0008150": ("Description for GO:0008150", "Biological Process"),
    "GO:0003674": ("Description for GO:0003674", "Molecular Function")
}

def test_populate_table():
    app = QApplication(sys.argv)
    table = QTableWidget()
    DataTableManager.populate_table(table, parsed_results, go_definitions)

time_taken = timeit.timeit("test_populate_table()", setup="from __main__ import test_populate_table", number=10)
print(f"Temps d'exécution moyen pour populate_table: {time_taken / 10} secondes")

if __name__ == "__main__":
    test_populate_table()