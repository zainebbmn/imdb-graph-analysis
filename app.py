from collections import Counter, defaultdict
import html
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path

import folium
from folium.plugins import FastMarkerCluster, Fullscreen, HeatMap, MarkerCluster, MiniMap
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium


DATA_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = DATA_DIR / "outputs"
SAMPLE_PRINCIPALS_ROWS = 100_000
GRAPH_CATEGORIES = ["actor", "actress", "director", "writer", "producer"]
ACTOR_CATEGORIES = ["actor", "actress"]
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
]
LINK_COLORS = {
    "Titres communs": "#2563eb",
    "Genres communs": "#3b82f6",
    "Communautes partagees": "#1d4ed8",
}
REGION_COORDS = {
    "US": (39.8283, -98.5795),
    "GB": (54.7024, -3.2766),
    "FR": (46.6034, 1.8883),
    "DE": (51.1638, 10.4478),
    "ES": (39.3261, -4.8379),
    "IT": (42.6384, 12.6743),
    "DK": (56.2639, 9.5018),
    "SE": (59.6749, 14.5209),
    "NO": (60.4720, 8.4689),
    "FI": (63.2468, 25.9209),
    "NL": (52.2435, 5.6343),
    "BE": (50.6403, 4.6667),
    "CH": (46.8182, 8.2275),
    "AT": (47.5939, 14.1246),
    "IE": (52.8652, -7.9795),
    "PT": (39.3999, -8.2245),
    "PL": (52.2159, 19.1344),
    "CZ": (49.8175, 15.4730),
    "SK": (48.6690, 19.6990),
    "HU": (47.1625, 19.5033),
    "RO": (45.9432, 24.9668),
    "BG": (42.7339, 25.4858),
    "HR": (45.1000, 15.2000),
    "SI": (46.1512, 14.9955),
    "RS": (44.0165, 21.0059),
    "GR": (38.9954, 21.9877),
    "TR": (38.9637, 35.2433),
    "RU": (61.5240, 105.3188),
    "UA": (48.3794, 31.1656),
    "JP": (36.5748, 139.2394),
    "KR": (36.6384, 127.6961),
    "CN": (35.8617, 104.1954),
    "IN": (22.3511, 78.6677),
    "AU": (-25.2744, 133.7751),
    "NZ": (-40.9006, 174.8860),
    "CA": (56.1304, -106.3468),
    "MX": (23.6345, -102.5528),
    "BR": (-14.2350, -51.9253),
    "AR": (-38.4161, -63.6167),
    "CL": (-35.6751, -71.5430),
    "CO": (4.5709, -74.2973),
    "VE": (6.4238, -66.5897),
    "ZA": (-30.5595, 22.9375),
    "EG": (26.8206, 30.8025),
    "IL": (31.0461, 34.8516),
    "IR": (32.4279, 53.6880),
    "TH": (15.8700, 100.9925),
    "PH": (12.8797, 121.7740),
    "ID": (-0.7893, 113.9213),
    "MY": (4.2105, 101.9758),
    "SG": (1.3521, 103.8198),
    "XWW": (20.0000, 0.0000),
    "XEU": (54.5260, 15.2551),
    "XAS": (34.0479, 100.6197),
    "XSA": (-8.7832, -55.4915),
}
REGION_NAMES = {
    "US": "United States",
    "GB": "United Kingdom",
    "FR": "France",
    "DE": "Germany",
    "ES": "Spain",
    "IT": "Italy",
    "DK": "Denmark",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "NL": "Netherlands",
    "BE": "Belgium",
    "CH": "Switzerland",
    "AT": "Austria",
    "IE": "Ireland",
    "PT": "Portugal",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "SK": "Slovakia",
    "HU": "Hungary",
    "RO": "Romania",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "SI": "Slovenia",
    "RS": "Serbia",
    "GR": "Greece",
    "TR": "Turkey",
    "RU": "Russia",
    "UA": "Ukraine",
    "JP": "Japan",
    "KR": "South Korea",
    "CN": "China",
    "IN": "India",
    "AU": "Australia",
    "NZ": "New Zealand",
    "CA": "Canada",
    "MX": "Mexico",
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",
    "VE": "Venezuela",
    "ZA": "South Africa",
    "EG": "Egypt",
    "IL": "Israel",
    "IR": "Iran",
    "TH": "Thailand",
    "PH": "Philippines",
    "ID": "Indonesia",
    "MY": "Malaysia",
    "SG": "Singapore",
    "XWW": "Worldwide",
    "XEU": "Europe",
    "XAS": "Asia",
    "XSA": "South America",
}


st.set_page_config(page_title="IMDb Map Communities", layout="wide")

if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Clair"

theme_left_col, theme_right_col = st.columns([6, 1.4])
with theme_right_col:
    st.radio(
        "Theme",
        ["Clair", "Sombre"],
        horizontal=True,
        label_visibility="collapsed",
        key="theme_mode",
    )

theme_mode = st.session_state["theme_mode"]
if theme_mode == "Sombre":
    theme_vars = {
        "app_bg": "radial-gradient(circle at top left, rgba(14, 165, 233, 0.10), transparent 28%), radial-gradient(circle at top right, rgba(34, 197, 94, 0.08), transparent 24%), linear-gradient(180deg, #020617 0%, #0f172a 100%)",
        "sidebar_bg": "linear-gradient(180deg, #020617 0%, #0f172a 100%)",
        "sidebar_text": "#e2e8f0",
        "hero_bg": "rgba(15, 23, 42, 0.86)",
        "hero_text": "#f8fafc",
        "hero_border": "rgba(51, 65, 85, 0.6)",
        "hero_subtext": "#cbd5e1",
        "hero_kicker_bg": "#082f49",
        "hero_kicker_text": "#bae6fd",
        "hero_chip_bg": "#111827",
        "hero_chip_border": "rgba(71, 85, 105, 0.5)",
        "hero_chip_text": "#e2e8f0",
        "note_bg": "rgba(15, 23, 42, 0.76)",
        "note_border": "rgba(71, 85, 105, 0.5)",
        "note_text": "#cbd5e1",
        "radio_border": "rgba(71, 85, 105, 0.45)",
        "radio_text": "#cbd5e1",
        "radio_selected": "#38bdf8",
    }
else:
    theme_vars = {
        "app_bg": "radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 28%), radial-gradient(circle at top right, rgba(22, 163, 74, 0.10), transparent 24%), linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%)",
        "sidebar_bg": "linear-gradient(180deg, #0f172a 0%, #13263f 100%)",
        "sidebar_text": "#e2e8f0",
        "hero_bg": "rgba(255, 255, 255, 0.88)",
        "hero_text": "#0f172a",
        "hero_border": "rgba(148, 163, 184, 0.18)",
        "hero_subtext": "#334155",
        "hero_kicker_bg": "#e0f2fe",
        "hero_kicker_text": "#075985",
        "hero_chip_bg": "#f8fafc",
        "hero_chip_border": "rgba(148, 163, 184, 0.24)",
        "hero_chip_text": "#0f172a",
        "note_bg": "rgba(255, 255, 255, 0.82)",
        "note_border": "rgba(148, 163, 184, 0.2)",
        "note_text": "#334155",
        "radio_border": "rgba(148, 163, 184, 0.25)",
        "radio_text": "#334155",
        "radio_selected": "#ef4444",
    }

st.markdown(
    f"""
    <style>
    .stApp {{
        background: {theme_vars["app_bg"]};
    }}
    [data-testid="stSidebar"] {{
        background: {theme_vars["sidebar_bg"]};
    }}
    [data-testid="stSidebar"] * {{
        color: {theme_vars["sidebar_text"]};
    }}
    .hero {{
        background: {theme_vars["hero_bg"]};
        color: {theme_vars["hero_text"]};
        border: 1px solid {theme_vars["hero_border"]};
        border-radius: 24px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(10px);
    }}
    .hero-top {{
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
        flex-wrap: wrap;
    }}
    .hero-kicker {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        background: {theme_vars["hero_kicker_bg"]};
        color: {theme_vars["hero_kicker_text"]};
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.45rem;
    }}
    .hero h1 {{
        margin: 0;
        font-size: 1.75rem;
    }}
    .hero p {{
        margin: 0.35rem 0 0 0;
        line-height: 1.45;
        max-width: 58rem;
        color: {theme_vars["hero_subtext"]};
    }}
    .hero-actions {{
        display: flex;
        gap: 0.65rem;
        flex-wrap: wrap;
    }}
    .hero-chip {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.55rem 0.85rem;
        border-radius: 999px;
        background: {theme_vars["hero_chip_bg"]};
        border: 1px solid {theme_vars["hero_chip_border"]};
        font-size: 0.85rem;
        color: {theme_vars["hero_chip_text"]};
        font-weight: 600;
    }}
    .note {{
        background: {theme_vars["note_bg"]};
        border-radius: 16px;
        border: 1px solid {theme_vars["note_border"]};
        padding: 0.65rem 0.9rem;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.04);
        color: {theme_vars["note_text"]};
        font-size: 0.92rem;
    }}
    div[data-testid="stRadio"] > div {{
        gap: 1rem;
    }}
    div[data-testid="stRadio"] label {{
        padding-bottom: 0.5rem;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] {{
        gap: 1.4rem;
        border-bottom: 1px solid {theme_vars["radio_border"]};
        padding-bottom: 0.25rem;
        margin-bottom: 0.75rem;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label {{
        border-radius: 0;
        padding: 0.25rem 0 0.8rem 0;
        border-bottom: 3px solid transparent;
        color: {theme_vars["radio_text"]};
        font-weight: 500;
        background: transparent;
    }}
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-selected="true"] {{
        color: {theme_vars["radio_selected"]};
        border-bottom-color: {theme_vars["radio_selected"]};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def clean_text_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = frame[column].replace("\\N", pd.NA)
    return frame


def max_imdb_number(ids: list[str], prefix: str) -> int | None:
    values = [
        int(value[len(prefix):])
        for value in ids
        if isinstance(value, str) and value.startswith(prefix) and value[len(prefix):].isdigit()
    ]
    return max(values) if values else None


def load_lookup_subset(
    path: Path,
    key_column: str,
    wanted_ids: list[str],
    columns: list[str],
    chunk_size: int = 200_000,
) -> pd.DataFrame:
    if not wanted_ids:
        return pd.DataFrame(columns=columns)

    wanted = set(wanted_ids)
    remaining = set(wanted_ids)
    matches = []
    prefix = "tt" if key_column in {"tconst", "titleId"} else "nm" if key_column == "nconst" else ""
    max_needed = max_imdb_number(wanted_ids, prefix) if prefix else None

    for chunk in pd.read_csv(
        path,
        sep="\t",
        usecols=columns,
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    ):
        found = chunk[chunk[key_column].isin(wanted)]
        if not found.empty:
            matches.append(found)
            remaining -= set(found[key_column].dropna())
            if not remaining:
                break

        if max_needed is not None:
            numeric_keys = pd.to_numeric(chunk[key_column].str.replace(prefix, "", regex=False), errors="coerce")
            chunk_max = numeric_keys.max()
            if pd.notna(chunk_max) and int(chunk_max) > max_needed:
                break

    if not matches:
        return pd.DataFrame(columns=columns)

    return pd.concat(matches, ignore_index=True).drop_duplicates(subset=[key_column])


def load_region_subset(title_ids: list[str], chunk_size: int = 250_000) -> pd.DataFrame:
    if not title_ids:
        return pd.DataFrame(columns=["titleId", "region"])

    wanted = set(title_ids)
    max_needed = max_imdb_number(title_ids, "tt")
    matches = []

    for chunk in pd.read_csv(
        DATA_DIR / "title.akas.tsv",
        sep="\t",
        usecols=["titleId", "region"],
        dtype=str,
        chunksize=chunk_size,
        low_memory=False,
    ):
        subset = chunk[chunk["titleId"].isin(wanted)].copy()
        if not subset.empty:
            subset = subset[subset["region"].notna() & subset["region"].ne("\\N")]
            if not subset.empty:
                subset["priority"] = subset["region"].apply(lambda value: 0 if value in REGION_COORDS else 1)
                matches.append(subset)

        if max_needed is not None:
            numeric_keys = pd.to_numeric(chunk["titleId"].str.replace("tt", "", regex=False), errors="coerce")
            chunk_max = numeric_keys.max()
            if pd.notna(chunk_max) and int(chunk_max) > max_needed:
                break

    if not matches:
        return pd.DataFrame(columns=["titleId", "region"])

    regions = pd.concat(matches, ignore_index=True)
    regions = regions.sort_values(["titleId", "priority", "region"]).drop_duplicates(subset=["titleId"])
    return regions[["titleId", "region"]]


def region_name(region_code: str) -> str:
    return REGION_NAMES.get(region_code, region_code)


def jitter_coordinates(lat: float, lon: float, key: str, max_offset: float = 0.45) -> tuple[float, float]:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    angle = int(digest[:4], 16) % 360
    radius_seed = int(digest[4:8], 16) / 65535
    radius = 0.08 + radius_seed * max_offset
    lat_offset = math.sin(math.radians(angle)) * radius
    lon_offset = math.cos(math.radians(angle)) * radius
    return lat + lat_offset, lon + lon_offset


def join_list(values: list[str], limit: int = 6) -> str:
    cleaned = [value for value in values if value]
    return ", ".join(cleaned[:limit]) if cleaned else "n/a"


def scroll_list_html(values: list[str], empty_text: str = "n/a", max_height: int = 150) -> str:
    cleaned = [str(value) for value in values if value]
    if not cleaned:
        return empty_text
    items = "".join(f"<li>{html.escape(value)}</li>" for value in cleaned)
    return f"<div style='max-height:{max_height}px; overflow-y:auto; padding-left:0.4rem;'><ul>{items}</ul></div>"


def preview_list_html(values: list[str], limit: int, max_height: int = 110) -> str:
    cleaned = [str(value) for value in values if value]
    if not cleaned:
        return "n/a"
    preview = cleaned[:limit]
    suffix = ""
    if len(cleaned) > limit:
        suffix = f"<div style='font-size:12px; color:#475569;'>... {len(cleaned) - limit} autres elements</div>"
    items = "".join(f"<li>{html.escape(value)}</li>" for value in preview)
    return f"<div style='max-height:{max_height}px; overflow-y:auto; padding-left:0.4rem;'><ul>{items}</ul>{suffix}</div>"


def count_genres(rows: pd.Series) -> Counter:
    counter = Counter()
    for genre_list in rows:
        counter.update([genre for genre in genre_list if genre and genre != "Unknown"])
    return counter


def top_genres_text(rows: pd.Series, limit: int = 4) -> str:
    counter = count_genres(rows)
    if not counter:
        return "Unknown"
    return ", ".join(f"{genre} ({count})" for genre, count in counter.most_common(limit))


@st.cache_data(show_spinner=False)
def load_imdb_map_data(sample_rows: int = SAMPLE_PRINCIPALS_ROWS) -> tuple[pd.DataFrame, dict]:
    cache_path = DATA_DIR / f"imdb_map_community_cache_{sample_rows}.pkl"
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    analysis_cache_path = DATA_DIR / f"imdb_graph_analysis_cache_{sample_rows}.pkl"
    if analysis_cache_path.exists():
        merged_base, analysis_audit = pd.read_pickle(analysis_cache_path)
        principals_raw = merged_base[["tconst", "nconst", "category"]].drop_duplicates()
        principals = principals_raw.copy()
        names = pd.DataFrame(columns=["nconst", "primaryName", "primaryProfession"])
        titles = pd.DataFrame(columns=["tconst", "primaryTitle", "titleType", "startYear", "genres"])
        ratings = pd.DataFrame(columns=["tconst", "averageRating", "numVotes"])
        merged = merged_base.copy()
    else:
        principals_raw = pd.read_csv(
            DATA_DIR / "title.principals.tsv",
            sep="\t",
            usecols=["tconst", "nconst", "category"],
            dtype=str,
            nrows=sample_rows,
            low_memory=False,
        )
        principals = principals_raw[principals_raw["category"].isin(GRAPH_CATEGORIES)].drop_duplicates()

        title_ids = principals["tconst"].dropna().unique().tolist()
        person_ids = principals["nconst"].dropna().unique().tolist()

        names = load_lookup_subset(
            DATA_DIR / "name.basics.tsv",
            "nconst",
            person_ids,
            ["nconst", "primaryName", "primaryProfession"],
        )
        titles = load_lookup_subset(
            DATA_DIR / "title.basics.tsv",
            "tconst",
            title_ids,
            ["tconst", "primaryTitle", "titleType", "startYear", "genres"],
        )
        ratings = load_lookup_subset(
            DATA_DIR / "title.ratings.tsv",
            "tconst",
            title_ids,
            ["tconst", "averageRating", "numVotes"],
        )

        merged = principals.merge(names, on="nconst", how="left")
        merged = merged.merge(titles, on="tconst", how="left")
        merged = merged.merge(ratings, on="tconst", how="left")

    title_ids = merged["tconst"].dropna().unique().tolist()
    regions = load_region_subset(title_ids)
    merged = merged.merge(regions, left_on="tconst", right_on="titleId", how="left")
    merged = merged.drop(columns=["titleId"], errors="ignore")

    merged = clean_text_columns(
        merged,
        [
            "primaryName",
            "primaryProfession",
            "primaryTitle",
            "titleType",
            "startYear",
            "genres",
            "averageRating",
            "numVotes",
            "region",
        ],
    )
    merged["primaryName"] = merged["primaryName"].fillna(merged["nconst"])
    merged["primaryProfession"] = merged["primaryProfession"].fillna("")
    merged["primaryTitle"] = merged["primaryTitle"].fillna(merged["tconst"])
    merged["titleType"] = merged["titleType"].fillna("unknown")
    merged["startYearInt"] = pd.to_numeric(merged["startYear"], errors="coerce")
    merged["genres"] = merged["genres"].fillna("Unknown")
    merged["genresList"] = merged["genres"].apply(
        lambda value: [genre.strip() for genre in str(value).split(",") if genre.strip()] or ["Unknown"]
    )
    merged["averageRating"] = pd.to_numeric(merged["averageRating"], errors="coerce").fillna(0.0)
    merged["numVotes"] = pd.to_numeric(merged["numVotes"], errors="coerce").fillna(0).astype(int)
    merged["region"] = merged["region"].fillna("XWW")
    merged["regionName"] = merged["region"].apply(region_name)
    merged["lat"] = merged["region"].map(lambda value: REGION_COORDS.get(value, REGION_COORDS["XWW"])[0])
    merged["lon"] = merged["region"].map(lambda value: REGION_COORDS.get(value, REGION_COORDS["XWW"])[1])

    merged["titleLabel"] = merged["primaryTitle"]
    year_mask = merged["startYearInt"].notna()
    merged.loc[year_mask, "titleLabel"] = (
        merged.loc[year_mask, "primaryTitle"]
        + " ("
        + merged.loc[year_mask, "startYearInt"].astype(int).astype(str)
        + ")"
    )

    valid_years = merged["startYearInt"].dropna()
    audit = {
        "sample_rows_requested": sample_rows,
        "principals_rows_read": int(len(principals_raw)),
        "principals_rows_kept": int(len(principals)),
        "unique_titles": int(principals["tconst"].nunique()),
        "unique_people": int(principals["nconst"].nunique()),
        "names_matched": int(
            analysis_audit["names_matched"] if analysis_cache_path.exists() else names["nconst"].nunique()
        ),
        "titles_matched": int(
            analysis_audit["titles_matched"] if analysis_cache_path.exists() else titles["tconst"].nunique()
        ),
        "ratings_matched": int(
            analysis_audit["ratings_matched"] if analysis_cache_path.exists() else ratings["tconst"].nunique()
        ),
        "regions_matched": int(regions["titleId"].nunique()),
        "merged_rows": int(len(merged)),
        "geo_titles": int(merged["tconst"].nunique()),
        "min_year": int(valid_years.min()) if not valid_years.empty else 1890,
        "max_year": int(valid_years.max()) if not valid_years.empty else 2026,
    }

    result = (merged.sort_values(["startYearInt", "primaryTitle", "primaryName"]), audit)
    pd.to_pickle(result, cache_path)
    return result


def apply_filters(
    frame: pd.DataFrame,
    selected_title_types: list[str],
    selected_genres: list[str],
    selected_regions: list[str],
    min_votes: int,
) -> pd.DataFrame:
    filtered = frame.copy()
    if selected_title_types:
        filtered = filtered[filtered["titleType"].isin(selected_title_types)]
    if selected_regions:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    if selected_genres:
        filtered = filtered[
            filtered["genresList"].apply(lambda genres: bool(set(genres).intersection(selected_genres)))
        ]
    filtered = filtered[filtered["numVotes"] >= min_votes]
    return filtered


def select_graph_titles(frame: pd.DataFrame, limit: int) -> list[str]:
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    if actor_rows.empty:
        return []
    ranked = (
        actor_rows.groupby("tconst")
        .agg(
            actor_count=("nconst", "nunique"),
            numVotes=("numVotes", "max"),
            averageRating=("averageRating", "max"),
        )
        .reset_index()
        .sort_values(["actor_count", "numVotes", "averageRating", "tconst"], ascending=[False, False, False, True])
        .head(limit)
    )
    return ranked["tconst"].tolist()


def build_actor_graph(frame: pd.DataFrame, max_actors_per_title: int = 12, min_weight: int = 1) -> nx.Graph:
    actor_rows = frame[frame["category"].isin(ACTOR_CATEGORIES)].copy()
    graph = nx.Graph()

    for actor_id, group in actor_rows.groupby("nconst"):
        all_categories = sorted(set(frame.loc[frame["nconst"] == actor_id, "category"].dropna()))
        profession_values = sorted(
            {
                profession.strip()
                for raw_value in group["primaryProfession"].dropna().astype(str)
                for profession in raw_value.split(",")
                if profession.strip()
            }
        )
        graph.add_node(
            actor_id,
            label=group["primaryName"].iloc[0],
            projects=int(group["tconst"].nunique()),
            role=", ".join(all_categories),
            profession=", ".join(profession_values),
        )

    for title_id, group in actor_rows.groupby("tconst"):
        actors = group[["nconst", "primaryName"]].drop_duplicates("nconst")
        if len(actors) < 2:
            continue
        if len(actors) > max_actors_per_title:
            actors = actors.head(max_actors_per_title)

        title_label = group["titleLabel"].iloc[0]
        genres = sorted({genre for genre_list in group["genresList"] for genre in genre_list if genre != "Unknown"})
        for left, right in combinations(actors["nconst"].tolist(), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
                graph[left][right]["titles"].add(title_label)
                graph[left][right]["genres"].update(genres)
            else:
                graph.add_edge(
                    left,
                    right,
                    weight=1,
                    titles={title_label},
                    genres=set(genres),
                )

    edges_to_remove = [(left, right) for left, right, data in graph.edges(data=True) if data["weight"] < min_weight]
    graph.remove_edges_from(edges_to_remove)
    graph.remove_nodes_from(list(nx.isolates(graph)))

    for _, _, data in graph.edges(data=True):
        data["titles"] = sorted(data["titles"])
        data["genres"] = sorted(data["genres"])

    actor_rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())]
    if graph.number_of_nodes() == 0:
        return graph

    community_map = detect_communities(graph)
    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))

    for actor_id, group in actor_rows.groupby("nconst"):
        genre_counter = count_genres(group["genresList"])
        regions = sorted(set(group["regionName"].dropna()))
        dominant_genres = [genre for genre, _ in genre_counter.most_common(5)]
        graph.nodes[actor_id]["community"] = community_map.get(actor_id, 0)
        graph.nodes[actor_id]["degree"] = degree_map.get(actor_id, 0)
        graph.nodes[actor_id]["weighted_degree"] = weighted_degree_map.get(actor_id, 0)
        graph.nodes[actor_id]["regions"] = regions
        graph.nodes[actor_id]["regionCodes"] = sorted(set(group["region"].dropna()))
        graph.nodes[actor_id]["dominantGenres"] = dominant_genres
        graph.nodes[actor_id]["mainRegion"] = regions[0] if regions else "Unknown"
        graph.nodes[actor_id]["mainGenre"] = dominant_genres[0] if dominant_genres else "Unknown"
        graph.nodes[actor_id]["titlesList"] = group["titleLabel"].drop_duplicates().tolist()
        graph.nodes[actor_id]["country"] = graph.nodes[actor_id]["mainRegion"]

    return graph


def build_director_graph(frame: pd.DataFrame, max_directors_per_title: int = 8, min_weight: int = 1) -> nx.Graph:
    director_rows = frame[frame["category"] == "director"].copy()
    graph = nx.Graph()

    for director_id, group in director_rows.groupby("nconst"):
        graph.add_node(
            director_id,
            label=group["primaryName"].iloc[0],
            projects=int(group["tconst"].nunique()),
            role="director",
        )

    for _, group in director_rows.groupby("tconst"):
        directors = group[["nconst", "primaryName"]].drop_duplicates("nconst")
        if len(directors) < 2:
            continue
        if len(directors) > max_directors_per_title:
            directors = directors.head(max_directors_per_title)

        title_label = group["titleLabel"].iloc[0]
        for left, right in combinations(directors["nconst"].tolist(), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
                graph[left][right]["titles"].add(title_label)
            else:
                graph.add_edge(left, right, weight=1, titles={title_label})

    edges_to_remove = [(left, right) for left, right, data in graph.edges(data=True) if data["weight"] < min_weight]
    graph.remove_edges_from(edges_to_remove)
    graph.remove_nodes_from(list(nx.isolates(graph)))

    for _, _, data in graph.edges(data=True):
        data["titles"] = sorted(data["titles"])

    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))
    for director_id, group in director_rows[director_rows["nconst"].isin(graph.nodes())].groupby("nconst"):
        graph.nodes[director_id]["degree"] = degree_map.get(director_id, 0)
        graph.nodes[director_id]["weighted_degree"] = weighted_degree_map.get(director_id, 0)
        graph.nodes[director_id]["titlesList"] = group["titleLabel"].drop_duplicates().tolist()
    return graph


def build_title_graph(frame: pd.DataFrame, max_titles_per_person: int = 8, min_weight: int = 1) -> nx.Graph:
    relevant_rows = frame[frame["category"].isin(GRAPH_CATEGORIES)].copy()
    graph = nx.Graph()

    for title_id, group in relevant_rows.groupby("tconst"):
        participants = group["primaryName"].drop_duplicates().tolist()
        graph.add_node(
            title_id,
            label=group["titleLabel"].iloc[0],
            projects=int(group["nconst"].nunique()),
            role=group["titleType"].iloc[0],
            profession=group["titleType"].iloc[0],
            year=int(group["startYearInt"].dropna().iloc[0]) if group["startYearInt"].notna().any() else None,
            rating=float(group["averageRating"].max()) if group["averageRating"].notna().any() else 0.0,
            votes=int(group["numVotes"].max()) if group["numVotes"].notna().any() else 0,
            mainGenre=next((genre for genre in group["genresList"].iloc[0] if genre != "Unknown"), "Unknown"),
            titlesList=participants,
            participantsList=participants,
        )

    for _, group in relevant_rows.groupby("nconst"):
        titles = (
            group[["tconst", "titleLabel", "numVotes", "category"]]
            .sort_values(["numVotes", "titleLabel"], ascending=[False, True])
            .drop_duplicates("tconst")
        )
        if len(titles) < 2:
            continue
        if len(titles) > max_titles_per_person:
            titles = titles.head(max_titles_per_person)

        participant_name = group["primaryName"].iloc[0]
        participant_roles = sorted(set(group["category"].dropna()))
        for left, right in combinations(titles["tconst"].tolist(), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
                graph[left][right]["sharedPeople"].add(participant_name)
                graph[left][right]["sharedRoles"].update(participant_roles)
            else:
                graph.add_edge(
                    left,
                    right,
                    weight=1,
                    titles={graph.nodes[left]["label"], graph.nodes[right]["label"]},
                    sharedPeople={participant_name},
                    sharedRoles=set(participant_roles),
                )

    edges_to_remove = [(left, right) for left, right, data in graph.edges(data=True) if data["weight"] < min_weight]
    graph.remove_edges_from(edges_to_remove)
    graph.remove_nodes_from(list(nx.isolates(graph)))

    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))
    for node, data in graph.nodes(data=True):
        data["degree"] = degree_map.get(node, 0)
        data["weighted_degree"] = weighted_degree_map.get(node, 0)

    for _, _, data in graph.edges(data=True):
        data["titles"] = sorted(data.get("titles", []))
        data["sharedPeople"] = sorted(data.get("sharedPeople", []))
        data["genres"] = sorted(data.get("sharedRoles", []))

    return graph


def build_creator_graph(
    frame: pd.DataFrame,
    focus_categories: tuple[str, ...] = ("director", "producer", "writer"),
    max_people_per_title: int = 10,
    min_weight: int = 1,
) -> nx.Graph:
    creator_rows = frame[frame["category"].isin(focus_categories)].copy()
    graph = nx.Graph()

    for person_id, group in creator_rows.groupby("nconst"):
        role_counts = Counter(group["category"].dropna())
        primary_role = role_counts.most_common(1)[0][0] if role_counts else "creator"
        profession_values = sorted(
            {
                profession.strip()
                for raw_value in group["primaryProfession"].dropna().astype(str)
                for profession in raw_value.split(",")
                if profession.strip()
            }
        )
        graph.add_node(
            person_id,
            label=group["primaryName"].iloc[0],
            projects=int(group["tconst"].nunique()),
            role=primary_role,
            profession=", ".join(profession_values),
            titlesList=group["titleLabel"].drop_duplicates().tolist(),
            mainGenre=next((genre for genre in count_genres(group["genresList"]).keys() if genre != "Unknown"), "Unknown"),
        )

    for _, group in creator_rows.groupby("tconst"):
        people = group[["nconst", "primaryName"]].drop_duplicates("nconst")
        if len(people) < 2:
            continue
        if len(people) > max_people_per_title:
            people = people.head(max_people_per_title)

        title_label = group["titleLabel"].iloc[0]
        title_roles = sorted(set(group["category"].dropna()))
        for left, right in combinations(people["nconst"].tolist(), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
                graph[left][right]["titles"].add(title_label)
                graph[left][right]["genres"].update(title_roles)
            else:
                graph.add_edge(left, right, weight=1, titles={title_label}, genres=set(title_roles))

    edges_to_remove = [(left, right) for left, right, data in graph.edges(data=True) if data["weight"] < min_weight]
    graph.remove_edges_from(edges_to_remove)
    graph.remove_nodes_from(list(nx.isolates(graph)))

    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))
    for node, data in graph.nodes(data=True):
        data["degree"] = degree_map.get(node, 0)
        data["weighted_degree"] = weighted_degree_map.get(node, 0)

    for _, _, data in graph.edges(data=True):
        data["titles"] = sorted(data["titles"])
        data["genres"] = sorted(data["genres"])

    return graph


def remember_resource(cache_name: str, cache_key: tuple, builder) -> object:
    cache = st.session_state.setdefault(cache_name, {})
    if cache_key not in cache:
        cache[cache_key] = builder()
        if len(cache) > 6:
            oldest_key = next(iter(cache))
            if oldest_key != cache_key:
                cache.pop(oldest_key, None)
    return cache[cache_key]


@st.cache_data(show_spinner=False)
def load_project_story_assets() -> dict:
    assets: dict[str, object] = {
        "all_image_path": OUTPUTS_DIR / "backend_community_bubbles_all_actors.png",
        "top_image_path": OUTPUTS_DIR / "backend_community_bubbles_top.png",
        "paths_image_path": OUTPUTS_DIR / "community_shortest_paths_focus.png",
        "all_stats": {},
        "genre_distribution": pd.DataFrame(),
        "community_percent_table": pd.DataFrame(),
        "community_genre_bubbles": pd.DataFrame(),
        "top_actors_table": pd.DataFrame(),
        "actor_producers_table": pd.DataFrame(),
    }

    all_stats_path = OUTPUTS_DIR / "backend_community_bubbles_all_actors_stats.json"
    top_stats_path = OUTPUTS_DIR / "backend_community_bubbles_top_stats.csv"
    top_actors_path = OUTPUTS_DIR / "top_acteurs_par_communaute.csv"
    community_genre_bubbles_path = OUTPUTS_DIR / "community_genre_percentages_global.csv"
    actor_producers_path = OUTPUTS_DIR / "actor_producers_by_community.csv"

    if all_stats_path.exists():
        assets["all_stats"] = json.loads(all_stats_path.read_text(encoding="utf-8"))

    top_stats = pd.read_csv(top_stats_path) if top_stats_path.exists() else pd.DataFrame()
    top_actors = pd.read_csv(top_actors_path) if top_actors_path.exists() else pd.DataFrame()
    if community_genre_bubbles_path.exists():
        assets["community_genre_bubbles"] = pd.read_csv(community_genre_bubbles_path)
    if actor_producers_path.exists():
        assets["actor_producers_table"] = pd.read_csv(actor_producers_path)

    total_connected_actors = int(assets["all_stats"].get("actors_analyzed", 0)) if assets["all_stats"] else 0

    if not top_actors.empty and total_connected_actors > 0:
        leaders = (
            top_actors[top_actors["rank_in_community"] == 1]
            .rename(columns={"actor_name": "acteur_central", "main_genre": "genre_principal_acteur"})
            [["community_id", "community_size", "acteur_central", "genre_principal_acteur", "weighted_degree", "degree", "projects"]]
        )
        if not top_stats.empty:
            top_stats = top_stats.rename(columns={"actor_count": "community_size"})
            leaders = leaders.merge(
                top_stats[["community_id", "community_size", "dominant_genres", "density", "title_count"]],
                on=["community_id", "community_size"],
                how="left",
            )
        top_actor_names = (
            top_actors[top_actors["rank_in_community"] <= 5]
            .sort_values(["community_id", "rank_in_community"])
            .groupby("community_id")["actor_name"]
            .apply(lambda values: ", ".join(values.tolist()))
            .reset_index(name="acteurs_importants")
        )
        leaders = leaders.merge(top_actor_names, on="community_id", how="left")
        leaders["pourcentage_acteurs"] = (leaders["community_size"] / total_connected_actors * 100).round(2)
        leaders = leaders.sort_values(["community_size", "weighted_degree"], ascending=False)
        assets["community_percent_table"] = leaders.rename(
            columns={
                "community_id": "communaute",
                "community_size": "acteurs",
                "weighted_degree": "degre_pondere_acteur_central",
                "degree": "liens_uniques_acteur_central",
                "projects": "projets_acteur_central",
                "dominant_genres": "genres_dominants",
                "title_count": "titres_associes",
                "density": "densite",
            }
        )
        assets["top_actors_table"] = top_actors.rename(
            columns={
                "community_id": "communaute",
                "community_size": "taille_communaute",
                "rank_in_community": "rang",
                "actor_name": "acteur",
                "weighted_degree": "degre_pondere",
                "degree": "liens_uniques",
                "projects": "projets",
                "main_genre": "genre_principal",
            }
        )

    global_cache_path = DATA_DIR / "imdb_graph_analysis_cache_300000.pkl"
    if global_cache_path.exists():
        merged_base, _ = pd.read_pickle(global_cache_path)
        actor_rows = merged_base[merged_base["category"].isin(ACTOR_CATEGORIES)].copy()
        source_actor_total = int(actor_rows["nconst"].nunique())
        assets["all_stats"]["source_actor_total"] = source_actor_total
        if total_connected_actors:
            assets["all_stats"]["not_connected_or_removed"] = source_actor_total - total_connected_actors

        exploded = actor_rows[["nconst", "genresList"]].explode("genresList")
        exploded["genresList"] = exploded["genresList"].fillna("Unknown").astype(str)
        exploded.loc[exploded["genresList"].eq(""), "genresList"] = "Unknown"
        genre_counts = (
            exploded.groupby(["nconst", "genresList"])
            .size()
            .reset_index(name="count")
            .sort_values(["nconst", "count", "genresList"], ascending=[True, False, True])
        )
        dominant_genres = genre_counts.drop_duplicates("nconst")[["nconst", "genresList"]].rename(columns={"genresList": "genre_principal"})
        genre_distribution = (
            dominant_genres["genre_principal"]
            .value_counts(dropna=False)
            .rename_axis("genre")
            .reset_index(name="acteurs")
        )
        genre_distribution["pourcentage"] = (genre_distribution["acteurs"] / max(source_actor_total, 1) * 100).round(2)
        assets["genre_distribution"] = genre_distribution

    return assets


def detect_communities(graph: nx.Graph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    if graph.number_of_edges() == 0:
        mapping = {node: index + 1 for index, node in enumerate(graph.nodes())}
        nx.set_node_attributes(graph, mapping, "community")
        return mapping

    communities = nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")
    mapping = {}
    for index, community in enumerate(communities, start=1):
        for node in community:
            mapping[node] = index
    nx.set_node_attributes(graph, mapping, "community")
    return mapping


def actor_summary_table(_graph: nx.Graph) -> pd.DataFrame:
    graph = _graph
    rows = []
    for node, data in graph.nodes(data=True):
        rows.append(
            {
                "acteur": data.get("label", node),
                "communaute": data.get("community", 0),
                "collaborateurs_uniques": data.get("degree", 0),
                "collaborations_ponderees": data.get("weighted_degree", 0),
                "titres": data.get("projects", 0),
                "genres_dominants": join_list(data.get("dominantGenres", []), limit=4),
                "regions": join_list(data.get("regions", []), limit=4),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["collaborateurs_uniques", "collaborations_ponderees", "titres"], ascending=False)


def director_summary_table(_graph: nx.Graph) -> pd.DataFrame:
    graph = _graph
    rows = []
    for node, data in graph.nodes(data=True):
        rows.append(
            {
                "realisateur": data.get("label", node),
                "collaborateurs_uniques": data.get("degree", 0),
                "collaborations_ponderees": data.get("weighted_degree", 0),
                "projets": data.get("projects", 0),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["collaborateurs_uniques", "collaborations_ponderees", "projets"], ascending=False)


def generic_graph_summary_table(graph: nx.Graph, label_column: str) -> pd.DataFrame:
    rows = []
    for node, data in graph.nodes(data=True):
        rows.append(
            {
                label_column: data.get("label", node),
                "type": data.get("role", ""),
                "liens_uniques": data.get("degree", 0),
                "liens_ponderes": data.get("weighted_degree", 0),
                "projets": data.get("projects", 0),
                "genre_principal": data.get("mainGenre", "Unknown"),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["liens_uniques", "liens_ponderes", "projets"], ascending=False)


def build_community_graph(actor_graph: nx.Graph, actor_rows: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    if actor_graph.number_of_nodes() == 0:
        return graph

    rows = actor_rows[actor_rows["nconst"].isin(actor_graph.nodes())].copy()
    if rows.empty:
        return graph

    community_map = nx.get_node_attributes(actor_graph, "community")
    degree_map = dict(actor_graph.degree())
    rows["community"] = rows["nconst"].map(community_map)
    rows = rows[rows["community"].notna()].copy()
    rows["community"] = rows["community"].astype(int)

    for community_id, group in rows.groupby("community"):
        actor_ids = sorted(set(group["nconst"]))
        top_actor_id = max(actor_ids, key=lambda actor_id: degree_map.get(actor_id, 0)) if actor_ids else None
        top_actor_name = actor_graph.nodes[top_actor_id].get("label", top_actor_id) if top_actor_id in actor_graph.nodes else "n/a"
        actor_names = sorted(group["primaryName"].drop_duplicates().tolist())
        graph.add_node(
            f"community_{community_id}",
            label=f"Communaute {community_id}",
            role="community",
            profession="community",
            communityId=int(community_id),
            projects=int(group["tconst"].nunique()),
            degree=0,
            weighted_degree=0,
            mainGenre=top_genres_text(group["genresList"], limit=1),
            actorsList=actor_names,
            titlesList=group["titleLabel"].drop_duplicates().tolist(),
            topActor=top_actor_name,
            actorCount=len(actor_ids),
        )

    edge_buckets: dict[tuple[str, str], dict] = {}
    for left, right, data in actor_graph.edges(data=True):
        left_community = community_map.get(left)
        right_community = community_map.get(right)
        if left_community is None or right_community is None or left_community == right_community:
            continue
        pair = tuple(sorted((f"community_{left_community}", f"community_{right_community}")))
        bucket = edge_buckets.setdefault(pair, {"weight": 0, "titles": set(), "actors": set(), "genres": set()})
        bucket["weight"] += int(data.get("weight", 1))
        bucket["titles"].update(data.get("titles", []))
        bucket["genres"].update(data.get("genres", []))
        bucket["actors"].update(
            [
                actor_graph.nodes[left].get("label", left),
                actor_graph.nodes[right].get("label", right),
            ]
        )

    for (left_node, right_node), data in edge_buckets.items():
        graph.add_edge(
            left_node,
            right_node,
            weight=data["weight"],
            titles=sorted(data["titles"]),
            genres=sorted(data["genres"]),
            sharedPeople=sorted(data["actors"]),
        )

    degree_map = dict(graph.degree())
    weighted_degree_map = dict(graph.degree(weight="weight"))
    for node in graph.nodes():
        graph.nodes[node]["degree"] = degree_map.get(node, 0)
        graph.nodes[node]["weighted_degree"] = weighted_degree_map.get(node, 0)

    return graph


def network_example_figure(
    graph: nx.Graph,
    title: str,
    node_color: str,
    max_nodes: int,
    list_field: str = "titlesList",
    list_label: str = "Titres",
    project_label: str = "Projets",
    color_attr: str | None = None,
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    fig = go.Figure()
    if graph.number_of_nodes() == 0:
        fig.update_layout(title=title, height=520)
        return fig

    weighted_degree = dict(graph.degree(weight="weight"))
    selected_nodes = sorted(graph.nodes(), key=lambda node: weighted_degree.get(node, 0), reverse=True)[:max_nodes]
    subgraph = graph.subgraph(selected_nodes).copy()
    if subgraph.number_of_nodes() == 0:
        fig.update_layout(title=title, height=520)
        return fig

    positions = nx.spring_layout(subgraph, seed=42, weight="weight", k=1.1 / max(math.sqrt(subgraph.number_of_nodes()), 1))

    edge_x = []
    edge_y = []
    edge_mid_x = []
    edge_mid_y = []
    edge_text = []
    for left, right, data in subgraph.edges(data=True):
        x0, y0 = positions[left]
        x1, y1 = positions[right]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_mid_x.append((x0 + x1) / 2)
        edge_mid_y.append((y0 + y1) / 2)
        detail_block = scroll_list_html(data.get("titles", []), max_height=120)
        if data.get("sharedPeople"):
            detail_block = scroll_list_html(data.get("sharedPeople", []), max_height=120)
        edge_text.append(
            f"{subgraph.nodes[left].get('label', left)} <-> {subgraph.nodes[right].get('label', right)}"
            f"<br>Poids: {data.get('weight', 1)}"
            f"<br>Detail: {detail_block}"
        )

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"color": "rgba(37, 99, 235, 0.35)", "width": 1.5},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    if edge_mid_x:
        fig.add_trace(
            go.Scatter(
                x=edge_mid_x,
                y=edge_mid_y,
                mode="markers",
                marker={"size": 9, "color": "rgba(37, 99, 235, 0.16)"},
                customdata=edge_text,
                hovertemplate="%{customdata}<extra>Lien</extra>",
                showlegend=False,
            )
        )

    node_x = []
    node_y = []
    node_size = []
    node_text = []
    node_labels = []
    node_colors = []
    degree_map = dict(subgraph.degree())
    weighted_degree_sub = dict(subgraph.degree(weight="weight"))
    for node, data in subgraph.nodes(data=True):
        x_value, y_value = positions[node]
        node_x.append(x_value)
        node_y.append(y_value)
        node_size.append(10 + min(weighted_degree_sub.get(node, 0) * 2.5, 30))
        node_labels.append(data.get("label", node)[:18])
        current_node_color = node_color
        if color_attr and color_map:
            current_node_color = color_map.get(str(data.get(color_attr, "")), node_color)
        node_text.append(
            f"{data.get('label', node)}"
            f"<br>Collaborateurs: {degree_map.get(node, 0)}"
            f"<br>Poids total: {weighted_degree_sub.get(node, 0)}"
            f"<br>{project_label}: {data.get('projects', 0)}"
            f"<br>{list_label}: {scroll_list_html(data.get(list_field, []), max_height=120)}"
        )
        node_colors.append(current_node_color)

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_labels,
            textposition="top center",
            marker={"size": node_size, "color": node_colors, "line": {"color": "white", "width": 1}},
            customdata=node_text,
            hovertemplate="%{customdata}<extra>Sommet</extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        title=title,
        height=560,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
    )
    return fig


def actor_group_value(node_data: dict, group_by: str) -> str:
    if group_by == "Pays":
        return node_data.get("mainRegion", "Unknown") or "Unknown"
    if group_by == "Genre":
        return node_data.get("mainGenre", "Unknown") or "Unknown"
    if group_by == "Profession":
        return node_data.get("profession", "") or node_data.get("role", "Unknown") or "Unknown"
    return f"Communaute {node_data.get('community', 0)}"


def grouped_network_positions(
    subgraph: nx.Graph,
    group_by: str,
    spacing_multiplier: float,
) -> dict[str, tuple[float, float]]:
    if subgraph.number_of_nodes() == 0:
        return {}

    grouped_nodes: dict[str, list[str]] = defaultdict(list)
    for node, data in subgraph.nodes(data=True):
        grouped_nodes[actor_group_value(data, group_by)].append(node)

    ordered_groups = sorted(grouped_nodes, key=lambda value: len(grouped_nodes[value]), reverse=True)
    cols = max(1, math.ceil(math.sqrt(len(ordered_groups))))
    spacing = 10.0 * spacing_multiplier
    positions: dict[str, tuple[float, float]] = {}

    for index, group_name in enumerate(ordered_groups):
        nodes = grouped_nodes[group_name]
        center_x = (index % cols) * spacing
        center_y = -(index // cols) * spacing
        group_graph = subgraph.subgraph(nodes).copy()

        if len(nodes) == 1:
            local_positions = {nodes[0]: (0.0, 0.0)}
        else:
            local_positions = nx.spring_layout(
                group_graph,
                seed=42 + index,
                weight="weight",
                k=max(0.8, 2.2 / max(math.sqrt(len(nodes)), 1)),
            )

        scale = (2.3 + min(len(nodes), 60) / 16) * spacing_multiplier
        for node, (x_value, y_value) in local_positions.items():
            positions[node] = (center_x + x_value * scale, center_y + y_value * scale)

    return positions


def filtered_actor_subgraph(
    graph: nx.Graph,
    group_by: str,
    selected_groups: list[str],
    edge_filter_mode: str,
    min_edge_weight: int,
    max_nodes: int,
    max_edges: int,
    keep_isolates: bool = False,
) -> tuple[nx.Graph, dict]:
    if graph.number_of_nodes() == 0:
        return nx.Graph(), {"nodes": 0, "edges_total": 0, "edges_shown": 0, "groups": 0}

    selected_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if not selected_groups or actor_group_value(data, group_by) in selected_groups
    ]
    if len(selected_nodes) > max_nodes:
        weighted_degree = dict(graph.degree(weight="weight"))
        selected_nodes = sorted(
            selected_nodes,
            key=lambda node: weighted_degree.get(node, 0),
            reverse=True,
        )[:max_nodes]

    subgraph = graph.subgraph(selected_nodes).copy()
    if subgraph.number_of_nodes() == 0:
        return subgraph, {"nodes": 0, "edges_total": 0, "edges_shown": 0, "groups": 0}

    edge_filter_mode = edge_filter_mode.strip()
    if edge_filter_mode != "Tous les liens":
        removable_by_mode = []
        for left, right, _ in subgraph.edges(data=True):
            left_data = subgraph.nodes[left]
            right_data = subgraph.nodes[right]
            same_community = left_data.get("community") == right_data.get("community")
            same_genre = left_data.get("mainGenre", "Unknown") == right_data.get("mainGenre", "Unknown")
            same_country = left_data.get("mainRegion", "Unknown") == right_data.get("mainRegion", "Unknown")
            same_profession = left_data.get("profession", "") == right_data.get("profession", "")
            remove = False
            if edge_filter_mode == "Liens meme communaute" and not same_community:
                remove = True
            elif edge_filter_mode == "Liens meme genre" and not same_genre:
                remove = True
            elif edge_filter_mode == "Liens meme pays" and not same_country:
                remove = True
            elif edge_filter_mode == "Liens meme profession" and not same_profession:
                remove = True
            if remove:
                removable_by_mode.append((left, right))
        subgraph.remove_edges_from(removable_by_mode)

    removable_edges = [
        (left, right)
        for left, right, data in subgraph.edges(data=True)
        if data.get("weight", 1) < min_edge_weight
    ]
    subgraph.remove_edges_from(removable_edges)

    total_edges = subgraph.number_of_edges()
    if total_edges > max_edges:
        ranked_edges = sorted(
            subgraph.edges(data=True),
            key=lambda item: (item[2].get("weight", 1), len(item[2].get("titles", []))),
            reverse=True,
        )[:max_edges]
        trimmed = nx.Graph()
        trimmed.add_nodes_from(subgraph.nodes(data=True))
        for left, right, data in ranked_edges:
            trimmed.add_edge(left, right, **data)
        subgraph = trimmed

    if not keep_isolates and subgraph.number_of_edges() > 0:
        subgraph.remove_nodes_from(list(nx.isolates(subgraph)))

    group_names = sorted({actor_group_value(data, group_by) for _, data in subgraph.nodes(data=True)})
    return subgraph, {
        "nodes": subgraph.number_of_nodes(),
        "edges_total": total_edges,
        "edges_shown": subgraph.number_of_edges(),
        "groups": len(group_names),
    }


def actor_browser_graph_html(
    subgraph: nx.Graph,
    group_by: str,
    spacing_multiplier: float,
    show_labels: bool,
    highlighted_path: list[str] | None = None,
) -> str:
    if subgraph.number_of_nodes() == 0:
        return """
        <div style="padding:2rem;border:1px solid #cbd5e1;border-radius:20px;background:white;color:#0f172a;">
            Aucun acteur visible avec ces filtres. Elargissez les groupes, augmentez la limite de sommets
            ou baissez le poids minimum des liens.
        </div>
        """

    positions = grouped_network_positions(subgraph, group_by, spacing_multiplier)
    group_names = sorted({actor_group_value(data, group_by) for _, data in subgraph.nodes(data=True)})
    group_color_map = {
        group_name: COMMUNITY_COLORS[index % len(COMMUNITY_COLORS)]
        for index, group_name in enumerate(group_names)
    }
    path_nodes = set(highlighted_path or [])
    path_edges = {
        tuple(sorted((highlighted_path[index], highlighted_path[index + 1])))
        for index in range(len(highlighted_path or []) - 1)
    }

    weighted_degree_map = dict(subgraph.degree(weight="weight"))
    ranked_nodes = sorted(
        subgraph.nodes(data=True),
        key=lambda item: weighted_degree_map.get(item[0], 0),
        reverse=True,
    )

    nodes_payload = []
    node_details = {}
    for rank, (node, data) in enumerate(ranked_nodes, start=1):
        group_value = actor_group_value(data, group_by)
        actor_name = data.get("label", node)
        is_path_node = node in path_nodes
        node_color = "#f59e0b" if is_path_node else group_color_map[group_value]
        border_color = "#0f172a" if is_path_node else "rgba(15, 23, 42, 0.35)"
        label_value = actor_name if show_labels or rank <= 18 or is_path_node else ""
        x_value, y_value = positions.get(node, (0.0, 0.0))
        nodes_payload.append(
            {
                "id": node,
                "label": label_value,
                "actorName": actor_name,
                "searchTitles": data.get("titlesList", []),
                "groupLabel": group_value,
                "x": round(x_value * 150, 3),
                "y": round(y_value * 150, 3),
                "size": max(10, min(28, 9 + weighted_degree_map.get(node, 0) * 0.42)),
                "shape": "dot",
                "color": {"background": node_color, "border": border_color, "highlight": {"background": "#f97316", "border": "#111827"}},
                "font": {"size": 16 if label_value else 1, "face": "Segoe UI", "color": "#0f172a"},
                "title": (
                    f"{html.escape(actor_name)}<br>"
                    f"Groupe: {html.escape(group_value)}<br>"
                    f"Collaborateurs: {data.get('degree', 0)}<br>"
                    f"Films joues: {data.get('projects', 0)}"
                ),
            }
        )
        node_details[node] = {
            "actorName": actor_name,
            "actorId": node,
            "groupLabel": group_value,
            "community": int(data.get("community", 0)),
            "country": data.get("country", "Unknown"),
            "mainGenre": data.get("mainGenre", "Unknown"),
            "roles": data.get("role", ""),
            "profession": data.get("profession", ""),
            "degree": int(data.get("degree", 0)),
            "weightedDegree": int(weighted_degree_map.get(node, 0)),
            "projects": int(data.get("projects", 0)),
            "regions": data.get("regions", []),
            "genres": data.get("dominantGenres", []),
            "titles": data.get("titlesList", []),
        }

    edges_payload = []
    edge_details = {}
    for left, right, data in subgraph.edges(data=True):
        edge_id = f"{left}__{right}"
        common_titles = data.get("titles", [])
        common_genres = data.get("genres", [])
        pair_key = tuple(sorted((left, right)))
        is_path_edge = pair_key in path_edges
        edges_payload.append(
            {
                "id": edge_id,
                "from": left,
                "to": right,
                "width": max(1.1, min(6.2, 1.0 + math.log1p(max(data.get("weight", 1), 1)) * 1.8)),
                "color": {"color": "#1d4ed8" if is_path_edge else "rgba(37, 99, 235, 0.30)", "highlight": "#0f172a"},
                "smooth": {"enabled": True, "type": "dynamic"},
                "title": (
                    f"{html.escape(subgraph.nodes[left].get('label', left))} <-> "
                    f"{html.escape(subgraph.nodes[right].get('label', right))}<br>"
                    f"Films en commun: {len(common_titles)}"
                ),
            }
        )
        edge_details[edge_id] = {
            "leftName": subgraph.nodes[left].get("label", left),
            "rightName": subgraph.nodes[right].get("label", right),
            "leftId": left,
            "rightId": right,
            "weight": int(data.get("weight", 1)),
            "commonTitlesCount": int(len(common_titles)),
            "titles": common_titles,
            "genres": common_genres,
            "leftGroup": actor_group_value(subgraph.nodes[left], group_by),
            "rightGroup": actor_group_value(subgraph.nodes[right], group_by),
            "leftTitles": subgraph.nodes[left].get("titlesList", []),
            "rightTitles": subgraph.nodes[right].get("titlesList", []),
            "leftProfession": subgraph.nodes[left].get("profession", ""),
            "rightProfession": subgraph.nodes[right].get("profession", ""),
        }

    legend_html = "".join(
        f"<span class='legend-chip'><span class='legend-dot' style='background:{group_color_map[group_name]}'></span>{html.escape(group_name)}</span>"
        for group_name in group_names[:18]
    )
    if len(group_names) > 18:
        legend_html += f"<span class='legend-chip'>+ {len(group_names) - 18} groupes</span>"

    suggestion_values = []
    seen_suggestions = set()
    for data in nodes_payload:
        actor_name = data["actorName"]
        if actor_name not in seen_suggestions:
            seen_suggestions.add(actor_name)
            suggestion_values.append(actor_name)
        for title in data.get("searchTitles", [])[:10]:
            if title not in seen_suggestions:
                seen_suggestions.add(title)
                suggestion_values.append(title)
        if len(suggestion_values) >= 500:
            break

    actor_options = "".join(
        f"<option value=\"{html.escape(value)}\"></option>"
        for value in suggestion_values[:500]
    )

    graph_payload_json = json.dumps(nodes_payload, ensure_ascii=True)
    edge_payload_json = json.dumps(edges_payload, ensure_ascii=True)
    node_details_json = json.dumps(node_details, ensure_ascii=True)
    edge_details_json = json.dumps(edge_details, ensure_ascii=True)

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css"/>
        <style>
            body {{
                margin: 0;
                background: transparent;
                font-family: "Segoe UI", Arial, sans-serif;
                color: #0f172a;
            }}
            .graph-shell {{
                background: white;
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 22px;
                box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
                overflow: hidden;
            }}
            .toolbar {{
                background: linear-gradient(135deg, #0f766e 0%, #0f9f74 55%, #2563eb 100%);
                color: white;
                padding: 18px 20px 16px 20px;
            }}
            .toolbar h3 {{
                margin: 0 0 6px 0;
                font-size: 24px;
            }}
            .toolbar p {{
                margin: 0 0 12px 0;
                font-size: 14px;
                opacity: 0.92;
            }}
            .toolbar-row {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                align-items: center;
            }}
            .toolbar input {{
                flex: 1 1 320px;
                min-width: 240px;
                border: none;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 14px;
            }}
            .toolbar button {{
                border: none;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                background: #082f49;
                color: white;
            }}
            .toolbar button.secondary {{
                background: rgba(255, 255, 255, 0.16);
            }}
            .stats-strip {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 12px;
            }}
            .stat-chip {{
                background: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 999px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            .legend {{
                padding: 12px 18px;
                border-bottom: 1px solid rgba(148, 163, 184, 0.20);
                background: #f8fafc;
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }}
            .legend-chip {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: white;
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            .legend-dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
                display: inline-block;
            }}
            .graph-grid {{
                display: grid;
                grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.9fr);
                min-height: 760px;
            }}
            #actor-network {{
                width: 100%;
                height: 760px;
                background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            }}
            .details-panel {{
                border-left: 1px solid rgba(148, 163, 184, 0.22);
                background: #fbfdff;
                padding: 18px;
                overflow-y: auto;
            }}
            .details-panel h4 {{
                margin: 0 0 10px 0;
                font-size: 20px;
            }}
            .details-panel p {{
                margin: 4px 0;
                font-size: 14px;
                line-height: 1.45;
            }}
            .details-panel .muted {{
                color: #475569;
            }}
            .detail-list {{
                margin-top: 10px;
                max-height: 220px;
                overflow-y: auto;
                padding-right: 6px;
                border-top: 1px solid rgba(148, 163, 184, 0.18);
                padding-top: 10px;
            }}
            .detail-pill {{
                display: inline-block;
                background: #e8f2ff;
                color: #0f172a;
                border: 1px solid rgba(59, 130, 246, 0.18);
                border-radius: 999px;
                padding: 5px 9px;
                margin: 0 6px 6px 0;
                font-size: 12px;
            }}
            @media (max-width: 1100px) {{
                .graph-grid {{
                    grid-template-columns: 1fr;
                }}
                .details-panel {{
                    border-left: none;
                    border-top: 1px solid rgba(148, 163, 184, 0.22);
                }}
            }}
        </style>
    </head>
    <body>
        <div class="graph-shell">
            <div class="toolbar">
                <h3>Graphe acteurs interactif</h3>
                <p>Un sommet = un acteur. Une arete = un ou plusieurs films en commun. La recherche accepte un nom d'acteur ou un titre de film.</p>
                <div class="toolbar-row">
                    <input id="actorSearch" list="actorSuggestions" placeholder="Rechercher un acteur ou un titre visible dans le graphe..." />
                    <datalist id="actorSuggestions">{actor_options}</datalist>
                    <button onclick="focusActor()">Rechercher</button>
                    <button class="secondary" onclick="toggleEdges()">Afficher / masquer les liens</button>
                    <button class="secondary" onclick="resetView()">Recentrer</button>
                </div>
                <div class="stats-strip">
                    <div class="stat-chip">{subgraph.number_of_nodes()} sommets visibles</div>
                    <div class="stat-chip">{subgraph.number_of_edges()} aretes visibles</div>
                    <div class="stat-chip">{len(group_names)} groupes</div>
                    <div class="stat-chip">Regroupement: {html.escape(group_by)}</div>
                </div>
            </div>
            <div class="legend">{legend_html}</div>
            <div class="graph-grid">
                <div id="actor-network"></div>
                <aside class="details-panel">
                    <div id="detailsContent">
                        <h4>Exploration guidee</h4>
                        <p class="muted">Cliquez un acteur pour voir toutes ses informations visibles dans la base chargee.</p>
                        <p class="muted">Cliquez un lien pour voir tous les films en commun entre deux acteurs, leurs genres partages et la force de la relation.</p>
                        <p class="muted">Le bouton de recherche peut recentrer le graphe sur un acteur ou retrouver les acteurs visibles relies a un titre de film.</p>
                    </div>
                </aside>
            </div>
        </div>

        <script>
            const nodesData = {graph_payload_json};
            const edgesData = {edge_payload_json};
            const nodeDetails = {node_details_json};
            const edgeDetails = {edge_details_json};
            const nodes = new vis.DataSet(nodesData);
            const edges = new vis.DataSet(edgesData);
            const container = document.getElementById("actor-network");
            const detailBox = document.getElementById("detailsContent");
            let linksVisible = true;

            function escapeHtml(value) {{
                return String(value ?? "")
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }}

            function renderPills(values) {{
                if (!values || !values.length) {{
                    return "<p class='muted'>n/a</p>";
                }}
                return "<div class='detail-list'>" + values.map((value) => "<span class='detail-pill'>" + escapeHtml(value) + "</span>").join("") + "</div>";
            }}

            function showNodeDetails(nodeId) {{
                const data = nodeDetails[nodeId];
                if (!data) {{
                    return;
                }}
                detailBox.innerHTML = `
                    <h4>${{escapeHtml(data.actorName)}}</h4>
                    <p><strong>ID IMDb:</strong> ${{escapeHtml(data.actorId)}}</p>
                    <p><strong>Groupe visible:</strong> ${{escapeHtml(data.groupLabel)}}</p>
                    <p><strong>Communaute:</strong> ${{escapeHtml(data.community)}}</p>
                    <p><strong>Pays:</strong> ${{escapeHtml(data.country)}}</p>
                    <p><strong>Genre principal:</strong> ${{escapeHtml(data.mainGenre)}}</p>
                    <p><strong>Roles dans les donnees:</strong> ${{escapeHtml(data.roles || "n/a")}}</p>
                    <p><strong>Primary profession IMDb:</strong> ${{escapeHtml(data.profession || "n/a")}}</p>
                    <p><strong>Collaborateurs differents:</strong> ${{escapeHtml(data.degree)}}</p>
                    <p><strong>Force totale des liens:</strong> ${{escapeHtml(data.weightedDegree)}}</p>
                    <p><strong>Nombre de projets:</strong> ${{escapeHtml(data.projects)}}</p>
                    <p><strong>Regions visibles:</strong></p>
                    ${{renderPills(data.regions)}}
                    <p><strong>Genres visibles:</strong></p>
                    ${{renderPills(data.genres)}}
                    <p><strong>Tous les films / titres visibles pour cet acteur:</strong></p>
                    ${{renderPills(data.titles)}}
                `;
            }}

            function showEdgeDetails(edgeId) {{
                const data = edgeDetails[edgeId];
                if (!data) {{
                    return;
                }}
                detailBox.innerHTML = `
                    <h4>${{escapeHtml(data.leftName)}} <span class="muted">&lt;-&gt;</span> ${{escapeHtml(data.rightName)}}</h4>
                    <p><strong>Acteur gauche:</strong> ${{escapeHtml(data.leftId)}}</p>
                    <p><strong>Acteur droit:</strong> ${{escapeHtml(data.rightId)}}</p>
                    <p><strong>Poids du lien:</strong> ${{escapeHtml(data.weight)}}</p>
                    <p><strong>Films / projets en commun:</strong> ${{escapeHtml(data.commonTitlesCount)}}</p>
                    <p><strong>Groupe gauche:</strong> ${{escapeHtml(data.leftGroup)}}</p>
                    <p><strong>Groupe droit:</strong> ${{escapeHtml(data.rightGroup)}}</p>
                    <p><strong>Profession gauche:</strong> ${{escapeHtml(data.leftProfession || "n/a")}}</p>
                    <p><strong>Profession droite:</strong> ${{escapeHtml(data.rightProfession || "n/a")}}</p>
                    <p><strong>Genres partages:</strong></p>
                    ${{renderPills(data.genres)}}
                    <p><strong>Tous les films en commun:</strong></p>
                    ${{renderPills(data.titles)}}
                    <p><strong>Tous les titres de l'acteur gauche:</strong></p>
                    ${{renderPills(data.leftTitles)}}
                    <p><strong>Tous les titres de l'acteur droit:</strong></p>
                    ${{renderPills(data.rightTitles)}}
                `;
            }}

            const network = new vis.Network(
                container,
                {{ nodes: nodes, edges: edges }},
                {{
                    autoResize: true,
                    physics: false,
                    interaction: {{
                        hover: true,
                        tooltipDelay: 80,
                        navigationButtons: true,
                        keyboard: true,
                        multiselect: false
                    }},
                    layout: {{
                        improvedLayout: true
                    }},
                    edges: {{
                        selectionWidth: 2.4,
                        smooth: {{
                            enabled: true,
                            type: "dynamic"
                        }}
                    }},
                    nodes: {{
                        borderWidth: 1.4
                    }}
                }}
            );

            network.fit({{ animation: {{ duration: 700, easingFunction: "easeInOutQuad" }} }});

            network.on("click", function(params) {{
                if (params.nodes.length) {{
                    showNodeDetails(params.nodes[0]);
                }} else if (params.edges.length) {{
                    showEdgeDetails(params.edges[0]);
                }}
            }});

            function focusActor() {{
                const query = document.getElementById("actorSearch").value.trim().toLowerCase();
                if (!query) {{
                    return;
                }}
                const actorMatches = nodesData.filter((node) => String(node.actorName || "").toLowerCase().includes(query));
                if (actorMatches.length) {{
                    const match = actorMatches[0];
                    network.selectNodes([match.id]);
                    network.focus(match.id, {{ scale: 1.35, animation: {{ duration: 900, easingFunction: "easeInOutQuad" }} }});
                    showNodeDetails(match.id);
                    return;
                }}

                const titleMatches = nodesData.filter((node) =>
                    (node.searchTitles || []).some((title) => String(title).toLowerCase().includes(query))
                );
                if (!titleMatches.length) {{
                    detailBox.innerHTML = "<h4>Aucun resultat</h4><p class='muted'>Aucun acteur ni aucun titre visible ne correspond a cette recherche. Essayez un nom plus court, un mot du titre, ou elargissez les filtres.</p>";
                    return;
                }}

                const matchedIds = titleMatches.slice(0, 25).map((node) => node.id);
                network.selectNodes(matchedIds);
                network.fit({{
                    nodes: matchedIds,
                    animation: {{ duration: 900, easingFunction: "easeInOutQuad" }}
                }});

                const titleResults = titleMatches.slice(0, 30).map((node) => {{
                    const titles = (node.searchTitles || []).filter((title) => String(title).toLowerCase().includes(query));
                    return `<p><strong>${{escapeHtml(node.actorName)}}</strong><br><span class="muted">${{escapeHtml(node.groupLabel)}}</span></p>${{renderPills(titles)}}`;
                }}).join("");

                detailBox.innerHTML = `
                    <h4>Resultats par titre</h4>
                    <p><strong>Recherche:</strong> ${{escapeHtml(query)}}</p>
                    <p><strong>Acteurs visibles trouves:</strong> ${{escapeHtml(titleMatches.length)}}</p>
                    <p class="muted">Le graphe a ete recentre sur les premiers acteurs visibles qui portent ce titre dans leurs donnees chargees.</p>
                    <div class="detail-list">${{titleResults}}</div>
                `;
            }}

            function toggleEdges() {{
                linksVisible = !linksVisible;
                const updates = edgesData.map((edge) => ({{ id: edge.id, hidden: !linksVisible }}));
                edges.update(updates);
            }}

            function resetView() {{
                network.unselectAll();
                network.fit({{ animation: {{ duration: 650, easingFunction: "easeInOutQuad" }} }});
            }}
        </script>
    </body>
    </html>
    """


def example_group_value(node_data: dict, group_attr: str) -> str:
    value = node_data.get(group_attr, "Autres")
    if isinstance(value, list):
        value = value[0] if value else "Autres"
    return str(value or "Autres")


def grouped_positions_by_attr(subgraph: nx.Graph, group_attr: str, spacing_multiplier: float = 2.0) -> dict[str, tuple[float, float]]:
    if subgraph.number_of_nodes() == 0:
        return {}

    grouped_nodes: dict[str, list[str]] = defaultdict(list)
    for node, data in subgraph.nodes(data=True):
        grouped_nodes[example_group_value(data, group_attr)].append(node)

    ordered_groups = sorted(grouped_nodes, key=lambda value: len(grouped_nodes[value]), reverse=True)
    cols = max(1, math.ceil(math.sqrt(len(ordered_groups))))
    spacing = 11.5 * spacing_multiplier
    positions: dict[str, tuple[float, float]] = {}

    for index, group_name in enumerate(ordered_groups):
        nodes = grouped_nodes[group_name]
        center_x = (index % cols) * spacing
        center_y = -(index // cols) * spacing
        group_graph = subgraph.subgraph(nodes).copy()

        if len(nodes) == 1:
            local_positions = {nodes[0]: (0.0, 0.0)}
        else:
            local_positions = nx.spring_layout(
                group_graph,
                seed=84 + index,
                weight="weight",
                k=max(1.0, 2.8 / max(math.sqrt(len(nodes)), 1)),
            )

        scale = (2.6 + min(len(nodes), 50) / 14) * spacing_multiplier
        for node, (x_value, y_value) in local_positions.items():
            positions[node] = (center_x + x_value * scale, center_y + y_value * scale)

    return positions


def browser_network_example_html(
    graph: nx.Graph,
    title: str,
    subtitle: str,
    max_nodes: int,
    group_attr: str,
    default_color: str,
    list_field: str = "titlesList",
    list_label: str = "Titres",
    edge_list_field: str = "titles",
    edge_list_label: str = "Elements en commun",
    color_attr: str | None = None,
    color_map: dict[str, str] | None = None,
) -> str:
    if graph.number_of_nodes() == 0:
        return """
        <div style="padding:2rem;border:1px solid #cbd5e1;border-radius:20px;background:white;color:#0f172a;">
            Aucun reseau disponible pour cette vue.
        </div>
        """

    weighted_degree = dict(graph.degree(weight="weight"))
    selected_nodes = sorted(graph.nodes(), key=lambda node: weighted_degree.get(node, 0), reverse=True)[:max_nodes]
    subgraph = graph.subgraph(selected_nodes).copy()
    if subgraph.number_of_nodes() == 0:
        return """
        <div style="padding:2rem;border:1px solid #cbd5e1;border-radius:20px;background:white;color:#0f172a;">
            Aucun reseau disponible pour cette vue.
        </div>
        """

    positions = grouped_positions_by_attr(subgraph, group_attr=group_attr, spacing_multiplier=2.1)
    group_names = sorted({example_group_value(data, group_attr) for _, data in subgraph.nodes(data=True)})
    if color_map:
        group_color_map = {group_name: color_map.get(group_name, default_color) for group_name in group_names}
    else:
        group_color_map = {
            group_name: COMMUNITY_COLORS[index % len(COMMUNITY_COLORS)]
            for index, group_name in enumerate(group_names)
        }

    nodes_payload = []
    node_details = {}
    ranked_nodes = sorted(subgraph.nodes(data=True), key=lambda item: weighted_degree.get(item[0], 0), reverse=True)
    for rank, (node, data) in enumerate(ranked_nodes, start=1):
        group_value = example_group_value(data, group_attr)
        node_name = data.get("label", node)
        x_value, y_value = positions.get(node, (0.0, 0.0))
        node_color = default_color
        if color_attr and color_map:
            node_color = color_map.get(str(data.get(color_attr, "")), default_color)
        elif group_color_map:
            node_color = group_color_map.get(group_value, default_color)
        label_value = node_name if rank <= 16 else ""
        nodes_payload.append(
            {
                "id": node,
                "label": label_value,
                "nodeName": node_name,
                "x": round(x_value * 150, 3),
                "y": round(y_value * 150, 3),
                "groupLabel": group_value,
                "size": max(10, min(28, 9 + weighted_degree.get(node, 0) * 0.45)),
                "shape": "dot",
                "color": {"background": node_color, "border": "rgba(15, 23, 42, 0.35)", "highlight": {"background": "#f97316", "border": "#111827"}},
                "font": {"size": 16 if label_value else 1, "face": "Segoe UI", "color": "#0f172a"},
            }
        )
        node_details[node] = {
            "nodeName": node_name,
            "nodeId": node,
            "groupLabel": group_value,
            "type": data.get("role", ""),
            "genre": data.get("mainGenre", "Unknown"),
            "projects": int(data.get("projects", 0)),
            "degree": int(data.get("degree", 0)),
            "weightedDegree": int(subgraph.degree(node, weight="weight")),
            "items": data.get(list_field, []),
        }

    edges_payload = []
    edge_details = {}
    for left, right, data in subgraph.edges(data=True):
        edge_id = f"{left}__{right}"
        detail_items = data.get(edge_list_field, [])
        edges_payload.append(
            {
                "id": edge_id,
                "from": left,
                "to": right,
                "width": max(1.0, min(6.0, 1.0 + math.log1p(max(data.get("weight", 1), 1)) * 1.7)),
                "color": {"color": "rgba(37, 99, 235, 0.30)", "highlight": "#0f172a"},
                "smooth": {"enabled": True, "type": "dynamic"},
            }
        )
        edge_details[edge_id] = {
            "leftName": subgraph.nodes[left].get("label", left),
            "rightName": subgraph.nodes[right].get("label", right),
            "weight": int(data.get("weight", 1)),
            "groupLeft": example_group_value(subgraph.nodes[left], group_attr),
            "groupRight": example_group_value(subgraph.nodes[right], group_attr),
            "items": detail_items,
        }

    legend_html = "".join(
        f"<span class='legend-chip'><span class='legend-dot' style='background:{group_color_map[group_name]}'></span>{html.escape(group_name)}</span>"
        for group_name in group_names[:16]
    )
    if len(group_names) > 16:
        legend_html += f"<span class='legend-chip'>+ {len(group_names) - 16} groupes</span>"

    suggestion_values = "".join(
        f"<option value=\"{html.escape(data['nodeName'])}\"></option>"
        for data in nodes_payload[:300]
    )

    nodes_json = json.dumps(nodes_payload, ensure_ascii=True)
    edges_json = json.dumps(edges_payload, ensure_ascii=True)
    node_details_json = json.dumps(node_details, ensure_ascii=True)
    edge_details_json = json.dumps(edge_details, ensure_ascii=True)

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css"/>
        <style>
            body {{
                margin: 0;
                background: transparent;
                font-family: "Segoe UI", Arial, sans-serif;
                color: #0f172a;
            }}
            .graph-shell {{
                background: white;
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 22px;
                box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
                overflow: hidden;
            }}
            .toolbar {{
                background: linear-gradient(135deg, #0f766e 0%, #0f9f74 55%, #2563eb 100%);
                color: white;
                padding: 16px 18px 14px 18px;
            }}
            .toolbar h3 {{
                margin: 0 0 5px 0;
                font-size: 22px;
            }}
            .toolbar p {{
                margin: 0 0 10px 0;
                font-size: 13px;
                opacity: 0.92;
            }}
            .toolbar-row {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                align-items: center;
            }}
            .toolbar input {{
                flex: 1 1 260px;
                min-width: 200px;
                border: none;
                border-radius: 12px;
                padding: 11px 13px;
                font-size: 14px;
            }}
            .toolbar button {{
                border: none;
                border-radius: 12px;
                padding: 11px 13px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                background: #082f49;
                color: white;
            }}
            .toolbar button.secondary {{
                background: rgba(255, 255, 255, 0.16);
            }}
            .stats-strip {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 12px;
            }}
            .stat-chip {{
                background: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 999px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            .legend {{
                padding: 12px 18px;
                border-bottom: 1px solid rgba(148, 163, 184, 0.20);
                background: #f8fafc;
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }}
            .legend-chip {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: white;
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            .legend-dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
                display: inline-block;
            }}
            .graph-grid {{
                display: grid;
                grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr);
                min-height: 680px;
            }}
            #example-network {{
                width: 100%;
                height: 680px;
                background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            }}
            .details-panel {{
                border-left: 1px solid rgba(148, 163, 184, 0.22);
                background: #fbfdff;
                padding: 18px;
                overflow-y: auto;
            }}
            .details-panel h4 {{
                margin: 0 0 10px 0;
                font-size: 20px;
            }}
            .details-panel p {{
                margin: 4px 0;
                font-size: 14px;
                line-height: 1.45;
            }}
            .details-panel .muted {{
                color: #475569;
            }}
            .detail-list {{
                margin-top: 10px;
                max-height: 220px;
                overflow-y: auto;
                padding-right: 6px;
                border-top: 1px solid rgba(148, 163, 184, 0.18);
                padding-top: 10px;
            }}
            .detail-pill {{
                display: inline-block;
                background: #e8f2ff;
                color: #0f172a;
                border: 1px solid rgba(59, 130, 246, 0.18);
                border-radius: 999px;
                padding: 5px 9px;
                margin: 0 6px 6px 0;
                font-size: 12px;
            }}
            @media (max-width: 1100px) {{
                .graph-grid {{
                    grid-template-columns: 1fr;
                }}
                .details-panel {{
                    border-left: none;
                    border-top: 1px solid rgba(148, 163, 184, 0.22);
                }}
            }}
        </style>
    </head>
    <body>
        <div class="graph-shell">
            <div class="toolbar">
                <h3>{html.escape(title)}</h3>
                <p>{html.escape(subtitle)}</p>
                <div class="toolbar-row">
                    <input id="exampleSearch" list="exampleSuggestions" placeholder="Rechercher un sommet visible..." />
                    <datalist id="exampleSuggestions">{suggestion_values}</datalist>
                    <button onclick="focusNode()">Rechercher</button>
                    <button class="secondary" onclick="toggleEdges()">Afficher / masquer les liens</button>
                    <button class="secondary" onclick="resetView()">Recentrer</button>
                </div>
                <div class="stats-strip">
                    <div class="stat-chip">{subgraph.number_of_nodes()} sommets</div>
                    <div class="stat-chip">{subgraph.number_of_edges()} aretes</div>
                    <div class="stat-chip">{len(group_names)} groupes</div>
                    <div class="stat-chip">Lecture: {html.escape(group_attr)}</div>
                </div>
            </div>
            <div class="legend">{legend_html}</div>
            <div class="graph-grid">
                <div id="example-network"></div>
                <aside class="details-panel">
                    <div id="detailsContent">
                        <h4>Lecture du reseau</h4>
                        <p class="muted">Cliquez un sommet pour voir ses informations.</p>
                        <p class="muted">Cliquez un lien pour voir ce que deux sommets partagent.</p>
                    </div>
                </aside>
            </div>
        </div>
        <script>
            const nodesData = {nodes_json};
            const edgesData = {edges_json};
            const nodeDetails = {node_details_json};
            const edgeDetails = {edge_details_json};
            const nodes = new vis.DataSet(nodesData);
            const edges = new vis.DataSet(edgesData);
            const container = document.getElementById("example-network");
            const detailBox = document.getElementById("detailsContent");
            let linksVisible = true;

            function escapeHtml(value) {{
                return String(value ?? "")
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }}

            function renderPills(values) {{
                if (!values || !values.length) {{
                    return "<p class='muted'>n/a</p>";
                }}
                return "<div class='detail-list'>" + values.map((value) => "<span class='detail-pill'>" + escapeHtml(value) + "</span>").join("") + "</div>";
            }}

            function showNodeDetails(nodeId) {{
                const data = nodeDetails[nodeId];
                if (!data) return;
                detailBox.innerHTML = `
                    <h4>${{escapeHtml(data.nodeName)}}</h4>
                    <p><strong>ID:</strong> ${{escapeHtml(data.nodeId)}}</p>
                    <p><strong>Groupe:</strong> ${{escapeHtml(data.groupLabel)}}</p>
                    <p><strong>Type:</strong> ${{escapeHtml(data.type || "n/a")}}</p>
                    <p><strong>Genre principal:</strong> ${{escapeHtml(data.genre || "Unknown")}}</p>
                    <p><strong>Liens uniques:</strong> ${{escapeHtml(data.degree)}}</p>
                    <p><strong>Poids total:</strong> ${{escapeHtml(data.weightedDegree)}}</p>
                    <p><strong>Projets:</strong> ${{escapeHtml(data.projects)}}</p>
                    <p><strong>{html.escape(list_label)}:</strong></p>
                    ${{renderPills(data.items)}}
                `;
            }}

            function showEdgeDetails(edgeId) {{
                const data = edgeDetails[edgeId];
                if (!data) return;
                detailBox.innerHTML = `
                    <h4>${{escapeHtml(data.leftName)}} <span class="muted"><-></span> ${{escapeHtml(data.rightName)}}</h4>
                    <p><strong>Poids du lien:</strong> ${{escapeHtml(data.weight)}}</p>
                    <p><strong>Gauche:</strong> ${{escapeHtml(data.groupLeft)}}</p>
                    <p><strong>Droite:</strong> ${{escapeHtml(data.groupRight)}}</p>
                    <p><strong>{html.escape(edge_list_label)}:</strong></p>
                    ${{renderPills(data.items)}}
                `;
            }}

            const network = new vis.Network(
                container,
                {{ nodes, edges }},
                {{
                    physics: false,
                    interaction: {{
                        hover: true,
                        tooltipDelay: 80,
                        navigationButtons: true,
                        keyboard: true,
                        multiselect: false
                    }},
                    layout: {{
                        improvedLayout: true
                    }},
                    edges: {{
                        selectionWidth: 2.4,
                        smooth: {{
                            enabled: true,
                            type: "dynamic"
                        }}
                    }},
                    nodes: {{
                        borderWidth: 1.4
                    }}
                }}
            );

            network.fit({{ animation: {{ duration: 700, easingFunction: "easeInOutQuad" }} }});

            network.on("click", function(params) {{
                if (params.nodes.length) {{
                    showNodeDetails(params.nodes[0]);
                }} else if (params.edges.length) {{
                    showEdgeDetails(params.edges[0]);
                }}
            }});

            function focusNode() {{
                const query = document.getElementById("exampleSearch").value.trim().toLowerCase();
                if (!query) return;
                const matches = nodesData.filter((node) => String(node.nodeName || "").toLowerCase().includes(query));
                if (!matches.length) {{
                    detailBox.innerHTML = "<h4>Aucun resultat</h4><p class='muted'>Aucun sommet visible ne correspond a cette recherche.</p>";
                    return;
                }}
                const match = matches[0];
                network.selectNodes([match.id]);
                network.focus(match.id, {{ scale: 1.35, animation: {{ duration: 900, easingFunction: "easeInOutQuad" }} }});
                showNodeDetails(match.id);
            }}

            function toggleEdges() {{
                linksVisible = !linksVisible;
                const updates = edgesData.map((edge) => ({{ id: edge.id, hidden: !linksVisible }}));
                edges.update(updates);
            }}

            function resetView() {{
                network.unselectAll();
                network.fit({{ animation: {{ duration: 650, easingFunction: "easeInOutQuad" }} }});
            }}
        </script>
    </body>
    </html>
    """


def shortest_actor_path_rows(subgraph: nx.Graph, source: str, target: str) -> tuple[list[str], pd.DataFrame]:
    if not source or not target or source == target:
        return [], pd.DataFrame()
    if source not in subgraph or target not in subgraph:
        return [], pd.DataFrame()

    distance_graph = subgraph.copy()
    for left, right, data in distance_graph.edges(data=True):
        data["distance"] = 1 / max(data.get("weight", 1), 1)

    try:
        path = nx.shortest_path(distance_graph, source=source, target=target, weight="distance")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], pd.DataFrame()

    rows = []
    for index, actor_id in enumerate(path):
        node_data = subgraph.nodes[actor_id]
        rows.append(
            {
                "ordre": index + 1,
                "acteur": node_data.get("label", actor_id),
                "id_imdb": actor_id,
                "communaute": node_data.get("community", 0),
                "pays": node_data.get("country", "Unknown"),
                "genre_principal": node_data.get("mainGenre", "Unknown"),
            }
        )
    return path, pd.DataFrame(rows)


def actor_network_detail_figure(
    graph: nx.Graph,
    group_by: str,
    selected_groups: list[str],
    edge_filter_mode: str,
    min_edge_weight: int,
    max_nodes: int,
    max_edges: int,
    show_labels: bool,
    spacing_multiplier: float,
) -> tuple[go.Figure, dict]:
    fig = go.Figure()
    if graph.number_of_nodes() == 0:
        fig.update_layout(title="Graphe acteurs detaille", height=720)
        return fig, {"nodes": 0, "edges_total": 0, "edges_shown": 0, "groups": 0}

    selected_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if not selected_groups or actor_group_value(data, group_by) in selected_groups
    ]
    if len(selected_nodes) > max_nodes:
        weighted_degree = dict(graph.degree(weight="weight"))
        selected_nodes = sorted(
            selected_nodes,
            key=lambda node: weighted_degree.get(node, 0),
            reverse=True,
        )[:max_nodes]
    subgraph = graph.subgraph(selected_nodes).copy()

    edge_filter_mode = edge_filter_mode.strip()
    if edge_filter_mode != "Tous les liens":
        removable_by_mode = []
        for left, right, _ in subgraph.edges(data=True):
            left_data = subgraph.nodes[left]
            right_data = subgraph.nodes[right]
            same_community = left_data.get("community") == right_data.get("community")
            same_genre = left_data.get("mainGenre", "Unknown") == right_data.get("mainGenre", "Unknown")
            same_country = left_data.get("mainRegion", "Unknown") == right_data.get("mainRegion", "Unknown")
            remove = False
            if edge_filter_mode == "Liens meme communaute" and not same_community:
                remove = True
            elif edge_filter_mode == "Liens meme genre" and not same_genre:
                remove = True
            elif edge_filter_mode == "Liens meme pays" and not same_country:
                remove = True
            if remove:
                removable_by_mode.append((left, right))
        subgraph.remove_edges_from(removable_by_mode)

    removable_edges = [
        (left, right)
        for left, right, data in subgraph.edges(data=True)
        if data.get("weight", 1) < min_edge_weight
    ]
    subgraph.remove_edges_from(removable_edges)
    subgraph.remove_nodes_from(list(nx.isolates(subgraph)))

    if subgraph.number_of_nodes() == 0:
        fig.update_layout(title="Graphe acteurs detaille", height=720)
        return fig, {"nodes": 0, "edges_total": 0, "edges_shown": 0, "groups": 0}

    total_edges = subgraph.number_of_edges()
    if total_edges > max_edges:
        ranked_edges = sorted(
            subgraph.edges(data=True),
            key=lambda item: item[2].get("weight", 1),
            reverse=True,
        )[:max_edges]
        allowed_pairs = {(left, right) for left, right, _ in ranked_edges}
        trimmed = nx.Graph()
        trimmed.add_nodes_from(subgraph.nodes(data=True))
        for left, right, data in ranked_edges:
            trimmed.add_edge(left, right, **data)
        trimmed.remove_nodes_from(list(nx.isolates(trimmed)))
        subgraph = trimmed
    shown_edges = subgraph.number_of_edges()

    positions = grouped_network_positions(subgraph, group_by, spacing_multiplier)
    group_names = sorted({actor_group_value(data, group_by) for _, data in subgraph.nodes(data=True)})
    group_color_map = {
        group_name: COMMUNITY_COLORS[index % len(COMMUNITY_COLORS)]
        for index, group_name in enumerate(group_names)
    }

    edge_x = []
    edge_y = []
    edge_mid_x = []
    edge_mid_y = []
    edge_text = []
    for left, right, data in subgraph.edges(data=True):
        x0, y0 = positions[left]
        x1, y1 = positions[right]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_mid_x.append((x0 + x1) / 2)
        edge_mid_y.append((y0 + y1) / 2)
        titles = data.get("titles", [])
        edge_text.append(
            f"{subgraph.nodes[left].get('label', left)} <-> {subgraph.nodes[right].get('label', right)}"
            f"<br>Films en commun: {len(titles)}"
            f"<br>Liste films: {'<br>'.join(html.escape(title) for title in titles[:80])}"
        )

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"color": "rgba(37, 99, 235, 0.22)", "width": 1.2},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    if edge_mid_x:
        fig.add_trace(
            go.Scattergl(
                x=edge_mid_x,
                y=edge_mid_y,
                mode="markers",
                marker={"size": 8, "color": "rgba(37, 99, 235, 0.12)"},
                customdata=edge_text,
                hovertemplate="%{customdata}<extra>Lien acteurs</extra>",
                showlegend=False,
            )
        )

    node_x = []
    node_y = []
    node_size = []
    node_color = []
    node_text = []
    node_labels = []
    degree_map = dict(subgraph.degree())
    weighted_degree_map = dict(subgraph.degree(weight="weight"))
    for node, data in subgraph.nodes(data=True):
        x_value, y_value = positions[node]
        node_x.append(x_value)
        node_y.append(y_value)
        node_size.append(7 + min(weighted_degree_map.get(node, 0) * 1.2, 18))
        group_value = actor_group_value(data, group_by)
        node_color.append(group_color_map[group_value])
        node_labels.append(data.get("label", node)[:18] if show_labels else "")
        node_text.append(
            f"{html.escape(data.get('label', node))}"
            f"<br>Groupe: {html.escape(group_value)}"
            f"<br>Collaborateurs: {degree_map.get(node, 0)}"
            f"<br>Poids total: {weighted_degree_map.get(node, 0)}"
            f"<br>Pays: {html.escape(join_list(data.get('regions', []), limit=4))}"
            f"<br>Genres: {html.escape(join_list(data.get('dominantGenres', []), limit=4))}"
            f"<br>Films: {'<br>'.join(html.escape(title) for title in data.get('titlesList', [])[:50])}"
        )

    fig.add_trace(
        go.Scattergl(
            x=node_x,
            y=node_y,
            mode="markers+text" if show_labels else "markers",
            text=node_labels,
            textposition="top center",
            marker={
                "size": node_size,
                "color": node_color,
                "line": {"color": "white", "width": 0.7},
                "opacity": 0.92,
            },
            customdata=node_text,
            hovertemplate="%{customdata}<extra>Acteur</extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        title=f"Graphe acteurs detaille - regroupement par {group_by.lower()}",
        height=780,
        margin={"l": 10, "r": 10, "t": 55, "b": 10},
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
    )
    return fig, {
        "nodes": subgraph.number_of_nodes(),
        "edges_total": total_edges,
        "edges_shown": shown_edges,
        "groups": len(group_names),
    }


def community_summary_table(_graph: nx.Graph, actor_rows: pd.DataFrame) -> pd.DataFrame:
    graph = _graph
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())].copy()
    rows["community"] = rows["nconst"].map(nx.get_node_attributes(graph, "community"))
    degree_map = dict(graph.degree())
    name_map = {node: data.get("label", node) for node, data in graph.nodes(data=True)}

    result = []
    for community_id, group in rows.groupby("community"):
        actors = sorted(set(group["nconst"]))
        top_actor = max(actors, key=lambda actor_id: degree_map.get(actor_id, 0)) if actors else None
        result.append(
            {
                "communaute": int(community_id),
                "acteurs": len(actors),
                "titres": int(group["tconst"].nunique()),
                "regions": int(group["region"].nunique()),
                "genre_dominant": top_genres_text(group["genresList"], limit=1),
                "genres_principaux": top_genres_text(group["genresList"], limit=4),
                "acteur_central": name_map.get(top_actor, "n/a"),
            }
        )
    table = pd.DataFrame(result)
    if table.empty:
        return table
    return table.sort_values(["acteurs", "titres"], ascending=False)


def genre_leaders_table(actor_rows: pd.DataFrame) -> pd.DataFrame:
    rows = (
        actor_rows[["tconst", "nconst", "primaryName", "genresList"]]
        .drop_duplicates(subset=["tconst", "nconst"])
        .explode("genresList")
    )
    rows = rows[rows["genresList"].notna() & rows["genresList"].ne("Unknown")]
    if rows.empty:
        return pd.DataFrame()

    collaborator_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for (genre, title_id), group in rows.groupby(["genresList", "tconst"]):
        actor_ids = group["nconst"].drop_duplicates().tolist()
        for left, right in combinations(actor_ids, 2):
            collaborator_map[(genre, left)].add(right)
            collaborator_map[(genre, right)].add(left)

    actor_name_map = rows.drop_duplicates("nconst").set_index("nconst")["primaryName"].to_dict()
    title_counts = rows.groupby(["genresList", "nconst"])["tconst"].nunique().to_dict()
    result = []
    for genre in sorted(rows["genresList"].unique()):
        genre_actor_ids = sorted(rows.loc[rows["genresList"] == genre, "nconst"].unique().tolist())
        if not genre_actor_ids:
            continue
        leader = max(
            genre_actor_ids,
            key=lambda actor_id: (
                len(collaborator_map.get((genre, actor_id), set())),
                title_counts.get((genre, actor_id), 0),
            ),
        )
        result.append(
            {
                "genre": genre,
                "acteur_dominant": actor_name_map.get(leader, leader),
                "collaborateurs_dans_genre": len(collaborator_map.get((genre, leader), set())),
                "titres_dans_genre": int(title_counts.get((genre, leader), 0)),
            }
        )
    table = pd.DataFrame(result)
    if table.empty:
        return table
    return table.sort_values(["collaborateurs_dans_genre", "titres_dans_genre"], ascending=False)


def prepare_region_overview(_graph: nx.Graph, actor_rows: pd.DataFrame, selected_community: str) -> pd.DataFrame:
    graph = _graph
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())].copy()
    rows["community"] = rows["nconst"].map(nx.get_node_attributes(graph, "community"))
    if selected_community != "Toutes":
        rows = rows[rows["community"] == int(selected_community)]

    degree_map = dict(graph.degree())
    result = []
    for region_code, group in rows.groupby("region"):
        actor_ids = sorted(set(group["nconst"]))
        top_actor = max(actor_ids, key=lambda actor_id: degree_map.get(actor_id, 0)) if actor_ids else None
        top_actor_name = graph.nodes[top_actor]["label"] if top_actor in graph.nodes else "n/a"
        top_actor_degree = degree_map.get(top_actor, 0) if top_actor else 0
        result.append(
            {
                "region": region_code,
                "region_name": group["regionName"].iloc[0],
                "lat": float(group["lat"].iloc[0]),
                "lon": float(group["lon"].iloc[0]),
                "actors": len(actor_ids),
                "titles": int(group["tconst"].nunique()),
                "communities": int(group["community"].nunique()),
                "dominant_genres": top_genres_text(group["genresList"], limit=4),
                "top_actor": top_actor_name,
                "top_actor_degree": int(top_actor_degree),
                "all_actors": group["primaryName"].drop_duplicates().tolist(),
                "all_titles": group["titleLabel"].drop_duplicates().tolist(),
            }
        )
    table = pd.DataFrame(result)
    if table.empty:
        return table
    return table.sort_values(["actors", "titles"], ascending=False)


def prepare_region_community_points(_graph: nx.Graph, actor_rows: pd.DataFrame, selected_community: str) -> pd.DataFrame:
    graph = _graph
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())].copy()
    rows["community"] = rows["nconst"].map(nx.get_node_attributes(graph, "community"))
    if selected_community != "Toutes":
        rows = rows[rows["community"] == int(selected_community)]

    degree_map = dict(graph.degree())
    result = []
    for (region_code, community_id), group in rows.groupby(["region", "community"]):
        actor_ids = sorted(set(group["nconst"]))
        top_actor = max(actor_ids, key=lambda actor_id: degree_map.get(actor_id, 0)) if actor_ids else None
        result.append(
            {
                "region": region_code,
                "region_name": group["regionName"].iloc[0],
                "lat": float(group["lat"].iloc[0]),
                "lon": float(group["lon"].iloc[0]),
                "community": int(community_id),
                "actors": len(actor_ids),
                "titles": int(group["tconst"].nunique()),
                "dominant_genres": top_genres_text(group["genresList"], limit=3),
                "top_actor": graph.nodes[top_actor]["label"] if top_actor in graph.nodes else "n/a",
                "all_actors": group["primaryName"].drop_duplicates().tolist(),
                "all_titles": group["titleLabel"].drop_duplicates().tolist(),
            }
        )
    table = pd.DataFrame(result)
    if table.empty:
        return table
    return table.sort_values(["actors", "titles"], ascending=False)


def prepare_title_points(
    filtered_data: pd.DataFrame,
    selected_community: str,
    graph: nx.Graph,
    limit: int | None = None,
) -> pd.DataFrame:
    actor_rows = filtered_data[filtered_data["category"].isin(ACTOR_CATEGORIES)].copy()
    actor_rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())]
    actor_rows["community"] = actor_rows["nconst"].map(nx.get_node_attributes(graph, "community"))
    if selected_community != "Toutes":
        actor_rows = actor_rows[actor_rows["community"] == int(selected_community)]

    title_rows = actor_rows[
        [
            "tconst",
            "titleLabel",
            "primaryTitle",
            "startYearInt",
            "titleType",
            "region",
            "regionName",
            "lat",
            "lon",
            "genresList",
            "averageRating",
            "numVotes",
        ]
    ].drop_duplicates("tconst")
    if title_rows.empty:
        return title_rows

    cast_map = actor_rows.groupby("tconst")["primaryName"].apply(lambda values: values.drop_duplicates().tolist()).to_dict()
    community_map = (
        actor_rows.groupby("tconst")["community"]
        .apply(lambda values: Counter(values.dropna()).most_common(1)[0][0] if len(values.dropna()) else 0)
        .to_dict()
    )
    title_rows = title_rows.copy()
    title_rows["cast_list"] = title_rows["tconst"].map(cast_map).apply(lambda value: value if isinstance(value, list) else [])
    title_rows["dominant_community"] = title_rows["tconst"].map(community_map).fillna(0).astype(int)
    title_rows["genres_text"] = title_rows["genresList"].apply(lambda values: join_list(values, limit=4))
    title_rows = title_rows.sort_values(["numVotes", "averageRating", "titleLabel"], ascending=[False, False, True])
    if limit is not None:
        title_rows = title_rows.head(limit)
    return title_rows


def build_region_links(_graph: nx.Graph, actor_rows: pd.DataFrame, link_basis: str, selected_community: str) -> pd.DataFrame:
    graph = _graph
    if graph.number_of_edges() == 0:
        return pd.DataFrame()

    actor_rows = actor_rows[actor_rows["nconst"].isin(graph.nodes())].copy()
    community_map = nx.get_node_attributes(graph, "community")
    actor_region_map = actor_rows.groupby("nconst")["region"].apply(lambda values: sorted(set(values.dropna()))).to_dict()
    actor_genre_map = (
        actor_rows[["nconst", "genresList"]]
        .explode("genresList")
        .groupby("nconst")["genresList"]
        .apply(lambda values: {genre for genre in values if genre and genre != "Unknown"})
        .to_dict()
    )
    actor_name_map = actor_rows.groupby("nconst")["primaryName"].first().to_dict()
    allowed_nodes = set(graph.nodes())
    if selected_community != "Toutes":
        community_value = int(selected_community)
        allowed_nodes = {node for node in allowed_nodes if community_map.get(node) == community_value}

    aggregate: dict[tuple[str, str], dict] = {}
    for left, right, data in graph.edges(data=True):
        if left not in allowed_nodes or right not in allowed_nodes:
            continue

        shared_genres = sorted(actor_genre_map.get(left, set()).intersection(actor_genre_map.get(right, set())))
        same_community = community_map.get(left) == community_map.get(right)
        if link_basis == "Titres communs":
            include = len(data.get("titles", [])) > 0
        elif link_basis == "Genres communs":
            include = len(shared_genres) > 0
        else:
            include = same_community

        if not include:
            continue

        for region_left in actor_region_map.get(left, []):
            for region_right in actor_region_map.get(right, []):
                if region_left == region_right:
                    continue
                pair = tuple(sorted((region_left, region_right)))
                bucket = aggregate.setdefault(
                    pair,
                    {
                        "actor_pairs": 0,
                        "titles": set(),
                        "genres": Counter(),
                        "communities": Counter(),
                        "examples": [],
                    },
                )
                bucket["actor_pairs"] += 1
                bucket["titles"].update(data.get("titles", []))
                bucket["genres"].update(shared_genres)
                bucket["communities"].update([community_map.get(left, 0)])
                bucket["examples"].append(f"{actor_name_map.get(left, left)} - {actor_name_map.get(right, right)}")

    rows = []
    for (region_left, region_right), data in aggregate.items():
        if region_left not in REGION_COORDS or region_right not in REGION_COORDS:
            continue
        rows.append(
            {
                "region_left": region_left,
                "region_left_name": region_name(region_left),
                "lat_left": REGION_COORDS[region_left][0],
                "lon_left": REGION_COORDS[region_left][1],
                "region_right": region_right,
                "region_right_name": region_name(region_right),
                "lat_right": REGION_COORDS[region_right][0],
                "lon_right": REGION_COORDS[region_right][1],
                "common_titles_count": int(len(data["titles"])),
                "actor_pairs": int(data["actor_pairs"]),
                "dominant_genres": ", ".join(genre for genre, _ in data["genres"].most_common(4)) or "n/a",
                "communities": ", ".join(str(value) for value, _ in data["communities"].most_common(4)) or "n/a",
                "examples": join_list(list(dict.fromkeys(data["examples"])), limit=5),
                "titles_list": sorted(data["titles"]),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["common_titles_count", "actor_pairs"], ascending=False)


def prepare_actor_map_points(
    _graph: nx.Graph,
    group_by: str,
    selected_groups: list[str],
    max_nodes: int,
) -> pd.DataFrame:
    graph = _graph
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    weighted_degree = dict(graph.degree(weight="weight"))
    rows = []
    for node, data in graph.nodes(data=True):
        group_value = actor_group_value(data, group_by)
        if selected_groups and group_value not in selected_groups:
            continue
        region_code = data.get("regionCodes", ["XWW"])[0] if data.get("regionCodes") else "XWW"
        lat_base, lon_base = REGION_COORDS.get(region_code, REGION_COORDS["XWW"])
        lat_value, lon_value = jitter_coordinates(lat_base, lon_base, node, max_offset=0.55)
        rows.append(
            {
                "actor_id": node,
                "actor_name": data.get("label", node),
                "group_value": group_value,
                "community": int(data.get("community", 0)),
                "role": data.get("role", ""),
                "profession": data.get("profession", ""),
                "main_region": data.get("mainRegion", "Unknown"),
                "main_genre": data.get("mainGenre", "Unknown"),
                "lat": lat_value,
                "lon": lon_value,
                "degree": int(data.get("degree", 0)),
                "weighted_degree": int(weighted_degree.get(node, 0)),
                "projects": int(data.get("projects", 0)),
                "titles_list": data.get("titlesList", []),
                "regions": data.get("regions", []),
                "genres": data.get("dominantGenres", []),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["weighted_degree", "degree", "projects"], ascending=False).head(max_nodes)


def build_actor_map_links(
    _graph: nx.Graph,
    actor_points: pd.DataFrame,
    link_mode: str,
    max_links: int,
) -> pd.DataFrame:
    graph = _graph
    if graph.number_of_edges() == 0 or actor_points.empty:
        return pd.DataFrame()

    visible_nodes = set(actor_points["actor_id"])
    node_lookup = actor_points.set_index("actor_id").to_dict("index")
    rows = []
    for left, right, data in graph.edges(data=True):
        if left not in visible_nodes or right not in visible_nodes:
            continue

        left_info = node_lookup[left]
        right_info = node_lookup[right]
        include = False
        if link_mode == "Films / projets communs":
            include = len(data.get("titles", [])) > 0
        elif link_mode == "Meme genre":
            include = left_info["main_genre"] == right_info["main_genre"] and left_info["main_genre"] != "Unknown"
        elif link_mode == "Meme profession":
            include = left_info["profession"] == right_info["profession"] and left_info["profession"] != ""
        elif link_mode == "Meme communaute":
            include = left_info["community"] == right_info["community"]
        elif link_mode == "Meme pays":
            include = left_info["main_region"] == right_info["main_region"] and left_info["main_region"] != "Unknown"

        if not include:
            continue

        rows.append(
            {
                "left_id": left,
                "left_name": left_info["actor_name"],
                "left_lat": left_info["lat"],
                "left_lon": left_info["lon"],
                "right_id": right,
                "right_name": right_info["actor_name"],
                "right_lat": right_info["lat"],
                "right_lon": right_info["lon"],
                "common_titles_count": int(len(data.get("titles", []))),
                "titles_list": data.get("titles", []),
                "genres": data.get("genres", []),
                "left_group": left_info["group_value"],
                "right_group": right_info["group_value"],
                "left_role": left_info["role"],
                "right_role": right_info["role"],
                "left_profession": left_info["profession"],
                "right_profession": right_info["profession"],
                "weight": int(data.get("weight", 1)),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["common_titles_count", "weight"], ascending=False).head(max_links)


def create_map(
    region_overview: pd.DataFrame,
    community_points: pd.DataFrame,
    title_points: pd.DataFrame,
    region_links: pd.DataFrame,
    link_basis: str,
    tile_name: str,
    show_regions: bool,
    show_communities: bool,
    show_titles: bool,
    show_links: bool,
    show_heatmap: bool,
    max_lines: int,
) -> folium.Map:
    if region_overview.empty and community_points.empty and title_points.empty:
        return folium.Map(location=[20, 0], zoom_start=2, tiles=tile_name)

    all_latitudes = []
    all_longitudes = []
    for table in [region_overview, community_points, title_points]:
        if not table.empty:
            all_latitudes.extend(table["lat"].tolist())
            all_longitudes.extend(table["lon"].tolist())

    center_lat = sum(all_latitudes) / len(all_latitudes) if all_latitudes else 20
    center_lon = sum(all_longitudes) / len(all_longitudes) if all_longitudes else 0
    result_map = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles=tile_name, control_scale=True)
    Fullscreen().add_to(result_map)
    MiniMap(toggle_display=True).add_to(result_map)

    if show_regions and not region_overview.empty:
        region_group = folium.FeatureGroup(name="Groupage par region", show=True)
        for row in region_overview.itertuples(index=False):
            popup_html = f"""
            <div style="width:300px">
            <strong>{row.region_name}</strong><br>
            Acteurs reliés: {row.actors}<br>
            Titres: {row.titles}<br>
            Communautés: {row.communities}<br>
            Genres dominants: {row.dominant_genres}<br>
            Acteur le plus connecté: {row.top_actor} ({row.top_actor_degree})<br>
            Exemples acteurs: {row.actor_examples}<br>
            Exemples titres: {row.title_examples}
            </div>
            """
            folium.CircleMarker(
                location=[row.lat, row.lon],
                radius=max(8, min(24, 5 + row.actors * 0.55)),
                color="#1d4ed8",
                fill=True,
                fill_color="#60a5fa",
                fill_opacity=0.32,
                weight=2,
                tooltip=f"{row.region_name}: {row.actors} acteurs, {row.titles} titres",
                popup=folium.Popup(popup_html, max_width=360),
            ).add_to(region_group)
        region_group.add_to(result_map)

    if show_communities and not community_points.empty:
        community_group = folium.FeatureGroup(name="Communautes d'acteurs", show=True)
        for row in community_points.itertuples(index=False):
            lat_value, lon_value = jitter_coordinates(row.lat, row.lon, f"{row.region}-{row.community}", max_offset=0.35)
            color = COMMUNITY_COLORS[(row.community - 1) % len(COMMUNITY_COLORS)]
            popup_html = f"""
            <div style="width:300px">
            <strong>{row.region_name}</strong><br>
            Communauté: {row.community}<br>
            Acteurs dans le groupe: {row.actors}<br>
            Titres dans le groupe: {row.titles}<br>
            Genres dominants: {row.dominant_genres}<br>
            Acteur central local: {row.top_actor}<br>
            Exemples acteurs: {row.actor_examples}
            </div>
            """
            folium.CircleMarker(
                location=[lat_value, lon_value],
                radius=max(4, min(12, 3 + row.actors * 0.32)),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.88,
                weight=1,
                tooltip=f"Communaute {row.community} - {row.region_name}",
                popup=folium.Popup(popup_html, max_width=360),
            ).add_to(community_group)
        community_group.add_to(result_map)

    if show_titles and not title_points.empty:
        title_cluster = MarkerCluster(name="Films et series", show=False)
        for row in title_points.itertuples(index=False):
            lat_value, lon_value = jitter_coordinates(row.lat, row.lon, row.tconst, max_offset=0.25)
            popup_html = f"""
            <div style="width:300px">
            <strong>{row.titleLabel}</strong><br>
            Type: {row.titleType}<br>
            Region: {row.regionName}<br>
            Genres: {row.genres_text}<br>
            Note: {row.averageRating:.1f}<br>
            Votes: {int(row.numVotes)}<br>
            Cast visible: {row.cast_examples}
            </div>
            """
            folium.CircleMarker(
                location=[lat_value, lon_value],
                radius=4,
                color="#0f172a",
                fill=True,
                fill_color="#f59e0b",
                fill_opacity=0.8,
                weight=1,
                tooltip=row.titleLabel,
                popup=folium.Popup(popup_html, max_width=340),
            ).add_to(title_cluster)
        title_cluster.add_to(result_map)

    if show_links and not region_links.empty:
        link_group = folium.FeatureGroup(name=f"Liens - {link_basis}", show=True)
        line_color = LINK_COLORS.get(link_basis, "#dc2626")
        visible_links = region_links.head(max_lines)
        for row in visible_links.itertuples(index=False):
            popup_html = f"""
            <div style="width:300px">
            <strong>{row.region_left_name} <-> {row.region_right_name}</strong><br>
            Force du lien: {row.strength}<br>
            Paires d'acteurs: {row.actor_pairs}<br>
            Genres partagés: {row.dominant_genres}<br>
            Communautés: {row.communities}<br>
            Exemples: {row.examples}
            </div>
            """
            folium.PolyLine(
                locations=[[row.lat_left, row.lon_left], [row.lat_right, row.lon_right]],
                color=line_color,
                weight=max(1.5, min(7.0, 1.2 + math.log1p(row.strength) * 1.4)),
                opacity=0.4,
                popup=folium.Popup(popup_html, max_width=360),
                tooltip=f"{row.region_left_name} <-> {row.region_right_name} ({row.strength})",
            ).add_to(link_group)
        link_group.add_to(result_map)

    if show_heatmap and not title_points.empty:
        heat_rows = [[row.lat, row.lon, 1 + max(0, row.numVotes / 10_000)] for row in title_points.itertuples(index=False)]
        HeatMap(heat_rows, name="Carte de chaleur", show=False, radius=26, blur=20).add_to(result_map)

    folium.LayerControl(collapsed=False).add_to(result_map)
    return result_map


def create_map_v2(
    actor_points: pd.DataFrame,
    actor_links: pd.DataFrame,
    region_overview: pd.DataFrame,
    community_points: pd.DataFrame,
    title_points: pd.DataFrame,
    region_links: pd.DataFrame,
    link_basis: str,
    tile_name: str,
    show_regions: bool,
    show_communities: bool,
    show_actor_nodes: bool,
    show_actor_links: bool,
    show_titles: bool,
    show_links: bool,
    show_heatmap: bool,
    max_lines: int,
    max_title_points: int,
) -> folium.Map:
    if actor_points.empty and region_overview.empty and community_points.empty and title_points.empty:
        return folium.Map(location=[20, 0], zoom_start=2, tiles=tile_name)

    all_latitudes = []
    all_longitudes = []
    for table in [actor_points, region_overview, community_points, title_points]:
        if not table.empty:
            all_latitudes.extend(table["lat"].tolist())
            all_longitudes.extend(table["lon"].tolist())

    center_lat = sum(all_latitudes) / len(all_latitudes) if all_latitudes else 20
    center_lon = sum(all_longitudes) / len(all_longitudes) if all_longitudes else 0
    result_map = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles=tile_name, control_scale=True)
    Fullscreen().add_to(result_map)
    MiniMap(toggle_display=True).add_to(result_map)

    if show_actor_nodes and not actor_points.empty:
        actor_group = folium.FeatureGroup(name="Acteurs (1 sommet = 1 acteur)", show=True)
        actor_cluster = MarkerCluster(name="Acteurs clusters", disableClusteringAtZoom=6)
        use_cluster = len(actor_points) > 180
        for row in actor_points.itertuples(index=False):
            popup_html = f"""
            <div style="width:320px">
            <strong>{html.escape(row.actor_name)}</strong><br>
            Groupe: {html.escape(str(row.group_value))}<br>
            Communaute: {row.community}<br>
            Profession: {html.escape(row.role)}<br>
            Pays: {html.escape(row.main_region)}<br>
            Genre principal: {html.escape(row.main_genre)}<br>
            Collaborateurs: {row.degree}<br>
            Poids total: {row.weighted_degree}<br>
            Projets: {row.projects}<br>
            Apercu titres:
            {preview_list_html(row.titles_list, limit=18, max_height=120)}
            </div>
            """
            color = COMMUNITY_COLORS[(row.community - 1) % len(COMMUNITY_COLORS)] if row.community > 0 else "#2563eb"
            marker = folium.CircleMarker(
                location=[row.lat, row.lon],
                radius=max(4, min(9, 4 + row.weighted_degree * 0.10)),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.84,
                weight=1,
                tooltip=f"{row.actor_name} - {row.group_value}",
                popup=folium.Popup(popup_html, max_width=360),
            )
            if use_cluster:
                marker.add_to(actor_cluster)
            else:
                marker.add_to(actor_group)
        if use_cluster:
            actor_cluster.add_to(actor_group)
        actor_group.add_to(result_map)

    if show_actor_links and not actor_links.empty:
        actor_link_group = folium.FeatureGroup(name="Liens acteurs", show=True)
        for row in actor_links.itertuples(index=False):
            popup_html = f"""
            <div style="width:320px">
            <strong>{html.escape(row.left_name)} <-> {html.escape(row.right_name)}</strong><br>
            Films / projets en commun: {row.common_titles_count}<br>
            Groupe gauche: {html.escape(str(row.left_group))}<br>
            Groupe droit: {html.escape(str(row.right_group))}<br>
            Profession gauche: {html.escape(row.left_role)}<br>
            Profession droite: {html.escape(row.right_role)}<br>
            Genres du lien: {html.escape(join_list(row.genres, limit=6))}<br>
            Apercu titres:
            {preview_list_html(row.titles_list, limit=20, max_height=120)}
            </div>
            """
            folium.PolyLine(
                locations=[[row.left_lat, row.left_lon], [row.right_lat, row.right_lon]],
                color="#2563eb",
                weight=max(1.5, min(6.0, 1.5 + math.log1p(max(row.common_titles_count, 1)) * 1.2)),
                opacity=0.52,
                tooltip=f"{row.left_name} <-> {row.right_name} ({row.common_titles_count} films)",
                popup=folium.Popup(popup_html, max_width=380),
            ).add_to(actor_link_group)
        actor_link_group.add_to(result_map)

    if show_regions and not region_overview.empty:
        region_group = folium.FeatureGroup(name="Groupage par region", show=True)
        for row in region_overview.itertuples(index=False):
            popup_html = f"""
            <div style="width:300px">
            <strong>{html.escape(row.region_name)}</strong><br>
            Acteurs relies: {row.actors}<br>
            Titres: {row.titles}<br>
            Communautes: {row.communities}<br>
            Genres dominants: {html.escape(row.dominant_genres)}<br>
            Acteur le plus connecte: {html.escape(row.top_actor)} ({row.top_actor_degree})<br>
            Apercu acteurs:
            {preview_list_html(row.all_actors, limit=20, max_height=90)}<br>
            Apercu titres:
            {preview_list_html(row.all_titles, limit=25, max_height=120)}
            </div>
            """
            folium.CircleMarker(
                location=[row.lat, row.lon],
                radius=max(8, min(24, 5 + row.actors * 0.55)),
                color="#1d4ed8",
                fill=True,
                fill_color="#60a5fa",
                fill_opacity=0.28,
                weight=2,
                tooltip=f"{row.region_name}: {row.actors} acteurs, {row.titles} titres",
                popup=folium.Popup(popup_html, max_width=360),
            ).add_to(region_group)
        region_group.add_to(result_map)

    if show_communities and not community_points.empty:
        community_group = folium.FeatureGroup(name="Communautes d'acteurs", show=True)
        for row in community_points.itertuples(index=False):
            lat_value, lon_value = jitter_coordinates(row.lat, row.lon, f"{row.region}-{row.community}", max_offset=0.35)
            color = COMMUNITY_COLORS[(row.community - 1) % len(COMMUNITY_COLORS)]
            popup_html = f"""
            <div style="width:300px">
            <strong>{html.escape(row.region_name)}</strong><br>
            Communaute: {row.community}<br>
            Acteurs dans le groupe: {row.actors}<br>
            Titres dans le groupe: {row.titles}<br>
            Genres dominants: {html.escape(row.dominant_genres)}<br>
            Acteur central local: {html.escape(row.top_actor)}<br>
            Apercu acteurs:
            {preview_list_html(row.all_actors, limit=16, max_height=90)}<br>
            Apercu titres:
            {preview_list_html(row.all_titles, limit=20, max_height=110)}
            </div>
            """
            folium.CircleMarker(
                location=[lat_value, lon_value],
                radius=max(4, min(12, 3 + row.actors * 0.32)),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                weight=1,
                tooltip=f"Communaute {row.community} - {row.region_name}",
                popup=folium.Popup(popup_html, max_width=360),
            ).add_to(community_group)
        community_group.add_to(result_map)

    if show_titles and not title_points.empty:
        visible_titles = title_points.head(max_title_points).copy()
        if len(visible_titles) > 5000:
            fast_rows = []
            for row in visible_titles.itertuples(index=False):
                lat_value, lon_value = jitter_coordinates(row.lat, row.lon, row.tconst, max_offset=0.25)
                color = COMMUNITY_COLORS[(max(row.dominant_community, 1) - 1) % len(COMMUNITY_COLORS)]
                popup_html = f"""
                <div style="width:300px">
                <strong>{html.escape(row.titleLabel)}</strong><br>
                Type: {html.escape(str(row.titleType))}<br>
                Region: {html.escape(row.regionName)}<br>
                Communaute dominante: {row.dominant_community}<br>
                Genres: {html.escape(row.genres_text)}<br>
                Note: {row.averageRating:.1f}<br>
                Votes: {int(row.numVotes)}<br>
                Tous les acteurs:
                {scroll_list_html(row.cast_list, max_height=120)}
                </div>
                """
                fast_rows.append([lat_value, lon_value, row.titleLabel, color, popup_html])

            callback = """
            function (row) {
                var marker = L.circleMarker(new L.LatLng(row[0], row[1]), {
                    radius: 4,
                    color: row[3],
                    fillColor: row[3],
                    fillOpacity: 0.82,
                    weight: 1
                });
                marker.bindTooltip(row[2]);
                marker.bindPopup(row[4], {maxWidth: 340});
                return marker;
            };
            """
            FastMarkerCluster(data=fast_rows, callback=callback, name="Films et series", show=True).add_to(result_map)
        else:
            title_cluster = MarkerCluster(name="Films et series", show=True)
            for row in visible_titles.itertuples(index=False):
                lat_value, lon_value = jitter_coordinates(row.lat, row.lon, row.tconst, max_offset=0.25)
                color = COMMUNITY_COLORS[(max(row.dominant_community, 1) - 1) % len(COMMUNITY_COLORS)]
                popup_html = f"""
                <div style="width:300px">
                <strong>{html.escape(row.titleLabel)}</strong><br>
                Type: {html.escape(str(row.titleType))}<br>
                Region: {html.escape(row.regionName)}<br>
                Communaute dominante: {row.dominant_community}<br>
                Genres: {html.escape(row.genres_text)}<br>
                Note: {row.averageRating:.1f}<br>
                Votes: {int(row.numVotes)}<br>
                Tous les acteurs:
                {scroll_list_html(row.cast_list, max_height=120)}
                </div>
                """
                folium.CircleMarker(
                    location=[lat_value, lon_value],
                    radius=4,
                    color="#0f172a",
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.82,
                    weight=1,
                    tooltip=row.titleLabel,
                    popup=folium.Popup(popup_html, max_width=340),
                ).add_to(title_cluster)
            title_cluster.add_to(result_map)

    if show_links and not region_links.empty:
        link_group = folium.FeatureGroup(name=f"Liens - {link_basis}", show=True)
        line_color = LINK_COLORS.get(link_basis, "#2563eb")
        visible_links = region_links.head(max_lines)
        for row in visible_links.itertuples(index=False):
            popup_html = f"""
            <div style="width:300px">
            <strong>{html.escape(row.region_left_name)} <-> {html.escape(row.region_right_name)}</strong><br>
            Titres en commun: {row.common_titles_count}<br>
            Paires d'acteurs: {row.actor_pairs}<br>
            Genres partages: {html.escape(row.dominant_genres)}<br>
            Communautes: {html.escape(row.communities)}<br>
            Exemples d'acteurs: {html.escape(row.examples)}<br>
            Tous les titres:
            {scroll_list_html(row.titles_list, max_height=150)}
            </div>
            """
            folium.PolyLine(
                locations=[[row.lat_left, row.lon_left], [row.lat_right, row.lon_right]],
                color=line_color,
                weight=max(2.0, min(8.0, 1.4 + math.log1p(row.common_titles_count) * 1.5)),
                opacity=0.58,
                popup=folium.Popup(popup_html, max_width=360),
                tooltip=f"{row.region_left_name} <-> {row.region_right_name} ({row.common_titles_count} titres)",
            ).add_to(link_group)
        link_group.add_to(result_map)

    if show_heatmap and not title_points.empty:
        heat_rows = [[row.lat, row.lon, 1 + max(0, row.numVotes / 10_000)] for row in title_points.head(max_title_points).itertuples(index=False)]
        HeatMap(heat_rows, name="Carte de chaleur", show=False, radius=26, blur=20).add_to(result_map)

    folium.LayerControl(collapsed=False).add_to(result_map)
    return result_map


@st.cache_data(show_spinner=False)
def render_map_html_cached(
    actor_points: pd.DataFrame,
    actor_links: pd.DataFrame,
    region_overview: pd.DataFrame,
    community_points: pd.DataFrame,
    title_points: pd.DataFrame,
    region_links: pd.DataFrame,
    link_basis: str,
    tile_name: str,
    show_regions: bool,
    show_communities: bool,
    show_actor_nodes: bool,
    show_actor_links: bool,
    show_titles: bool,
    show_links: bool,
    show_heatmap: bool,
    max_lines: int,
    max_title_points: int,
) -> str:
    movie_map = create_map_v2(
        actor_points=actor_points,
        actor_links=actor_links,
        region_overview=region_overview,
        community_points=community_points,
        title_points=title_points,
        region_links=region_links,
        link_basis=link_basis,
        tile_name=tile_name,
        show_regions=show_regions,
        show_communities=show_communities,
        show_actor_nodes=show_actor_nodes,
        show_actor_links=show_actor_links,
        show_titles=show_titles,
        show_links=show_links,
        show_heatmap=show_heatmap,
        max_lines=max_lines,
        max_title_points=max_title_points,
    )
    return movie_map.get_root().render()


st.markdown(
    """
    <div class="hero">
        <div class="hero-top">
            <div>
                <div class="hero-kicker">IMDb Graphes</div>
                <h1>Exploration des acteurs, films et communautes</h1>
                <p>Un espace plus simple pour chercher, comparer et analyser les relations IMDb sans surcharger l'ecran.</p>
            </div>
            <div class="hero-actions">
                <span class="hero-chip">Acteurs <-> acteurs</span>
                <span class="hero-chip">Carte geographique</span>
                <span class="hero-chip">Plus court chemin</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.spinner("Lecture des fichiers TSV et preparation de la carte..."):
    imdb_data, audit = load_imdb_map_data()

available_title_types = sorted(imdb_data["titleType"].dropna().unique().tolist())
available_genres = sorted({genre for genres in imdb_data["genresList"] for genre in genres if genre != "Unknown"})
available_regions = (
    imdb_data[["region", "regionName"]]
    .drop_duplicates()
    .sort_values("regionName")
)

st.caption(f"Donnees chargees: {audit['principals_rows_read']:,} lignes `title.principals.tsv`")
navigation_views = [
    "Graphe interactif acteurs",
    "Carte acteurs",
    "Analyses",
    "Exemples reseau",
    "Synthese projet",
    "Donnees et details",
]
view_param = ""
try:
    view_param = str(st.query_params.get("view", "")).strip()
except Exception:
    view_param = ""
default_view_index = navigation_views.index(view_param) if view_param in navigation_views else 0
active_view = st.radio(
    "Navigation",
    navigation_views,
    index=default_view_index,
    horizontal=True,
    label_visibility="collapsed",
)
try:
    st.query_params["view"] = active_view
except Exception:
    pass

DEFAULT_GRAPH_TITLE_LIMIT = 500
DEFAULT_INTERACTIVE_NODES = 500
DEFAULT_INTERACTIVE_EDGES = 1000
DEFAULT_INTERACTIVE_SPACING = 2.2
DEFAULT_MAP_NODES = 120
DEFAULT_MAP_LINKS = 60
DEFAULT_MAP_TITLES = 120
DEFAULT_REGION_LINES = 40

with st.expander("Filtres de donnees", expanded=True):
    filter_col_1, filter_col_2, filter_col_3 = st.columns(3)
    with filter_col_1:
        selected_title_types = st.multiselect(
            "Types de titres",
            options=available_title_types,
            default=available_title_types,
        )
    with filter_col_2:
        selected_genres = st.multiselect("Themes / genres", options=available_genres, default=[])
    with filter_col_3:
        selected_regions = st.multiselect(
            "Regions IMDb",
            options=available_regions["region"].tolist(),
            default=[],
            format_func=lambda code: f"{available_regions.loc[available_regions['region'] == code, 'regionName'].iloc[0]} ({code})",
        )

    filter_col_4, filter_col_5, filter_col_6 = st.columns(3)
    with filter_col_4:
        min_votes = st.slider("Votes minimum", 0, 50_000, 0, step=500)
    with filter_col_5:
        min_edge_weight = st.slider("Liens minimum entre deux acteurs", 1, 5, 1)
    with filter_col_6:
        graph_title_limit = st.slider(
            "Titres max pour construire le graphe",
            500,
            10000,
            DEFAULT_GRAPH_TITLE_LIMIT,
            step=250,
        )

filtered_data = apply_filters(
    imdb_data,
    selected_title_types=selected_title_types,
    selected_genres=selected_genres,
    selected_regions=selected_regions,
    min_votes=min_votes,
)

graph_title_ids = select_graph_titles(filtered_data, graph_title_limit)
graph_source_data = filtered_data[filtered_data["tconst"].isin(graph_title_ids)].copy()
actor_rows = graph_source_data[graph_source_data["category"].isin(ACTOR_CATEGORIES)].copy()

if filtered_data.empty or actor_rows.empty:
    st.warning("Aucune donnee exploitable ne correspond aux filtres actuels.")
    st.stop()

actor_graph = nx.Graph()
community_options = ["Toutes"]
community_count = 0
titles_available_count = int(actor_rows["tconst"].nunique())

if active_view not in {"Donnees et details", "Synthese projet"}:
    with st.spinner("Construction du graphe acteurs..."):
        actor_graph = remember_resource(
            "_actor_graph_cache",
            (tuple(graph_title_ids), int(min_edge_weight), 12),
            lambda: build_actor_graph(graph_source_data, max_actors_per_title=12, min_weight=min_edge_weight),
        )
    if actor_graph.number_of_nodes() == 0:
        st.warning("Aucun graphe d'acteurs exploitable n'a pu etre construit avec ces filtres.")
        st.stop()
    community_values = sorted({int(data.get("community", 0)) for _, data in actor_graph.nodes(data=True)})
    community_options = ["Toutes"] + [str(value) for value in community_values]
    community_count = len(community_values)
    titles_available_count = int(actor_rows[actor_rows["nconst"].isin(actor_graph.nodes())]["tconst"].nunique())

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Titres geolocalises", f"{filtered_data['tconst'].nunique():,}")
metric_2.metric("Acteurs dans le graphe", f"{actor_graph.number_of_nodes() if actor_graph.number_of_nodes() else actor_rows['nconst'].nunique():,}")
metric_3.metric("Communautes", f"{community_count:,}")
metric_4.metric("Titres disponibles", f"{titles_available_count:,}")

if active_view == "Graphe interactif acteurs":
    st.markdown(
        """
        <div class="note">
            Vue principale: 1 acteur = 1 sommet, 1 lien = des films en commun.
        </div>
        """,
        unsafe_allow_html=True,
    )

    graph_col_1, graph_col_2, graph_col_3, graph_col_4 = st.columns(4)
    with graph_col_1:
        actor_group_mode = st.selectbox("Regrouper par", ["Communaute", "Pays", "Genre", "Profession"], key="interactive_group_mode")
    interactive_group_values = sorted({actor_group_value(data, actor_group_mode) for _, data in actor_graph.nodes(data=True)})
    with graph_col_2:
        selected_actor_groups = st.multiselect("Filtrer les groupes", options=interactive_group_values, default=[], key="interactive_selected_groups")
    with graph_col_3:
        actor_edge_mode = st.selectbox(
            "Type de liens visibles",
            ["Tous les liens", "Liens meme communaute", "Liens meme genre", "Liens meme pays", "Liens meme profession"],
            key="interactive_edge_mode",
        )
    with graph_col_4:
        actor_detail_min_edge = st.slider("Poids min des liens", 1, 6, min_edge_weight, key="interactive_min_edge")

    graph_col_5, graph_col_6, graph_col_7, graph_col_8 = st.columns(4)
    with graph_col_5:
        actor_detail_max_nodes = st.slider("Sommets visibles max", 200, 3000, DEFAULT_INTERACTIVE_NODES, step=100, key="interactive_max_nodes")
    with graph_col_6:
        actor_detail_max_edges = st.slider("Aretes visibles max", 200, 12000, DEFAULT_INTERACTIVE_EDGES, step=200, key="interactive_max_edges")
    with graph_col_7:
        actor_spacing = st.slider("Espacement des groupes", 1.0, 3.2, DEFAULT_INTERACTIVE_SPACING, step=0.1, key="interactive_spacing")
    with graph_col_8:
        actor_labels_toggle = st.toggle("Afficher plus de noms", value=False, key="interactive_labels_toggle")

    graph_col_9, graph_col_10 = st.columns(2)
    with graph_col_9:
        show_interactive_edges = st.toggle("Afficher les liens dans le graphe", value=True, key="interactive_show_edges")
    with graph_col_10:
        keep_isolates_toggle = st.toggle("Garder les acteurs isoles", value=False, key="interactive_keep_isolates")

    interactive_graph, interactive_stats = filtered_actor_subgraph(
        actor_graph,
        group_by=actor_group_mode,
        selected_groups=selected_actor_groups,
        edge_filter_mode=actor_edge_mode,
        min_edge_weight=actor_detail_min_edge,
        max_nodes=actor_detail_max_nodes,
        max_edges=actor_detail_max_edges,
        keep_isolates=keep_isolates_toggle,
    )
    interactive_display_graph = interactive_graph.copy()
    if not show_interactive_edges:
        interactive_display_graph.remove_edges_from(list(interactive_display_graph.edges()))

    visible_actor_options = [
        (node_data.get("label", node_id), node_id)
        for node_id, node_data in sorted(
            interactive_graph.nodes(data=True),
            key=lambda item: item[1].get("label", item[0]),
        )
    ]
    visible_actor_labels = [""] + [f"{label} [{actor_id}]" for label, actor_id in visible_actor_options]
    actor_lookup = {f"{label} [{actor_id}]": actor_id for label, actor_id in visible_actor_options}

    path_col_1, path_col_2 = st.columns(2)
    with path_col_1:
        path_source_label = st.selectbox("Acteur depart pour le plus court chemin", visible_actor_labels, key="path_source")
    with path_col_2:
        target_choices = [""] + [value for value in visible_actor_labels[1:] if value != path_source_label]
        path_target_label = st.selectbox("Acteur arrivee pour le plus court chemin", target_choices, key="path_target")

    highlighted_path_ids: list[str] = []
    path_table = pd.DataFrame()
    if path_source_label and path_target_label:
        highlighted_path_ids, path_table = shortest_actor_path_rows(
            interactive_graph,
            actor_lookup[path_source_label],
            actor_lookup[path_target_label],
        )

    stats_col_1, stats_col_2, stats_col_3, stats_col_4 = st.columns(4)
    stats_col_1.metric("Sommets visibles", f"{interactive_stats['nodes']:,}")
    stats_col_2.metric("Aretes visibles", f"{interactive_display_graph.number_of_edges():,}")
    stats_col_3.metric("Aretes avant coupe", f"{interactive_stats['edges_total']:,}")
    stats_col_4.metric("Groupes visibles", f"{interactive_stats['groups']:,}")

    browser_html = actor_browser_graph_html(
        interactive_display_graph,
        group_by=actor_group_mode,
        spacing_multiplier=actor_spacing,
        show_labels=actor_labels_toggle,
        highlighted_path=highlighted_path_ids,
    )
    components.html(browser_html, height=980, scrolling=False)

    if path_source_label and path_target_label:
        st.subheader("Plus court chemin visible")
        if path_table.empty:
            st.warning("Aucun chemin n'existe entre ces deux acteurs dans le sous-graphe courant. Elargissez les filtres ou affichez plus de liens.")
        else:
            st.caption("Le chemin minimise une distance inverse du poids du lien : plus deux acteurs ont de films en commun, plus leur connexion est courte.")
            st.dataframe(path_table, width="stretch", hide_index=True)

elif active_view == "Carte acteurs":
    st.markdown(
        """
        <div class="note">
            La carte charge uniquement quand vous la demandez, pour garder l'application fluide.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "map_render_enabled" not in st.session_state:
        st.session_state["map_render_enabled"] = False

    map_col_1, map_col_2, map_col_3, map_col_4 = st.columns(4)
    with map_col_1:
        selected_community = st.selectbox("Analyser une communaute", community_options, key="map_selected_community")
    with map_col_2:
        link_basis = st.selectbox("Type de liens geographiques", ["Titres communs", "Genres communs", "Communautes partagees"], key="map_link_basis")
    with map_col_3:
        tile_name = st.selectbox("Fond de carte", ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"], key="map_tile_name")
    with map_col_4:
        map_actor_group_mode = st.selectbox("Regrouper la carte acteurs par", ["Communaute", "Pays", "Genre", "Profession"], key="map_group_mode")

    map_actor_group_values = sorted({actor_group_value(data, map_actor_group_mode) for _, data in actor_graph.nodes(data=True)})
    map_col_5, map_col_6, map_col_7, map_col_8 = st.columns(4)
    with map_col_5:
        map_selected_groups = st.multiselect("Groupes visibles sur la carte", options=map_actor_group_values, default=[], key="map_selected_groups")
    with map_col_6:
        map_actor_nodes_limit = st.slider("Sommets acteurs carte", 50, 1500, DEFAULT_MAP_NODES, step=50, key="map_nodes_limit")
    with map_col_7:
        map_actor_links_limit = st.slider("Liens acteurs carte", 20, 3000, DEFAULT_MAP_LINKS, step=20, key="map_links_limit")
    with map_col_8:
        max_lines = st.slider("Liens geographiques max", 10, 400, DEFAULT_REGION_LINES, step=10, key="map_max_lines")

    map_col_9, map_col_10, map_col_11, map_col_12 = st.columns(4)
    with map_col_9:
        show_actor_nodes_on_map = st.toggle("Afficher acteurs", value=True, key="map_show_actor_nodes")
    with map_col_10:
        show_actor_links_on_map = st.toggle("Afficher liens acteurs", value=False, key="map_show_actor_links")
    with map_col_11:
        show_regions = st.toggle("Afficher regions", value=False, key="map_show_regions")
    with map_col_12:
        show_communities = st.toggle("Afficher communautes", value=False, key="map_show_communities")

    map_col_13, map_col_14, map_col_15, map_col_16 = st.columns(4)
    with map_col_13:
        map_actor_link_mode = st.selectbox(
            "Type de liens acteurs",
            ["Films / projets communs", "Meme genre", "Meme profession", "Meme communaute", "Meme pays"],
            key="map_actor_link_mode",
        )
    with map_col_14:
        show_titles = st.toggle("Afficher films / series", value=False, key="map_show_titles")
    with map_col_15:
        show_links = st.toggle("Afficher liens geographiques", value=False, key="map_show_region_links")
    with map_col_16:
        show_heatmap = st.toggle("Afficher carte de chaleur", value=False, key="map_show_heatmap")

    action_col_1, action_col_2 = st.columns([1, 3])
    with action_col_1:
        if st.button("Afficher / actualiser la carte", key="render_map_button"):
            st.session_state["map_render_enabled"] = True
    with action_col_2:
        st.caption("La carte ne se charge qu'a la demande pour eviter l'attente inutile et les blocages du navigateur.")

    default_max_title_points = min(titles_available_count, DEFAULT_MAP_TITLES) if titles_available_count else 0
    if titles_available_count > 0:
        min_title_points = 1 if titles_available_count < 100 else 100
        title_step = 1 if titles_available_count < 100 else 10 if titles_available_count < 1_000 else 50 if titles_available_count < 5_000 else 250
        max_title_points = st.slider(
            "Nombre max de points films",
            min_title_points,
            int(titles_available_count),
            int(max(default_max_title_points, min(titles_available_count, min_title_points))),
            step=title_step,
            key="map_max_title_points",
        )
    else:
        max_title_points = 0

    if not st.session_state["map_render_enabled"]:
        st.info("Cliquez sur `Afficher / actualiser la carte` pour lancer son rendu.")
    else:
        region_overview = prepare_region_overview(actor_graph, actor_rows, selected_community) if show_regions else pd.DataFrame()
        community_points = (
            prepare_region_community_points(actor_graph, actor_rows, selected_community)
            if show_communities
            else pd.DataFrame()
        )
        actor_map_points = (
            prepare_actor_map_points(
                actor_graph,
                group_by=map_actor_group_mode,
                selected_groups=map_selected_groups,
                max_nodes=map_actor_nodes_limit,
            )
            if show_actor_nodes_on_map
            else pd.DataFrame()
        )
        actor_map_links = (
            build_actor_map_links(actor_graph, actor_points=actor_map_points, link_mode=map_actor_link_mode, max_links=map_actor_links_limit)
            if show_actor_links_on_map
            else pd.DataFrame()
        )
        title_points = (
            prepare_title_points(filtered_data, selected_community, actor_graph, limit=max_title_points)
            if (show_titles or show_heatmap) and max_title_points > 0
            else pd.DataFrame()
        )
        region_links = build_region_links(actor_graph, actor_rows, link_basis, selected_community) if show_links else pd.DataFrame()

        with st.spinner("Preparation de la carte..."):
            map_html = render_map_html_cached(
                actor_points=actor_map_points,
                actor_links=actor_map_links,
                region_overview=region_overview,
                community_points=community_points,
                title_points=title_points,
                region_links=region_links,
                link_basis=link_basis,
                tile_name=tile_name,
                show_regions=show_regions,
                show_communities=show_communities,
                show_actor_nodes=show_actor_nodes_on_map,
                show_actor_links=show_actor_links_on_map,
                show_titles=show_titles,
                show_links=show_links,
                show_heatmap=show_heatmap,
                max_lines=max_lines,
                max_title_points=max_title_points,
            )
        components.html(map_html, height=760, scrolling=False)

elif active_view == "Analyses":
    with st.spinner("Preparation des analyses..."):
        actor_table = actor_summary_table(actor_graph)
        community_table = community_summary_table(actor_graph, actor_rows)
        genre_table = genre_leaders_table(actor_rows)
        lead_actor = actor_table.iloc[0] if not actor_table.empty else None
        lead_genre = genre_table.iloc[0] if not genre_table.empty else None

    analysis_col_1, analysis_col_2, analysis_col_3 = st.columns(3)
    with analysis_col_1:
        selected_community = st.selectbox("Communaute analysee", community_options, key="analysis_selected_community")
    with analysis_col_2:
        link_basis = st.selectbox("Type de liens pour l'analyse geo", ["Titres communs", "Genres communs", "Communautes partagees"], key="analysis_link_basis")
    with analysis_col_3:
        show_analysis_links = st.toggle("Calculer les liens geographiques", value=False, key="analysis_show_links")

    region_overview = prepare_region_overview(actor_graph, actor_rows, selected_community)
    region_links = build_region_links(actor_graph, actor_rows, link_basis, selected_community) if show_analysis_links else pd.DataFrame()

    top_left, top_right = st.columns(2)
    with top_left:
        st.subheader("Acteur qui a joue avec le plus d'acteurs")
        if lead_actor is None:
            st.info("Aucun acteur disponible.")
        else:
            st.dataframe(pd.DataFrame([lead_actor]), width="stretch", hide_index=True)

        st.subheader("Communautes d'acteurs")
        st.dataframe(community_table, width="stretch", hide_index=True)

        st.subheader("Acteurs les plus connectes")
        st.dataframe(actor_table.head(20), width="stretch", hide_index=True)

    with top_right:
        st.subheader("Acteur dominant par genre")
        if lead_genre is None:
            st.info("Aucun genre disponible.")
        else:
            st.dataframe(genre_table, width="stretch", hide_index=True)

        st.subheader("Regions les plus actives")
        st.dataframe(
            region_overview[
                ["region_name", "actors", "titles", "communities", "dominant_genres", "top_actor", "top_actor_degree"]
            ].head(20),
            width="stretch",
            hide_index=True,
        )

        st.subheader(f"Liens geographiques - {link_basis}")
        if region_links.empty:
            st.info("Activez le calcul des liens geographiques pour afficher cette table.")
        else:
            st.dataframe(
                region_links[
                    ["region_left_name", "region_right_name", "common_titles_count", "actor_pairs", "dominant_genres", "communities", "examples"]
                ].head(30),
                width="stretch",
                hide_index=True,
            )

elif active_view == "Exemples reseau":
    with st.spinner("Preparation des exemples reseau..."):
        community_graph = remember_resource(
            "_community_graph_cache",
            (tuple(graph_title_ids), int(min_edge_weight)),
            lambda: build_community_graph(actor_graph, actor_rows),
        )
        title_graph = remember_resource(
            "_title_graph_cache",
            (tuple(graph_title_ids), int(min_edge_weight), 8),
            lambda: build_title_graph(graph_source_data, max_titles_per_person=8, min_weight=min_edge_weight),
        )
        creator_graph = remember_resource(
            "_creator_graph_cache",
            (tuple(graph_title_ids), int(min_edge_weight), 10),
            lambda: build_creator_graph(graph_source_data, focus_categories=("director", "producer", "writer"), max_people_per_title=10, min_weight=min_edge_weight),
        )
        community_table = community_summary_table(actor_graph, actor_rows)
        title_table = generic_graph_summary_table(title_graph, "film")
        creator_table = generic_graph_summary_table(creator_graph, "personne")

    st.subheader("Graphes secondaires")
    st.caption("Trois autres lectures du projet, a partir du meme jeu de donnees IMDb.")

    example_col_1, example_col_2, example_col_3 = st.columns(3)
    with example_col_1:
        community_network_nodes = st.slider("Noeuds communautes", 4, 80, 20, step=2)
    with example_col_2:
        title_network_nodes = st.slider("Noeuds films", 20, 160, 70, step=10)
    with example_col_3:
        creator_network_nodes = st.slider("Noeuds createurs", 20, 160, 60, step=10)

    st.markdown("**Communautes <-> communautes**")
    components.html(
        browser_network_example_html(
            community_graph,
            title="Communautes d'acteurs reliees entre elles",
            subtitle="Chaque point est une communaute d'acteurs. Un lien apparait quand deux communautes se croisent par des collaborations entre leurs membres.",
            max_nodes=community_network_nodes,
            group_attr="mainGenre",
            default_color="#2563eb",
            list_field="titlesList",
            list_label="Titres de la communaute",
            edge_list_field="sharedPeople",
            edge_list_label="Acteurs passerelles",
        ),
        height=900,
        scrolling=False,
    )
    st.dataframe(
        community_table[["communaute", "acteurs", "titres", "regions", "genre_dominant", "acteur_central"]].head(15),
        width="stretch",
        hide_index=True,
    )

    example_row_2_left, example_row_2_right = st.columns(2)
    with example_row_2_left:
        st.markdown("**Films <-> films**")
        components.html(
            browser_network_example_html(
                title_graph,
                title="Films relies par personnes partagees",
                subtitle="Chaque point est un film ou une serie. Un lien apparait quand plusieurs personnes ont travaille sur les deux titres.",
                max_nodes=title_network_nodes,
                group_attr="role",
                default_color="#0f766e",
                list_field="participantsList",
                list_label="Participants visibles",
                edge_list_field="sharedPeople",
                edge_list_label="Personnes partagees",
                color_attr="role",
                color_map={
                    "movie": "#0f766e",
                    "tvSeries": "#2563eb",
                    "short": "#f59e0b",
                    "tvMovie": "#7c3aed",
                    "tvMiniSeries": "#dc2626",
                },
            ),
            height=900,
            scrolling=False,
        )
        if title_table.empty:
            st.info("Pas assez de films relies dans la selection actuelle.")
        else:
            st.dataframe(title_table.head(15), width="stretch", hide_index=True)

    with example_row_2_right:
        st.markdown("**Createurs <-> createurs**")
        components.html(
            browser_network_example_html(
                creator_graph,
                title="Createurs relies par projets",
                subtitle="Chaque point est un realisateur, producteur ou scenariste. Les liens montrent les projets partages.",
                max_nodes=creator_network_nodes,
                group_attr="role",
                default_color="#7c3aed",
                list_field="titlesList",
                list_label="Projets visibles",
                edge_list_field="titles",
                edge_list_label="Projets en commun",
                color_attr="role",
                color_map={"director": "#ea580c", "producer": "#16a34a", "writer": "#7c3aed"},
            ),
            height=900,
            scrolling=False,
        )
        if creator_table.empty:
            st.info("Pas assez de createurs relies dans la selection actuelle.")
        else:
            st.dataframe(creator_table.head(15), width="stretch", hide_index=True)

    st.markdown(
        """
        <div class="note">
            Idees pour la suite: graphe biparti acteurs-films, graphe des pays relies par cast commun, ou graphe des communautes d'acteurs avec poids entre groupes.
        </div>
        """,
        unsafe_allow_html=True,
    )

elif active_view == "Synthese projet":
    st.subheader("Synthese du projet")
    st.caption("Cette vue utilise les exports globaux prepares sur le backend large (cache 300000 lignes), independamment des filtres interactifs du haut.")

    story_assets = load_project_story_assets()
    global_stats = story_assets.get("all_stats", {}) or {}
    community_percent_table = story_assets.get("community_percent_table", pd.DataFrame())
    top_actors_table = story_assets.get("top_actors_table", pd.DataFrame())
    genre_distribution = story_assets.get("genre_distribution", pd.DataFrame())
    community_genre_bubbles = story_assets.get("community_genre_bubbles", pd.DataFrame())
    actor_producers_table = story_assets.get("actor_producers_table", pd.DataFrame())
    all_image_path = story_assets.get("all_image_path")
    top_image_path = story_assets.get("top_image_path")
    paths_image_path = story_assets.get("paths_image_path")

    summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
    summary_col_1.metric("Acteurs source", f"{int(global_stats.get('source_actor_total', 0)):,}")
    summary_col_2.metric("Acteurs relies", f"{int(global_stats.get('actors_analyzed', 0)):,}")
    summary_col_3.metric("Liens acteur-acteur", f"{int(global_stats.get('edges_analyzed', 0)):,}")
    summary_col_4.metric("Communautes detectees", f"{int(global_stats.get('communities_detected', 0)):,}")

    summary_col_5, summary_col_6, summary_col_7, summary_col_8 = st.columns(4)
    summary_col_5.metric("Grandes communautes detaillees", f"{int(global_stats.get('top_communities_detailed', 0)):,}")
    summary_col_6.metric("Acteurs dans 'Autres'", f"{int(global_stats.get('others_grouped_actor_count', 0)):,}")
    summary_col_7.metric("Acteurs non relies / retires", f"{int(global_stats.get('not_connected_or_removed', 0)):,}")
    summary_col_8.metric("Lignes sources backend", f"{int(global_stats.get('source_rows_read', 0)):,}")

    st.markdown("**1. Deux vues globales pour expliquer le backend**")
    global_img_col, global_text_col = st.columns([1.5, 1])
    with global_img_col:
        if isinstance(all_image_path, Path) and all_image_path.exists():
            st.image(str(all_image_path), use_container_width=True)
        else:
            st.warning("Image globale des communautes non trouvee dans le dossier outputs.")
    with global_text_col:
        st.markdown(
            f"""
            **Ce que montre cette image**

            - Tous les points representent des **acteurs**.
            - Cette vue utilise environ **{int(global_stats.get('actors_analyzed', 0)):,} acteurs relies** sur une base source de **{int(global_stats.get('source_actor_total', 0)):,} acteurs**.
            - Les **18 plus grandes communautes** sont separees visuellement.
            - Les petites communautes restantes sont regroupees dans une zone **`Autres communautes`**.
            - Les bulles sont placees d'abord selon leurs **relations entre communautes**, puis espacees artificiellement pour eviter qu'elles se chevauchent.

            **Comment les communautes sont faites**

            - `1 sommet = 1 acteur`
            - `1 lien = au moins un film en commun`
            - `poids du lien = nombre de films en commun`
            - les communautes sont detectees avec une logique de **modularite**
            - une communaute = un groupe d'acteurs qui collaborent davantage **entre eux** qu'avec le reste du graphe
            """
        )

    focus_img_col, focus_text_col = st.columns([1.5, 1])
    with focus_img_col:
        if isinstance(top_image_path, Path) and top_image_path.exists():
            st.image(str(top_image_path), use_container_width=True)
        else:
            st.warning("Image des communautes principales non trouvee dans le dossier outputs.")
    with focus_text_col:
        st.markdown(
            """
            **Pourquoi cette deuxieme image existe**

            - La vue globale des ~31 000 acteurs donne l'echelle du projet.
            - La vue par bulles principales montre mieux **les communautes les plus importantes**.
            - Ici, les points affiches sont les acteurs les plus centraux de chaque grande communaute.

            **Ce que veulent dire les liens**

            - Un lien entre deux acteurs signifie qu'ils ont joue dans **au moins un meme titre**.
            - Plus le poids est fort, plus ils ont **plusieurs films en commun**.
            - Deux acteurs dans la meme communaute ne sont pas toujours relies directement : ils peuvent etre relies **indirectement** via d'autres acteurs.
            - Les acteurs non relies n'apparaissent pas dans le graphe relationnel final, car ils n'ont **aucune collaboration exploitable** dans la selection consideree.
            """
        )

    st.markdown("**1 bis. De la vue communautaire a l'analyse des distances entre communautes**")
    path_img_col, path_text_col = st.columns([1.5, 1])
    with path_img_col:
        if isinstance(paths_image_path, Path) and paths_image_path.exists():
            st.image(str(paths_image_path), use_container_width=True)
        else:
            st.warning("Image des plus courts chemins entre communautes non trouvee dans le dossier outputs.")
    with path_text_col:
        st.markdown(
            """
            **Comment lire cette troisieme image**

            - On part de la **deuxieme image** ou chaque bulle representait une grande communaute.
            - Ici, on fait encore un niveau d'abstraction :
              chaque point devient **une communaute entiere**.
            - Les liens entre points sont des **liens inter-communautes** :
              ils existent si des acteurs de deux communautes sont relies.
            - Les liens en **bleu fonce** montrent ceux qui appartiennent a au moins un **plus court chemin**.

            **Quel est le sens de la distance ?**

            - la distance n'est pas la distance visuelle du dessin
            - elle est calculee sur le graphe des communautes
            - on utilise une logique du type : `distance = 1 / poids du lien`
            - donc plus deux communautes ont beaucoup de connexions, plus elles sont **proches**

            **Ce que cette image permet d'analyser**

            - quelles communautes sont les plus proches de la communaute principale
            - quelles communautes servent de **pont**
            - quelles communautes sont plus eloignees en nombre de sauts
            - comment on passe d'un grand bloc d'acteurs a une lecture **algorithmique des chemins**
            """
        )

    st.markdown(
        """
        **Progression logique des trois images**

        1. La premiere image montre **presque tous les acteurs connectes** du backend large.
        2. La deuxieme image se concentre sur les **grandes communautes d'acteurs**.
        3. La troisieme image transforme ces communautes en **graphe de communautes** pour etudier les plus courts chemins.
        """
    )

    st.markdown("**2. Pourcentages d'acteurs par communaute et genres dominants**")
    percent_col, genre_col = st.columns([1.2, 0.8])
    with percent_col:
        if community_percent_table.empty:
            st.info("Le tableau des communautes detaillees n'a pas ete trouve.")
        else:
            community_display = community_percent_table[
                [
                    "communaute",
                    "acteurs",
                    "pourcentage_acteurs",
                    "genres_dominants",
                    "acteur_central",
                    "acteurs_importants",
                ]
            ].copy()
            community_display["pourcentage_acteurs"] = community_display["pourcentage_acteurs"].map(lambda value: f"{value:.2f}%")
            st.dataframe(community_display.head(12), width="stretch", hide_index=True)
    with genre_col:
        if genre_distribution.empty:
            st.info("La repartition globale des genres n'a pas ete calculee.")
        else:
            genre_display = genre_distribution.copy()
            genre_display["pourcentage"] = genre_display["pourcentage"].map(lambda value: f"{value:.2f}%")
            st.dataframe(genre_display.head(12), width="stretch", hide_index=True)

    st.markdown("**2 bis. Pourcentage d'acteurs par genre dans chaque communaute**")
    if community_genre_bubbles.empty:
        st.info("Les bulles communaute x genre n'ont pas ete trouvees.")
    else:
        bubble_col_1, bubble_col_2 = st.columns([1, 1])
        with bubble_col_1:
            max_bubble_communities = min(18, int(community_genre_bubbles["community_id"].nunique()))
            selected_bubble_community_count = st.slider(
                "Communautes affichees dans les bulles",
                4,
                max_bubble_communities,
                min(10, max_bubble_communities),
                key="synthese_bubble_community_count",
            )
        with bubble_col_2:
            available_bubble_genres = (
                community_genre_bubbles.groupby("genre")["actor_count"].sum().sort_values(ascending=False).index.tolist()
            )
            default_bubble_genres = available_bubble_genres[:8]
            selected_bubble_genres = st.multiselect(
                "Genres visibles dans les bulles",
                options=available_bubble_genres,
                default=default_bubble_genres,
                key="synthese_bubble_genres",
            )

        top_bubble_communities = (
            community_genre_bubbles[["community_id", "community_size"]]
            .drop_duplicates()
            .sort_values(["community_size", "community_id"], ascending=[False, True])
            .head(selected_bubble_community_count)["community_id"]
            .tolist()
        )
        bubble_frame = community_genre_bubbles[
            community_genre_bubbles["community_id"].isin(top_bubble_communities)
        ].copy()
        if selected_bubble_genres:
            bubble_frame = bubble_frame[bubble_frame["genre"].isin(selected_bubble_genres)].copy()
        bubble_frame["communaute_label"] = bubble_frame["community_id"].apply(
            lambda value: f"Communaute {int(value)} ({int(bubble_frame.loc[bubble_frame['community_id'] == value, 'community_size'].iloc[0])} acteurs)"
        )
        bubble_frame["taille_bulle"] = bubble_frame["actor_percent_in_community"].clip(lower=0.8) * 2.2

        if bubble_frame.empty:
            st.info("Aucune combinaison communaute / genre a afficher avec les filtres actuels.")
        else:
            bubble_chart = go.Figure(
                data=[
                    go.Scatter(
                        x=bubble_frame["communaute_label"],
                        y=bubble_frame["genre"],
                        mode="markers+text",
                        text=bubble_frame["actor_percent_in_community"].map(lambda value: f"{value:.1f}%"),
                        textposition="middle center",
                        marker={
                            "size": bubble_frame["taille_bulle"],
                            "color": bubble_frame["actor_percent_in_community"],
                            "colorscale": "Blues",
                            "showscale": True,
                            "colorbar": {"title": "% dans la communaute"},
                            "line": {"width": 1, "color": "rgba(15,23,42,0.18)"},
                            "opacity": 0.88,
                        },
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Genre: %{y}<br>"
                            "Acteurs: %{customdata[0]}<br>"
                            "Pourcentage: %{customdata[1]}%<extra></extra>"
                        ),
                        customdata=bubble_frame[["actor_count", "actor_percent_in_community"]].values,
                    )
                ]
            )
            bubble_chart.update_layout(
                height=720,
                margin={"l": 20, "r": 20, "t": 40, "b": 20},
                title="Bulles des genres dominants par communaute",
                xaxis_title="Communautes",
                yaxis_title="Genres",
            )
            st.plotly_chart(bubble_chart, use_container_width=True)

            bubble_table = bubble_frame[
                ["community_id", "community_size", "genre", "actor_count", "actor_percent_in_community"]
            ].rename(
                columns={
                    "community_id": "communaute",
                    "community_size": "taille_communaute",
                    "genre": "genre",
                    "actor_count": "acteurs",
                    "actor_percent_in_community": "pourcentage_dans_la_communaute",
                }
            )
            bubble_table["pourcentage_dans_la_communaute"] = bubble_table["pourcentage_dans_la_communaute"].map(
                lambda value: f"{value:.2f}%"
            )
            st.dataframe(bubble_table.sort_values(["taille_communaute", "acteurs"], ascending=False), width="stretch", hide_index=True)

    st.markdown("**3. Acteurs les plus importants par communaute**")
    if top_actors_table.empty:
        st.info("Le classement des acteurs par communaute n'a pas ete trouve.")
    else:
        actor_focus = top_actors_table[
            [
                "communaute",
                "taille_communaute",
                "rang",
                "acteur",
                "degre_pondere",
                "liens_uniques",
                "projets",
                "genre_principal",
            ]
        ].copy()
        st.dataframe(actor_focus.head(80), width="stretch", hide_index=True)

    st.markdown("**3 bis. Acteurs qui sont aussi producteurs**")
    st.info(
        "Important : les fichiers IMDb Open Data locaux ne contiennent pas de budget de production. "
        "On peut donc identifier les acteurs qui sont aussi producteurs, mais pas calculer un vrai 'film au budget le plus eleve' sans source externe supplementaire. "
        "Le titre affiche ici est donc le plus vote de la communaute, comme proxy IMDb."
    )
    if actor_producers_table.empty:
        st.info("Le tableau des acteurs-producteurs n'a pas ete trouve.")
    else:
        producer_summary = (
            actor_producers_table.groupby("community_id")["actor_id"]
            .nunique()
            .reset_index(name="acteurs_producteurs")
            .sort_values(["acteurs_producteurs", "community_id"], ascending=[False, True])
        )
        producer_col_1, producer_col_2 = st.columns([0.75, 1.25])
        with producer_col_1:
            st.dataframe(
                producer_summary.rename(columns={"community_id": "communaute"}),
                width="stretch",
                hide_index=True,
            )
        with producer_col_2:
            producer_display = actor_producers_table.rename(
                columns={
                    "community_id": "communaute",
                    "actor_name": "acteur",
                    "weighted_degree": "degre_pondere",
                    "degree": "liens_uniques",
                    "actor_projects": "projets_acteur",
                    "producer_titles_count": "titres_comme_producteur",
                    "all_roles": "roles",
                    "community_top_title_by_votes": "titre_le_plus_vote_de_la_communaute",
                    "community_top_title_votes": "votes_titre_proxy",
                    "community_top_title_rating": "note_titre_proxy",
                }
            )
            st.dataframe(
                producer_display[
                    [
                        "communaute",
                        "acteur",
                        "degre_pondere",
                        "liens_uniques",
                        "titres_comme_producteur",
                        "roles",
                        "titre_le_plus_vote_de_la_communaute",
                        "votes_titre_proxy",
                        "note_titre_proxy",
                    ]
                ].head(80),
                width="stretch",
                hide_index=True,
            )

else:
    st.subheader("Donnees et details")
    detail_col_1, detail_col_2, detail_col_3, detail_col_4 = st.columns(4)
    detail_col_1.metric("Lignes lues", f"{audit['principals_rows_read']:,}")
    detail_col_2.metric("Lignes gardees", f"{audit['principals_rows_kept']:,}")
    detail_col_3.metric("Titres uniques", f"{audit['unique_titles']:,}")
    detail_col_4.metric("Personnes uniques", f"{audit['unique_people']:,}")

    source_table = pd.DataFrame(
        [
            {"fichier": "title.principals.tsv", "role_dans_l_app": "relie les personnes aux titres avec leur categorie IMDb"},
            {"fichier": "name.basics.tsv", "role_dans_l_app": "ajoute le nom complet et la profession principale"},
            {"fichier": "title.basics.tsv", "role_dans_l_app": "ajoute le type, l'annee et les genres du titre"},
            {"fichier": "title.ratings.tsv", "role_dans_l_app": "ajoute la note moyenne et le nombre de votes"},
            {"fichier": "title.akas.tsv", "role_dans_l_app": "ajoute la region IMDb utilisee pour la carte"},
        ]
    )
    st.markdown("**Fichiers relies**")
    st.dataframe(source_table, width="stretch", hide_index=True)

    audit_table = pd.DataFrame(
        [
            {"mesure": "Noms retrouves dans name.basics.tsv", "valeur": audit["names_matched"]},
            {"mesure": "Titres retrouves dans title.basics.tsv", "valeur": audit["titles_matched"]},
            {"mesure": "Notes retrouvees dans title.ratings.tsv", "valeur": audit["ratings_matched"]},
            {"mesure": "Regions retrouvees dans title.akas.tsv", "valeur": audit["regions_matched"]},
            {"mesure": "Lignes finales apres jointures", "valeur": audit["merged_rows"]},
            {"mesure": "Periode disponible", "valeur": f"{audit['min_year']} - {audit['max_year']}"},
        ]
    )
    audit_table["valeur"] = audit_table["valeur"].astype(str)
    st.markdown("**Ce que l'application a reussi a recuperer**")
    st.dataframe(audit_table, width="stretch", hide_index=True)

    role_table = (
        filtered_data.groupby("category")
        .agg(personnes_uniques=("nconst", "nunique"), titres_uniques=("tconst", "nunique"), lignes=("nconst", "size"))
        .reset_index()
        .rename(columns={"category": "categorie"})
        .sort_values(["personnes_uniques", "titres_uniques"], ascending=False)
    )
    st.markdown("**Repartition des roles dans la selection courante**")
    st.dataframe(role_table, width="stretch", hide_index=True)

    st.markdown("**Apercu des lignes utiles**")
    preview = filtered_data[
        [
            "tconst",
            "titleLabel",
            "titleType",
            "startYearInt",
            "region",
            "regionName",
            "genres",
            "nconst",
            "primaryName",
            "category",
            "averageRating",
            "numVotes",
        ]
    ].rename(
        columns={
            "tconst": "id_titre",
            "titleLabel": "titre",
            "titleType": "type",
            "startYearInt": "annee",
            "region": "code_region",
            "regionName": "region",
            "genres": "genres",
            "nconst": "id_personne",
            "primaryName": "nom",
            "category": "role",
            "averageRating": "note",
            "numVotes": "votes",
        }
    )
    st.dataframe(preview.head(250), width="stretch", hide_index=True)

    st.markdown("**Comment les graphes sont construits**")
    st.markdown(
        """
        - Graphe principal: un sommet = un acteur, un lien = au moins un film joue en commun.
        - Poids d'un lien: nombre de titres en commun entre deux acteurs.
        - Carte: les codes region de `title.akas.tsv` servent a placer les titres et les acteurs par zone IMDb.
        - Analyses: les communautes viennent du graphe d'acteurs, puis sont relues par genre, pays et densite relationnelle.
        - Graphes secondaires: ils montrent d'autres lectures possibles du meme jeu de donnees avec les films ou les createurs.
        """
    )
