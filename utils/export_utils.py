import json
import csv


def export_to_json(table, filename='table_data.json'):
    table_data = []
    for row in range(table.rowCount()):
        row_data = {
            "Protein ID": table.item(row, 0).text(),
            "Protein Length": table.item(row, 1).text(),
            "Annotation": table.item(row, 2).text(),
            "Manual Annotation": table.cellWidget(row, 3).text(),
            "Hits": table.item(row, 4).text(),
            "InterPro Domain": table.item(row, 5).text(),
            "GOs": table.item(row, 6).text(),
            "Classification": table.cellWidget(row, 7).windowIconText()
        }
        table_data.append(row_data)
    with open(filename, 'w') as file:
        json.dump(table_data, file, indent=4)


def export_to_csv(table, filename='table_data.csv', delimiter=','):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=delimiter)
        # headers
        writer.writerow([table.horizontalHeaderItem(i).text() for i in range(table.columnCount())])
        #  rows
        for row in range(table.rowCount()):
            writer.writerow([table.item(row, col).text() if table.item(row, col) else '' for col in range(table.columnCount())])
