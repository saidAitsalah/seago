from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, QWidget, QHeaderView, QProgressBar
)
from PySide6.QtGui import QPixmap, QColor, QBrush
from PySide6.QtCore import Qt
from ui.customHeader import CustomHeader


class DataTableManager:

    ICON_PATHS = {
        "classified": "assets/check.png",
        "unclassified": "assets/close.png"
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

 #   TABLE_STYLE = 
    """
        QTableWidget {
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
            background-color: #f9f9f9;
            color: #333;
            gridline-color: #cccccc;
            selection-background-color: #c5e0b3;
            selection-color: #000;
            border: 1px solid #cccccc;
            border-radius: 5px;
            padding: 5px;
        }
        
        QHeaderView::section {
            background-color: #4F518C;
            color: white;
            font-weight: bold;
            font-size: 13px;
            padding: 5px;
        }
        
        QTableWidget::item {
            padding: 5px;
        }
        
        QTableWidget::item:selected {
            background-color: #8FE388;
            color: #000;
        }
        
        QTableWidget::horizontalHeader {
            font-weight: bold;
            background-color: #4F518C;
            color: white;
            padding: 10px;
        }
        
        QTableWidget::verticalHeader {
            font-weight: bold;
            background-color: #f0f0f0;
            color: #4F518C;
            padding: 5px;
        }

        QTableWidget::item:hover {
            background-color: #f0f0f0;
        }
        
        QTableWidget::item:selected:hover {
            background-color: #8FE388;
        }

        QTableWidget::corner {
            background-color: #f0f0f0;
        }
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
        # Appliquer un style spécifique à l'en-tête de la colonne
        #header.setSectionResizeMode(column_index, QHeaderView.Stretch)  # Ajuste la taille de la section
        header.setStyleSheet(f"QHeaderView::section:nth-child({column_index + 1}) {{ background-color: {color}; }}")   

    @staticmethod
    def style_table_headers(table: QTableWidget,target_column: int):
        """Apply styles to table headers."""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.HEADER_STYLE)
        header.setSectionResizeMode(QHeaderView.Interactive)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)

        """Apply styles to table headers with one column highlighted."""
        #custom_header = CustomHeader(Qt.Horizontal, table, target_column=target_column)
        #table.setHorizontalHeader(custom_header)
        #header.setSectionResizeMode(QHeaderView.ResizeToContents)  # Ajuste les colonnes au contenu
        header.setStretchLastSection(True)  # Étend la dernière colonne pour remplir l'espace disponible
        table.resizeRowsToContents()

        #table.setHorizontalHeaderLabels(["GOs"])

    HEADER_STYLE2 = """
        background-color: #077187;  /* hits */
            color: #333333;
            font : Roboto;
            font-weight: bold;
            font-size: 12px ;
    """    

        


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


    @staticmethod
    def style_table_data(table: QTableWidget):
            """Apply style to table data cells."""
            table.setStyleSheet(DataTableManager.TABLE_STYLE)

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


            # Ajout du tooltip en fonction du type de tag
            if tag_type == "blast":
                label.setToolTip("Résultats Blast (alignement avec les bases de données).")
            elif tag_type == "interpro":
                label.setToolTip("Résultats InterPro (classification fonctionnelle).")
            else:
                label.setToolTip("Résultats de GO ontologie.")

            tag_layout.addWidget(label)

        tag_widget.setLayout(tag_layout)
        return tag_widget

    @staticmethod
    def create_icon_widget(tag):
        """an icon for classification """
        icon_widget = QWidget()
        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(QPixmap(DataTableManager.ICON_PATHS[tag]).scaled(16, 16, Qt.KeepAspectRatio))

        icon_layout.addWidget(icon_label)
        icon_widget.setLayout(icon_layout)
        return icon_widget
    


 
    def populate_table(table: QTableWidget, parsed_results: list):
        """Populate the table with data."""
        if not isinstance(parsed_results, list) or not all(isinstance(result, dict) for result in parsed_results):
            raise ValueError("parsed_results should be a list of dictionaries.")

        column_headers = [
            "Protein ID", "Description","Length", "Tags",
            "Definition", "PFAMs", "GOs", "Classification",
            "Preferred name", "COG", "Enzyme","InterPro"
        ]
        table.setColumnCount(len(column_headers))
        table.setHorizontalHeaderLabels(column_headers)
        table.setRowCount(len(parsed_results))


        for row_idx, result in enumerate(parsed_results):
            prot_id = result.get("query_id", "N/A")
            prot_length = result.get("query_len", 0)
            eggnog_annotations = result.get("eggNOG_annotations", [])
            eggnog_annotation = eggnog_annotations[0].get("Description", "N/A") if eggnog_annotations else "N/A"
            query_def = result.get("query-def", "N/A")
            PFAMs = eggnog_annotations[0].get("PFAMs", "N/A") if eggnog_annotations else "N/A"
            preferred_name = eggnog_annotations[0].get("Preferred_name", "N/A") if eggnog_annotations else "N/A"
            cog_category = eggnog_annotations[0].get("COG_category", "N/A") if eggnog_annotations else "N/A"
            ec_number = eggnog_annotations[0].get("EC", "N/A") if eggnog_annotations else "N/A"
            gos = eggnog_annotations[0].get("GOs", "").split(',') if eggnog_annotations else []
            Interpro = result.get("InterproScan_annotation", [])
            #Interpro_annotation = Interpro[0].get("interpro", "N/A") if Interpro else "N/A"

            current_interpro_annotations = [
                interpro.get("interpro", "") for interpro in Interpro]


            go_terms_display = gos[:7]  # Limitez à 7 termes si nécessaire
            if len(gos) > 7:
                go_terms_display.append("...")  # Ajouter "..." si plus de termes
            """go_label = QLabel()
            go_terms_display = gos[:7]  # Affiche les 7 premiers termes
            if len(gos) > 7:
                go_terms_display.append("...")  # Ajoute '...' si la liste est trop longue

            go_label.setText("\n".join(go_terms_display))
            go_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Aligne le contenu en haut à gauche
            go_label.setStyleSheet("""
                #font-family: 'Roboto', sans-serif;
                #font-size: 12px;
                #color: #333;
                #background-color: #f9f9f9;
                #padding: 5px;
                #border-radius: 3px;
            """)
            #table.setCellWidget(row_idx, 6, go_label)"""
            # Create a QLabel for GO terms
            go_label = QLabel("\n".join(go_terms_display))  # Join terms with line breaks
            go_label.setWordWrap(True)  # Enable word wrapping if needed

            table.setRowHeight(row_idx, 100)  # Augmenter la hauteur (ajustez si besoin)

            go_label.setStyleSheet("""
                font-family: 'Roboto', sans-serif;
                font-size: 12px;
                color: #333;
                background-color: #FFEBE1;
                padding: 5px;

            """)
            go_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)




            #les ID InterPro
            IPR_label = QLabel("\n".join(current_interpro_annotations))  # Join terms with line breaks
            IPR_label.setWordWrap(True)  # Enable word wrapping if needed

            IPR_label.setStyleSheet("""
                font-family: 'Roboto', sans-serif;
                font-size: 12px;
                color: #333;
                background-color: #CACCE4; 
                padding: 5px;
            """)# 8083B5 couleur à tester pour bck
            IPR_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            tags = []
            if len(gos) > 0:
                tags.append(("go", len(gos)))

            if len(result.get("InterproScan_annotation", [])) > 0:
                tags.append(("interpro", len(result.get("InterproScan_annotation", []))))
            if len(result.get("blast_hits", [])) > 0:
                tags.append(("blast", len(result.get("blast_hits", []))))

            classification_tag = "classified" if len(gos) > 10 else "unclassified"

            row_data = [
                prot_id, eggnog_annotation, prot_length, tags,
                query_def, PFAMs, None, classification_tag,
                preferred_name, cog_category,f"EC:{ec_number}",None
            ]

            for col_idx, value in enumerate(row_data):
                if col_idx == 3:
                    table.setCellWidget(row_idx, col_idx, DataTableManager.create_tag_widget(value))
                elif col_idx == 7:
                    table.setCellWidget(row_idx, col_idx, DataTableManager.create_icon_widget(value))
                elif col_idx == 6:
                    table.setCellWidget(row_idx, col_idx, go_label)
                elif col_idx == 11:
                    table.setCellWidget(row_idx, col_idx, IPR_label)                    
                else:
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        # Ajustement de la largeur des colonnes
        for col_idx, header in enumerate(column_headers):
            if header == "Length":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 50)  # Fixe la largeur à 50px
            elif header == "COG":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 50)  # Fixe la largeur à 50px    
            elif header == "Enzyme":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 80)  # Fixe la largeur à 50px    
            elif header == "Classification":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 80)  # Fixe la largeur à 50px   
            elif header == "Protein ID":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 130)  # Fixe la largeur à 50px           
            elif header == "Description":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 250)  # Fixe la largeur à 50px       
            elif header == "GOs":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 100)  # Fixe la largeur à 50px   
            elif header == "InterPro":  # Si l'en-tête correspond à "Protein Length"
                table.setColumnWidth(col_idx, 100)  # Fixe la largeur à 50px                          
            else:
                table.setColumnWidth(col_idx, 150)  # Largeur par défaut pour les autres colonnes





    def populate_additional_table(table: QTableWidget, parsed_results: list):
        """Populates a table with parsed results for additional data."""
        addTable_column_headers = [
            "Hit id", "definition", "accession", "identity", "Alignment length", "E_value", "Bit_score",
            "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
        ]
        table.setHorizontalHeaderLabels(addTable_column_headers)

        total_hits = sum(len(result["blast_hits"]) for result in parsed_results)
        table.setRowCount(total_hits)

              # Apply table data styling
        #DataTableManager.style_table_data(table)

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
                hsp_bitScore = hsp[0].get("bit_score", "N/A")

                row_data = [
                    hit["hit_id"],  # hit_id
                    hit["hit_def"],  # hit_def
                    chunked_value,  # accession
                    (float(hit["percent_identity"]) / float(hit["alignment_length"])) * 100,  # percent_identity
                    hit["alignment_length"],  # alignment_length
                    hit["e_value"],  # e_value
                    hit["bit_score"],  # bit_score
                    query_start,  # Query Start
                    query_end,  # Query End
                    subject_start,  # Subject Start
                    subject_end,  # Subject End
                    hsp_bitScore
                ]

                for col_idx, value in enumerate(row_data):
                        
                    if col_idx == 3:  # percent_identity column with progress bar
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
                        item.setBackground(QBrush(QColor("#A8D8DE")))  
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
            signature = InterproScan_annotation[0].get("signature", "N/A") if InterproScan_annotation else "N/A"
            
            #signature = InterproScan_annotation[0].get("signature", "N/A") if InterproScan_annotation else "N/A"
            #ac = signature[0].get("ac", "N/A") if InterproScan_annotation else "N/A"
            #name = signature[0].get("name", "N/A") if InterproScan_annotation else "N/A"
            #desc = signature[0].get("desc", "N/A") if InterproScan_annotation else "N/A"



            


            


            row_data = [
                domain,code,methode,method_id,description,status,interpro,interpro_description,type
            ]



            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                table.setItem(row_idx, col_idx, item)

        #largeur des colonnes
        for col_idx, header in enumerate(table_column_headers):
            table.setColumnWidth(col_idx, 150)

