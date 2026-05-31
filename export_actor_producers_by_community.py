from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from export_backend_community_bubbles_all_actors import (
    ACTOR_CATEGORIES,
    build_actor_graph,
    detect_communities,
    load_cached_backend,
)


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_CSV = OUTPUT_DIR / "actor_producers_by_community.csv"
OUTPUT_JSON = OUTPUT_DIR / "actor_producers_by_community.json"
OUTPUT_MD = OUTPUT_DIR / "actor_producers_by_community.md"


def is_producer_profile(group: pd.DataFrame) -> bool:
    categories = set(group["category"].dropna().astype(str).tolist())
    if "producer" in categories:
        return True
    profession_text = ",".join(group["primaryProfession"].dropna().astype(str).tolist()).lower()
    return "producer" in profession_text


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame, _ = load_cached_backend()
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    actor_graph = build_actor_graph(frame)
    detect_communities(actor_graph)
    community_map = {node: int(data.get("community", 0)) for node, data in actor_graph.nodes(data=True)}

    full_person_groups = frame.groupby("nconst")
    producer_actor_ids = [
        actor_id
        for actor_id in actor_graph.nodes()
        if actor_id in full_person_groups.groups and is_producer_profile(frame.loc[full_person_groups.groups[actor_id]])
    ]

    weighted_degree = dict(actor_graph.degree(weight="weight"))
    degree_map = dict(actor_graph.degree())
    rows: list[dict[str, object]] = []

    for actor_id in producer_actor_ids:
        person_group = frame[frame["nconst"] == actor_id].copy()
        actor_titles = actor_rows[actor_rows["nconst"] == actor_id].copy()
        community_id = community_map.get(actor_id, 0)
        titles_for_community = actor_rows[
            actor_rows["nconst"].isin([node for node, comm in community_map.items() if comm == community_id])
        ].copy()
        top_title = (
            titles_for_community[["titleLabel", "numVotes", "averageRating"]]
            .drop_duplicates("titleLabel")
            .sort_values(["numVotes", "averageRating", "titleLabel"], ascending=[False, False, True])
            .head(1)
        )
        rows.append(
            {
                "community_id": int(community_id),
                "actor_id": actor_id,
                "actor_name": actor_graph.nodes[actor_id].get("label", actor_id),
                "weighted_degree": int(weighted_degree.get(actor_id, 0)),
                "degree": int(degree_map.get(actor_id, 0)),
                "actor_projects": int(actor_graph.nodes[actor_id].get("projects", 0)),
                "producer_titles_count": int(person_group[person_group["category"] == "producer"]["tconst"].nunique()),
                "all_roles": ", ".join(sorted(set(person_group["category"].dropna().astype(str)))),
                "community_top_title_by_votes": top_title["titleLabel"].iloc[0] if not top_title.empty else "n/a",
                "community_top_title_votes": int(top_title["numVotes"].iloc[0]) if not top_title.empty else 0,
                "community_top_title_rating": float(top_title["averageRating"].iloc[0]) if not top_title.empty else 0.0,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        OUTPUT_JSON.write_text("[]", encoding="utf-8")
        OUTPUT_MD.write_text("# Aucun acteur-producteur détecté\n", encoding="utf-8")
        return

    result = result.sort_values(
        ["community_id", "weighted_degree", "producer_titles_count", "actor_projects", "actor_name"],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)
    result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    result.to_json(OUTPUT_JSON, orient="records", force_ascii=False, indent=2)

    community_counts = result.groupby("community_id")["actor_id"].nunique().to_dict()
    lines = [
        "# Acteurs qui sont aussi producteurs",
        "",
        "Important : les fichiers IMDb Open Data locaux n'incluent pas le budget de production.",
        "La colonne budget n'existe pas dans `title.basics.tsv`, `title.ratings.tsv`, `title.principals.tsv`, `title.crew.tsv` ou `name.basics.tsv`.",
        "Dans cette analyse, on peut donc identifier les acteurs qui ont aussi un role de producteur, mais le 'film au plus gros budget' n'est pas calculable sans autre source externe.",
        "",
        "Pour remplacer cela dans le projet, on utilise un proxy IMDb :",
        "- le titre le plus vote de la communaute",
        "- et sa note moyenne",
        "",
        "## Nombre d'acteurs-producteurs par communaute",
    ]
    for community_id, count in sorted(community_counts.items(), key=lambda item: item[1], reverse=True)[:20]:
        subset = result[result["community_id"] == community_id].head(5)
        names = ", ".join(subset["actor_name"].tolist())
        lines.append(f"- Communaute {int(community_id)} : {int(count)} acteurs-producteurs. Exemples : {names}.")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"CSV={OUTPUT_CSV}")
    print(f"JSON={OUTPUT_JSON}")
    print(f"MD={OUTPUT_MD}")
    print(f"ACTOR_PRODUCERS={result['actor_id'].nunique()}")


if __name__ == "__main__":
    main()
