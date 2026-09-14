# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : biblizou_dialog_patri.py
Groupe : Botazou
Description : Dialog de gestion des espèces patrimoniales
"""

import os
from qgis.PyQt import uic, QtWidgets
from .settings.biblizou_settings import (
    # imports des statuts boolean
    DEFAULT_BERNE, DEFAULT_CITES, DEFAULT_BONN,  # Conventions internationales
    DEFAULT_DH2, DEFAULT_DH4, DEFAULT_DO1, DEFAULT_DO4,  # Directives Européennes
    DEFAULT_PN, DEFAULT_PR,  # Espèces protégées
    DEFAULT_ZDET,  # Déterminantes de ZNIEFF
    get_status_bool, set_status_bool,

    # imports des statuts list (listes rouges)
    DEFAULT_LR_MOND, DEFAULT_LR_EURO,
    DEFAULT_LR_NAT, DEFAULT_LR_REG,
    get_lr_statuts, set_lr_statuts
)

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'biblizou_dialog_patri.ui'))


class BiblizouDialogPatri(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        super(BiblizouDialogPatri, self).__init__(parent)
        self.setupUi(self)

        # 1. Charger l'état sauvegardé depuis QgsSettings (ou defaults)
        self.load_settings()

        # 2. Connecter le QDialogButtonBox (OK / Cancel)
        self.buttonBox.accepted.connect(self.save_and_accept)
        self.buttonBox.rejected.connect(self.reject)

        # 3. Connecter le bouton Reset
        self.btnReset.clicked.connect(self.reset_to_defaults)

    def load_settings(self):
        """Applique les valeurs enregistrées dans QgsSettings (ou valeurs par défaut)."""
        self.chbBerne.setChecked(get_status_bool("berne", DEFAULT_BERNE))
        self.chbCites.setChecked(get_status_bool("cites", DEFAULT_CITES))
        self.chbBonn.setChecked(get_status_bool("bonn", DEFAULT_BONN))
        self.chbDH2.setChecked(get_status_bool("dh2", DEFAULT_DH2))
        self.chbDH4.setChecked(get_status_bool("dh4", DEFAULT_DH4))
        self.chbDO1.setChecked(get_status_bool("do1", DEFAULT_DO1))
        self.chbDO4.setChecked(get_status_bool("do4", DEFAULT_DO4))
        self.chbPN.setChecked(get_status_bool("pn", DEFAULT_PN))
        self.chbPR.setChecked(get_status_bool("pr", DEFAULT_PR))
        self.chbZDet.setChecked(get_status_bool("zdet", DEFAULT_ZDET))

        self.gBListeRougeMond.set_statuts_coches(get_lr_statuts("lr_mondial", DEFAULT_LR_MOND))
        self.gBListeRougeEuro.set_statuts_coches(get_lr_statuts("lr_europe", DEFAULT_LR_EURO))
        self.gBListeRougeNat.set_statuts_coches(get_lr_statuts("lr_national", DEFAULT_LR_NAT))
        self.gBListeRougeReg.set_statuts_coches(get_lr_statuts("lr_regional", DEFAULT_LR_REG))

    def save_and_accept(self):
        """Enregistre la saisie utilisateur puis ferme le dialogue (OK)."""
        set_status_bool("berne", self.chbBerne.isChecked())
        set_status_bool("cites", self.chbCites.isChecked())
        set_status_bool("bonn", self.chbBonn.isChecked())
        set_status_bool("dh2", self.chbDH2.isChecked())
        set_status_bool("dh4", self.chbDH4.isChecked())
        set_status_bool("do1", self.chbDO1.isChecked())
        set_status_bool("do4", self.chbDO4.isChecked())
        set_status_bool("pn", self.chbPN.isChecked())
        set_status_bool("pr", self.chbPR.isChecked())
        set_status_bool("zdet", self.chbZDet.isChecked())

        set_lr_statuts("lr_mondial", self.gBListeRougeMond.statuts_coches())
        set_lr_statuts("lr_europe", self.gBListeRougeEuro.statuts_coches())
        set_lr_statuts("lr_national", self.gBListeRougeNat.statuts_coches())
        set_lr_statuts("lr_regional", self.gBListeRougeReg.statuts_coches())
        self.accept()

    def reset_to_defaults(self):
        """Réinitialise les cases aux valeurs par défaut sans fermer le dialogue."""
        self.chbBerne.setChecked(DEFAULT_BERNE)
        self.chbCites.setChecked(DEFAULT_CITES)
        self.chbBonn.setChecked(DEFAULT_BONN)
        self.chbDH2.setChecked(DEFAULT_DH2)
        self.chbDH4.setChecked(DEFAULT_DH4)
        self.chbDO1.setChecked(DEFAULT_DO1)
        self.chbDO4.setChecked(DEFAULT_DO4)
        self.chbPN.setChecked(DEFAULT_PN)
        self.chbPR.setChecked(DEFAULT_PR)
        self.chbZDet.setChecked(DEFAULT_ZDET)

        self.gBListeRougeMond.set_statuts_coches(DEFAULT_LR_MOND)
        self.gBListeRougeEuro.set_statuts_coches(DEFAULT_LR_EURO)
        self.gBListeRougeNat.set_statuts_coches(DEFAULT_LR_NAT)
        self.gBListeRougeReg.set_statuts_coches(DEFAULT_LR_REG)

    def get_filter_conditions(self):
        """Traduit l'état de l'UI en une liste de conditions de filtrage sur status_data."""
        conditions = []

        # 1. Conventions internationales
        if self.gBConventionsInternationales.isChecked():
            mapping = {
                self.chbBerne: "Convention de Berne",
                self.chbCites: "CITES",
                self.chbBonn: "Convention de Bonn",
            }
            for checkbox, type_name in mapping.items():
                if checkbox.isChecked():
                    conditions.append({"statusTypeName": type_name})

        # 2. Directives européennes
        if self.gBDirEuro.isChecked():
            if self.gBDH.isChecked():
                STATUS_TYPE_DIR_HAB = "Directive Habitats, Faune, Flore"
                dh_mapping = {
                    self.chbDH2: "CDH2",
                    self.chbDH4: "CDH4",
                }
                for checkbox, code in dh_mapping.items():
                    if checkbox.isChecked():
                        conditions.append({
                            "statusTypeName": STATUS_TYPE_DIR_HAB,
                            "statusCode": code,
                        })

            if self.gBDO.isChecked():
                STATUS_TYPE_DIR_OIS = "Directive Oiseaux"
                do_mapping = {
                    self.chbDO1: "CDO1",
                    self.chbDO4: "CDO4",
                }
                for checkbox, code in do_mapping.items():
                    if checkbox.isChecked():
                        conditions.append({
                            "statusTypeName": STATUS_TYPE_DIR_OIS,
                            "statusCode": code,
                        })

        # 3. Protection
        if self.gBProtection.isChecked():
            mapping = {
                self.chbPN: "Protection nationale",
                self.chbPR: "Protection régionale",
            }
            for checkbox, type_name in mapping.items():
                if checkbox.isChecked():
                    conditions.append({"statusTypeName": type_name})

        # 4. ZNIEFF
        if self.gBZnieff.isChecked():
            mapping = {
                self.chbZDet: "ZNIEFF Déterminantes",
            }
            for checkbox, type_name in mapping.items():
                if checkbox.isChecked():
                    conditions.append({"statusTypeName": type_name})

        # 5. Listes rouges
        if self.gBListesRouges.isChecked():
            lr_groups = [
                (self.cBListeRougeMond, self.gBListeRougeMond, "Liste rouge mondiale"),
                (self.cBListeRougeEuro, self.gBListeRougeEuro, "Liste rouge européenne"),
                (self.cBListeRougeNat, self.gBListeRougeNat, "Liste rouge nationale"),
                (self.cBListeRougeReg, self.gBListeRougeReg, "Liste rouge régionale"),
            ]

            for master_cb, groupbox, type_name in lr_groups:
                if master_cb.isChecked():
                    for code in groupbox.statuts_coches():
                        conditions.append({
                            "statusTypeName": type_name,
                            "statusCode": code,
                        })

        return conditions