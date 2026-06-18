# Biblizou — Plugin QGIS

Biblizou génère automatiquement une base de données bibliographique via quatre modules principaux :
* **FSD** : Moissonnage automatique des données issues des Formulaires Standards de Données (FSD) des sites ZNIEFF et Natura 2000 intersectant l'aire d'étude choisie.
* **TaxRef** : Interrogation de l'API de l'INPN (Inventaire National du Patrimoine Naturel) pour extraire les référentiels taxonomiques officiels.
* **BDC** : Interrogation de l'API de l'INPN pour consolider les statuts de protection et de conservation des espèces.
* **Botazou** : Regroupement automatisé des espèces de la flore par affinités écologiques (analyses multivariées).

## Prérequis

* QGIS `3.x`
* Extension **Processing R Provider** installée et activée via `Extensions` → `Gérer et installer les extensions`.

## Configuration de R

Le moteur R est indispensable au fonctionnement du module **Botazou**.

1. Accéder à `Traitement` → `Options` → `Fournisseurs` → `R`.
2. Configurer le **Dossier R** pointant vers l'exécutable local (ex: `C:\Program Files\R\R-4.x.x`).
3. Configurer le **Dossier de scripts R** (ex: `%APPDATA%\QGIS\QGIS3\profiles\default\processing\rscripts`).

*Note : Le script requis `DcaToMembershipDf.rsx` est automatiquement déployé dans ce répertoire lors de l'activation du plugin.*

## Installation

1. Télécharger ou cloner le dépôt.
2. Déplacer le dossier `biblizou` dans le répertoire des extensions QGIS :
   * **Windows** : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins`
   * **Linux** : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
3. Activer **Biblizou** dans `Extensions` → `Gérer et installer les extensions` → `Installé`.

## Contribution

Le projet est collaboratif. Vous pouvez participer via deux canaux :
* **Workflow Git** : Ouverture d'une *Issue* pour signaler un bug/proposer une évolution, ou soumission directe d'une *Pull Request* (PR).
* **Contact direct** : Envoi de suggestions par e-mail si vous n'utilisez pas Git.

**Auteur** : François Botcazou — francois.botcazou@proton.me

## Références & Citations

* **Baseflor** : Julve, P. (1998-). *Index botanique, écologique et chorologique de la flore de France*. Institut Catholique de Lille (Extrait du 06/06/2026).
* **FactoMineR** : Lê, S., Josse, J. & Husson, F. (2008). *FactoMineR: An R Package for Multivariate Analysis*. Journal of Statistical Software, 25(1), 1-18.
* **INPN** : Référentiel TAXREF & Base de connaissances sur les statuts de conservation des espèces.
