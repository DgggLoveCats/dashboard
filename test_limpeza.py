import math

import pandas as pd
import pytest

from limpeza import converter_data, converter_numero, limpar, mapear_colunas


@pytest.mark.parametrize("entrada, esperado", [
    ("R$ 1.299,90", 1299.90),
    ("89,90", 89.90),
    (150, 150.0),
    ("2500.5", 2500.5),
])
def test_converter_numero(entrada, esperado):
    assert converter_numero(entrada) == pytest.approx(esperado)


@pytest.mark.parametrize("entrada", [None, "", "abc", float("nan")])
def test_converter_numero_invalido(entrada):
    assert math.isnan(converter_numero(entrada))


def test_converter_data_formatos():
    esperado = pd.Timestamp(2026, 3, 5)
    assert converter_data("05/03/2026") == esperado
    assert converter_data("2026-03-05") == esperado
    assert converter_data(pd.Timestamp(2026, 3, 5)) == esperado
    assert pd.isna(converter_data("99/99/2026"))


def test_mapear_colunas_com_apelidos():
    df = pd.DataFrame(columns=["Data da Venda", "Item", "Responsável", "QTDE", "Preço Unitário"])
    assert list(mapear_colunas(df).columns) == ["data", "produto", "vendedor", "quantidade", "preco"]


def test_mapear_colunas_faltando():
    with pytest.raises(ValueError, match="preco"):
        mapear_colunas(pd.DataFrame(columns=["data", "produto", "vendedor", "quantidade"]))


def test_limpar_descarta_invalidos_e_duplicados():
    bruto = pd.DataFrame({
        "data": ["01/02/2026", "01/02/2026", "02/02/2026", "03/02/2026", None],
        "produto": ["  mouse ", "Mouse", "Teclado", "Monitor", None],
        "vendedor": ["ana", "Ana", "Bruno", "Carla", None],
        "quantidade": [2, 2, 0, 1, None],
        "preco": ["R$ 89,90", 89.90, 199.90, 899.0, None],
        "linha_origem": [2, 3, 4, 5, 6],
        "arquivo": ["a.csv"] * 5,
    })
    validos, problemas = limpar(bruto)

    assert len(validos) == 2                       # Mouse (1ª ocorrência) + Monitor
    assert set(validos["produto"]) == {"Mouse", "Monitor"}
    assert len(problemas) == 2                     # quantidade 0 + duplicado (linha vazia é ignorada)
    assert any("duplicado" in m.lower() for m in problemas["motivo"])
