import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def main():
    # Configuração da página do Streamlit
    st.set_page_config(
        page_title="Análise de Horário de Pico de Passageiros por Linha",
        layout="wide"
    )

    # --- Índices das Colunas (Base 0) ---
    COLUNA_CODIGO_LINHA = 4
    COLUNA_PASSAGEIROS = 28
    COLUNA_DATA_HORA = 42
    # ---------------------------------------------

    # Nomes dos dias da semana para as colunas
    NOMES_DIAS = {
        0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 
        4: 'Sexta', 5: 'Sábado', 6: 'Domingo'
    }
    DIAS_UTEIS_NUM = [0, 1, 2, 3, 4]

    def get_agregacao_info(dia_nome):
        """
        Retorna o tipo de agregação (função e nome) com base no Dia da Semana.
        ATUALIZAÇÃO: AGORA RETORNA SEMPRE SOMA (sum) para todos os dias,
        conforme solicitação. O cálculo da média diária é feito na função de pico.
        """
        # A agregação primária agora é sempre SOMA (total de passageiros na hora)
        return 'sum', 'Soma', 'passageiros (total na hora)'

    # @st.cache_data removido da leitura para evitar MemoryError em arquivos grandes.
    def carregar_dados(uploaded_file):
        """Carrega o arquivo (CSV ou Excel) e faz o pré-processamento inicial."""
        with st.spinner('Carregando e pré-processando a planilha...'):
            try:
                # 1. Detectar o tipo de arquivo e carregar
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if file_extension == 'csv':
                    df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
                elif file_extension in ['xlsx', 'xls']:
                    df = pd.read_excel(uploaded_file)
                else:
                    st.error("Formato de arquivo não suportado. Use CSV, XLSX ou XLS.")
                    return pd.DataFrame()

                # 2. Renomeia e prepara colunas
                max_col_index = max(COLUNA_CODIGO_LINHA, COLUNA_PASSAGEIROS, COLUNA_DATA_HORA)
                if len(df.columns) <= max_col_index:
                    st.error(f"Erro: O arquivo tem apenas {len(df.columns)} colunas. Certifique-se de que ele tem as colunas E (4), AC (28) e AQ (42).")
                    return pd.DataFrame()
                    
                colunas_importantes = {
                    df.columns[COLUNA_CODIGO_LINHA]: 'Código Externo Linha',
                    df.columns[COLUNA_DATA_HORA]: 'Data Hora Início',
                    df.columns[COLUNA_PASSAGEIROS]: 'Passageiros'
                }
                
                df = df.rename(columns=colunas_importantes)
                
                # Pré-processamento
                df['Código Externo Linha'] = df['Código Externo Linha'].astype(str)
                df['Data Hora Início'] = pd.to_datetime(df['Data Hora Início'], errors='coerce')
                df = df.dropna(subset=['Data Hora Início'])
                
                df['Hora'] = df['Data Hora Início'].dt.hour.astype(str).str.zfill(2) + ':00'
                df['Dia da Semana'] = df['Data Hora Início'].dt.dayofweek
                
                df['Passageiros'] = pd.to_numeric(df['Passageiros'], errors='coerce').fillna(0).astype(int)
                
                # Cria a coluna granular do dia da semana (Segunda, Terça, etc.)
                df['Dia Nome'] = df['Data Hora Início'].dt.dayofweek.map(NOMES_DIAS)
                
                return df

            except Exception as e:
                st.error(f"Erro ao carregar ou processar o arquivo: {e}")
                return pd.DataFrame()


    @st.cache_data
    def calcular_pico_agrupado(df_filtrado):
        """
        Calcula o horário de pico com agregação granular por dia da semana.
        ATUALIZADO: Agregação granular é sempre SOMA. Dia Útil é Média da Soma.
        """
        
        # 1. Agregação Granular (Soma para todos os dias)
        
        df_agregado_granular = pd.DataFrame()
        
        for dia_num, dia_nome in NOMES_DIAS.items():
            
            # agg_func agora sempre é 'sum'
            agg_func, agg_name, _ = get_agregacao_info(dia_nome)
            
            df_dia = df_filtrado[df_filtrado['Dia Nome'] == dia_nome]
            
            # Agrega: Soma (Total de passageiros na hora)
            df_agreg = df_dia.groupby(['Dia Nome', 'Hora'])['Passageiros'].agg(agg_func).reset_index()
            df_agreg.rename(columns={'Passageiros': 'Valor Agregado'}, inplace=True)
            df_agreg['Agregacao'] = agg_name
            
            df_agregado_granular = pd.concat([df_agregado_granular, df_agreg])

        df_agregado_granular['Valor Agregado'] = df_agregado_granular['Valor Agregado'].round(2)
        
        # Pivoteamento para ter Dia Nome como Coluna
        tabela_granular = df_agregado_granular.pivot_table(
            index='Hora', columns='Dia Nome', values='Valor Agregado'
        ).fillna(0).reset_index()
        
        # Ordena as colunas dos 7 dias e preenche faltantes com 0
        ordem_dias = list(NOMES_DIAS.values())
        tabela_granular = tabela_granular[[c for c in ['Hora'] + ordem_dias if c in tabela_granular.columns]]

        # 2. Cálculo da Média de Dia Útil (Média da SOMA de Seg a Sex)
        dias_uteis_cols = [NOMES_DIAS[d] for d in DIAS_UTEIS_NUM if NOMES_DIAS[d] in tabela_granular.columns]
        
        # NOVO NOME DA COLUNA
        NOME_COLUNA_DIA_UTIL = 'Dia Útil (Média da Soma)'
        
        if dias_uteis_cols:
            # Calcula a média da Soma total dos dias úteis
            tabela_granular[NOME_COLUNA_DIA_UTIL] = tabela_granular[dias_uteis_cols].mean(axis=1).round(2)
        else:
            tabela_granular[NOME_COLUNA_DIA_UTIL] = 0

        # 3. Identifica o horário de pico
        picos = {}
        
        # Tipos de dias para os quais o pico será calculado
        pico_tipos = [NOME_COLUNA_DIA_UTIL, 'Sábado', 'Domingo']
        
        for tipo in pico_tipos:
            
            # Mapeia o nome do tipo de pico para o nome da coluna no DF
            tipo_coluna = NOME_COLUNA_DIA_UTIL if tipo == NOME_COLUNA_DIA_UTIL else tipo
            
            if tipo_coluna in tabela_granular.columns and not tabela_granular[tipo_coluna].empty and tabela_granular[tipo_coluna].max() > 0:
                
                pico_hora = tabela_granular.loc[tabela_granular[tipo_coluna].idxmax()]['Hora']
                pico_valor = tabela_granular[tipo_coluna].max()
                
                # Ajuste o nome da agregação para o display
                if NOME_COLUNA_DIA_UTIL in tipo:
                    agg_name, agg_label = 'Média', 'passageiros (média das somas por hora)'
                    
                else:
                    # Sábado e Domingo continuam como Soma
                    agg_func, agg_name, agg_label = get_agregacao_info(tipo)
                
                picos[tipo] = {
                    'Hora': pico_hora, 
                    'Valor Pico': pico_valor, # VALOR ORIGINAL (COM .ROUND(2))
                    'Agregacao': agg_name,
                    'Label': agg_label
                }
            else:
                picos[tipo] = {'Hora': 'N/A', 'Valor Pico': 0, 'Agregacao': 'N/A', 'Label': ''}

        # 4. Detalhamento por Linha no Horário de Pico
        df_detalhe = pd.DataFrame()
        
        # Detalhamento é feito na Hora do Pico
        detalhe_map = {
            NOME_COLUNA_DIA_UTIL: NOMES_DIAS[DIAS_UTEIS_NUM[0]], # Pega a Segunda-feira como referência
            'Sábado': 'Sábado',
            'Domingo': 'Domingo'
        }

        for tipo_pico, pico_info in picos.items():
            if pico_info['Hora'] != 'N/A':
                hora_pico = pico_info['Hora']
                
                # Encontra o dia de referência para o detalhe
                dia_ref_nome = detalhe_map.get(tipo_pico, tipo_pico)
                
                # Ajusta a função de agregação para o detalhe (Será 'sum' para Sáb/Dom)
                agg_func, agg_name, _ = get_agregacao_info(dia_ref_nome)

                # Filtra o dataframe original pela HORA do pico e pelo TIPO DE DIA
                df_pico = df_filtrado[
                    (df_filtrado['Hora'] == hora_pico) & 
                    (df_filtrado['Dia Nome'].isin(dias_uteis_cols) if tipo_pico == NOME_COLUNA_DIA_UTIL else (df_filtrado['Dia Nome'] == dia_ref_nome))
                ]
                
                # Se for Dia Útil, o detalhe é a média da SOMA de todos os dias úteis.
                if tipo_pico == NOME_COLUNA_DIA_UTIL:
                    
                    # 1. Agrupa por Linha e Dia para ter a SOMA por Dia (Seg a Sex)
                    df_linha_diaria = df_pico.groupby(['Código Externo Linha', 'Dia Nome'])['Passageiros'].sum().reset_index()
                    
                    # 2. Calcula a Média dessas Somas Diárias
                    detalhe_linha = df_linha_diaria.groupby('Código Externo Linha')['Passageiros'].mean().reset_index()
                    
                    agg_name = 'Média' # O nome do agregado no detalhe é 'Média'
                
                else:
                    # Sábado e Domingo: Agrega com a função definida ('sum')
                    detalhe_linha = df_pico.groupby('Código Externo Linha')['Passageiros'].agg(agg_func).reset_index()
                
                detalhe_linha.rename(
                    columns={'Passageiros': f'{agg_name} de Passageiros'}, inplace=True
                )
                detalhe_linha[f'{agg_name} de Passageiros'] = detalhe_linha[f'{agg_name} de Passageiros'].round(2)
                detalhe_linha['Tipo Dia'] = tipo_pico
                detalhe_linha['Hora do Pico do Grupo'] = hora_pico
                
                df_detalhe = pd.concat([df_detalhe, detalhe_linha])
                
        return tabela_granular, picos, df_detalhe


    # --- Interface Streamlit ---

    st.title("🚌 Análise de Horário de Pico de Passageiros por Linha(s)")

    # --- BARRA LATERAL ---
    st.sidebar.header("Passo 1: Carregar Dados")
    uploaded_file = st.sidebar.file_uploader(
        "Carregue o arquivo (CSV, XLSX ou XLS):",
        type=['csv', 'xlsx', 'xls']
    )

    if uploaded_file is not None:
        df_bruto = carregar_dados(uploaded_file)
        
        if not df_bruto.empty:
            
            st.sidebar.header("Passo 2: Selecionar Linha(s)")
            
            linhas_disponiveis = sorted(df_bruto['Código Externo Linha'].unique().tolist())
            
            linhas_selecionadas = st.sidebar.multiselect(
                "Selecione o(s) Código(s) Externo(s) da(s) Linha(s):",
                options=linhas_disponiveis,
                default=linhas_disponiveis[:min(3, len(linhas_disponiveis))]
            )

            if linhas_selecionadas:
                
                df_filtrado = df_bruto[df_bruto['Código Externo Linha'].isin(linhas_selecionadas)]
                
                st.subheader(f"Análise de Grupo para: **{', '.join(linhas_selecionadas)}**")
                
                tabela_resultados, picos, df_detalhe_linhas = calcular_pico_agrupado(df_filtrado.copy())

            # ================= TABELA RESUMO DIÁRIO POR LINHA =================

                dados_resumo = []

                for linha in linhas_selecionadas:

                    df_linha = df_filtrado[df_filtrado['Código Externo Linha'] == linha]

                    # ----- DIA ÚTIL (média do total diário) -----
                    df_uteis = df_linha[df_linha['Dia da Semana'].isin(DIAS_UTEIS_NUM)]

                    if not df_uteis.empty:
                        totais_diarios_uteis = (
                            df_uteis
                            .groupby(df_uteis['Data Hora Início'].dt.date)['Passageiros']
                            .sum()
                        )
                        media_dia_util = totais_diarios_uteis.mean()
                    else:
                        media_dia_util = 0

                    # ----- SÁBADO (total diário) -----
                    total_sabado = df_linha[df_linha['Dia Nome'] == 'Sábado']['Passageiros'].sum()

                    # ----- DOMINGO (total diário) -----
                    total_domingo = df_linha[df_linha['Dia Nome'] == 'Domingo']['Passageiros'].sum()

                    dados_resumo.append({
                        'Linha': linha,
                        'Dia Útil (Média do Total Diário)': round(media_dia_util, 2),
                        'Sábado (Total Diário)': round(total_sabado, 2),
                        'Domingo (Total Diário)': round(total_domingo, 2)
                    })

                df_resumo_linhas = pd.DataFrame(dados_resumo)
                # =================================================================

                if tabela_resultados is not None:
                    
                    # --- CORREÇÃO DO ERRO (INSERIR ESTE BLOCO) ---
                    # Garante que as colunas de Sábado e Domingo existam no DataFrame
                    # Se não existirem (porque a linha não roda), cria com valor 0.
                    # Isso evita o KeyError no .melt() abaixo.
                    for dia_fds in ['Sábado', 'Domingo']:
                        if dia_fds not in tabela_resultados.columns:
                            tabela_resultados[dia_fds] = 0.0
                    # ---------------------------------------------

                    # --- TABELA DE VALORES AGREGADOS POR HORA (GRUPO) ---
                    st.markdown("### 1. Demanda Agregada por Hora (Grupo)")
                    st.markdown("**(Segunda a Domingo = Soma Total de Passageiros na Hora)**") 
                    st.markdown("**(Coluna 'Dia Útil' é a Média da Soma de Seg a Sex)**") 
                    
                    # CÓPIA PARA ARREDONDAMENTO P/ CIMA (SOMENTE EXIBIÇÃO)
                    tabela_resultados_exibicao = tabela_resultados.copy()
                    cols_para_ceil = [c for c in tabela_resultados_exibicao.columns if c != 'Hora']
                    tabela_resultados_exibicao[cols_para_ceil] = np.ceil(tabela_resultados_exibicao[cols_para_ceil])

                    st.dataframe(tabela_resultados_exibicao, use_container_width=True, hide_index=True)
                    
                    # --- GRÁFICO GERAL ---
                    # Os dados dos gráficos NÃO são arredondados para cima para manter a precisão das curvas
                    df_plot = tabela_resultados.melt(
                        id_vars='Hora', 
                        # Colunas de dias úteis e a média da soma
                        value_vars=[c for c in tabela_resultados.columns if c not in ['Hora', 'Sábado', 'Domingo']], 
                        var_name='Tipo de Dia', 
                        value_name='Passageiros Agregados'
                    )
                    
                    # Adiciona Sábado e Domingo separadamente para o gráfico, se necessário
                    # AGORA ISSO NÃO VAI DAR ERRO PORQUE GARANTIMOS QUE AS COLUNAS EXISTEM ACIMA
                    df_plot_fim_semana = tabela_resultados.melt(
                        id_vars='Hora', 
                        value_vars=['Sábado', 'Domingo'],
                        var_name='Tipo de Dia', 
                        value_name='Passageiros Agregados'
                    )

                    st.markdown("#### Curvas de Demanda dos Dias Úteis e Média Final")
                    fig_geral = px.line(
                        df_plot, 
                        x='Hora', 
                        y='Passageiros Agregados', 
                        color='Tipo de Dia',
                        # TÍTULO ATUALIZADO
                        title='Demanda de Passageiros (Soma Total na Hora) por Hora', 
                        template='plotly_white',
                        # LABEL ATUALIZADO
                        labels={'Passageiros Agregados': 'Valor de Passageiros (Soma Total na Hora)'}
                    )
                    st.plotly_chart(fig_geral, use_container_width=True)

                    st.markdown("#### Curvas de Demanda de Sábado e Domingo (Soma Total)")
                    fig_fim_semana = px.line(
                        df_plot_fim_semana, 
                        x='Hora', 
                        y='Passageiros Agregados', 
                        color='Tipo de Dia',
                        title='Demanda de Passageiros (Soma Total na Hora) por Hora',
                        template='plotly_white',
                        labels={'Passageiros Agregados': 'Valor de Passageiros (Soma Total na Hora)'}
                    )
                    st.plotly_chart(fig_fim_semana, use_container_width=True)

                    st.markdown("---")

                    st.markdown("### 📊 Resumo Diário de Passageiros por Linha")

                    df_resumo_exib = df_resumo_linhas.copy()
                    df_resumo_exib.iloc[:, 1:] = np.ceil(df_resumo_exib.iloc[:, 1:]).astype(int)

                    st.dataframe(df_resumo_exib, use_container_width=True, hide_index=True)

                    # --- HORÁRIO DE PICO E DETALHAMENTO POR LINHA ---
                    st.markdown("### 2. Horários de Pico e Detalhamento por Linha")
                    
                    cols_picos = st.columns(3)
                    
                    # Mapeia as chaves de pico para as colunas
                    NOME_COLUNA_DIA_UTIL = 'Dia Útil (Média da Soma)' # Garantir que o nome é consistente
                    pico_tipos = [NOME_COLUNA_DIA_UTIL, 'Sábado', 'Domingo']
                    
                    for i, tipo in enumerate(pico_tipos):
                        pico_info = picos.get(tipo, {'Hora': 'N/A', 'Valor Pico': 0, 'Agregacao': 'N/A', 'Label': ''})
                        
                        with cols_picos[i]:
                            # Ajusta o título para o Dia Útil
                            display_title = 'Dia Útil' if tipo == NOME_COLUNA_DIA_UTIL else tipo
                            
                            # --- MODIFICAÇÃO PARA ARREDONDAR PARA CIMA NA EXIBIÇÃO ---
                            valor_pico_ceil = np.ceil(pico_info['Valor Pico'])
                            
                            cols_picos[i].metric(
                                f"Pico - {display_title} ({pico_info['Agregacao']})",
                                f"⏰ {pico_info['Hora']}",
                                f"{valor_pico_ceil:.0f} {pico_info['Label']}" # Formatado como inteiro (sem casas decimais)
                            )
                            # -------------------------------------------------------------------
                            
                            if pico_info['Hora'] != 'N/A' and pico_info['Agregacao'] != 'N/A' and not df_detalhe_linhas.empty:
                                
                                agg_name = pico_info['Agregacao']
                                st.markdown(f"**{agg_name} de passageiros por linha em {pico_info['Hora']}**")
                                
                                df_pico_detalhe_bruto = df_detalhe_linhas[df_detalhe_linhas['Tipo Dia'] == tipo].drop(columns=['Tipo Dia', 'Hora do Pico do Grupo']).sort_values(by=f'{agg_name} de Passageiros', ascending=False)
                                
                                # CÓPIA PARA ARREDONDAMENTO P/ CIMA (SOMENTE EXIBIÇÃO)
                                df_pico_detalhe = df_pico_detalhe_bruto.copy()
                                df_pico_detalhe[f'{agg_name} de Passageiros'] = np.ceil(df_pico_detalhe[f'{agg_name} de Passageiros']).astype(int)
                                
                                st.dataframe(df_pico_detalhe, hide_index=True, use_container_width=True)
                                
                                # Gráfico de Detalhe por Linha (Barras)
                                # Usamos o DataFrame ARREDONDADO para que o gráfico reflita a tabela
                                fig_detalhe = px.bar(
                                    df_pico_detalhe,
                                    x='Código Externo Linha',
                                    y=f'{agg_name} de Passageiros',
                                    title=f'{display_title} - {pico_info["Hora"]}',
                                    labels={'Código Externo Linha': 'Linha', f'{agg_name} de Passageiros': f'{agg_name} de Pass.'},
                                    template='plotly_white',
                                    color='Código Externo Linha',
                                )
                                fig_detalhe.update_layout(showlegend=False, margin=dict(t=50, b=0, l=0, r=0))
                                st.plotly_chart(fig_detalhe, use_container_width=True, config={'displayModeBar': False})
                                
            else:
                st.info("Por favor, selecione pelo menos um Código Externo da Linha no menu lateral para iniciar a análise.")
        
    else:
        st.info("Por favor, carregue sua planilha de dados (CSV, XLSX ou XLS) no menu lateral para começar.")