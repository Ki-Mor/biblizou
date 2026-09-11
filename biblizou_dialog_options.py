# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BiblizouDialogOptions
                                 A QGIS plugin
 Moissonnage bibliographique automatisé
                             -------------------
        begin                : 2026-09-10
        copyright            : (C) 2026 by François Botcazou
        email                : francois.botcazou@proton.me
 ***************************************************************************/
Description : Fenêtre des réglages généraux du plugin (premier réglage :
              nom du GeoPackage d'export). Persistance via QgsSettings,
              voir biblizou_settings.py.

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from .settings.biblizou_settings import get_gpkg_filename, set_gpkg_filename, is_valid_gpkg_name

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "biblizou_dialog_options.ui")
)


class BiblizouDialogOptions(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        super(BiblizouDialogOptions, self).__init__(parent)
        self.setupUi(self)

        # Pré-remplissage avec la valeur actuellement enregistrée
        self.leGpkgName.setText(get_gpkg_filename())

        self.leGpkgName.textChanged.connect(self.update_ok_button_state)
        self.update_ok_button_state(self.leGpkgName.text())

    def update_ok_button_state(self, text):
        """Active ou désactive le bouton Ok selon la validité du nom saisi."""
        ok_button = self.buttonBox.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(is_valid_gpkg_name(text))

    def accept(self):
        """Enregistre le nom du GeoPackage avant de fermer le dialog."""
        set_gpkg_filename(self.leGpkgName.text())
        super(BiblizouDialogOptions, self).accept()
