"""
Funções de análise usadas pelo dashboard.

Ficam separadas da interface (dashboard.py) de propósito: assim podem ser
testadas sem abrir o Streamlit e reaproveitadas em outros projetos.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from limpeza import ler_arquivo, limpar

COLUNAS_PROBLEMAS = ["arquivo", "linha", "motivo"]


# --------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------
def consolidar(caminhos: list[Path], manter_duplicados: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lê e limpa as planilhas. Devolve (vendas_validas, problemas)."""
    tabelas, avisos = [], []
    for caminho in caminhos:
        novas, novos_avisos = ler_arquivo(caminho)
        tabelas += novas
        avisos += novos_avisos
    avisos_df = pd.DataFrame(avisos, columns=COLUNAS_PROBLEMAS)

    if not tabelas:
        return pd.DataFrame(), avisos_df

    validos, problemas = limpar(pd.concat(tabelas, ignore_index=True), manter_duplicados)
    if not avisos_df.empty:
        problemas = pd.concat([avisos_df, problemas], ignore_index=True)
    validos["total"] = validos["quantidade"] * validos["preco"]
    return validos, problemas


# --------------------------------------------------------------------------
# Formatação (padrão brasileiro)
# --------------------------------------------------------------------------
def formatar_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_percentual(fracao: float) -> str:
    return f"{fracao * 100:.1f}".replace(".", ",") + "%"


def formatar_inteiro(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


# --------------------------------------------------------------------------
# Indicadores
# --------------------------------------------------------------------------
def indicadores(df: pd.DataFrame) -> dict[str, float]:
    faturamento = float(df["total"].sum())
    vendas = len(df)
    return {
        "faturamento": faturamento,
        "itens": float(df["quantidade"].sum()),
        "vendas": vendas,
        "ticket_medio": faturamento / vendas if vendas else 0.0,
    }


def variacao(atual: float, anterior: float) -> float | None:
    """Variação percentual em fração (0.12 = +12%). None se não há base de comparação."""
    if not anterior:
        return None
    return atual / anterior - 1


def periodo_anterior(df: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    """Vendas do período imediatamente anterior, com a mesma duração de [inicio, fim]."""
    dias = (fim - inicio).days + 1
    ini_anterior = pd.Timestamp(inicio - timedelta(days=dias))
    fim_anterior = pd.Timestamp(inicio - timedelta(days=1))
    return df[(df["data"] >= ini_anterior) & (df["data"] <= fim_anterior)]


def serie_temporal(df: pd.DataFrame, frequencia: str) -> pd.DataFrame:
    """Faturamento por dia ('D'), semana ('W') ou mês ('MS'). Períodos sem venda viram 0."""
    serie = df.set_index("data")["total"].resample(frequencia).sum()
    return serie.reset_index().rename(columns={"data": "periodo", "total": "faturamento"})


def por_categoria(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Faturamento, itens e nº de vendas por produto ou vendedor, do maior para o menor."""
    resultado = (
        df.groupby(coluna)
        .agg(faturamento=("total", "sum"), itens=("quantidade", "sum"), vendas=("total", "size"))
        .reset_index()
        .rename(columns={coluna: "categoria"})
        .sort_values("faturamento", ascending=False)
        .reset_index(drop=True)
    )
    return resultado


def matriz_vendedor_produto(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="vendedor", columns="produto", values="total",
                          aggfunc="sum", fill_value=0)


def gerar_destaques(df: pd.DataFrame) -> list[str]:
    """Frases-resumo automáticas (Markdown) sobre o recorte atual."""
    if df.empty:
        return []
    destaques = []
    total = df["total"].sum()

    produtos = por_categoria(df, "produto")
    lider = produtos.iloc[0]
    destaques.append(
        f"**{lider['categoria']}** lidera o faturamento, com "
        f"{formatar_moeda(lider['faturamento'])} ({formatar_percentual(lider['faturamento'] / total)} do total)."
    )
    mais_vendido = produtos.sort_values("itens", ascending=False).iloc[0]
    if mais_vendido["categoria"] != lider["categoria"]:
        destaques.append(
            f"Em volume, o campeão é **{mais_vendido['categoria']}**, "
            f"com {formatar_inteiro(mais_vendido['itens'])} unidades vendidas."
        )

    vendedores = por_categoria(df, "vendedor")
    destaque = vendedores.iloc[0]
    destaques.append(
        f"Maior faturamento entre os vendedores: **{destaque['categoria']}**, "
        f"com {formatar_moeda(destaque['faturamento'])}."
    )

    meses = serie_temporal(df, "MS")
    if len(meses) > 1:
        melhor = meses.sort_values("faturamento", ascending=False).iloc[0]
        destaques.append(
            f"O melhor mês foi **{melhor['periodo']:%m/%Y}**, com {formatar_moeda(melhor['faturamento'])}."
        )
    return destaques
