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
    def populate_table(table: QTableWidget, parsed_results: list, go_definitions: dict ):
        """Populate the table with data."""
        if not isinstance(parsed_results, list) or not all(isinstance(result, dict) for result in parsed_results):
            raise ValueError("parsed_results should be a list of dictionaries.")

        column_headers = [
            "Protein ID", "Description","Length", "Results",
            "PFAMs", "GO", "Classification",
            "Preferred name", "COG", "Enzyme","InterPro"
        ]
        table.setColumnCount(len(column_headers))
        table.setHorizontalHeaderLabels(column_headers)
        table.setRowCount(len(parsed_results))


        for row_idx, result in enumerate(parsed_results):
            """Table data storing"""
            prot_id = result.get("query_id", "N/A")
            prot_length = result.get("query_len", 0)
            eggnog_annotations = result.get("eggNOG_annotations", [])
            eggnog_annotation = eggnog_annotations[0].get("Description", "N/A") if eggnog_annotations else "N/A"
            #query_def = result.get("query-def", "N/A")
            PFAMs = eggnog_annotations[0].get("PFAMs", "N/A") if eggnog_annotations else "N/A"
            preferred_name = eggnog_annotations[0].get("Preferred_name", "N/A") if eggnog_annotations else "N/A"
            cog_category = eggnog_annotations[0].get("COG_category", "N/A") if eggnog_annotations else "N/A"
            ec_number = eggnog_annotations[0].get("EC", "N/A") if eggnog_annotations else "N/A"
            gos = eggnog_annotations[0].get("GOs", "").split(',') if eggnog_annotations else []
            Interpro = result.get("InterproScan_annotation", [])
            current_interpro_annotations = [
                interpro.get("interpro", "") for interpro in Interpro]
            
            """GO display"""
            # Updating GOs with names
            go_terms_with_description = []
            for go_id in gos:
                description, go_type = go_definitions.get(go_id, ("No description available", ""))
                highlighted_go_type = f"<span style='background-color: yellow;'>{go_type}</span>"
                go_terms_with_description.append(f"<p>{go_id} - {highlighted_go_type} - {description}</p>")

            # Limiting at 7 GO terms
            go_terms_display = go_terms_with_description[:7]
            if len(go_terms_with_description) > 7:
                go_terms_display.append("<p>...</p>")  # Adding "..." if exceeding > 7 terms

            go_label = QLabel("".join(go_terms_display))  # Use HTML to join terms
            go_label.setWordWrap(True)
            table.setRowHeight(row_idx, 120)  # Adding height for all rows
            go_label.setStyleSheet("""
                font-family: 'Roboto', sans-serif;
                font-size: 12px;
                color: #333;
                background-color: #FFEBE1;
                padding: 5px;
            """)
            go_label.setTextFormat(Qt.RichText)  # Enable rich text format
            go_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)



            """InterPRO display"""
            IPR_label = QLabel("\n".join(current_interpro_annotations))  # Join terms with line breaks
            IPR_label.setWordWrap(True)  # Enable word wrapping if needed

            IPR_label.setStyleSheet("""
                font-family: 'Roboto', sans-serif;
                font-size: 12px;
                color: #333;
                background-color: #CACCE4; 
                padding: 5px;
            """)# 8083B5 color to test for the background
            IPR_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            """Tags display"""
            tags = []
            if len(gos) > 0:
                tags.append(("go", len(gos)))
            if len(result.get("InterproScan_annotation", [])) > 0:
                tags.append(("interpro", len(result.get("InterproScan_annotation", []))))
            if len(result.get("blast_hits", [])) > 0:
                tags.append(("blast", len(result.get("blast_hits", []))))

            classification_tag = "classified" if len(gos) > 10 else "unclassified"

            """Data List"""
            row_data = [
                prot_id, eggnog_annotation, prot_length, tags,
                 PFAMs, None, classification_tag,
                preferred_name, cog_category,f"EC:{ec_number}",None
            ]

            for col_idx, value in enumerate(row_data):
                if col_idx == 3:
                    table.setCellWidget(row_idx, col_idx, DataTableManager.create_tag_widget(value))
                elif col_idx == 6:
                    table.setCellWidget(row_idx, col_idx, DataTableManager.create_icon_widget(value))
                elif col_idx == 5:
                    table.setCellWidget(row_idx, col_idx, go_label)
                elif col_idx == 10:
                    table.setCellWidget(row_idx, col_idx, IPR_label)                    
                else:
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        # Adjusting column width
        for col_idx, header in enumerate(column_headers):
            if header == "Length":  
                table.setColumnWidth(col_idx, 50)  
            elif header == "COG":  
                table.setColumnWidth(col_idx, 50)    
            elif header == "Enzyme":  
                table.setColumnWidth(col_idx, 80)  
            elif header == "Classification": 
                table.setColumnWidth(col_idx, 80)  
            elif header == "Protein ID": 
                table.setColumnWidth(col_idx, 130)          
            elif header == "Description":  
                table.setColumnWidth(col_idx, 250)      
            elif header == "GO ": 
                table.setColumnWidth(col_idx, 300)     
            elif header == "InterPro":  
                table.setColumnWidth(col_idx, 100)
            elif header == "Preferred name":  
                table.setColumnWidth(col_idx, 100)                     
            else:
                table.setColumnWidth(col_idx, 150) 




    @staticmethod
    def populate_additional_table(table: QTableWidget, parsed_results: list):
        """Remplit une table avec les résultats analysés pour les informations sur les hits."""

        addTable_column_headers = [
            "Hit id", "definition", "accession", "identity", "Alignment length", "E_value", "Bit_score",
            "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
        ]
        table.setHorizontalHeaderLabels(addTable_column_headers)
        total_hits = sum(len(result["blast_hits"]) for result in parsed_results)
        table.setRowCount(total_hits)

        row_idx = 0
        for result in parsed_results:
            for hit in result["blast_hits"]:
                query_start = hit["query_positions"]["start"]
                query_end = hit["query_positions"]["end"]
                subject_start = hit["subject_positions"]["start"]
                subject_end = hit["subject_positions"]["end"]
                hit_accession = result.get("hit_accession", "N/A")
                chunked_value = hit_accession.split("[[taxon")[0].strip()
                hsp = hit.get("hsps", [])
                hsp = hit.get("hsps", [])
                if hsp:
                    hsp_bitScore = hsp[0].get("bit_score", "N/A")
                else:
                    hsp_bitScore = "N/A"


                #hsp_bitScore = hsp[0].get("bit_score", "N/A")

                # Vérification et conversion des valeurs numériques
                try:
                    percent_identity = float(hit["percent_identity"]) if hit["percent_identity"] is not None else 0.0
                    alignment_length = float(hit["alignment_length"]) if hit["alignment_length"] is not None else 1.0  # Éviter la division par zéro
                    percent_identity_value = (percent_identity / alignment_length) * 100
                except (ValueError, ZeroDivisionError):
                    percent_identity_value = 0.0  # Valeur par défaut appropriée


                row_data = [
                    hit["hit_id"],  # hit_id
                    hit["hit_def"],  # hit_def
                    chunked_value,  # accession
                    percent_identity_value,  # percent_identity
                    alignment_length,  # alignment_length
                    hit["e_value"],  # e_value
                    hit["bit_score"],  # bit_score
                    query_start,  # Query Start
                    query_end,  # Query End
                    subject_start,  # Subject Start
                    subject_end,  # Subject End
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

                
                
                   
