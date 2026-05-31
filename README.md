# IMDb Graph Analysis

Projet d'analyse de graphes construit a partir des donnees **IMDb Open Data**.

L'application principale est une interface **Streamlit** qui transforme les collaborations entre acteurs en reseau interactif afin d'explorer :

- les liens entre acteurs
- les communautes de collaboration
- les acteurs les plus centraux
- les plus courts chemins dans le reseau
- plusieurs graphes secondaires issus du meme jeu de donnees

## Objectif du projet

Le projet cherche a repondre a la question suivante :

> Comment un graphe d'acteurs permet-il de reveler les communautes, les liens et les distances du reseau ?

Pour cela, les fichiers IMDb sont nettoyes, fusionnes, puis transformes en graphes exploitables pour l'analyse et la visualisation.

## Fonctionnalites principales

### Application web

L'application `app.py` permet de :

- rechercher un acteur ou un film
- filtrer les donnees visibles
- afficher un graphe principal `acteur <-> acteur`
- consulter les details d'un acteur ou d'un lien
- calculer le plus court chemin entre deux acteurs
- explorer une vue de synthese du reseau
- afficher des graphes secondaires

### Graphe principal

Le modele principal est :

- `1 sommet = 1 acteur`
- `1 arete = au moins un film en commun`
- `poids = nombre de titres partages`

Le graphe est **non oriente** et **pondere**.

## Donnees utilisees

Le projet s'appuie sur plusieurs fichiers IMDb Open Data :

- `title.principals.tsv`
- `name.basics.tsv`
- `title.basics.tsv`
- `title.ratings.tsv`
- `title.akas.tsv`

Ces fichiers permettent de relier :

- les personnes
- les titres
- les genres
- les notes et votes IMDb
- certaines informations de region utilisees dans l'application

## Logique de calcul

Les calculs importants du projet sont :

- construction des liens entre acteurs a partir des films en commun
- calcul du poids des aretes
- detection des communautes par modularite
- calcul du degre et du degre pondere
- calcul des plus courts chemins
- calcul de statistiques globales sur les communautes et les genres

## Structure du projet

### Fichiers Python principaux

- `app.py` : application Streamlit principale
- `data_loader.py` : lecture / chargement des donnees IMDb
- `graph_builder.py` : construction des graphes
- `graph_algorithms.py` : algorithmes et mesures de graphe
- `analysis.py` : calculs et statistiques
- `visualize.py` : visualisations statiques
- `aggregate_data.py` : preparation / aggregation des donnees
- `main.py` : pipeline secondaire de traitement

### Scripts d'export utilises

- `export_backend_community_bubbles.py`
- `export_backend_community_bubbles_all_actors.py`
- `export_community_shortest_paths_focus.py`
- `export_actor_producers_by_community.py`

### Ressources front-end

- `lib/vis-9.1.2/` : bibliotheque reseau
- `lib/tom-select/` : composant de selection

### Sorties conservees dans le depot

Le dossier `outputs/` contient uniquement les exports encore utilises par l'application pour la vue de synthese.

## Installation

### 1. Creer un environnement virtuel

```powershell
python -m venv venv
```

### 2. Activer l'environnement

```powershell
venv\Scripts\activate
```

### 3. Installer les dependances

```powershell
pip install -r requirements.txt
```

## Lancement de l'application

```powershell
streamlit run app.py
```

Ou, si besoin :

```powershell
venv\Scripts\streamlit.exe run app.py
```

Puis ouvrir dans le navigateur :

```text
http://localhost:8501
```

## Notes importantes

- Les fichiers `.tsv` IMDb volumineux ne sont pas prevus pour etre pushes sur GitHub.
- Les caches `.pkl`, les logs, les environnements virtuels et les gros fichiers locaux sont ignores via `.gitignore`.
- Certaines vues de synthese de l'application s'appuient sur les exports presents dans `outputs/`.

## Depot GitHub

Le depot contient :

- le code utile au projet
- les ressources front-end necessaires
- les petits exports encore utilises par l'application

Il ne contient pas :

- les donnees IMDb brutes volumineuses
- les caches locaux
- les documents de soutenance et fichiers temporaires
