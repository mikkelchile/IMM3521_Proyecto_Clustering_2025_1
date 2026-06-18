README.txt

Nombre del proyecto:
Optimización y Agrupamiento de Bancos de Perforación - Proyecto TecMin

Descripción general:
Este proyecto tiene como objetivo realizar una optimización sobre bancos de perforación a partir de un archivo Excel (bancos.xlsx) y aplicar técnicas de clustering para agrupar los resultados. El código permite ejecutar distintos tipos de agrupamientos, visualizar los resultados y calcular métricas asociadas a cada solución.

Estructura del proyecto:

- main.py:
  Script principal que ejecuta el flujo completo del proyecto.
  1. Carga los datos desde bancos.xlsx.
  2. Llama a funciones de procesamiento y agrupamiento desde clustering.py.
  3. Define las configuraciones de parámetros desde parameters.py.
  4. Imprime y visualiza los resultados finales.

- clustering.py:
  Contiene las funciones principales para ejecutar los algoritmos de clustering y evaluación.
  - Se incluye el uso de algoritmos como DBSCAN, KMeans y Agglomerative Clustering.
  - Calcula métricas de agrupamiento como Silhouette Score y Davies-Bouldin Index.
  - Funciones para visualizar los resultados.

- parameters.py:
  Archivo de configuración de parámetros que permite ajustar fácilmente los valores utilizados en main.py y clustering.py.
  - Define parámetros como el número de clusters, método de agrupamiento a usar, columnas relevantes del dataset, entre otros.

- bancos.xlsx:
  Archivo fuente con los datos de entrada. Contiene las características geométricas y espaciales de los bancos.

Requisitos del entorno:
- Python 3.10 o superior
- Bibliotecas requeridas: pandas, numpy, matplotlib, scikit-learn, openpyxl

Ejecución del código:
1. Asegúrate de tener instaladas las dependencias necesarias.
2. Ejecuta el script principal:
   python main.py
3. El programa mostrará los resultados de agrupamiento en consola y generará visualizaciones interactivas.

Notas adicionales:
- Asegúrate de que bancos.xlsx esté en la misma carpeta del script.
- Puedes ajustar los parámetros fácilmente en parameters.py para explorar diferentes configuraciones y mejorar la agrupación.
- El código está diseñado para ser modular y fácilmente escalable a más tipos de algoritmos de clustering.
- ®_Mikkel2025_®