@staticmethod
def _add_row(table):
    """Ajoute une ligne au tables de l'ui."""
    row = table.rowCount()
    table.insertRow(row)

    lyr_cb = QgsMapLayerComboBox()
    lyr_cb.setFilters(QgsMapLayerProxyModel.VectorLayer)
    fld_cb = QgsFieldComboBox()
    fld_cb.setLayer(lyr_cb.currentLayer())
    lyr_cb.layerChanged.connect(fld_cb.setLayer)

    btn_del = QPushButton()
    icon_path = os.path.join(os.path.dirname(__file__), 'misc', 'cross.png')
    btn_del.setIcon(QtGui.QIcon(icon_path))
    btn_del.setIconSize(QtCore.QSize(16, 16))
    btn_del.setMaximumWidth(30)
    btn_del.clicked.connect(lambda: self.tableTaxref.removeRow(self.tableTaxref.indexAt(btn_del.pos()).row()))

    table.setCellWidget(row, 0, lyr_cb)
    table.setCellWidget(row, 1, fld_cb)
    table.setCellWidget(row, 2, btn_del)

@staticmethod
def _get_table_data(table):
    """Extrait les IDs et colonnes du tableau (pour collecte cd_nom)."""
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

@staticmethod
def _auto_lookup_layer(iface) -> tuple[List[QgsVectorLayer], List[str]] | None:
    """
    Recherche automatiquement les couches et les en-têtes de colonnes
    correspondant aux conditions (cdnom/cdref).
    """
    layers_names = iface.mapCanvas().layers()

    matched_layers = []
    matched_fields = []

    for layer_name in layers_names:
        field_names = [field.name() for field in layer_name.fields()]
        for field_name in field_names:
            if field_name.strip() == "cdnom" or field_name.strip() == "cdref":
                matched_layers.append(layer_name)
                matched_fields.append(field_name)
                break

    if not matched_layers:
        return None

    return matched_layers, matched_fields


@staticmethod
def (table, matched_layers, matched_fields):
    """
    charge automatiquement l'interface avec le résultat de auto_lookup_layer
    """
    buddies = zip(matched_layers, matched_fields)
    for buddy in buddies:
        QgsMapLayerComboBox =
        QgsFieldComboBox =