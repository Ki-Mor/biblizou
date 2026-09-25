"""
Auteur : François Botcazou
Nom : UxiUtils.py
Groupe : utils
Description : Utilitaires pour l'Ux
"""

import os
from qgis.PyQt import QtGui, QtCore
from qgis.PyQt.QtWidgets import QPushButton
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox

def add_row(table):
    row = table.rowCount()
    table.insertRow(row)

    lyr_cb = QgsMapLayerComboBox()
    lyr_cb.setFilters(QgsMapLayerProxyModel.VectorLayer)
    fld_cb = QgsFieldComboBox()
    fld_cb.setLayer(lyr_cb.currentLayer())
    lyr_cb.layerChanged.connect(fld_cb.setLayer)

    btn_del = QPushButton()
    icon_path = os.path.join(os.path.dirname(__file__), '..', 'misc', 'cross.png')
    btn_del.setIcon(QtGui.QIcon(icon_path))
    btn_del.setIconSize(QtCore.QSize(16, 16))
    btn_del.setMaximumWidth(30)
    btn_del.clicked.connect(lambda: table.removeRow(table.indexAt(btn_del.pos()).row()))

    table.setCellWidget(row, 0, lyr_cb)
    table.setCellWidget(row, 1, fld_cb)
    table.setCellWidget(row, 2, btn_del)

def get_table_data(table):
    data = []
    for row in range(table.rowCount()):
        lyr_widget = table.cellWidget(row, 0)
        fld_widget = table.cellWidget(row, 1)
        if lyr_widget and lyr_widget.currentLayer():
            data.append({
                "layer_id": lyr_widget.currentLayer().id(),
                "column": fld_widget.currentField()
            })
    return data


# @staticmethod
# def auto_lookup_layer(iface) -> tuple[List[QgsVectorLayer], List[str]] | None:
#     """
#     Recherche automatiquement les couches et les en-têtes de colonnes
#     correspondant aux conditions (cdnom/cdref).
#     """
#     layers_names = iface.mapCanvas().layers()
#
#     matched_layers = []
#     matched_fields = []
#
#     for layer_name in layers_names:
#         field_names = [field.name() for field in layer_name.fields()]
#         for field_name in field_names:
#             if field_name.strip() == "cdnom" or field_name.strip() == "cdref":
#                 matched_layers.append(layer_name)
#                 matched_fields.append(field_name)
#                 break
#
#     if not matched_layers:
#         return None
#
#     return matched_layers, matched_fields


# @staticmethod
# def auto_fill_table(table, matched_layers, matched_fields):
#     """
#     charge automatiquement l'interface avec le résultat de auto_lookup_layer
#     """
#     buddies = zip(matched_layers, matched_fields)
#     for buddy in buddies:
#         QgsMapLayerComboBox =
#         QgsFieldComboBox =

def _on_process_finished(self, message, button):
    """Gestion commune de fin de traitement."""
    button.setEnabled(True)
    self._hide_progress()
    QtWidgets.QMessageBox.information(self, "Succès", message)
    self.iface.mainWindow().statusBar().clearMessage()