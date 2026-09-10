# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Styles
                                 A QGIS plugin
 Moissonnage bibliographique automatisé
                             -------------------
        begin                : 2026-09-10
        copyright            : (C) 2026 by François Botcazou
        email                : francois.botcazou@proton.me
 ***************************************************************************/
Description : Charge et applique la feuille de style resources/biblizou.qss
"""

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
