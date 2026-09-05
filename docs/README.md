<p align="center">
  <a href="https://ki-mor.github.io/biblizou_frontend/"><img src="../misc/icon.svg" alt="biblizou_frontend" width="100"></a>
</p>

# **[Biblizou — Plugin QGIS](https://ki-mor.github.io/biblizou_frontend/)**

Biblizou génère automatiquement une base de données bibliographique via quatre modules principaux :

* **[FSD](https://ki-mor.github.io/biblizou/Fsd.html)** : Moissonnage automatique des données issues des Formulaires
  Standards de Données (FSD) des sites ZNIEFF et Natura 2000 intersectant l'aire d'étude choisie.
* **[TAXREF](https://ki-mor.github.io/biblizou/Taxref.html)** : Interrogation de l'API de l'INPN (Inventaire National du
  Patrimoine Naturel) pour extraire les référentiels taxonomiques officiels.
* **[BDC](https://ki-mor.github.io/biblizou/Bdc.html)*** : Interrogation de l'API de l'INPN pour consolider les statuts
  de protection et de conservation des espèces.
<!-- **Botazou** : Regroupement automatisé des espèces de la flore par affinités écologiques (analyses multivariées). -->

## Progrès
  - <img src="https://img.shields.io/badge/Avancement-██████████_100%25-brightgreen" alt="Avancement 100%"> : Module de moissonnage des FSD - moissonnage automatique des données issues des Formulaires Standards de Données (FSD) des sites ZNIEFF et Natura 2000 intersectant l’aire d’étude choisie.
  - <img src="https://img.shields.io/badge/Avancement-█████████░_90%25-green" alt="Avancement 090%"> : Module d'enrichissement TAXREF - interrogation de l’API de l’INPN pour extraire les référentiels taxonomiques officiels.
  - <img src="https://img.shields.io/badge/Avancement-█████████░_90%25-green" alt="Avancement 090%"> : Module d'enrichissement BDC - interrogation de l’API de l’INPN pour consolider les statuts de protection et de conservation des espèces.
  - <img src="https://img.shields.io/badge/Avancement-█████░░░░░_50%25-orange" alt="Avancement 050%"> : Module Botazou - regroupement automatisé des espèces de la flore par affinités écologiques
  - <img src="https://img.shields.io/badge/Avancement-░░░░░░░░░░_00%25-red" alt="Avancement 000%"> : Migration vers Qgis4

## Prérequis

* QGIS `3.x`
<!-- * Extension **Processing R Provider** installée et activée via `Extensions` → `Gérer et installer les extensions`.

## Configuration de R

Le moteur R est indispensable au fonctionnement du module **Botazou**.

1. Accéder à `Traitement` → `Options` → `Fournisseurs` → `R`.
2. Configurer le **Dossier R** pointant vers l'exécutable local (ex: `C:\Program Files\R\R-4.x.x`).
3. Configurer le **Dossier de scripts R** (ex: `%APPDATA%\QGIS\QGIS3\profiles\default\processing\rscripts`).

*Note : Le script requis `DcaToMembershipDf.rsx` est automatiquement déployé dans ce répertoire lors de l'activation du plugin.* -->

## Installation
... par Qgis

Activer **Biblizou** dans `Extensions` → `Gérer et installer les extensions` → `Toutes`.

... par GitHub
1. Télécharger ou cloner le dépôt.
2. Déplacer le dossier `biblizou` dans le répertoire des extensions QGIS :
   * **Windows** : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins`
   * **Linux** : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
3. Activer **Biblizou** dans `Extensions` → `Gérer et installer les extensions` → `Installées`.

## Liens utiles

[![Présentation](https://img.shields.io/badge/Présentation_du_plugin-6F42C1?style=for-the-badge&logo=githubpages&logoColor=white)](https://Ki-Mor.github.io/biblizou_frontend/)
[![Documentation technique](https://img.shields.io/badge/Documentation_technique-226C61?style=for-the-badge&logo=githubpages&logoColor=white)](https://Ki-Mor.github.io/biblizou/)
[![Bug tracker](https://img.shields.io/badge/Bug_tracking-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Ki-Mor/biblizou/issues)
[![Page QGIS](https://img.shields.io/badge/Page_QGIS-589632?style=for-the-badge&logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/biblizou/)

## Crédits

* **Auteur** : François Botcazou

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/botcazoufrancois/)
[![ResearchGate](https://img.shields.io/badge/ResearchGate-00CCBB?style=for-the-badge&logo=ResearchGate&logoColor=white)](https://www.researchgate.net/profile/Francois-Botcazou)
[![Portfolio](https://img.shields.io/badge/Portfolio-6F42C1?style=for-the-badge&logo=githubpages&logoColor=white)](https://Ki-Mor.github.io/porfolio/) [![Mail Pro](https://img.shields.io/badge/Mail-purple?style=for-the-badge&logo=proton&logoColor=white)](mailto:francois.botcazou@proton.me)

* **Contributeurs-ices** :

<a href="https://github.com/Ki-Mor/biblizou/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Ki-Mor/biblizou&anon=0" />
</a>

### Pour contribuer

Le projet est collaboratif. Vous pouvez participer via deux canaux :
* **Workflow Git** : Ouverture d'une *Issue* pour signaler un bug/proposer une évolution, ou soumission directe d'une *Pull Request* (PR).
* **Contact direct** : Envoi de suggestions par e-mail si vous n'utilisez pas Git.

## Licence

Ce projet est sous licence GNU v3 GPL.
Vous pouvez le partager, l’adapter et l’utiliser à des fins non commerciales, en mentionnant l’auteur original.
https://www.gnu.org/licenses/gpl-3.0.html#license-text
