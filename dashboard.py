"""
Painel de Vendas (Streamlit)

Lê planilhas de vendas em formatos variados (limpeza em limpeza.py), aplica
filtros e mostra indicadores, gráficos e a tabela de dados.

Rodar:  streamlit run dashboard.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analise import (
    consolidar, formatar_inteiro, formatar_moeda, gerar_destaques, indicadores,
    matriz_vendedor_produto, periodo_anterior, por_categoria, serie_temporal, variacao,
)

PASTA_EXEMPLO = Path(__file__).parent / "dados_entrada"

TEAL = "#0F766E"
TEAL_CLARO = "#E3F0EE"
GRAFITE = "#1B2A2E"

st.set_page_config(page_title="Painel de Vendas", page_icon="📊", layout="wide")

st.markdown(
    f"""
    <style>
      [data-testid="stMetric"] {{
        border-left: 4px solid {TEAL};
        padding: 0.2rem 0 0.2rem 0.9rem;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Dados
# --------------------------------------------------------------------------
def arquivos_de_exemplo() -> tuple[tuple[str, bytes], ...]:
    caminhos = sorted(p for p in PASTA_EXEMPLO.glob("*") if p.suffix.lower() in {".xlsx", ".csv"})
    return tuple((p.name, p.read_bytes()) for p in caminhos)


@st.cache_data(show_spinner="Consolidando as planilhas...")
def carregar(arquivos: tuple[tuple[str, bytes], ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
    with tempfile.TemporaryDirectory() as pasta:
        caminhos = []
        for nome, conteudo in arquivos:
            destino = Path(pasta) / Path(nome).name  # .name evita caminhos maliciosos
            destino.write_bytes(conteudo)
            caminhos.append(destino)
        return consolidar(caminhos)


def estilizar(fig, altura: int = 360):
    """Aparência única para todos os gráficos."""
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=GRAFITE),
        separators=",.",  # padrão brasileiro: vírgula decimal, ponto de milhar
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E5E7EB")
    return fig


def texto_delta(atual: float, anterior: float) -> str | None:
    v = variacao(atual, anterior)
    return None if v is None else f"{v * 100:+.1f}%".replace(".", ",")


# --------------------------------------------------------------------------
# Barra lateral: fonte dos dados e filtros
# --------------------------------------------------------------------------
st.sidebar.header("Dados")
fonte = st.sidebar.radio("Fonte", ["Dados de exemplo", "Enviar minhas planilhas"])

if fonte == "Enviar minhas planilhas":
    enviados = st.sidebar.file_uploader(
        "Planilhas (.xlsx ou .csv)", type=["xlsx", "xlsm", "csv"], accept_multiple_files=True
    )
    arquivos = tuple((f.name, f.getvalue()) for f in enviados)
    if not arquivos:
        st.title("Painel de Vendas")
        st.info("Envie uma ou mais planilhas pela barra lateral. As colunas precisam ser: "
                "data, produto, vendedor, quantidade e preço (os nomes podem variar, "
                "por exemplo Qtd, Item, Valor Unitário).")
        st.stop()
else:
    arquivos = arquivos_de_exemplo()
    if not arquivos:
        st.error("Pasta dados_entrada não encontrada. Rode gerar_dados_exemplo.py primeiro.")
        st.stop()

vendas, problemas = carregar(arquivos)
if vendas.empty:
    st.title("Painel de Vendas")
    st.error("Nenhuma venda válida encontrada. Veja os motivos na tabela abaixo.")
    st.dataframe(problemas, hide_index=True)
    st.stop()

st.sidebar.header("Filtros")
data_min, data_max = vendas["data"].min().date(), vendas["data"].max().date()
periodo = st.sidebar.date_input("Período", value=(data_min, data_max),
                                min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
if len(periodo) != 2:
    st.info("Selecione também a data final do período.")
    st.stop()
inicio, fim = periodo

vendedores = st.sidebar.multiselect("Vendedores", sorted(vendas["vendedor"].unique()),
                                    default=sorted(vendas["vendedor"].unique()))
produtos = st.sidebar.multiselect("Produtos", sorted(vendas["produto"].unique()),
                                  default=sorted(vendas["produto"].unique()))
if not vendedores or not produtos:
    st.warning("Escolha pelo menos um vendedor e um produto.")
    st.stop()

base = vendas[vendas["vendedor"].isin(vendedores) & vendas["produto"].isin(produtos)]
atual = base[(base["data"] >= pd.Timestamp(inicio)) & (base["data"] <= pd.Timestamp(fim))]
if atual.empty:
    st.title("Painel de Vendas")
    st.warning("Nenhuma venda para os filtros escolhidos.")
    st.stop()
anterior = periodo_anterior(base, inicio, fim)


# --------------------------------------------------------------------------
# Página
# --------------------------------------------------------------------------
st.title("Painel de Vendas")
st.caption(f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}, comparado ao período anterior de mesma duração. "
           f"Fonte: {'dados de exemplo' if fonte == 'Dados de exemplo' else 'planilhas enviadas'}.")

kpi_atual, kpi_anterior = indicadores(atual), indicadores(anterior)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Faturamento", formatar_moeda(kpi_atual["faturamento"]),
          texto_delta(kpi_atual["faturamento"], kpi_anterior["faturamento"]))
c2.metric("Itens vendidos", formatar_inteiro(kpi_atual["itens"]),
          texto_delta(kpi_atual["itens"], kpi_anterior["itens"]))
c3.metric("Número de vendas", formatar_inteiro(kpi_atual["vendas"]),
          texto_delta(kpi_atual["vendas"], kpi_anterior["vendas"]))
c4.metric("Ticket médio", formatar_moeda(kpi_atual["ticket_medio"]),
          texto_delta(kpi_atual["ticket_medio"], kpi_anterior["ticket_medio"]))

with st.container(border=True):
    st.markdown("**O que os dados dizem**")
    for frase in gerar_destaques(atual):
        st.markdown(f"- {frase}")

aba_geral, aba_detalhes, aba_qualidade = st.tabs(["Visão geral", "Detalhes", "Qualidade dos dados"])

with aba_geral:
    st.subheader("Evolução do faturamento")
    agrupar = st.radio("Agrupar por", ["Dia", "Semana", "Mês"], index=2, horizontal=True)
    serie = serie_temporal(atual, {"Dia": "D", "Semana": "W", "Mês": "MS"}[agrupar])
    if agrupar == "Mês":
        fig = px.bar(serie, x="periodo", y="faturamento", color_discrete_sequence=[TEAL])
        fig.update_xaxes(tickformat="%m/%Y", dtick="M1")
    else:
        fig = px.line(serie, x="periodo", y="faturamento", color_discrete_sequence=[TEAL])
        fig.update_xaxes(tickformat="%d/%m")
    fig.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>")
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, tickprefix="R$ ")
    st.plotly_chart(estilizar(fig))

    col_produtos, col_vendedores = st.columns(2)
    with col_produtos:
        st.subheader("Faturamento por produto")
        por_produto = por_categoria(atual, "produto").sort_values("faturamento")
        fig = px.bar(por_produto, x="faturamento", y="categoria", orientation="h",
                     color_discrete_sequence=[TEAL])
        fig.update_traces(hovertemplate="%{y}<br>R$ %{x:,.2f}<extra></extra>")
        fig.update_xaxes(title=None, tickprefix="R$ ")
        fig.update_yaxes(title=None)
        st.plotly_chart(estilizar(fig))
    with col_vendedores:
        st.subheader("Faturamento por vendedor")
        por_vendedor = por_categoria(atual, "vendedor")
        fig = px.bar(por_vendedor, x="categoria", y="faturamento", color_discrete_sequence=[TEAL])
        fig.update_traces(hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None, tickprefix="R$ ")
        st.plotly_chart(estilizar(fig))

with aba_detalhes:
    st.subheader("Quem vende o quê")
    st.caption("Faturamento de cada vendedor em cada produto. Quanto mais escuro, maior o valor.")
    matriz = matriz_vendedor_produto(atual)
    fig = px.imshow(matriz, aspect="auto", text_auto=",.0f",
                    color_continuous_scale=[[0, TEAL_CLARO], [1, TEAL]],
                    labels=dict(x="Produto", y="Vendedor", color="Faturamento"))
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(title=None, side="top")
    fig.update_yaxes(title=None)
    st.plotly_chart(estilizar(fig, altura=320))

    st.subheader("Vendas")
    tabela = atual[["data", "produto", "vendedor", "quantidade", "preco", "total", "arquivo"]].rename(
        columns={"data": "Data", "produto": "Produto", "vendedor": "Vendedor",
                 "quantidade": "Quantidade", "preco": "Preço unitário", "total": "Total",
                 "arquivo": "Arquivo de origem"})
    st.dataframe(
        tabela, hide_index=True,
        column_config={
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Preço unitário": st.column_config.NumberColumn(format="R$ %.2f"),
            "Total": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )
    csv = tabela.to_csv(index=False, sep=";", decimal=",", date_format="%d/%m/%Y").encode("utf-8-sig")
    st.download_button("Baixar esta tabela (CSV)", csv, "vendas_filtradas.csv", "text/csv")

with aba_qualidade:
    st.subheader("O que foi tratado nas planilhas")
    st.caption("Nada some em silêncio: toda linha descartada aparece aqui com o motivo.")
    total_lido = len(vendas) + len(problemas)
    q1, q2, q3 = st.columns(3)
    q1.metric("Vendas aproveitadas", formatar_inteiro(len(vendas)))
    q2.metric("Registros descartados", formatar_inteiro(len(problemas)))
    q3.metric("Aproveitamento", f"{len(vendas) / total_lido * 100:.1f}%".replace(".", ",") if total_lido else "-")
    if problemas.empty:
        st.success("Nenhum problema encontrado nas planilhas.")
    else:
        resumo = problemas["motivo"].value_counts().rename_axis("Motivo").reset_index(name="Registros")
        st.dataframe(resumo, hide_index=True)
        st.dataframe(problemas.rename(columns={"arquivo": "Arquivo", "linha": "Linha", "motivo": "Motivo"}),
                     hide_index=True)
