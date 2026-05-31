# IMDb Graph Analysis

Application Streamlit d'exploration de graphes construits a partir des donnees IMDb Open Data.

## Fonction principale

Le projet construit un graphe `acteur <-> acteur` ou :

- `1 sommet = 1 acteur`
- `1 arete = au moins un film en commun`
- `poids = nombre de titres partages`

L'application permet ensuite de :

- visualiser le graphe interactif principal
- explorer les communautes detectees
- calculer le plus court chemin entre deux acteurs
- consulter une synthese globale du reseau
- afficher des graphes secondaires

## Fichiers principaux

- `app.py` : application Streamlit principale
- `data_loader.py` : chargement / lecture des donnees IMDb
- `graph_builder.py` : construction des graphes
- `graph_algorithms.py` : algorithmes de graphe
- `analysis.py` : calculs et statistiques complementaires
- `visualize.py` : sorties graphiques statiques

## Lancement

1. Creer un environnement virtuel
2. Installer les dependances :

```powershell
pip install -r requirements.txt
```

3. Lancer l'application :

```powershell
streamlit run app.py
```

## Donnees

Les fichiers TSV IMDb volumineux et les caches locaux ne sont pas prevus pour etre pushes sur GitHub. Ils sont ignores via `.gitignore`.

## Sorties conservees

Le dossier `outputs/` garde uniquement les exports encore utilises par l'application pour la vue de synthese.
