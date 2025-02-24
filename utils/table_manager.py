from PySide6.QtWidgets import QTableView,QTableWidget,QTableWidgetItem, QLabel, QWidget, QHeaderView, QProgressBar, QHBoxLayout
from PySide6.QtGui import QPixmap, QColor,QBrush
from PySide6.QtCore import Qt
import logging
import traceback

COLUMN_CONFIG = {
    "main": {
        "Length": 50, "COG": 50, "Enzyme": 80,
        "Classification": 80, "Protein ID": 130,
        "Description": 250, "InterPro": 100,
        "Preferred name": 100
    },
    "blast": {
        "hit_id": 100, "percent_identity": 120
    }
}

MAIN_HEADERS = [
    "Protein ID", "Description", "Length", "Results",
    "PFAMs", "GO", "Classification",
    "Preferred name", "COG", "Enzyme", "InterPro"
]

BLAST_HEADERS = [
    "Hit id", "Definition", "Accession", "Identity", 
    "Alignment length", "E-value", "Bit-score",
    "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
]

INTERPRO_HEADERS = [
    "InterPro ID", "Description", "Start", "End", "E-value"
]

class DataTableManager:
    ICON_PATHS = {
        "classified": "assets/settings.png",
        "unclassified": "assets/edit.png"
    }

    COLUMN_CONFIG = {
    "main": {
        "Length": 50, "COG": 50, "Enzyme": 80,
        "Classification": 80, "Protein ID": 130,
        "Description": 250, "InterPro": 100,
        "Preferred name": 100
    },
    "blast": {
        "hit_id": 100, "percent_identity": 120
    }
}

    HEADER_STYLE = "QHeaderView::section { background-color: lightblue; font-weight: bold; }"
    STYLES = {
        "header": """
            QHeaderView::section {
                background-color: #D7D7D7;
                color: #333333;
                font-family: Roboto;
                font-weight: bold;
                font-size: 12px;
            }
        """,
        "go": """
            font-family: 'Roboto'; font-size: 12px;
            color: #333; background-color: #FFEBE1;
            padding: 5px;
        """,
        "interpro": """
            font-family: 'Roboto'; font-size: 12px;
            color: #333; background-color: #CACCE4; 
            padding: 5px;
        """,
        "tag": {
            "blast": "background-color: #077187; color: white;",
            "interpro": "background-color: #4F518C; color: white;",
            "default": "background-color: #ED7D3A; color: white;"
        }
    }
    TAG_STYLES = {
        "blast": "background-color: #077187; color: white;",
        "interpro": "background-color: #4F518C; color: white;",
        "default": "background-color: #ED7D3A; color: white;"
    }

    @staticmethod
    def process_batch(items, go_definitions=None):
        """Process a batch of items and return their data"""
        processed_data = []
        for item in items:
            row_data = DataTableManager._process_main_row(item, go_definitions)
            processed_data.append(row_data)
        return processed_data

    @staticmethod
    def _process_main_row(row_data, go_definitions):
        """Prepare data for a table row"""
        try:
            eggnog_annotations = row_data.get("eggNOG_annotations", [])
            eggnog = eggnog_annotations[0] if eggnog_annotations else {}
            interpro = row_data.get("InterproScan_annotation", [{}])
            tags = []
            gos = eggnog_annotations[0].get("GOs", "").split(',') if eggnog_annotations else []

            if len(gos) > 0:
                tags.append(("go", len(gos)))
            if len(row_data.get("InterproScan_annotation", [])) > 0:
                tags.append(("interpro", len(row_data.get("InterproScan_annotation", []))))
            if len(row_data.get("blast_hits", [])) > 0:
                tags.append(("blast", len(row_data.get("blast_hits", []))))

            # Prepare display data
            display_data = {
                "Protein ID": row_data.get("query_id", "N/A"),
                "Description": eggnog.get("Description", "N/A"),
                "Length": row_data.get("query_len", 0),
                "Results": tags,  # Directly assign tags here
                "PFAMs": eggnog.get("PFAMs", "N/A"),
                "GO": DataTableManager._process_go_terms(eggnog.get("GOs", ""), go_definitions),
                "Classification": "classified" if len(eggnog.get("GOs", "").split(',')) > 10 else "unclassified",
                "Preferred name": eggnog.get("Preferred_name", "N/A"),
                "COG": eggnog.get("COG_category", "N/A"),
                "Enzyme": f"EC:{eggnog.get('EC', 'N/A')}",
                "InterPro": DataTableManager._process_interpro(interpro)
            }

            #logging.debug(f"Processed row data: {display_data}")

            # Create widgets directly
            widget_data = {
                "Results": DataTableManager.create_tag_widget(display_data["Results"]),
                #"GO": DataTableManager._create_go_widget(display_data["GO"]),
                #"Classification": DataTableManager._create_icon_widget(display_data["Classification"]),
                #"InterPro": DataTableManager._create_interpro_widget(display_data["InterPro"])
            }

            #logging.debug(f"Widget data: {widget_data}")

            return {"display": display_data, "widgets": widget_data}
        except Exception as e:
            #logging.error(f"Error processing row data: {e}")
            traceback.print_exc()
            return {"display": {}, "widgets": {}}

    @staticmethod
    def _process_go_terms(gos_str, go_definitions):
        """Process GO terms for display"""
        return gos_str.split(',')[:7]

    @staticmethod
    def _process_interpro(interpro_data):
        """Process InterPro data for display"""
        return [item.get("interpro_description", "") for item in interpro_data if "interpro_description" in item]

    @staticmethod
    def _prepare_tags(row_data):
        """Prepare tags for display"""
        tags = []
        ##logging.debug(f"Row data for tags: {row_data}")
        if row_data.get("blast_hits"):
            tags.append(("blast", str(len(row_data["blast_hits"]))))
        if row_data.get("InterproScan_annotation"):
            tags.append(("interpro", str(len(row_data["InterproScan_annotation"]))))
        #logging.debug(f"Tags created: {tags}")
        return tags

    @staticmethod
    def create_widget(widget_type, data):
        """Create widget based on type and data"""
        #logging.debug(f"Creating widget of type {widget_type} with data: {data}")

        if widget_type == "tags":
            return DataTableManager._create_tags_widget(data)
        elif widget_type == "go":
            return DataTableManager._create_go_widget(data)
        elif widget_type == "icon":
            return DataTableManager._create_icon_widget(data)
        elif widget_type == "interpro":
            return DataTableManager._create_interpro_widget(data)
        return None

    @staticmethod
    def create_table(table_type: str) -> QTableView:
        """Crée un tableau selon le type spécifié"""
        table = QTableView()
        
        if table_type == 'main':
            headers = MAIN_HEADERS
        elif table_type == 'blast':
            headers = BLAST_HEADERS
        elif table_type == 'interpro':
            headers = INTERPRO_HEADERS
        else:
            raise ValueError(f"Unknown table type: {table_type}")

        model = VirtualTableModel([], headers)

        table.setModel(model)
        DataTableManager.style_table_headers(table)
        
        return table

    @staticmethod
    def style_table_headers(table: QTableView, target_column: int = None):
        """Style les en-têtes du tableau"""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.STYLES["header"])
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        
        if target_column is not None:
            header.setSectionResizeMode(target_column, QHeaderView.Stretch)

    @staticmethod
    def style_AdditionalTable_headers(table: QTableWidget):
        """Style les en-têtes du tableau additionnel"""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.STYLES["header"])
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

    @staticmethod
    def style_IprscanTable_headers(table: QTableWidget):
        """Style les en-têtes du tableau IPRscan"""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.STYLES["header"])
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

    @staticmethod
    def populate_additional_table(table: QTableWidget, parsed_results: list):
        """Remplit une table avec les résultats analysés pour les informations sur les hits."""
        try:
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

                    try:
                        percent_identity = float(hit["percent_identity"]) if hit["percent_identity"] is not None else 0.0
                        alignment_length = float(hit["alignment_length"]) if hit["alignment_length"] is not None else 1.0  # Éviter la division par zéro
                        percent_identity_value = (percent_identity / alignment_length) * 100
                    except (ValueError, ZeroDivisionError):
                        percent_identity_value = 0.0  # Valeur par défaut appropriée

                    row_data = [
                        hit["hit_id"],  # hit_id
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
                table.setColumnWidth(col_idx, 100)
        except Exception as e:
            #logging.error(f"Error populating additional table: {e}")
            traceback.print_exc()

    @staticmethod
    def populate_interproscan_table(table: QTableWidget, interproscan_results: list):
        """Populates a table with InterProScan annotation results."""
        try:
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
                signature = result.get("signature", {"ac": "N/A", "name": "N/A", "desc": "N/A"})
                ac = signature.get("ac", "N/A")
                name = signature.get("name", "N/A")
                desc = signature.get("desc", "N/A")

                row_data = [
                    domain, code, methode, method_id, description, status, interpro, interpro_description, type, ac, name, desc
                ]

                for col_idx, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)

            # columns width
            for col_idx, header in enumerate(table_column_headers):
                table.setColumnWidth(col_idx, 150)
        except Exception as e:
            #logging.error(f"Error populating InterProScan table: {e}")
            traceback.print_exc()

    @staticmethod
    def populate_GO_table(table: QTableWidget, GO_results: list):
        """Populates a QTableWidget with GO annotation results."""
        try:
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
        except Exception as e:
            #logging.error(f"Error populating GO table: {e}")
            traceback.print_exc()

  
 
    

    @staticmethod
    def create_tag_widget(tags):
        """ styled tags """
        #logging.debug(f"Creating tags widget with tags: {tags}")
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
        #logging.debug(f"Created tag widget: {tag_widget}")
        return tag_widget



    @staticmethod
    def create_icon_widget(tag):
        """Crée un widget d'icône"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        pixmap = QPixmap(DataTableManager.ICON_PATHS[tag])
        label = QLabel()
        label.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio))
        layout.addWidget(label)
        
        return widget

    @staticmethod
    def populate_table(table: QTableView, parsed_results: list, go_definitions: dict):
        """Peuple le tableau principal de manière optimisée"""
        from model.data_model import VirtualTableModel  # Importation déplacée ici
        try:
            #logging.debug("Starting to populate table")
            table.setUpdatesEnabled(False)
            
            # Préparation des données
            processed_data = [
                DataTableManager._process_main_row(row, go_definitions)
                for row in parsed_results
            ]
            #logging.debug(f"Processed data: {processed_data}")
            
            # Configuration
            headers = MAIN_HEADERS
            data = [data["display"] for data in processed_data]
            model = VirtualTableModel(data, headers)
            
            model.widgets = {(row_idx, col_idx): widget
                            for row_idx, data in enumerate(processed_data)
                            for col_idx, widget in enumerate(data["widgets"].values())}
            #logging.debug(f"Widgets created: {model.widgets}")
            table.setModel(model)
            #logging.debug("Table model updated")
            
            # Configuration finale
            DataTableManager._apply_table_config(table, 'main')
            #logging.debug("Table configuration applied")

        except Exception as e:
            #logging.error(f"Error populating table: {e}")
            traceback.print_exc()
        finally:
            table.setUpdatesEnabled(True)

    @staticmethod
    def _apply_table_config(table, table_type):
        """Applique la configuration des colonnes"""
        config = DataTableManager.COLUMN_CONFIG.get(table_type, {})

        # 1. Create a mapping of column names to indices:
        column_name_to_index = {}
        for i in range(table.model().columnCount()):
            header_item = table.model().headerData(i, Qt.Horizontal, Qt.DisplayRole)
            if header_item is not None:  # Important check!
                column_name_to_index[header_item] = i
            else:
                print(f"No header item found at index {i}. Skipping this column.")
                continue  # Skip to the next column if no header item

        for col_name, width in config.items():  # Iterate through column NAMES
            col_index = column_name_to_index.get(col_name)  # Get the INDEX
            if col_index is not None:  # Check if the column exists
                try:
                    if isinstance(width, int):
                        table.setColumnWidth(col_index, width)  # Use the INDEX
                    else:
                        try:
                            width = float(width)
                            table.setColumnWidth(col_index, int(width))  # Use the INDEX
                        except ValueError:
                            print(f"Invalid width '{width}' for column {col_name}. Setting to default (100).")
                            table.setColumnWidth(col_index, 100)  # Use the INDEX
                except (ValueError, TypeError):  # This should now be very rare
                    print(f"Error processing width for column {col_name}. Setting to default (100).")
                    table.setColumnWidth(col_index, 100)  # Use the INDEX
            else:
                print(f"Column '{col_name}' not found in the table. Skipping.")

        table.resizeRowsToContents()

    @staticmethod
    def parse_enzyme_file(file_path):
        """Parse the enzyme file and return a dictionary."""
        enzyme_dict = {}
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    parts = line.strip().split('\t')
                    if len(parts) == 2:
                        enzyme_dict[parts[0]] = parts[1]
        except Exception as e:
            print(f"Error parsing enzyme file: {e}")
        return enzyme_dict