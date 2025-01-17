import csv
import json
from PySide6.QtWidgets import QTableWidget, QLabel

def export_to_json(table: QTableWidget, file_path='table_data.json'):
    """Export table data to a JSON file."""
    table_data = []
    for row in range(table.rowCount()):
        row_data = {
            "PROTID": table.item(row, 0).text() if table.item(row, 0) else "",
            "Prot Length": table.item(row, 1).text() if table.item(row, 1) else "",
            "Annot": table.item(row, 2).text() if table.item(row, 2) else "",
            # Gérer les widgets dans la colonne 3
            "Annot SEAGO": extract_text_from_widget(table.cellWidget(row, 3)),
            "Hits": table.item(row, 4).text() if table.item(row, 4) else "",
            "InterPro Domain": table.item(row, 5).text() if table.item(row, 5) else "",
            "GOs": table.item(row, 6).text() if table.item(row, 6) else "",
            # Gérer les widgets dans la colonne 7
            "Classification": extract_text_from_widget(table.cellWidget(row, 7))
        }
        table_data.append(row_data)

    with open(file_path, 'w') as file:
        json.dump(table_data, file, indent=4)
    print("Table data has been exported to", file_path)

def export_to_csv(table: QTableWidget, file_path='table_data.csv'):
    """Export table data to a CSV file."""
    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Écriture des en-têtes
        writer.writerow([table.horizontalHeaderItem(i).text() for i in range(table.columnCount())])
        # Écriture des lignes
        for row in range(table.rowCount()):
            row_data = [
                table.item(row, col).text() if table.item(row, col) else ""    
                if not table.cellWidget(row, col)
                else extract_text_from_widget(table.cellWidget(row, col))
                for col in range(table.columnCount())
            ]
            writer.writerow(row_data)
    print("Table data has been exported to", file_path)

def export_to_tsv(table: QTableWidget, file_path='table_data.tsv'):
    """Export table data to a TSV file."""
    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter='\t')
        # Écriture des en-têtes
        writer.writerow([table.horizontalHeaderItem(i).text() for i in range(table.columnCount())])
        # Écriture des lignes
        for row in range(table.rowCount()):
            row_data = [
                table.item(row, col).text() if table.item(row, col) else ""
                if not table.cellWidget(row, col)
                else extract_text_from_widget(table.cellWidget(row, col))
                for col in range(table.columnCount())
            ]
            writer.writerow(row_data)
    print("Table data has been exported to", file_path)




def extract_text_from_widget(widget):
    """Extract text from a widget, handling QLabel or other common widget types."""
    if not widget:
        return ""
    # Vérifiez si le widget est un QLabel ou un autre type de widget
    label = widget.findChild(QLabel)
    if label:
        return label.text()
    return ""  # Retournez une chaîne vide si aucun texte n'est trouvé
