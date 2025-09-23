# ipk_app.py
# -*- coding: utf-8 -*-

import pandas as pd
import streamlit as st
import re

def main():
    st.title("Índice de Passageiros por KM por Operadora")

    # Upload do arquivo
    arquivo = st.file_uploader("Escolha o arquivo (Excel, CSV ou TXT)", type=["xlsx", "csv", "txt"])

    if arquivo is not None:
        # Ler arquivo dependendo da extensão
        try:
            colunas_para_ler = [2, 9, 11] # Colunas C, J, L (índices 2, 9, 11)
            if arquivo.name.endswith(".xlsx"):
                df = pd.read_excel(arquivo, usecols=colunas_para_ler, engine='openpyxl')
            else:  # CSV ou TXT
                # Alteração principal: definindo o separador como ';' para garantir a leitura correta
                df = pd.read_csv(arquivo, usecols=colunas_para_ler, sep=';', decimal=',')
            
            st.success(f"Arquivo lido com sucesso. Total de linhas: {len(df)}")

        except Exception as e:
            st.error(f"Erro ao ler o arquivo. Certifique-se de que ele tem as colunas C, J e L: {e}")
            st.stop()

        # Renomear colunas para facilitar
        df.columns = ["Operadora", "Passageiros", "KM"]

        # Converte colunas numéricas
        df["Passageiros"] = pd.to_numeric(df["Passageiros"], errors="coerce")
        df["KM"] = pd.to_numeric(df["KM"], errors="coerce")
        
        # Remove linhas com valores inválidos (NaN) e onde Passageiros é 0
        df = df.dropna(subset=["Passageiros", "KM"])
        df = df[df["Passageiros"] > 0]
        
        st.info(f"Linhas após remover NaN e Passageiros = 0: {len(df)}")
        
        if df.empty:
            st.warning("Nenhuma linha restante após a filtragem inicial. Verifique se as colunas de Passageiros e KM têm dados válidos e se há passageiros > 0.")
            st.stop()

        # Padronização e extração do nome da operadora
        df["Operadora_Principal"] = df["Operadora"].str.extract(r"(Rosa|Sao Joao)", flags=re.IGNORECASE, expand=False)
        
        # Remove linhas onde a extração não encontrou "Rosa" ou "Sao Joao"
        df = df.dropna(subset=["Operadora_Principal"])
        
        st.info(f"Linhas restantes após filtrar por operadora (Rosa ou Sao Joao): {len(df)}")
        
        if df.empty:
            st.warning("Nenhuma linha restante após filtrar por operadora. Verifique se 'Rosa' ou 'Sao Joao' aparecem nos nomes da coluna 'Operadora' (C).")
            st.stop()
        
        # Padroniza os nomes extraídos para "Rosa" e "Sao Joao"
        df["Operadora_Principal"] = df["Operadora_Principal"].str.title().replace('Sao Joao', 'Sao Joao')
        
        # Agrupar, somar e calcular o IPK
        resumo = df.groupby("Operadora_Principal")[["Passageiros", "KM"]].sum().reset_index()
        
        # Evita divisão por zero
        resumo["IPK"] = resumo.apply(lambda row: row["Passageiros"] / row["KM"] if row["KM"] > 0 else 0, axis=1)

        st.subheader("Índice de Passageiros por KM")
        
        # Exibe a tabela final
        st.dataframe(resumo[["Operadora_Principal", "IPK"]].rename(columns={"Operadora_Principal": "Operadora"}))