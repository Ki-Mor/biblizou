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