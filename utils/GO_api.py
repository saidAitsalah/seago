import requests
import networkx as nx
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import requests
import time
import json
import os
from PySide6.QtWebEngineWidgets import QWebEngineView



class GONetwork:
    @staticmethod
    def get_go_terms(query):
        """Récupérer les termes GO et leurs relations depuis l'API GO."""
        url = f"http://api.geneontology.org/api/ontology/term/{query}/graph"
        print(f"URL de requête : {url}")
        start_time = time.time()
        response = requests.get(url)
        end_time = time.time()
        if response.status_code == 200:
            print("Données récupérées avec succès.")
            print(f"Temps de réponse: {end_time - start_time} secondes")

            return response.json()
        else:
            print(f"Erreur de requête API GO : {response.status_code}")
            return None

    def create_go_network(self, go_data):
        """Créer un graphe NetworkX à partir des données GO."""
        G = nx.DiGraph()
        print(f"Données récupérées : {go_data}")  # Ajout de cette ligne pour afficher les données brutes

        # Mise à jour pour accéder aux données sous 'topology_graph_json'
        if 'topology_graph_json' not in go_data:
            print("Aucun graphe trouvé dans les données GO.")
            return None

        graph_data = go_data['topology_graph_json']
        for term in graph_data['nodes']:
            G.add_node(term['id'], label=term.get('lbl', ''))
        for edge in graph_data['edges']:
            G.add_edge(edge['sub'], edge['obj'])
        return G

    def create_go_network_tab(self, query):
        """Créer un onglet pour afficher un réseau de termes GO avec vis.js"""
        print(f"Récupération des données GO pour le terme : {query}")
        go_data = self.get_go_terms(query)
        if go_data is None:
            print("Échec de la récupération des données GO.")
            return None

        G = self.create_go_network(go_data)
        if G is None or len(G.nodes) == 0:
            print("Échec de la création du graphe NetworkX.")
            return None

        print(f"Graph NetworkX créé avec {len(G.nodes)} nœuds et {len(G.edges)} arêtes.")

        # Générer le fichier HTML
        html_path = self.save_graph_as_html(G)

        # Créer le widget QWebEngineView pour afficher le graphe interactif
        web_view = QWebEngineView()
        web_view.setUrl(f"file://{html_path}")

        return web_view

    def save_graph_as_html(self, G, filename="go_network.html"):
            """Sauvegarde le graphe NetworkX en un fichier HTML avec vis.js"""
            nodes = [{"id": n, "label": G.nodes[n]["label"]} for n in G.nodes()]
            edges = [{"from": e[0], "to": e[1]} for e in G.edges()]
            graph_data = {"nodes": nodes, "edges": edges}

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/vis-network.min.js"></script>
                <style> #mynetwork {{ width: 100vw; height: 100vh; }} </style>
            </head>
            <body>
                <div id="mynetwork"></div>
                <script>
                    var nodes = new vis.DataSet({json.dumps(nodes)});
                    var edges = new vis.DataSet({json.dumps(edges)});
                    var container = document.getElementById('mynetwork');
                    var data = {{ nodes: nodes, edges: edges }};
                    var options = {{ nodes: {{ shape: "dot", size: 20 }} }};
                    var network = new vis.Network(container, data, options);
                </script>
            </body>
            </html>
            """

            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            return os.path.abspath(filename)