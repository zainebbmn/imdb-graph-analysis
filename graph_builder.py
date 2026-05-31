from itertools import combinations

import networkx as nx

from data_loader import load_aggregated


ACTOR_NODE_TYPES = {"actor", "actress", "realisateur"}


def build_imdb_graph(sample_size: int | None = None):
    """Build a bipartite graph and an actor/realisateur collaboration graph.

    If `data_aggregated.json` is missing, fall back to a small built-in sample
    graph so the rest of the pipeline still runs.
    """
    nodes_df, edges_df = load_aggregated()
    if nodes_df.empty:
        print("No aggregated data found. Using a small fallback graph.")
        bipartite_graph = nx.karate_club_graph()
        for node in bipartite_graph.nodes:
            bipartite_graph.nodes[node]["label"] = str(node)
            bipartite_graph.nodes[node]["type"] = "actor"
            bipartite_graph.nodes[node]["degree"] = bipartite_graph.degree(node)
        return bipartite_graph, bipartite_graph.copy()

    if sample_size is not None:
        nodes_df = nodes_df.head(sample_size).copy()
        valid_ids = set(nodes_df["id"])
        edges_df = edges_df[
            edges_df["source"].isin(valid_ids) & edges_df["target"].isin(valid_ids)
        ].copy()

    bipartite_graph = nx.Graph()

    for _, node in nodes_df.iterrows():
        bipartite_graph.add_node(
            node["id"],
            label=node.get("label", node["id"]),
            type=node.get("type", "unknown"),
            lat=node.get("lat", 0),
            lon=node.get("lon", 0),
            rating=node.get("averageRating", 0),
        )

    for _, edge in edges_df.iterrows():
        bipartite_graph.add_edge(
            edge["source"],
            edge["target"],
            weight=int(edge.get("weight", 1) or 1),
            type=edge.get("type", "bipartite"),
        )

    for node in bipartite_graph.nodes:
        bipartite_graph.nodes[node]["degree"] = bipartite_graph.degree(node)

    collaboration_graph = nx.Graph()
    actor_nodes = [
        node for node, data in bipartite_graph.nodes(data=True) if data.get("type") in ACTOR_NODE_TYPES
    ]

    for node in actor_nodes:
        collaboration_graph.add_node(node, **bipartite_graph.nodes[node])

    title_nodes = [
        node for node, data in bipartite_graph.nodes(data=True) if data.get("type") not in ACTOR_NODE_TYPES
    ]
    for title_node in title_nodes:
        collaborators = [neighbor for neighbor in bipartite_graph.neighbors(title_node) if neighbor in collaboration_graph]
        for left, right in combinations(sorted(collaborators), 2):
            if collaboration_graph.has_edge(left, right):
                collaboration_graph[left][right]["weight"] += 1
            else:
                collaboration_graph.add_edge(left, right, weight=1)

    for node in collaboration_graph.nodes:
        collaboration_graph.nodes[node]["degree"] = collaboration_graph.degree(node)

    print(
        f"Graph built: {bipartite_graph.number_of_nodes()} nodes, "
        f"{bipartite_graph.number_of_edges()} bipartite edges"
    )
    print(
        f"Collaboration graph: {collaboration_graph.number_of_nodes()} people, "
        f"{collaboration_graph.number_of_edges()} collaboration edges"
    )
    return bipartite_graph, collaboration_graph


if __name__ == "__main__":
    graph_bipartite, graph_collab = build_imdb_graph()
    print(graph_bipartite)
    print(graph_collab)
