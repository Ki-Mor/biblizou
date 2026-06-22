.. _module-fsd:

Module FSD — Formulaires Standards de Données
==============================================

.. contents:: Sommaire
   :depth: 3
   :local:

Présentation
------------

Le module **FSD** automatise le moissonnage des données issues des Formulaires Standards de Données (FSD)
des zonages naturels intersectant l'aire d'étude. Il traite deux référentiels complémentaires :

- **Natura 2000** : sites SIC (*Sites d'Importance Communautaire*) et ZPS (*Zones de Protection Spéciale*),
  dont les FSD sont publiés au format XML par l'INPN à l'adresse
  ``https://inpn.mnhn.fr/docs/natura2000/fsdxml/{zone_id}.xml``.

- **ZNIEFF** : inventaires de type I et II (*Zones Naturelles d'Intérêt Écologique, Faunistique et Floristique*),
  dont les fiches XML sont publiées à l'adresse
  ``https://inpn.mnhn.fr/docs/ZNIEFF/znieffxml/{zone_id}.xml``.

Pour chaque référentiel, le module produit trois couches attributaires (sans géométrie) enregistrées
dans un GeoPackage ``biblizou.gpkg``, puis deux tableaux croisés dynamiques (pivots) facilitant
la lecture bibliographique.

.. note::
   Les étapes de téléchargement XML (``NaturaDwlXml``, ``ZnieffDwlXml``) sont actuellement
   désactivées dans le workflow automatique. L'utilisateur doit déposer manuellement les fichiers
   XML dans le dossier de travail avant de lancer le traitement.


Flux de traitement
------------------

Le module FSD est orchestré par ``FsdProcessingThread`` (``biblizou_worker.py``),
un ``QThread`` PyQt5 qui enchaîne les étapes suivantes dans cet ordre :

.. list-table::
   :header-rows: 1
   :widths: 5 40 30

   * - Étape
     - Description
     - Classe / Fonction appelée
   * - 1
     - Configuration des connexions WFS INPN
     - ``WfsManager.setup_wfs_connections()``
   * - 2
     - Chargement des couches WFS dans le projet
     - ``WfsManager.load_wfs_layers()``
   * - 3
     - Extraction des descriptions ZNIEFF
     - ``ZnieffXmlToLayerDesc``
   * - 4
     - Extraction des espèces ZNIEFF
     - ``ZnieffXmlToLayerEsp``
   * - 5
     - Extraction des habitats déterminants ZNIEFF
     - ``ZnieffXmlToLayerHab``
   * - 6
     - Extraction des descriptions Natura 2000
     - ``NaturaXmlToLayerDesc``
   * - 7
     - Extraction des espèces Natura 2000
     - ``NaturaXmlToLayerEsp``
   * - 8
     - Extraction des habitats Natura 2000
     - ``NaturaXmlToLayerHab``
   * - 9
     - Tableau croisé espèces déterminantes ZNIEFF
     - ``ZnieffPivotEspeces``
   * - 10
     - Tableau croisé habitats déterminants ZNIEFF
     - ``ZnieffPivotHabitats``
   * - 11
     - Tableau croisé espèces Natura 2000
     - ``NaturaPivotEspeces``
   * - 12
     - Tableau croisé habitats Natura 2000
     - ``NaturaPivotHabitats``

.. note::
   Les étapes de pivot (9 à 12) ne sont exécutées que si les étapes d'extraction correspondantes
   ont produit des données (flags ``_has_znieff_esp``, ``_has_znieff_hab``, ``_has_natura_esp``,
   ``_has_natura_hab`` positionnés par le thread).

Le thread émet trois signaux PyQt5 :

- ``progress(int, int, str)`` — numéro d'étape, total, libellé
- ``log(str)`` — messages textuels
- ``finished(str)`` / ``error(str)`` — résultat final


Architecture des classes de base
---------------------------------

Le module FSD repose sur deux classes abstraites mutualisées définies dans ``modules/base/``.


DwlXml (``base/DwlXml.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Classe abstraite gérant le **téléchargement des fichiers XML** depuis l'INPN.
Elle s'appuie sur les couches WFS Patrinat déjà chargées dans le projet pour
déterminer, par intersection spatiale avec l'aire d'étude, les identifiants de zones à télécharger.

**Méthodes abstraites** (à implémenter dans les classes enfants) :

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Méthode
     - Rôle
   * - ``get_patrinat_layer_names() → tuple``
     - Noms des deux couches WFS Patrinat à rechercher dans le projet QGIS
   * - ``build_url(zone_id: str) → str``
     - Construction de l'URL de téléchargement pour un identifiant de zone

**Méthodes concrètes mutualisées** :

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Méthode
     - Rôle
   * - ``run_with_path(reference_layer, folder_path)``
     - Point d'entrée : orchestre la recherche des couches, la sélection spatiale et le téléchargement
   * - ``find_patrinat_layers()``
     - Recherche les deux couches Patrinat par nom dans le projet QGIS
   * - ``selectionner_et_stocker(couche_source, liste_stockage)``
     - Sélection spatiale par intersection avec l'aire d'étude ; stockage des ``id_mnhn``
   * - ``download_file(url, save_path, retries=3)``
     - Téléchargement HTTP avec retry exponentiel (1, 2, 4 secondes)
   * - ``execute_download()``
     - Lance la sélection spatiale sur les deux couches puis télécharge tous les XML

**Sélection spatiale** : la géométrie de la couche de référence (aire d'étude) est reprojetée
dans le SCR de la couche WFS, puis une requête par boîte englobante filtre les candidats avant
une vérification exacte d'intersection (``intersects``). Seuls les ``id_mnhn`` des entités
intersectantes sont conservés.


XmlToLayer (``base/XmlToLayer.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Classe abstraite gérant le **parsing des fichiers XML** et la **création des couches QGIS**.
Elle suit le patron *Template Method* : le squelette du traitement est fixé dans les méthodes
concrètes, les classes enfants n'implémentent que les quatre méthodes abstraites.

**Méthodes abstraites** :

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Méthode
     - Rôle
   * - ``get_layer_name() → str``
     - Nom de la couche QGIS et du layer dans le GeoPackage
   * - ``get_xml_filter() → callable``
     - Fonction lambda filtrant les fichiers XML du dossier par nom
   * - ``process_xml_file(xml_path) → list``
     - Parsing d'un fichier XML ; retourne une liste de dictionnaires
   * - ``create_temp_layer(data) → QgsVectorLayer``
     - Création de la couche mémoire QGIS (sans géométrie) avec les champs appropriés

**Méthodes concrètes mutualisées** :

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Méthode
     - Rôle
   * - ``run_with_path(folder_path)``
     - Point d'entrée : parcourt le dossier, crée la couche, sauvegarde et charge depuis le GPKG
   * - ``process_folder(folder_path)``
     - Liste les fichiers XML éligibles et appelle ``process_xml_file()`` sur chacun
   * - ``save_to_geopackage(layer)``
     - Délègue à ``LayerUtils.save_to_gpkg()`` ; met à jour le flag ``gpkg_saved``
   * - ``load_from_geopackage()``
     - Charge la couche depuis le GPKG et la substitue dans le projet via ``LayerUtils.replace_layer()``

**Valeurs de retour de** ``run_with_path()`` :

- ``True`` — données trouvées, couche créée et chargée
- ``None`` — aucune donnée dans le dossier (situation normale, sans erreur)
- ``False`` — erreur technique


PivotLayer (``base/PivotLayer.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Classe abstraite gérant la **création des tableaux croisés dynamiques** (format large)
à partir des couches attributaires produites par ``XmlToLayer``.
Chaque colonne représente un site ; chaque ligne une espèce ou un habitat.
La requête SQL est exécutée via une couche virtuelle QGIS (provider ``virtual``).

**Méthodes abstraites** :

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Méthode
     - Rôle
   * - ``get_source_layer_name() → str``
     - Nom de la couche source à lire dans le projet QGIS
   * - ``get_output_layer_name() → str``
     - Nom de la couche pivot à créer
   * - ``get_site_keys() → tuple``
     - Paire ``(code_field, name_field)`` pour extraire les sites depuis la couche source
   * - ``build_pivot_query() → str``
     - Requête SQL ``SELECT … CASE WHEN … GROUP BY`` complète

**Méthodes concrètes mutualisées** :

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Méthode
     - Rôle
   * - ``run(gpkg_path)``
     - Orchestre le chargement de la source, la génération SQL, la création du pivot et l'export GPKG
   * - ``get_sites() → dict``
     - Extrait les paires ``{code: nom}`` uniques depuis la couche source
   * - ``create_virtual_layer(sql_query)``
     - Crée et substitue la couche virtuelle dans le projet
   * - ``export_to_geopackage(layer, gpkg_path)``
     - Sauvegarde persistante via ``LayerUtils.save_to_gpkg()``
   * - ``col_alias(code, name) → str``
     - Génère l'alias de colonne au format ``[CODE] - NOM_SANS_ACCENTS``

**Nommage des colonnes** : les accents sont supprimés (normalisation NFD) et le nom est mis
en majuscules. Exemple : ``FR2500093 - BAIE DU MONT-SAINT-MICHEL``.


LayerUtils (``base/LayerUtils.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Classe utilitaire statique centralisant toutes les opérations sur les couches QGIS.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Méthode statique
     - Rôle
   * - ``get_layer(name) → QgsVectorLayer``
     - Retourne la première couche du projet correspondant au nom exact
   * - ``layer_is_ready(name) → bool``
     - Vérifie qu'une couche existe, est valide et contient des entités
   * - ``replace_layer(layer) → bool``
     - Supprime atomiquement l'ancienne version d'une couche et ajoute la nouvelle
   * - ``load_from_gpkg(gpkg_path, name) → QgsVectorLayer``
     - Charge un layer spécifique depuis un GeoPackage
   * - ``create_empty_gpkg(gpkg_path) → bool``
     - Crée physiquement un GeoPackage vide s'il n'existe pas
   * - ``save_to_gpkg(layer, gpkg_path) → tuple[bool, str]``
     - Exporte n'importe quelle couche (y compris virtuelle) dans un GeoPackage via ``QgsVectorFileWriter``


Volet Natura 2000
-----------------

Téléchargement — ``NaturaDwlXml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``NaturaDwlXml`` hérite de ``DwlXml`` et spécialise le téléchargement pour les sites Natura 2000.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Méthode implémentée
     - Valeur retournée
   * - ``get_patrinat_layer_names()``
     - ``('Patrinat : SIC', 'Patrinat : ZPS')``
   * - ``build_url(zone_id)``
     - ``https://inpn.mnhn.fr/docs/natura2000/fsdxml/{zone_id}.xml``

**Filtre des fichiers XML** lors du parsing aval : fichiers dont le nom commence par ``FR``,
se termine par ``.xml`` et comporte exactement 13 caractères (ex : ``FR2500093.xml``).


Extraction des descriptions — ``NaturaXmlToLayerDesc``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse les balises ``SITECODE``, ``SITE_NAME`` et ``COMMENTAIRE/COMMENTAIRE_ROW``
de chaque fichier XML Natura 2000.

**Couche produite** : ``Natura_2000_Descriptions``

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Champ
     - Type
     - Description
   * - ``SITECODE``
     - String
     - Code officiel du site Natura 2000 (ex : ``FR2500093``)
   * - ``SITE_NAME``
     - String
     - Nom du site
   * - ``QUALITY``
     - String
     - Valeur écologique et intérêt du site (balise ``QUALITY``)
   * - ``VULNAR``
     - String
     - Vulnérabilités et menaces identifiées (balise ``VULNAR``)
   * - ``HTML_POPUP``
     - String
     - Popup HTML stylisée pour l'affichage QGIS (couleur ``#009999``)

``setDisplayExpression("SITE_NAME")`` est appliqué après chargement depuis le GeoPackage.


Extraction des habitats — ``NaturaXmlToLayerHab``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse les balises ``HABIT1_ROW`` de chaque fichier XML Natura 2000.

**Couche produite** : ``Natura_2000_Habitats``

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Champ
     - Type
     - Description
   * - ``SITECODE``
     - String
     - Code du site Natura 2000
   * - ``SITE_NAME``
     - String
     - Nom du site
   * - ``CD_UE``
     - String
     - Code habitat directive Habitats (ex : ``6210``)
   * - ``LB_HABDH_FR``
     - String
     - Libellé français de l'habitat directive

Seules les lignes comportant au moins un code ``CD_UE`` ou un libellé ``LB_HABDH_FR`` sont retenues.


Extraction des espèces — ``NaturaXmlToLayerEsp``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse les balises ``BIOTOP/SPECIES/SPECIES_ROW`` de chaque fichier XML.
Cette classe fonctionne en **mode hors-ligne** (sans appel à l'API TaxRef).

**Couche produite** : ``Natura_2000_Especes``

La couche comporte **43 champs** correspondant à l'intégralité des balises ``SPECIES_ROW``,
dont les principaux :

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Champ
     - Type
     - Description
   * - ``SITECODE`` / ``SITE_NAME``
     - String
     - Identifiants du site
   * - ``CD_NOM``
     - String
     - Code TaxRef de l'espèce
   * - ``NOM``
     - String
     - Nom scientifique
   * - ``TAXGROUP``
     - String
     - Groupe taxonomique (Oiseaux, Mammifères, etc.)
   * - ``ANNEXE_II``
     - String
     - Inscription à l'annexe II de la directive Habitats
   * - ``POPULATION``
     - String
     - Évaluation de la population sur le site
   * - ``CONSERVE``
     - String
     - État de conservation
   * - ``TENDANCE``
     - String
     - Tendance d'évolution de la population
   * - ``UUID_SPECIES``
     - String
     - Identifiant UUID de l'espèce dans la base INPN


Tableau croisé des habitats — ``NaturaPivotHabitats``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transforme ``Natura_2000_Habitats`` (format long) en tableau large avec un site par colonne.

**Couche produite** : ``Natura_2000_Habitats_Pivot``

- Colonnes fixes : ``CD_UE``, ``LB_HABDH_FR``
- Colonnes dynamiques : une par site, nommée ``[SITECODE] - NOM_SITE``
- Valeur : ``1`` si l'habitat est présent sur le site, ``NULL`` sinon
- Tri : par ``CD_UE`` croissant

**Requête SQL générée** (exemple simplifié) :

.. code-block:: sql

   SELECT CD_UE, LB_HABDH_FR,
     MAX(CASE WHEN SITECODE = 'FR2500093' THEN 1 END) AS "FR2500093 - BAIE DU MONT-SAINT-MICHEL",
     MAX(CASE WHEN SITECODE = 'FR2500094' THEN 1 END) AS "FR2500094 - DUNES DE ..."
   FROM "Natura_2000_Habitats"
   GROUP BY CD_UE, LB_HABDH_FR
   ORDER BY CD_UE


Tableau croisé des espèces — ``NaturaPivotEspeces``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transforme ``Natura_2000_Especes`` en tableau large.

**Couche produite** : ``Natura_2000_Especes_Pivot``

- Colonnes fixes : ``GROUPE`` (alias de ``TAXGROUP``), ``CD_NOM``, ``NOM``
- Colonnes dynamiques : une par site, nommée ``[SITECODE] - NOM_SITE``
- Valeur : ``1`` si l'espèce est présente, ``NULL`` sinon
- Tri : par groupe puis par nom croissant

.. note::
   La requête SQL référence la couche par son **ID interne QGIS** (``layer.id()``) plutôt
   que par son nom, afin d'éviter les conflits lorsque le nom contient des espaces ou des
   caractères spéciaux.


Volet ZNIEFF
------------

Téléchargement — ``ZnieffDwlXml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ZnieffDwlXml`` hérite de ``DwlXml`` et spécialise le téléchargement pour les inventaires ZNIEFF.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Méthode implémentée
     - Valeur retournée
   * - ``get_patrinat_layer_names()``
     - ``('Patrinat : ZNIEFF1', 'Patrinat : ZNIEFF2')``
   * - ``build_url(zone_id)``
     - ``https://inpn.mnhn.fr/docs/ZNIEFF/znieffxml/{zone_id}.xml``

**Filtre des fichiers XML** lors du parsing aval : fichiers se terminant par ``.xml``,
de 13 caractères, ne commençant **pas** par ``FR`` (convention ZNIEFF).


Extraction des descriptions — ``ZnieffXmlToLayerDesc``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse les balises de description de chaque fichier XML ZNIEFF. Les fichiers peuvent
contenir des balises ``<p>`` imbriquées dans les champs texte longs (``TX_GENE``, ``TX_GEO``,
``TX_ACTH``…) ; la méthode ``_rich_text()`` gère cette ambivalence.

**Couche produite** : ``Znieff_Descriptions``

La couche comporte **39 champs**, dont les principaux :

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Champ
     - Type
     - Description
   * - ``NM_SFFZN``
     - String
     - Numéro national ZNIEFF
   * - ``LB_ZN``
     - String
     - Nom de la ZNIEFF
   * - ``TY_ZONE``
     - String
     - Type de zone (1 ou 2)
   * - ``SU_ZN``
     - Double
     - Superficie en hectares
   * - ``ALT_MINI`` / ``ALT_MAXI``
     - Double
     - Altitudes minimale et maximale
   * - ``DESCRIPTION``
     - String
     - Texte général de description (balise ``TX_GENE``)
   * - ``TX_ACTH``
     - String
     - Activités humaines
   * - ``TX_MESPRO``
     - String
     - Mesures de protection
   * - ``TX_INTERET``
     - String
     - Intérêt du site
   * - ``DATE_CREA`` / ``DATE_MODIF``
     - String
     - Dates de création et de dernière modification
   * - ``ZNI_NM_SFFZN`` / ``ZNI_LB_ZN``
     - String
     - Identifiants de la ZNIEFF parente (balise ``ZNI``)
   * - ``HTML_POPUP``
     - String
     - Popup HTML stylisée pour l'affichage QGIS

``setDisplayExpression`` appliqué : ``coalesce(LB_ZN, '') || ' (' || coalesce(NM_SFFZN, '') || ')'``

.. note::
   Les champs numériques (``SU_ZN``, ``ALT_MINI``, ``ALT_MAXI``, ``PROF_MINI``, ``PROF_MAXI``,
   ``X_L2E``, ``Y_L2E``) font l'objet d'une conversion explicite ``_to_double()`` lors de la
   création de la couche, avec nettoyage des virgules décimales et des caractères parasites.


Extraction des espèces — ``ZnieffXmlToLayerEsp``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse les balises ``ESPECE_PROJET_ROW`` et ``ESPECE_ROW`` des fichiers XML ZNIEFF.

**Couche produite** : ``Znieff_Especes``

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Champ
     - Type
     - Description
   * - ``nm_sffzn``
     - String
     - Numéro ZNIEFF (issu de la ligne espèce ou de la racine XML)
   * - ``lb_zn``
     - String
     - Nom de la ZNIEFF
   * - ``groupe``
     - String
     - Groupe taxonomique
   * - ``cd_nom``
     - String
     - Code TaxRef
   * - ``nom_complet``
     - String
     - Nom scientifique complet
   * - ``nom_vern``
     - String
     - Nom vernaculaire
   * - ``fg_esp``
     - String
     - Flag espèce déterminante (``D`` = déterminante)
   * - ``fg_conf``
     - String
     - Flag de confidentialité
   * - ``origine``
     - String
     - Origine de la donnée


Extraction des habitats — ``ZnieffXmlToLayerHab``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse les balises ``TYPO_INFO_ROW`` des fichiers XML ZNIEFF.
Seuls les habitats **déterminants** (``FG_TYPO = 'D'``) sont retenus.

**Couche produite** : ``Znieff_Habitats``

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Champ
     - Type
     - Description
   * - ``NM_SFFZN``
     - String
     - Numéro ZNIEFF
   * - ``LB_ZN``
     - String
     - Nom de la ZNIEFF
   * - ``LB_CODE``
     - String
     - Code de l'habitat (référentiel CORINE Biotopes ou autre)
   * - ``LB_HAB``
     - String
     - Libellé de l'habitat


Tableau croisé des habitats — ``ZnieffPivotHabitats``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transforme ``Znieff_Habitats`` en tableau large.

**Couche produite** : ``Znieff_Hab_Pivot``

- Colonnes fixes : ``LB_CODE``, ``LB_HAB``
- Colonnes dynamiques : une par ZNIEFF, nommée ``[NM_SFFZN] - NOM_ZNIEFF``
- Valeur : ``1`` si l'habitat est présent, ``NULL`` sinon
- Tri : par ``LB_CODE`` croissant


Tableau croisé des espèces déterminantes — ``ZnieffPivotEspeces``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transforme ``Znieff_Especes`` en tableau large, filtré sur les espèces déterminantes
(``fg_esp = 'D'``).

**Couche produite** : ``Znieff_EspDet_Pivot``

- Colonnes fixes : ``GROUPE``, ``cd_nom``, ``nom_complet``, ``nom_vern``
- Colonnes dynamiques : une par ZNIEFF avec des espèces déterminantes, nommée ``[NM_SFFZN] - NOM_ZNIEFF``
- Valeur : ``1`` si l'espèce est déterminante sur cette ZNIEFF, ``NULL`` sinon
- Tri : par groupe puis par ``nom_complet`` croissant

.. note::
   La méthode ``get_sites()`` est **surchargée** dans cette classe afin de ne collecter
   que les sites ayant au moins une espèce déterminante (``fg_esp = 'D'``), réduisant ainsi
   le nombre de colonnes dans le pivot.

   Comme ``NaturaPivotEspeces``, la requête SQL référence la couche source par son ID interne
   QGIS pour éviter les conflits de nommage.


Connexions WFS — ``WfsManager``
--------------------------------

``WfsManager`` configure dans le registre QGIS (``QSettings``) la connexion au service WFS
de l'IGN/INPN (``data.geopf.fr``) et charge dans le projet les quatre couches de zonage
utilisées comme référence spatiale par ``DwlXml``.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Nom de couche dans le projet
     - Typename WFS
   * - ``Patrinat : ZPS``
     - ``patrinat_zps:zps``
   * - ``Patrinat : SIC``
     - ``patrinat_sic:sic``
   * - ``Patrinat : ZNIEFF1``
     - ``patrinat_znieff1:znieff1``
   * - ``Patrinat : ZNIEFF2``
     - ``patrinat_znieff2:znieff2``

Toutes les couches sont chargées en ``EPSG:3857``. Une couche déjà présente dans le projet
n'est pas rechargée (vérification par ``mapLayersByName``).


Couches et GeoPackage produits
-------------------------------

Toutes les couches du module FSD sont des couches **attributaires sans géométrie**
(provider ``"None"`` en mémoire, puis exportées en GPKG via ``QgsVectorFileWriter``).

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Nom de la couche / layer GPKG
     - Référentiel
     - Contenu
   * - ``Natura_2000_Descriptions``
     - Natura 2000
     - Descriptions qualité/vulnérabilité par site
   * - ``Natura_2000_Habitats``
     - Natura 2000
     - Habitats directive (format long)
   * - ``Natura_2000_Especes``
     - Natura 2000
     - Espèces directive (format long, 43 champs)
   * - ``Natura_2000_Habitats_Pivot``
     - Natura 2000
     - Tableau croisé habitats × sites
   * - ``Natura_2000_Especes_Pivot``
     - Natura 2000
     - Tableau croisé espèces × sites
   * - ``Znieff_Descriptions``
     - ZNIEFF
     - Descriptions des ZNIEFF (39 champs)
   * - ``Znieff_Especes``
     - ZNIEFF
     - Espèces (toutes, format long)
   * - ``Znieff_Habitats``
     - ZNIEFF
     - Habitats déterminants (format long)
   * - ``Znieff_EspDet_Pivot``
     - ZNIEFF
     - Tableau croisé espèces déterminantes × ZNIEFF
   * - ``Znieff_Hab_Pivot``
     - ZNIEFF
     - Tableau croisé habitats déterminants × ZNIEFF

Toutes ces couches sont enregistrées dans le fichier ``biblizou.gpkg`` situé dans le dossier
de travail défini par l'utilisateur.


Référence des fichiers source
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Fichier
     - Groupe
     - Rôle
   * - ``modules/base/DwlXml.py``
     - base
     - Classe abstraite téléchargement XML
   * - ``modules/base/XmlToLayer.py``
     - base
     - Classe abstraite parsing XML → couche QGIS
   * - ``modules/base/PivotLayer.py``
     - base
     - Classe abstraite tableau croisé dynamique
   * - ``modules/base/LayerUtils.py``
     - base
     - Utilitaires couches QGIS et GeoPackage
   * - ``modules/WfsManager.py``
     - FSD
     - Connexions et chargement WFS INPN
   * - ``modules/NaturaDwlXml.py``
     - FSD
     - Téléchargement XML Natura 2000
   * - ``modules/NaturaXmlToLayerDesc.py``
     - FSD
     - Extraction descriptions Natura 2000
   * - ``modules/NaturaXmlToLayerHab.py``
     - FSD
     - Extraction habitats Natura 2000
   * - ``modules/NaturaXmlToLayerEsp.py``
     - FSD
     - Extraction espèces Natura 2000
   * - ``modules/NaturaPivotHabitats.py``
     - FSD
     - Pivot habitats Natura 2000
   * - ``modules/NaturaPivotEspeces.py``
     - FSD
     - Pivot espèces Natura 2000
   * - ``modules/ZnieffDwlXml.py``
     - FSD
     - Téléchargement XML ZNIEFF
   * - ``modules/ZnieffXmlToLayerDesc.py``
     - FSD
     - Extraction descriptions ZNIEFF
   * - ``modules/ZnieffXmlToLayerHab.py``
     - FSD
     - Extraction habitats déterminants ZNIEFF
   * - ``modules/ZnieffXmlToLayerEsp.py``
     - FSD
     - Extraction espèces ZNIEFF
   * - ``modules/ZnieffPivotHabitats.py``
     - FSD
     - Pivot habitats déterminants ZNIEFF
   * - ``modules/ZnieffPivotEspeces.py``
     - FSD
     - Pivot espèces déterminantes ZNIEFF
   * - ``biblizou_worker.py``
     - —
     - Orchestration des threads de traitement