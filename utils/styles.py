import os


def load_stylesheet(plugin_dir=None) -> str:
    if plugin_dir is None:
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    qss_path = os.path.join(plugin_dir, "resources", "style", "biblizou.qss")

    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        QgsMessageLog.logMessage(
            f"Impossible de charger la feuille de style : {e}",
            "Biblizou",
            level=Qgis.Warning
        )
        return ""


def apply_stylesheet(widget, plugin_dir=None):
    widget.setStyleSheet(load_stylesheet(plugin_dir))
