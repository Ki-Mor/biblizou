.. _interface:

Interface utilisateur
=====================

.. contents:: Sommaire
   :depth: 3
   :local:


Présentation générale
---------------------

Biblizou s'intègre dans QGIS sous la forme d'un **panneau latéral ancrable** (``QDockWidget``),
accessible depuis le menu :menuselection:`Extensions --> Biblizou`.
Le panneau est défini dans ``biblizou_dockwidget_base.ui`` (Qt Designer)
et piloté par ``BiblizouDockWidget`` (``biblizou_dockwidget.py``).

Il se compose de trois zones :

- Un **en-tête** avec le logo et un bouton *[i] Aide*
- Un **sélecteur de dossier de travail**, commun à tous les modules
- Un **widget à onglets** donnant accès aux quatre modules (FSD, TaxRef, BDC Statuts, Botazou)

Tous les traitements sont lancés dans des ``QThread`` distincts afin de ne pas bloquer
l'interface QGIS. La progression est reportée dans la barre de statut principale de QGIS
(``statusBar().showMessage()``) et les messages détaillés dans le panneau
:menuselection:`Vue --> Panneaux --> Journal des messages` sous la catégorie **Biblizou**.


Dossier de travail
------------------

Le widget ``QgsFileWidget`` (``mQgsFileWidget``) en mode *GetDirectory* est commun à
l'ensemble des modules. Il désigne le dossier dans lequel :

- les fichiers XML téléchargés ou déposés manuellement doivent se trouver ;
- le fichier ``biblizou.gpkg`` sera créé ou mis à jour par tous les modules.

Une validation bloque l'exécution de tout workflow si le chemin est absent ou invalide.


Onglet FSD
----------

Cet onglet permet de lancer le moissonnage des Formulaires Standards de Données
(voir :ref:`module-fsd`).

**Widgets de saisie :**

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Widget (nom objet)
     - Type
     - Rôle
   * - ``mapLayerZnieff``
     - ``QgsMapLayerComboBox``
     - Couche polygonale de référence pour les ZNIEFF (filtre : couches polygonales uniquement)
   * - ``mapLayerN2k``
     - ``QgsMapLayerComboBox``
     - Couche polygonale de référence pour les sites Natura 2000 (filtre : couches polygonales uniquement)
   * - ``mQgsFileWidget``
     - ``QgsFileWidget``
     - Dossier de travail contenant les fichiers XML

.. note::
   Les couches de référence sélectionnées dans cet onglet ne sont **pas transmises** au thread
   de traitement ``FsdProcessingThread`` : seul le chemin ``working_folder`` lui est passé.
   La sélection spatiale dans ``DwlXml`` s'effectue en interrogeant directement le projet QGIS
   (via ``QgsProject.instance()``), ce qui suppose que les couches WFS Patrinat sont déjà
   chargées dans le projet.

**Validation** (``validate_fsd()``) :

- La couche ZNIEFF de référence doit être sélectionnée.
- La couche Natura 2000 de référence doit être sélectionnée.
- Le dossier de travail doit exister sur le disque.

**Bouton** ``btnRunFsd`` — *Lancer le moissonnage FSD* :

1. Appel de ``validate_fsd()``.
2. Affichage d'une boîte de confirmation récapitulant le dossier de travail.
3. Instanciation de ``FsdProcessingThread`` et connexion de ses signaux.
4. Démarrage du thread ; le bouton est désactivé pendant l'exécution.
5. À la fin (signal ``finished``), réactivation du bouton et message de succès.


Onglet TaxRef
-------------

Cet onglet permet de consolider les taxons présents dans des couches du projet
avec le référentiel national TaxRef via l'API INPN
(voir :ref:`module-taxref`).

**Widgets de saisie :**

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Widget (nom objet)
     - Type
     - Rôle
   * - ``tableTaxref``
     - ``QTableWidget`` (3 colonnes)
     - Table de configuration des sources de ``cd_nom``
   * - ``btnAddLayerRowTaxtef``
     - ``QPushButton``
     - Ajoute une ligne dans ``tableTaxref``

**Structure du tableau ``tableTaxref``** :

Chaque ligne correspond à une source de codes taxons :

.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Colonne
     - Type de widget
     - Rôle
   * - 0
     - ``QgsMapLayerComboBox`` (couches vectorielles)
     - Couche source contenant les ``cd_nom``
   * - 1
     - ``QgsFieldComboBox`` (synchronisé avec col. 0)
     - Champ de la couche contenant les ``cd_nom``
   * - 2
     - ``QPushButton`` (icône croix)
     - Supprime la ligne

Les colonnes 0 et 1 sont extensibles ; la colonne 2 s'ajuste au contenu.

**Validation** (``validate_taxref()``) :

- Le dossier de travail doit être valide.
- Au moins une ligne doit être configurée dans ``tableTaxref``.

**Bouton** ``btnRunTaxref`` — *Lancer la consolidation TaxRef* :

1. Appel de ``validate_taxref()``.
2. Extraction des paires ``{layer_id, column}`` depuis ``tableTaxref``
   via ``get_taxref_consolidation_data()``.
3. Confirmation indiquant le nombre de couches à traiter.
4. Instanciation de ``TaxrefProcessingThread`` avec les paramètres
   ``working_folder``, ``consolidation_config`` et ``gpkg_path``.
5. Démarrage du thread.


Onglet BDC Statuts
------------------

Cet onglet permet d'interroger la Base de Données sur les statuts de conservation
de l'INPN et de consolider les résultats avec les taxons du projet
(voir :ref:`module-bdc`).

**Widgets de saisie :**

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Widget (nom objet)
     - Type
     - Rôle
   * - ``comboBoxDpt``
     - ``QComboBox`` éditable + ``QCompleter``
     - Sélection du département de référence (filtrage par nom, stocke le ``code_insee``)
   * - ``tableStat``
     - ``QTableWidget`` (3 colonnes)
     - Table de configuration des sources de ``cd_nom`` pour les statuts
   * - ``btnAddLayerRowStat``
     - ``QPushButton``
     - Ajoute une ligne dans ``tableStat``

**Liste déroulante département** (``comboBoxDpt``) :

Alimentée depuis ``config/dept_fr.csv`` (colonnes ``nom_officiel``, ``code_insee``).
La liste est rendue éditable et dotée d'un ``QCompleter`` en mode ``MatchContains``
(insensible à la casse) permettant de filtrer les départements en saisissant
n'importe quelle partie du nom.
La **valeur stockée** (``currentData()``) est le ``code_insee``, transmis à l'API.

**Structure du tableau ``tableStat``** : identique à ``tableTaxref`` (couche + champ + supprimer).

**Validation** (``validate_stat()``) :

- Le dossier de travail doit être valide.
- Un département doit être sélectionné (``currentData()`` non nul).
- Au moins une ligne doit être configurée dans ``tableStat``.

**Bouton** ``btnRunStat`` — *Associer à la BDC* :

1. Appel de ``validate_stat()``.
2. Confirmation récapitulant le département, le nombre de couches et le chemin du GeoPackage.
3. Instanciation de ``BdStatutsProcessingThread`` avec les paramètres
   ``gpkg_path``, ``code_insee`` et ``consolidation_config``.
4. Démarrage du thread.


Comportement commun aux threads
---------------------------------

Les trois threads (``FsdProcessingThread``, ``TaxrefProcessingThread``,
``BdStatutsProcessingThread``) partagent le même schéma de signaux et de réponses UI :

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Signal émis par le thread
     - Comportement dans ``BiblizouDockWidget``
   * - ``progress(step, total, message)``
     - Affichage dans ``iface.mainWindow().statusBar()`` : *"Biblizou : [message] ([step]/[total])"*
   * - ``log(message)``
     - Écriture dans ``QgsMessageLog`` sous la catégorie *Biblizou* (niveau Info)
   * - ``finished(message)``
     - Réactivation du bouton lanceur + ``QMessageBox.information``
   * - ``error(message)``
     - Réactivation de tous les boutons + ``QMessageBox.critical``

À la fermeture du panneau (``closeEvent``), le signal ``closingPlugin`` est émis
pour permettre au plugin principal (``biblizou.py``) de nettoyer ses références.


Référence des fichiers source
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Fichier
     - Rôle
   * - ``biblizou_dockwidget_base.ui``
     - Définition Qt Designer du panneau (widgets, layout, styles QSS)
   * - ``biblizou_dockwidget.py``
     - Logique de l'interface : validation, collecte des paramètres, gestion des threads
   * - ``config/dept_fr.csv``
     - Liste des départements français (``nom_officiel``, ``code_insee``)