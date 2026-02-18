from PySide2.QtWidgets import QTreeWidgetItem


def create_attrs_in_rig_tree_item(display_string: str) -> QTreeWidgetItem:
    """
    Creates a QTreeWidgetItem with the given display string.
    
    Args:
        display_string (str): The string to display in the tree widget item.
        
    Returns:
        QtWidgets.QTreeWidgetItem: A new tree widget item with the display string.
    """
    item = QTreeWidgetItem([display_string])
    return item