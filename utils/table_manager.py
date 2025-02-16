from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, QWidget, QHeaderView, QProgressBar
)
from PySide6.QtGui import QPixmap, QColor, QBrush
from PySide6.QtCore import Qt



class DataTableManager:

    ICON_PATHS = {
        "classified": "assets/settings.png",
        "unclassified": "assets/edit.png"
    }

    HEADER_STYLE = """
        QHeaderView::section {
            background-color: #D7D7D7;
            color: #333333;
            font : Roboto;
            font-weight: bold;
            font-size: 12px ;
        }
    """
    
    HEADER_STYLE2 = """
        background-color: #077187;  /* hits */
            color: #333333;
            font : Roboto;
            font-weight: bold;
            font-size: 12px ;
    """    
    TAG_STYLES = {
        "blast": "background-color: #077187; color: white; font-weight: bold; border-radius: 5px; padding: 3px;",
        "interpro": "background-color: #4F518C; color: white; font-weight: bold; border-radius: 5px; padding: 3px;",
        "default": "background-color: #ED7D3A; color: white; font-weight: bold; border-radius: 5px; padding: 3px;"
    }

    @staticmethod
    def change_specific_header_color(table: QTableWidget, column_index: int, color: str):
        """Change the color of a specific header column."""
        header = table.horizontalHeader()
        #header.setSectionResizeMode(column_index, QHeaderView.Stretch)
        header.setStyleSheet(f"QHeaderView::section:nth-child({column_index + 1}) {{ background-color: {color}; }}")   

    @staticmethod
    def style_table_headers(table: QTableWidget,target_column: int):
        """Apply styles to table headers."""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.HEADER_STYLE)
        header.setSectionResizeMode(QHeaderView.Interactive)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        #custom_header = CustomHeader(Qt.Horizontal, table, target_column=target_column)
        #table.setHorizontalHeader(custom_header)
        #header.setSectionResizeMode(QHeaderView.ResizeToContents)  
        header.setStretchLastSection(True)  # Expands the last column to fill available space
        table.resizeRowsToContents()
        #table.setHorizontalHeaderLabels(["GOs"])


    @staticmethod
    def style_AdditionalTable_headers(table: QTableWidget):
        """Apply styles to table headers."""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.HEADER_STYLE)
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)    

    @staticmethod
    def style_IprscanTable_headers(table: QTableWidget):
        """Apply styles to table headers."""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.HEADER_STYLE)
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)    

    """
    @staticmethod
    def style_table_data(table: QTableWidget):
            table.setStyleSheet(DataTableManager.TABLE_STYLE)
    """

    @staticmethod
    def create_tag_widget(tags):
        """ styled tags """
        tag_layout = QHBoxLayout()
        tag_widget = QWidget()

        for tag_type, tag_value in tags:
            label = QLabel(str(tag_value))
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(35, 18)
            label.setStyleSheet(DataTableManager.TAG_STYLES.get(tag_type, DataTableManager.TAG_STYLES["default"]))


            # tooltip 
            if tag_type == "blast":
                label.setToolTip("Blast results (alignement avec les bases de données).")
            elif tag_type == "interpro":
                label.setToolTip("InterPro results (functional classification).")
            else:
                label.setToolTip("GO ontologie results.")

            tag_layout.addWidget(label)

        tag_widget.setLayout(tag_layout)
        return tag_widget

    @staticmethod
    def create_icon_widget(tag):
        """icon for classification """
        icon_widget = QWidget()
        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(QPixmap(DataTableManager.ICON_PATHS[tag]).scaled(16, 16, Qt.KeepAspectRatio))

        #tooltip
        icon_label.setToolTip("Manual/Automatic Annotation.")

        icon_layout.addWidget(icon_label)
        icon_widget.setLayout(icon_layout)
        return icon_widget
    


    @staticmethod
    def populate_table(table, parsed_results, go_definitions):
        table.setRowCount(0)  # Clear existing rows
        table.setColumnCount(1) # Just one column for now
        table.setHorizontalHeaderLabels(["query_id"]) # Column header

        for i, result in enumerate(parsed_results[:5]): # Show first 5
            table.insertRow(i)
            item = QTableWidgetItem(result.get("query_id", "")) # Handle missing key
            table.setItem(i, 0, item)




    @staticmethod
    def populate_additional_table(table: QTableWidget, parsed_results: list):
        addTable_column_headers = [
            "Hit id", "definition", "accession", "identity", "Alignment length", 
            "E_value", "Bit_score", "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
        ]
        table.setHorizontalHeaderLabels(addTable_column_headers)

        total_hits = 0
        for result in parsed_results:
            if "blast_hits" in result:  # Check if "blast_hits" key exists
                total_hits += len(result["blast_hits"])

        table.setRowCount(total_hits)

        row_idx = 0
        for result in parsed_results:
            if "blast_hits" in result:  # Check AGAIN before iterating over hits
                for hit in result["blast_hits"]:
                    query_start = hit.get("query_positions", {}).get("start")  # Handle missing keys
                    query_end = hit.get("query_positions", {}).get("end")
                    subject_start = hit.get("subject_positions", {}).get("start")
                    subject_end = hit.get("subject_positions", {}).get("end")
                    hit_accession = result.get("hit_accession", "N/A")
                    chunked_value = hit_accession.split("[[taxon")[0].strip() if hit_accession != "N/A" else "N/A" # Handle split error
                    hsp = hit.get("hsps", [])
                    hsp_bitScore = hsp[0].get("bit_score", "N/A") if hsp else "N/A"

                    percent_identity_str = hit.get("percent_identity")
                    percent_identity = 0.0
                    if percent_identity_str and str(percent_identity_str).replace(".", "", 1).isdigit():
                        try:
                            percent_identity = float(percent_identity_str)
                        except ValueError:
                            print(f"Warning: Invalid percent_identity string: {percent_identity_str}")

                    alignment_length_str = hit.get("alignment_length")
                    alignment_length = 1.0
                    if alignment_length_str and alignment_length_str != "Unknown":
                        try:
                            alignment_length = float(alignment_length_str)
                        except ValueError:
                            print(f"Warning: Invalid alignment_length string: {alignment_length_str}")

                    percent_identity_value = (percent_identity / (alignment_length if alignment_length > 0 else 1)) * 100

                    row_data = [
                        hit.get("hit_id", "N/A"),  # Use get() and provide default
                        "N/A",  # definition (not available in your current code)
                        chunked_value,
                        percent_identity_value,
                        alignment_length,
                        hit.get("e_value", "N/A"),
                        hit.get("bit_score", "N/A"),
                        query_start,
                        query_end,
                        subject_start,
                        subject_end,
                        hsp_bitScore
                    ]

                for col_idx, value in enumerate(row_data):
                    if col_idx == 3:  # colonne percent_identity avec barre de progression
                        progress = QProgressBar()
                        progress.setValue(int(value))
                        progress.setAlignment(Qt.AlignCenter)
                        if int(value) > 90:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #8FE388;}")
                        elif int(value) < 70:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #E3AE88;}")
                        else:
                            progress.setStyleSheet("QProgressBar::chunk {background-color: #88BCE3;}")
                        table.setCellWidget(row_idx, col_idx, progress)
                    elif col_idx == 0:
                        item = QTableWidgetItem(str(value))
                        item.setBackground(QBrush(QColor("#A8D8DE")))  # hits id avec un code couleur
                        table.setItem(row_idx, col_idx, item)
                    else:
                        item = QTableWidgetItem(str(value))
                        table.setItem(row_idx, col_idx, item)

                row_idx += 1


        for col_idx, header in enumerate(addTable_column_headers):
                    if header == "percent_identity":
                        table.setColumnWidth(col_idx, 100)
                    elif header == "hit_id":
                        table.setColumnWidth(col_idx, 100)
                    else:
                        table.setColumnWidth(col_idx, 100)    
                        


    @staticmethod
    def populate_interproscan_table(table: QTableWidget, interproscan_results: list):
        """Populates a table with InterProScan annotation results."""
        table_column_headers = [
            "domain_id", "code", "method", "Method ID", "Description", "status", "Ipr ID", 
            "description", "Signature Type", "ac", "name", "desc"
        ]
        table.setColumnCount(len(table_column_headers))
        table.setHorizontalHeaderLabels(table_column_headers)

        total_rows = len(interproscan_results)
        table.setRowCount(total_rows)


        if not isinstance(interproscan_results, list) or not all(isinstance(result, dict) for result in interproscan_results):
            raise ValueError("parsed_results should be a list of dictionaries.")

     
        for row_idx, result in enumerate(interproscan_results):

            InterproScan_annotation = result.get("InterproScan_annotation", [])
            domain = InterproScan_annotation[0].get("domain_id", "N/A") if InterproScan_annotation else "N/A"
            code = InterproScan_annotation[0].get("code", "N/A") if InterproScan_annotation else "N/A"
            methode = InterproScan_annotation[0].get("method", "N/A") if InterproScan_annotation else "N/A"
            method_id = InterproScan_annotation[0].get("method_id", "N/A") if InterproScan_annotation else "N/A"
            description = InterproScan_annotation[0].get("description", "N/A") if InterproScan_annotation else "N/A"
            status = InterproScan_annotation[0].get("status", "N/A") if InterproScan_annotation else "N/A"
            interpro = InterproScan_annotation[0].get("interpro", "N/A") if InterproScan_annotation else "N/A"
            interpro_description = InterproScan_annotation[0].get("interpro_description", "N/A") if InterproScan_annotation else "N/A"
            type = InterproScan_annotation[0].get("type", "N/A") if InterproScan_annotation else "N/A"
            """TO-DO !!"""
            signature = result.get("signature", {"ac": "N/A", "name": "N/A", "desc": "N/A"})
            ac = signature.get("ac", "N/A")
            name = signature.get("name", "N/A")
            desc = signature.get("desc", "N/A")

            row_data = [
                domain,code,methode,method_id,description,status,interpro,interpro_description,type,ac,name,desc
            ]

            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                table.setItem(row_idx, col_idx, item)

        #columns width
        for col_idx, header in enumerate(table_column_headers):
            table.setColumnWidth(col_idx, 150)

    @staticmethod
    def populate_GO_table(table: QTableWidget, GO_results: list):
        """Populates a QTableWidget with GO annotation results."""
        
        table_column_headers = [
            "id", "name", "namespace", "Definition", "comment", 
            "synonym", "is_a", "is_obsolete", "relationship", "xref"
        ]
        
        table.setColumnCount(len(table_column_headers))
        table.setHorizontalHeaderLabels(table_column_headers)

        total_rows = len(GO_results)
        table.setRowCount(total_rows)

        if not isinstance(GO_results, list) or not all(isinstance(result, dict) for result in GO_results):
            raise ValueError("GO_results should be a list of dictionaries.")
        

        for row_idx, result in enumerate(GO_results):
            for col_idx, header in enumerate(table_column_headers):
                value = result.get(header, "")  # Récupérer la valeur ou ""
                
                # Convertir les listes en texte si nécessaire
                if isinstance(value, list):
                    value = "; ".join(value)  # Séparer les valeurs par "; "

                item = QTableWidgetItem(str(value)) 
        
                if header == "id":
                    item.setBackground(QColor("#FFEBE1"))  # go color code 
                
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

                
                
                   
