import networkx as nx

from graph_builder import build_imdb_graph


def build_models(sample_size: int | None = None):
    """Return the bipartite graph and the collaboration graph."""
    return build_imdb_graph(sample_size=sample_size)


def graph_algorithms(bipartite_graph: nx.Graph, collaboration_graph: nx.Graph):
    """Compute a few reusable graph metrics."""
    degree_centrality = nx.degree_centrality(collaboration_graph)
    betweenness = (
        nx.betweenness_centrality(
            collaboration_graph,
            k=min(100, max(10, collaboration_graph.number_of_nodes() // 10)),
            weight="weight",
        )
        if collaboration_graph.number_of_nodes() > 1
        else {}
    )
    communities = (
        list(nx.community.greedy_modularity_communities(collaboration_graph, weight="weight"))
        if collaboration_graph.number_of_edges() > 0
        else []
    )
    return {
        "degree_centrality": degree_centrality,
        "betweenness": betweenness,
        "communities": communities,
        "bipartite_nodes": bipartite_graph.number_of_nodes(),
        "collaboration_nodes": collaboration_graph.number_of_nodes(),
    }


if __name__ == "__main__":
    graph_bipartite, graph_collab = build_models(sample_size=50_000)
    metrics = graph_algorithms(graph_bipartite, graph_collab)
    print(
        f"Graph G: {graph_bipartite.number_of_nodes()} nodes, "
        f"{graph_bipartite.number_of_edges()} edges"
    )
    print(
        f"Actor/realisateur collab: {graph_collab.number_of_nodes()} people, "
        f"{graph_collab.number_of_edges()} collab edges"
    )
    top_degree = sorted(metrics["degree_centrality"], key=metrics["degree_centrality"].get, reverse=True)[:5]
    print(f"Degree centrality top: {top_degree}")
    print(f"Communautes trouvees: {len(metrics['communities'])}")
