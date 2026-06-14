"""
Auteur : ExEco Environnement - François Botcazou
Date : 2026/06
Version : 1.0
Nom : ApiToTable.py
Groupe : base
Description : Classe abstraite (ABC) mutualisée pour l'extraction de données
              à partir de l'API de l'INPN vers une table.

              Toute la logique commune (I/O fichiers, GeoPackage, logging) est
              implémentée ici une seule fois. Les classes enfants n'ont qu'à
              implémenter les méthodes abstraites spécifiques à leur format XML.

"""

