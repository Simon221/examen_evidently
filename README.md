
# 📘 Analyse de dérive avec Evidently sur le Bike Sharing Dataset / Examen Datascientest

## Auteur : Simon Pierre DIOUF
## Email : simonpierre.diouf@orange-sonatel.com


## Objectif du projet

Ce projet vise à entraîner un modèle de régression sur les données de location de vélos à Washington D.C. (Bike Sharing Dataset) en janvier 2011, puis à surveiller **les dérives de performance** et **les dérives de données** au fil du mois de février, et en utilisant les données de janv à l'aide de la bibliothèque Evidently.

---

## Questions d'analyse

### 1. Après l'étape 4, expliquez ce qui a changé au cours des semaines 1, 2 et 3.

Dans les **rapports hebdomadaires (week1, week2, week3)** générés à l’étape 4, on observe :

- **Week 1 :** Les performances du modèle sont relativement bonnes. Les distributions de certaines features (comme `hr`, `temp`, `workingday`) restent proches de celles de janvier. Peu ou pas de dérive détectée.
  
- **Week 2 :** Une **légère baisse de performance** est visible. On remarque un changement dans la distribution de `weekday`, `workingday` et surtout **une hausse des valeurs de `cnt`** (nombre de locations).

- **Week 3 :** C’est là que la **performance chute fortement**. Le modèle sous-estime largement la demande. Les horaires d’utilisation changent, la météo est différente, et on note une augmentation importante du nombre moyen de locations par heure.

**Donc :** Il y a une évolution progressive du comportement utilisateur, des conditions climatiques ou du calendrier (plus de jours actifs, météo plus clémente ?) au fil du mois de février, entraînant une perte de précision du modèle.

---

### 2. Après l'étape 5, expliquez ce qui semble être la cause première de la dérive ?.

La distribution de la variable cible (cnt) en février, particulièrement en semaine 3, montre un décalage vers des valeurs plus élevées par rapport à janvier. Cela indique une augmentation générale de l'utilisation des vélos.

En examinant les variables d'entrée, on constate que les variables météorologiques, en particulier temp et atemp (température réelle et température ressentie), montrent les changements les plus significatifs. Ces variables présentent une distribution différente en février par rapport à janvier, avec des valeurs généralement plus élevées.

Le modèle a été entraîné sur des données de janvier, où la relation entre la température et l'utilisation des vélos correspondait à un modèle hivernal. En février, avec l'augmentation des températures, cette relation a évolué, entraînant une sous-estimation systématique de l'utilisation des vélos par le modèle.

Selon moi, la cause première de la dérive semble être un changement saisonnier des conditions météorologiques (principalement la température) qui a modifié le comportement des utilisateurs de vélos d'une manière que le modèle, entraîné uniquement sur les données de janvier, n'était pas en mesure de prédire correctement.
---

### 3. Après l'étape 6, expliquez quelle stratégie appliquer.


1. **Réalimenter le modèle avec des données plus récentes** :
   - Inclure février dans les données d'entraînement.
   - Mettre en place une politique de "retraining régulier" (ex : tous les 15 jours).

2. **Mettre en place une surveillance continue avec Evidently** :
   - Automatiser la détection des dérives de cible et de features.

3. **Segmenter les modèles** :
   - Utiliser des modèles différents pour les jours ouvrés / week-ends, ou pour les saisons (hiver, printemps, etc.).

4. **Ajouter des variables explicatives** :
   - Intégrer la température réelle ou prévue, les événements spéciaux ou les congés.

---

## Lancer l’interface Evidently

```bash
evidently ui --workspace examen_evidently_workspace
```

Cela ouvre une interface web pour consulter tous les rapports générés automatiquement.
