from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import hashlib

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
OUTPUT_PNG = OUTPUT_DIR / "backend_community_bubbles_all_actors.png"
OUTPUT_JSON = OUTPUT_DIR / "backend_community_bubbles_all_actors_stats.json"
OUTPUT_MD = OUTPUT_DIR / "backend_community_bubbles_all_actors_analysis.md"

MAX_ACTORS_PER_TITLE = 10
TOP_COMMUNITIES = 18
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
    "#0284c7",
    "#84cc16",
    "#f59e0b",
    "#14b8a6",
    "#8b5cf6",
    "#ef4444",
]


def stable_float(text: str, salt: str = "") -> float:
    digest = hashlib.md5(f"{salt}:{text}".encode("utf-8")).hexdigest()[:12]
    return int(digest, 16) / float(16**12 - 1)


def load_cached_backend() -> tuple[pd.DataFrame, dict]:
    frame, audit = pd.read_pickle(CACHE_PATH)
    return frame.copy(), dict(audit)


def build_actor_graph(frame: pd.DataFrame) -> nx.Graph:
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    graph = nx.Graph()

    actor_projects = actor_rows.groupby("nconst")["tconst"].nunique().to_dict()
    actor_names = actor_rows.groupby("nconst")["primaryName"].first().to_dict()
    actor_genres = (
        actor_rows[["nconst", "genresList"]]
        .explode("genresList")
        .dropna(subset=["genresList"])
        .query("genresList != 'Unknown'")
        .groupby("nconst")["genresList"]
        .apply(list)
        .to_dict()
    )

    for actor_id, label in actor_names.items():
        genres = actor_genres.get(actor_id, [])
        dominant_genre = Counter(genres).most_common(1)[0][0] if genres else "Unknown"
        graph.add_node(
            actor_id,
            label=label,
            projects=int(actor_projects.get(actor_id, 0)),
            mainGenre=dominant_genre,
        )

    for _, group in actor_rows.groupby("tconst"):
        actors = group[["nconst"]].drop_duplicates("nconst")
        if len(actors) < 2:
            continue
        if len(actors) > MAX_ACTORS_PER_TITLE:
            actors = actors.head(MAX_ACTORS_PER_TITLE)
        for left, right in combinations(actors["nconst"].tolist(), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
            else:
                graph.add_edge(left, right, weight=1)

    graph.remove_nodes_from(list(nx.isolates(graph)))
    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))
    nx.set_node_attributes(graph, degree_map, "degree")
    nx.set_node_attributes(graph, weighted_degree_map, "weighted_degree")
    return graph


def detect_communities(graph: nx.Graph) -> dict[str, int]:
    if hasattr(nx.algorithms.community, "louvain_communities"):
        communities = nx.algorithms.community.louvain_communities(graph, weight="weight", seed=42)
    else:
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


def community_tables(graph: nx.Graph, actor_rows: pd.DataFrame) -> tuple[pd.DataFrame, nx.Graph]:
    community_map = nx.get_node_attributes(graph, "community")
    rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())].copy()
    rows["community"] = rows["nconst"].map(community_map)

    grouped_actor_ids: dict[int, list[str]] = defaultdict(list)
    for node, community_id in community_map.items():
        grouped_actor_ids[int(community_id)].append(node)

    weighted_degree_map = dict(graph.degree(weight="weight"))
    records: list[dict[str, object]] = []
    meta_graph = nx.Graph()

    for community_id, actor_ids in grouped_actor_ids.items():
        subgraph = graph.subgraph(actor_ids).copy()
        community_rows = rows[rows["community"] == community_id].copy()
        top_actor_id = max(actor_ids, key=lambda actor_id: weighted_degree_map.get(actor_id, 0))
        records.append(
            {
                "community_id": int(community_id),
                "actor_count": int(len(actor_ids)),
                "edge_count": int(subgraph.number_of_edges()),
                "internal_weight": int(sum(data.get("weight", 1) for _, _, data in subgraph.edges(data=True))),
                "density": float(nx.density(subgraph)) if subgraph.number_of_nodes() > 1 else 0.0,
                "title_count": int(community_rows["tconst"].nunique()),
                "dominant_genres": top_genres_text(community_rows["genresList"], limit=3),
                "central_actor": graph.nodes[top_actor_id].get("label", top_actor_id),
                "central_actor_weighted_degree": int(weighted_degree_map.get(top_actor_id, 0)),
            }
        )

    for left, right, data in graph.edges(data=True):
        left_c = int(community_map.get(left, 0))
        right_c = int(community_map.get(right, 0))
        if left_c == right_c:
            continue
        if meta_graph.has_edge(left_c, right_c):
            meta_graph[left_c][right_c]["weight"] += int(data.get("weight", 1))
        else:
            meta_graph.add_edge(left_c, right_c, weight=int(data.get("weight", 1)))

    stats = pd.DataFrame(records)
    stats["importance_score"] = (
        stats["actor_count"] * 5
        + stats["internal_weight"] * 0.12
        + stats["edge_count"] * 0.04
        + stats["density"] * 100
    )
    stats = stats.sort_values(["importance_score", "actor_count", "internal_weight"], ascending=False).reset_index(drop=True)
    return stats, meta_graph


def assign_display_groups(stats: pd.DataFrame) -> dict[int, str]:
    top_ids = stats.head(TOP_COMMUNITIES)["community_id"].astype(int).tolist()
    group_map: dict[int, str] = {}
    for community_id in stats["community_id"].astype(int).tolist():
        if community_id in top_ids:
            group_map[community_id] = f"Communaute {community_id}"
        else:
            group_map[community_id] = "Autres communautes"
    return group_map


def build_display_positions(graph: nx.Graph, stats: pd.DataFrame, meta_graph: nx.Graph) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]], dict[str, float], list[str]]:
    community_map = nx.get_node_attributes(graph, "community")
    display_group_map = assign_display_groups(stats)
    top_stats = stats.head(TOP_COMMUNITIES).copy()
    display_groups = top_stats["community_id"].astype(int).map(lambda value: f"Communaute {value}").tolist()
    display_groups.append("Autres communautes")

    group_actor_counts: dict[str, int] = defaultdict(int)
    for node in graph.nodes():
        group_name = display_group_map.get(int(community_map.get(node, 0)), "Autres communautes")
        group_actor_counts[group_name] += 1

    group_radii = {
        group_name: 10.0 + math.sqrt(max(count, 1)) * 1.2
        for group_name, count in group_actor_counts.items()
    }

    top_ids = top_stats["community_id"].astype(int).tolist()
    top_meta = meta_graph.subgraph(top_ids).copy()
    top_meta.add_nodes_from(top_ids)
    if top_meta.number_of_edges() > 0:
        base_positions = nx.spring_layout(top_meta, seed=42, weight="weight", k=3.2)
    else:
        base_positions = {community_id: (math.cos(index), math.sin(index)) for index, community_id in enumerate(top_ids)}

    group_centers: dict[str, list[float]] = {
        f"Communaute {community_id}": [float(coords[0]) * 55.0, float(coords[1]) * 55.0]
        for community_id, coords in base_positions.items()
    }
    group_centers.setdefault("Autres communautes", [0.0, -75.0])

    ordered_groups = [f"Communaute {value}" for value in top_ids] + ["Autres communautes"]
    min_gap = 18.0
    for _ in range(320):
        moved = False
        for index, left_group in enumerate(ordered_groups):
            for right_group in ordered_groups[index + 1 :]:
                left_center = group_centers[left_group]
                right_center = group_centers[right_group]
                dx = right_center[0] - left_center[0]
                dy = right_center[1] - left_center[1]
                distance = math.hypot(dx, dy)
                target = group_radii[left_group] + group_radii[right_group] + min_gap
                if distance == 0:
                    dx, dy = 1.0, 0.0
                    distance = 1.0
                if distance < target:
                    overlap = (target - distance) / 2.0
                    ux = dx / distance
                    uy = dy / distance
                    left_center[0] -= ux * overlap
                    left_center[1] -= uy * overlap
                    right_center[0] += ux * overlap
                    right_center[1] += uy * overlap
                    moved = True
        if not moved:
            break

    positions: dict[str, tuple[float, float]] = {}
    grouped_nodes: dict[str, list[str]] = defaultdict(list)
    for node, data in graph.nodes(data=True):
        group_name = display_group_map.get(int(data.get("community", 0)), "Autres communautes")
        grouped_nodes[group_name].append(node)

    for group_name, nodes in grouped_nodes.items():
        nodes = sorted(nodes, key=lambda node_id: graph.nodes[node_id].get("weighted_degree", 0), reverse=True)
        center_x, center_y = group_centers[group_name]
        radius = group_radii[group_name]
        for rank, node_id in enumerate(nodes):
            ring = int(math.sqrt(rank))
            ring_radius = min(radius * 0.88, ring * 0.9)
            angle = (rank * 0.61803398875 * 2 * math.pi) % (2 * math.pi)
            jitter_x = (stable_float(node_id, "x") - 0.5) * 0.55
            jitter_y = (stable_float(node_id, "y") - 0.5) * 0.55
            x_value = center_x + math.cos(angle) * ring_radius + jitter_x
            y_value = center_y + math.sin(angle) * ring_radius + jitter_y
            positions[node_id] = (x_value, y_value)

    group_centers_final = {group: (coords[0], coords[1]) for group, coords in group_centers.items()}
    return positions, group_centers_final, group_radii, ordered_groups


def render_image(graph: nx.Graph, stats: pd.DataFrame, meta_graph: nx.Graph, audit: dict) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    positions, centers, radii, ordered_groups = build_display_positions(graph, stats, meta_graph)
    display_group_map = assign_display_groups(stats)
    community_map = nx.get_node_attributes(graph, "community")

    top_ids = stats.head(TOP_COMMUNITIES)["community_id"].astype(int).tolist()
    group_colors = {f"Communaute {community_id}": COMMUNITY_COLORS[index % len(COMMUNITY_COLORS)] for index, community_id in enumerate(top_ids)}
    group_colors["Autres communautes"] = "#94a3b8"

    fig, ax = plt.subplots(figsize=(26, 20), dpi=180)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    top_meta = meta_graph.subgraph(top_ids).copy()
    for left_c, right_c, data in top_meta.edges(data=True):
        left_group = f"Communaute {int(left_c)}"
        right_group = f"Communaute {int(right_c)}"
        x1, y1 = centers[left_group]
        x2, y2 = centers[right_group]
        width = min(1.0 + math.log1p(float(data.get("weight", 1))) * 0.45, 4.5)
        ax.plot([x1, x2], [y1, y2], color="#93c5fd", alpha=0.35, linewidth=width, zorder=1)

    for group_name in ordered_groups:
        center_x, center_y = centers[group_name]
        radius = radii[group_name]
        color = group_colors[group_name]
        ax.add_patch(Circle((center_x, center_y), radius=radius, facecolor=color, edgecolor=color, alpha=0.08, linewidth=2.0, zorder=2))
        ax.add_patch(Circle((center_x, center_y), radius=radius, facecolor="none", edgecolor=color, alpha=0.75, linewidth=2.0, zorder=3))

    node_colors = []
    node_sizes = []
    for node, data in graph.nodes(data=True):
        group_name = display_group_map.get(int(data.get("community", 0)), "Autres communautes")
        node_colors.append(group_colors[group_name])
        if group_name == "Autres communautes":
            node_sizes.append(5.0)
        else:
            node_sizes.append(max(6.0, min(36.0, 6.0 + math.sqrt(float(data.get("weighted_degree", 0)) + 1) * 1.05)))

    nx.draw_networkx_nodes(
        graph,
        positions,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.82,
        linewidths=0.0,
        ax=ax,
    )

    for row in stats.head(TOP_COMMUNITIES).itertuples(index=False):
        group_name = f"Communaute {int(row.community_id)}"
        center_x, center_y = centers[group_name]
        radius = radii[group_name]
        ax.text(
            center_x,
            center_y + radius + 2.2,
            f"{group_name}\n{int(row.actor_count)} acteurs\nGenre: {row.dominant_genres}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#0f172a",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "#ffffff", "edgecolor": "#cbd5e1", "alpha": 0.9},
            zorder=5,
        )

    other_count = sum(1 for _, data in graph.nodes(data=True) if display_group_map.get(int(data.get("community", 0)), "Autres communautes") == "Autres communautes")
    if other_count:
        center_x, center_y = centers["Autres communautes"]
        radius = radii["Autres communautes"]
        ax.text(
            center_x,
            center_y + radius + 2.2,
            f"Autres communautes\n{other_count} acteurs",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#0f172a",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "#ffffff", "edgecolor": "#cbd5e1", "alpha": 0.9},
            zorder=5,
        )

    top_labels = {}
    top_community_lookup = set(top_ids)
    for row in stats.head(TOP_COMMUNITIES).itertuples(index=False):
        community_id = int(row.community_id)
        central_name = row.central_actor
        for node, data in graph.nodes(data=True):
            if int(data.get("community", 0)) == community_id and data.get("label") == central_name:
                top_labels[node] = central_name
                break
    nx.draw_networkx_labels(graph, positions, labels=top_labels, font_size=7, font_weight="bold", font_color="#111827", ax=ax)

    info_text = (
        f"Vue globale backend - tous les acteurs disponibles dans le cache\n"
        f"- source backend : {int(audit.get('principals_rows_read', 0)):,} lignes title.principals.tsv\n"
        f"- acteurs uniques analyses : {graph.number_of_nodes():,}\n"
        f"- liens acteur-acteur : {graph.number_of_edges():,}\n"
        f"- communautes detectees : {int(stats.shape[0]):,}\n"
        f"- image : top {TOP_COMMUNITIES} communautes detaillees + autres communautes regroupees\n"
        f"- tous les points representent des acteurs"
    )
    ax.text(
        0.015,
        0.985,
        info_text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        color="#0f172a",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#ffffff", "edgecolor": "#cbd5e1", "alpha": 0.96},
    )

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=group_colors[group_name], markersize=9, label=group_name)
        for group_name in ordered_groups[: min(len(ordered_groups), 10)]
    ]
    ax.legend(handles=legend_handles, title="Communautes / groupes", loc="upper right", frameon=False, fontsize=9, title_fontsize=10)
    ax.set_title(
        "Vue globale des ~31 000 acteurs du backend IMDb\n"
        "Les grandes communautes sont separees ; les petites sont regroupees dans un ensemble 'Autres communautes'.",
        fontsize=18,
        fontweight="bold",
        color="#0f172a",
        pad=20,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    stats_payload = {
        "source_rows_read": int(audit.get("principals_rows_read", 0)),
        "actors_analyzed": int(graph.number_of_nodes()),
        "edges_analyzed": int(graph.number_of_edges()),
        "communities_detected": int(stats.shape[0]),
        "top_communities_detailed": TOP_COMMUNITIES,
        "others_grouped_actor_count": other_count,
    }
    OUTPUT_JSON.write_text(json.dumps(stats_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats_payload


def write_analysis(stats: pd.DataFrame, payload: dict[str, object]) -> None:
    top = stats.head(TOP_COMMUNITIES)
    lines = [
        "# Vue globale des 31 030 acteurs environ",
        "",
        "## Paramètres",
        f"- Acteurs analysés : {payload['actors_analyzed']:,}.",
        f"- Liens analysés : {payload['edges_analyzed']:,}.",
        f"- Communautés détectées : {payload['communities_detected']:,}.",
        f"- Communautés détaillées séparément : {payload['top_communities_detailed']}.",
        f"- Acteurs regroupés dans 'Autres communautés' : {payload['others_grouped_actor_count']:,}.",
        "",
        "## Lecture",
        "- Tous les points de l'image représentent des acteurs.",
        "- Les bulles principales correspondent aux plus grandes communautés détectées sur le graphe acteur-acteur.",
        "- Les petites communautés sont regroupées visuellement pour éviter une image illisible.",
        "- La position des bulles dépend des relations entre communautés, puis d'un espacement artificiel pour qu'elles ne se chevauchent pas.",
        "",
        "## Principales communautés",
    ]
    for row in top.itertuples(index=False):
        lines.extend(
            [
                f"### Communauté {int(row.community_id)}",
                f"- Taille : {int(row.actor_count)} acteurs.",
                f"- Liens internes : {int(row.edge_count)}.",
                f"- Poids interne : {int(row.internal_weight)}.",
                f"- Densité : {float(row.density):.4f}.",
                f"- Titres associés : {int(row.title_count)}.",
                f"- Genres dominants : {row.dominant_genres}.",
                f"- Acteur central : {row.central_actor}.",
                "",
            ]
        )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frame, audit = load_cached_backend()
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    graph = build_actor_graph(frame)
    detect_communities(graph)
    stats, meta_graph = community_tables(graph, actor_rows)
    payload = render_image(graph, stats, meta_graph, audit)
    write_analysis(stats, payload)
    print(f"Image générée : {OUTPUT_PNG}")
    print(f"Analyse : {OUTPUT_MD}")
    print(f"Statistiques : {OUTPUT_JSON}")
    print(f"Acteurs analysés : {graph.number_of_nodes():,}")
    print(f"Communautés détectées : {stats.shape[0]:,}")


if __name__ == "__main__":
    main()
