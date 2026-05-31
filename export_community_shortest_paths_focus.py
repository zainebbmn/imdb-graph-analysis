from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import networkx as nx

from export_backend_community_bubbles_all_actors import (
    ACTOR_CATEGORIES,
    COMMUNITY_COLORS,
    build_actor_graph,
    community_tables,
    detect_communities,
    load_cached_backend,
)


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_PNG = OUTPUT_DIR / "community_shortest_paths_focus.png"
OUTPUT_JSON = OUTPUT_DIR / "community_shortest_paths_focus.json"
OUTPUT_MD = OUTPUT_DIR / "community_shortest_paths_focus.md"

TOP_COMMUNITIES = 12


def build_meta_graph(actor_graph: nx.Graph) -> nx.Graph:
    community_map = nx.get_node_attributes(actor_graph, "community")
    meta_graph = nx.Graph()
    for left, right, data in actor_graph.edges(data=True):
        left_c = int(community_map.get(left, 0))
        right_c = int(community_map.get(right, 0))
        if left_c == 0 or right_c == 0 or left_c == right_c:
            continue
        weight = float(data.get("weight", 1))
        if meta_graph.has_edge(left_c, right_c):
            meta_graph[left_c][right_c]["weight"] += weight
        else:
            meta_graph.add_edge(left_c, right_c, weight=weight)

    for left_c, right_c, data in meta_graph.edges(data=True):
        data["distance"] = 1.0 / max(float(data.get("weight", 1.0)), 1.0)
    return meta_graph


def compute_positions(top_stats, meta_graph: nx.Graph) -> tuple[dict[int, tuple[float, float]], dict[int, float]]:
    top_ids = top_stats["community_id"].astype(int).tolist()
    subgraph = meta_graph.subgraph(top_ids).copy()
    subgraph.add_nodes_from(top_ids)
    if subgraph.number_of_edges() > 0:
        positions = nx.spring_layout(subgraph, seed=42, weight="weight", k=2.8)
    else:
        positions = {community_id: (math.cos(index), math.sin(index)) for index, community_id in enumerate(top_ids)}

    positions = {int(node): (float(x) * 35.0, float(y) * 35.0) for node, (x, y) in positions.items()}
    radii = {
        int(row.community_id): 4.5 + math.sqrt(max(int(row.actor_count), 1)) * 0.35
        for row in top_stats.itertuples(index=False)
    }

    mutable_positions = {node: [coords[0], coords[1]] for node, coords in positions.items()}
    ordered = top_ids[:]
    min_gap = 10.0
    for _ in range(220):
        moved = False
        for index, left_id in enumerate(ordered):
            for right_id in ordered[index + 1 :]:
                left_center = mutable_positions[left_id]
                right_center = mutable_positions[right_id]
                dx = right_center[0] - left_center[0]
                dy = right_center[1] - left_center[1]
                distance = math.hypot(dx, dy)
                target = radii[left_id] + radii[right_id] + min_gap
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

    return {node: (coords[0], coords[1]) for node, coords in mutable_positions.items()}, radii


def build_shortest_path_summary(top_stats, meta_graph: nx.Graph) -> tuple[list[dict], int]:
    top_ids = top_stats["community_id"].astype(int).tolist()
    source_community = int(top_stats.iloc[0]["community_id"])
    summary_rows: list[dict] = []

    for target in top_ids:
        if target == source_community:
            continue
        if not nx.has_path(meta_graph, source_community, target):
            summary_rows.append(
                {
                    "source_community": source_community,
                    "target_community": int(target),
                    "hop_count": None,
                    "distance_total": None,
                    "path": "Aucun chemin",
                }
            )
            continue
        path = nx.shortest_path(meta_graph, source=source_community, target=target, weight="distance")
        distance_total = nx.shortest_path_length(meta_graph, source=source_community, target=target, weight="distance")
        summary_rows.append(
            {
                "source_community": source_community,
                "target_community": int(target),
                "hop_count": int(len(path) - 1),
                "distance_total": float(distance_total),
                "path": " -> ".join(f"C{int(value)}" for value in path),
            }
        )

    return summary_rows, source_community


def render_image(top_stats, meta_graph: nx.Graph, summary_rows: list[dict], source_community: int, total_communities: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    top_ids = top_stats["community_id"].astype(int).tolist()
    positions, radii = compute_positions(top_stats, meta_graph)
    color_map = {
        int(row.community_id): COMMUNITY_COLORS[index % len(COMMUNITY_COLORS)]
        for index, row in enumerate(top_stats.itertuples(index=False))
    }

    highlighted_edges: set[tuple[int, int]] = set()
    for row in summary_rows:
        path_text = row["path"]
        if not path_text or path_text == "Aucun chemin":
            continue
        ids = [int(part[1:]) for part in path_text.split(" -> ")]
        for left, right in zip(ids, ids[1:]):
            highlighted_edges.add(tuple(sorted((left, right))))

    fig, ax = plt.subplots(figsize=(22, 16), dpi=180)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    subgraph = meta_graph.subgraph(top_ids).copy()
    for left, right, data in subgraph.edges(data=True):
        x1, y1 = positions[int(left)]
        x2, y2 = positions[int(right)]
        pair = tuple(sorted((int(left), int(right))))
        highlighted = pair in highlighted_edges
        ax.plot(
            [x1, x2],
            [y1, y2],
            color="#2563eb" if highlighted else "#cbd5e1",
            alpha=0.75 if highlighted else 0.45,
            linewidth=min(1.0 + math.log1p(float(data.get("weight", 1))) * (0.38 if highlighted else 0.18), 4.8),
            zorder=1 if highlighted else 0,
        )

    for row in top_stats.itertuples(index=False):
        community_id = int(row.community_id)
        x_value, y_value = positions[community_id]
        radius = radii[community_id]
        color = color_map[community_id]
        is_source = community_id == source_community
        ax.add_patch(
            Circle(
                (x_value, y_value),
                radius=radius,
                facecolor=color,
                edgecolor="#0f172a" if is_source else color,
                linewidth=3.0 if is_source else 2.0,
                alpha=0.14,
                zorder=2,
            )
        )
        ax.add_patch(
            Circle(
                (x_value, y_value),
                radius=radius,
                facecolor="none",
                edgecolor="#0f172a" if is_source else color,
                linewidth=3.0 if is_source else 2.0,
                alpha=0.85,
                zorder=3,
            )
        )
        ax.scatter(
            [x_value],
            [y_value],
            s=max(80, min(700, row.actor_count * 0.08)),
            color=color,
            edgecolors="#ffffff",
            linewidths=1.2,
            zorder=4,
        )
        ax.text(
            x_value,
            y_value,
            f"C{community_id}",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="#0f172a",
            zorder=5,
        )
        ax.text(
            x_value,
            y_value - radius - 2.2,
            f"{int(row.actor_count)} acteurs\n{row.dominant_genres}",
            ha="center",
            va="top",
            fontsize=8.5,
            color="#0f172a",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "#ffffff", "edgecolor": "#cbd5e1", "alpha": 0.9},
            zorder=5,
        )

    info_text = (
        "Photo analytique - plus courts chemins entre communautes\n"
        f"- noeuds: top {TOP_COMMUNITIES} communautes par taille\n"
        f"- source mise en avant: C{source_community}\n"
        f"- communautes detectees au total: {total_communities:,}\n"
        "- un lien entre communautes existe si des acteurs des deux communautes sont relies\n"
        "- distance utilisee: 1 / poids du lien inter-communautes\n"
        "- en bleu fort: les liens utilises dans au moins un plus court chemin depuis la source"
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
        Line2D([0], [0], color="#2563eb", linewidth=3, label="Lien sur un plus court chemin"),
        Line2D([0], [0], color="#cbd5e1", linewidth=3, label="Autre lien inter-communautes"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", frameon=False, fontsize=10)
    ax.set_title(
        "Graphe des communautes et plus courts chemins\n"
        "Cette vue developpe l'image precedente en montrant comment les communautes se relient entre elles.",
        fontsize=18,
        fontweight="bold",
        color="#0f172a",
        pad=18,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(top_stats, summary_rows: list[dict], source_community: int) -> None:
    payload = {
        "source_community": source_community,
        "top_communities_considered": int(top_stats.shape[0]),
        "paths": summary_rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Plus courts chemins entre communautés",
        "",
        f"- Communauté source principale : C{source_community}.",
        f"- Nombre de communautés majeures considérées : {top_stats.shape[0]}.",
        "",
        "## Résultats",
    ]
    for row in summary_rows:
        if row["path"] == "Aucun chemin":
            lines.append(
                f"- C{row['source_community']} -> C{row['target_community']} : aucun chemin trouvé dans le graphe des communautés."
            )
        else:
            lines.append(
                f"- C{row['source_community']} -> C{row['target_community']} : chemin `{row['path']}`, "
                f"{row['hop_count']} saut(s), distance pondérée {row['distance_total']:.6f}."
            )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frame, _ = load_cached_backend()
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    actor_graph = build_actor_graph(frame)
    detect_communities(actor_graph)
    stats, _ = community_tables(actor_graph, actor_rows)
    meta_graph = build_meta_graph(actor_graph)

    top_stats = stats.head(TOP_COMMUNITIES).copy().reset_index(drop=True)
    summary_rows, source_community = build_shortest_path_summary(top_stats, meta_graph)
    render_image(top_stats, meta_graph, summary_rows, source_community, int(stats.shape[0]))
    write_outputs(top_stats, summary_rows, source_community)

    print(f"Image générée : {OUTPUT_PNG}")
    print(f"JSON : {OUTPUT_JSON}")
    print(f"Markdown : {OUTPUT_MD}")
    print(f"Communauté source : C{source_community}")


if __name__ == "__main__":
    main()
