# 📈 Painel de Vendas

Dashboard interativo em Python (Streamlit) que transforma planilhas de vendas, **mesmo bagunçadas e em formatos diferentes**, em indicadores e gráficos que um gestor entende em segundos.

> 📸 *Coloque aqui um print ou GIF do painel (veja a seção "Como apresentar" abaixo).*

## O que ele mostra

- **Indicadores principais:** faturamento, itens vendidos, número de vendas e ticket médio, cada um comparado ao período anterior de mesma duração.
- **"O que os dados dizem":** frases geradas automaticamente (produto líder, campeão em volume, melhor mês, vendedor destaque).
- **Evolução do faturamento** por dia, semana ou mês.
- **Rankings** por produto e por vendedor.
- **Mapa "quem vende o quê":** faturamento de cada vendedor em cada produto.
- **Tabela de vendas** com download em CSV (já no formato que o Excel brasileiro abre direto).
- **Qualidade dos dados:** quantas linhas foram aproveitadas e quais foram descartadas, com o motivo.

Tudo responde aos filtros da barra lateral (período, vendedores e produtos). Também dá para **enviar as suas próprias planilhas** pela interface.

## Como funciona

Antes de desenhar os gráficos, o painel limpa as planilhas (`limpeza.py`): reconhece nomes de colunas diferentes, converte datas e preços em formato brasileiro, padroniza textos, remove duplicatas e descarta linhas inválidas registrando o motivo. A parte de análise fica em `analise.py`, separada da interface, e é coberta por testes.

## Como rodar

Requisito: Python 3.9 ou mais novo.

```bash
# 1. Baixe o projeto e entre na pasta
git clone https://github.com/SEU-USUARIO/dashboard-vendas.git
cd dashboard-vendas

# 2. Instale as dependências
python -m pip install -r requirements.txt

# 3. Abra o painel
python -m streamlit run dashboard.py
```

O painel abre no navegador (geralmente em http://localhost:8501) já com os dados de exemplo da pasta `dados_entrada/`. Para parar, aperte `Ctrl + C` no terminal. Para gerar novos dados de exemplo, rode `python gerar_dados_exemplo.py`.

> No Windows, se o comando `python` não for reconhecido, use `py` no lugar.

### Formato esperado das planilhas

Cinco colunas, com nomes flexíveis: **data, produto, vendedor, quantidade e preço**. Exemplos aceitos: `Qtd`, `QTDE`, `Item`, `Responsável`, `Valor Unitário`.

## Estrutura

```
dashboard.py             # interface (Streamlit + Plotly)
analise.py               # indicadores, séries e rankings (sem interface)
limpeza.py               # leitura e limpeza das planilhas
gerar_dados_exemplo.py   # cria planilhas de exemplo
test_analise.py          # testes da análise
test_limpeza.py          # testes da limpeza
dados_entrada/           # planilhas de exemplo
.streamlit/config.toml   # tema visual
requirements.txt
```

## Testes

```bash
python -m pip install -r requirements-dev.txt
pytest
```

## Publicar online (opcional, mas vale muito no portfólio)

O **Streamlit Community Cloud** hospeda apps gratuitamente a partir de um repositório do GitHub. Com o link público, quem for contratar você abre o painel direto no navegador, sem instalar nada. Depois de publicar, coloque o link no topo deste README.

## Como apresentar no perfil de freelance

Descreva pelo resultado, não pela tecnologia. Por exemplo:

> *"Transformo planilhas espalhadas em um painel interativo: você envia os arquivos e vê faturamento, ranking de produtos e vendedores, evolução por período e comparação com o mês anterior, tudo filtrável e atualizado na hora."*

Dicas: tire um print da tela principal (com os indicadores e o gráfico de evolução) e um da aba "Detalhes", e grave um GIF curto mexendo nos filtros.

## Tecnologias

Python 3.9+, Streamlit, Plotly, pandas, openpyxl.
