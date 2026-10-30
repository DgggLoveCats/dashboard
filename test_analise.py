from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from analise import (
    consolidar, formatar_moeda, formatar_percentual, gerar_destaques, indicadores,
    matriz_vendedor_produto, periodo_anterior, por_categoria, serie_temporal, variacao,
)

PASTA_EXEMPLO = Path(__file__).parent / "dados_entrada"


@pytest.fixture
def vendas():
    df = pd.DataFrame({
        "data": pd.to_datetime(["2026-01-05", "2026-01-20", "2026-02-03", "2026-02-10"]),
        "produto": ["Mouse", "Notebook", "Mouse", "Teclado"],
        "vendedor": ["Ana", "Bruno", "Ana", "Bruno"],
        "quantidade": [2, 1, 3, 1],
        "preco": [100.0, 3000.0, 100.0, 200.0],
    })
    df["total"] = df["quantidade"] * df["preco"]
    return df


def test_formatacao_brasileira():
    assert formatar_moeda(1234.5) == "R$ 1.234,50"
    assert formatar_percentual(0.3596) == "36,0%"


def test_indicadores(vendas):
    k = indicadores(vendas)
    assert k["faturamento"] == 3700.0
    assert k["itens"] == 7
    assert k["vendas"] == 4
    assert k["ticket_medio"] == 925.0


def test_indicadores_vazio(vendas):
    assert indicadores(vendas.iloc[0:0])["ticket_medio"] == 0.0


def test_variacao():
    assert variacao(150, 100) == pytest.approx(0.5)
    assert variacao(10, 0) is None


def test_periodo_anterior(vendas):
    anterior = periodo_anterior(vendas, date(2026, 2, 1), date(2026, 2, 28))  # 28 dias -> janeiro
    assert len(anterior) == 2
    assert anterior["data"].max() < pd.Timestamp("2026-02-01")


def test_serie_mensal(vendas):
    serie = serie_temporal(vendas, "MS")
    assert list(serie["faturamento"]) == [3200.0, 500.0]


def test_por_categoria_ordena_pelo_faturamento(vendas):
    produtos = por_categoria(vendas, "produto")
    assert list(produtos["categoria"]) == ["Notebook", "Mouse", "Teclado"]
    assert produtos.loc[produtos["categoria"] == "Mouse", "itens"].iloc[0] == 5


def test_matriz(vendas):
    m = matriz_vendedor_produto(vendas)
    assert m.loc["Ana", "Mouse"] == 500.0
    assert m.loc["Ana", "Notebook"] == 0


def test_destaques(vendas):
    texto = " ".join(gerar_destaques(vendas))
    assert "Notebook" in texto and "Mouse" in texto  # líder em valor e em volume
    assert gerar_destaques(vendas.iloc[0:0]) == []


def test_consolidar_dados_de_exemplo():
    caminhos = sorted(PASTA_EXEMPLO.glob("*"))
    validos, problemas = consolidar(caminhos)
    assert len(validos) == 133
    assert len(problemas) == 8
    assert (validos["total"] == validos["quantidade"] * validos["preco"]).all()


def test_consolidar_sem_arquivos_validos(tmp_path):
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("a;b;c\n1;2;3\n")
    validos, problemas = consolidar([ruim])
    assert validos.empty
    assert len(problemas) == 1
