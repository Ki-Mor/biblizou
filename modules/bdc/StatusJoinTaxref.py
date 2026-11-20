# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusJoinTaxref.py
Groupe : bdc
Description : Enrichit la table layer_name avec nom vernaculaire et groupe taxonomique
              obtenus par requête API TaxRef (GET taxa/{cd_nom}), comme TaxrefApiToTable.
              Enregistre le résultat dans biblizou.gpkg|output_name.
"""

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsField,
    QgsMessageLog,
    Qgis
)

TAXREF_LAYER = "data_taxref"

def _clean_key(value):
    """Normalise un identifiant en texte sans '.0' (3723.0 -> '3723')."""
    return str(value).split(".")[0].strip() if value is not None else ""

def _build_taxon_lookup(gpkg_path):
    """Lit data_taxref. Renvoie {cdnom: {"nom_vern": ..., "groupe": ...}}."""
    layer_taxref = LayerUtils.load_from_gpkg(gpkg_path, TAXREF_LAYER)
    if layer_taxref is None:
        return None
    fields = layer_taxref.fields()
    idx_id = fields.indexOf("id")
    idx_vern = fields.indexOf("frenchVernacularName")
    idx_grp = fields.indexOf("vernacularGroup2")
    if -1 in (idx_id, idx_vern, idx_grp):
        return None
    lookup = {}
    for feat in layer_taxref.getFeatures():
        attrs = feat.attributes()
        key = _clean_key(attrs[idx_id])
        if key:
            lookup[key] = {"nom_vern": str(attrs[idx_vern] or ""),
                           "groupe": str(attrs[idx_grp] or "")}
    return lookup

from ..base.LayerUtils import LayerUtils

def _fetch_taxon_info(cdnom, session):
    """Récupère vernacularName1 et groupe (classe ou ordre) via l'API TaxRef."""
    try:
        r = session.get(f"{API_TAXA}/{cdnom}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        nom_vern = (data.get("vernacularName1") or data.get("nomVern") or "")
        if isinstance(nom_vern, dict):
            nom_vern = nom_vern.get("value", "") or ""
        groupe = (data.get("classe") or data.get("ordre") or data.get(
            "groupe") or "")
        if isinstance(groupe, dict):
            groupe = groupe.get("value", "") or ""
        return {"nom_vern": str(nom_vern), "groupe": str(groupe)}
    except Exception:
        return None


def run(gpkg_path: str, layer_name: str,
        progress_callback=None, log_callback=None,
        output_name: str | None = None) -> tuple[bool, str]:
    """
    Charge la couche layer_name depuis gpkg_path.
    Pour chaque cdnom distinct appelle l'API TaxRef pour récupérer nom vernaculaire et groupe,
    puis ajoute les colonnes nom_vern et groupe à layer_name
    Résultat enregistré dans une nouvelle couche "status_joined_taxref".
        Args:
                gpkg_path: chemin vers biblizou.gpkg
                layer_name: layer obtenue via le worker
                progress_callback:
                log_callback: optional (message)
                output_name: nom de la couche de sortie (défaut "status_joined_taxref")

        Returns:
            (success: bool, message: str)
        """

    def log(msg):
        QgsMessageLog.logMessage(f"[StatusJoinTaxRef]: {msg}", "Biblizou",
                                 Qgis.Info)  # mis à jour aujourd'hui précédemment QgsMessageLog.logMessage(msg, "Biblizou", level=Qgis.Info)
        if log_callback:
            log_callback(msg)

    layer_status = LayerUtils.load_from_gpkg(gpkg_path, layer_name)
    if layer_status is None:
        return False, f"Avertissement : aucune couche {layer_name} trouvée dans le GeoPackage."

    idx_cdnom = layer_status.fields().indexOf("cdnom")
    if idx_cdnom == -1:
        return False, f"Champ cdnom absent de {layer_name}."

    # Cdnom distincts
    cdnoms = set()
    for feat in layer_status.getFeatures():
        v = feat.attributes()[idx_cdnom]
        if v is not None:
            key = str(v).split(".")[0].strip()
            if key:
                cdnoms.add(key)

    if not cdnoms:
        return False, f"Aucun cdnom dans {layer_name}."

    log(f"Jointure locale sur {TAXREF_LAYER} pour {len(cdnoms)} taxons...")
    lookup = _build_taxon_lookup(gpkg_path)
    if lookup is None:
        return False, (f"Couche {TAXREF_LAYER} ou champs id / "
                       "frenchVernacularName / vernacularGroup2 introuvables.")
    taxon_info = {}
    for i, cdnom in enumerate(sorted(cdnoms)):
        if progress_callback and len(cdnoms) > 0:
            progress_callback(i + 1, len(cdnoms), f"API TaxRef {cdnom}")
        info = _fetch_taxon_info(cdnom, session)
        taxon_info[cdnom] = info or {"nom_vern": "", "groupe": ""}
        time.sleep(0.15)

    def compute_fn(feat):
        cdnom = feat.attributes()[idx_cdnom]
        key = str(cdnom).split(".")[0].strip() if cdnom is not None else ""
        info = taxon_info.get(key, {"nom_vern": "", "groupe": ""})
        return [info["nom_vern"], info["groupe"]]

    new_fields = [QgsField("nom_vern", QVariant.String),
                  QgsField("groupe", QVariant.String)]

    layer_joined = LayerUtils.add_computed_fields(
        layer_status, new_fields, compute_fn,
        output_name=output_name or "status_joined_taxref"
    )
    if layer_joined is None:
        return False, "Avertissement : aucune référence taxonomique ajoutée."

    success, err_msg = LayerUtils.save_to_gpkg(layer_joined, gpkg_path)
    if not success:
        return False, f"Erreur sauvegarde GPKG : {err_msg}"

    log(f"Colonnes Taxref ajoutées à {layer_name}.")
    return True, f"Colonnes Taxref ajoutées à {layer_name}."
