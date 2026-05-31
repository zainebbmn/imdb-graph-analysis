from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import networkx as nx
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent
CACHE_PATH = ROOT_DIR / "imdb_graph_analysis_cache_300000.pkl"
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_PNG = OUTPUT_DIR / "backend_community_bubbles_top.png"
OUTPUT_JSON = OUTPUT_DIR / "backend_community_bubbles_top_stats.json"
OUTPUT_CSV = OUTPUT_DIR / "backend_community_bubbles_top_stats.csv"
OUTPUT_MD = OUTPUT_DIR / "backend_community_bubbles_top_analysis.md"

TITLE_LIMIT = 2_000
MAX_ACTORS_PER_TITLE = 12
TOP_COMMUNITIES = 8
MAX_ACTORS_PER_COMMUNITY = 120
MIN_EDGE_WEIGHT = 1

ACTOR_CATEGORIES = {"actor", "actress"}
COMMUNITY_COLORS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#65a30d",
    "#4f46e5",
    "#ea580c",
    "#0f766e",
    "#e11d48",
]


def load_cached_backend() -> tuple[pd.DataFrame, dict]:
    if not CACHE_PATH.exists():
        raise FileNotFoundError(f"Cache introuvable: {CACHE_PATH}")
    frame, audit = pd.read_pickle(CACHE_PATH)
    return frame.copy(), dict(audit)


def select_top_titles(frame: pd.DataFrame, limit: int) -> list[str]:
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    ranked = (
        actor_rows.groupby("tconst")
        .agg(
            actor_count=("nconst", "nunique"),
            numVotes=("numVotes", "max"),
            averageRating=("averageRating", "max"),
        )
        .reset_index()
        .sort_values(
            ["actor_count", "numVotes", "averageRating", "tconst"],
            ascending=[False, False, False, True],
        )
        .head(limit)
    )
    return ranked["tconst"].tolist()


def build_actor_graph(frame: pd.DataFrame) -> nx.Graph:
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    graph = nx.Graph()

    for actor_id, group in actor_rows.groupby("nconst"):
        graph.add_node(
            actor_id,
            label=group["primaryName"].iloc[0],
            projects=int(group["tconst"].nunique()),
        )

    for _, group in actor_rows.groupby("tconst"):
        actors = group[["nconst", "primaryName"]].drop_duplicates("nconst")
        if len(actors) < 2:
            continue
        if len(actors) > MAX_ACTORS_PER_TITLE:
            actors = actors.head(MAX_ACTORS_PER_TITLE)

        for left, right in combinations(actors["nconst"].tolist(), 2):
            title_label = group["titleLabel"].iloc[0]
            genres = sorted(
                {
                    genre
                    for genres_list in group["genresList"]
                    for genre in genres_list
                    if genre and genre != "Unknown"
                }
            )
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
                graph[left][right]["titles"].add(title_label)
                graph[left][right]["genres"].update(genres)
            else:
                graph.add_edge(left, right, weight=1, titles={title_label}, genres=set(genres))

    graph.remove_edges_from([(u, v) for u, v, data in graph.edges(data=True) if int(data.get("weight", 1)) < MIN_EDGE_WEIGHT])
    graph.remove_nodes_from(list(nx.isolates(graph)))

    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))
    nx.set_node_attributes(graph, degree_map, "degree")
    nx.set_node_attributes(graph, weighted_degree_map, "weighted_degree")

    for _, _, data in graph.edges(data=True):
        data["titles"] = sorted(data["titles"])
        data["genres"] = sorted(data["genres"])

    return graph


def detect_communities(graph: nx.Graph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    if graph.number_of_edges() == 0:
        mapping = {node: index + 1 for index, node in enumerate(graph.nodes())}
        nx.set_node_attributes(graph, mapping, "community")
        return mapping

    communities = nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")
    mapping: dict[str, int] = {}
    for index, community in enumerate(communities, start=1):
        for node in community:
            mapping[node] = index
    nx.set_node_attributes(graph, mapping, "community")
    return mapping


def top_genres_text(values: pd.Series, limit: int = 3) -> str:
    counter: Counter[str] = Counter()
    for item in values:
        if isinstance(item, list):
            for genre in item:
                if genre and genre != "Unknown":
                    counter[str(genre)] += 1
    if not counter:
        return "Unknown"
    return ", ".join(genre for genre, _ in counter.most_common(limit))


def compute_community_stats(graph: nx.Graph, actor_rows: pd.DataFrame) -> tuple[pd.DataFrame, nx.Graph]:
    community_map = nx.get_node_attributes(graph, "community")
    rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())].copy()
    rows["community"] = rows["nconst"].map(community_map)

    community_graph = nx.Graph()
    edge_buckets: dict[tuple[int, int], dict[str, object]] = {}

    for left, right, data in graph.edges(data=True):
        left_c = community_map.get(left)
        right_c = community_map.get(right)
        if left_c is None or right_c is None:
            continue
        if left_c == right_c:
            continue
        pair = tuple(sorted((int(left_c), int(right_c))))
        bucket = edge_buckets.setdefault(pair, {"weight": 0, "titles": set(), "bridges": set()})
        bucket["weight"] += int(data.get("weight", 1))
        bucket["titles"].update(data.get("titles", []))
        bucket["bridges"].update(
            [
                graph.nodes[left].get("label", left),
                graph.nodes[right].get("label", right),
            ]
        )

    for (left_c, right_c), bucket in edge_buckets.items():
        community_graph.add_edge(
            left_c,
            right_c,
            weight=int(bucket["weight"]),
            titles=sorted(bucket["titles"]),
            bridges=sorted(bucket["bridges"]),
        )

    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))

    results: list[dict[str, object]] = []
    grouped_actor_ids: dict[int, list[str]] = defaultdict(list)
    for node, community_id in community_map.items():
        grouped_actor_ids[int(community_id)].append(node)

    for community_id, actor_ids in grouped_actor_ids.items():
        subgraph = graph.subgraph(actor_ids).copy()
        community_rows = rows[rows["community"] == community_id].copy()
        if community_rows.empty:
            continue

        internal_weight = int(sum(data.get("weight", 1) for _, _, data in subgraph.edges(data=True)))
        top_actor_id = max(actor_ids, key=lambda actor_id: weighted_degree_map.get(actor_id, 0))
        top_actor_name = graph.nodes[top_actor_id].get("label", top_actor_id)
        top_actor_degree = int(weighted_degree_map.get(top_actor_id, 0))

        external_weight = 0
        bridge_actor_id = None
        bridge_actor_weight = -1
        for actor_id in actor_ids:
            actor_external = 0
            for neighbor in graph.neighbors(actor_id):
                if community_map.get(neighbor) != community_id:
                    actor_external += int(graph[actor_id][neighbor].get("weight", 1))
            external_weight += actor_external
            if actor_external > bridge_actor_weight:
                bridge_actor_weight = actor_external
                bridge_actor_id = actor_id

        results.append(
            {
                "community_id": int(community_id),
                "actor_count": int(len(actor_ids)),
                "edge_count": int(subgraph.number_of_edges()),
                "internal_weight": internal_weight,
                "density": float(nx.density(subgraph)) if subgraph.number_of_nodes() > 1 else 0.0,
                "title_count": int(community_rows["tconst"].nunique()),
                "dominant_genres": top_genres_text(community_rows["genresList"], limit=3),
                "central_actor": top_actor_name,
                "central_actor_weighted_degree": top_actor_degree,
                "bridge_actor": graph.nodes[bridge_actor_id].get("label", bridge_actor_id) if bridge_actor_id else "n/a",
                "bridge_external_weight": int(max(bridge_actor_weight, 0)),
                "external_weight_total": int(external_weight),
            }
        )

    stats_table = pd.DataFrame(results)
    if stats_table.empty:
        return stats_table, community_graph

    stats_table["importance_score"] = (
        stats_table["actor_count"] * 4
        + stats_table["internal_weight"] * 0.2
        + stats_table["edge_count"] * 0.1
        + stats_table["density"] * 100
    )
    stats_table = stats_table.sort_values(
        ["importance_score", "actor_count", "internal_weight"],
        ascending=False,
    ).reset_index(drop=True)
    return stats_table, community_graph


def build_display_subgraph(graph: nx.Graph, top_communities: list[int]) -> nx.Graph:
    selected_nodes: list[str] = []
    for community_id in top_communities:
        community_nodes = [
            node
            for node, data in graph.nodes(data=True)
            if int(data.get("community", 0)) == int(community_id)
        ]
        community_nodes = sorted(
            community_nodes,
            key=lambda node_id: graph.nodes[node_id].get("weighted_degree", 0),
            reverse=True,
        )[:MAX_ACTORS_PER_COMMUNITY]
        selected_nodes.extend(community_nodes)
    return graph.subgraph(selected_nodes).copy()


def compute_positions(
    display_graph: nx.Graph,
    selected_stats: pd.DataFrame,
    community_graph: nx.Graph,
) -> tuple[dict[str, tuple[float, float]], dict[int, tuple[float, float]], dict[int, float]]:
    community_ids = selected_stats["community_id"].astype(int).tolist()
    community_radii = {
        int(row.community_id): 6.0 + math.sqrt(max(int(row.actor_count), 1)) * 1.15
        for row in selected_stats.itertuples(index=False)
    }
    meta_graph = community_graph.subgraph(community_ids).copy()
    meta_graph.add_nodes_from(community_ids)
    if meta_graph.number_of_nodes() == 0:
        meta_graph.add_nodes_from(community_ids)

    if meta_graph.number_of_edges() > 0:
        community_centers = nx.spring_layout(meta_graph, seed=42, weight="weight", k=2.5)
    else:
        community_centers = {}
        cols = max(1, math.ceil(math.sqrt(len(community_ids))))
        for index, community_id in enumerate(community_ids):
            community_centers[community_id] = (index % cols, -(index // cols))

    community_centers = {
        int(community_id): (float(coords[0]) * 40.0, float(coords[1]) * 40.0)
        for community_id, coords in community_centers.items()
    }

    node_positions: dict[str, tuple[float, float]] = {}

    # Push community bubbles apart until they no longer overlap.
    community_center_map = {int(key): [value[0], value[1]] for key, value in community_centers.items()}
    min_gap = 10.0
    for _ in range(240):
        moved = False
        for index, left_id in enumerate(community_ids):
            for right_id in community_ids[index + 1 :]:
                left_center = community_center_map[left_id]
                right_center = community_center_map[right_id]
                dx = right_center[0] - left_center[0]
                dy = right_center[1] - left_center[1]
                distance = math.hypot(dx, dy)
                target_distance = community_radii[left_id] + community_radii[right_id] + min_gap

                if distance == 0:
                    dx, dy = 1.0, 0.0
                    distance = 1.0

                if distance < target_distance:
                    overlap = (target_distance - distance) / 2.0
                    ux = dx / distance
                    uy = dy / distance
                    left_center[0] -= ux * overlap
                    left_center[1] -= uy * overlap
                    right_center[0] += ux * overlap
                    right_center[1] += uy * overlap
                    moved = True
        if not moved:
            break

    community_centers = {community_id: (coords[0], coords[1]) for community_id, coords in community_center_map.items()}

    for row in selected_stats.itertuples(index=False):
        community_id = int(row.community_id)
        center_x, center_y = community_centers[community_id]
        community_nodes = [
            node for node, data in display_graph.nodes(data=True) if int(data.get("community", 0)) == community_id
        ]
        community_subgraph = display_graph.subgraph(community_nodes).copy()
        radius = community_radii[community_id]

        if len(community_nodes) == 1:
            local_positions = {community_nodes[0]: (0.0, 0.0)}
        else:
            local_positions = nx.spring_layout(
                community_subgraph,
                seed=community_id + 10,
                weight="weight",
                k=max(0.35, 2.4 / max(math.sqrt(len(community_nodes)), 1)),
            )

        scale = radius * 0.8
        for node, (x_value, y_value) in local_positions.items():
            node_positions[node] = (center_x + x_value * scale, center_y + y_value * scale)

    return node_positions, community_centers, community_radii


def render_figure(
    graph: nx.Graph,
    display_graph: nx.Graph,
    selected_stats: pd.DataFrame,
    community_graph: nx.Graph,
    audit: dict,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    positions, community_centers, community_radii = compute_positions(display_graph, selected_stats, community_graph)
    color_map = {
        int(community_id): COMMUNITY_COLORS[index % len(COMMUNITY_COLORS)]
        for index, community_id in enumerate(selected_stats["community_id"].astype(int).tolist())
    }

    fig, ax = plt.subplots(figsize=(24, 18), dpi=180)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    selected_community_ids = set(selected_stats["community_id"].astype(int).tolist())
    meta_subgraph = community_graph.subgraph(selected_community_ids).copy()
    for left_c, right_c, data in meta_subgraph.edges(data=True):
        x1, y1 = community_centers[int(left_c)]
        x2, y2 = community_centers[int(right_c)]
        width = min(1.4 + math.log1p(data.get("weight", 1)) * 0.65, 5.0)
        ax.plot([x1, x2], [y1, y2], color="#93c5fd", alpha=0.45, linewidth=width, zorder=1)

    for row in selected_stats.itertuples(index=False):
        community_id = int(row.community_id)
        center_x, center_y = community_centers[community_id]
        radius = community_radii[community_id]
        color = color_map[community_id]

        circle = Circle(
            (center_x, center_y),
            radius=radius,
            facecolor=color,
            edgecolor=color,
            alpha=0.10,
            linewidth=2.0,
            zorder=2,
        )
        ax.add_patch(circle)
        outline = Circle(
            (center_x, center_y),
            radius=radius,
            facecolor="none",
            edgecolor=color,
            alpha=0.75,
            linewidth=2.0,
            zorder=3,
        )
        ax.add_patch(outline)

    internal_edges = [
        (left, right, data)
        for left, right, data in display_graph.edges(data=True)
        if int(display_graph.nodes[left].get("community", 0)) == int(display_graph.nodes[right].get("community", 0))
    ]
    if internal_edges:
        widths = [min(0.55 + 0.18 * data.get("weight", 1), 2.1) for _, _, data in internal_edges]
        nx.draw_networkx_edges(
            display_graph,
            positions,
            edgelist=[(left, right) for left, right, _ in internal_edges],
            width=widths,
            edge_color="#cbd5e1",
            alpha=0.18,
            ax=ax,
        )

    node_colors = [color_map[int(data.get("community", 0))] for _, data in display_graph.nodes(data=True)]
    node_sizes = [
        max(10.0, min(140.0, 11.0 + math.sqrt(float(data.get("weighted_degree", 0)) + 1) * 4.1))
        for _, data in display_graph.nodes(data=True)
    ]
    nx.draw_networkx_nodes(
        display_graph,
        positions,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.9,
        linewidths=0.2,
        edgecolors="#ffffff",
        ax=ax,
    )

    labels = {}
    for row in selected_stats.itertuples(index=False):
        community_id = int(row.community_id)
        center_actor = row.central_actor
        matching_node = None
        for node, data in display_graph.nodes(data=True):
            if int(data.get("community", 0)) == community_id and data.get("label") == center_actor:
                matching_node = node
                break
        if matching_node:
            labels[matching_node] = center_actor
    nx.draw_networkx_labels(display_graph, positions, labels=labels, font_size=8, font_weight="bold", font_color="#0f172a", ax=ax)

    for row in selected_stats.itertuples(index=False):
        community_id = int(row.community_id)
        center_x, center_y = community_centers[community_id]
        radius = community_radii[community_id]
        ax.text(
            center_x,
            center_y + radius + 1.8,
            (
                f"Communaute {community_id}\n"
                f"{row.actor_count} acteurs | {row.edge_count} liens\n"
                f"Genre: {row.dominant_genres}"
            ),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#0f172a",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "#ffffff", "edgecolor": "#cbd5e1", "alpha": 0.88},
            zorder=5,
        )

    info = (
        f"Analyse de communautes - backend IMDb\n"
        f"- source backend: {int(audit.get('principals_rows_read', 0)):,} lignes title.principals.tsv\n"
        f"- titres retenus pour le graphe: {TITLE_LIMIT:,}\n"
        f"- graphe complet: {graph.number_of_nodes():,} acteurs / {graph.number_of_edges():,} liens\n"
        f"- communautes detectees: {selected_stats.shape[0]:,} principales affichees / "
        f"{int(nx.number_connected_components(graph)):,} composantes connexes\n"
        f"- vue dessinee: {display_graph.number_of_nodes():,} acteurs"
    )
    ax.text(
        0.015,
        0.985,
        info,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        color="#0f172a",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#cbd5e1", "alpha": 0.96},
    )

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=color_map[int(row.community_id)], markersize=10, label=f"Communaute {int(row.community_id)}")
        for row in selected_stats.itertuples(index=False)
    ]
    ax.legend(handles=legend_handles, title="Communautes majeures", loc="upper right", frameon=False, fontsize=9, title_fontsize=10)

    ax.set_title(
        "Vue NetworkX par blocs de communautes\n"
        "Chaque bulle represente une communaute importante ; les points sont les acteurs les plus centraux de cette communaute.",
        fontsize=18,
        fontweight="bold",
        color="#0f172a",
        pad=20,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_analysis(
    graph: nx.Graph,
    selected_stats: pd.DataFrame,
    community_graph: nx.Graph,
) -> None:
    payload = selected_stats.copy()
    payload.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    OUTPUT_JSON.write_text(payload.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")

    top_community = selected_stats.iloc[0]
    densest_community = selected_stats.sort_values("density", ascending=False).iloc[0]
    strongest_bridge = None
    if community_graph.number_of_edges() > 0:
        left_c, right_c, data = max(community_graph.edges(data=True), key=lambda item: item[2].get("weight", 0))
        strongest_bridge = {
            "left": int(left_c),
            "right": int(right_c),
            "weight": int(data.get("weight", 0)),
            "sample_titles": ", ".join(data.get("titles", [])[:8]),
        }

    lines = [
        "# Analyse automatique des communautés IMDb",
        "",
        "## Paramètres utilisés",
        f"- Lignes backend sources : 300000 lignes de `title.principals.tsv` via le cache existant.",
        f"- Titres retenus pour construire le graphe : {TITLE_LIMIT}.",
        f"- Limite d'acteurs par titre : {MAX_ACTORS_PER_TITLE}.",
        f"- Communautés affichées : {TOP_COMMUNITIES} communautés les plus importantes.",
        f"- Acteurs affichés par communauté : jusqu'à {MAX_ACTORS_PER_COMMUNITY}.",
        "",
        "## Lecture générale",
        f"- Graphe acteur complet construit : {graph.number_of_nodes():,} acteurs et {graph.number_of_edges():,} liens.",
        f"- Les communautés ont été détectées avec une logique de modularité : les acteurs sont regroupés s'ils collaborent davantage entre eux qu'avec le reste du graphe.",
        f"- La communauté la plus importante dans cette vue est la communauté {int(top_community['community_id'])}, avec {int(top_community['actor_count'])} acteurs et {int(top_community['internal_weight'])} collaborations pondérées internes.",
        f"- La communauté la plus dense est la communauté {int(densest_community['community_id'])}, avec une densité de {float(densest_community['density']):.4f}.",
    ]
    if strongest_bridge:
        lines.extend(
            [
                f"- Le lien inter-communautés le plus fort relie les communautés {strongest_bridge['left']} et {strongest_bridge['right']} avec un poids agrégé de {strongest_bridge['weight']}.",
                f"- Exemples de titres associés à ce pont : {strongest_bridge['sample_titles']}.",
            ]
        )
    lines.extend(
        [
            "",
            "## Analyse des communautés majeures",
        ]
    )

    for row in selected_stats.itertuples(index=False):
        lines.extend(
            [
                f"### Communauté {int(row.community_id)}",
                f"- Taille : {int(row.actor_count)} acteurs.",
                f"- Liens internes : {int(row.edge_count)} arêtes, pour un poids interne total de {int(row.internal_weight)}.",
                f"- Densité : {float(row.density):.4f}.",
                f"- Titres distincts associés : {int(row.title_count)}.",
                f"- Genres dominants : {row.dominant_genres}.",
                f"- Acteur central : {row.central_actor} (degré pondéré {int(row.central_actor_weighted_degree)}).",
                f"- Acteur passerelle principal : {row.bridge_actor} (poids externe {int(row.bridge_external_weight)}).",
                "",
            ]
        )

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frame, audit = load_cached_backend()
    title_ids = select_top_titles(frame, TITLE_LIMIT)
    graph_source = frame[frame["tconst"].isin(title_ids)].copy()
    actor_rows = graph_source[graph_source["category"].isin(ACTOR_CATEGORIES)].copy()

    graph = build_actor_graph(graph_source)
    detect_communities(graph)
    community_stats, community_graph = compute_community_stats(graph, actor_rows)

    top_community_ids = community_stats.head(TOP_COMMUNITIES)["community_id"].astype(int).tolist()
    selected_stats = community_stats[community_stats["community_id"].isin(top_community_ids)].copy()
    selected_stats = selected_stats.sort_values(["importance_score", "actor_count"], ascending=False).reset_index(drop=True)

    display_graph = build_display_subgraph(graph, top_community_ids)
    render_figure(graph, display_graph, selected_stats, community_graph, audit)
    write_analysis(graph, selected_stats, community_graph)

    print(f"Image générée : {OUTPUT_PNG}")
    print(f"Stats JSON : {OUTPUT_JSON}")
    print(f"Stats CSV : {OUTPUT_CSV}")
    print(f"Analyse Markdown : {OUTPUT_MD}")
    print(f"Communautés affichées : {len(top_community_ids)}")
    print(f"Acteurs affichés : {display_graph.number_of_nodes():,}")


if __name__ == "__main__":
    main()
