import pandas as pd
import plotly.graph_objects as go
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances, silhouette_score, davies_bouldin_score, calinski_harabasz_score
import numpy as np
from parameters import eps
from parameters import min
from parameters import nofcluster
from parameters import max_cluster 
from parameters import similarity
from parameters import print_banner

# Cargar datos
df = pd.read_excel('bancos.xlsx')

# Asegurar que existan columnas requeridas para 2TA y otros cálculos
required_columns_for_clustering = ['x', 'y', 'z', 'cueq', 'density']
for col in required_columns_for_clustering:
    if col not in df.columns:
        print(f"Advertencia: Columna '{col}' no encontrada. Añadiendo con NaN.")
        df[col] = np.nan

# Calcular tonelaje si no existe (necesario para DBSCAN hover y 2TA)
if 'tonelaje' not in df.columns:
    df['tonelaje'] = df['density'] * 1000.0

# Atributos visualizables (sin incluir clustering)
atributos_color = {
    'CuEq (%)': 'cueq',
    'Oro (g/t)': 'au',
    'Plata (g/t)': 'ag',
}

# Ordenar bancos de mayor a menor profundidad (z)
bancos_unicos = sorted(df['z'].unique(), reverse=True)

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Desarrollos de Algoritmos

# Preparar datos para clustering (escalado)
X = df[['x', 'y', 'z', 'cueq']].copy()
X_scaled = StandardScaler().fit_transform(X)

# DBSCAN
db = DBSCAN(eps=eps, min_samples=min)
df['cluster_dbscan'] = db.fit_predict(X_scaled)

# Agglomerative Clustering
agg = AgglomerativeClustering(n_clusters=nofcluster)
df['cluster_agglo'] = agg.fit_predict(X_scaled)

# --- Cálculo de estadísticas para Agglomerative Clustering ---
grp_agglo = df.groupby("cluster_agglo")
agglo_stats = grp_agglo.size().to_frame("agglo_bloques") # Renombrado
agglo_stats["agglo_tonelaje_total"] = grp_agglo["tonelaje"].sum() # Renombrado

if "cueq" in df.columns:
    agglo_stats["agglo_cueq_prom"] = grp_agglo["cueq"].mean() # Renombrado
if "cut" in df.columns:
    agglo_stats["agglo_cut_prom"] = grp_agglo["cut"].mean() # Renombrado
else:
    agglo_stats["agglo_cut_prom"] = np.nan

agglo_stats = agglo_stats.reset_index()
df = df.merge(agglo_stats, on="cluster_agglo", how="left")


# --- Funciones y Simulación del algoritmo 2TA (basado en similitud con atributos espaciales y de roca/ley) ---

def calculate_cluster_stats(cluster_df):
    """Calcula estadísticas para un cluster"""
    stats = {
        '_2ta_cueq_prom': cluster_df['cueq'].mean(), # Renombrado
        '_2ta_cut_prom': cluster_df['cut'].mean() if 'cut' in cluster_df else 0, # Renombrado
        '_2ta_bloques': len(cluster_df), # Renombrado
        '_2ta_tonelaje_total': cluster_df['tonelaje'].sum() # Renombrado
    }
    return stats

def clustering_2ta(df_data, max_cluster_size=max_cluster, similarity_threshold=similarity):
    cluster_labels = -1 * np.ones(len(df_data), dtype=int)
    current_cluster_id = 0
    all_stats = {}

    for z_val in sorted(df_data['z'].unique(), reverse=True):
        banco_df = df_data[df_data['z'] == z_val].copy()

        if banco_df.empty:
            continue

        # Preparar características
        coords = banco_df[['x', 'y']].values
        grades = banco_df['cueq'].values.reshape(-1, 1)

        # Manejo de 'litologia': si no existe, se usa un array de ceros
        if 'litologia' in banco_df.columns:
            rock_features = pd.get_dummies(banco_df['litologia'], prefix='lit').values
        else:
            rock_features = np.zeros((len(banco_df), 1))

        # Normalización
        features = np.hstack([coords, grades, rock_features])
        # Asegurarse de que features no esté vacío antes de escalar
        if features.size == 0:
            continue
        features = StandardScaler().fit_transform(features)
        dist_matrix = pairwise_distances(features)

        assigned = set()

        for i in range(len(banco_df)):
            if i in assigned:
                continue

            cluster_indices = [i]
            assigned.add(i)

            candidates = [j for j in range(len(banco_df)) if j != i and j not in assigned]
            candidates.sort(key=lambda j: dist_matrix[i, j])

            for j in candidates:
                if dist_matrix[i, j] < similarity_threshold:
                    if len(cluster_indices) < max_cluster_size:
                        cluster_indices.append(j)
                        assigned.add(j)
                    else:
                        break

            # Asignar etiquetas y calcular stats
            for idx in cluster_indices:
                original_idx = banco_df.iloc[idx].name
                cluster_labels[original_idx] = current_cluster_id

            # Calcular estadísticas para este cluster
            cluster_data = banco_df.iloc[cluster_indices]
            if not cluster_data.empty:
                all_stats[current_cluster_id] = calculate_cluster_stats(cluster_data)

            current_cluster_id += 1

    # Crear DataFrame de estadísticas
    stats_df = pd.DataFrame.from_dict(all_stats, orient='index')
    stats_df.index.name = 'cluster_2ta'
    stats_df.reset_index(inplace=True)

    # Unir estadísticas al DataFrame original
    df_data['cluster_2ta'] = cluster_labels
    df_data = df_data.merge(stats_df, on='cluster_2ta', how='left')

    return df_data

# Ejecutar clustering 2TA
df = clustering_2ta(df)

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Función para crear trazas 3D (Modificada para manejar hover de clusters genéricos como Agglomerative y 2TA)
def crear_trazas(atributo):
    trazas = []
    mostrar_colorbar = not atributo.startswith('cluster')
    colorbar_config = dict(title=atributo, x=0, xanchor='left') if mostrar_colorbar else {}

    custom_data_cols = []
    hover_template_str = ''

    # Definir customdata y hovertemplate para los clusters (Agglomerative y 2TA)
    if atributo == 'cluster_agglo':
        stats_prefix = 'agglo_'
        custom_data_cols = [
            f'{stats_prefix}cueq_prom',
            f'{stats_prefix}cut_prom',
            f'{stats_prefix}tonelaje_total',
            f'{stats_prefix}bloques',
            atributo
        ]
        hover_template_str = (
            f"<b>Clúster ID:</b> %{{customdata[4]}}<br>"
            "<b>Bloques:</b> %{customdata[3]}<br>"
            "<b>CuEq promedio:</b> %{customdata[0]:.2f}%<br>"
            "<b>CUT promedio:</b> %{customdata[1]:.2f}%<br>"
            "<b>Tonelaje total:</b> %{customdata[2]:,.0f} t<extra></extra>"
        )
    elif atributo == 'cluster_2ta':
        stats_prefix = '_2ta_'
        custom_data_cols = [
            f'{stats_prefix}cueq_prom',
            f'{stats_prefix}cut_prom',
            f'{stats_prefix}tonelaje_total',
            f'{stats_prefix}bloques',
            atributo
        ]
        hover_template_str = (
            f"<b>Clúster ID:</b> %{{customdata[4]}}<br>"
            "<b>Bloques:</b> %{customdata[3]}<br>"
            "<b>CuEq promedio:</b> %{customdata[0]:.2f}%<br>"
            "<b>CUT promedio:</b> %{customdata[1]:.2f}%<br>"
            "<b>Tonelaje total:</b> %{customdata[2]:,.0f} t<extra></extra>"
        )
    else:
        # Hovers para atributos normales (CuEq, Au, Ag)
        hover_template_str = (
            'X: %{x}<br>' +
            'Y: %{y}<br>' +
            'Z: %{z}<br>' +
            f'{atributo}: %{{marker.color}}<extra></extra>'
        )

    # Asegurarse de que las columnas de customdata existan antes de intentar acceder a ellas
    # Si no existen, se añadirán con NaN para evitar errores
    for col in custom_data_cols:
        if col not in df.columns:
            df[col] = np.nan

    # Traza para "Todos los Bancos"
    trace_all_banks = go.Scatter3d(
        x=df['x'], y=df['y'], z=df['z'],
        mode='markers',
        marker=dict(
            size=3,
            color=df[atributo],
            colorscale='Viridis',
            opacity=0.7,
            **({'colorbar': colorbar_config} if mostrar_colorbar else {})
        ),
        customdata=df[custom_data_cols].values if custom_data_cols else None,
        hovertemplate=hover_template_str,
        name='Todos los Bancos',
        visible=True
    )
    trazas.append(trace_all_banks)

    # Trazas por banco individual
    for banco in bancos_unicos:
        banco_df = df[df['z'] == banco]
        if not banco_df.empty:
            trace_bank = go.Scatter3d(
                x=banco_df['x'], y=banco_df['y'], z=banco_df['z'],
                mode='markers',
                marker=dict(
                    size=3,
                    color=banco_df[atributo],
                    colorscale='Viridis',
                    opacity=0.7
                ),
                customdata=banco_df[custom_data_cols].values if custom_data_cols else None,
                hovertemplate=hover_template_str,
                name=f'Banco z={banco}',
                visible=False
            )
            trazas.append(trace_bank)
    return trazas


# Crear figura y añadir trazas de atributos
fig = go.Figure()
trazas_por_atributo = {}
for i, (nombre, col) in enumerate(atributos_color.items()):
    trazas = crear_trazas(col)
    for t in trazas:
        t.visible = (i == 0 and t.name == 'Todos los Bancos') # Solo el primer atributo y "Todos los Bancos" visible por defecto
        fig.add_trace(t)
    trazas_por_atributo[nombre] = list(range(i * len(trazas), (i + 1) * len(trazas)))


# Guardar posiciones para clustering
offset_dbscan = len(fig.data)

# Traza DBSCAN con hover solo de estadísticas del clúster
trazas_dbscan = []
# Asegurarse de que 'tonelaje' exista para el cálculo de stats de DBSCAN
if 'tonelaje' not in df.columns:
    df['tonelaje'] = df['density'] * 1000.0

# Usar un sufijo para las columnas de estadísticas de DBSCAN para evitar conflictos
df['_cluster_dbscan_key'] = df[['z', 'cluster_dbscan']].astype(str).agg('-'.join, axis=1)
stats_dbscan = df.groupby('_cluster_dbscan_key').agg(
    dbscan_ley_cueq_prom=('cueq', 'mean'), # Cambiado el nombre
    dbscan_ley_cut_prom=('cut', 'mean') if 'cut' in df.columns else ('cueq', lambda x: np.nan), # Cambiado el nombre
    dbscan_bloques=('cueq', 'count'), # Cambiado el nombre
    dbscan_tonelaje_total=('tonelaje', 'sum') # Cambiado el nombre
).reset_index()
df = df.merge(stats_dbscan, on='_cluster_dbscan_key', how='left') # No usar suffixes aquí, ya los nombres son únicos


for banco in bancos_unicos:
    banco_df = df[df['z'] == banco].copy()
    # Traza para información del clúster DBSCAN
    traza_cluster_dbscan = go.Scatter3d(
        x=banco_df['x'],
        y=banco_df['y'],
        z=banco_df['z'],
        mode='markers',
        marker=dict(
            size=3,
            color=banco_df['cluster_dbscan'],
            colorscale='Viridis',
            opacity=0.7
        ),
        # Asegurarse de que estos nombres de columna coincidan con los calculados arriba
        customdata=banco_df[['dbscan_ley_cueq_prom', 'dbscan_ley_cut_prom', 'dbscan_tonelaje_total', 'dbscan_bloques', 'cluster_dbscan']],
        hovertemplate=
            'Clúster ID: %{customdata[4]}<br>' +
            'Bloques: %{customdata[3]}<br>' +
            'CuEq promedio: %{customdata[0]:.2f}%<br>' +
            'CUT promedio: %{customdata[1]:.2f}%<br>' +
            'Tonelaje total: %{customdata[2]:,.0f} t' +
            '<extra></extra>',
        name=f'Banco z={banco}',
        visible=False
    )
    trazas_dbscan.append(traza_cluster_dbscan)
    fig.add_trace(traza_cluster_dbscan)

    # Traza para información de bloques individuales DBSCAN (esta ya estaba bien)
    traza_bloque_dbscan = go.Scatter3d(
        x=banco_df['x'],
        y=banco_df['y'],
        z=banco_df['z'],
        mode='markers',
        marker=dict(
            size=3,
            color=banco_df['cluster_dbscan'],
            colorscale='Viridis',
            opacity=0.7
        ),
        customdata=banco_df[['cueq', 'cut', 'density', 'cluster_dbscan']],
        hovertemplate=
            'X: %{x}<br>' +
            'Y: %{y}<br>' +
            'Z: %{z}<br>' +
            'CuEq: %{customdata[0]:.2f}%<br>' +
            'CUT: %{customdata[1]:.2f}%<br>' +
            'Densidad: %{customdata[2]:.2f} g/cm³<br>' +
            'Cluster: %{customdata[3]}<br>' +
            'Tonelaje estimado: %{customdata[2]*1000:.0f} t<extra></extra>',
        name=f'Banco z={banco}',
        visible=False
    )
    #trazas_dbscan.append(traza_bloque_dbscan)
    #fig.add_trace(traza_bloque_dbscan)


offset_agglo = len(fig.data)
trazas_agglo = crear_trazas('cluster_agglo')
for t in trazas_agglo:
    t.visible = False
    fig.add_trace(t)

offset_2ta = len(fig.data)
trazas_2ta = crear_trazas('cluster_2ta') # Usar la función modificada para 2TA
for t in trazas_2ta:
    t.visible = False
    fig.add_trace(t)

# Dropdown de bancos
dropdown_bancos = []
n_atributos = len(atributos_color)
# Cada atributo tiene (1 + len(bancos_unicos)) trazas (Todos los Bancos + cada banco individual)
trazas_por_atributo_set = (1 + len(bancos_unicos))

for i in range(trazas_por_atributo_set):
    visibles = [False] * len(fig.data)
    # Activar las trazas del atributo actualmente seleccionado para el banco i
    # Esto asume que el primer atributo es el visible por defecto
    for j in range(n_atributos): # Para cada grupo de atributos
        # Si es el primer atributo (j==0), se activa la traza correspondiente al banco i
        # Si no es el primer atributo, se mantiene invisible por defecto
        if j == 0: # Solo el primer atributo es visible por defecto
            visibles[j * trazas_por_atributo_set + i] = True
    dropdown_bancos.append(dict(
        label=f'Banco z={bancos_unicos[i-1]}' if i > 0 else 'Todos los Bancos',
        method='update',
        args=[{'visible': visibles}]
    ))

# Dropdown de atributos
dropdown_atributos = []
for i, nombre in enumerate(atributos_color.keys()):
    visibles = [False] * len(fig.data)
    # Activar todas las trazas (Todos los Bancos + cada banco individual) para el atributo i
    for j in range(trazas_por_atributo_set):
        visibles[i * trazas_por_atributo_set + j] = True
    dropdown_atributos.append(dict(
        label=nombre,
        method='update',
        args=[{'visible': visibles}]
    ))

# Dropdown de clustering
def visibilidad_clustering(offset, cantidad):
    visibles = [False] * len(fig.data)
    for i in range(cantidad):
        visibles[offset + i] = True
    return visibles

dropdown_clustering = [
    dict(
        label='Ver DBSCAN Clustering',
        method='update',
        args=[
            {'visible': visibilidad_clustering(offset_dbscan, len(trazas_dbscan))},
            {'title': 'DBSCAN Clustering'}
        ]
    ),
    dict(
        label='Ver Agglomerative Clustering',
        method='update',
        args=[
            {'visible': visibilidad_clustering(offset_agglo, len(trazas_agglo))},
            {'title': 'Agglomerative Clustering'}
        ]
    ),
    dict(
        label='Ver Two-Stage Clustering',
        method='update',
        args=[
            {"visible": visibilidad_clustering(offset_2ta, len(trazas_2ta))},
            {"title": 'Two-Stage Clustering'}
        ]
    )
]

# Layout final con 3 menús
fig.update_layout(
    updatemenus=[
        dict(
            buttons=dropdown_bancos,
            direction="down",
            showactive=True,
            x=0.01, xanchor="left",
            y=1.15, yanchor="top"
        ),
        dict(
            buttons=dropdown_atributos,
            direction="down",
            showactive=True,
            x=0.28, xanchor="left",
            y=1.15, yanchor="top"
        ),
        dict(
            buttons=dropdown_clustering,
            direction="down",
            showactive=True,
            x=0.55, xanchor="left",
            y=1.15, yanchor="top"
        )
    ],
    scene=dict(
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        zaxis_title='Profundidad Z (m)'
    ),
    title='Visualización 3D de Bloques',
    margin=dict(l=0, r=0, b=0, t=50)
)

fig.show()

########### FINAL WELL

# =====================
# MÉTRICAS DE EVALUACIÓN
# =====================

def calculate_clustering_metrics(X_data, labels, algorithm_name):
    """
    Calcula y imprime las métricas de Silhouette, Davies-Bouldin y Calinski-Harabasz.
    
    Args:
        X_data (np.array): Los datos utilizados para el clustering.
        labels (np.array): Las etiquetas de clúster asignadas por el algoritmo.
        algorithm_name (str): El nombre del algoritmo de clustering para la impresión.
    """
    # Filtrar el ruido (-1) para DBSCAN y asegurar al menos 2 clústeres válidos
    valid_mask = (labels != -1)
    
    # Asegurarse de que haya suficientes muestras y clústeres para calcular las métricas
    if valid_mask.sum() > 1 and len(np.unique(labels[valid_mask])) > 1:
        X_valid = X_data[valid_mask]
        labels_valid = labels[valid_mask]

        sil_score = silhouette_score(X_valid, labels_valid)
        db_score = davies_bouldin_score(X_valid, labels_valid)
        ch_score = calinski_harabasz_score(X_valid, labels_valid)

        print(f"\n--- MÉTRICAS DE CLUSTERING para {algorithm_name} ---")
        print(f"Silhouette Score: {sil_score:.4f}")
        print(f"Davies-Bouldin Index: {db_score:.4f}")
        print(f"Calinski-Harabasz Index: {ch_score:.4f}")
    else:
        print(f"\n[!] No se pueden calcular métricas clásicas para {algorithm_name} (menos de 2 clústeres válidos o solo ruido).")


# Calcular métricas para DBSCAN
calculate_clustering_metrics(X_scaled, df['cluster_dbscan'].values, "DBSCAN")

# Calcular métricas para Agglomerative Clustering
calculate_clustering_metrics(X_scaled, df['cluster_agglo'].values, "Agglomerative Clustering")

# Calcular métricas para Two-Stage Clustering (2TA)
# Para 2TA, X_scaled es apropiado ya que las características se normalizan de manera similar.
# Sin embargo, si 2TA usa un conjunto de características diferente o un escalado distinto,
# se debería usar el X_scaled específico de 2TA. Aquí asumimos que X_scaled es representativo.
calculate_clustering_metrics(X_scaled, df['cluster_2ta'].values, "Two-Stage Clustering (2TA)")

print_banner()
# ®By: Mikkel2025_®