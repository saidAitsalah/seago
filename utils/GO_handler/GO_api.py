import requests
import networkx as nx
from pyvis.network import Network
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView

#to review
class GoGraphWidget(QWidget):
    def __init__(self, go_terms, parent=None):
        super().__init__(parent) 
        self.go_terms = go_terms 
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)
        self.generate_go_graph()

    def get_go_relations(self, go_id, relation_type):
        """ Récupère les ancêtres ou descendants d'un terme GO """
        url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}/{relation_type}"
        response = requests.get(url, headers={"Accept": "application/json"})
        if response.status_code == 200:
            data = response.json()
            return data["results"][0].get(relation_type, []) if "results" in data and data["results"] else []
        return []

    def get_go_specific_relations(self, go_id):
        """ Récupère les relations spécifiques d'un terme GO """
        url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}/relations"
        response = requests.get(url, headers={"Accept": "application/json"})
        if response.status_code == 200:
            data = response.json()
            return data["results"][0].get("relations", []) if "results" in data and data["results"] else []
        return []

    def generate_go_graph(self):
        """ Génère un graphe interactif et l'affiche dans QWebEngineView """
        file_path = "go_graph.html"
        G = nx.DiGraph()

        # Build the graph by recovering the relationships
        for go_id in self.go_terms:
            # directe relationships
            for relation in self.get_go_specific_relations(go_id):
                G.add_edge(relation["subject"], relation["object"], label=relation["relation"])
            
            # ancestors
            for ancestor in self.get_go_relations(go_id, "ancestors"):
                G.add_edge(go_id, ancestor, label="ancestor")

            # Descendance
            for descendant in self.get_go_relations(go_id, "descendants"):
                G.add_edge(descendant, go_id, label="descendant")

        # graphe with Pyvis
        net = Network(notebook=False, directed=True, height="750px", width="100%", bgcolor="#222222", font_color="white")
        net.from_nx(G)

        #adding label on edges
        for edge in G.edges(data=True):
            net.add_edge(edge[0], edge[1], title=edge[2]['label'])

        # Optimisation of the layout
        net.force_atlas_2based(gravity=-50, central_gravity=0.1, spring_length=200, spring_strength=0.02, damping=0.4)

        # displaying options
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -8000,
                    "centralGravity": 0.3,
                    "springLength": 100,
                    "springConstant": 0.04
                }
            }
        }
        """)

        # generation iof the html
        net.write_html(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # displaying in QWebEngineView
        self.web_view.setHtml(html_content)
