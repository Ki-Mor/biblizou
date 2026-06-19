# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaPivotEspeces.py
Groupe : FSD
Description : Module pour créer un tableau croisé dynamique (pivot) des habitats Natura 2000.
              Transforme la table longue en format large avec un site par colonne.

"""

from .base.PivotLayer import PivotLayer
from qgis.core import Qgis


class NaturaPivotEspeces(PivotLayer):
    """
    Pivot des espèces Natura 2000.
    Colonnes : TAXGROUP, CD_NOM, NOM + une colonne par site.
    Utilise l'ID de couche dans la requête SQL.
    """

    def get_source_layer_name(self) -> str:
        return "Natura_2000_Especes"

    def get_output_layer_name(self) -> str:
        return "Natura_2000_Especes_Pivot"

    def get_site_keys(self) -> tuple:
        return ('SITECODE', 'SITE_NAME')

    def build_pivot_query(self) -> str:
        sites = self.get_sites()
        if not sites:
            return None

        layer_id = self.source_layer.id()

        case_statements = [
            f'MAX(CASE WHEN SITECODE = \'{str(code).replace("\'", "\'\'")}\' THEN 1 ELSE NULL END) AS "{self.col_alias(code, name)}"'
            for code, name in sorted(sites.items())
        ]

        self.log(f"Requête SQL générée avec {len(case_statements)} colonnes", Qgis.Info)

        return (
            f'SELECT TAXGROUP AS GROUPE, CD_NOM, NOM, '
            f'{", ".join(case_statements)} '
            f'FROM "{layer_id}" '
            f'GROUP BY TAXGROUP, CD_NOM, NOM '
            f'ORDER BY TAXGROUP ASC, NOM ASC'
        )


def run_module(gpkg_path: str = None):
    return NaturaPivotEspeces().run(gpkg_path)


if __name__ == "__console__":
    run_module()
