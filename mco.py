import streamlit as st
import pandas as pd
import plotly.express as px
from unidecode import unidecode

def main(preloaded_df=None):
    st.set_page_config(layout="wide")
    st.title('Análise de Passagens de Ônibus')
    st.markdown('Faça o upload da sua planilha para visualizar os dados de passagens e gerar gráficos interativos.')

    if preloaded_df is None:
        uploaded_file = st.file_uploader(
            "Escolha um arquivo Excel (.xlsx), CSV (.csv) ou de Texto (.txt)", 
            type=['xlsx', 'csv', 'txt']
        )
        if uploaded_file is None:
            st.info("Aguardando upload do arquivo...")
            return

        if uploaded_file.name.endswith(('.csv', '.txt')):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
            except UnicodeDecodeError:
                df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
        else:
            df = pd.read_excel(uploaded_file)
    else:
        df = preloaded_df.copy()

    # --- renomeação de colunas ---
    col_map = {
        'Nome Operadora': ['Nome Operadora', 'Nome Garagem'],
        'Código Externo Linha': ['Codigo Externo Linha', 'Cod. Externo Linha'],
        'Nome Linha': ['Nome Linha'],
        'Inteiras': ['Inteiras'],
        'VT': ['VT'],
        'VT Integração': ['VT Integracao', 'VT Integração'],
        'Gratuidade': ['Gratuidade'],
        'Passagens': ['Passagens'],
        'Passagens Integração': ['Passagens Integracao', 'Passagens Integração'],
        'Estudantes': ['Estudantes'],
        'Estudantes Integração': ['Estudantes Integracao', 'Estudantes Integração']
    }
    rename_dict = {}
    for new_name, possible_names in col_map.items():
        for col in df.columns:
            normalized_col = unidecode(col).lower()
            normalized_possible_names = [unidecode(p).lower() for p in possible_names]
            if any(p in normalized_col for p in normalized_possible_names):
                rename_dict[col] = new_name
                break
    df.rename(columns=rename_dict, inplace=True)

    # --- Conversões numéricas ---
    cols_numeric = ['Inteiras', 'VT', 'VT Integração', 'Gratuidade',
                    'Passagens', 'Passagens Integração',
                    'Estudantes', 'Estudantes Integração']
    for col in cols_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Passagens_Inteiras'] = df.get('Inteiras', 0)
    df['Passagens_VT'] = df.get('VT', 0)
    df['Passagens_Gratuidade'] = df.get('Gratuidade', 0)
    df['Passagens_Social'] = df.get('Passagens', 0)
    df['Passagens_Estudantes'] = df.get('Estudantes', 0)
    df['Passagens_Integracao'] = (
        df.get('VT Integração', 0) +
        df.get('Passagens Integração', 0) +
        df.get('Estudantes Integração', 0)
    )

    # --- Filtros na Sidebar ---
    st.sidebar.header('Filtros')
    operadoras = ['Todas'] + sorted(df['Nome Operadora'].unique()) if 'Nome Operadora' in df.columns else ['Todas']
    selected_operadora = st.sidebar.selectbox('Selecione a Operadora', operadoras)

    if selected_operadora != 'Todas' and 'Nome Linha' in df.columns:
        linhas_disponiveis = df[df['Nome Operadora'] == selected_operadora]['Nome Linha'].unique()
    elif 'Nome Linha' in df.columns:
        linhas_disponiveis = df['Nome Linha'].unique()
    else:
        linhas_disponiveis = []

    linhas = ['Todas'] + sorted(linhas_disponiveis)
    selected_linha = st.sidebar.selectbox('Selecione a Linha', linhas)

    df_filtered = df.copy()
    if selected_operadora != 'Todas':
        df_filtered = df_filtered[df_filtered['Nome Operadora'] == selected_operadora]
    if selected_linha != 'Todas' and 'Nome Linha' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Nome Linha'] == selected_linha]

    # --- Filtro de datas ---
    if 'Data Coleta' in df.columns:
        s = df['Data Coleta'].astype(str).str.strip()
        parsed = pd.to_datetime(s, format="%d/%m/%Y", dayfirst=True, errors='coerce')
        parsed_alt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        df['Data Coleta'] = parsed.fillna(parsed_alt)

        df_valid = df[df['Data Coleta'].notna()]
        if not df_valid.empty:
            min_date = df_valid['Data Coleta'].min().date()
            max_date = df_valid['Data Coleta'].max().date()
            periodo = st.sidebar.date_input(
                "Período",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
            if isinstance(periodo, (list, tuple)):
                start_date, end_date = periodo
            else:
                start_date = periodo
                end_date = periodo
            if isinstance(start_date, pd.Timestamp):
                start_date = start_date.date()
            if isinstance(end_date, pd.Timestamp):
                end_date = end_date.date()
            mask_date = (
                df['Data Coleta'].notna() &
                (df['Data Coleta'].dt.date >= start_date) &
                (df['Data Coleta'].dt.date <= end_date)
            )
            df = df.loc[mask_date].copy()

    # --- Saída ---
    st.header('Análise de Tipos de Passagens')
    if not df_filtered.empty:
        total_inteiras = df_filtered['Passagens_Inteiras'].sum()
        total_vt = df_filtered['Passagens_VT'].sum()
        total_gratuidade = df_filtered['Passagens_Gratuidade'].sum()
        total_social = df_filtered['Passagens_Social'].sum()
        total_estudantes = df_filtered['Passagens_Estudantes'].sum()
        total_integracao = df_filtered['Passagens_Integracao'].sum()
        total_geral = total_inteiras + total_vt + total_gratuidade + total_social + total_estudantes + total_integracao

        total_data = {
            'Tipo de Passagem': ['Inteiras', 'VT', 'Gratuidade', 'Social', 'Estudantes', 'Integração', 'Total'],
            'Quantidade': [total_inteiras, total_vt, total_gratuidade, total_social, total_estudantes, total_integracao, total_geral]
        }
        total_df = pd.DataFrame(total_data)

        fig = px.bar(
            total_df,
            x='Tipo de Passagem',
            y='Quantidade',
            title='Quantidade de Passagens por Tipo',
            labels={'Quantidade': 'Total de Passagens'},
            color='Tipo de Passagem',
            text='Quantidade'
        )
        col1, col2 = st.columns([2.5, 1])
        with col1:
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader('Totais')
            st.dataframe(total_df, use_container_width=True)

        # --- 📊 NOVA TABELA: Média de Passageiros por Empresa ---
        st.subheader("📊 Média de Passageiros por Empresa")

        # Se existir coluna Passageiros, usa ela
        if 'Passageiros' in df.columns:
            media_df = df.groupby('Nome Operadora')['Passageiros'].mean().reset_index()
            media_df.rename(columns={'Passageiros': 'Média de Passageiros'}, inplace=True)
        else:
            # Se não existir, usa soma das passagens como proxy
            df['Total_Passagens'] = (
                df['Passagens_Inteiras'] +
                df['Passagens_VT'] +
                df['Passagens_Gratuidade'] +
                df['Passagens_Social'] +
                df['Passagens_Estudantes'] +
                df['Passagens_Integracao']
            )
            media_df = df.groupby('Nome Operadora')['Total_Passagens'].mean().reset_index()
            media_df.rename(columns={'Total_Passagens': 'Média de Passageiros'}, inplace=True)

        st.dataframe(media_df, use_container_width=True)

    else:
        st.warning('Nenhum dado encontrado com os filtros selecionados.')