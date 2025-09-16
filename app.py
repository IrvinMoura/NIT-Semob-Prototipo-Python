# app.py
# -*- coding: utf-8 -*-

import pandas as pd
import plotly.express as px
import streamlit as st
import datetime

# Configuração da página para o modo "largo"
st.set_page_config(layout="wide")

# ===============================
# Início da Interface do Streamlit
# ===============================
st.title("Dashboard de Análise de Soltura")
st.info("ℹ️ Exibindo dados para o período fixo da Soltura: 03:30 às 08:00, apenas viagens ociosas saindo da garagem.")

# 🔹 1. Upload de múltiplos arquivos pelo usuário
arquivos = st.file_uploader(
    "Escolha os arquivos Excel (um ou mais)",
    type=["xlsx"],
    accept_multiple_files=True
)

if arquivos:
    # 🔹 2. Ler e juntar todos os arquivos enviados
    lista_de_dfs = []
    for arquivo in arquivos:
        df_temp = pd.read_excel(arquivo, usecols=[0, 1, 2, 3, 6, 7, 9, 12])
        lista_de_dfs.append(df_temp)

    df = pd.concat(lista_de_dfs, ignore_index=True)

    # 🔹 3. Renomear e padronizar as colunas
    df.columns = ["Empresa", "Linha", "Atendimento", "Sentido", "Atividade", "Ponto Início", "Veículo", "Início"]
    df["Sentido"] = df["Sentido"].str.strip().str.lower()
    df["Atividade"] = df["Atividade"].str.strip().str.lower()
    df["Empresa"] = df["Empresa"].str.strip()
    df["Linha"] = df["Linha"].astype(str).str.strip()
    df["Atendimento"] = df["Atendimento"].astype(str).str.strip()
    df["Veículo"] = df["Veículo"].astype(str).str.strip()
    df["Ponto Início"] = df["Ponto Início"].astype(str).str.lower()

    # Converter a coluna 'Início' para datetime ANTES de usar como chave
    df["Início"] = pd.to_datetime(df["Início"], format="%d/%m/%Y %H:%M:%S", errors='coerce')
    df.dropna(subset=['Início'], inplace=True)

    # --- MUDANÇA CRÍTICA: Verificação e remoção de duplicatas ---
    registros_antes = len(df)
    # Define uma viagem única pela combinação de Empresa, Linha, Veículo e o horário exato de Início
    df.drop_duplicates(subset=['Empresa', 'Linha', 'Veículo', 'Início'], keep='first', inplace=True)
    registros_depois = len(df)
    
    st.success(f"✔ Verificação concluída: {registros_antes - registros_depois} registros duplicados foram removidos.")
    st.markdown("---") # Adiciona uma linha divisória
    
    # Criar a coluna com o nome completo da linha
    df.dropna(subset=['Linha', 'Atendimento'], inplace=True)
    df['Linha_Completa'] = df['Linha'] + " - " + df['Atendimento']

    # 🔹 4. APLICAR A FILTRAGEM CORRETA DA SOLTURA
    
    # Regra 1: Filtrar pelo horário
    hora_inicio = datetime.time(3, 30)
    hora_fim = datetime.time(8, 0)
    df_filtrado_tempo = df[(df["Início"].dt.time >= hora_inicio) & (df["Início"].dt.time <= hora_fim)]
    
    # Regra 2: Filtrar para pegar somente as viagens ociosas
    df_filtrado_ocioso = df_filtrado_tempo[df_filtrado_tempo["Sentido"] == 'ocioso']
    
    # Regra 3: Filtrar para pegar somente as que saem da garagem
    df_soltura = df_filtrado_ocioso[df_filtrado_ocioso["Ponto Início"].str.contains('garagem', na=False)]

    # Filtro de empresa na barra lateral (agora usa o df_soltura)
    st.sidebar.header("Filtros")
    empresa_filtro = st.sidebar.multiselect(
        "Selecione a Empresa:",
        options=df_soltura["Empresa"].unique(),
        default=df_soltura["Empresa"].unique()
    )
    # Aplica o filtro de empresa selecionado
    df_filtrado_final = df_soltura[df_soltura["Empresa"].isin(empresa_filtro)]

    # 🔹 6. Contagem por empresa
    contagem_empresa = df_filtrado_final.groupby("Empresa")["Veículo"].nunique().reset_index()
    contagem_empresa.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)

    # 🔹 7. Contagem por linha (destino da soltura)
    contagem_linha = df_filtrado_final.groupby("Linha_Completa")["Veículo"].nunique().reset_index()
    contagem_linha.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)

    # 🔹 8. Quantidade total de veículos
    total_veiculos = df_filtrado_final["Veículo"].nunique()
    st.subheader("Resumo da Frota no Período da Soltura")
    st.write(f"🚍 Quantidade total de veículos que realizaram a soltura: {total_veiculos}")

    # 🔹 9. Gráfico de pizza (Empresa)
    st.subheader("Distribuição de Veículos por Empresa")
    fig1 = px.pie(
        contagem_empresa,
        names="Empresa",
        values="Qtd_Veiculos",
        hole=0.3
    )
    fig1.update_traces(textinfo="percent+value")
    st.plotly_chart(fig1)

    # 🔹 10. Gráfico de barras horizontal (Linha)
    st.subheader("Quantidade de Veículos por Linha de Destino (após Soltura)")

    contagem_linha_filtrada = contagem_linha[contagem_linha["Qtd_Veiculos"] > 0]
    contagem_linha_filtrada = contagem_linha_filtrada.sort_values("Qtd_Veiculos", ascending=True)

    altura_dinamica = len(contagem_linha_filtrada) * 35
    altura_final = max(800, altura_dinamica)

    fig2 = px.bar(
        contagem_linha_filtrada,
        x="Qtd_Veiculos",
        y="Linha_Completa",
        orientation="h",
        title="Veículos Únicos por Linha no Período da Soltura",
        labels={"Linha_Completa": "Linha", "Qtd_Veiculos": "Quantidade de Veículos"},
        text="Qtd_Veiculos",
        height=altura_final
    )
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("Por favor, faça o upload de um ou mais arquivos para iniciar a análise.")