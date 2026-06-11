Biblizou — Plugin QGIS
======================

Moissonnage bibliographique automatisé (FSD ZNIEFF / Natura 2000, TaxRef, BD Statuts, Botanix).

Prérequis
---------

- QGIS 3.x
- Extension « Processing R Provider » installée et activée
  (menu Extensions → Gérer et installer les extensions → rechercher « Processing R Provider »)

Configuration R (obligatoire pour l'onglet Botanix)
---------------------------------------------------

1. Ouvrir Traitement → Options (ou Paramètres → Options → onglet Traitement)
2. Aller dans Fournisseurs → R
3. Configurer :
   - Dossier R : chemin vers l'installation R (ex. C:\Program Files\R\R-4.x.x sur Windows)
   - Dossier de scripts R : dossier où QGIS charge les scripts .rsx
     (ex. %APPDATA%\QGIS\QGIS3\profiles\default\processing\rscripts)

À l'activation du plugin, le script DcaToMembershipDf.rsx est copié automatiquement
dans le(s) dossier(s) de scripts R configuré(s).

Analyse Botanix (DCA → Membership)
----------------------------------

Le workflow Botanix exécute le script R via le Processing R Provider de QGIS
(processing.run), et non plus via un appel subprocess direct à Rscript.

Fichiers attendus dans le dossier de travail :
- julve_df.csv (généré par BotaJulveBuilder)

Installation
------------

Copier le dossier biblizou dans le répertoire des extensions QGIS, puis activer
le plugin dans Extensions → Gérer et installer les extensions → Installé.

Auteur : François Botcazou — francois.botcazou@proton.me
