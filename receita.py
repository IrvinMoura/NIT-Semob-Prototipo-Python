import streamlit as st
import pandas as pd
import plotly.express as px

def main():
    # --- Configuração da Página ---
    st.set_page_config(
        page_title="Cálculo de Receita e Passageiros por Operadora",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- Título do Aplicativo ---
    st.title("💰 Cálculo de Receita e Passageiros por Operadora")
    st.markdown("Faça o upload de uma planilha (CSV ou Excel) para calcular a receita e o fluxo de passageiros das operadoras.")

    # --- Constantes ---
    TARIFA = 5.15 # Tarifa em R$ para o cálculo do Passageiro Equivalente

    # --- Nomes das colunas conforme a descrição do usuário ---
    COLUNA_OPERADORA = 'Nome Operadora'    # Coluna G na planilha
    COLUNA_VALOR = 'Valor Passageiros'    # Coluna AB na planilha
    COLUNA_PASSAGEIROS = 'Passageiros'      # Coluna AA na planilha

    # --- Termos de busca para as operadoras (para garantir a identificação) ---
    TERMO_ROSA = "rosa"
    TERMO_SAO_JOAO = "sao joao"
    TERMO_VIA_FEIRA = "viafeira" 

    # --- Função para carregar os dados (INALTERADA) ---
    @st.cache_data
    def carregar_dados(uploaded_file):
        """Lê o arquivo CSV ou Excel e retorna um DataFrame do pandas."""
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1') 
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                return None, "Tipo de arquivo não suportado."
            
            return df, None
        except Exception as e:
            return None, f"Erro ao carregar o arquivo: {e}"

    # --- Funções Auxiliares de Limpeza ---

    def limpar_e_converter_valor(df, coluna):
        """Limpiza e converte a coluna de valor (formato brasileiro) para float."""
        try:
            if df[coluna].dtype != 'object':
                df[coluna] = df[coluna].astype(str)

            # 1. REMOVER o ponto (.) de milhar (se houver)
            df[coluna] = df[coluna].str.replace('.', '', regex=False)
            
            # 2. SUBSTITUIR a vírgula (,) decimal por ponto (.)
            df[coluna] = df[coluna].str.replace(',', '.', regex=False)
            
            # 3. Remover R$ e espaços em branco
            df[coluna] = df[coluna].str.replace('R$', '', regex=False).str.strip()
            
            # 4. Conversão para numérico
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
            
            df.dropna(subset=[coluna], inplace=True)
            return True
        except Exception as e:
            st.error(f"Erro na limpeza/conversão da coluna **'{coluna}'**. Erro técnico: {e}")
            return False

    # --- Função para identificar nomes (INALTERADA, adaptada para ser externa) ---

    def encontrar_nomes_operadoras(receita_total):
        """Identifica e retorna os nomes exatos das 3 operadoras no DataFrame."""
        def encontrar_nome_exato(termo_busca):
            matches = receita_total[receita_total[COLUNA_OPERADORA].str.contains(termo_busca, case=False, na=False)]
            if not matches.empty:
                return matches[COLUNA_OPERADORA].iloc[0] 
            return termo_busca.upper() 

        nome_via_feira = encontrar_nome_exato(TERMO_VIA_FEIRA)
        nome_rosa = encontrar_nome_exato(TERMO_ROSA)
        nome_sao_joao = encontrar_nome_exato(TERMO_SAO_JOAO)
        return nome_via_feira, nome_rosa, nome_sao_joao


    # --- Função para calcular a RECEITA ---
    def calcular_receita(df_original):
        """Soma os valores e aplica a regra de divisão da receita da Via Feira."""
        df = df_original.copy()
        
        # 1. Selecionar e validar colunas
        colunas_necessarias = [COLUNA_OPERADORA, COLUNA_VALOR]
        if not all(col in df.columns for col in colunas_necessarias):
            st.error(f"O arquivo deve conter as colunas **'{COLUNA_OPERADORA}'** e **'{COLUNA_VALOR}'**.")
            return None, 0.0, 0.0, "NÃO ENCONTRADO"

        df = df[colunas_necessarias]
        
        # 2. Limpeza de dados (CORREÇÃO DE FORMATO)
        if not limpar_e_converter_valor(df, COLUNA_VALOR):
            return None, 0.0, 0.0, "NÃO ENCONTRADO"

        # 3. Agrupar e somar a receita total por operadora
        receita_total = df.groupby(COLUNA_OPERADORA)[COLUNA_VALOR].sum().reset_index(name='Receita Bruta')
        
        # 4. Identificar os nomes exatos das operadoras
        nome_via_feira, nome_rosa, nome_sao_joao = encontrar_nomes_operadoras(receita_total)
        
        # 5. Aplicar a regra de divisão da Via Feira
        try:
            receita_via_feira = receita_total[receita_total[COLUNA_OPERADORA] == nome_via_feira]['Receita Bruta'].iloc[0]
        except IndexError:
            receita_via_feira = 0.0
            
        parcela_por_operadora = receita_via_feira / 2
        
        # 6. Ajustar e Consolidar as receitas (Apenas Rosa e São João)
        df_resultado = pd.DataFrame([
            {COLUNA_OPERADORA: nome_rosa, 'Receita Final': 0.0},
            {COLUNA_OPERADORA: nome_sao_joao, 'Receita Final': 0.0}
        ])
        
        for index, row in receita_total.iterrows():
            operadora = row[COLUNA_OPERADORA]
            receita_bruta = row['Receita Bruta']
            
            if operadora == nome_via_feira:
                continue
            elif operadora == nome_rosa:
                df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_rosa, 'Receita Final'] += receita_bruta
            elif operadora == nome_sao_joao:
                df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_sao_joao, 'Receita Final'] += receita_bruta
                
        df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_rosa, 'Receita Final'] += parcela_por_operadora
        df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_sao_joao, 'Receita Final'] += parcela_por_operadora

        # NOME DA COLUNA AJUSTADO DE "Receita Ajustada (R$)" para "Receita (R$)"
        df_resultado.rename(columns={'Receita Final': 'Receita (R$)'}, inplace=True)
        
        return df_resultado, receita_via_feira, parcela_por_operadora, nome_via_feira


    # --- Função para calcular Passageiros e Passageiro Equivalente ---
    def calcular_passageiros_e_equivalente(df_original, nome_via_feira, nome_rosa, nome_sao_joao):
        """Calcula o total de passageiros, aplica a divisão da Via Feira e calcula o Passageiro Equivalente."""
        
        df = df_original.copy()
        
        # 1. Selecionar e validar colunas
        colunas_necessarias = [COLUNA_OPERADORA, COLUNA_PASSAGEIROS]
        if not all(col in df.columns for col in colunas_necessarias):
            # Aviso mantido aqui, mas a chamada principal tratará o caso de falha.
            return None, 0.0, 0.0

        df = df[colunas_necessarias]
        
        # 2. Limpeza de dados: Garantir que a coluna de Passageiros seja numérica
        try:
            df[COLUNA_PASSAGEIROS] = pd.to_numeric(df[COLUNA_PASSAGEIROS], errors='coerce')
            df.dropna(subset=[COLUNA_PASSAGEIROS], inplace=True)
        except Exception as e:
            st.error(f"Erro ao converter a coluna **'{COLUNA_PASSAGEIROS}'** para número. Verifique se a coluna contém apenas números inteiros. Erro técnico: {e}")
            return None, 0.0, 0.0

        # 3. Agrupar e somar o total de passageiros por operadora
        passageiros_total = df.groupby(COLUNA_OPERADORA)[COLUNA_PASSAGEIROS].sum().reset_index(name='Total Passageiros Bruto')
        
        # 4. Aplicar a regra de divisão da Via Feira para Passageiros
        try:
            passageiros_via_feira = passageiros_total[passageiros_total[COLUNA_OPERADORA] == nome_via_feira]['Total Passageiros Bruto'].iloc[0]
        except IndexError:
            passageiros_via_feira = 0.0
            
        parcela_passageiros = passageiros_via_feira / 2
        
        # 5. Ajustar e Consolidar os passageiros (Apenas Rosa e São João)
        df_passageiros = pd.DataFrame([
            {COLUNA_OPERADORA: nome_rosa, 'Passageiros Final': 0.0},
            {COLUNA_OPERADORA: nome_sao_joao, 'Passageiros Final': 0.0}
        ])
        
        for index, row in passageiros_total.iterrows():
            operadora = row[COLUNA_OPERADORA]
            passageiros_bruto = row['Total Passageiros Bruto']
            
            if operadora == nome_via_feira:
                continue
            elif operadora == nome_rosa:
                df_passageiros.loc[df_passageiros[COLUNA_OPERADORA] == nome_rosa, 'Passageiros Final'] += passageiros_bruto
            elif operadora == nome_sao_joao:
                df_passageiros.loc[df_passageiros[COLUNA_OPERADORA] == nome_sao_joao, 'Passageiros Final'] += passageiros_bruto
                
        df_passageiros.loc[df_passageiros[COLUNA_OPERADORA] == nome_rosa, 'Passageiros Final'] += parcela_passageiros
        df_passageiros.loc[df_passageiros[COLUNA_OPERADORA] == nome_sao_joao, 'Passageiros Final'] += parcela_passageiros

        # NOME DA COLUNA AJUSTADO PARA "Total Passageiros"
        df_passageiros.rename(columns={'Passageiros Final': 'Total Passageiros'}, inplace=True)

        return df_passageiros, passageiros_via_feira, parcela_passageiros


    # --- Componente de Upload ---
    uploaded_file = st.file_uploader(
        "Selecione um arquivo CSV ou Excel",
        type=['csv', 'xlsx'],
        help="O arquivo deve conter as colunas: 'Nome Operadora', 'Valor Passageiros' e 'Passageiros'."
    )

    if uploaded_file is not None:
        
        df, erro = carregar_dados(uploaded_file)

        if erro:
            st.error(erro)
        elif df is not None:
            st.success("Arquivo carregado com sucesso!")
            
            # --- CÁLCULO DE RECEITA ---
            resultado_receita, receita_via_feira, parcela_receita, nome_via_feira = calcular_receita(df)

            if resultado_receita is not None and not resultado_receita.empty:
                
                # --- CÁLCULO DE PASSAGEIROS ---
                if COLUNA_OPERADORA in df.columns:
                    receita_temp = df.groupby(COLUNA_OPERADORA)[COLUNA_OPERADORA].count().reset_index(name='Count')
                    _, nome_rosa, nome_sao_joao = encontrar_nomes_operadoras(receita_temp)
                else:
                    nome_rosa, nome_sao_joao = TERMO_ROSA.upper(), TERMO_SAO_JOAO.upper()
                    
                df_passageiros, passageiros_via_feira, parcela_passageiros = calcular_passageiros_e_equivalente(df, nome_via_feira, nome_rosa, nome_sao_joao)

                
                # --- CONSOLIDAÇÃO E EXIBIÇÃO ---
                
                # 1. Consolida Receita e Passageiros
                
                # DataFrame final que será exibido
                df_final = resultado_receita.copy()

                if df_passageiros is not None:
                    # Merge dos DataFrames (Receita e Passageiros)
                    df_final = pd.merge(df_final, df_passageiros, on=COLUNA_OPERADORA, how='left')
                    
                    # 2. Calcular Passageiro Equivalente
                    df_final['Passageiro Equivalente'] = df_final['Receita (R$)'] / TARIFA
                    
                    # 3. Adicionar linha de SOMA (SIT)
                    
                    # Cria a linha de soma
                    nova_linha_sit = {
                        COLUNA_OPERADORA: 'SIT',
                        'Receita (R$)': df_final['Receita (R$)'].sum(),
                        'Total Passageiros': df_final['Total Passageiros'].sum(),
                        'Passageiro Equivalente': df_final['Passageiro Equivalente'].sum()
                    }
                    
                    # Adiciona a linha ao DataFrame
                    # O pd.concat é mais seguro para adicionar linhas do que o .append (que foi depreciado)
                    df_final = pd.concat([df_final, pd.Series(nova_linha_sit).to_frame().T], ignore_index=True)


                    # 4. Reordenar colunas para exibição
                    df_final = df_final[[
                        COLUNA_OPERADORA, 
                        'Receita (R$)', 
                        'Total Passageiros', 
                        'Passageiro Equivalente'
                    ]]

                else:
                    # Se o cálculo de passageiros falhar, mostra apenas a receita e calcula o equivalente
                    df_final['Passageiro Equivalente'] = df_final['Receita (R$)'] / TARIFA
                    
                    # Adicionar linha de SOMA (SIT) (apenas para Receita e Equivalente)
                    nova_linha_sit = {
                        COLUNA_OPERADORA: 'SIT',
                        'Receita (R$)': df_final['Receita (R$)'].sum(),
                        'Passageiro Equivalente': df_final['Passageiro Equivalente'].sum()
                    }
                    df_final = pd.concat([df_final, pd.Series(nova_linha_sit).to_frame().T], ignore_index=True)


                st.header("Resultado Consolidado por Operadora")
                
                # 1. Informações sobre a tarifa (mantida para contexto do Equivalente)
                st.info(f"O cálculo de Passageiro Equivalente é baseado na Tarifa de R$ {TARIFA:,.2f}.")

                # 2. Tabela de Receita Final
                st.subheader("Receita, Passageiros e Equivalente (Rosa, São João e SIT)")
                
                # Formatação dos números na tabela
                format_dict = {
                    'Receita (R$)': "R$ {:,.2f}",
                    'Total Passageiros': "{:,.0f}", 
                    'Passageiro Equivalente': "{:,.2f}"
                }
                
                # Adiciona um estilo especial para a linha de soma (negrito)
                def highlight_sit(row):
                    return ['font-weight: bold'] * len(row) if row[COLUNA_OPERADORA] == 'SIT' else [''] * len(row)
                    
                st.dataframe(
                    df_final.style.format(format_dict).apply(highlight_sit, axis=1),
                    hide_index=True,
                    use_container_width=True
                )
                
                # 3. Gráfico de Barras da Receita
                # O gráfico DEVE EXCLUIR a linha 'SIT'
                df_grafico = df_final[df_final[COLUNA_OPERADORA] != 'SIT']
                
                st.subheader("Visualização da Receita")
                
                fig = px.bar(
                    df_grafico,
                    x=COLUNA_OPERADORA,
                    y='Receita (R$)',
                    title='Receita por Operadora',
                    labels={COLUNA_OPERADORA: "Operadora", "Receita (R$)": "Receita (R$)"},
                    color=COLUNA_OPERADORA,
                    text='Receita (R$)'
                )
                fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
                fig.update_yaxes(tickprefix="R$ ")
                st.plotly_chart(fig, use_container_width=True)

            elif resultado_receita is not None and resultado_receita.empty:
                st.warning("Nenhum dado encontrado para as operadoras Rosa ou São João.")
            else:
                st.warning("Ocorreu um erro inesperado no processamento dos dados. Verifique a estrutura da planilha.")
        
    else:
        st.info("Aguardando o upload de um arquivo...")