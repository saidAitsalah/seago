import sys
import os
#adding model Path because its not recognised by the system
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'model')))
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem,QTableView, QHBoxLayout, QLabel, 
    QWidget, QHeaderView, QProgressBar
)
from PySide6.QtGui import QPixmap, QColor, QBrush
from PySide6.QtCore import Qt,QModelIndex
import itertools
from model.data_model import VirtualTableModel,WidgetDelegate
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

    COLUMN_CONFIG = {
        "main": {
            "Length": 50, "COG": 50, "Enzyme": 80,
            "Classification": 80, "Protein ID": 130,
            "Description": 250, "InterPro": 100,
            "Preferred name": 100
        }
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
        # Handle None input
        if row_data is None:
            return {
                "display": {
                    "Protein ID": "N/A",
                    "Description": "N/A",
                    "Length": 0,
                    "Results": [("default", "N/A")],
                    "PFAMs": "N/A",
                    "GO": [],
                    "Classification": "unclassified",
                    "Preferred name": "N/A",
                    "COG": "N/A",
                    "Enzyme": "EC:N/A",
                    "InterPro": []
                },
                "widgets": {
                    "Results": {"type": "tags", "data": [("default", "N/A")]},
                    "GO": {"type": "go", "data": []},
                    "Classification": {"type": "icon", "data": "unclassified"},
                    "InterPro": {"type": "interpro", "data": []}
                }
            }
        
        # Check if row_data is a string (which is causing the error)
        if isinstance(row_data, str):
            # Handle string case - create a basic display object
            return {
                "display": {
                    "Protein ID": "Error",
                    "Description": row_data[:100] if len(row_data) > 100 else row_data,
                    "Length": "0",
                    "Results": [("default", "Error")],
                    "PFAMs": "",
                    "GO": [],
                    "Classification": "unclassified",
                    "Preferred name": "",
                    "COG": "",
                    "Enzyme": "",
                    "InterPro": []
                },
                "widgets": {
                    "Results": {"type": "tags", "data": [("default", "Error")]},
                    "GO": {"type": "go", "data": []},
                    "InterPro": {"type": "interpro", "data": []}
                }
            }
        
        # Check which JSON format we have
        if "PROTID" in row_data:
            # Format from table_data.json
            protein_id = row_data.get("PROTID", "N/A")
            description = row_data.get("Annot", "N/A")
            length = row_data.get("Prot Length", "0")
            hits = row_data.get("Hits", "0")
            interpro = row_data.get("InterPro Domain", "")
            gos = row_data.get("GOs", "")
            classification = "classified" if row_data.get("Classification") else "unclassified"
            
            # Create tags based on hit count
            tags = []
            if hits and hits != "0":
                tags.append(("blast", str(hits)))
            if interpro:
                tags.append(("interpro", "Yes"))
            if not tags:
                tags.append(("default", "N/A"))
                
            # Prepare display data for table_data.json format
            display_data = {
                "Protein ID": protein_id,
                "Description": description,
                "Length": length,
                "Results": tags,
                "PFAMs": "N/A",
                "GO": DataTableManager._process_go_terms(gos, go_definitions),
                "Classification": classification,
                "Preferred name": protein_id,  # Use PROTID as preferred name
                "COG": "N/A",
                "Enzyme": "EC:N/A",
                "InterPro": interpro.split(",") if interpro else []
            }
        else:
            # Original format (used by your current code)
            eggnog_annotations = row_data.get("eggNOG_annotations", [])
            eggnog = eggnog_annotations[0] if eggnog_annotations else {}
            interpro = row_data.get("InterproScan_annotation", [{}])

            # Extract tags
            tags = []
            if row_data.get("blast_hits"):
                tags.append(("blast", str(len(row_data["blast_hits"]))))
            if row_data.get("InterproScan_annotation"):
                tags.append(("interpro", str(len(row_data["InterproScan_annotation"]))))
            if not tags:
                tags.append(("default", "N/A"))

            # Original display data mapping
            display_data = {
                "Protein ID": row_data.get("query_id", "N/A"),
                "Description": eggnog.get("Description", "N/A"),
                "Length": row_data.get("query_len", 0),
                "Results": tags,
                "PFAMs": eggnog.get("PFAMs", "N/A"),
                "GO": DataTableManager._process_go_terms(eggnog.get("GOs", ""), go_definitions),
                "Classification": "classified" if len(eggnog.get("GOs", "").split(',')) > 10 else "unclassified",
                "Preferred name": eggnog.get("Preferred_name", "N/A"),
                "COG": eggnog.get("COG_category", "N/A"),
                "Enzyme": f"EC:{eggnog.get('EC', 'N/A')}",
                "InterPro": DataTableManager._process_interpro(interpro)
            }

        # Same widget data handling
        widget_data = {
            "Results": {"type": "tags", "data": display_data["Results"]},
            "GO": {"type": "go", "data": display_data["GO"]},
            "Classification": {"type": "icon", "data": display_data["Classification"]},
            "InterPro": {"type": "interpro", "data": display_data["InterPro"]}
        }

        # Add missing keys
        for key in ["Protein ID", "Description", "Length", "PFAMs", "Preferred name", "COG", "Enzyme"]:
            if key not in display_data:
                display_data[key] = "N/A"
            if key not in widget_data:
                widget_data[key] = {"type": "text", "data": display_data.get(key, "N/A")}

        return {"display": display_data, "widgets": widget_data}
    

    """****************************************helpers for processing main rows****************************"""

    @staticmethod
    def safe_text_for_widget(text):
        """Make text safe for display in widgets, avoiding font parsing issues"""
        if not text:
            return ""
        
        # Replace problematic characters that cause QFont parsing errors
        if isinstance(text, str) and (',' in text or ';' in text):
            # For text containing commas that cause font parsing errors
            return text.replace(',', '·').replace(';', '·')
        
        return str(text)

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
        """
        Prepare tags for display based on the provided row data.

        This function generates a list of tags based on the presence of specific keys
        in the input dictionary `row_data`. The tags are used for display purposes.

        Args:
            row_data (dict): A dictionary containing data for a row. Expected keys are:
                - "blast_hits": A list of blast hits.
                - "InterproScan_annotation": A list of InterproScan annotations.

        Returns:
            list: A list of tuples where each tuple contains a tag name and its corresponding count.
                  If no specific tags are found, a default tag ("default", "N/A") is returned.
        """
        logging.debug(f"Preparing tags ")
        tags = []
        if row_data.get("blast_hits"):
            tags.append(("blast", str(len(row_data["blast_hits"]))))
        if row_data.get("InterproScan_annotation"):
            tags.append(("interpro", str(len(row_data["InterproScan_annotation"]))))
        if not tags:
            tags.append(("default", "N/A"))
        return tags
    
    @staticmethod
    def _batch_process(iterable, batch_size=50):
        """Process items in batches to improve performance"""
        batch = []
        for item in iterable:
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
    
    """*******************************************************************************************************************"""
    
    #to review?
    @staticmethod
    def create_table(table_type: str) -> QTableWidget:
        """Crée un tableau selon le type spécifié"""
        table = QTableWidget()
        
        if table_type == 'main':
            headers = MAIN_HEADERS
        elif table_type == 'blast':
            headers = BLAST_HEADERS
        elif table_type == 'interpro':
            headers = INTERPRO_HEADERS
        else:
            raise ValueError(f"Unknown table type: {table_type}")

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        DataTableManager.style_table_headers(table)
        
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
    def add_batch_to_table(table, data_batch, go_definitions=None):
        """Add a batch of rows to the table without recreating the whole table"""
        go_definitions = go_definitions or {}
        
        for item in data_batch:
            if not isinstance(item, dict):
                print(f"Skipping non-dictionary item: {item}")
                continue
                
            base_data, widgets = DataTableManager._process_main_row(item, go_definitions)
            row_position = table.rowCount()
            table.insertRow(row_position)
            
            for col, value in enumerate(base_data):
                if isinstance(value, (str, int, float)) or value is None:
                    table.setItem(row_position, col, QTableWidgetItem(str(value or "")))
                elif col in widgets:
                    table.setCellWidget(row_position, col, widgets[col])

    @staticmethod
    def add_batch_to_table_view(table_view, data_batch, go_definitions=None):
        """Add a batch of rows to the QTableView efficiently"""
        logging.debug(f"Adding batch of {len(data_batch)} items to table")
        
        # Get the model
        model = table_view.model()
        if not model:
            logging.error("No model attached to table view")
            return
            
        # Ensure model has required attributes
        if not hasattr(model, 'widgets'):
            model.widgets = {}
        if not hasattr(model, 'widget_cells'):
            model.widget_cells = set()
            
        # Process the batch
        processed_data = DataTableManager.process_batch(data_batch, go_definitions)
        
        # Add rows in a single operation
        first_new_row = model.rowCount()
        model.beginInsertRows(QModelIndex(), first_new_row, first_new_row + len(processed_data) - 1)
        model._data.extend(processed_data)
        model.endInsertRows()
        
        # Only create widgets for visible rows
        visible_rect = table_view.viewport().rect()
        first_visible = table_view.rowAt(visible_rect.top())
        last_visible = table_view.rowAt(visible_rect.bottom())
        
        if first_visible < 0:
            first_visible = 0
        if last_visible < 0:
            last_visible = min(first_visible + 20, model.rowCount() - 1)
        
        # Create widgets only for visible rows
        for row in range(first_visible, last_visible + 1):
            if row < first_new_row:
                continue  # Skip already processed rows
            
            for col in range(model.columnCount()):
                index = model.index(row, col)
                table_view.update(index)
        
        # Update layout
        #table_view.resizeRowsToContents()
        table_view.viewport().update()

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

        #table.resizeRowsToContents()




    @staticmethod
    def populate_table(table: QTableView, parsed_results: list, go_definitions: dict):
        """Populate the main table using QTableView and VirtualTableModel"""
        # Process the data
        processed_data = []
        for i, row in enumerate(parsed_results):
            if not isinstance(row, dict):
                print(f"Row {i} is not a dictionary: {row}")
                raise ValueError("Each row in parsed_results must be a dictionary")
            processed_data.append(DataTableManager._process_main_row(row, go_definitions))
        
        # Configure table settings
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        
        # Create a custom model
        model = VirtualTableModel(processed_data, go_definitions)
        
        # Add widget_cells set to track which cells should use widgets
        model.widget_cells = set()
        
        # Set the model
        table.setModel(model)
        
        # Configure the delegate
        delegate = WidgetDelegate(table)
        table.setItemDelegate(delegate)
        
        #column_width
        for col_idx, header in enumerate(model.HEADERS):
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
            elif header == "GO": 
                table.setColumnWidth(col_idx, 300)     
            elif header == "InterPro":  
                table.setColumnWidth(col_idx, 100)
            elif header == "Preferred name":  
                table.setColumnWidth(col_idx, 100)                     
            else:
                table.setColumnWidth(col_idx, 150)

        table.verticalHeader().setDefaultSectionSize(120)  # Fixed height of 40px
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)        
        
        # Add widgets to table cells
        for row in range(model.rowCount()):
            row_data = model._data[row]
            widgets_data = row_data.get("widgets", {})
            
            for col, header in enumerate(model.HEADERS):
                # Look for matching widget info (case-insensitive)
                header_key = header.lower()
                matching_key = None
                for key in widgets_data.keys():
                    if key.lower() == header_key:
                        matching_key = key
                        break
                
                if not matching_key:
                    continue
                    
                widget_info = widgets_data[matching_key]
                widget_type = widget_info.get("type")
                widget_data = widget_info.get("data")
                
                if widget_type and widget_data is not None:
                    try:
                        widget = DataTableManager.create_widget(widget_type, widget_data, go_definitions)
                        if widget:
                            # Mark this cell to use widget instead of text
                            model.widget_cells.add((row, col))
                            
                            # Add the widget to the model and view
                            index = model.index(row, col)
                            model.widgets[(row, col)] = widget
                            table.setIndexWidget(index, widget)
                    except Exception as e:
                        logging.error(f"Error creating widget for cell ({row}, {col}): {e}")
        
        # Ensure proper display
        #table.resizeRowsToContents()
        table.viewport().update()
        logging.debug(f"Table populated with {len(processed_data)} rows")
        
        # Patch the model's data method to prevent overlap
        original_data_method = model.data
        
        def patched_data(index, role=Qt.DisplayRole):
            if not index.isValid():
                return None
                
            row, col = index.row(), index.column()
            
            # For display role, return empty string for cells with widgets
            if role == Qt.DisplayRole and (row, col) in model.widget_cells:
                return ""
                
            # For all other roles, use the original method
            return original_data_method(index, role)
            
        model.data = patched_data
        
        return model

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
    def style_AdditionalTable_headers(table):
            """Apply styles to table headers."""
            header = table.horizontalHeader()
            header.setStyleSheet(DataTableManager.HEADER_STYLE)
            header.setSectionResizeMode(QHeaderView.Interactive)
            table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
            header.setStretchLastSection(True)  # Expands the last column to fill available space
            table.resizeRowsToContents()
    
    """
    Create a widget based on the specified type and data.
    Args:
        widget_type (str): The type of widget to create. Supported types are "tags", "go", "interpro", "icon", and "text".
        data (any): The data to be used for creating the widget.
        go_definitions (dict, optional): A dictionary of GO term definitions. Defaults to None.
    Returns:
        QWidget: The created widget. If an error occurs, a QLabel with an error message is returned.
    """
# In utils/table_manager.py - Modify the create_widget method:

    def create_widget(widget_type, data, go_definitions=None):
        """Create optimized widgets for table cells"""
        try:
            if widget_type == "text":
                # Simple text widgets with safe text handling
                safe_text = DataTableManager.safe_text_for_widget(str(data))
                label = QLabel(safe_text)
                label.setMaximumWidth(300)  # Prevent excessive width
                return label
                
            elif widget_type == "tags":
                # For tags, create a simplified version for large datasets
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(2, 2, 2, 2)
                layout.setSpacing(2)
                
                # Limit to first 3 tags
                display_tags = data[:3] if len(data) > 3 else data
                
                for tag_type, value in display_tags:
                    label = QLabel(DataTableManager.safe_text_for_widget(str(value)))
                    label.setAlignment(Qt.AlignCenter)
                    label.setFixedSize(30, 20)
                    style = DataTableManager.STYLES["tag"].get(tag_type, DataTableManager.STYLES["tag"]["default"])
                    label.setStyleSheet(f"{style} border-radius: 3px; padding: 2px;")
                    layout.addWidget(label)
                    
                if len(data) > 3:
                    more_label = QLabel(f"+{len(data)-3}")
                    more_label.setAlignment(Qt.AlignCenter)
                    more_label.setStyleSheet("color: #666;")
                    layout.addWidget(more_label)
                    
                layout.addStretch()
                return widget
                
            elif widget_type == "go":
                # Simplify GO widgets
                if not data:
                    return QLabel("No GO terms")
                    
                # Show count for large lists
                if isinstance(data, list) and len(data) > 3:
                    return QLabel(f"{len(data)} GO terms")
                    
                # Show first term only
                go_id = data[0] if isinstance(data, list) and data else str(data).split(',')[0]
                desc, go_type = go_definitions.get(go_id, ("", ""))
                label = QLabel(f"{go_id} - {go_type}")
                return label
                
            elif widget_type == "interpro":
                # Simplify interpro widgets
                if not data or (isinstance(data, list) and not data):
                    return QLabel("No data")
                    
                # Show count for large lists
                if isinstance(data, list) and len(data) > 2:
                    return QLabel(f"{len(data)} annotations")
                    
                # Show first item only
                if isinstance(data, list):
                    text = str(data[0])
                else:
                    text = str(data)
                    
                if len(text) > 50:
                    text = text[:47] + "..."
                    
                return QLabel(text)
                
            elif widget_type == "icon":
                # Simplified icon
                icon_type = "classified" if data == "classified" else "unclassified"
                label = QLabel(icon_type.capitalize())
                color = "#4CAF50" if icon_type == "classified" else "#F44336"
                label.setStyleSheet(f"color: {color}; font-weight: bold;")
                return label
                
            else:
                return QLabel(str(data))
                    
        except Exception as e:
            logging.error(f"Error creating widget: {str(e)}")
            return QLabel("Error")
    """
    Create a stylized tag widget.
    Args:
        tags (list of tuple): A list of tuples where each tuple contains a tag type and its value.
    Returns:
        QWidget: The created tag widget.
    """

    @staticmethod
    def create_tag_widget(tags):
        """Crée un widget de tags stylisés"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)  # Increase margins for better visibility
        layout.setSpacing(4)  # Add spacing between tags

        for tag_type, value in tags:
            label = QLabel(str(value))
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(30, 20)  # Larger fixed size for visibility
            style = DataTableManager.STYLES["tag"].get(tag_type, DataTableManager.STYLES["tag"]["default"])
            label.setStyleSheet(f"{style} border-radius: 5px; padding: 4px; font-weight: bold;")
            layout.addWidget(label)

        widget.setMinimumHeight(30)  # Ensure widget has adequate minimum height
        return widget
    """
    Create a GO widget with formatted content.
    Args:
        gos_data (str or list): GO terms data, either as a comma-separated string or a list of GO terms.
        go_definitions (dict): A dictionary of GO term definitions.
    Returns:
        QLabel: The created GO widget.
"""
    @staticmethod
    def _create_go_widget(gos_data, go_definitions):
        """Crée le widget GO avec mise en forme"""
        content = []
        
        # Vérifier si c'est une liste ou une chaîne
        if isinstance(gos_data, list):
            gos = gos_data[:7]  # Prendre les 7 premiers éléments si c'est une liste
        else:
            # Conserver le comportement d'origine pour les chaînes
            gos = str(gos_data).split(',')[:7]
        
        for go_id in gos:
            if not go_id:  # Ignorer les entrées vides
                continue
            desc, go_type = go_definitions.get(go_id, ("No description", ""))
            content.append(f"<p>{go_id} - <b>{go_type}</b> - {desc}</p>")
        
        if isinstance(gos_data, str) and len(gos_data.split(',')) > 7:
            content.append("<p>...</p>")
        elif isinstance(gos_data, list) and len(gos_data) > 7:
            content.append("<p>...</p>")

        # Si aucun contenu, afficher un message par défaut
        if not content:
            content.append("<p>Aucune donnée GO disponible</p>")

        # Ensure the widget is properly sized
        label = QLabel("".join(content))
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet(DataTableManager.STYLES["go"] + "min-height: 30px; border-radius: 4px;")
        label.setWordWrap(True)  # Allow text to wrap
        label.setMinimumHeight(30)  # Minimum height
        label.setMinimumWidth(150) # Set minimum width
        return label
    """
    Create an InterPro widget.
    Args:
        data (list or str): InterPro data, either as a list of dictionaries or a string.
    Returns:
        QLabel: The created InterPro widget. If an error occurs, a QLabel with an error message is returned.
    """
    @staticmethod
    def _create_interpro_widget(data):
        """Crée le widget InterPro"""
        try:
            if not data:
                return QLabel("No InterPro data")
                
            # Handle case where data is already a list of strings
            if isinstance(data, list):
                if data and isinstance(data[0], str):
                    annotations = data
                else:
                    # Original behavior for list of dictionaries
                    annotations = [ip.get("interpro", "") for ip in data if isinstance(ip, dict)]
            else:
                # Handle string or other types
                annotations = [str(data)]
                
            # Filter out empty strings and join with newlines
            filtered_annotations = list(filter(None, annotations))
            if not filtered_annotations:
                label_text = "No annotations"
            else:
                # Escape commas in domain names by replacing them with HTML encoding
                # This prevents Qt from trying to parse them as font descriptions
                escaped_annotations = []
                for annotation in filtered_annotations:
                    if "," in annotation:
                        # Use HTML formatting instead of plain text
                        escaped_annotations.append(annotation.replace(",", "&#44;"))
                    else:
                        escaped_annotations.append(annotation)
                        
                label_text = "<br>".join(escaped_annotations)
                
            label = QLabel()
            label.setTextFormat(Qt.RichText)  # Enable rich text interpretation
            label.setText(label_text)
            label.setStyleSheet(DataTableManager.STYLES["interpro"] + "min-height: 30px; border-radius: 4px;")
            label.setWordWrap(True)  # Allow text to wrap
            
            return label
        except Exception as e:
            print(f"Error creating InterPro widget: {e}")
            return QLabel(f"Error: {str(e)}")
    """
    Create an icon widget for classification status.
    Args:
        icon_type (str): The type of icon to create. Supported types are "classified" and "unclassified".
    Returns:
        QWidget: The created icon widget.
    """
    @staticmethod
    def create_icon_widget(icon_type):
        """Create an icon widget for classification status"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Create icon
        icon_path = DataTableManager.ICON_PATHS.get(icon_type, DataTableManager.ICON_PATHS["unclassified"])
        pixmap = QPixmap(icon_path)
        
        if pixmap.isNull():
            # Fallback if icon doesn't load
            logging.warning(f"Icon not found: {icon_path}")
            label = QLabel(icon_type)
            label.setStyleSheet("color: #333; font-weight: bold;")
        else:
            # Create icon label
            label = QLabel()
            pixmap = pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
        
        # Add icon to layout
        layout.addWidget(label)
        
        # Add text label too
        text_label = QLabel(icon_type.capitalize())
        text_label.setStyleSheet("color: #333;")
        layout.addWidget(text_label)
        
        # Add spacer to push content to the left
        layout.addStretch()
        
        return widget

    @staticmethod
    def update_widget(widget, widget_type, data, go_definitions=None):
        """Update an existing widget with new data instead of creating a new one"""
        try:
            if widget_type == "tags":
                # Update tag labels
                if hasattr(widget, 'layout'):
                    layout = widget.layout()
                    # Clear existing tags
                    while layout.count():
                        item = layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    
                    # Add new tags
                    tags = data[:3] if len(data) > 3 else data
                    for tag_type, value in tags:
                        label = QLabel(str(value))
                        label.setAlignment(Qt.AlignCenter)
                        label.setFixedSize(30, 20)
                        style = DataTableManager.STYLES["tag"].get(tag_type, DataTableManager.STYLES["tag"]["default"])
                        label.setStyleSheet(f"{style} border-radius: 3px; padding: 2px;")
                        layout.addWidget(label)
                        
                    # Show count if more tags
                    if len(data) > 3:
                        more_label = QLabel(f"+{len(data)-3}")
                        more_label.setAlignment(Qt.AlignCenter)
                        more_label.setStyleSheet("color: #666;")
                        layout.addWidget(more_label)
                        
                    layout.addStretch()
                    
            elif widget_type == "go" and isinstance(widget, QLabel):
                # Update GO text
                if not data:
                    widget.setText("No GO terms")
                elif isinstance(data, list) and len(data) > 3:
                    widget.setText(f"{len(data)} GO terms")
                else:
                    go_id = data[0] if isinstance(data, list) and data else str(data).split(',')[0]
                    desc, go_type = go_definitions.get(go_id, ("", ""))
                    widget.setText(f"{go_id} - {go_type}")
                    
            elif widget_type == "interpro" and isinstance(widget, QLabel):
                # Update interpro text
                if not data:
                    widget.setText("No data")
                elif isinstance(data, list) and len(data) > 2:
                    widget.setText(f"{len(data)} annotations")
                else:
                    text = str(data[0]) if isinstance(data, list) and data else str(data)
                    if len(text) > 50:
                        text = text[:47] + "..."
                    widget.setText(text)
                    
            elif widget_type == "icon" and isinstance(widget, QLabel):
                # Update icon
                icon_type = "classified" if data == "classified" else "unclassified"
                color = "#4CAF50" if icon_type == "classified" else "#F44336"
                widget.setText(icon_type.capitalize())
                widget.setStyleSheet(f"color: {color}; font-weight: bold;")
                    
        except Exception as e:
            logging.error(f"Error updating widget: {str(e)}")