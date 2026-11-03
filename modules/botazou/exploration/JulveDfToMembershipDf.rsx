##Biblizou=group
##output_plots_to_html
##folder_path=folder
##input_file=string julve_df.csv
##julve_labels=file

# Classification écologique des espèces par indices Julve
# Auteur : François Botcazou
# Version : AFC (FactoMineR) en remplacement de la DCA

library(FactoMineR)
library(e1071)
library(ggplot2)
library(jsonlite)

# 1. Chargement des données
folder_path <- normalizePath(folder_path, winslash = "/", mustWork = FALSE)

cat("folder_path recu :", folder_path, "\n")
cat("input_file recu  :", input_file, "\n")

raw <- read.csv(file.path(folder_path, input_file),
                sep = ",",
                encoding = "UTF-8",
                stringsAsFactors = FALSE)

# Stocker CD_REF et NOM_SCIENTIFIQUE avant filtrage
cd_ref_vec <- setNames(raw$CD_REF, raw$NOM_SCIENTIFIQUE)

# NOM_SCIENTIFIQUE comme rownames
rownames(raw) <- raw$NOM_SCIENTIFIQUE

# Filtrer uniquement les indices Julve numériques
indices_julve <- c("L", "T", "C", "HA", "HE", "R", "N", "S", "Tx", "MO")
data_input <- raw[, intersect(indices_julve, colnames(raw)), drop = FALSE]

# 2. Nettoyage : suppression des espèces sans aucun indice renseigné
data_input <- data_input[rowSums(is.na(data_input)) < ncol(data_input), ]

# Synchroniser cd_ref_vec avec les espèces restantes après nettoyage
cd_ref_vec <- cd_ref_vec[rownames(data_input)]

# Imputation par la médiane puis arrondi — l'AFC exige des entiers positifs
for (col in colnames(data_input)) {
  data_input[[col]][is.na(data_input[[col]])] <-
    median(data_input[[col]], na.rm = TRUE)
}
data_input <- round(data_input)

# Vérification : toutes les valeurs doivent être >= 0
if (any(data_input < 0, na.rm = TRUE)) {
  stop("Le tableau contient des valeurs négatives — incompatible avec l'AFC.")
}

# 3. AFC
ord <- CA(data_input, graph = FALSE)

# Choix automatique des axes : on retient ceux dont la valeur propre
# est supérieure à l'inertie moyenne
inertie_moyenne <- mean(ord$eig[, 1])
n_axes <- sum(ord$eig[, 1] > inertie_moyenne)
n_axes <- max(n_axes, 2)   # au moins 2 axes pour le clustering
cat("Nombre d'axes retenus :", n_axes, "\n")

axes <- ord$row$coord[, 1:n_axes, drop = FALSE]

# Coordonnées colonnes (indices Julve) dans le même espace — utilisées
# pour la labellisation directe des groupes
coord_indices <- ord$col$coord[, 1:n_axes, drop = FALSE]

# 4. Éboulis des valeurs propres
barplot(ord$eig[, 2],
        names.arg = rownames(ord$eig),
        xlab = "Dimension", ylab = "% inertie",
        main = "AFC — éboulis des valeurs propres",
        col = ifelse(ord$eig[, 1] > inertie_moyenne, "#2196F3", "#BBDEFB"))
abline(h = inertie_moyenne / sum(ord$eig[, 1]) * 100,
       col = "red", lty = 2)
legend("topright", legend = "Inertie moyenne", col = "red",
       lty = 2, bty = "n")

# 5. Boucle FCM k = 2 à 15
set.seed(42)
resultats <- lapply(2:15, function(k) {
  fcm <- cmeans(axes, centers = k, m = 2, iter.max = 500, verbose = FALSE)

  pc         <- sum(fcm$membership^2) / nrow(axes)
  separation <- min(dist(fcm$centers)^2)
  xb         <- fcm$withinerror / (nrow(axes) * separation)

  list(k = k, PC = pc, Xie_Beni = xb, modele = fcm)
})

# 6. Synthèse et choix automatique de k
synthese <- data.frame(
  k        = sapply(resultats, `[[`, "k"),
  PC       = sapply(resultats, `[[`, "PC"),
  Xie_Beni = sapply(resultats, `[[`, "Xie_Beni")
)

synthese$PC_norm <- (synthese$PC - min(synthese$PC)) /
  (max(synthese$PC) - min(synthese$PC))
synthese$XB_norm <- (synthese$Xie_Beni - min(synthese$Xie_Beni)) /
  (max(synthese$Xie_Beni) - min(synthese$Xie_Beni))

synthese$score <- synthese$PC_norm - synthese$XB_norm
k_optimal <- synthese$k[which.max(synthese$score)]
cat("Nombre de groupes optimal :", k_optimal, "\n")

# 7. Modèle final
modele_final <- resultats[[k_optimal - 1]]$modele

# 8. Tableau membership
membership_df <- as.data.frame(modele_final$membership)
colnames(membership_df) <- paste0("groupe_", seq_len(k_optimal))
membership_df$espece  <- rownames(axes)
membership_df$CD_REF  <- cd_ref_vec[rownames(axes)]
membership_df <- membership_df[, c("espece", "CD_REF",
                                   paste0("groupe_", seq_len(k_optimal)))]

print(head(membership_df))

# 9. Visualisation des critères FCM
par(mfrow = c(1, 2))
plot(synthese$k, synthese$PC, type = "b", pch = 19,
     xlab = "Nombre de groupes (k)", ylab = "Partition Coefficient",
     main = "PC — à maximiser")
abline(v = k_optimal, col = "red", lty = 2)

plot(synthese$k, synthese$Xie_Beni, type = "b", pch = 19,
     xlab = "Nombre de groupes (k)", ylab = "Xie-Beni index",
     main = "Xie-Beni — à minimiser")
abline(v = k_optimal, col = "red", lty = 2)

# 10. Labellisation directe via les coordonnées colonnes de l'AFC
julve_labels_data <- fromJSON(julve_labels)

centroides_axes <- t(sapply(seq_len(k_optimal), function(k) {
  poids <- modele_final$membership[, k]
  apply(axes, 2, function(col) weighted.mean(col, poids))
}))
rownames(centroides_axes) <- paste0("groupe_", seq_len(k_optimal))

get_label <- function(indice, valeur) {
  valeur_arrondie <- as.character(round(valeur))
  tryCatch(
    julve_labels_data[[indice]][["valeurs"]][[valeur_arrondie]],
    error = function(e) "indéterminé"
  )
}

labels_groupes <- sapply(seq_len(k_optimal), function(k) {
  distances <- apply(coord_indices, 1, function(coord_ind) {
    sqrt(sum((centroides_axes[k, ] - coord_ind)^2))
  })
  indices_proches <- names(sort(distances)[1:2])

  poids <- modele_final$membership[, k]
  parties <- sapply(indices_proches, function(indice) {
    if (indice %in% colnames(data_input)) {
      valeur_moy <- weighted.mean(data_input[, indice], poids, na.rm = TRUE)
      get_label(indice, valeur_moy)
    } else {
      NA
    }
  })

  parties <- parties[!is.na(parties)]
  paste(parties, collapse = " / ")
})

# 11. Tableau récapitulatif des groupes avec centroides sur data_input
centroides_bruts <- t(sapply(seq_len(k_optimal), function(k) {
  poids <- modele_final$membership[, k]
  apply(data_input, 2, function(col) weighted.mean(col, poids, na.rm = TRUE))
}))
rownames(centroides_bruts) <- paste0("groupe_", seq_len(k_optimal))

groupes_df <- data.frame(
  groupe = paste0("groupe_", seq_len(k_optimal)),
  label  = labels_groupes,
  stringsAsFactors = FALSE
)
groupes_df <- cbind(groupes_df, round(centroides_bruts, 2))

cat("\nGroupes écologiques :\n")
print(groupes_df[, c("groupe", "label")])

# 12. Renommage des colonnes membership avec les labels
colnames(membership_df)[
  colnames(membership_df) %in% paste0("groupe_", seq_len(k_optimal))
] <- labels_groupes

print(head(membership_df))

# Export membership_df
output_csv <- file.path(folder_path, "_ecoFuzz_membership.csv")
write.csv(membership_df, output_csv, row.names = FALSE, fileEncoding = "UTF-8")
cat("Membership exporté :", output_csv, "\n")
