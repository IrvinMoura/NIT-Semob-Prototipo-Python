import streamlit as st
import pandas as pd
import plotly.express as px
from unidecode import unidecode

# --- Funções auxiliares ---
def calcular_km_falha(operadora, km_percorrido):
    # A lógica de acréscimo é aplicada pela Operadora, não pelo Tipo de Veículo
    nome_norm = unidecode(str(operadora)).lower()
    if 'sao joao' in nome_norm or 'são joão' in nome_norm or 'saojoao' in nome_norm:
        return km_percorrido * 1.04
    if 'rosa' in nome_norm:
        return km_percorrido * 1.07
    return km_percorrido

def calcular_km_ociosa(km_falha):
    return km_falha * 1.05

def main():
    # Título da aplicação
    st.title('Análise de Quilometragem')
    st.markdown('Faça o upload do seu arquivo de texto (.txt) para visualizar a quilometragem percorrida, com falhas e ociosa.')

    # AQUI ESTÁ A MUDANÇA: Aceita apenas '.txt'
    uploaded_file = st.file_uploader("Escolha um arquivo de Texto (.txt)", type=['txt'])

    if uploaded_file:
        try:
            # --- Lógica de Leitura Simplificada para .txt (que pode ser um CSV) ---
            # Removemos a verificação de tipo de arquivo (xlsx, csv) pois só aceitamos .txt agora.
            # E focamos em tentar ler com o separador ';' e tratando encodings comuns.
            
            # Tenta com o separador ';' e utf-8
            try:
                # O Pandas trata arquivos de texto como CSV se eles tiverem um separador
                df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
            except UnicodeDecodeError:
                # Tenta com o separador ';' e latin1
                uploaded_file.seek(0) # Volta para o início do arquivo
                df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
            except Exception:
                # Última tentativa lendo com o separador padrão de CSV (vírgula) ou tabulação, sem encoding
                uploaded_file.seek(0) 
                try:
                    df = pd.read_csv(uploaded_file, sep=';') # Tenta com ';' sem encoding
                except Exception:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep='\t') # Tenta com tabulação


            st.success('Arquivo carregado com sucesso!')

            # --- Mapeamento e Padronização de Colunas ---
            col_map = {
                'Nome Operadora': ['Nome Operadora', 'Nome Garagem'],
                'Distância': ['Distância', 'Distancia'],
                'Passageiros': ['Passageiros'],
                'Intervalo Viagem': ['Intervalo Viagem', 'Intervalo Viagem'],
                # COLUNA MANTIDA: Essencial para a nova tabela detalhada
                'Desc. Tipo Veículo': ['Desc. Tipo Veículo', 'Tipo Veiculo', 'Tipo de Veículo']
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
                st.error(f'As seguintes colunas essenciais não foram encontradas: {", ".join(missing_cols)}')
                st.write('Colunas encontradas no seu arquivo:', df.columns.tolist())
            else:
                # --- Pré-Processamento e Filtros Iniciais ---
                df = df[~df['Nome Operadora'].str.contains('VIAFEIRA', case=False, na=False)].copy()
                df['Intervalo Viagem'] = pd.to_numeric(df['Intervalo Viagem'], errors='coerce')
                df['Passageiros'] = pd.to_numeric(df['Passageiros'], errors='coerce')

                # Filtro de viagens "vazias"
                df_filtered = df[~((df['Passageiros'] == 0) & (df['Intervalo Viagem'] < 5))]
                df_filtered['Distância (km)'] = pd.to_numeric(df_filtered['Distância'], errors='coerce').fillna(0) / 1000

                # --- Configuração dos Filtros na Sidebar ---
                st.sidebar.header('Filtros')

                # 1. Filtro por Período
                df_to_filter = df_filtered.copy() 
                if 'Data Coleta' in df.columns:
                    df_to_filter['Data Coleta'] = pd.to_datetime(df_to_filter['Data Coleta'], errors='coerce', dayfirst=True)
                    min_date = df_to_filter['Data Coleta'].min()
                    max_date = df_to_filter['Data Coleta'].max()

                    if pd.notna(min_date) and pd.notna(max_date):
                        start_date, end_date = st.sidebar.date_input(
                            "Selecione o período",
                            [min_date, max_date],
                            min_value=min_date,
                            max_value=max_date
                        )
                        if isinstance(start_date, pd.Timestamp) and isinstance(end_date, pd.Timestamp):
                            df_to_filter = df_to_filter[(df_to_filter['Data Coleta'] >= start_date) & (df_to_filter['Data Coleta'] <= end_date)].copy()
                
                # 2. Filtro por Operadora
                operadoras = ['Total Geral'] + sorted(df_to_filter['Nome Operadora'].unique().astype(str))
                selected_operadora = st.sidebar.selectbox('Selecione a Operadora', operadoras)

                if selected_operadora != 'Total Geral':
                    # O DataFrame final agora contém apenas a Operadora selecionada
                    df_final = df_to_filter[df_to_filter['Nome Operadora'] == selected_operadora].copy()
                else:
                    # Ou contém todos os dados filtrados por data
                    df_final = df_to_filter.copy()
                
                if df_final.empty:
                    st.warning('Nenhum dado encontrado com os filtros aplicados.')
                    return # Encerra a execução se não houver dados

                # --- Agrupamento e Cálculo Principal (Quilometragem TOTAL por Operadora) ---
                # Este DataFrame é usado para o PRIMEIRO gráfico (Km Percorrido, Km Falha, Km Ociosa)
                operadoras_km_total = df_final.groupby('Nome Operadora')['Distância (km)'].sum().reset_index()
                operadoras_km_total.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                
                # A função 'calcular_km_falha' usa 'Nome Operadora' mesmo para o Total Geral
                operadoras_km_total['Km Falha'] = operadoras_km_total.apply(
                    lambda row: calcular_km_falha(row['Nome Operadora'], row['Km Percorrido']), axis=1
                )
                operadoras_km_total['Km Ociosa'] = operadoras_km_total['Km Falha'].apply(calcular_km_ociosa)


                # --- Exibição Principal (Gráfico 1: Resumo) ---
                st.header(f'Análise de Quilometragem - {selected_operadora}')
                
                if not operadoras_km_total.empty:
                    # Lógica de seleção (Total Geral ou Operadora específica) para o GRÁFICO RESUMO
                    if selected_operadora != 'Total Geral':
                        data_plot = operadoras_km_total[operadoras_km_total['Nome Operadora'] == selected_operadora].copy()
                        title_prefix = f'Métricas de Quilometragem para {selected_operadora}'
                    else:
                        # Cálculo do Total Geral 
                        total_km_percorrido = operadoras_km_total['Km Percorrido'].sum()
                        total_km_falha = operadoras_km_total['Km Falha'].sum()
                        total_km_ociosa = operadoras_km_total['Km Ociosa'].sum()
                        data_plot = pd.DataFrame({
                            'Nome Operadora': ['Total Geral'],
                            'Km Percorrido': [total_km_percorrido],
                            'Km Falha': [total_km_falha],
                            'Km Ociosa': [total_km_ociosa]
                        })
                        title_prefix = 'Métricas de Quilometragem (Total Geral)'

                    # Montagem do DataFrame para o primeiro gráfico
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
                        title=title_prefix, 
                        labels={'Valor (Km)': 'Quilometragem (Km)'},
                        color='Métrica',
                        text_auto='.2f'
                    )
                    fig.update_traces(textposition='outside')
                    fig.update_layout(height=500)

                    col1, col2 = st.columns([2.5, 1])
                    with col1:
                        st.plotly_chart(fig, use_container_width=True)
                    with col2:
                        st.subheader('Tabela de Métricas')
                        st.dataframe(plot_df.set_index('Métrica').style.format({'Valor (Km)': "{:,.2f}"}))
                
                # --- NOVO BLOCO: Tabela detalhada por Tipo de Veículo ---
                st.markdown('---')
                st.subheader(f'Detalhamento de Quilometragem por Tipo de Veículo em {selected_operadora}')

                # Novo agrupamento para criar a tabela detalhada. Agrupamos por Operadora E Tipo.
                tipo_km_detalhe = df_final.groupby(['Nome Operadora', 'Desc. Tipo Veículo'])['Distância (km)'].sum().reset_index()
                tipo_km_detalhe.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                
                # REAPLICAÇÃO DOS CÁLCULOS: Aqui está o ponto chave.
                # Precisamos aplicar o acréscimo de Falha usando a Operadora correta, mesmo no detalhe.
                tipo_km_detalhe['Km Falha'] = tipo_km_detalhe.apply(
                    lambda row: calcular_km_falha(row['Nome Operadora'], row['Km Percorrido']), axis=1
                )
                tipo_km_detalhe['Km Ociosa'] = tipo_km_detalhe['Km Falha'].apply(calcular_km_ociosa)
                
                # Se for "Total Geral", somamos todos os resultados por tipo
                if selected_operadora == 'Total Geral':
                    # Agrupa novamente APENAS por tipo de veículo (somando os Km de todas as operadoras)
                    tabela_final = tipo_km_detalhe.groupby('Desc. Tipo Veículo')[['Km Percorrido', 'Km Falha', 'Km Ociosa']].sum().reset_index()
                else:
                    # Se for uma operadora específica, já temos o detalhamento pronto
                    tabela_final = tipo_km_detalhe.drop(columns=['Nome Operadora'])
                
                # Formatando a tabela para exibição
                tabela_final = tabela_final.sort_values(by='Km Percorrido', ascending=False)
                tabela_final.set_index('Desc. Tipo Veículo', inplace=True)
                
                st.dataframe(
                    tabela_final.style.format("{:,.2f}"), 
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo. Verifique se o formato e o separador estão corretos (esperado: ';'): {e}")

if __name__ == '__main__':
    main()