# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : biblizou_dialog_patri.py
Groupe : Botazou
Description : Dialog de gestion des espèces patrimoniales
"""

import os
from qgis.PyQt import uic, QtWidgets

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'biblizou_dialog_patri.ui'))


class BiblizouDialogPatri(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        super(BiblizouDialogPatri, self).__init__(parent)
        self.setupUi(self)
        self.setup_collapsible_groupbox(self.gBConventionInternationales)
        self.setup_collapsible_groupbox(self.gBDirEuro)
        self.setup_collapsible_groupbox(self.gBProtection)
        self.setup_collapsible_groupbox(self.gBListesRouges)

    def setup_collapsible_groupbox(self, groupbox):
        groupbox.setCheckable(True)
        groupbox.initial_max_height = groupbox.maximumHeight()

        def toggle_group(is_checked):
            if is_checked:
                groupbox.setMaximumHeight(
                    groupbox.initial_max_height if groupbox.initial_max_height != 16777215 else 1000)
            else:
                groupbox.setMaximumHeight(24)

        groupbox.toggled.connect(toggle_group)
        toggle_group(groupbox.isChecked())