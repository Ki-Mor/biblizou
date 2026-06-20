# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaPivotHabitats.py
Groupe : FSD
Description : Module pour créer un tableau croisé dynamique (pivot) des habitats Natura 2000.
              Transforme la table longue en format large avec un site par colonne.

"""

from .base.PivotLayer import PivotLayer
from qgis.core import Qgis


class NaturaPivotHabitats(PivotLayer):
    """
    Pivot des habitats directive Natura 2000.
    Colonnes : CD_UE, LB_HABDH_FR + une colonne par site.
    """

    def get_source_layer_name(self) -> str:
        return "Natura_2000_Habitats"

    def get_output_layer_name(self) -> str:
        return "Natura_2000_Habitats_Pivot"

    def get_site_keys(self) -> tuple:
        return ('SITECODE', 'SITE_NAME')

    def build_pivot_query(self) -> str:
        sites = self.get_sites()
        if not sites:
            return None

        case_statements = [
            f'MAX(CASE WHEN SITECODE = \'{str(code).replace("\'", "\'\'")}\' THEN 1 END) AS "{self.col_alias(code, name)}"'
            for code, name in sorted(sites.items())
        ]

        self.log(f"Requête SQL générée avec {len(case_statements)} colonnes", Qgis.Info)

        return f"""
SELECT CD_UE, LB_HABDH_FR, {', '.join(case_statements)}
FROM "{self.get_source_layer_name()}"
GROUP BY CD_UE, LB_HABDH_FR
ORDER BY CD_UE
"""


def run_module(gpkg_path: str = None):
    return NaturaPivotHabitats().run(gpkg_path)

if __name__ == "__console__":
    run_module()