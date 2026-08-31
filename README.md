<p align="center">
  <img src="misc/icon.svg" alt="Description" width=100>
</p>

# Biblizou — Plugin QGIS

Biblizou génère automatiquement une base de données bibliographique via quatre modules principaux :
* **FSD** : Moissonnage automatique des données issues des Formulaires Standards de Données (FSD) des sites ZNIEFF et Natura 2000 intersectant l'aire d'étude choisie.
* **TaxRef** : Interrogation de l'API de l'INPN (Inventaire National du Patrimoine Naturel) pour extraire les référentiels taxonomiques officiels.
* **BDC** : Interrogation de l'API de l'INPN pour consolider les statuts de protection et de conservation des espèces.
<!-- **Botazou** : Regroupement automatisé des espèces de la flore par affinités écologiques (analyses multivariées). -->

## Prérequis

* QGIS `3.x`

## Installation

1. Télécharger ou cloner le dépôt.
2. Déplacer le dossier `biblizou` dans le répertoire des extensions QGIS :
   * **Windows** : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins`
   * **Linux** : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
3. Activer **Biblizou** dans `Extensions` → `Gérer et installer les extensions` → `Installé`.

## Liens utiles

[![Présentation](https://img.shields.io/badge/Présentation_du_plugin-6F42C1?style=for-the-badge&logo=githubpages&logoColor=white)](https://Ki-Mor.github.io/biblizou_frontend/)
[![Documentation technique](https://img.shields.io/badge/Documentation_technique-226C61?style=for-the-badge&logo=githubpages&logoColor=white)](https://Ki-Mor.github.io/biblizou/)
[![Bug tracker](https://img.shields.io/badge/Bug_tracking-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Ki-Mor/biblizou/issues)
[![Page QGIS](https://img.shields.io/badge/Page_QGIS-589632?style=for-the-badge&logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/biblizou/)

## Contribution

* **Auteur** : François Botcazou

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/botcazoufrancois/)
[![ResearchGate](https://img.shields.io/badge/ResearchGate-00CCBB?style=for-the-badge&logo=ResearchGate&logoColor=white)](https://www.researchgate.net/profile/Francois-Botcazou)
[![Portfolio](https://img.shields.io/badge/Portfolio-6F42C1?style=for-the-badge&logo=githubpages&logoColor=white)](https://Ki-Mor.github.io/porfolio/) [![Mail Pro](https://img.shields.io/badge/Mail-purple?style=for-the-badge&logo=proton&logoColor=white)](mailto:francois.botcazou@proton.me)

* **Contributeurs** :

<a href="https://github.com/Ki-Mor/biblizou/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Ki-Mor/biblizou" />
</a>


Le projet est collaboratif. Vous pouvez participer via deux canaux :
* **Workflow Git** : Ouverture d'une *Issue* pour signaler un bug/proposer une évolution, ou soumission directe d'une *Pull Request* (PR).
* **Contact direct** : Envoi de suggestions par e-mail si vous n'utilisez pas Git.
