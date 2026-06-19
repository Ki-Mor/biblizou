# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffPivotEspeces.py
Groupe : FSD
Description : Module pour créer un tableau croisé dynamique (pivot) unique des espèces ZNIEFF.
              Filtré uniquement sur les espèces déterminantes (FG_ESP = 'D').
              - GROUPE en première colonne
              - cd_noms, nom_complets, nom_vern en colonnes suivantes.
              - Sites en colonnes nommées "[nm_sffzn] - [lb_zn]" (sans accents).
              - Valeurs NULL au lieu de 0 pour la clarté visuelle.
              - Tri par GROUPE puis par nom_complet (ascendant).
"""

from .base.PivotLayer import PivotLayer
from qgis.core import Qgis


class ZnieffPivotEspeces(PivotLayer):
    """
    Pivot des espèces déterminantes ZNIEFF (FG_ESP = 'D').
    Colonnes : GROUPE, cd_nom, nom_complet, nom_vern + une colonne par ZNIEFF.
    Utilise l'ID de couche dans la requête SQL pour éviter les conflits de noms.
    """

    def get_source_layer_name(self) -> str:
        return "Znieff_Especes"

    def get_output_layer_name(self) -> str:
        return "Znieff_EspDet_Pivot"

    def get_site_keys(self) -> tuple:
        return ('nm_sffzn', 'lb_zn')

    def get_sites(self) -> dict:
        """
        Surcharge : filtre sur les espèces déterminantes uniquement (fg_esp = 'D')
        avant d'extraire les sites.
        """
        sites = {}
        try:
            for feat in self.source_layer.getFeatures():
                if feat['fg_esp'] == 'D':
                    code = feat['nm_sffzn']
                    name = feat['lb_zn']
                    if code:
                        sites[code] = name if name else "Nom inconnu"
        except KeyError as e:
            self.log(f"Champ manquant : {e}", Qgis.Critical)

        if not sites:
            self.log("Aucun site trouvé pour les espèces déterminantes", Qgis.Warning)

        return sites

    def build_pivot_query(self) -> str:
        sites = self.get_sites()
        if not sites:
            return None

        # Utilise l'ID de couche pour éviter les conflits si le nom contient des caractères spéciaux
        layer_id = self.source_layer.id()

        case_statements = [
            f'MAX(CASE WHEN nm_sffzn = \'{str(code).replace("\'", "\'\'")}\' THEN 1 ELSE NULL END) AS "{self.col_alias(code, name)}"'
            for code, name in sorted(sites.items())
        ]

        self.log(f"Requête SQL générée avec {len(case_statements)} colonnes", Qgis.Info)

        return (
            f'SELECT groupe AS GROUPE, cd_nom, nom_complet, nom_vern, '
            f'{", ".join(case_statements)} '
            f'FROM "{layer_id}" '
            f"WHERE fg_esp = 'D' "
            f'GROUP BY groupe, cd_nom, nom_complet, nom_vern '
            f'ORDER BY groupe ASC, nom_complet ASC'
        )


def run_module(gpkg_path: str = None):
    return ZnieffPivotEspeces().run(gpkg_path)

if __name__ == "__console__":
    run_module()