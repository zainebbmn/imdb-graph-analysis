import os

import pandas as pd


def analyze_graph(graph_or_tuple):
    """Analyze the most useful graph for exports.

    If a tuple `(bipartite_graph, collaboration_graph)` is provided, the
    collaboration graph is analyzed by default because it is more readable for
    actor/realisateur relationships.
    """
    if isinstance(graph_or_tuple, tuple):
        bipartite_graph, collaboration_graph = graph_or_tuple
        graph = collaboration_graph if collaboration_graph.number_of_nodes() else bipartite_graph
    else:
        bipartite_graph = None
        collaboration_graph = None
        graph = graph_or_tuple

    if graph.number_of_nodes() == 0:
        print("No graph, skip analysis")
        return {}

    os.makedirs("analysis", exist_ok=True)

    degrees = dict(graph.degree())
    weighted_degrees = dict(graph.degree(weight="weight"))
    degree_table = pd.DataFrame(
        [
            {
                "node": node,
                "label": graph.nodes[node].get("label", node),
                "type": graph.nodes[node].get("type", "unknown"),
                "degree": degrees.get(node, 0),
                "weighted_degree": weighted_degrees.get(node, 0),
            }
            for node in graph.nodes
        ]
    ).sort_values(["weighted_degree", "degree"], ascending=False)
    degree_table.to_csv("analysis/degrees.csv", index=False)

    top_nodes = degree_table.head(20)
    top_nodes.to_csv("analysis/top_nodes.csv", index=False)

    top_people = [
        (row["label"], int(row["weighted_degree"]))
        for _, row in degree_table.head(10).iterrows()
    ]

    summary = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "top_actors": top_people,
        "top_nodes": top_people,
        "graph_kind": "collaboration" if collaboration_graph is not None else "single_graph",
        "bipartite_nodes": bipartite_graph.number_of_nodes() if bipartite_graph is not None else graph.number_of_nodes(),
        "collaboration_nodes": collaboration_graph.number_of_nodes() if collaboration_graph is not None else graph.number_of_nodes(),
    }

    pd.DataFrame([summary]).to_csv("analysis/summary.csv", index=False)
    print("Analysis saved to analysis/")
    return summary
