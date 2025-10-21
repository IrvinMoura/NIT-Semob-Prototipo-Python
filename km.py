import streamlit as st
import pandas as pd
import plotly.express as px
from unidecode import unidecode

def main():
    # Título da aplicação
    st.title('Análise de Quilometragem')
    st.markdown('Faça o upload da sua planilha para visualizar a quilometragem percorrida, com falhas e ociosa.')

    # --- Funções auxiliares ---
    def calcular_km_falha(operadora, km_percorrido):
        nome_norm = unidecode(str(operadora)).lower()
        if 'sao joao' in nome_norm or 'são joão' in nome_norm or 'saojoao' in nome_norm:
            return km_percorrido * 1.04
        if 'rosa' in nome_norm:
            return km_percorrido * 1.07
        return km_percorrido

    def calcular_km_ociosa(km_falha):
        return km_falha * 1.05

    uploaded_file = st.file_uploader("Escolha um arquivo Excel (.xlsx), CSV (.csv) ou de Texto (.txt)", type=['xlsx', 'csv', 'txt'])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(('.csv', '.txt')):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
            else:
                df = pd.read_excel(uploaded_file)
            st.success('Arquivo carregado com sucesso!')

            col_map = {
                'Nome Operadora': ['Nome Operadora', 'Nome Garagem'],
                'Distância': ['Distância', 'Distancia'],
                'Passageiros': ['Passageiros'],
                'Intervalo Viagem': ['Intervalo Viagem', 'Intervalo Viagem']
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

            required_cols = list(col_map.keys())
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f'As seguintes colunas não foram encontradas: {", ".join(missing_cols)}')
                st.write(df.columns.tolist())
            else:
                df = df[~df['Nome Operadora'].str.contains('VIAFEIRA', case=False, na=False)].copy()
                df['Intervalo Viagem'] = pd.to_numeric(df['Intervalo Viagem'], errors='coerce')
                df['Passageiros'] = pd.to_numeric(df['Passageiros'], errors='coerce')

                df_filtered = df[~((df['Passageiros'] == 0) & (df['Intervalo Viagem'] < 5))]
                df_filtered['Distância (km)'] = pd.to_numeric(df_filtered['Distância'], errors='coerce').fillna(0) / 1000

                operadoras_km = df_filtered.groupby('Nome Operadora')['Distância (km)'].sum().reset_index()
                operadoras_km.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)

                operadoras_km['Km Falha'] = operadoras_km.apply(
                    lambda row: calcular_km_falha(row['Nome Operadora'], row['Km Percorrido']), axis=1
                )
                operadoras_km['Km Ociosa'] = operadoras_km['Km Falha'].apply(calcular_km_ociosa)

                st.sidebar.header('Filtros')
                operadoras = ['Total Geral'] + sorted(operadoras_km['Nome Operadora'].unique())
                selected_operadora = st.sidebar.selectbox('Selecione a Operadora', operadoras)

                # --- Filtro por Período ---
                if 'Data Coleta' in df.columns:
                    df['Data Coleta'] = pd.to_datetime(df['Data Coleta'], errors='coerce', dayfirst=True)

                    min_date = df['Data Coleta'].min()
                    max_date = df['Data Coleta'].max()

                    start_date, end_date = st.sidebar.date_input(
                        "Selecione o período",
                        [min_date, max_date],
                        min_value=min_date,
                        max_value=max_date
                    )

                    if isinstance(start_date, pd.Timestamp) and isinstance(end_date, pd.Timestamp):
                        df = df[(df['Data Coleta'] >= start_date) & (df['Data Coleta'] <= end_date)]

                st.header('Análise de Quilometragem')
                if not operadoras_km.empty:
                    if selected_operadora != 'Total Geral':
                        data_plot = operadoras_km[operadoras_km['Nome Operadora'] == selected_operadora].copy()
                    else:
                        total_km_percorrido = operadoras_km['Km Percorrido'].sum()
                        total_km_falha = operadoras_km['Km Falha'].sum()
                        total_km_ociosa = operadoras_km['Km Ociosa'].sum()
                        data_plot = pd.DataFrame({
                            'Nome Operadora': ['Total Geral'],
                            'Km Percorrido': [total_km_percorrido],
                            'Km Falha': [total_km_falha],
                            'Km Ociosa': [total_km_ociosa]
                        })

                    plot_df = data_plot.melt(
                        id_vars='Nome Operadora',
                        value_vars=['Km Percorrido', 'Km Falha', 'Km Ociosa'],
                        var_name='Métrica',
                        value_name='Valor (Km)'
                    )

                    fig = px.bar(
                        plot_df,
                        x='Métrica',
                        y='Valor (Km)',
                        title=f'Métricas de Quilometragem para {selected_operadora}',
                        labels={'Valor (Km)': 'Quilometragem (Km)'},
                        color='Métrica',
                        text_auto='.2f'
                    )
                    fig.update_traces(textposition='outside')
                    fig.update_layout(height=600)

                    col1, col2 = st.columns([2.5, 1])
                    with col1:
                        st.plotly_chart(fig, use_container_width=True)
                    with col2:
                        st.subheader('Tabela de Métricas')
                        st.dataframe(plot_df.set_index('Métrica'))
                else:
                    st.warning('Nenhum dado encontrado com os filtros aplicados.')
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
