import pandas as pd
import os
import json


def load_ratings(path='title.ratings.tsv'):
    """Load full title.ratings.tsv"""
    df = pd.read_csv(path, sep='\t', header=0)
    df['numVotes'] = pd.to_numeric(df['numVotes'], errors='coerce').fillna(0).astype(int)
    df['averageRating'] = pd.to_numeric(df['averageRating'], errors='coerce').fillna(0).astype(float)
    return df

def load_sample_principals(path='title.principals.tsv', nrows=100000):
    """Load sample from large principals (first nrows lines)"""
    return pd.read_csv(path, sep='\t', nrows=nrows, header=0)

def load_sample_names(path='name.basics.tsv', nrows=50000):
    """Load sample names"""
    return pd.read_csv(path, sep='\t', nrows=nrows, header=0)

def load_sample_titles(path='title.basics.tsv', nrows=50000):
    """Load sample titles"""
    return pd.read_csv(path, sep='\t', nrows=nrows, header=0)

def load_aggregated(path='data_aggregated.json'):
    """Load single aggregated data: nodes, edges"""
    if not os.path.exists(path):
        print(f"Warning: {path} not found. Run aggregate_data.py first.")
        return pd.DataFrame(), pd.DataFrame()
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = pd.DataFrame(data['nodes'])
    edges = pd.DataFrame(data['edges'])
    return nodes, edges


def get_top_rated_movies(ratings_df, top_n=100):
    """Get top N highest rated movies with >1000 votes"""
    top = ratings_df[ratings_df['numVotes'] > 1000].nlargest(top_n, 'averageRating')
    return top['tconst'].tolist()

if __name__ == '__main__':
    print('Data loader ready.')


