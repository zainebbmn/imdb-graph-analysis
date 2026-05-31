import pandas as pd
import json
import numpy as np
from tqdm import tqdm
import os

def hash_to_geo(name):
    """Fake realistic geo from name hash - spread world cities"""
    h = abs(hash(name)) % 10000 / 10000
    cities = [
        (40.71, -74.00),  # NYC
        (51.51, -0.13),   # London
        (48.86, 2.35),    # Paris
        (52.37, 4.90),    # Amsterdam
        (37.77, -122.42), # SF
        (35.68, 139.77),  # Tokyo
        (55.75, 37.62),   # Moscow
        (41.00, 28.97),   # Istanbul
        (34.05, -118.24), # LA
        (-33.87, 151.21)  # Sydney
    ]
    idx = int(h * len(cities))
    lat = cities[idx][0] + (np.random.random()-0.5)*2
    lon = cities[idx][1] + (np.random.random()-0.5)*4
    return lat, lon

print("Loading FULL data (chunked for memory)...")

# Load smaller full
ratings = pd.read_csv('title.ratings.tsv', sep='\t', low_memory=False)
names = pd.read_csv('name.basics.tsv', sep='\t', low_memory=False)
titles = pd.read_csv('title.basics.tsv', sep='\t', low_memory=False)

# Chunk principals (huge)
principals_chunks = []
chunk_size = 100000
for chunk in tqdm(pd.read_csv('title.principals.tsv', sep='\t', chunksize=chunk_size, low_memory=False)):
    # Filter relevant categories
    rel_chunk = chunk[chunk['category'].isin(['actor', 'actress', 'director', 'producer'])]
    principals_chunks.append(rel_chunk)
    del chunk

principals = pd.concat(principals_chunks, ignore_index=True)
print(f"Principals filtered: {len(principals)} rows")

# Merge
df = principals.merge(names[['nconst', 'primaryName', 'birthYear', 'primaryProfession']], on='nconst', how='left')
df = df.merge(titles[['tconst', 'primaryTitle', 'genres']], on='tconst', how='left')
df = df.merge(ratings[['tconst', 'averageRating']], on='tconst', how='left')

# Clean
df['primaryName'] = df['primaryName'].fillna(df['nconst'])
df['primaryTitle'] = df['primaryTitle'].fillna(df['tconst'])
df['averageRating'] = df['averageRating'].fillna(0)
df = df.dropna(subset=['nconst', 'tconst'])

# Add geo
df['lat'] = df['primaryName'].apply(lambda n: hash_to_geo(n)[0])
df['lon'] = df['primaryName'].apply(lambda n: hash_to_geo(n)[1])

# Nodes: unique actors/films
actors = df[['nconst', 'primaryName', 'category', 'lat', 'lon', 'birthYear']].drop_duplicates('nconst')
actors['type'] = 'actor'  # or 'realisateur' if category=='director'
actors.loc[actors['category']=='director', 'type'] = 'realisateur'
actors = actors.rename(columns={'nconst':'id', 'primaryName':'label'})

films = df[['tconst', 'primaryTitle', 'averageRating', 'genres']].drop_duplicates('tconst')
films['type'] = 'film'
films = films.rename(columns={'tconst':'id', 'primaryTitle':'label'})

nodes = pd.concat([actors[['id','label','type','lat','lon','birthYear','category']], films[['id','label','type','averageRating','genres']].rename(columns={'averageRating':'birthYear', 'genres':'category'})], ignore_index=True)
nodes['degree'] = 0  # placeholder

# Edges: bipartite actor-film
edges = df[['nconst', 'tconst', 'category']].rename(columns={'nconst':'source', 'tconst':'target'})
edges['weight'] = 1
edges['type'] = 'bipartite'

# Export single JSON
data = {
    'nodes': nodes.to_dict('records'),
    'edges': edges.to_dict('records')
}
with open('data_aggregated.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Aggregated: {len(nodes)} nodes, {len(edges)} edges -> data_aggregated.json")
print("Ready for graph building!")

