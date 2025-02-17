from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, 
    QWidget, QHeaderView, QProgressBar
)
from PySide6.QtGui import QPixmap, QColor, QBrush
from PySide6.QtCore import Qt
import itertools

class DataTableManager:
    ICON_PATHS = {
        "classified": "assets/settings.png",
        "unclassified": "assets/edit.png"
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

    @staticmethod
    def _batch_process(iterable, batch_size=500):
        """Générateur pour le traitement par lots"""
        it = iter(iterable)
        while True:
            batch = list(itertools.islice(it, batch_size))
            if not batch:
                break
            yield batch

    @staticmethod
    def create_table(table_type: str) -> QTableWidget:
        """Crée un tableau selon le type spécifié"""
        table = QTableWidget()
        
        if table_type == 'main':
            headers = [
                "Protein ID", "Description", "Length", "Results",
                "PFAMs", "GO", "Classification",
                "Preferred name", "COG", "Enzyme", "InterPro"
            ]
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            DataTableManager.style_table_headers(table)
        
        elif table_type == 'blast':
            headers = [
                "Hit id", "Definition", "Accession", "Identity", 
                "Alignment length", "E-value", "Bit-score",
                "QStart", "QEnd", "sStart", "sEnd", "Hsp bit score"
            ]
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            DataTableManager.style_AdditionalTable_headers(table)
        
        return table
    @staticmethod
    def _create_table_item(value, background=None):
        """Création optimisée d'items de tableau"""
        item = QTableWidgetItem(str(value))
        if background:
            item.setBackground(background)
        return item

    @staticmethod
    def style_table_headers(table: QTableWidget, target_column: int = None):
        """Style les en-têtes du tableau"""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.STYLES["header"])
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        
        if target_column is not None:
            header.setSectionResizeMode(target_column, QHeaderView.Stretch)

    @staticmethod
    def create_tag_widget(tags):
        """Crée un widget de tags stylisés"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)

        for tag_type, value in tags:
            label = QLabel(str(value))
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(35, 18)
            style = DataTableManager.STYLES["tag"].get(tag_type, DataTableManager.STYLES["tag"]["default"])
            label.setStyleSheet(f"{style} border-radius: 5px; padding: 3px;")
            layout.addWidget(label)

        return widget

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
    def populate_table(table: QTableWidget, parsed_results: list, go_definitions: dict):
        """Peuple le tableau principal de manière optimisée"""
        try:
            table.setUpdatesEnabled(False)
            table.clearContents()
            
            # Préparation des données
            processed_data = [
                DataTableManager._process_main_row(row, go_definitions)
                for row in parsed_results
            ]
            
            # Configuration
            table.setRowCount(len(processed_data))
            table.setColumnCount(11)
            
            # Peuplement par lots
            for batch in DataTableManager._batch_process(enumerate(processed_data)):
                for row_idx, (data, widgets) in batch:
                    # Colonnes standards
                    for col_idx in [0, 1, 2, 4, 7, 8, 9]:
                        table.setItem(row_idx, col_idx, DataTableManager._create_table_item(data[col_idx]))
                    
                    # Colonnes spéciales
                    table.setCellWidget(row_idx, 3, widgets['tags'])
                    table.setCellWidget(row_idx, 5, widgets['go'])
                    table.setCellWidget(row_idx, 6, widgets['icon'])
                    table.setCellWidget(row_idx, 10, widgets['interpro'])

            # Configuration finale
            DataTableManager._apply_table_config(table, 'main')

        finally:
            table.setUpdatesEnabled(True)

    @staticmethod
    def _process_main_row(row_data, go_definitions):
        """Prépare les données pour une ligne du tableau principal"""
        #eggnog = row_data.get("eggNOG_annotations", [{}])[0]

        eggnog_annotations = row_data.get("eggNOG_annotations", [])
        if eggnog_annotations:  # Si la liste n'est pas vide
            eggnog = eggnog_annotations[0]
        else:
            eggnog = {}
        interpro = row_data.get("InterproScan_annotation", [{}])

        base_data = [
            row_data.get("query_id", "N/A"),
            eggnog.get("Description", "N/A"),
            row_data.get("query_len", 0),
            DataTableManager._prepare_tags(row_data),
            eggnog.get("PFAMs", "N/A"),
            None,
            "classified" if len(eggnog.get("GOs", "").split(',')) > 10 else "unclassified",
            eggnog.get("Preferred_name", "N/A"),
            eggnog.get("COG_category", "N/A"),
            f"EC:{eggnog.get('EC', 'N/A')}",
            None
        ]

        widgets = {
            'tags': DataTableManager.create_tag_widget(base_data[3]),
            'go': DataTableManager._create_go_widget(eggnog.get("GOs", ""), go_definitions),
            'icon': DataTableManager.create_icon_widget(base_data[6]),
            'interpro': DataTableManager._create_interpro_widget(interpro)
        }

        return base_data, widgets

    @staticmethod
    def _create_go_widget(gos_str, go_definitions):
        """Crée le widget GO avec mise en forme"""
        gos = gos_str.split(',')[:7]
        content = []
        
        for go_id in gos:
            desc, go_type = go_definitions.get(go_id, ("No description", ""))
            content.append(f"<p>{go_id} - <b>{go_type}</b> - {desc}</p>")
        
        if len(gos_str.split(',')) > 7:
            content.append("<p>...</p>")

        label = QLabel("".join(content))
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet(DataTableManager.STYLES["go"])
        return label

    @staticmethod
    def _create_interpro_widget(data):
        """Crée le widget InterPro"""
        annotations = [ip.get("interpro", "") for ip in data]
        label = QLabel("\n".join(filter(None, annotations)))
        label.setStyleSheet(DataTableManager.STYLES["interpro"])
        return label

    def _apply_table_config(table, table_type):
        """Applique la configuration des colonnes"""
        config = DataTableManager.COLUMN_CONFIG.get(table_type, {})

        # 1. Create a mapping of column names to indices:
        column_name_to_index = {}
        for i in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(i)
            if header_item is not None:  # Important check!
                header_text = header_item.text()
                column_name_to_index[header_text] = i
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
    def populate_additional_table(table: QTableWidget, parsed_results: list):
        """Peuple le tableau des résultats BLAST"""
        try:
            table.setUpdatesEnabled(False)
            all_hits = []
            
            # Collecte des hits
            for result in parsed_results:
                all_hits.extend(result.get("blast_hits", []))
            
            # Configuration
            table.setRowCount(len(all_hits))
            table.clearContents()
            
            # Peuplement optimisé
            for batch in DataTableManager._batch_process(enumerate(all_hits)):
                for row_idx, hit in batch:
                    identity = DataTableManager._calculate_identity(hit)
                    
                    # Progress bar
                    progress = QProgressBar()
                    progress.setValue(int(identity))
                    progress.setStyleSheet(
                        f"QProgressBar::chunk {{background-color: {DataTableManager._get_identity_color(identity)};}}"
                    )
                    
                    # Données
                    row_data = [
                        hit.get("hit_id", "N/A"),
                        hit.get("hit_def", "N/A"),
                        hit.get("accession", "N/A").split("[[taxon")[0].strip(),
                        identity,
                        hit.get("alignment_length", "N/A"),
                        hit.get("e_value", "N/A"),
                        hit.get("bit_score", "N/A"),
                        hit.get("query_positions", {}).get("start", "N/A"),
                        hit.get("query_positions", {}).get("end", "N/A"),
                        hit.get("subject_positions", {}).get("start", "N/A"),
                        hit.get("subject_positions", {}).get("end", "N/A"),
                        hit.get("hsps", [{}])[0].get("bit_score", "N/A")
                    ]
                    
                    # Peuplement
                    for col_idx, value in enumerate(row_data):
                        if col_idx == 3:
                            table.setCellWidget(row_idx, col_idx, progress)
                        else:
                            table.setItem(row_idx, col_idx, DataTableManager._create_table_item(value))

            # Configuration finale
            DataTableManager._apply_table_config(table, 'blast')

        finally:
            table.setUpdatesEnabled(True)

    @staticmethod
    def _calculate_identity(hit):
        """Calcule le pourcentage d'identité"""
        try:
            identity = float(hit.get("percent_identity", 0))
            length = float(hit.get("alignment_length", 1)) or 1
            return (identity / length) * 100
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _get_identity_color(value):
        """Détermine la couleur de la progress bar"""
        if value > 90:
            return "#8FE388"
        elif value < 70:
            return "#E3AE88"
        return "#88BCE3"

    @staticmethod
    def populate_interproscan_table(table: QTableWidget, results: list):
        """Peuple le tableau InterProScan"""
        try:
            table.setUpdatesEnabled(False)
            table.clearContents()
            
            # Préparation des données
            processed_data = []
            for result in results:
                interpro = result.get("InterproScan_annotation", [{}])[0]
                signature = interpro.get("signature", {})
                processed_data.append([
                    interpro.get("domain_id", "N/A"),
                    interpro.get("code", "N/A"),
                    interpro.get("method", "N/A"),
                    interpro.get("method_id", "N/A"),
                    interpro.get("description", "N/A"),
                    interpro.get("status", "N/A"),
                    interpro.get("interpro", "N/A"),
                    interpro.get("interpro_description", "N/A"),
                    interpro.get("type", "N/A"),
                    signature.get("ac", "N/A"),
                    signature.get("name", "N/A"),
                    signature.get("desc", "N/A")
                ])
            
            # Peuplement
            table.setRowCount(len(processed_data))
            for batch in DataTableManager._batch_process(enumerate(processed_data)):
                for row_idx, data in batch:
                    for col_idx, value in enumerate(data):
                        table.setItem(row_idx, col_idx, DataTableManager._create_table_item(value))

            # Configuration
            table.resizeColumnsToContents()

        finally:
            table.setUpdatesEnabled(True)

    @staticmethod
    def populate_GO_table(table: QTableWidget, go_terms: list):
        """Peuple le tableau des termes GO"""
        try:
            table.setUpdatesEnabled(False)
            table.clearContents()
            
            # Préparation des données
            processed_data = []
            for term in go_terms:
                processed_data.append([
                    term.get("id", ""),
                    term.get("name", ""),
                    term.get("namespace", ""),
                    term.get("def", ""),
                    term.get("comment", ""),
                    "; ".join(term.get("synonym", [])),
                    "; ".join(term.get("is_a", [])),
                    term.get("is_obsolete", ""),
                    "; ".join(term.get("relationship", [])),
                    "; ".join(term.get("xref", []))
                ])
            
            # Peuplement
            table.setRowCount(len(processed_data))
            for batch in DataTableManager._batch_process(enumerate(processed_data)):
                for row_idx, data in batch:
                    for col_idx, value in enumerate(data):
                        item = DataTableManager._create_table_item(value)
                        if col_idx == 0:
                            item.setBackground(QColor("#FFEBE1"))
                        table.setItem(row_idx, col_idx, item)

            # Configuration
            table.resizeColumnsToContents()

        finally:
            table.setUpdatesEnabled(True)

    @staticmethod
    def _prepare_tags(row_data):
        """Prépare les tags pour la colonne 'Results'"""
        tags = []
        if "blast_results" in row_data:
            tags.append(("blast", "BLAST"))
        if "interpro_results" in row_data:
            tags.append(("interpro", "InterPro"))
        if not tags:
            tags.append(("default", "N/A"))
        return tags

    @staticmethod
    def style_AdditionalTable_headers(table):
        """Apply styles to table headers."""
        header = table.horizontalHeader()
        header.setStyleSheet(DataTableManager.HEADER_STYLE)
        header.setSectionResizeMode(QHeaderView.Interactive)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        header.setStretchLastSection(True)  # Expands the last column to fill available space
        table.resizeRowsToContents()