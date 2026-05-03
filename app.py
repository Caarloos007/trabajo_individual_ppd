import streamlit as st
import threading
import queue
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List
from collections import defaultdict
import matplotlib.pyplot as plt


st.set_page_config(layout="wide")
st.title("⚽ Simulación de Acceso al Estadio")


# ─────────────────────────────
# SIDEBAR
# ─────────────────────────────
st.sidebar.header("Configuración")

total = st.sidebar.slider("Aficionados", 100, 2000, 500)
puertas_n = st.sidebar.slider("Puertas", 1, 6, 4)
tornos = st.sidebar.slider("Tornos por puerta", 1, 10, 3)

PUERTAS = ["Norte", "Sur", "Este", "Oeste", "VIP", "Prensa"][:puertas_n]


# ─────────────────────────────
# MODELOS
# ─────────────────────────────
@dataclass
class Estado:
    aforo: int
    dentro: int = 0
    rechazados: int = 0

    procesados: Dict[str, int] = field(default_factory=dict)
    esperas: Dict[str, list] = field(default_factory=lambda: defaultdict(list))

    lock: threading.Lock = field(default_factory=threading.Lock)

    def init(self, puertas):
        for p in puertas:
            self.procesados[p] = 0
            self.esperas[p] = []

    def entrar(self, puerta):
        with self.lock:
            if self.dentro < self.aforo:
                self.dentro += 1
                self.procesados[puerta] += 1
            else:
                self.rechazados += 1

    def espera(self, puerta, t):
        with self.lock:
            self.esperas[puerta].append(t)


# ─────────────────────────────
# SIMULACIONES
# ─────────────────────────────
def sim_concurrente():
    estado = Estado(int(total * 0.9))
    estado.init(PUERTAS)

    colas = {p: queue.Queue() for p in PUERTAS}
    sems = {p: threading.Semaphore(tornos) for p in PUERTAS}

    for i in range(total):
        colas[random.choice(PUERTAS)].put(i)

    def worker(p):
        while True:
            try:
                _ = colas[p].get(timeout=0.1)
            except:
                break

            t0 = time.perf_counter()
            sems[p].acquire()
            espera = time.perf_counter() - t0

            estado.espera(p, espera)
            time.sleep(random.uniform(0.005, 0.02))
            estado.entrar(p)

            sems[p].release()
            colas[p].task_done()

    threads = []
    t0 = time.perf_counter()

    for p in PUERTAS:
        t = threading.Thread(target=worker, args=(p,))
        t.start()
        threads.append(t)

    for p in PUERTAS:
        colas[p].join()

    return estado, time.perf_counter() - t0


def sim_secuencial():
    estado = Estado(int(total * 0.9))
    estado.init(["Única"])

    t0 = time.perf_counter()

    for _ in range(total):
        time.sleep(random.uniform(0.005, 0.02))
        estado.espera("Única", 0)
        estado.entrar("Única")

    return estado, time.perf_counter() - t0


# ─────────────────────────────
# EJECUCIÓN
# ─────────────────────────────
if st.button("▶ Ejecutar simulación"):

    est_seq, t_seq = sim_secuencial()
    est_conc, t_conc = sim_concurrente()

    # ─────────────────────────
    # MÉTRICAS
    # ─────────────────────────
    st.subheader("📊 Métricas principales")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tiempo secuencial", f"{t_seq:.3f}s")
    col2.metric("Tiempo concurrente", f"{t_conc:.3f}s")
    col3.metric("Speedup", f"{t_seq/t_conc:.2f}x")
    col4.metric("Aficionados dentro", est_conc.dentro)

    # ─────────────────────────
    # MÁS DATOS
    # ─────────────────────────
    st.subheader("📈 Estadísticas")

    espera_media = sum([t for v in est_conc.esperas.values() for t in v]) / max(1, sum(len(v) for v in est_conc.esperas.values()))

    col1, col2, col3 = st.columns(3)
    col1.metric("Espera media", f"{espera_media*1000:.2f} ms")
    col2.metric("Rechazados", est_conc.rechazados)
    col3.metric("Puerta más saturada", max(est_conc.procesados, key=est_conc.procesados.get))

    # ─────────────────────────
    # GRÁFICOS (compactos)
    # ─────────────────────────
    st.subheader("📊 Visualización")

    c1, c2 = st.columns(2)

    # Carga por puerta
    with c1:
        fig = plt.figure(figsize=(4,3))
        plt.title("Carga por puerta")
        plt.bar(est_conc.procesados.keys(), est_conc.procesados.values())
        plt.xticks(rotation=45)
        st.pyplot(fig)

    # Comparación tiempos
    with c2:
        fig = plt.figure(figsize=(4,3))
        plt.title("Tiempo total")
        plt.bar(["Secuencial", "Concurrente"], [t_seq, t_conc])
        st.pyplot(fig)

    # ─────────────────────────
    # HISTOGRAMA
    # ─────────────────────────
    todos = [t for v in est_conc.esperas.values() for t in v]

    c3, c4 = st.columns(2)

    with c3:
        fig = plt.figure(figsize=(4,3))
        plt.title("Histograma esperas")
        plt.hist(todos, bins=30)
        st.pyplot(fig)

    # ─────────────────────────
    # BOXPLOT ARREGLADO
    # ─────────────────────────
    with c4:
        fig = plt.figure(figsize=(4,3))
        plt.title("Boxplot por puerta")
        datos = [est_conc.esperas[p] for p in PUERTAS]
        plt.boxplot(datos)
        plt.xticks(range(1, len(PUERTAS)+1), PUERTAS, rotation=45)
        st.pyplot(fig)