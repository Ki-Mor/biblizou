# -*- coding: utf-8 -*-
"""
Auteur : ExEco Environnement - François Botcazou
Nom : BuildJulveDf .py
Groupe : Botazou
Description : Collecte les codes CD_NOM uniques depuis les couches sélectionnées,
              jointure avec baseflor.csv (indices Julve),
              export dans le dossier de travail sous julve_df.csv
"""
import os
import csv
from qgis.core import (
    QgsProject,
    QgsMessageLog,
    Qgis
)
from qgis.PyQt.QtCore import pyqtSignal, QObject


class BuildJulveDf(QObject):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    BASEFLOR_PATH = os.path.join(
        os.path.dirname(__file__), "..", "config", "baseflor.csv"
    )

    def __init__(self, working_folder):
        super().__init__()
        self.output_path = os.path.join(working_folder, "julve_df.csv")

    def _collecter_codes(self, layer_config):
        """Collecte les CD_NOM uniques depuis les couches sélectionnées."""
        unique_codes = set()
        for config in layer_config:
            layer = QgsProject.instance().mapLayer(config['layer_id'])
            if not layer:
                continue
            idx = layer.fields().lookupField(config['column'])
            for feat in layer.getFeatures():
                val = feat.attributes()[idx]
                if val is not None and str(val).strip():
                    clean_val = "".join(filter(str.isdigit, str(val)))
                    if clean_val:
                        unique_codes.add(clean_val)
        return unique_codes

    def _charger_baseflor(self):
        """Charge baseflor.csv et retourne un dict {cd_nom: row}."""
        baseflor = {}
        with open(self.BASEFLOR_PATH, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=",", quotechar='"')
            for row in reader:
                cd_nom = row.get("CD_NOM", "").strip()
                if cd_nom:
                    baseflor[cd_nom] = row
        return baseflor

    def run(self, layer_config):
        # 1. Collecte des codes
        self.status_changed.emit("Collecte des codes CD_NOM...")
        unique_codes = self._collecter_codes(layer_config)

        if not unique_codes:
            return False, "Aucun code CD_NOM trouvé dans les couches sélectionnées."

        self.status_changed.emit(f"{len(unique_codes)} codes uniques collectés.")

        # 2. Chargement baseflor
        self.status_changed.emit("Chargement de baseflor.csv...")
        try:
            baseflor = self._charger_baseflor()
        except FileNotFoundError:
            return False, f"baseflor.csv introuvable : {self.BASEFLOR_PATH}"

        # 3. Jointure
        self.status_changed.emit("Jointure avec baseflor...")
        resultats = []
        non_trouves = []

        for code in sorted(unique_codes):
            if code in baseflor:
                resultats.append(baseflor[code])
            else:
                non_trouves.append(code)

        if non_trouves:
            QgsMessageLog.logMessage(
                f"{len(non_trouves)} codes absents de baseflor : {', '.join(non_trouves[:10])}{'...' if len(non_trouves) > 10 else ''}",
                "Biblizou", Qgis.Warning
            )

        if not resultats:
            return False, "Aucune correspondance trouvée dans baseflor.csv."

        # 4. Export CSV
        self.status_changed.emit("Export julve_df.csv...")
        fieldnames = ["CD_NOM", "CD_REF", "NOM_SCIENTIFIQUE",
                      "L", "T", "C", "HA", "HE", "R", "N", "S", "Tx", "MO"]

        with open(self.output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames,
                                    delimiter=",", quotechar='"',
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(resultats)

        self.status_changed.emit("julve_df.csv enregistré.")
        return True, (
            f"{len(resultats)} espèces exportées vers {self.output_path}. "
            f"{len(non_trouves)} codes sans correspondance dans baseflor."
        )