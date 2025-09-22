import streamlit as st
import pandas as pd
import plotly.express as px
from unidecode import unidecode

def main(): 
    # Título da aplicação
    st.title('Análise de Passagens de Ônibus')
    st.markdown('Faça o upload da sua planilha para visualizar os dados de passagens e gerar gráficos interativos.')

    # --- Seção de Upload de Arquivo ---
    uploaded_file = st.file_uploader(
        "Escolha um arquivo Excel (.xlsx), CSV (.csv) ou de Texto (.txt)", 
        type=['xlsx', 'csv', 'txt']
    )

    if uploaded_file:
        try:
            # Carregar o dataframe com base no tipo de arquivo
            if uploaded_file.name.endswith('.csv') or uploaded_file.name.endswith('.txt'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success('Arquivo carregado com sucesso!')

            # --- Processamento dos Dados ---
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

            # Cria dicionário de renomeação usando unidecode
            rename_dict = {}
            for new_name, possible_names in col_map.items():
                for col in df.columns:
                    normalized_col = unidecode(col).lower()
                    normalized_possible_names = [unidecode(p).lower() for p in possible_names]
                    if any(p in normalized_col for p in normalized_possible_names):
                        rename_dict[col] = new_name
                        break

            df.rename(columns=rename_dict, inplace=True)

            # 🔹 Dividir VIAFEIRA SEDE entre Rosa e São João
            if "Nome Operadora" in df.columns:
                viafeira_mask = df["Nome Operadora"].str.contains("VIAFEIRA SEDE", case=False, na=False)
                df_viafeira = df[viafeira_mask].copy()

                if not df_viafeira.empty:
                    # Dividir todos os valores numéricos pela metade
                    cols_numericas = df_viafeira.select_dtypes(include=["number"]).columns
                    df_viafeira[cols_numericas] = df_viafeira[cols_numericas] / 2

                    # Criar duas cópias: uma para Rosa, outra para São João
                    df_rosa = df_viafeira.copy()
                    df_rosa["Nome Operadora"] = "EMPRESA DE ONIBUS ROSA LTDA"

                    df_sjoao = df_viafeira.copy()
                    df_sjoao["Nome Operadora"] = "AUTO ONIBUS SAO JOAO LTDA"

                    # Remover a VIAFEIRA original e adicionar Rosa + São João
                    df = df[~viafeira_mask]
                    df = pd.concat([df, df_rosa, df_sjoao], ignore_index=True)

            # Verificação de colunas obrigatórias
            required_cols = list(col_map.keys())
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                st.error(f'As seguintes colunas não foram encontradas no arquivo: {", ".join(missing_cols)}')
                st.write("Verifique os nomes das colunas no seu arquivo. As colunas encontradas são:")
                st.write(df.columns.tolist())
            else:
                # Conversão numérica
                cols_numeric = ['Inteiras', 'VT', 'VT Integração', 'Gratuidade', 'Passagens',
                                'Passagens Integração', 'Estudantes', 'Estudantes Integração']
                for col in cols_numeric:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                df['Passagens_Inteiras'] = df['Inteiras']
                df['Passagens_VT'] = df['VT']
                df['Passagens_Gratuidade'] = df['Gratuidade']
                df['Passagens_Social'] = df['Passagens']
                df['Passagens_Estudantes'] = df['Estudantes']
                df['Passagens_Integracao'] = (
                    df['VT Integração'] + df['Passagens Integração'] + df['Estudantes Integração']
                )

                # --- Filtros na Sidebar ---
                st.sidebar.header('Filtros')

                # Filtro por Operadora
                operadoras = ['Todas'] + sorted(df['Nome Operadora'].unique())
                selected_operadora = st.sidebar.selectbox('Selecione a Operadora', operadoras)

                # Filtro por Linha
                if selected_operadora != 'Todas':
                    linhas_disponiveis = df[df['Nome Operadora'] == selected_operadora]['Nome Linha'].unique()
                else:
                    linhas_disponiveis = df['Nome Linha'].unique()

                linhas = ['Todas'] + sorted(linhas_disponiveis)
                selected_linha = st.sidebar.selectbox('Selecione a Linha', linhas)

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

                # Aplicação dos filtros Operadora/Linha
                df_filtered = df.copy()
                if selected_operadora != 'Todas':
                    df_filtered = df_filtered[df_filtered['Nome Operadora'] == selected_operadora]
                if selected_linha != 'Todas':
                    df_filtered = df_filtered[df_filtered['Nome Linha'] == selected_linha]
                
                # --- Geração dos Gráficos e Totais ---
                st.header('Análise de Tipos de Passagens')

                if not df_filtered.empty:
                    total_inteiras = df_filtered['Passagens_Inteiras'].sum()
                    total_vt = df_filtered['Passagens_VT'].sum()
                    total_gratuidade = df_filtered['Passagens_Gratuidade'].sum()
                    total_social = df_filtered['Passagens_Social'].sum()
                    total_estudantes = df_filtered['Passagens_Estudantes'].sum()
                    total_integracao = df_filtered['Passagens_Integracao'].sum()
                    
                    total_geral = (total_inteiras + total_vt + total_gratuidade +
                                total_social + total_estudantes + total_integracao)
                    
                    total_data = {
                        'Tipo de Passagem': ['Inteiras', 'VT', 'Gratuidade', 'Social', 'Estudantes', 'Integração', 'Total'],
                        'Quantidade': [
                            total_inteiras,
                            total_vt,
                            total_gratuidade,
                            total_social,
                            total_estudantes,
                            total_integracao,
                            total_geral
                        ]
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

                else:
                    st.warning('Nenhum dado encontrado com os filtros selecionados.')

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
