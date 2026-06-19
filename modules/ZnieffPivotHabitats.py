# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffPivotHabitats.py
Groupe : FSD
Description : Module pour créer un tableau croisé dynamique (pivot) des habitats déterminants ZNIEFF.
              Transforme la table longue en format large avec une ZNIEFF par colonne.
"""

from .base.PivotLayer import PivotLayer
from qgis.core import Qgis


class ZnieffPivotHabitats(PivotLayer):
    """
    Pivot des habitats déterminants ZNIEFF.
    Colonnes : LB_CODE, LB_HAB + une colonne par ZNIEFF.
    """

    def get_source_layer_name(self) -> str:
        return "Znieff_Habitats"

    def get_output_layer_name(self) -> str:
        return "Znieff_Hab_Pivot"

    def get_site_keys(self) -> tuple:
        return ('NM_SFFZN', 'LB_ZN')

    def build_pivot_query(self) -> str:
        sites = self.get_sites()
        if not sites:
            return None

        case_statements = [
            f'MAX(CASE WHEN NM_SFFZN = \'{str(code).replace("\'", "\'\'")}\' THEN 1 END) AS "{self.col_alias(code, name)}"'
            for code, name in sorted(sites.items())
        ]

        self.log(f"Requête SQL générée avec {len(case_statements)} colonnes", Qgis.Info)

        return f"""
SELECT LB_CODE, LB_HAB, {', '.join(case_statements)}
FROM "{self.get_source_layer_name()}"
GROUP BY LB_CODE, LB_HAB
ORDER BY LB_CODE
"""


def run_module():
    return ZnieffPivotHabitats().run()

if __name__ == "__console__":
    run_module()