"""Cria 3 planilhas de exemplo, de propósito bagunçadas, em dados_entrada/.

Cada arquivo usa nomes de colunas, formatos de data e de preço diferentes,
e o de março traz duplicatas, linhas vazias e erros para o painel tratar.
"""
import random
from datetime import datetime
from pathlib import Path

import pandas as pd

random.seed(42)
PASTA = Path("dados_entrada")
PRODUTOS = {"Notebook": 3499.90, "Mouse": 89.90, "Teclado": 199.90,
            "Monitor": 899.00, "Headset": 249.90, "Webcam": 179.90}
PESOS = [1, 6, 4, 2, 3, 3]
VENDEDORES = ["Ana", "Bruno", "Carla", "Diego"]


def gerar_vendas(mes: int, quantidade_linhas: int) -> pd.DataFrame:
    linhas = []
    for _ in range(quantidade_linhas):
        produto = random.choices(list(PRODUTOS), weights=PESOS)[0]
        linhas.append({
            "data": datetime(2026, mes, random.randint(1, 28)),
            "produto": produto,
            "vendedor": random.choice(VENDEDORES),
            "quantidade": random.randint(1, 5),
            "preco": PRODUTOS[produto],
        })
    return pd.DataFrame(linhas)


def preco_brasileiro(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return random.choice(["R$ ", ""]) + texto


def main() -> None:
    PASTA.mkdir(exist_ok=True)

    # Janeiro: Excel "limpo", datas reais do Excel
    jan = gerar_vendas(1, 40)
    jan.columns = ["Data", "Produto", "Vendedor", "Qtd", "Preço Unitário"]
    jan.to_excel(PASTA / "vendas_janeiro.xlsx", index=False)

    # Fevereiro: CSV com ";" e latin-1, datas dd/mm/aaaa e preços "R$ 1.299,90"
    fev = gerar_vendas(2, 45)
    fev["data"] = fev["data"].dt.strftime("%d/%m/%Y")
    fev["preco"] = fev["preco"].map(preco_brasileiro)
    fev.columns = ["Data da Venda", "Item", "Responsável", "Quantidade", "Valor Unitário"]
    fev.to_csv(PASTA / "vendas_fevereiro.csv", sep=";", index=False, encoding="latin-1")

    # Março: cabeçalhos em maiúsculas, texto bagunçado e vários problemas
    mar = gerar_vendas(3, 50)
    mar["data"] = mar["data"].dt.strftime("%Y-%m-%d")
    mar["produto"] = mar["produto"].map(lambda p: random.choice([p.upper(), p.lower(), f"  {p} "]))
    duplicadas = mar.sample(3, random_state=1)
    vazias = pd.DataFrame([[None] * 5] * 2, columns=mar.columns)
    erros = pd.DataFrame([
        {"data": "2026-03-10", "produto": "Mouse", "vendedor": "Ana", "quantidade": 0, "preco": 89.90},
        {"data": "2026-03-11", "produto": "Teclado", "vendedor": None, "quantidade": 2, "preco": 199.90},
        {"data": "99/99/2026", "produto": "Monitor", "vendedor": "Bruno", "quantidade": 1, "preco": 899.00},
    ])
    mar = pd.concat([mar, duplicadas, vazias, erros], ignore_index=True)
    mar.columns = ["DATA", "PRODUTO", "VENDEDOR", "QTDE", "PRECO"]
    mar.to_excel(PASTA / "vendas_marco.xlsx", index=False)

    print(f"Planilhas de exemplo criadas em {PASTA}/")


if __name__ == "__main__":
    main()
