#!/usr/bin/env python3
"""Main script for the IMDb graph project.

Loads graph data, runs a lightweight analysis, and exports static outputs.
"""

from analysis import analyze_graph
from graph_builder import build_imdb_graph
from visualize import visualize_graph


if __name__ == "__main__":
    print("Building IMDb Graph...")
    graphs = build_imdb_graph(sample_size=50_000)

    print("Analyzing...")
    results = analyze_graph(graphs)

    print("Visualizing...")
    visualize_graph(graphs, results)

    print("Done! Check analysis/ and graphs/ folders.")
