from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.dashboard.db import VALID_STATUSES, fetch_orders


st.set_page_config(
    page_title="Dashboard de Vendas",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Dashboard de Vendas")
st.caption("Acompanhamento de pedidos, faturamento e produtos.")

STATUS_LABELS = {
    "CRIADO": "Criado",
    "PAGO": "Pago",
    "NOTIFICADO": "Notificado",
}

ORDER_OPTIONS = {
    "Mais recentes": "created_desc",
    "Mais antigos": "created_asc",
    "Maior valor": "total_desc",
    "Menor valor": "total_asc",
}


@st.cache_data(ttl=60, show_spinner=False)
def load_orders(
    start_date,
    end_date_exclusive,
    statuses,
    item_search,
    order_by,
    limit,
):
    """Consulta pedidos no banco e mantém o resultado em cache por 60 s."""
    return fetch_orders(
        start_date=start_date,
        end_date_exclusive=end_date_exclusive,
        statuses=statuses,
        item_search=item_search,
        order_by=order_by,
        limit=limit,
    )


def format_brl(value):
    """Formata valores monetários no padrão brasileiro."""
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


with st.sidebar:
    st.header("Filtros")

    today = date.today()

    start_date = st.date_input(
        "Data inicial",
        value=today - timedelta(days=30),
    )

    end_date = st.date_input(
        "Data final",
        value=today,
    )

    selected_statuses = st.multiselect(
        "Status dos pedidos",
        options=sorted(VALID_STATUSES),
        default=sorted(VALID_STATUSES),
        format_func=lambda status: STATUS_LABELS.get(status, status),
    )

    item_search = st.text_input(
        "Buscar produto",
        placeholder="Digite o nome do produto",
    )

    selected_order = st.selectbox(
        "Ordenação",
        options=list(ORDER_OPTIONS.keys()),
    )

    limit = st.slider(
        "Máximo de registros",
        min_value=1,
        max_value=1000,
        value=500,
        step=50,
    )

    if st.button("Atualizar dados", use_container_width=True):
        st.cache_data.clear()


if start_date > end_date:
    st.error("A data inicial não pode ser posterior à data final.")
    st.stop()


try:
    with st.spinner("Consultando pedidos..."):
        orders = load_orders(
            start_date=start_date,
            end_date_exclusive=end_date + timedelta(days=1),
            statuses=tuple(selected_statuses),
            item_search=item_search,
            order_by=ORDER_OPTIONS[selected_order],
            limit=limit,
        )
except Exception:
    st.error(
        "Não foi possível consultar os pedidos. "
        "Verifique a conexão com o banco de dados e tente novamente."
    )
    st.stop()


df = pd.DataFrame(orders)

if df.empty:
    st.info("Nenhum pedido foi encontrado com os filtros selecionados.")
    st.caption("Altere o período, os status ou o nome do produto.")
    st.stop()


df["valor_total_num"] = pd.to_numeric(
    df["valor_total"],
    errors="coerce",
).fillna(0)

df["quantidade"] = pd.to_numeric(
    df["quantidade"],
    errors="coerce",
).fillna(0)

df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

# Cada pedido é contabilizado uma única vez nos indicadores.
unique_orders = df.drop_duplicates(subset=["pedido_id"]).copy()

# Somente pedidos pagos entram no cálculo do faturamento.
paid_orders_df = unique_orders[
    unique_orders["status"] == "PAGO"
].copy()

total_orders = unique_orders["pedido_id"].nunique()
paid_orders = paid_orders_df["pedido_id"].nunique()

total_revenue = paid_orders_df["valor_total_num"].sum()

# Ticket médio calculado somente sobre pedidos pagos.
average_ticket = (
    total_revenue / paid_orders
    if paid_orders
    else 0
)


st.subheader("Indicadores do período")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Pedidos", f"{total_orders:,}".replace(",", "."))
col2.metric("Faturamento", format_brl(total_revenue))
col3.metric("Pedidos pagos", f"{paid_orders:,}".replace(",", "."))
col4.metric("Ticket médio", format_brl(average_ticket))


st.divider()

left_chart, right_chart = st.columns(2)

with left_chart:
    st.subheader("Faturamento recebido por dia")

    daily_orders = paid_orders_df.dropna(
        subset=["created_at"]
    ).copy()

    daily_orders["data"] = daily_orders["created_at"].dt.date

    daily_revenue = (
        daily_orders.groupby("data")["valor_total_num"]
        .sum()
        .sort_index()
    )

    if daily_revenue.empty:
        st.info(
            "Não há pedidos pagos no período para exibir o faturamento."
        )
    else:
        st.line_chart(daily_revenue)


with right_chart:
    st.subheader("Pedidos por status")

    status_counts = (
        unique_orders.groupby("status")["pedido_id"]
        .nunique()
        .sort_values(ascending=False)
    )

    if status_counts.empty:
        st.info("Não há pedidos para exibir.")
    else:
        status_counts.index = [
            STATUS_LABELS.get(status, status)
            for status in status_counts.index
        ]
        st.bar_chart(status_counts)


st.subheader("5 produtos mais vendidos")

top_products = (
    df.groupby("item_name")["quantidade"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
)

if top_products.empty:
    st.info("Não há produtos para exibir.")
else:
    st.bar_chart(top_products)


st.divider()
st.subheader("Pedidos encontrados")

display_df = df[
    [
        "pedido_id",
        "created_at",
        "status",
        "item_name",
        "quantidade",
        "valor_total_num",
    ]
].copy()

display_df["created_at"] = display_df["created_at"].dt.strftime(
    "%d/%m/%Y %H:%M"
)
display_df["status"] = display_df["status"].map(
    lambda status: STATUS_LABELS.get(status, status)
)
display_df["valor_total_num"] = display_df["valor_total_num"].map(
    format_brl
)

display_df = display_df.rename(
    columns={
        "pedido_id": "Pedido",
        "created_at": "Data e hora",
        "status": "Status",
        "item_name": "Produto",
        "quantidade": "Quantidade",
        "valor_total_num": "Valor total",
    }
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

csv_data = display_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="Baixar pedidos em CSV",
    data=csv_data,
    file_name="pedidos_dashboard.csv",
    mime="text/csv",
)