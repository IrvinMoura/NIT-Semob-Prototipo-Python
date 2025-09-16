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
st.info("ℹ️ Exibindo dados para o período fixo da Soltura: 03:40 às 08:00, apenas viagens ociosas saindo da garagem.")

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
    df["Empresa"] = df["Empresa"].str.strip().str.upper() # Usar upper para padronizar
    df["Linha"] = df["Linha"].astype(str).str.strip()
    df["Atendimento"] = df["Atendimento"].astype(str).str.strip()
    df["Veículo"] = df["Veículo"].astype(str).str.strip()
    df["Ponto Início"] = df["Ponto Início"].astype(str).str.lower()

    # Converter a coluna 'Início' para datetime ANTES de usar como chave
    df["Início"] = pd.to_datetime(df["Início"], format="%d/%m/%Y %H:%M:%S", errors='coerce')
    df.dropna(subset=['Início'], inplace=True)

    # Verificação e remoção de duplicatas entre arquivos
    registros_antes = len(df)
    df.drop_duplicates(subset=['Empresa', 'Linha', 'Veículo', 'Início'], keep='first', inplace=True)
    registros_depois = len(df)
    
    st.success(f"✔ Verificação concluída: {registros_antes - registros_depois} registros duplicados foram removidos.")
    st.markdown("---")
    
    # Criar a coluna com o nome completo da linha
    df.dropna(subset=['Linha', 'Atendimento'], inplace=True)
    df['Linha_Completa'] = df['Linha'] + " - " + df['Atendimento']

    # 🔹 4. Aplicar a filtragem correta da Soltura
    hora_inicio = datetime.time(3, 40)
    hora_fim = datetime.time(8, 0)
    df_filtrado_tempo = df[(df["Início"].dt.time >= hora_inicio) & (df["Início"].dt.time <= hora_fim)]
    df_filtrado_ocioso = df_filtrado_tempo[df_filtrado_tempo["Sentido"] == 'ocioso']
    df_soltura = df_filtrado_ocioso[df_filtrado_ocioso["Ponto Início"].str.contains('garagem', na=False)]

    # Filtro de empresa na barra lateral
    st.sidebar.header("Filtros")
    opcoes_filtro = [empresa.upper() for empresa in df_soltura["Empresa"].unique()]
    
    empresa_filtro = st.sidebar.multiselect(
        "Selecione a Empresa:",
        options=opcoes_filtro,
        default=opcoes_filtro
    )
    df_filtrado_final = df_soltura[df_soltura["Empresa"].isin(empresa_filtro)]

    # 🔹 Contagem por empresa
    contagem_empresa = df_filtrado_final.groupby("Empresa")["Veículo"].nunique().reset_index()
    contagem_empresa.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)

    # 🔹 Contagem por linha (destino da soltura)
    contagem_linha = df_filtrado_final.groupby("Linha_Completa")["Veículo"].nunique().reset_index()
    contagem_linha.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)

    # 🔹 Gráfico de pizza (Empresa)
    st.subheader("Distribuição de Veículos por Empresa")

    total_veiculos_grafico = contagem_empresa['Qtd_Veiculos'].sum()
    st.metric(label="Total de Veículos Analisados", value=f"🚍 {total_veiculos_grafico}")
    
    # --- MUDANÇA: Definição do mapa de cores com os códigos Hex ---
    mapa_de_cores = {
        'AUTO ONIBUS SAO JOAO LTDA': '#222a74', # Azul escuro
        'EMPRESA DE ONIBUS ROSA LTDA': '#46b7ac'  # Verde água
    }

    fig1 = px.pie(
        contagem_empresa,
        names="Empresa",
        values="Qtd_Veiculos",
        hole=0.3,
        color="Empresa",
        color_discrete_map=mapa_de_cores
    )
    fig1.update_traces(textinfo="percent+value")
    st.plotly_chart(fig1)

    # 🔹 Gráfico de barras horizontal (Linha)
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