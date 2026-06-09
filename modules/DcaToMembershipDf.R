# ============================================================
# Classification écologique des espèces par indices Julve
# Auteur : François Botcazou
# ============================================================

# 0. Librairies
pkgs <- c("vegan", "e1071", "ggplot2", "jsonlite")
for (pkg in pkgs) if (!requireNamespace(pkg, quietly = TRUE)) install.packages(pkg)
for (pkg in pkgs) library(pkg, character.only = TRUE)

# 1. Chargement des données

args   <- commandArgs(trailingOnly = TRUE)
params <- fromJSON(args[1])

folder_path <- params$folder_path

data_input <- read.csv(folder_path, "bota_julve.csv"),
                       sep = ",", 
                       encoding = "UTF-8",
                       row.names = 1)  # colonne espèce en nom de ligne

# 2. Nettoyage : suppression des espèces sans aucun indice renseigné
data_input <- data_input[rowSums(is.na(data_input)) < ncol(data_input), ]

# Remplacement des NA par la moyenne de la colonne (imputation simple)
for (col in colnames(data_input)) {
  data_input[[col]][is.na(data_input[[col]])] <- mean(data_input[[col]], na.rm = TRUE)
}

# 3. DCA
ord      <- decorana(data_input)
axes_DCA <- scores(ord, display = "sites", choices = 1:4)

# 4. Boucle FCM k = 2 à 15
set.seed(42)  # reproductibilité
resultats <- lapply(2:15, function(k) {
  fcm <- cmeans(axes_DCA, centers = k, m = 2, iter.max = 500, verbose = FALSE)
  
  # Partition Coefficient (PC) — maximiser
  pc <- sum(fcm$membership^2) / nrow(axes_DCA)
  
  # Xie-Beni — minimiser
  separation <- min(dist(fcm$centers)^2)
  xb <- fcm$withinerror / (nrow(axes_DCA) * separation)
  
  list(k = k, PC = pc, Xie_Beni = xb, modele = fcm)
})

# 5. Synthèse et choix automatique de k
synthese <- data.frame(
  k        = sapply(resultats, `[[`, "k"),
  PC       = sapply(resultats, `[[`, "PC"),
  Xie_Beni = sapply(resultats, `[[`, "Xie_Beni")
)

# Normalisation pour combiner les deux critères
synthese$PC_norm <- (synthese$PC - min(synthese$PC)) / 
  (max(synthese$PC) - min(synthese$PC))
synthese$XB_norm <- (synthese$Xie_Beni - min(synthese$Xie_Beni)) / 
  (max(synthese$Xie_Beni) - min(synthese$Xie_Beni))

# Score composite : maximiser PC, minimiser Xie-Beni
synthese$score <- synthese$PC_norm - synthese$XB_norm
k_optimal <- synthese$k[which.max(synthese$score)]
cat("Nombre de groupes optimal :", k_optimal, "\n")

# 6. Modèle final
modele_final <- resultats[[k_optimal - 1]]$modele

# 7. Tableau membership
membership_df <- as.data.frame(modele_final$membership)
colnames(membership_df) <- paste0("groupe_", seq_len(k_optimal))
membership_df$espece <- rownames(axes_DCA)
membership_df$groupe_dominant <- apply(modele_final$membership, 1, which.max)
membership_df <- membership_df[, c("espece", "groupe_dominant", 
                                   paste0("groupe_", seq_len(k_optimal)))]

print(head(membership_df))

# 8. Visualisation des critères
par(mfrow = c(1, 2))
plot(synthese$k, synthese$PC, type = "b", pch = 19,
     xlab = "Nombre de groupes (k)", ylab = "Partition Coefficient",
     main = "PC — à maximiser")
abline(v = k_optimal, col = "red", lty = 2)

plot(synthese$k, synthese$Xie_Beni, type = "b", pch = 19,
     xlab = "Nombre de groupes (k)", ylab = "Xie-Beni index",
     main = "Xie-Beni — à minimiser")
abline(v = k_optimal, col = "red", lty = 2)

# 9. Labellisation automatique des groupes
library(jsonlite)

# Chargement du mapping ordinal
julve_labels <- fromJSON("chemin/vers/config/julve_labels.json")

# Centroïdes des groupes dans l'espace des indices Julve originaux
# (pas dans l'espace DCA — pour que les labels soient interprétables)
centroides <- t(sapply(seq_len(k_optimal), function(k) {
  poids <- modele_final$membership[, k]
  apply(data_julve, 2, function(col) weighted.mean(col, poids, na.rm = TRUE))
}))
rownames(centroides) <- paste0("groupe_", seq_len(k_optimal))

# Fonction de lookup label
get_label <- function(indice, valeur) {
  valeur_arrondie <- as.character(round(valeur))
  tryCatch(
    julve_labels[[indice]][["valeurs"]][[valeur_arrondie]],
    error = function(e) "indéterminé"
  )
}

# Identification des indices les plus discriminants
# = ceux dont la variance inter-groupes est la plus forte
variance_inter <- apply(centroides, 2, var)
indices_discriminants <- names(sort(variance_inter, decreasing = TRUE)[1:2])

cat("Indices les plus discriminants :", indices_discriminants, "\n")

# Construction des labels
labels_groupes <- sapply(seq_len(k_optimal), function(k) {
  parties <- sapply(indices_discriminants, function(indice) {
    if (indice %in% colnames(centroides)) {
      get_label(indice, centroides[k, indice])
    } else {
      NA
    }
  })
  parties <- parties[!is.na(parties)]
  paste(parties, collapse = " / ")
})

# Tableau récapitulatif des groupes
groupes_df <- data.frame(
  groupe    = paste0("groupe_", seq_len(k_optimal)),
  label     = labels_groupes,
  stringsAsFactors = FALSE
)

# Ajout des valeurs centroïdes pour traçabilité
groupes_df <- cbind(groupes_df, round(centroides, 2))

cat("\nGroupes écologiques :\n")
print(groupes_df[, c("groupe", "label")])

# 10. Renommage des colonnes membership avec les labels
colnames(membership_df)[colnames(membership_df) %in% paste0("groupe_", seq_len(k_optimal))] <- labels_groupes

print(head(membership_df))