"""
Auteur : François Botcazou
Nom : UxiUtils.py
Groupe : utils
Description : Utilitaires pour l'Ux
"""

import os
from typing import List

from qgis.PyQt import QtGui, QtCore
from qgis.PyQt.QtWidgets import QPushButton
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer, QgsProject
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

def run_auto_fill(table, iface, log):
    """
    Enchaîne auto_lookup_layer, get_new_pairs et auto_fill_table pour préremplir
    automatiquement une table de couches/champs (TaxRef ou Stat).
    """
    result = auto_lookup_layer(iface)

    if result is None:
        log("Autofill : aucune couche compatible trouvée (colonne cdnom/cdref).")
        return

    matched_layers, matched_fields = result

    new_layers, new_fields = get_new_pairs(table, matched_layers, matched_fields)

    if not new_layers:
        log("Autofill : aucune nouvelle couche à ajouter (déjà présentes dans la table).")
        return

    auto_fill_table(table, new_layers, new_fields)
    log(f"Autofill : {len(new_layers)} couche(s) ajoutée(s).")

@staticmethod
def auto_lookup_layer(iface) -> tuple[List[QgsVectorLayer], List[str]] | None:
    """
    Recherche automatiquement les couches et les en-têtes de colonnes
    correspondant aux conditions (cdnom/cdref).
    """
    layers_names = QgsProject.instance().mapLayers().values()

    matched_layers = []
    matched_fields = []

    for layer_name in layers_names:
        field_names = [field.name() for field in layer_name.fields()]
        for field_name in field_names:
            normalized_field = field_name.strip().casefold().replace("_", "")
            if normalized_field == "cdnom" or normalized_field == "cdref":
                matched_layers.append(layer_name)
                matched_fields.append(field_name)
                break

    if not matched_layers:
        return None

    return matched_layers, matched_fields

@staticmethod
def get_new_pairs(table, matched_layers, matched_fields):
    """
    get_new_pairs est un garde-fou qui empêche d'ajouter des couples déjà présents dans l'interface.
    """
    existing_pairs = set()

    for row in range(table.rowCount()):
        lyr_cb = table.cellWidget(row, 0)
        fld_cb = table.cellWidget(row, 1)
        existing_layer = lyr_cb.currentLayer()
        existing_field = fld_cb.currentField()
        if existing_layer is not None:
            existing_pairs.add((existing_layer.id(), existing_field))

    new_layers = []
    new_fields = []

    for layer, field_name in zip(matched_layers, matched_fields):
        if (layer.id(), field_name) not in existing_pairs:
            new_layers.append(layer)
            new_fields.append(field_name)

    return new_layers, new_fields


@staticmethod
def auto_fill_table(table, new_layers, new_fields):
    """
    charge automatiquement l'interface avec le résultat de auto_lookup_layer
    """

    for layer, field_name in zip(new_layers, new_fields):

        row = table.rowCount()
        table.insertRow(row)

        lyr_cb = QgsMapLayerComboBox()
        lyr_cb.setFilters(QgsMapLayerProxyModel.VectorLayer)
        lyr_cb.setLayer(layer)
        fld_cb = QgsFieldComboBox()
        fld_cb.setLayer(layer)
        fld_cb.setField(field_name)
        lyr_cb.layerChanged.connect(fld_cb.setLayer)

        btn_del = QPushButton()
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'misc', 'cross.png')
        btn_del.setIcon(QtGui.QIcon(icon_path))
        btn_del.setIconSize(QtCore.QSize(16, 16))
        btn_del.setMaximumWidth(30)
        btn_del.clicked.connect(lambda checked, b=btn_del: table.removeRow(table.indexAt(b.pos()).row()))
        table.setCellWidget(row, 0, lyr_cb)
        table.setCellWidget(row, 1, fld_cb)
        table.setCellWidget(row, 2, btn_del)


def _on_process_finished(self, message, button):
    """Gestion commune de fin de traitement."""
    button.setEnabled(True)
    self._hide_progress()
    QtWidgets.QMessageBox.information(self, "Succès", message)
    self.iface.mainWindow().statusBar().clearMessage()