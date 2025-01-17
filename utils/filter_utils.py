from PySide6.QtCore import Qt

def apply_dynamic_filters(table, filter_fields, logic):
    """Applies all dynamic filters to the table."""
    for row in range(table.rowCount()):
        row_matches = []
        for column_dropdown, filter_input in filter_fields:
            # Check if filter_input is still valid
            if filter_input and filter_input.parent() is not None:
                filter_value = filter_input.text().strip().lower()
                if not filter_value: 
                    continue

                column_index = column_dropdown.currentIndex()
                item = table.item(row, column_index)
                row_matches.append(item and filter_value in item.text().strip().lower())

        if logic == "AND":
            row_visible = all(row_matches) if row_matches else True
        else:
            row_visible = any(row_matches) if row_matches else True
                
        table.setRowHidden(row, not row_visible)

    visible_count = sum(not table.isRowHidden(row) for row in range(table.rowCount()))
    return visible_count

def clear_filters(filter_fields):
    for _, filter_input in filter_fields:
        if filter_input and filter_input.parent() is not None:
            filter_input.clear()

def reset_table_visibility(table):
    """Reset the visibility of all rows in the table."""
    for row in range(table.rowCount()):
        table.setRowHidden(row, False)


      