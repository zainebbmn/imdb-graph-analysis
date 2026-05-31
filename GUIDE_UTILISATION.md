# Guide d'utilisation

Ce document explique comment lancer et utiliser l'application IMDb Graph Analysis.

## 1. Prerequis

Avant de lancer l'application, verifier que :

- Python est installe
- les dependances du projet sont installees
- les fichiers de donnees IMDb necessaires sont disponibles localement

## 2. Installer les dependances

Si ce n'est pas deja fait :

```powershell
pip install -r requirements.txt
```

## 3. Lancer l'application

Depuis le dossier du projet :

```powershell
streamlit run app.py
```

Ou, si vous utilisez l'environnement virtuel du projet :

```powershell
venv\Scripts\streamlit.exe run app.py
```

## 4. Ouvrir l'application

Par defaut, Streamlit ouvre l'application sur :

```text
http://localhost:8501
```

Si le port `8501` est deja utilise, Streamlit affichera une autre URL dans le terminal. Il faut alors ouvrir cette nouvelle adresse dans le navigateur.

## 5. Onglets principaux

L'application contient plusieurs vues :

- `Graphe interactif acteurs`
  - graphe principal acteur <-> acteur
  - recherche par acteur ou film
  - clic sur sommets et aretes

- `Carte acteurs`
  - vue geographique secondaire
  - affichage spatial simplifie selon les regions IMDb

- `Analyses`
  - statistiques et indicateurs reseau
  - acteurs les plus connectes
  - repartitions globales

- `Exemples reseau`
  - autres graphes construits a partir des memes donnees
  - communautes <-> communautes
  - films <-> films
  - createurs <-> createurs

- `Synthese projet`
  - vues globales du reseau
  - grandes communautes
  - distances entre communautes
  - repartitions par genre et acteurs importants

- `Donnees et details`
  - informations sur les fichiers utilises
  - volumes lus et structures exploitees

## 6. Utilisation rapide

### Rechercher un acteur ou un film

Dans l'onglet `Graphe interactif acteurs` :

- utilisez la barre de recherche
- tapez un nom d'acteur ou un titre

### Voir les details d'un acteur

- cliquez sur un sommet
- les informations de l'acteur apparaissent dans le panneau de details

### Voir les details d'un lien

- cliquez sur une arete
- l'application affiche les titres en commun entre les deux acteurs

### Calculer un plus court chemin

- choisissez un acteur de depart
- choisissez un acteur d'arrivee
- le tableau affiche le chemin trouve et les acteurs intermediaires si necessaire

## 7. Interpretation rapide

Dans le graphe principal :

- `1 sommet = 1 acteur`
- `1 arete = au moins 1 film en commun`
- `poids = nombre de films partages`

Donc :

- plus un acteur a de voisins, plus il est connecte
- plus deux acteurs partagent de films, plus leur lien est fort

## 8. En cas de probleme

### L'application ne s'affiche pas

- verifiez que Streamlit est bien lance
- faites un `Ctrl + F5` dans le navigateur
- relancez l'application si besoin

### Le port n'est pas 8501

Ce n'est pas une erreur.

- regardez l'URL affichee dans le terminal
- ouvrez cette URL dans le navigateur

### Certaines vues sont plus longues a charger

Les vues les plus lourdes sont celles qui utilisent :

- les graphes globaux
- les communautes
- certaines visualisations de synthese

Il peut donc y avoir un temps de chargement plus important selon la vue.

## 9. Commande resume

Commande principale pour lancer l'application :

```powershell
venv\Scripts\streamlit.exe run app.py
```
