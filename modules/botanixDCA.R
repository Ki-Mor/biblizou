# -*- coding: utf-8 -*-
"""
Auteur : ExEco Environnement - François Botcazou
Nom : StatusApiToTable.py
"""
# 0. Téléchargement des librairies
pkgs <- c("vegan", "sf", "reshape2", "ggplot2", "e1071")
for (pkg in pkgs) if (!requireNamespace(pkg, quietly = TRUE)) install.packages(pkg)
for (pkg in pkgs) library(pkg, character.only = TRUE)

# 1. Chargement des données (Table simple sans géométrie)
data_julve <- st_read("chemin/vers/votre_fichier.gpkg", layer = "Bota_Julve")

# 2. Isolement des indices écologiques (on exclut les 3 premières colonnes de texte/ID)
matrice_indices <- data_julve[, 4:ncol(data_julve)]

# 3. Analyse de Gradient (DCA) et extraction des coordonnées des espèces
ord <- decorana(matrice_indices)
axes_DCA <- scores(ord, display = "sites", choices = 1:4)

# 4. Pipeline FCM : Boucle d'optimisation (k = 2 à 15 groupes)
resultats <- lapply(2:15, function(k) {
  fcm <- cmeans(axes_DCA, centers = k, m = 2, iter.max = 500, verbose = FALSE)
  
  pc <- sum(fcm$membership^2) / nrow(axes_DCA)
  
  compacite <- sum(fcm$withinerror)
  separation <- min(dist(fcm$centers)^2)
  xb <- compacite / (nrow(axes_DCA) * separation)
  
  list(k = k, PC = pc, Xie_Beni = xb, modele = fcm)
})

# 5. Synthèse des critères pour le choix du nombre de groupes
synthese <- data.frame(
  k = sapply(resultats, function(x) x$k),
  PC = sapply(resultats, function(x) x$PC),
  Xie_Beni = sapply(resultats, function(x) x$Xie_Beni)
)

print(synthese)