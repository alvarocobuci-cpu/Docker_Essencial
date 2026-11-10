import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import redis
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import metrics_data


st.set_page_config(
    page_title="Observabilidade da API",
    page_icon="📊",
    layout="wide",
)

PERIOD_OPTIONS = {
    "Última hora": 1,
    "Últimas 6 horas": 6,
    "Últimas 24 horas": 24,
    "Últimos 7 dias": 168,
    "Todo o período": None,
}


@st.cache_data(ttl=10, show_spinner=False)
def load_request_records():
    """Carrega e normaliza os eventos HTTP armazenados no Redis."""
    return metrics_data.parse_request_events(
        metrics_data.load_request_events()
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_cache_records():
    """Carrega as estatisticas de cache do microsservico de inventario."""
    return metrics_data.load_cache_metrics()


@st.cache_data(ttl=10, show_spinner=False)
def load_messaging_records():
    """Carrega e normaliza os eventos de mensageria."""
    return metrics_data.parse_messaging_events(
        metrics_data.load_messaging_events()
    )


st.title("📊 Dashboard de Desempenho da API")
st.caption(
    "Monitoramento de latência, volume de requisições "
    "e respostas HTTP do SynapseShop."
)

try:
    records = load_request_records()
except redis.RedisError as error:
    st.error(f"Não foi possível conectar ao Redis: {error}")
    st.stop()

if not records:
    st.warning(
        "Nenhuma métrica encontrada. Faça requisições à API "
        "para começar a alimentar o painel."
    )
    st.stop()

st.sidebar.header("Filtros")

selected_period = st.sidebar.selectbox(
    "Período",
    list(PERIOD_OPTIONS.keys()),
)

records = metrics_data.filter_by_period(
    records,
    now=time.time(),
    hours=PERIOD_OPTIONS[selected_period],
)

endpoints = sorted(
    {
        record["endpoint"]
        for record in records
        if record["endpoint"]
    }
)

selected_endpoints = st.sidebar.multiselect(
    "Endpoints",
    endpoints,
    default=endpoints,
)

records = metrics_data.filter_by_endpoints(
    records,
    selected_endpoints,
)

status_groups = sorted(
    {record["status_group"] for record in records}
)

selected_statuses = st.sidebar.multiselect(
    "Status HTTP",
    status_groups,
    default=status_groups,
)

records = metrics_data.filter_by_status_groups(
    records,
    selected_statuses,
)

st.sidebar.caption("Os dados são atualizados a cada 10 segundos.")

if not records:
    st.warning("Nenhuma requisição encontrada com os filtros selecionados.")
    st.stop()

kpis = metrics_data.compute_kpis(records)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de requisições", kpis["total_requests"])
col2.metric(
    "Latência média",
    f"{kpis['average_latency_ms']:.2f} ms",
)
col3.metric(
    "Latência p95",
    f"{kpis['p95_latency_ms']:.2f} ms",
)
col4.metric(
    "Taxa de erros",
    f"{kpis['error_rate_percent']:.2f}%",
)

st.divider()

st.subheader("Latência ao longo do tempo")

latency_rows = metrics_data.aggregate_latency_by_minute(records)
df_latency = pd.DataFrame(latency_rows)
df_latency["horario"] = pd.to_datetime(
    df_latency["minute"],
    unit="s",
    utc=True,
)

fig_latency = px.line(
    df_latency,
    x="horario",
    y="average_latency_ms",
    markers=True,
    labels={
        "horario": "Horário",
        "average_latency_ms": "Latência média (ms)",
    },
)

st.plotly_chart(fig_latency, width="stretch")

st.subheader("Volume de requisições")

throughput_rows = metrics_data.aggregate_throughput_by_minute(records)
df_throughput = pd.DataFrame(throughput_rows)
df_throughput["horario"] = pd.to_datetime(
    df_throughput["minute"],
    unit="s",
    utc=True,
)

fig_requests = px.bar(
    df_throughput,
    x="horario",
    y="requests",
    labels={
        "horario": "Horário",
        "requests": "Requisições",
    },
)

st.plotly_chart(fig_requests, width="stretch")

st.subheader("Distribuição dos códigos HTTP")

status_rows = metrics_data.aggregate_status_distribution(records)
df_status = pd.DataFrame(status_rows)

fig_status = px.pie(
    df_status,
    names="status_group",
    values="count",
    hole=0.4,
    labels={
        "status_group": "Grupo HTTP",
        "count": "Quantidade",
    },
)

st.plotly_chart(fig_status, width="stretch")

st.divider()

st.subheader("Cache do inventário")

try:
    cache_rows = load_cache_records()
except redis.RedisError as error:
    st.warning(f"Não foi possível ler as métricas de cache: {error}")
    cache_rows = []

if cache_rows:
    df_cache = pd.DataFrame(cache_rows)

    total_hits = int(df_cache["hits"].sum())
    total_lookups = int(df_cache["lookups"].sum())
    overall_rate = (
        (total_hits / total_lookups) * 100 if total_lookups else 0.0
    )

    cache_col1, cache_col2, cache_col3 = st.columns(3)
    cache_col1.metric("Cache hits", total_hits)
    cache_col2.metric(
        "Cache misses",
        int(df_cache["misses"].sum()),
    )
    cache_col3.metric("Hit rate", f"{overall_rate:.2f}%")

    fig_cache = px.bar(
        df_cache,
        x="endpoint",
        y=["hits", "misses"],
        barmode="group",
        labels={
            "endpoint": "Endpoint",
            "value": "Eventos",
            "variable": "Resultado",
        },
    )

    st.plotly_chart(fig_cache, width="stretch")

    st.dataframe(
        df_cache.rename(
            columns={
                "endpoint": "Endpoint",
                "hits": "Hits",
                "misses": "Misses",
                "lookups": "Consultas",
                "hit_rate_percent": "Hit rate (%)",
            }
        ),
        width="stretch",
        hide_index=True,
    )
else:
    st.info(
        "Nenhuma estatística de cache registrada. Faça consultas "
        "aos endpoints do inventário para popular os contadores."
    )

st.subheader("Mensageria")

try:
    messaging_records = load_messaging_records()
except redis.RedisError as error:
    st.warning(
        f"Não foi possível ler as métricas de mensageria: {error}"
    )
    messaging_records = []

if messaging_records:
    messaging_rows = metrics_data.aggregate_messaging(
        messaging_records
    )
    df_messaging = pd.DataFrame(messaging_rows)

    fig_messaging = px.bar(
        df_messaging,
        x="direction",
        y="count",
        color="outcome",
        barmode="group",
        labels={
            "direction": "Direção",
            "count": "Eventos",
            "outcome": "Resultado",
        },
    )

    st.plotly_chart(fig_messaging, width="stretch")
else:
    st.info(
        "Nenhum evento de mensageria registrado. O painel está "
        "pronto para exibir os dados assim que a instrumentação "
        "de produtores e consumidores for habilitada."
    )

st.divider()

st.subheader("Requisições registradas")

display_df = pd.DataFrame(records)[
    [
        "timestamp",
        "method",
        "endpoint",
        "status_code",
        "duration_ms",
    ]
].copy()

display_df["timestamp"] = pd.to_datetime(
    display_df["timestamp"],
    unit="s",
    utc=True,
)

display_df = display_df.sort_values(
    "timestamp",
    ascending=False,
)

display_df.columns = [
    "Data e hora",
    "Método",
    "Endpoint",
    "Status HTTP",
    "Latência (ms)",
]

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
)

if st.button("Atualizar métricas"):
    load_request_records.clear()
    load_cache_records.clear()
    load_messaging_records.clear()
    st.rerun()
