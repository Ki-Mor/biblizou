# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : RRunner.py
Groupe : Botanix
Description : Utilitaire pour executer des scripts R depuis QGIS
"""

import os
import json
import subprocess

from qgis.core import QgsMessageLog, Qgis


class RRunner:

    def __init__(self):
        # Racine du plugin : utils/ est un niveau en dessous
        self.plugin_dir = os.path.dirname(os.path.dirname(__file__))
        self.modules_dir = os.path.join(self.plugin_dir, "modules")
        self.rscript_path = self._find_rscript()

    def _find_rscript(self):
        """Trouve Rscript depuis la config QGIS ou le PATH système."""
        from qgis.core import QgsSettings
        import shutil

        settings = QgsSettings()
        r_folder = settings.value("processing/configuration/R_FOLDER", "")
        if r_folder:
            candidate = os.path.join(r_folder, "bin", "Rscript.exe")
            if os.path.isfile(candidate):
                return candidate

        # Fallback : Rscript dans le PATH système
        found = shutil.which("Rscript")
        if found:
            return found

        QgsMessageLog.logMessage(
            "RRunner: Rscript introuvable. Configurez R dans Traitement → Options.",
            "Botanix", level=Qgis.Critical
        )
        return None

    def run(self, script_name, folder_path, input_file=None):
        """
        Lance un script R en lui passant folder_path.

        :param script_name: nom du fichier R ex: "DcaToMembershipDf.R"
        :param folder_path: dossier de travail défini par l'utilisateur
        :return: True si succès, False sinon
        """
        if not self.rscript_path:
            return False

        if not os.path.isdir(folder_path):
            QgsMessageLog.logMessage(
                f"RRunner: Dossier introuvable: {folder_path}",
                "Botanix",
                level=Qgis.Warning
            )  # ← ferme logMessage(
            return False

        script_r = os.path.join(self.modules_dir, script_name)
        if not os.path.isfile(script_r):
            QgsMessageLog.logMessage(
                f"RRunner: Script R introuvable: {script_r}",
                "Botanix",
                level=Qgis.Critical
            )
            return False

        params = {"folder_path": folder_path}
        if input_file:
            params["input_file"] = input_file

        try:
            result = subprocess.run(
                [self.rscript_path, script_r, json.dumps(params)],
                capture_output=True,
                text=True,
                check=True
            )
            QgsMessageLog.logMessage(
                f"RRunner: {script_name} terminé.\n{result.stdout}",
                "Botanix",
                level=Qgis.Info
            )
            return True

        except subprocess.CalledProcessError as e:
            QgsMessageLog.logMessage(
                f"RRunner: Erreur R:\n{e.stderr}",
                "Botanix",
                level=Qgis.Critical
            )
            return False