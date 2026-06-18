import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import plotly.graph_objects as go

# ========================
# 1. Cargar datos
# ========================
def load_data(path="fase_banco_proyecto2.xlsx"):
    df = pd.read_excel(path, sheet_name="Hoja1")
    return df

# ========================
# 2. Preprocesamiento y filtrado
# ========================
def preprocess_data(df):
    bancos_objetivo = df['z'].unique()[:2]  # primeros 2 bancos únicos
    df_filt = df[df['z'].isin(bancos_objetivo)].copy()
    return df_filt

# ========================
# 3. Implementación DBSCAN
# ========================
def apply_dbscan(df, eps=10, min_samples=5):
    coords = df[['x', 'y']].values
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(coords)
    df['dbscan_cluster'] = labels
    return df, model

# ========================
# 4. Implementación Agglomerative Clustering
# ========================
def apply_agglomerative(df, n_clusters=10):
    coords = df[['x', 'y']].values
    model = AgglomerativeClustering(n_clusters=n_clusters)
    labels = model.fit_predict(coords)
    df['agg_cluster'] = labels
    return df, model

# ========================
# 5. Evaluación de calidad de clusters
# ========================
def evaluate_clustering(df, column):
    valid = df[df[column] != -1]  # remover ruido DBSCAN si aplica
    coords = valid[['x', 'y']].values
    labels = valid[column].values
    if len(valid) <= 1 or len(np.unique(labels)) < 2:
        return {
            'silhouette': None,
            'davies_bouldin': None,
            'calinski_harabasz': None,
            'warning': f'No se puede evaluar clustering: {len(valid)} muestras con {len(np.unique(labels))} clusters.'
        }
    return {
        'silhouette': silhouette_score(coords, labels),
        'davies_bouldin': davies_bouldin_score(coords, labels),
        'calinski_harabasz': calinski_harabasz_score(coords, labels)
    }

# ========================
# 6. Generar trazas de visualización 3D
# ========================
def generate_traces(df, cluster_column):
    traces = []
    for cluster in sorted(df[cluster_column].unique()):
        df_cluster = df[df[cluster_column] == cluster]
        traces.append(go.Scatter3d(
            x=df_cluster['x'], y=df_cluster['y'], z=df_cluster['z'],
            mode='markers',
            marker=dict(
                size=3,
                color=[cluster]*len(df_cluster),
                colorscale='Viridis',
                opacity=0.7,
                colorbar=dict(title=cluster_column) if cluster == sorted(df[cluster_column].unique())[0] else None
            ),
            name=f'{cluster_column} {cluster}',
            visible=True
        ))
    return traces

# ========================
# 7. Punto de entrada parametrizable para Dash
# ========================
def run_clustering_analysis(n_clusters=10, eps=12, min_samples=6):
    df = load_data()
    df = preprocess_data(df)

    # DBSCAN
    df, db_model = apply_dbscan(df, eps=eps, min_samples=min_samples)
    db_metrics = evaluate_clustering(df, 'dbscan_cluster')
    db_traces = generate_traces(df, 'dbscan_cluster')

    # Agglomerative
    df, agg_model = apply_agglomerative(df, n_clusters=n_clusters)
    agg_metrics = evaluate_clustering(df, 'agg_cluster')
    agg_traces = generate_traces(df, 'agg_cluster')

    return {
        'df': df,
        'dbscan': {'metrics': db_metrics, 'traces': db_traces},
        'agglo': {'metrics': agg_metrics, 'traces': agg_traces}
    }