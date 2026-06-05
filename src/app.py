from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import io
from io import BytesIO
import base64
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import scipy.stats as stats

########################################################################################################################
# app.py est le coeur du site web. Flask est utilisé en Python et avec mongoDB Atlas qui héberge la base de données.   #
# Toutes les routes nécessaires au bon fonctionnement de l'application sont implémenté ici.                            #
########################################################################################################################

# Connexion MongoDB sur Atlas où est hébergée ma base de données
uri = "mongodb+srv://redacted@redacted.zewwl.mongodb.net/?retryWrites=true&w=majority&appName=SDD1003"
client = MongoClient(uri, server_api=ServerApi('1')) # Version 1 du serveur pour intéragir avec la base de données

app = Flask(__name__) # Initie une application Flask

db = client["VideoGames"] # Accède à la base de donnée nommée VideoGames
collection = db["Sales"] # Accède à la collection Sales de la BD VideoGames

########################################################################################################################

# Route de la page principale (menu). Route par défaut quand l'application est lancé
@app.route('/')
def menu():
    return render_template("MenuPrincipal.html") # Retourne la page web MenuPrincipal.html dans les templates

########################################################################################################################

# Route pour afficher tous les jeux avec une simple recherche par titre
@app.route('/jeux', methods=['GET']) # Fonction afficher_jeux() = URL '/jeux'. Accepte uniquement les requêtes GET
def afficher_jeux():
    query = request.args.get('query', '') # Récupère le paramètre query de la requête
    if query: # Si un paramètre query est fournis (nom du jeu)
        documents = list( # Essais de trouver un titre qui correspond à un jeu dans la collection et trie par rang croissant
            collection.find({"Game Title": {"$regex": query, "$options": "i"}}).sort("Rank", 1)
        )
    else: # Si aucun query, retourne la liste complète des jeux dans la collection, trier par rang croissant
        documents = list(collection.find().sort("Rank", 1))
    for doc in documents: # Parcours chaque document
        doc["_id"] = str(doc["_id"])  # Convertir l'ID en chaîne de caractères pour éviter les potentiels problèmes JSON
    return render_template("ListeJeux.html", jeux=documents) # Passe la liste de jeux à la page html

########################################################################################################################

# Route pour rechercher les jeux selon un ou plusieurs critères
@app.route('/recherche', methods=['GET', 'POST']) # Fonction recherche() = URL '/recherche'. Accepte les requêtes GET et POST
def recherche():
    if request.method == 'POST': # Si requête de traitement des données saisie par utilisateur
        filtres = {} # Crée un dictionnaire vide qui va servir à stocker les critères de recherche (filtres)

        # Gérer la recherche par titre
        if title := request.form.get('title'): # Récupère la valeur du formulaire saisie dans titre
            filtres["Game Title"] = {"$regex": title, "$options": "i"} # Ajout filtre et utilise $regex

        # Gérer la recherche par année
        if year := request.form.get('year'): # Récupère la valeur du formulaire saisie dans année
            filtres["Year"] = int(year) # Ajout filtre et convertit année en int

        # Gérer la recherche par genre
        if genre := request.form.getlist('genre'):  # Récupère dans le formulaire une liste de genres choisie dans genre
            filtres["Genre"] = {"$in": [g for g in genre if g]}  # Ajout filtre pour rechercher documents ou l'un des genres choisis est présent

        # Gérer la recherche par plateforme
        if platform := request.form.getlist(
                'platform'):  # Récupère dans le formulaire une liste de plateforme choisie dans plateforme
            filtres["Platform"] = {"$in": [p for p in platform if p]}  # Ajout filtre pour rechercher documents ou l'une des plateformes choisit est présent

        # Gérer la recherche par éditeur
        if publisher := request.form.get('publisher'): # Récupère la valeur du formulaire saisie dans éditeur
            filtres["Publisher"] = {"$regex": publisher, "$options": "i"} # Ajout filtre et utilise $regex

        # Gérer la recherche par note
        if review := request.form.get('review'): # Récupère la valeur minimale de note spécifiée
            filtres["Review"] = {"$gte": float(review)} # Ajout filtre ou note est supérieur ou égal à ce qui est spécifié et convertit en float

        # Recherche les jeux dans la base de données
        documents = list(collection.find(filtres)) # Utilise les filtres définit pour trouver les documents correspondants et convertit en liste Python
        for doc in documents: # ObjectId peut causer des problèmes donc convertit _id en chaine de caractères
            doc["_id"] = str(doc["_id"])

        return render_template("ResultatsRecherche.html", jeux=documents) # Jeux correspondants passés en liste à ResultatsRecherche.html

    return render_template("FormulaireRecherche.html") # Si requête GET, affiche la page du formulaire

########################################################################################################################

# Route pour modifier un ou plusieurs attributs d'un jeu
@app.route('/modifier/<jeu_id>', methods=['GET', 'POST']) # Fonction modifier_jeu(jeu_id) = URL '/modifier/<jeu_id>'. Accepte les requêtes GET et POST
def modifier_jeu(jeu_id): # Prends en paramètre l'id du jeu à modifier
    jeu = collection.find_one({"_id": ObjectId(jeu_id)}) # Recherche dans la collection un document avec _id égal à jeu_id (convertit en ObjectId)
    if request.method == 'POST': # Formulaire soumis et doit traiter les données saisies
        updated_data = { # Récupère les données du formulaire (tous les attributs)
            "Game Title": request.form['title'],
            "Platform": request.form['platform'],
            "Year": int(request.form['year']),
            "Genre": request.form['genre'],
            "Publisher": request.form['publisher'],
            "Review": float(request.form['review']),
        }
        # Mettre à jour le jeu dans la base de données
        collection.update_one({"_id": ObjectId(jeu_id)}, {"$set": updated_data}) # Filtre qui sélectionne l'id correspondant et le met à jour
        return redirect(url_for('afficher_jeux'))  # Redirige après la modification vers la route qui affiche tous les jeux
    return render_template('ModifierJeux.html', jeu=jeu) # Si requête GET, le formulaire de modification est affiché

########################################################################################################################

# Route pour supprimer définitivement un jeu de la base de données
@app.route('/supprimer/<jeu_id>', methods=['GET']) # Fonction supprimer_jeu(jeu_id) = URL '/supprimer/<jeu_id>'. Accepte seulement requête GET
def supprimer_jeu(jeu_id): # Prends en paramètre l'id du jeu à supprimer
    collection.delete_one({"_id": ObjectId(jeu_id)}) # Recherche dans la collection un document avec _id égal à jeu_id (convertit en ObjectId)
    return redirect(url_for('afficher_jeux'))  # Redirige après la suppression vers la route qui affiche tous les jeux

########################################################################################################################

# Route pour visualiser les divers graphiques en lien avec les données
@app.route('/visualisations', methods=['GET']) # Fonction visualisations() = URL '/visualisations/'. Accepte seulement requête GET
def visualisations():
    # Recherche dans la base de données et transforme sous forme de liste les éléments inclus ci-bas (1). 0 = exclus.
    documents = list(collection.find({}, {"Genre": 1, "Global": 1, "Year":1, "Publisher":1, "_id": 0, "North America": 1, "Europe": 1, "Japan": 1, "Rest of World": 1}))
    df = pd.DataFrame(documents) # Création d'un dataframe avec pandas pour grandement faciliter les manipulations

    ### 1. Graphique à barres - Genre de jeux les plus vendus ###

    # Groupe les données du champ genre, calcule la somme des ventes globales, réinitialise l'index = transforme résultat en 2 colonnes
    genre_sales = df.groupby("Genre")["Global"].sum().reset_index()

    plt.figure(figsize=(12, 10)) # Dimensions du graphique
    sns.barplot(x="Genre", y="Global", data=genre_sales, palette="viridis") # Seaborn pour tracer graph a barres avec les données
    plt.title("Genre de jeux les plus vendus", fontsize=16, weight='bold') # Titre du graph
    plt.xlabel("Genre", fontsize=12, weight='bold') # Titre axe x
    plt.ylabel("Ventes globales (en millions)", fontsize=12, weight='bold') # Titre axe y
    plt.xticks(rotation=45) # Noms des genres (axe x) pivoté à 45 degrées pour plus de visibilité

    # Convertir le graphique à barres en image grâce à Base64
    buf = BytesIO() # Crée un tampon mémoire pour stocker l'image
    plt.savefig(buf, format="png") # Sauvegarde le graphique généré en format png
    buf.seek(0) # Réinitialise le curseur du tampon pour permettre lecture des données
    image_base64_barre = base64.b64encode(buf.getvalue()).decode("utf-8") # Récupère données de l'image, encode et convertit en chaine Base64 en format lisible.
    buf.close() # Ferme le tampon

    ### 2. Graphique en camembert - Proportion des ventes globales par région ###

    # Sélectionne uniquement les colonnes représentant les ventes par région puis fait la somme des ventes
    total_ventes_region = df[['North America', 'Europe', 'Japan', 'Rest of World']].sum()

    # Calcul des proportions
    proportions = total_ventes_region / total_ventes_region.sum() # Ventes de chaque région divisée par ventes globales (sommes de toutes les régions)
    couleurs = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'] # Couleurs pour chaque proportion

    fig, axs = plt.subplots(1, 1, figsize=(8, 8))  # Crée une figure avec un axe et définis taille du graphique

    # Création du graphique camembert
    axs.pie(proportions, # Valeur qui correspond aux proportions calculées
            labels=proportions.index, # Noms de région comme étiquette
            autopct='%1.1f%%', # Affiche % avec un chiffre après la virgule
            startangle=90, # Commence le graph dans un angle de 90 degrée
            colors=couleurs, # Utilise couleurs prédéfinies
            textprops=dict(fontweight='bold'), # Étiquette en gras
            wedgeprops=dict(width=0.3, edgecolor='black', linewidth=1.5), # Graphique en anneau avec l'épaisseur et les contours
            pctdistance=0.85) # Positionnement des %

    axs.set_title('Proportion des ventes par région', fontsize=16, weight='bold') # Titre du graph

    # Convertir le graphique en camembert en image grâce à Base64
    buf = BytesIO() # Crée un tampon mémoire pour stocker l'image
    plt.savefig(buf, format="png") # Sauvegarde le graphique généré en format png
    buf.seek(0) # Réinitialise le curseur du tampon pour permettre lecture des données
    image_base64_camembert = base64.b64encode(buf.getvalue()).decode("utf-8") # Récupère données de l'image, encode et convertit en chaine Base64 en format lisible.
    buf.close() # Ferme le tampon

    ### 3. Heatmap - Ventes globales par genre au fil des années ###

    # Regroupe les données en combinant les années et les genres, puis calcule somme des ventes globales pour chaque combinaison, puis réinitialise l'index
    ventes_genres_annees = df.groupby(['Year', 'Genre']).agg({'Global': 'sum'}).reset_index()

    pivot_genre_ventes = ventes_genres_annees.pivot(index='Year', columns='Genre', values='Global') # Table pivot pour les données. Année = ligne, Genre = colonne, Ventes = cellules
    pivot_genre_ventes = pivot_genre_ventes.fillna(0)  # Remplacer NaN par 0 pour les genres sans ventes certaines années

    plt.figure(figsize=(15, 10)) # Taille du graph
    sns.heatmap(pivot_genre_ventes, annot=False, cmap='Reds') # Crée une heatmap avec seaborn et de la table pivot ci-haute
    plt.title('Ventes globales par genre au fil des années', fontsize=16, weight='bold') # Titre du graph
    plt.ylabel('Année', fontsize=12, weight='bold') # Titre axe y
    plt.xlabel('Genre', fontsize=12, weight='bold') # Titre axe x

    # Convertir le heatmap en image Base64
    buf = BytesIO() # Crée un tampon mémoire pour stocker l'image
    plt.savefig(buf, format="png") # Sauvegarde le graphique généré en format png
    buf.seek(0) # Réinitialise le curseur du tampon pour permettre lecture des données
    image_base64_heatmap = base64.b64encode(buf.getvalue()).decode("utf-8") # Récupère données de l'image, encode et convertit en chaine Base64 en format lisible.
    buf.close() # Ferme le tampon

    ### 4. Graphique à barres horizontales - Titres par éditeur (**BONUS**) ###

    # Regroupe les données par éditeur, compte le nombre de titres par éditeur et réinitialise l'index pour transformer résultat en colonne nommée count
    editeur_titre = df.groupby('Publisher').size().reset_index(name='count')

    # Trier les éditeurs par le nombre de titres, puis sélectionner les 15 premiers
    top_editeurs = editeur_titre.sort_values(by='count', ascending=False).head(15)

    # Création du graphique avec étiquettes des barres (nom éditeurs) et longueur des barres (nombre de titres)
    plt.figure(figsize=(20, 10)) # Taille du graph
    bars = plt.barh(top_editeurs['Publisher'], top_editeurs['count'], color='#845EC2')

    plt.gca().invert_yaxis()  # Inverser l'axe des y pour avoir la barre la plus haute en haut (nombre de titres le plus haut)

    # Ajouter les valeurs à côté des barres
    for bar in bars: # Parcours chaque barre du graph
        position_y = bar.get_y() + bar.get_height() / 2 # Obtenir position verticale de la barre + son hauteur/2 pour centrer
        # Ajoute texte avec nombre de titres selon longueur, centré, arrondis à 2 décimales, aligne le texte à gauche et au centre verticalement, en gras
        plt.text(bar.get_width(), position_y, round(bar.get_width(), 2), ha='left', va='center', fontsize=12, weight='bold')

    # Ajout pour que le graph soit lisible et clair
    plt.yticks(fontweight='bold') # Valeurs axe y en gras
    plt.xlabel('') # Supprime titre axe x
    plt.ylabel('') # Supprime titre axe y
    plt.xticks([]) # Supprime valeurs axe x
    sns.despine(left=True, right=True, top=True, bottom=True) # Supprime bordures
    plt.title('Top 15 des éditeurs selon le nombre de jeux produits', fontsize=16, weight='bold') # Titre du graph

    # Convertir le graphique horizontal en image Base64
    buf = BytesIO() # Crée un tampon mémoire pour stocker l'image
    plt.savefig(buf, format="png") # Sauvegarde le graphique généré en format png
    buf.seek(0) # Réinitialise le curseur du tampon pour permettre lecture des données
    image_base64_horizon = base64.b64encode(buf.getvalue()).decode("utf-8") # Récupère données de l'image, encode et convertit en chaine Base64 en format lisible.
    buf.close() # Ferme le tampon

    # Passer les graphiques encodés en Base64 comme des images png à la page visualisations.html qui va gérer l'affichage de ceux-ci
    return render_template("Visualisations.html",
                           image_base64_barre=image_base64_barre,
                           image_base64_camembert=image_base64_camembert,
                           image_base64_heatmap=image_base64_heatmap,
                           image_base64_horizon=image_base64_horizon)

########################################################################################################################

# Route pour visualiser les diverses analyses en lien avec les données à l'aide d'algorithme d'apprentissage automatique
@app.route('/analyse', methods=['GET'])  # Fonction analyse_df() = URL '/analyse/'. Accepte seulement requête GET
def analyse_df():
    # Convertir la collection MongoDB en DataFrame
    documents = list(collection.find({}, {"_id": 0}))  # Récupère tous les champs sauf _id et convertit en liste
    df = pd.DataFrame(documents)  # Convertit la liste de documents en un DataFrame pandas pour mieux travailler

    # Analyse initiale (données brutes sans modification)
    buffer = io.StringIO() # Crée un buffer qui capture le texte en sortie
    df.info(buf=buffer) # Appelle df.info() en le dirigeant dans buffer pour capturer sa sortie
    texte_info_initial = buffer.getvalue() # Extrait le contenu du buffer et le stock dans une variable
    texte_null_initiale = df.isnull().sum().to_string() # Calcule le nombre de valeurs manquantes par colonne et le convertit en chaine de caractères
    analyse_initiale = f"=== Analyse initiale ===\n{texte_info_initial}\n\n{texte_null_initiale}\n" # Chaine formatée pour insérer dynamiquement les valeurs

    # Analyse finale (gestion des valeurs manquantes)
    df['Year'].fillna(df['Year'].median(), inplace=True) # Remplace les 29 valeurs manquantes de year avec la médiane (inplace pour pas créer de copie)
    df['Publisher'].fillna('Inconnue', inplace=True) # Remplace les 2 valeurs manquantes de publisher avec une chaine "Inconnue"
    texte_null_apres = df.isnull().sum().to_string() # Recalcule le nombre de valeurs nulles par colonne puis convertit en chaine de caractères
    analyse_finale = f"=== Après gestion des valeurs manquantes ===\n{texte_null_apres}\n" # Chaine formatée pour insérer dynamiquement les valeurs

    # Définir les variables dépendantes et indépendantes
    x = df['Rank'].values.reshape(-1, 1) # Ventes mondiales des jeux comme variable indépendante. Reshape permet compatibilité avec scikit-learn tableau 2D
    y_actual = df['Review'].values  # Note moyenne des jeux comme variable dépendante (cible à prédire)

    # Séparer les données en ensembles d'entraînement (80%) et de test (20%)
    x_train, x_test, y_train, y_test = train_test_split(x, y_actual, test_size=0.2, random_state=111)

    # Standardisation des données
    scaler = StandardScaler() # Crée un objet StandardScaler
    x_train_scaled = scaler.fit_transform(x_train) # Applique la standardisation sur les données d'entraînement
    x_test_scaled = scaler.transform(x_test) # Applique la même transformation sur les données de test

    ### Régression Linéaire ###

    rg = LinearRegression() # Initialise un modèle de régression linéaire
    rg.fit(x_train_scaled, y_train) # Entraine le modèle avec l'ensemble d'entrainement standardisé
    y_predicted = rg.predict(x_test_scaled) # Utilise le modèle entrainé pour prédire les notes moyennes (y_predicted) en fonction des valeurs tests de x

    # Calcul des métriques de performance
    rmse_regression = np.sqrt(mean_squared_error(y_test, y_predicted)) # Calcule erreur quadratique moyenne entre valeur réelle et prédites puis éxtrait racine carrée. Donne une mesure de l'erreur moyenne de prédiction
    rho_regression, p_value_regression = stats.pearsonr(y_test, y_predicted) # Calcul du coefficient de corrélation de Pearson

    # Graphique de régression linéaire
    plt.figure(figsize=(16, 10)) # Taille du graphique
    plt.scatter(x_test, y_test, color='gray', label='Note réelle') # Nuage de point qui représente les notes réelles
    plt.plot(x_test, y_predicted, color='blue', linewidth=4, label='Régression linéaire') # Ligne qui correspond aux valeurs prédites selon le rang
    plt.xlabel('Rang') # Titre axe x
    plt.ylabel('Notes moyennes') # Titre axe y
    plt.ylim(30, 100) # Ajustez les limites de l'axe y
    plt.title('Prédiction des notes selon le rang') # Titre graph
    plt.legend() # Affiche la légende
    img_stream_regression = io.BytesIO() # Crée un flux mémoire pour stocker le graph comme image
    plt.savefig(img_stream_regression, format='png') # Sauvegarde dans le flux en format png
    plt.close() # Libère les ressources
    img_stream_regression.seek(0) # Positionne le pointeur au début du flux mémoire pour permettre bonne lecture de l'image
    img_base64_regression = base64.b64encode(img_stream_regression.read()).decode('utf-8') # Convertit image en chaine encodée Base64 puis la décode pour un affichage direct dans une page web

    # Formate les résultats des métriques (RMSE et Spearman)
    resultats_regression = (
        f"RMSE : {rmse_regression:.2f}\n"
        f"Coefficient de corrélation de Pearson: {rho_regression:.2f}\n"
        f"p-value: {p_value_regression:.4f}\n"
    )

    ### KNN ###

    # Conserve une copie des données d'origine pour l'affichage sinon il est horrible
    x_test_original = x_test.copy()

    # Crée une instance de voisin le plus proche avec un paramètre de 3 (utilise les 3 points de données les plus proches pour estimer valeur de cible)
    knn = KNeighborsRegressor(n_neighbors=3) # On peut l'ajuster au besoin ici
    knn.fit(x_train, y_train) # Entraine le modèle avec les valeurs standardisé, x_train comme valeurs indépendantes et y_train comme cible
    y_knn_predicted = knn.predict(x_test) # Prédit les valeurs cible en fonction des données d'entrées (x_test). Pour chaque x, l'algo calcule la moyenne des cibles des 3 points les plus proches

    # Calcul des métriques de performance
    rmse_knn = np.sqrt(mean_squared_error(y_test, y_knn_predicted)) # Calcule erreur quadratique moyenne entre valeur réelle et prédites puis éxtrait racine carrée. Donne une mesure de l'erreur moyenne de prédiction
    rho_knn, p_value_knn = stats.spearmanr(y_test, y_knn_predicted) # Calcul du coefficient de corrélation de Spearman

    # Graphique de KNN
    plt.figure(figsize=(16, 10)) # Taille du graphique
    plt.scatter(x_test_original, y_test, color='gray', label='Notes réelles (test)') # Nuage de point qui représente les notes réelles
    plt.scatter(x_test_original, y_knn_predicted, color='red', label='KNN (k=3)', s=20) # Nuage de point en rouge qui représente les notes prédites
    plt.ylim(30, 100) # Ajustez les limites de l'axe y
    plt.xlabel('Rang') # Titre axe x
    plt.ylabel('Notes moyennes') # Titre axe y
    plt.title('Prédiction des notes selon le rang') # Titre graph
    plt.legend() # Affiche la légende
    img_stream_knn = io.BytesIO() # Crée un flux mémoire pour stocker le graph comme image
    plt.savefig(img_stream_knn, format='png') # Sauvegarde dans le flux en format png
    plt.close() # Libère les ressources
    img_stream_knn.seek(0) # Positionne le pointeur au début du flux mémoire pour permettre bonne lecture de l'image
    img_base64_knn = base64.b64encode(img_stream_knn.read()).decode('utf-8') # Convertit image en chaine encodée Base64 puis la décode pour un affichage direct dans une page web

    # Formate les résultats des métriques (RMSE et Spearman)
    resultats_knn = (
        f"RMSE : {rmse_knn:.2f}\n"
        f"Coefficient de corrélation de Spearman: {rho_knn:.2f}\n"
        f"p-value: {p_value_knn:.4f}\n"
    )

    ### RandomForestRegressor ###

    # Création et entraînement du modèle RandomForest
    rf = RandomForestRegressor(n_estimators=100, random_state=333) # Crée une instance de forêt aléatoire avec 100 arbres et un seed aléatoire sauvegardé
    rf.fit(x_train_scaled, y_train) # Entraine le modèle avec les valeurs standardisé, x_train comme valeurs indépendantes et y_train comme cible
    y_rf_predicted = rf.predict(x_test_scaled) # Prédit les valeurs cible pour les données de test

    # Calcul des métriques de performance
    rmse_rf = np.sqrt(mean_squared_error(y_test, y_rf_predicted)) # Calcule l'erreur quadratique moyenne
    rho_rf, p_value_rf = stats.spearmanr(y_test, y_rf_predicted) # Calcul du coefficient de corrélation de Spearman

    # Graphique de RandomForestRegressor
    plt.figure(figsize=(16, 10)) # Taille du graphique
    plt.scatter(x_test, y_test, color='gray', label='Note réelle') # Nuage de points des notes réelles
    plt.plot(x_test, y_rf_predicted, color='green', linestyle=':', linewidth=0.8, label='RandomForestRegressor') # Ligne de prédictions du modèle
    plt.ylim(30, 100) # Ajustez les limites de l'axe y
    plt.xlabel('Rang') # Titre de l'axe X
    plt.ylabel('Notes moyennes') # Titre de l'axe Y
    plt.title('Prédiction des notes selon le rang') # Titre du graphique
    plt.legend() # Affiche la légende
    img_stream_rf = io.BytesIO() # Crée un flux mémoire pour stocker le graphique
    plt.savefig(img_stream_rf, format='png') # Sauvegarde l'image dans le flux
    plt.close() # Libère les ressources de la figure
    img_stream_rf.seek(0) # Positionne le pointeur au début du flux mémoire
    img_base64_rf = base64.b64encode(img_stream_rf.read()).decode('utf-8') # Encode l'image en base64 pour un affichage direct

    # Formate les résultats des métriques (RMSE et Spearman)
    resultats_rf = (
        f"RMSE : {rmse_rf:.2f}\n"
        f"Coefficient de corrélation de Spearman: {rho_rf:.2f}\n"
        f"p-value: {p_value_rf:.4f}\n"
    )

    ### Graphique de comparaison des 3 modèles ###

    plt.figure(figsize=(16, 10)) # Taille du graphique
    plt.scatter(x, y_actual, color='gray', label='Note réelle', alpha=0.5) # Nuage de point qui représente les notes réelles
    plt.plot(x_test, y_predicted, color='blue', linewidth=4, label='Régression linéaire') # Affiche la régression linéaire
    plt.scatter(x_test, y_knn_predicted, color='red', label='KNN (k=3)', s=15) # Affiche l'algorithme KNN
    plt.plot(x_test, y_rf_predicted, color='green', linestyle=':', linewidth=0.8, label='RandomForestRegressor') # Affiche la forêt aléatoire
    plt.ylim(30, 100) # Ajustez les limites de l'axe y
    plt.xlabel('Rang des Jeux') # Titre axe x
    plt.ylabel('Notes moyennes') # Titre axe y
    plt.title('Comparaison des modèles (Régression Linéaire, KNN, Random Forest)') # Titre graph
    plt.legend() # Affiche la légende
    img_stream_comparaison = io.BytesIO() # Crée un flux mémoire pour stocker le graph comme image
    plt.savefig(img_stream_comparaison, format='png') # Sauvegarde dans le flux en format png
    plt.close() # Libère les ressources
    img_stream_comparaison.seek(0) # Positionne le pointeur au début du flux mémoire pour permettre bonne lecture de l'image
    img_base64_comparaison = base64.b64encode(img_stream_comparaison.read()).decode('utf-8') # Convertit image en chaine encodée Base64 puis la décode pour un affichage direct dans une page web

    # Passer les résultats d'analyses et les graphiques encodés en Base64 comme des images png à la page AnalyseDF.html qui va gérer l'affichage de ceux-ci
    return render_template(
        "AnalyseDF.html",
        analyse_initiale=analyse_initiale,
        analyse_finale=analyse_finale,
        resultats_regression=resultats_regression,
        img_base64_regression=img_base64_regression,
        resultats_knn=resultats_knn,
        img_base64_knn=img_base64_knn,
        resultats_rf=resultats_rf,
        img_base64_rf=img_base64_rf,
        img_base64_comparaison=img_base64_comparaison
    )

########################################################################################################################

# Fonction basique pour attribuer une classification aux résultats des algorithmes (prédictions de la note)
def classification(note_reelle, prediction): # Déclare la fonction
    difference = abs(note_reelle - prediction) # Calcule différence absolue entre note réelle et prédiction
    if difference <= 2: # Si + ou - de 2
        return "Excellente prédiction", "green" # On attribue la classification d'excellente prédiction
    elif difference <= 4.5: # Si + ou - de 4.5
        return "Prédiction acceptable", "yellow" # On attribue la classification de prédiction acceptable
    else: # Sinon
        return "Mauvaise prédiction", "red" # On attribue la classification de mauvaise prédiction

# Route de recherche par rang sur lequel on veut effectuer les manipulations
@app.route('/recherche-rang', methods=['GET']) # Fonction recherche_par_rang() = URL '/recherche-rang/'. Accepte seulement requête GET
def recherche_par_rang():
    rang = request.args.get('rank') # Obtient le rang passé en paramètre par l'utilisateur
    if not rang: # Si aucun rang saisie
        return render_template('RechercheRang.html', resultat=None) # Affiche rien

    # Charger les données depuis MongoDB
    documents = list(collection.find({}, {"_id": 0})) # Récupère tous les champs sauf _id et convertit en liste
    df = pd.DataFrame(documents)  # Convertit la liste de documents en un DataFrame pandas pour mieux travailler

    # Définition des variables pour les modèles
    x = df['Rank'].values.reshape(-1, 1)  # Variable indépendante : rang, sous forme de tableau 2D avec reshape
    y_actual = df['Review'].values  # Variable dépendante : note réelle

    # Séparation des données en ensembles d'entraînement (80%) et de test (20%)
    x_train, x_test, y_train, y_test = train_test_split(x, y_actual, test_size=0.2, random_state=111)

    # Standardisation des données
    scaler = StandardScaler()  # Initialise un scaler pour standardiser les données (moyenne = 0, écart-type = 1)
    x_train_scaled = scaler.fit_transform(x_train) # Ajuste et transforme les données d'entraînement

    # Générer puis entraîner les modèles, exactement le même principe que la route /analyse
    rg = LinearRegression() # Génère un modèle de régression linéaire
    rg.fit(x_train_scaled, y_train) # Entraine le modèle avec x_train comme entrée et y_train comme cible
    knn = KNeighborsRegressor(n_neighbors=3) # Crée une instance de voisin le plus proche avec un paramètre de 3 (utilise les 3 points de données les plus proches pour estimer valeur de cible)
    knn.fit(x_train_scaled, y_train) # Entraine le modèle avec x_train comme valeurs indépendantes et y_train comme cible
    rf = RandomForestRegressor(n_estimators=100, random_state=123) # Crée une instance de forêt aléatoire. Estimators = nombre d'arbres de décision. State = Graine aléatoire pour pouvoir reproduire résultats
    rf.fit(x_train_scaled, y_train) # Entraine le modèle avec x_train comme valeurs indépendantes et y_train comme cible. Plusieurs arbres de décision sont créées et ils combinent leurs prédictions pour améliorer précision

    # Prédictions selon les différents modèles
    x_saisie = np.array([[int(rang)]])  # Crée un tableau 2D avec le rang qui a été saisie comme entrée
    x_saisie_scaled = scaler.transform(x_saisie)  # Applique la même standardisation au rang saisie (x)
    prediction_rg = rg.predict(x_saisie_scaled)[0]  # Modèle entrainé et standardisé de régression prédit la note pour le rang donné puis extrait la valeur de prédiction (predict retourne tableau de 1 valeur)
    prediction_knn = knn.predict(x_saisie_scaled)[0]  # Modèle entrainé et standardisé de KNN prédit la note pour le rang donné puis extrait la valeur de prédiction
    prediction_rf = rf.predict(x_saisie_scaled)[0]  # Modèle entrainé et standardisé de forêt prédit la note pour le rang donné puis extrait la valeur de prédiction

    # Récupérer la note réelle et le nom du jeu
    note_reelle = None # Vide par défaut
    nom_jeu = None # Vide par défaut
    if int(rang) in df['Rank'].values: # Vérifie si le rang saisi existe dans la base de données, si oui :
        note_reelle = df.loc[df['Rank'] == int(rang), 'Review'].values[0] # Récupère la note réelle associée au rang
        nom_jeu = df.loc[df['Rank'] == int(rang), 'Game Title'].values[0] # Récupère le nom du jeu associé au rang

    # Calcul des classifications selon la prédiction. Vérifie si note réelle existe pour le rang et appelle la fonction classification
    # qui compare chaque prédiction à la note réelle et stock les résultats dans 2 variables pour note prédite et couleur.
    # Sinon, elle est fixé à N/A
    classification_rg, color_rg = classification(note_reelle, prediction_rg) if note_reelle is not None else (
    "N/A", "gray")
    classification_knn, color_knn = classification(note_reelle, prediction_knn) if note_reelle is not None else (
    "N/A", "gray")
    classification_rf, color_rf = classification(note_reelle, prediction_rf) if note_reelle is not None else (
    "N/A", "gray")

    # Création du graphique
    fig, ax = plt.subplots(figsize=(8, 6)) # Taille du graph
    if note_reelle is not None: # Afficher uniquement le rang et la note réelle du jeu sélectionné (si elle existe)
        ax.scatter(int(rang), note_reelle, label='Note réelle', color='gray', zorder=2) # Affiche un point gris unique sur le graph représentant la note réelle
    ax.scatter(int(rang), prediction_rg, label='Prédiction Régression', color='blue', marker='d', zorder=1) # Affiche un losange bleu unique sur le graph représentant la prédiction de la régression
    ax.scatter(int(rang), prediction_knn, label='Prédiction KNN', color='red', marker='s', zorder=1) # Affiche un carré rouge unique sur le graph représentant la prédiction de KNN
    ax.scatter(int(rang), prediction_rf, label='Prédiction Forêt', color='green', marker='^', zorder=1) # Affiche un triangle vert unique sur le graph représentant la prédiction de la forêt aléatoire
    ax.set_xlim([min(df['Rank']) - 30, max(df['Rank']) + 30]) # Élargie les maximums de l'axe x (rang) sinon les points min et max sont collés sur la ligne du graph (rang 1, rang 1907 par exemple)
    min_y = max(0, note_reelle - 20) # Note minimum = 0. Les notes avec 20 points en dessous de la note réelle ne sont pas affichés pour la clarté
    max_y = min(100, note_reelle + 20) # Note maximum = 100. Les notes avec 20 points supérieur de la note réelle ne sont pas affichés pour la clarté
    ax.set_ylim(min_y, max_y) # Applique les conditions de limitations de l'axe y ci-haute
    ax.set_title(f"Prédictions pour le Rang {rang} (Jeu: {nom_jeu})") # Insère le rang et nom de jeu comme titre de graph
    ax.set_xlabel('Rang') # Titre axe x
    ax.set_ylabel('Note') # Titre axe y
    ax.legend() # Affiche légende

    # Sauvegarder le graphique dans un buffer en mémoire
    img_grap_rang = io.BytesIO() # Crée un flux mémoire pour stocker le graph comme image
    plt.savefig(img_grap_rang, format='png') # Sauvegarde en image png
    img_grap_rang.seek(0) # Positionne le pointeur au début du flux mémoire pour permettre bonne lecture de l'image
    img_base64 = base64.b64encode(img_grap_rang.getvalue()).decode('utf-8') # Convertit image en chaine encodée Base64 puis la décode pour un affichage direct dans une page web

    # Construire la réponse à envoyer comme résultat
    resultat = {
        "rang": rang, # Le rang recherché fournit par l'utilisateur
        "nom_jeu": nom_jeu, # Le nom du jeu correspondant au rang
        "note_reelle": note_reelle, # La note réelle correspondante au rang
        "prediction_regression": round(prediction_rg, 2), # Arrondis à deux décimales (prédiction linéaire)
        "prediction_knn": round(prediction_knn, 2), # Arrondis à deux décimales (prédiction KNN)
        "prediction_foret": round(prediction_rf, 2), # Arrondis à deux décimales (prédiction forêt)
        "classification": [
            # Liste avec classification qui inclut nom du modèle d'apprentissage, la classification donnée et la couleur associé
            {"modele": "Régression Linéaire", "classif": classification_rg, "color": color_rg},
            {"modele": "KNN", "classif": classification_knn, "color": color_knn},
            {"modele": "Forêt Aléatoire", "classif": classification_rf, "color": color_rf}
        ],
        "graphique": img_base64 # Chaine encodée en image qui représente le graphique généré
    }

    # Dictionnaire resultat en transmit comme paramètre à la page web qui va gérer l'affichage des éléments
    return render_template('RechercheRang.html', resultat=resultat)

########################################################################################################################