Simulación Concurrente de Acceso a un Estadio

Proyecto de programación concurrente en Python que simula el acceso masivo de aficionados a un estadio utilizando:

Threads
Locks
Semáforos
Colas (queue)
Patrón productor-consumidor
Dashboard interactivo con Streamlit
Visualización de métricas y gráficos

Objetivo del proyecto
Comparar el rendimiento entre:
Ejecución secuencial
Ejecución concurrente
y analizar cómo mejora el tiempo total de procesamiento cuando varias puertas y tornos trabajan simultáneamente.

Tecnologías utilizadas
Python 3
Streamlit
NumPy
Matplotlib
threading
queue
Funcionalidades
Simulación de aficionados

Cada aficionado puede:
Tener una entrada válida o inválida
Llegar tarde
Tener una entrada duplicada
Ser asignado aleatoriamente a una puerta

Concurrencia implementada
Threads
Cada puerta del estadio funciona con un hilo independiente.
Queue (colas)
Cada puerta posee una cola propia de aficionados.
Implementa el patrón:
Productor → Consumidor
Semaphore
Limita el número de personas que pueden pasar simultáneamente por los tornos de una puerta.
Lock
Protege variables compartidas:
contadores globales
entradas usadas
estadísticas
evitando condiciones de carrera.
Dashboard interactivo
La aplicación incluye un dashboard web desarrollado con Streamlit.

Permite modificar:
Número de aficionados
Número de puertas
Tornos por puerta
Probabilidad de entradas inválidas
Probabilidad de duplicados
Probabilidad de llegadas tarde
Gráficos incluidos
Comparación secuencial vs concurrente

Compara:
Tiempo total secuencial
Tiempo total concurrente
Speedup obtenido
Procesados por puerta
Muestra cuántos aficionados fueron procesados por cada puerta.
Histograma de tiempos de espera
Representa la distribución de tiempos de espera.

Permite observar:
concentración de tiempos
dispersión
colas largas
picos de saturación
Boxplot por puerta

Compara la distribución de tiempos entre puertas:
medianas
dispersión
valores extremos
puertas más saturadas
Estadísticas avanzadas

El sistema calcula:
Media
Mediana
Percentil 95
Tiempo máximo de los tiempos de espera.
Exportación de resultados

La simulación permite descargar resultados en:
CSV
JSON

Ejecución
1. Instalar dependencias
pip install -r requirements.txt
2. Ejecutar la aplicación
streamlit run app.py

Estructura del proyecto
proyecto/
│
├── app.py
├── requirements.txt
└── README.md
Explicación del speedup

El speedup representa cuánto más rápida es la versión concurrente respecto a la secuencial.

Fórmula:

Speedup = Tiempo secuencial / Tiempo concurrente
