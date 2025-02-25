# SeaGo - Annotation and Visualization of Genomic Data

## Description
SeaGo est une application de bureau développée pour l'annotation et la visualisation des données génomiques. Elle permet de charger des fichiers JSON contenant des résultats d'analyses génomiques, de les afficher dans un tableau interactif et de fournir diverses visualisations et outils d'exportation.

## Fonctionnalités

### Chargement et Analyse des Données
- **Chargement des fichiers JSON** : Permet de sélectionner et de charger des fichiers JSON contenant des résultats d'analyses génomiques.
- **Analyse des données** : Les données JSON sont traitées et préparées pour l'affichage et la visualisation.

### Affichage Principal du Tableau
- **Tableau interactif** : Affichage des données analysées via un `QTableWidget`.
- **Widgets de données** : Interaction avec les cellules pour une meilleure expérience utilisateur.

### Filtrage et Tri
- **Filtrage dynamique** : Application de filtres pour affiner les données affichées.
- **Tri des données** : Tri des colonnes pour faciliter l'analyse.

### Visualisation des Données
- **Onglets de visualisation** :
  - **Tableau des Hits** : Affichage des résultats BLAST.
  - **Tableau des Domaines** : Affichage des annotations InterProScan.
  - **Vue des Détails** : Informations détaillées sur les annotations sélectionnées.
  - **Annotations GO** : Visualisation des annotations GO.
  - **Graphiques de Distribution** : Représentation graphique des données.
  - **Métadonnées** : Affichage des informations sur les analyses.

### Exportation des Données
- **Formats supportés** : JSON, CSV et TSV.

### Barre de Statut et Barre de Menu
- **Barre de statut** : Affiche les informations sur l'application.
- **Barre de menu** : Accès rapide aux opérations courantes.

## Structure du Projet

```
root
├── main.py
├── ui
│   ├── table_window.py
│   ├── donut_widget.py
│   ├── distributionChart.py
├── utils
│   ├── data_loader.py
│   ├── table_manager.py
│   ├── export_utils.py
│   ├── GO_handler
│       ├── GO_api.py
│       ├── obo.py
├── data_model.py
├── ontologies
│   ├── go-basic.obo
│   ├── enzclass.txt
├── assets
│   ├── images.png
├── requirements.txt
├── README.md
```

## Installation

### Prérequis
- **Python 3.8 ou supérieur**
- **PySide6**

### Installation des Dépendances
```sh
pip install -r requirements.txt
```

### Lancement de l'Application
```sh
python main.py
```

## Utilisation
1. **Lancer l'application** : Exécutez `main.py`.
2. **Charger un fichier JSON** : Utilisez la boîte de dialogue de fichier.
3. **Explorer les données** : Naviguez dans les différents onglets et tableaux.
4. **Exporter les données** : Utilisez les options d'exportation pour sauvegarder les résultats.

## Contribuer
Les contributions sont les bienvenues !

1. **Forker** le dépôt
2. **Cloner** votre fork
3. Créer une nouvelle branche :
   ```sh
   git checkout -b feature/YourFeature
   ```
4. Faire vos modifications et commit :
   ```sh
   git commit -am "Ajout d'une nouvelle fonctionnalité"
   ```
5. Pousser votre branche :
   ```sh
   git push origin feature/YourFeature
   ```
6. Créer une **Pull Request**




