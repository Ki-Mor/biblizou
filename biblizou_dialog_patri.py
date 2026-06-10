# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : biblizou_dialog_patri.py
Groupe : Botanix
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