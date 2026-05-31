import os

import matplotlib.pyplot as plt
import networkx as nx


os.makedirs("graphs", exist_ok=True)


def _select_graph(graph_or_tuple):
    if isinstance(graph_or_tuple, tuple):
        bipartite_graph, collaboration_graph = graph_or_tuple
        return collaboration_graph if collaboration_graph.number_of_nodes() else bipartite_graph
    return graph_or_tuple


def visualize_graph(graph_or_tuple, analysis_results):
    """Generate a few light static visualizations."""
    graph = _select_graph(graph_or_tuple)
    if graph.number_of_nodes() == 0:
        print("No graph to visualize.")
        return

    plt.figure(figsize=(12, 10))
    sample_nodes = list(graph.nodes())[: min(200, graph.number_of_nodes())]
    sample_graph = graph.subgraph(sample_nodes).copy()
    pos = nx.spring_layout(sample_graph, seed=42, weight="weight")
    nx.draw(
        sample_graph,
        pos,
        node_size=60,
        node_color="lightblue",
        edge_color="gray",
        with_labels=False,
    )
    plt.title("IMDb Collaboration Graph (sample view)")
    plt.savefig("graphs/graph.png", dpi=200, bbox_inches="tight")
    plt.close()

    degrees = [degree for _, degree in graph.degree()]
    plt.figure(figsize=(10, 6))
    plt.hist(degrees, bins=30, color="#2563eb", edgecolor="white")
    plt.title("Degree Distribution")
    plt.xlabel("Degree")
    plt.ylabel("Count")
    plt.savefig("graphs/degrees_hist.png", dpi=200, bbox_inches="tight")
    plt.close()

    top_people = analysis_results.get("top_actors", [])
    if top_people:
        names, values = zip(*top_people[:10])
        plt.figure(figsize=(10, 6))
        plt.bar(range(len(values)), values, color="#0f766e")
        plt.xticks(range(len(values)), [name[:18] for name in names], rotation=45, ha="right")
        plt.title("Top 10 people by collaboration weight")
        plt.tight_layout()
        plt.savefig("graphs/top_actors.png", dpi=200, bbox_inches="tight")
        plt.close()

    print("Visualizations saved to graphs/")
