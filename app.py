# app.py
# -*- coding: utf-8 -*-

import pandas as pd
import plotly.express as px
import streamlit as st

# 🔹 1. Título do app
st.title("Análise de Veículos")

# 🔹 2. Upload do arquivo Excel pelo usuário
arquivo = st.file_uploader("Escolha o arquivo Excel", type=["xlsx"])
if arquivo is not None:
    # 🔹 3. Ler Excel e selecionar colunas desejadas
    df = pd.read_excel(arquivo, usecols=[0, 1, 3, 6, 9, 12])
    df.columns = ["Empresa", "Linha", "Sentido", "Atividade", "Veículo", "Início"]

    # 🔹 3.1 Padronizar colunas de texto
    df["Sentido"] = df["Sentido"].str.strip().str.lower()
    df["Atividade"] = df["Atividade"].str.strip().str.lower()
    df["Empresa"] = df["Empresa"].str.strip()
    df["Linha"] = df["Linha"].astype(str).str.strip()

    # 🔹 Contagem total de veículos (sem duplicados)
    veiculos_totais = df["Veículo"].drop_duplicates()
    st.write(f"Total de veículos diferentes na planilha: {len(veiculos_totais)}")

    # 🔹 Contagem de veículos diferentes por empresa
    contagem_empresa_total = df.groupby("Empresa")["Veículo"].nunique().reset_index()
    contagem_empresa_total.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)
    st.subheader("Veículos diferentes por empresa")
    st.dataframe(contagem_empresa_total)


    # 🔹 4. Converter coluna "Início" para datetime
    df["Início"] = pd.to_datetime(df["Início"], errors="coerce")

    # 🔹 5. Filtrar dados apenas "ociosos" entre 4h e 8h
    df_filtrado = df[
        (df["Sentido"].str.upper() == "OCIOSO") &  # padroniza texto
        (df["Início"].notna()) &  # ignora NaT
        ((df["Início"].dt.hour > 3) | ((df["Início"].dt.hour == 3) & (df["Início"].dt.minute >= 40))) &
        ((df["Início"].dt.hour < 8) | ((df["Início"].dt.hour == 8) & (df["Início"].dt.minute == 0)))
    ]

    # 🔹 5.1 Remover duplicados, mantendo a primeira ocorrência de cada veículo
    df_filtrado = df_filtrado.sort_values("Início").drop_duplicates(subset=["Veículo"], keep="first")

    # 🔹 6. Totais
    veiculos_empresa = df_filtrado.groupby("Empresa")["Veículo"].unique()
    veiculos_linha = df_filtrado.groupby("Linha")["Veículo"].unique()
    todos_veiculos = df_filtrado["Veículo"].unique()

    st.write(f"Total veículos por empresa: {sum(len(v) for v in veiculos_empresa)}")
    st.write(f"Total veículos por linha: {sum(len(v) for v in veiculos_linha)}")
    st.write(f"Total veículos únicos filtrados: {len(todos_veiculos)}")

    # 🔹 Veículos com mais de uma linha
    veiculos_duplicados = df_filtrado.groupby("Veículo")["Linha"].nunique()
    veiculos_duplicados = veiculos_duplicados[veiculos_duplicados > 1].index
    duplicados_detalhes = df_filtrado[df_filtrado["Veículo"].isin(veiculos_duplicados)]
    duplicados_detalhes = duplicados_detalhes[["Veículo", "Linha", "Início"]].sort_values(["Veículo", "Início"])

    st.subheader("Veículos com mais de uma linha registrada")
    st.dataframe(duplicados_detalhes)

    # 🔹 7. Contagem por empresa
    contagem_empresa = df_filtrado.groupby("Empresa")["Veículo"].nunique().reset_index()
    contagem_empresa.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)

    # 🔹 8. Contagem por linha
    contagem_linha = df_filtrado.groupby("Linha")["Veículo"].nunique().reset_index()
    contagem_linha.rename(columns={"Veículo": "Qtd_Veiculos"}, inplace=True)

    # 🔹 9. Quantidade total de veículos
    total_veiculos = df_filtrado["Veículo"].nunique()
    st.write(f"🚍 Quantidade total de veículos que realizaram a soltura: {total_veiculos}")

    # 🔹 10. Gráfico de pizza (Empresa)
    st.subheader("Distribuição de Veículos por Empresa")
    fig1 = px.pie(
        contagem_empresa,
        names="Empresa",
        values="Qtd_Veiculos",
        hole=0.3
    )
    fig1.update_traces(textinfo="percent+value")
    st.plotly_chart(fig1)

    # 🔹 11. Gráfico de barras (Linha)
    contagem_linha_filtrada = contagem_linha[contagem_linha["Qtd_Veiculos"] > 0]
    contagem_linha_filtrada = contagem_linha_filtrada.sort_values("Linha")

    st.subheader("Quantidade de Veículos por Linha")
    fig2 = px.bar(
        contagem_linha_filtrada,
        x="Linha",
        y="Qtd_Veiculos",
        labels={"Linha": "Linha", "Qtd_Veiculos": "Qtd de Veículos"},
        height=600
    )
    fig2.update_traces(text=contagem_linha_filtrada["Qtd_Veiculos"], textposition="inside")
    fig2.update_layout(bargap=0.2)
    st.plotly_chart(fig2)
