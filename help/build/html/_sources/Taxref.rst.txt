.. _module-taxref:

Module TaxRef — Consolidation taxonomique
==========================================

.. contents:: Sommaire
   :depth: 3
   :local:


Présentation
------------

Le module **TaxRef** interroge l'API REST de l'INPN pour enrichir les listes d'espèces
du projet avec les données du référentiel taxonomique national **TAXREF**.

Pour chaque code taxon (``cd_nom``) collecté dans les couches vectorielles désignées par
l'utilisateur, le module récupère la fiche complète du taxon (noms, rang, groupes,
synonymies, etc.) et l'enregistre dans la table ``data_taxref`` du GeoPackage ``biblizou.gpkg``.

Cette table sert ensuite de **table de jointure de référence** pour les autres modules,
notamment :ref:`module-bdc` (``StatusJoinTaxref``).


Flux de traitement
------------------

Le module TaxRef est orchestré par ``TaxrefProcessingThread`` (``biblizou_worker.py``),
un ``QThread`` PyQt5 qui exécute une étape unique :

.. list-table::
   :header-rows: 1
   :widths: 5 40 30

   * - Étape
     - Description
     - Classe / Fonction appelée
   * - 1
     - Consolidation des taxons via l'API TaxRef
     - ``TaxrefApiToTable``

Le thread émet les signaux ``progress(int, int, str)``, ``log(str)``,
``finished(str)`` et ``error(str)``.

**Paramètres transmis par l'interface :**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Clé
     - Valeur
   * - ``working_folder``
     - Chemin du dossier de travail
   * - ``gpkg_path``
     - ``{working_folder}/biblizou.gpkg``
   * - ``consolidation_config``
     - Liste de dicts ``[{'layer_id': '...', 'column': '...'}]`` extraite du tableau ``tableTaxref``


Classes et utilitaires
-----------------------

ApiUtils (``base/ApiUtils.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Module utilitaire partagé par les modules TaxRef et BDC Statuts.

``collect_cdnom_from_config(layer_config: list) → list``
   Collecte les valeurs de ``cd_nom`` **uniques** depuis les couches du projet QGIS
   décrites dans ``layer_config``.

   Pour chaque entrée ``{'layer_id', 'column'}`` :

   1. Récupère la couche via ``QgsProject.instance().mapLayer(layer_id)``.
   2. Localise le champ par ``fields().lookupField(column)``.
   3. Itère sur les entités et ne retient que les valeurs numériques
      (nettoyage par ``filter(str.isdigit, ...)`` pour supprimer les éventuels espaces
      ou caractères parasites).
   4. Dédoublonne via un ``set``.

   Retourne une liste de chaînes numériques propres.

``create_taxref_session() → requests.Session``
   Crée et retourne une session ``requests`` préconfigurée avec l'en-tête
   ``accept: application/hal+json;version=1`` requis par l'API TaxRef INPN.


TaxrefApiToTable (``modules/TaxrefApiToTable.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Classe principale du module TaxRef. Hérite de ``QObject`` pour exposer les signaux
PyQt5 ``progress_changed(int)`` et ``status_changed(str)``.

**Constructeur :**

.. code-block:: python

   TaxrefApiToTable(gpkg_path: str)

Initialise la session HTTP via ``create_taxref_session()``.

**Méthode principale :** ``run(layer_config: list) → tuple[bool, str]``

Déroulement détaillé :

1. **Collecte des codes** — appel à ``collect_cdnom_from_config(layer_config)`` ;
   arrêt anticipé si aucun code n'est trouvé.

2. **Requêtage API** — pour chaque ``cd_nom`` unique :

   - Appel ``GET https://taxref.mnhn.fr/api/taxa/{cd_nom}`` (timeout 10 s).
   - En cas de réponse 200, aplatissement du JSON (``{k: str(v) ...}``)
     en excluant les clés commençant par ``_`` (métadonnées HAL).
   - Les clés rencontrées sont accumulées dans ``all_keys`` pour construire
     le schéma dynamiquement.
   - Émission de ``progress_changed`` en pourcentage d'avancement.
   - Les erreurs par taxon sont journalisées sans interrompre la boucle.

3. **Construction du schéma de champs** — tri alphabétique de toutes les clés
   collectées, avec ``cdNom`` placé en première position.

4. **Création de la couche mémoire** — couche ``"None"`` nommée ``data_taxref``
   avec un champ ``QgsField(key, QVariant.String)`` par clé.

5. **Export GPKG** — délégation à ``LayerUtils.save_to_gpkg()``.
   Retourne ``(True, message)`` en succès, ``(False, message_erreur)`` en échec.

.. note::
   Le schéma de la table ``data_taxref`` est **dynamique** : il dépend de l'union
   de toutes les clés retournées par l'API pour l'ensemble des taxons traités.
   Une clé absente pour un taxon donné produit une chaîne vide (``""``) dans ce champ.


Endpoint API TaxRef
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Paramètre
     - Valeur
   * - URL
     - ``https://taxref.mnhn.fr/api/taxa/{cd_nom}``
   * - Méthode
     - ``GET``
   * - En-tête requis
     - ``accept: application/hal+json;version=1``
   * - Timeout
     - 10 secondes
   * - Format de réponse
     - JSON (HAL+JSON)

Principaux champs retournés par l'API (liste non exhaustive) :

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Champ
     - Description
   * - ``cdNom``
     - Code taxon (identifiant numérique)
   * - ``cdRef``
     - Code du taxon de référence (synonymie)
   * - ``nomComplet``
     - Nom scientifique complet avec auteur
   * - ``nomValide``
     - Nom valide selon TaxRef
   * - ``nomVern``
     - Nom vernaculaire français
   * - ``rang``
     - Rang taxonomique (ES, SSES, GN…)
   * - ``famille``
     - Famille
     
   * - ``ordre``
     - Ordre
   * - ``classe``
     - Classe
   * - ``phylum``
     - Phylum
   * - ``regne``
     - Règne
   * - ``group1Inpn``
     - Groupe fonctionnel INPN (niveau 1)
   * - ``group2Inpn``
     - Groupe fonctionnel INPN (niveau 2)


Table produite
--------------

**Nom dans le GeoPackage :** ``data_taxref``

Table attributaire sans géométrie. Le nombre et le nom des colonnes dépendent
des clés retournées par l'API pour l'ensemble des ``cd_nom`` traités.
La colonne ``cdNom`` est toujours positionnée en premier.

.. note::
   Si la table ``data_taxref`` existe déjà dans ``biblizou.gpkg``, elle est
   **écrasée** (mode ``CreateOrOverwriteLayer`` de ``QgsVectorFileWriter``).
   Pour conserver un historique, il convient de sauvegarder le GeoPackage
   avant de relancer le module.


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
     - Export de la couche vers le GeoPackage
   * - ``modules/TaxrefApiToTable.py``
     - Requêtage API et création de la table ``data_taxref``
   * - ``biblizou_worker.py``
     - ``TaxrefProcessingThread`` — orchestration du thread
   * - ``biblizou_dockwidget.py``
     - Collecte des paramètres et lancement du thread depuis l'interface