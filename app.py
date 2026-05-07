import threading
import queue
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st


# ══════════════════════════════════════════════
# CONFIGURACIÓN STREAMLIT
# ══════════════════════════════════════════════

st.set_page_config(
    page_title="Simulación Estadio Concurrente",
    layout="wide"
)


# ══════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════

CONFIG = {
    "total_aficionados": 500,
    "aforo_maximo": 450,
    "num_puertas": 4,
    "tornos_por_puerta": 3,
    "tiempo_control_min": 0.005,
    "tiempo_control_max": 0.020,
    "prob_entrada_invalida": 0.05,
    "prob_entrada_duplicada": 0.04,
    "prob_llegada_tarde": 0.10,
    "tiempo_partido": 2.5,
    "velocidad_llegada": 0.002,
    "nombres_puertas": [
        "Norte", "Sur", "Este", "Oeste",
        "VIP", "Prensa", "Visitante", "Accesible"
    ],
    "seed": 42,
}


# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════

st.sidebar.title("Configuración")

CONFIG["total_aficionados"] = st.sidebar.slider(
    "Aficionados",
    100,
    5000,
    CONFIG["total_aficionados"]
)

CONFIG["aforo_maximo"] = st.sidebar.slider(
    "Aforo máximo",
    50,
    CONFIG["total_aficionados"],
    CONFIG["aforo_maximo"]
)

CONFIG["num_puertas"] = st.sidebar.slider(
    "Número de puertas",
    1,
    8,
    CONFIG["num_puertas"]
)

CONFIG["tornos_por_puerta"] = st.sidebar.slider(
    "Tornos por puerta",
    1,
    10,
    CONFIG["tornos_por_puerta"]
)

CONFIG["prob_entrada_invalida"] = st.sidebar.slider(
    "Probabilidad entrada inválida",
    0.0,
    0.3,
    CONFIG["prob_entrada_invalida"]
)

CONFIG["prob_entrada_duplicada"] = st.sidebar.slider(
    "Probabilidad entrada duplicada",
    0.0,
    0.3,
    CONFIG["prob_entrada_duplicada"]
)

CONFIG["prob_llegada_tarde"] = st.sidebar.slider(
    "Probabilidad llegada tarde",
    0.0,
    0.5,
    CONFIG["prob_llegada_tarde"]
)

NOMBRES_PUERTAS = CONFIG["nombres_puertas"][:CONFIG["num_puertas"]]


# ══════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════

def ajustar_ejes(ax, datos, margen=0.10, minimo=1):

    if not datos:
        ax.set_ylim(0, minimo)
        return

    maximo = max(datos)

    if maximo <= 0:
        maximo = minimo

    limite_superior = maximo * (1 + margen)
    limite_superior = max(limite_superior, minimo)

    ax.set_ylim(0, limite_superior)


# ══════════════════════════════════════════════
# ESTADO COMPARTIDO
# ══════════════════════════════════════════════

@dataclass
class EstadoEstadio:

    aforo_maximo: int

    dentro: int = 0
    rechazados: int = 0
    duplicados: int = 0
    tarde: int = 0
    aforo_completo: int = 0

    procesados_puerta: Dict[str, int] = field(default_factory=dict)
    tiempos_espera: Dict[str, list] = field(default_factory=lambda: defaultdict(list))

    entradas_usadas: set = field(default_factory=set)

    lock_global: threading.Lock = field(default_factory=threading.Lock)
    lock_entradas: threading.Lock = field(default_factory=threading.Lock)

    def inicializar_puertas(self, nombres: List[str]):

        for n in nombres:
            self.procesados_puerta[n] = 0
            self.tiempos_espera[n] = []

    def intentar_entrar(self, aficionado, puerta: str) -> str:

        if aficionado.entrada_invalida:

            with self.lock_global:
                self.rechazados += 1
                self.procesados_puerta[puerta] += 1

            return "INVALIDO"

        with self.lock_entradas:

            if aficionado.id_entrada in self.entradas_usadas:

                with self.lock_global:
                    self.duplicados += 1
                    self.procesados_puerta[puerta] += 1

                return "DUPLICADO"

        with self.lock_global:

            if self.dentro >= self.aforo_maximo:

                self.aforo_completo += 1
                self.procesados_puerta[puerta] += 1

                return "AFORO"

            self.dentro += 1
            self.procesados_puerta[puerta] += 1

            with self.lock_entradas:
                self.entradas_usadas.add(aficionado.id_entrada)

        return "OK"

    def registrar_espera(self, puerta: str, segundos: float):

        with self.lock_global:
            self.tiempos_espera[puerta].append(segundos)

    def registrar_tarde(self):

        with self.lock_global:
            self.tarde += 1


# ══════════════════════════════════════════════
# AFICIONADO
# ══════════════════════════════════════════════

@dataclass
class Aficionado:

    aficionado_id: int
    id_entrada: int
    puerta_asignada: str
    entrada_invalida: bool
    hora_llegada: float


# ══════════════════════════════════════════════
# GENERADOR
# ══════════════════════════════════════════════

def generar_aficionados(cfg: dict, nombres_puertas: List[str]):

    random.seed(cfg["seed"])

    total = cfg["total_aficionados"]

    aficionados = []

    ids_entradas = list(range(1, total + 1))

    num_dup = int(total * cfg["prob_entrada_duplicada"])

    duplicados_ids = random.choices(
        ids_entradas[:total // 2],
        k=num_dup
    )

    ids_entradas_con_dup = ids_entradas + duplicados_ids

    random.shuffle(ids_entradas_con_dup)

    ids_entradas_con_dup = ids_entradas_con_dup[:total]

    for i in range(total):

        invalida = random.random() < cfg["prob_entrada_invalida"]

        tarde = random.random() < cfg["prob_llegada_tarde"]

        hora = (
            cfg["tiempo_partido"] * 1.2
            if tarde
            else random.uniform(0, cfg["tiempo_partido"] * 0.95)
        )

        puerta = random.choice(nombres_puertas)

        aficionados.append(
            Aficionado(
                aficionado_id=i + 1,
                id_entrada=ids_entradas_con_dup[i],
                puerta_asignada=puerta,
                entrada_invalida=invalida,
                hora_llegada=hora,
            )
        )

    return sorted(aficionados, key=lambda a: a.hora_llegada)


# ══════════════════════════════════════════════
# WORKER
# ══════════════════════════════════════════════

def worker_puerta(
    nombre,
    cola,
    semaforo,
    estado,
    inicio_partido,
    cfg,
):

    while True:

        try:
            item = cola.get(timeout=0.05)

        except queue.Empty:

            if inicio_partido.is_set() and cola.empty():
                break

            continue

        aficionado, _ = item

        # Llegó tarde
        if aficionado.hora_llegada > cfg["tiempo_partido"]:

            estado.registrar_tarde()

            cola.task_done()

            continue

        # ─────────────────────────────────────
        # MEDICIÓN REAL:
        # espera en cola + control seguridad
        # ─────────────────────────────────────

        t_inicio_total = time.perf_counter()

        semaforo.acquire()

        try:

            # Simulación del control de seguridad
            time.sleep(
                random.uniform(
                    cfg["tiempo_control_min"],
                    cfg["tiempo_control_max"]
                )
            )

            # Tiempo total real
            t_total = time.perf_counter() - t_inicio_total

            # Registrar métrica
            estado.registrar_espera(
                nombre,
                t_total
            )

            # Intentar entrar
            estado.intentar_entrar(
                aficionado,
                nombre
            )

        finally:

            semaforo.release()

        cola.task_done()

# ══════════════════════════════════════════════
# SIMULACIÓN CONCURRENTE
# ══════════════════════════════════════════════

def simular_concurrente(aficionados, cfg):

    estado = EstadoEstadio(cfg["aforo_maximo"])

    estado.inicializar_puertas(NOMBRES_PUERTAS)

    inicio_partido = threading.Event()

    colas = {
        p: queue.Queue()
        for p in NOMBRES_PUERTAS
    }

    semaforos = {
        p: threading.Semaphore(cfg["tornos_por_puerta"])
        for p in NOMBRES_PUERTAS
    }

    workers = []

    for nombre in NOMBRES_PUERTAS:

        t = threading.Thread(
            target=worker_puerta,
            args=(
                nombre,
                colas[nombre],
                semaforos[nombre],
                estado,
                inicio_partido,
                cfg,
            ),
            daemon=True,
        )

        t.start()

        workers.append(t)

    t0 = time.perf_counter()

    def productor():

        t_inicio_sim = time.perf_counter()

        for af in aficionados:

            t_objetivo = (
                t_inicio_sim
                + af.hora_llegada * cfg["velocidad_llegada"] * 10
            )

            ahora = time.perf_counter()

            if t_objetivo > ahora:
                time.sleep(t_objetivo - ahora)

            colas[af.puerta_asignada].put((af, time.perf_counter()))

    hilo_productor = threading.Thread(
        target=productor,
        daemon=True
    )

    hilo_productor.start()

    time.sleep(
        cfg["tiempo_partido"] * cfg["velocidad_llegada"] * 10
    )

    inicio_partido.set()

    hilo_productor.join()

    for w in workers:
        w.join()

    tiempo_total = time.perf_counter() - t0

    return estado, tiempo_total


# ══════════════════════════════════════════════
# SIMULACIÓN SECUENCIAL
# ══════════════════════════════════════════════

def simular_secuencial(aficionados, cfg):

    estado = EstadoEstadio(cfg["aforo_maximo"])

    estado.inicializar_puertas(["Única"])

    t0 = time.perf_counter()

    for af in aficionados:

        if af.hora_llegada > cfg["tiempo_partido"]:

            estado.registrar_tarde()

            continue

        t_inicio = time.perf_counter()

        time.sleep(
            random.uniform(
                cfg["tiempo_control_min"],
                cfg["tiempo_control_max"]
            )
        )

        t_espera = time.perf_counter() - t_inicio

        estado.registrar_espera("Única", t_espera)

        estado.intentar_entrar(af, "Única")

    tiempo_total = time.perf_counter() - t0

    return estado, tiempo_total


# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════

st.title("Simulación Concurrente de Acceso al Estadio")

st.markdown("""
### Conceptos utilizados

- Threads
- Locks
- Semáforos
- Colas
- Productor-consumidor
- Programación concurrente
""")


if st.button("Ejecutar simulación"):

    aficionados = generar_aficionados(
        CONFIG,
        NOMBRES_PUERTAS
    )

    estado_seq, t_seq = simular_secuencial(
        aficionados,
        CONFIG
    )

    estado_conc, t_conc = simular_concurrente(
        aficionados,
        CONFIG
    )

    st.success("Simulación completada")

    # ══════════════════════════════════════════
    # MÉTRICAS
    # ══════════════════════════════════════════

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Entraron", estado_conc.dentro)

    col2.metric("Inválidas", estado_conc.rechazados)

    col3.metric("Duplicadas", estado_conc.duplicados)

    col4.metric("Llegaron tarde", estado_conc.tarde)

    st.divider()

    # ══════════════════════════════════════════
    # COMPARACIÓN
    # ══════════════════════════════════════════

    st.subheader("Comparación secuencial vs concurrente")

    colA, colB = st.columns([1, 1])

    with colA:

        st.metric(
            "Tiempo secuencial",
            f"{t_seq:.3f} s"
        )

        st.metric(
            "Tiempo concurrente",
            f"{t_conc:.3f} s"
        )

        speedup = t_seq / t_conc if t_conc > 0 else 0

        st.metric(
            "Aceleración",
            f"{speedup:.2f}x"
        )

    with colB:

        fig4, ax4 = plt.subplots(figsize=(5.5, 3))

        modos = ["Secuencial", "Concurrente"]

        tiempos = [t_seq, t_conc]

        ax4.bar(modos, tiempos)

        ajustar_ejes(
            ax4,
            tiempos,
            margen=0.20
        )

        for i, v in enumerate(tiempos):

            ax4.text(
                i,
                v + max(tiempos) * 0.03,
                f"{v:.2f}s",
                ha='center'
            )

        ax4.set_title("Tiempo total")
        ax4.set_ylabel("Segundos")

        st.pyplot(fig4)

    st.divider()

    # ══════════════════════════════════════════
    # BARRAS POR PUERTA
    # ══════════════════════════════════════════

    st.subheader("Procesados por puerta")

    fig1, ax1 = plt.subplots(figsize=(6, 3.2))

    puertas = list(estado_conc.procesados_puerta.keys())

    valores = list(estado_conc.procesados_puerta.values())

    ax1.bar(puertas, valores)

    ax1.set_title("Aficionados procesados")

    ax1.set_ylabel("Personas")

    ajustar_ejes(ax1, valores)

    for i, v in enumerate(valores):

        ax1.text(
            i,
            v + max(valores) * 0.02,
            str(v),
            ha='center'
        )

    st.pyplot(fig1)

    # ══════════════════════════════════════════
    # HISTOGRAMA
    # ══════════════════════════════════════════

    st.subheader("Histograma de tiempos de espera")

    fig2, ax2 = plt.subplots(figsize=(6, 3.2))

    esperas_ms = [
        t * 1000
        for lista in estado_conc.tiempos_espera.values()
        for t in lista
    ]

    if esperas_ms:

        bins = min(
            30,
            max(10, int(np.sqrt(len(esperas_ms))))
        )

        ax2.hist(
            esperas_ms,
            bins=bins
        )

        p95 = np.percentile(esperas_ms, 95)

        media = np.mean(esperas_ms)

        ax2.axvline(
            media,
            linestyle='--',
            label=f"Media: {media:.1f} ms"
        )

        ax2.axvline(
            p95,
            linestyle=':',
            label=f"P95: {p95:.1f} ms"
        )

        ax2.legend()

        ax2.set_xlim(
            0,
            max(esperas_ms) * 1.1
        )

    ax2.set_title("Distribución de tiempos")

    ax2.set_xlabel("Tiempo (ms)")

    ax2.set_ylabel("Frecuencia")

    st.pyplot(fig2)

    # ══════════════════════════════════════════
    # BOXPLOT
    # ══════════════════════════════════════════

    st.subheader("Boxplot de espera por puerta")

    fig3, ax3 = plt.subplots(figsize=(6, 2.8))

    esperas_por_puerta = []

    labels = []

    for puerta, tiempos in estado_conc.tiempos_espera.items():

        if tiempos:

            esperas_por_puerta.append([
                t * 1000
                for t in tiempos
            ])

            labels.append(puerta)

    if esperas_por_puerta:

        ax3.boxplot(
            esperas_por_puerta,
            tick_labels=labels,
            vert=False,
            patch_artist=True,
        )

        todos = [
            x
            for lista in esperas_por_puerta
            for x in lista
        ]

        ax3.set_xlim(
            0,
            max(todos) * 1.15
        )

    ax3.set_title("Distribución por puerta")

    ax3.set_xlabel("Tiempo (ms)")

    st.pyplot(fig3)

    # ══════════════════════════════════════════
    # ESTADÍSTICAS AVANZADAS
    # ══════════════════════════════════════════

    st.subheader("Estadísticas avanzadas")

    if esperas_ms:

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Media",
            f"{np.mean(esperas_ms):.2f} ms"
        )

        c2.metric(
            "Mediana",
            f"{np.median(esperas_ms):.2f} ms"
        )

        c3.metric(
            "P95",
            f"{np.percentile(esperas_ms, 95):.2f} ms"
        )

        c4.metric(
            "Máximo",
            f"{np.max(esperas_ms):.2f} ms"
        )