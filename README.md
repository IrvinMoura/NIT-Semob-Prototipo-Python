# Dashboard de Análise de Frota - SEMOB

Este é um projeto de aplicação web desenvolvido em Python com a biblioteca Streamlit. A ferramenta permite que o usuário faça o upload de um relatório de viagens em formato Excel (.xlsx) e visualize análises interativas sobre a frota de veículos.

## 📋 Funcionalidades

* **Upload de Arquivos:** Permite o upload de relatórios em formato Excel (`.xlsx`).
* **Análise de Frota:** Calcula e exibe a quantidade total de veículos únicos, além da contagem por empresa e por linha.
* **Detecção de Duplicados:** Identifica e exibe registros que possam estar duplicados com base no veículo e no horário de início.
* **Filtros Interativos:** Permite filtrar os dados por um intervalo de horário específico.
* **Visualização de Dados:** Apresenta os dados de forma visual através de gráficos de pizza (distribuição por empresa) e barras (quantidade por linha).

## 🚀 Como Executar o Projeto

Siga os passos abaixo para configurar e rodar a aplicação em seu ambiente local (Windows).

### Pré-requisitos

* **Python 3.8** ou superior instalado na sua máquina. Você pode baixar em [python.org](https://www.python.org/downloads/).

### Passos de Instalação

**1. Clone o Repositório**

Primeiro, clone este repositório para a sua máquina local (ou simplesmente baixe e extraia os arquivos em uma pasta).

```bash
git clone <https://github.com/IrvinMoura/NIT-Semob.git>
cd <NIT-SEMOB>
```

**2. Crie e Ative o Ambiente Virtual (`venv`)**

É uma boa prática usar um ambiente virtual para isolar as dependências do projeto. No Windows, os comandos são os seguintes:

```bash
# 1. Crie o ambiente virtual (será criada uma pasta chamada "venv")
python -m venv venv

# 2. Ative o ambiente virtual
.\venv\Scripts\activate

# 2.1 ou
source venv/bin/activate
```
*Após ativar, você verá `(venv)` no início do seu prompt de comando, indicando que o ambiente está ativo.*

**3. Instale as Bibliotecas Necessárias**

Com o ambiente virtual ativo, instale todas as bibliotecas listadas no arquivo `requirements.txt` com um único comando:

```bash
pip install -r requirements.txt
```

### ▶️ Rodando a Aplicação

Depois de tudo instalado, para iniciar o dashboard, execute o seguinte comando no terminal:

```bash
streamlit run soltura.py
```

Seu navegador abrirá automaticamente com a aplicação rodando.

## 💻 Como Usar

1.  Com a aplicação aberta no navegador, clique no botão **"Browse files"**.
2.  Selecione o arquivo Excel (`.xlsx`) com o relatório de viagens que você deseja analisar.
3.  Aguarde o processamento. Os gráficos e tabelas serão atualizados automaticamente com os dados do seu arquivo.
4.  Use os filtros na barra lateral para refinar sua análise.