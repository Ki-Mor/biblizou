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
        self.setup_collapsible_groupbox(self.gBZnieff)


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

    def get_filter_conditions(self):
        """
        Traduit l'état de l'UI en une liste de conditions de filtrage sur status_data.

        Règle : une feuille n'émet une condition que si toute sa chaîne parentale
        est cochée (QGroupBox et QCheckBox intermédiaires).

        Retourne une liste de dicts. Deux formes possibles :
          - condition sur statusTypeName seul :
              {"statusTypeName": "Convention de Berne"}
          - condition sur (statusTypeName, statusCode) pour les listes rouges
            et les annexes de la Directive Habitats :
              {"statusTypeName": "Liste rouge nationale", "statusCode": "NT"}
              {"statusTypeName": "Directive Habitats, Faune, Flore", "statusCode": "CDH2"}

        Retourne [] si aucun widget actif — l'appelant décide du comportement.
        """
        conditions = []

        # ------------------------------------------------------------------ #
        # 1. Conventions internationales                                      #
        # ------------------------------------------------------------------ #
        if self.gBConventionInternationales.isChecked():
            mapping = {
                self.cBBerne: "Convention de Berne",
                self.cBCITES: "CITES",
                self.cBBonn:  "Convention de Bonn",
            }
            for checkbox, type_name in mapping.items():
                if checkbox.isChecked():
                    conditions.append({"statusTypeName": type_name})

        # ------------------------------------------------------------------ #
        # 2. Directives européennes                                           #
        # ------------------------------------------------------------------ #
        if self.gBDirEuro.isChecked():
            if self.cBDirHab.isChecked():
                STATUS_TYPE_DIR_HAB = "Directive Habitats, Faune, Flore"
                annexes = {
                    self.cBDirHab2: "CDH2",
                    self.cBDirHab4: "CDH4",
                }
                for checkbox, code in annexes.items():
                    if checkbox.isChecked():
                        conditions.append({
                            "statusTypeName": STATUS_TYPE_DIR_HAB,
                            "statusCode": code,
                        })

        # ------------------------------------------------------------------ #
        # 3. Protection                                                       #
        # ------------------------------------------------------------------ #
        if self.gBProtection.isChecked():
            mapping = {
                self.cBProtNat: "Protection nationale",
                self.cBProtReg: "Protection régionale",
            }
            for checkbox, type_name in mapping.items():
                if checkbox.isChecked():
                    conditions.append({"statusTypeName": type_name})

        # ------------------------------------------------------------------ #
        # 4. ZNIEFF                                                       #
        # ------------------------------------------------------------------ #
        if self.gBZnieff.isChecked():
            mapping = {
                self.cBZnieffDet: "ZNIEFF Déterminantes",
            }
            for checkbox, type_name in mapping.items():
                if checkbox.isChecked():
                    conditions.append({"statusTypeName": type_name})

        # ------------------------------------------------------------------ #
        # 5. Listes rouges                                                    #
        # ------------------------------------------------------------------ #
        if self.gBListesRouges.isChecked():
            # Chaque sous-GroupBox mappe sur un statusTypeName,
            # chaque checkbox feuille sur un statusCode.
            lr_groups = [
                (self.gBListeRougeMond, "Liste rouge mondiale", [
                    (self.cBLRMondLC, "LC"), (self.cBLRMondNT, "NT"),
                    (self.cBLRMondVU, "VU"), (self.cBLRMondEN, "EN"),
                    (self.cBLRMondCR, "CR"),
                ]),
                (self.gBListeRougeEuro, "Liste rouge européenne", [
                    (self.cBLREuLC, "LC"), (self.cBLREuNT, "NT"),
                    (self.cBLREuVU, "VU"), (self.cBLREuEN, "EN"),
                    (self.cBLREuCR, "CR"),
                ]),
                (self.gBListeRougeNat, "Liste rouge nationale", [
                    (self.cBLRNatLC, "LC"), (self.cBLRNatNT, "NT"),
                    (self.cBLRNatVU, "VU"), (self.cBLRNatEN, "EN"),
                    (self.cBLRNatCR, "CR"),
                ]),
                (self.gBListeRougeReg, "Liste rouge régionale", [
                    (self.cBLRRegLC, "LC"), (self.cBLRRegNT, "NT"),
                    (self.cBLRRegVU, "VU"), (self.cBLRRegEN, "EN"),
                    (self.cBLRRegCR, "CR"),
                ]),
            ]

            for groupbox, type_name, leaves in lr_groups:
                if not groupbox.isChecked():
                    continue
                for checkbox, code in leaves:
                    if checkbox.isChecked():
                        conditions.append({
                            "statusTypeName": type_name,
                            "statusCode": code,
                        })

        return conditions