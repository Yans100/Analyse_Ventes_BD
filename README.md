
# Analyse des ventes de jeux vidéo — SDD1003

Application web Flask connectée à MongoDB Atlas permettant de consulter, rechercher, modifier et analyser un dataset de ventes de jeux vidéo avec visualisations et prédictions par apprentissage automatique.

## Fonctionnalités

- Affichage et recherche multicritères (titre, année, genre, plateforme, éditeur, note)
- Ajout, modification et suppression de jeux dans la base de données
- Visualisations : graphique à barres, camembert, heatmap, barres horizontales (top éditeurs)
- Analyse ML : régression linéaire, KNN (k=3), Random Forest — prédiction de la note selon le rang
- Recherche par rang avec prédictions des 3 modèles et classification de qualité (Excellente / Acceptable / Mauvaise)
- Gestion des valeurs manquantes (médiane pour les années, "Inconnue" pour les éditeurs)

## Technologies

- Python
- Flask
- MongoDB Atlas (PyMongo)
- Pandas
- scikit-learn (LinearRegression, KNeighborsRegressor, RandomForestRegressor)
- Matplotlib / Seaborn
- Jinja2

## Prérequis

```bash
pip install flask pymongo pandas scikit-learn matplotlib seaborn scipy
```

> La connexion MongoDB Atlas dans `app.py` utilise des identifiants personnels — remplacer l'URI par votre propre cluster avant de lancer.

## Lancer le projet

```bash
python app.py
```

## Structure

```
app.py           — routes Flask, logique ML et visualisations
templates/
  MenuPrincipal.html
  ListeJeux.html
  FormulaireRecherche.html
  ResultatsRecherche.html
  ModifierJeux.html
  Visualisations.html
  AnalyseDF.html
  RechercheRang.html
```

---

Projet universitaire solo — cours SDD1003, UQTR.
