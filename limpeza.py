"""
Leitura e limpeza das planilhas de vendas.

Aceita arquivos .xlsx e .csv com nomes de colunas, datas e valores em formatos
variados e devolve uma tabela padronizada, junto com a lista de linhas
descartadas e o motivo de cada descarte.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger("limpeza")

# --------------------------------------------------------------------------
# Configuração
# --------------------------------------------------------------------------
COLUNAS_PADRAO = ["data", "produto", "vendedor", "quantidade", "preco"]

# Nomes alternativos aceitos para cada coluna (já sem acento e em minúsculas).
# Para suportar uma planilha nova, basta acrescentar o nome aqui.
APELIDOS = {
    "data": {"data", "dt", "data venda", "data da venda", "date"},
    "produto": {"produto", "item", "descricao", "product"},
    "vendedor": {"vendedor", "vendedora", "responsavel", "seller"},
    "quantidade": {"quantidade", "qtd", "qtde", "quantity"},
    "preco": {"preco", "preco unitario", "valor unitario", "valor", "price"},
}

FORMATOS_DATA = ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y")



# --------------------------------------------------------------------------
# Conversão e limpeza de valores
# --------------------------------------------------------------------------
def normalizar_texto(texto: object) -> str:
    """'Preço Unitário ' -> 'preco unitario' (para comparar nomes de colunas)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[\s_]+", " ", sem_acento).strip().lower()


def converter_numero(valor: object) -> float:
    """Aceita 1234.5, '1.234,50', 'R$ 89,90' etc. Retorna NaN se não der."""
    if pd.isna(valor):
        return float("nan")
    if pd.api.types.is_number(valor):
        return float(valor)
    texto = re.sub(r"[^\d,.\-]", "", str(valor))
    if not texto:
        return float("nan")
    if "," in texto:  # formato brasileiro: ponto separa milhar, vírgula os decimais
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return float("nan")


def converter_data(valor: object) -> pd.Timestamp:
    """Aceita datas do Excel, '2026-03-15', '15/03/2026', '15/03/26'..."""
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, datetime):  # inclui pd.Timestamp
        return pd.Timestamp(valor)
    texto = str(valor).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", texto):
        return pd.to_datetime(texto[:10], format="%Y-%m-%d", errors="coerce")
    for formato in FORMATOS_DATA:
        try:
            return pd.Timestamp(datetime.strptime(texto, formato))
        except ValueError:
            continue
    return pd.NaT


def padronizar_texto(valor: object):
    """'  nOtebook ' -> 'Notebook'. Vazio vira NA."""
    if pd.isna(valor):
        return pd.NA
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return texto.title() if texto else pd.NA


# --------------------------------------------------------------------------
# Leitura
# --------------------------------------------------------------------------
def listar_arquivos(pasta: Path) -> list[Path]:
    extensoes = {".xlsx", ".xlsm", ".csv"}
    return sorted(
        p for p in pasta.iterdir()
        if p.suffix.lower() in extensoes and not p.name.startswith("~$")
    )


def ler_csv(caminho: Path) -> pd.DataFrame:
    """Descobre sozinho o separador (; , ou tab) e o encoding do CSV."""
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with open(caminho, encoding=encoding) as f:
                cabecalho = f.readline()
            separador = max((";", ",", "\t"), key=cabecalho.count)
            return pd.read_csv(caminho, sep=separador, encoding=encoding, dtype=object)
        except UnicodeDecodeError:
            continue
    raise ValueError("encoding do CSV não reconhecido")


def mapear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia as colunas para o padrão interno. Erro se faltar alguma."""
    renomear: dict[str, str] = {}
    for coluna in df.columns:
        chave = normalizar_texto(coluna)
        for padrao, apelidos in APELIDOS.items():
            if chave in apelidos and padrao not in renomear.values():
                renomear[coluna] = padrao
    faltando = [c for c in COLUNAS_PADRAO if c not in renomear.values()]
    if faltando:
        raise ValueError("colunas não encontradas: " + ", ".join(faltando))
    return df.rename(columns=renomear)[COLUNAS_PADRAO].copy()


def ler_arquivo(caminho: Path) -> tuple[list[pd.DataFrame], list[dict]]:
    """Lê um arquivo (todas as abas, se for Excel). Devolve (tabelas, avisos)."""
    tabelas, avisos = [], []
    try:
        if caminho.suffix.lower() == ".csv":
            abas = {None: ler_csv(caminho)}
        else:
            abas = pd.read_excel(caminho, sheet_name=None, dtype=object)
    except Exception as erro:  # arquivo corrompido, protegido por senha etc.
        log.warning("  ! %s ignorado: %s", caminho.name, erro)
        return [], [{"arquivo": caminho.name, "linha": "-", "motivo": f"Arquivo ilegível: {erro}"}]

    for aba, df in abas.items():
        origem = caminho.name if len(abas) == 1 else f"{caminho.name} [{aba}]"
        try:
            df = mapear_colunas(df)
        except ValueError as erro:
            log.warning("  ! %s ignorada: %s", origem, erro)
            avisos.append({"arquivo": origem, "linha": "-", "motivo": f"Aba ignorada: {erro}"})
            continue
        df["linha_origem"] = df.index + 2  # +2: cabeçalho é a linha 1
        df["arquivo"] = origem
        tabelas.append(df)
    return tabelas, avisos


# --------------------------------------------------------------------------
# Limpeza e validação
# --------------------------------------------------------------------------
def validar_linha(linha: dict) -> str:
    """Devolve o motivo da rejeição, ou '' se a linha estiver ok."""
    faltando = [c for c in COLUNAS_PADRAO if pd.isna(linha[c])]
    if faltando:
        return "Campo ausente ou inválido: " + ", ".join(faltando)
    if linha["quantidade"] <= 0:
        return "Quantidade deve ser maior que zero"
    if linha["preco"] < 0:
        return "Preço negativo"
    return ""


def limpar(bruto: pd.DataFrame, manter_duplicados: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (vendas_validas, problemas)."""
    df = bruto.dropna(how="all", subset=COLUNAS_PADRAO).copy()  # some linhas totalmente vazias

    df["data"] = pd.to_datetime(df["data"].map(converter_data))
    df["quantidade"] = df["quantidade"].map(converter_numero)
    df["preco"] = df["preco"].map(converter_numero)
    for coluna in ("produto", "vendedor"):
        df[coluna] = df[coluna].map(padronizar_texto)

    df["motivo"] = [validar_linha(linha) for linha in df.to_dict("records")]
    colunas_problema = ["arquivo", "linha_origem", "motivo"]
    problemas = [df.loc[df["motivo"] != "", colunas_problema]]
    validos = df[df["motivo"] == ""].copy()

    if not manter_duplicados:
        duplicado = validos.duplicated(subset=COLUNAS_PADRAO, keep="first")
        extras = validos[duplicado].assign(motivo="Registro duplicado (ignorado)")
        problemas.append(extras[colunas_problema])
        validos = validos[~duplicado]

    validos = validos.sort_values(["data", "arquivo", "linha_origem"]).reset_index(drop=True)
    validos["mes"] = validos["data"].dt.to_period("M").dt.to_timestamp()

    problemas = pd.concat(problemas, ignore_index=True).rename(columns={"linha_origem": "linha"})
    return validos, problemas
