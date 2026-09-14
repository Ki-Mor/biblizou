# -*- coding: utf-8 -*-
"""
Widget promu utilisé par biblizou_dialog_patri.ui pour les 4 groupes
"Liste Rouge" (mondiale / européenne / nationale / régionale).

Les 4 instances du .ui sont structurellement identiques (5 checkboxes
LC / NT / VU / EN / CR). Cette classe centralise cette structure une
seule fois, en Python, plutôt que de la dupliquer 4x dans le .ui.
"""

from qgis.PyQt.QtWidgets import QGroupBox, QGridLayout, QCheckBox

# Ordre et libellés des statuts UICN gérés par chaque bloc "Liste Rouge"
STATUTS_UICN = ("LC", "NT", "VU", "EN", "CR")


class ListeRougeGroupBox(QGroupBox):
    """QGroupBox cochable contenant 5 QCheckBox (un par statut UICN)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Dynamic property utilisée par le QSS : QGroupBox[class="listeRouge"]
        self.setProperty("class", "listeRouge")

        self.checkboxes = {}
        for col, statut in enumerate(STATUTS_UICN):
            cb = QCheckBox(self)
            cb.setObjectName(f"cB{statut}")
            layout.addWidget(cb, 0, col)
            self.checkboxes[statut] = cb

        self.setLayout(layout)

    def set_statuts_coches(self, statuts):
        """
        Définit les statuts cochés par défaut.

        :param statuts: itérable de statuts à cocher, ex. ("NT", "VU", "EN", "CR").
                         Les statuts absents de la liste sont décochés.
        """
        statuts = set(statuts)
        for statut, cb in self.checkboxes.items():
            cb.setChecked(statut in statuts)

    def statuts_coches(self):
        """Retourne la liste des statuts actuellement cochés."""
        return [statut for statut, cb in self.checkboxes.items() if cb.isChecked()]
