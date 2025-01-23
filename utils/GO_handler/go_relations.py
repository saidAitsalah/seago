import requests
import networkx as nx
from pyvis.network import Network
import os
import webbrowser
import time

go_terms = ["GO:0000976", "GO:0000977", "GO:0000978", "GO:0000981", "GO:0000982", "GO:0000987"]

# graphe dirigé
G = nx.DiGraph()

# les ancestors and descendants
def get_go_relations(go_id, relation_type):
    url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}/{relation_type}"
    response = requests.get(url, headers={"Accept": "application/json"})
    if response.status_code == 200:
        data = response.json()
        return data["results"][0].get(relation_type, []) if "results" in data and data["results"] else []
    return []

# specific relations
def get_go_specific_relations(go_id):
    url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}/relations"
    response = requests.get(url, headers={"Accept": "application/json"})
    if response.status_code == 200:
        data = response.json()
        return data["results"][0].get("relations", []) if "results" in data and data["results"] else []
    return []

for go_id in go_terms:
    # adding directe relations
    for relation in get_go_specific_relations(go_id):
        G.add_edge(relation["subject"], relation["object"], label=relation["relation"])
    
    #  ancestors
    for ancestor in get_go_relations(go_id, "ancestors"):
        G.add_edge(go_id, ancestor, label="ancestor")
    
    #   descendants
    for descendant in get_go_relations(go_id, "descendants"):
        G.add_edge(descendant, go_id, label="descendant")

# Pyvis
net = Network(notebook=True, directed=True, height="800px", width="100%", bgcolor="#222222", font_color="white")
net.from_nx(G)

# adding labels to edges
for edge in G.edges(data=True):
    net.add_edge(edge[0], edge[1], title=edge[2]['label'])

net.force_atlas_2based(gravity=-50, central_gravity=0.1, spring_length=200, spring_strength=0.02, damping=0.4)
options = """
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
"""
net.set_options(options)

output_file = "go_graph.html"
net.show(output_file)

current_dir = os.getcwd()
os.system(f"python -m http.server 8000 --directory {current_dir} &")  

time.sleep(1)
webbrowser.open(f'http://localhost:8000/{output_file}')

print(f" Graphe généré et ouvert dans votre navigateur : {output_file}")
