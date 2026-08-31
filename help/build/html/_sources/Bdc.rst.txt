.. _module-bdc:

Module BDC — Base de Données sur les statuts de Conservation
=============================================================

.. contents:: Sommaire
   :depth: 3
   :local:


Présentation
------------

Le module **BDC Statuts** interroge l'API *TaxRef Statuts* de l'INPN pour récupérer,
pour un département donné, l'ensemble des statuts de protection et de conservation
associés aux taxons présents dans les couches du projet.

Il produit trois tables dans ``biblizou.gpkg`` :

- ``status_data`` — table brute, une ligne par statut par taxon ;
- ``status_data_joined`` — enrichissement de ``status_data`` avec le nom vernaculaire
  et le groupe taxonomique récupérés via l'API TaxRef ;
- une série de **couches pivots** ``Statuts_Pivot_{groupe}`` — une par groupe de statuts
  (protection nationale, directive Habitats, liste rouge…), en format large.


Flux de traitement
------------------

Le module BDC est orchestré par ``BdStatutsProcessingThread`` (``biblizou_worker.py``),
un ``QThread`` PyQt5 qui enchaîne quatre étapes :

.. list-table::
   :header-rows: 1
   :widths: 5 45 35

   * - Étape
     - Description
     - Fonction appelée
   * - 1
     - Requête API Statuts → ``status_data``
     - ``StatusApiToTable.run()``
   * - 2
     - Enrichissement via API TaxRef → ``status_data_joined``
     - ``StatusJoinTaxref.run()``
   * - 3
     - Création des pivots par groupe de statuts
     - ``StatusPivotByGroup.run()``
   * - 4
     - Fin
     - —

.. note::
   L'étape 2 est **non bloquante** : en cas d'échec (par exemple si l'API TaxRef est
   inaccessible), le workflow continue avec ``status_data`` seule, et les pivots
   sont construits à partir de cette table de repli.

Le thread émet les signaux ``progress(int, int, str)``, ``log(str)``,
``finished(str)`` et ``error(str)``.

**Paramètres transmis par l'interface :**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Clé
     - Valeur
   * - ``gpkg_path``
     - ``{working_folder}/biblizou.gpkg``
   * - ``code_insee``
     - Code INSEE du département sélectionné (ex. ``"14"``, ``"2A"``)
   * - ``consolidation_config``
     - Liste de dicts ``[{'layer_id': '...', 'column': '...'}]`` extraite de ``tableStat``


Étape 1 — Requête API Statuts (``StatusApiToTable``)
------------------------------------------------------

**Fichier :** ``modules/StatusApiToTable.py``

**Fonction principale :** ``run(gpkg_path, code_insee_dept, layer_config, progress_callback, log_callback)``

Déroulement :

1. **Collecte des cd_nom** via ``collect_cdnom_from_config()`` (``ApiUtils``).

2. **Construction du ``locationId``** : ``f"INSEED{code_insee_dept}"``
   (ex. ``"INSEED14"`` pour le Calvados).

3. **Requêtage par lots** (``BATCH_SIZE = 50``) :

   - Pour chaque lot, appel ``GET`` à l'endpoint ``/api/status/search/lines``
     avec les paramètres ``locationId``, ``taxrefId`` (répété par taxon),
     ``page=1`` et ``size=10000``.
   - Retry exponentiel : jusqu'à ``MAX_RETRIES = 3`` tentatives avec pause de 2 s.
   - Pause de 0,3 s entre chaque lot pour ménager l'API.

4. **Aplatissement des réponses** : pour chaque statut retourné dans
   ``_embedded.status``, extraction des champs suivants :

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Champ extrait
     - Source dans la réponse API
   * - ``cdnom``
     - ``taxon.id``
   * - ``scientificName``
     - ``taxon.scientificName``
   * - ``statusTypeName``
     - ``statusTypeName``
   * - ``statusTypeGroup``
     - ``statusTypeGroup`` (ex. *Protection nationale*, *Liste rouge*, *Directive Habitats*)
   * - ``statusCode``
     - ``statusCode`` (ex. *PN*, *EN*, *LC*, *II*)
   * - ``statusName``
     - ``statusName``
   * - ``locationId``
     - ``locationId``
   * - ``locationName``
     - ``locationName``
   * - ``statusRemarks``
     - ``statusRemarks`` (tronqué à 500 caractères)
   * - ``source``
     - ``source`` (tronqué à 1 000 caractères)

5. **Export GPKG** vers la table ``status_data`` via ``LayerUtils.save_to_gpkg()``.

**Endpoint API :**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Paramètre
     - Valeur
   * - URL de base
     - ``https://taxref.mnhn.fr/api/status/search/lines``
   * - ``locationId``
     - ``INSEED{code_insee}`` — identifiant départemental INPN
   * - ``taxrefId``
     - Répété pour chaque cd_nom du lot (max 50)
   * - ``page`` / ``size``
     - ``1`` / ``10000``
   * - Timeout
     - 30 secondes
   * - En-tête
     - ``accept: application/hal+json;version=1``


Étape 2 — Enrichissement TaxRef (``StatusJoinTaxref``)
-------------------------------------------------------

**Fichier :** ``modules/StatusJoinTaxref.py``

**Fonction principale :** ``run(gpkg_path, progress_callback, log_callback)``

Déroulement :

1. **Chargement** de ``status_data`` depuis le GeoPackage.

2. **Extraction des ``cdnom`` distincts** (nettoyage des éventuels suffixes décimaux
   hérités du stockage ``QVariant.String``).

3. **Requêtage API TaxRef** — pour chaque ``cdnom`` unique :

   - ``GET https://taxref.mnhn.fr/api/taxa/{cdnom}`` (timeout 10 s, ``MAX_RETRIES = 2``).
   - Extraction de ``vernacularName1`` (ou ``nomVern`` en repli) → champ ``nom_vern``.
   - Extraction de ``classe`` (ou ``ordre``, ou ``groupe`` en repli) → champ ``groupe``.
   - Pause de 0,15 s entre chaque appel.

4. **Construction de** ``status_data_joined`` : copie de toutes les lignes de
   ``status_data`` auxquelles sont ajoutées les deux colonnes ``nom_vern`` et ``groupe``.

5. **Export GPKG** vers la table ``status_data_joined``
   (via ``QgsVectorFileWriter.writeAsVectorFormatV3`` en mode ``CreateOrOverwriteLayer``).

.. note::
   Cette étape ne s'appuie **pas** sur la table ``data_taxref`` produite par le module
   :ref:`module-taxref`. Elle appelle directement l'API TaxRef pour éviter toute dépendance
   à l'exécution préalable du module TaxRef.


Étape 3 — Pivots par groupe (``StatusPivotByGroup``)
------------------------------------------------------

**Fichier :** ``modules/StatusPivotByGroup.py``

**Fonction principale :** ``run(gpkg_path, progress_callback, log_callback)``

Déroulement :

1. **Chargement de la source** : tente d'abord ``status_data_joined``,
   se replie sur ``status_data`` si la première est absente ou invalide.
   La couche est ajoutée temporairement au projet QGIS (requis pour les couches virtuelles).

2. **Détection du champ vernaculaire** (``_get_vernacular_field()``) :
   recherche dans l'ordre ``nom_vern``, ``vernacularName1``, ``nomVern``,
   ``taxref_vernacularName1``, ``taxref_nomVern`` ; se replie sur ``scientificName``.

3. **Collecte des groupes et types** : itération sur toutes les entités pour
   construire le dictionnaire ``{statusTypeGroup → {statusTypeName, ...}}``.

4. **Génération d'une couche virtuelle par groupe** :

   Pour chaque ``statusTypeGroup``, une requête SQL de type pivot est construite :

   .. code-block:: sql

      SELECT cdnom, scientificName AS nom_latin, "{nom_vern}" AS nom_vernaculaire,
        MAX(CASE WHEN statusTypeName = 'Protection nationale' THEN statusCode END) AS "Protection nationale",
        MAX(CASE WHEN statusTypeName = 'Liste rouge nationale' THEN statusCode END) AS "Liste rouge nationale",
        ...
      FROM "{layer_id}"
      WHERE statusTypeGroup = '{groupe}'
      GROUP BY cdnom, scientificName, "{nom_vern}"
      ORDER BY scientificName

   La requête référence la table par **ID interne QGIS** (``layer.id()``) pour éviter
   les conflits de nommage.

5. **Nommage et ajout au projet** : la couche est nommée
   ``Statuts_Pivot_{groupe_nettoyé}``, où le nom du groupe est assaini par
   ``_sanitize_layer_name()`` (remplacement des caractères non alphanumériques par ``_``).
   Une couche éponyme déjà présente dans le projet est supprimée avant l'ajout.

.. note::
   Les couches pivot ``Statuts_Pivot_*`` sont des **couches virtuelles QGIS** (non persistées
   dans le GeoPackage). Elles dépendent de la présence de ``status_data_joined`` ou
   ``status_data`` dans le projet QGIS. Pour les rendre persistantes, l'utilisateur doit
   les exporter manuellement via :menuselection:`Couche --> Enregistrer sous`.


Tables et couches produites
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Nom
     - Support
     - Contenu
   * - ``status_data``
     - GPKG
     - Table brute : une ligne par statut par taxon, 10 champs
   * - ``status_data_joined``
     - GPKG
     - ``status_data`` enrichie avec ``nom_vern`` et ``groupe`` (API TaxRef)
   * - ``Statuts_Pivot_{groupe}``
     - Couche virtuelle QGIS
     - Une couche par ``statusTypeGroup`` ; colonnes = types de statuts, valeurs = codes


Structure de ``status_data``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Champ
     - Type
     - Description
   * - ``cdnom``
     - String
     - Code TaxRef du taxon
   * - ``scientificName``
     - String
     - Nom scientifique
   * - ``statusTypeName``
     - String
     - Type de statut (ex. *Protection nationale*, *Directive Oiseaux*)
   * - ``statusTypeGroup``
     - String
     - Groupe de statuts (ex. *Protection*, *Liste rouge*, *Réglementation*)
   * - ``statusCode``
     - String
     - Code du statut (ex. *PN*, *LC*, *EN*, *II*)
   * - ``statusName``
     - String
     - Libellé du statut
   * - ``locationId``
     - String
     - Identifiant de localisation INPN (ex. ``INSEED14``)
   * - ``locationName``
     - String
     - Nom du territoire (ex. *Calvados*)
   * - ``statusRemarks``
     - String
     - Remarques (tronqué à 500 caractères)
   * - ``source``
     - String
     - Source bibliographique du statut (tronqué à 1 000 caractères)

``status_data_joined`` reprend tous ces champs et y ajoute :

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Champ ajouté
     - Type
     - Description
   * - ``nom_vern``
     - String
     - Nom vernaculaire français (API TaxRef)
   * - ``groupe``
     - String
     - Groupe taxonomique — classe, ordre ou groupe selon disponibilité (API TaxRef)


Référence des fichiers source
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Fichier
     - Rôle
   * - ``modules/base/ApiUtils.py``
     - Collecte des ``cd_nom`` et création de la session HTTP
   * - ``modules/base/LayerUtils.py``
     - Export des tables vers le GeoPackage
   * - ``modules/StatusApiToTable.py``
     - Requêtage API Statuts, création de ``status_data``
   * - ``modules/StatusJoinTaxref.py``
     - Enrichissement API TaxRef, création de ``status_data_joined``
   * - ``modules/StatusPivotByGroup.py``
     - Génération des couches virtuelles pivot par groupe de statuts
   * - ``biblizou_worker.py``
     - ``BdStatutsProcessingThread`` — orchestration du thread
   * - ``biblizou_dockwidget.py``
     - Collecte des paramètres (département, couches sources) et lancement du thread