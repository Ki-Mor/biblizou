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