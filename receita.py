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
    st.markdown("Faça o upload de uma planilha (CSV ou Excel) para calcular a receita e o fluxo de passageiros das operadoras. (Usar arquivo de Relação de Faturamento)")

    # --- Constantes ---
    TARIFA = 5.15

    # --- Colunas esperadas ---
    COLUNA_OPERADORA = 'Nome Operadora'
    COLUNA_VALOR = 'Valor Passageiros'
    COLUNA_PASSAGEIROS = 'Passageiros'

    # --- Termos de identificação ---
    TERMO_ROSA = "rosa"
    TERMO_SAO_JOAO = "sao joao"
    TERMO_VIA_FEIRA = "viafeira"

    # ----------------------------------------------------------------
    # --- FUNÇÃO: carregar dados ---
    # ----------------------------------------------------------------
    @st.cache_data
    def carregar_dados(uploaded_file):
        try:
            df = None
            if uploaded_file.name.endswith('.csv'):
                # Tenta ler com separador automático ou ponto e vírgula (comum no Brasil)
                try:
                    df = pd.read_csv(uploaded_file, sep=';', engine='python', encoding='latin-1')
                    if df.shape[1] < 2:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1')
                except:
                     uploaded_file.seek(0)
                     df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin-1')
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                return None, "Tipo de arquivo não suportado."
            
            if df is not None:
                # Remove espaços em branco dos nomes das colunas para evitar erros de busca
                df.columns = df.columns.str.strip()
                return df, None
            return None, "Erro desconhecido ao ler o arquivo."
        except Exception as e:
            return None, f"Erro ao carregar o arquivo: {e}"

    # ----------------------------------------------------------------
    # --- FUNÇÕES DE LIMPEZA ---
    # ----------------------------------------------------------------
    def limpar_e_converter_valor(df, coluna):
        try:
            df[coluna] = df[coluna].astype(str)
            df[coluna] = df[coluna].str.replace('.', '', regex=False)
            df[coluna] = df[coluna].str.replace(',', '.', regex=False)
            df[coluna] = df[coluna].str.replace('R$', '', regex=False).str.strip()
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
            df.dropna(subset=[coluna], inplace=True)
            return True
        except Exception as e:
            # st.error(f"Erro ao limpar coluna '{coluna}': {e}") # Opcional: comentar para não poluir
            return False

    # ----------------------------------------------------------------
    # --- FUNÇÃO: identificar operadoras reais ---
    # ----------------------------------------------------------------
    def encontrar_nomes_operadoras(receita_total):
        def encontrar_nome_exato(termo):
            m = receita_total[receita_total[COLUNA_OPERADORA].str.contains(termo, case=False, na=False)]
            if not m.empty:
                return m[COLUNA_OPERADORA].iloc[0]
            return termo.upper()
        return (
            encontrar_nome_exato(TERMO_VIA_FEIRA),
            encontrar_nome_exato(TERMO_ROSA),
            encontrar_nome_exato(TERMO_SAO_JOAO)
        )

    # ----------------------------------------------------------------
    # --- FUNÇÃO: cálculo de receita ---
    # ----------------------------------------------------------------
    def calcular_receita(df_original):
        df = df_original.copy()
        
        # Verificação flexível de colunas obrigatórias
        if COLUNA_OPERADORA not in df.columns:
            st.error(f"Coluna '{COLUNA_OPERADORA}' não encontrada.")
            return None, 0, 0, ""
        if COLUNA_VALOR not in df.columns:
            st.error(f"Coluna '{COLUNA_VALOR}' não encontrada.")
            return None, 0, 0, ""

        df = df[[COLUNA_OPERADORA, COLUNA_VALOR]]
        if not limpar_e_converter_valor(df, COLUNA_VALOR):
            return None, 0, 0, ""

        receita_total = df.groupby(COLUNA_OPERADORA)[COLUNA_VALOR].sum().reset_index(name="Receita Bruta")

        nome_via, nome_rosa, nome_sj = encontrar_nomes_operadoras(receita_total)
        via_feira_rec = receita_total.loc[receita_total[COLUNA_OPERADORA] == nome_via, "Receita Bruta"].iloc[0] if nome_via in receita_total[COLUNA_OPERADORA].values else 0
        quota = via_feira_rec / 2

        df_resultado = pd.DataFrame([
            {COLUNA_OPERADORA: nome_rosa, "Receita Final": 0},
            {COLUNA_OPERADORA: nome_sj, "Receita Final": 0}
        ])

        for _, row in receita_total.iterrows():
            op = row[COLUNA_OPERADORA]
            val = row["Receita Bruta"]
            if op == nome_via: continue
            if op == nome_rosa:
                df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_rosa, "Receita Final"] += val
            if op == nome_sj:
                df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_sj, "Receita Final"] += val

        df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_rosa, "Receita Final"] += quota
        df_resultado.loc[df_resultado[COLUNA_OPERADORA] == nome_sj, "Receita Final"] += quota
        df_resultado.rename(columns={"Receita Final": "Receita (R$)"}, inplace=True)

        return df_resultado, via_feira_rec, quota, nome_via

    # ----------------------------------------------------------------
    # --- CÁLCULO PASSAGEIROS ---
    # ----------------------------------------------------------------
    def calcular_passageiros_e_equivalente(df_original, nome_via, nome_rosa, nome_sj):
        df = df_original.copy()
        if COLUNA_PASSAGEIROS not in df.columns:
            return None, 0, 0

        df[COLUNA_PASSAGEIROS] = pd.to_numeric(df[COLUNA_PASSAGEIROS], errors="coerce")
        df.dropna(subset=[COLUNA_PASSAGEIROS], inplace=True)

        passageiros_total = df.groupby(COLUNA_OPERADORA)[COLUNA_PASSAGEIROS].sum().reset_index(name="Pass Bruto")

        via_pass = passageiros_total.loc[passageiros_total[COLUNA_OPERADORA] == nome_via, "Pass Bruto"].iloc[0] if nome_via in passageiros_total[COLUNA_OPERADORA].values else 0
        quota = via_pass / 2

        df_res = pd.DataFrame([
            {COLUNA_OPERADORA: nome_rosa, "Total Passageiros": 0},
            {COLUNA_OPERADORA: nome_sj, "Total Passageiros": 0},
        ])

        for _, row in passageiros_total.iterrows():
            op = row[COLUNA_OPERADORA]
            val = row["Pass Bruto"]
            if op == nome_via: continue
            if op == nome_rosa:
                df_res.loc[df_res[COLUNA_OPERADORA] == nome_rosa, "Total Passageiros"] += val
            if op == nome_sj:
                df_res.loc[df_res[COLUNA_OPERADORA] == nome_sj, "Total Passageiros"] += val

        df_res.loc[df_res[COLUNA_OPERADORA] == nome_rosa, "Total Passageiros"] += quota
        df_res.loc[df_res[COLUNA_OPERADORA] == nome_sj, "Total Passageiros"] += quota

        return df_res, via_pass, quota

    # ----------------------------------------------------------------
    # --- UPLOAD ---
    # ----------------------------------------------------------------
    file = st.file_uploader("Selecione um arquivo CSV ou Excel", type=["csv", "xlsx"])

    if file is None:
        st.info("Aguardando upload...")
        return

    df, erro = carregar_dados(file)

    if erro:
        st.error(erro)
        return

    st.success("Arquivo carregado com sucesso!")

    # ---------------------------------------------------------
    # -------- CALCULAR RECEITA PRINCIPAL ---------------------
    # ---------------------------------------------------------
    resultado_receita, via_val, via_cota, nome_via = calcular_receita(df)

    if resultado_receita is None:
        return

    df_ops = df[[COLUNA_OPERADORA]].drop_duplicates()
    _, nome_rosa, nome_sj = encontrar_nomes_operadoras(df_ops)

    df_pass, via_pass, via_cota_pass = calcular_passageiros_e_equivalente(df, nome_via, nome_rosa, nome_sj)

    # Construir tabela final
    df_final = resultado_receita.copy()

    if df_pass is not None:
        df_final = df_final.merge(df_pass, on=COLUNA_OPERADORA, how="left")
        df_final["Passageiro Equivalente"] = df_final["Receita (R$)"] / TARIFA

        nova_linha = {
            COLUNA_OPERADORA: "SIT",
            "Receita (R$)": df_final["Receita (R$)"].sum(),
            "Total Passageiros": df_final["Total Passageiros"].sum(),
            "Passageiro Equivalente": df_final["Passageiro Equivalente"].sum()
        }
        df_final = pd.concat([df_final, pd.DataFrame([nova_linha])], ignore_index=True)

    # ---------------------------------------------------------
    # --- TABELA: Receita Final ---
    # ---------------------------------------------------------
    st.header("Resultado Consolidado por Operadora")

    st.dataframe(
        df_final.style.format({
            "Receita (R$)": "R$ {:,.2f}",
            "Total Passageiros": "{:,.0f}",
            "Passageiro Equivalente": "{:,.2f}",
        }),
        use_container_width=True
    )

    # ---------------------------------------------------------
    # --- GRÁFICO ---
    # ---------------------------------------------------------
    df_graf = df_final[df_final[COLUNA_OPERADORA] != "SIT"]

    st.subheader("Gráfico de Receita por Operadora")
    fig = px.bar(
        df_graf,
        x=COLUNA_OPERADORA,
        y="Receita (R$)",
        color=COLUNA_OPERADORA,
        text="Receita (R$)",
        title="Receita por Operadora"
    )
    fig.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # ===================================================================
    # === SEÇÃO: TABELA DE RECEITA POR TIPO DE PASSAGEM =================
    # ===================================================================
    st.header("🧾 Receita por Tipo de Passagem")

    # Filtra colunas que parecem ser tipos de passagem/valor
    colunas_receita_tipo = [
        col for col in df.columns
        if (
            any(k in col.lower() for k in [
                "inteira", "vt", "estud", "grat", "social", "integra", "passe", "vale", "passag"
            ])
            and "passageiro" not in col.lower()   # evita colunas de quantidade total (geralmente "Passageiros" ou "Valor Passageiros")
            and col != COLUNA_VALOR               # evita duplicar a coluna principal
        )
    ]

    if not colunas_receita_tipo:
        st.warning("Nenhuma coluna de receita por tipo encontrada.")
    else:
        df_receita_tipos = df[colunas_receita_tipo + [COLUNA_OPERADORA]].copy()

        # Limpeza robusta das colunas selecionadas
        for col in colunas_receita_tipo:
            df_receita_tipos[col] = (
                df_receita_tipos[col].astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.replace('R$', '', regex=False)
                .str.strip()
            )
            df_receita_tipos[col] = pd.to_numeric(df_receita_tipos[col], errors="coerce").fillna(0)

        # -------------------------------------------------------
        # IDENTIFICAÇÃO DINÂMICA DAS COLUNAS DE VALOR DE INTEGRAÇÃO
        # -------------------------------------------------------
        # Procura colunas que tenham "valor" E "integra" no nome (case insensitive)
        cols_int_existentes = [
            c for c in df_receita_tipos.columns 
            if ('integra' in c.lower())
        ]
        
        # Debug (opcional, remova se quiser limpar a tela)
        # if not cols_int_existentes:
        #    st.warning("Atenção: Não foram identificadas colunas de Valor de Integração automaticamente.")
        
        # Tabela geral (Soma de tudo por coluna)
        tabela_soma = (
            df_receita_tipos[colunas_receita_tipo]
            .sum()
            .reset_index()
            .rename(columns={"index": "Tipo de Passagem", 0: "Receita Total (R$)"})
        )

        # Se encontrou colunas de integração, cria a linha de soma
        if cols_int_existentes:
            total_integracao = df_receita_tipos[cols_int_existentes].sum().sum()
            
            linha_integracao = pd.DataFrame([{
                "Tipo de Passagem": "--- SOMA INTEGRAÇÃO (Passagem + Est + VT) ---", 
                "Receita Total (R$)": total_integracao
            }])
            
            # Adiciona ao final da tabela de totais
            tabela_soma = pd.concat([tabela_soma, linha_integracao], ignore_index=True)

        st.subheader("Total Geral por Tipo")
        st.dataframe(
            tabela_soma.style.format({"Receita Total (R$)": "R$ {:,.2f}"}),
            use_container_width=True
        )

        # NOVA FEATURE → Soma por operadora
        st.subheader("Receita por Tipo Separada por Operadora")
        
        # Agrupa por operadora
        tabela_por_operadora = df_receita_tipos.groupby(COLUNA_OPERADORA)[colunas_receita_tipo].sum()
        
        # Adiciona coluna de Soma de Integração se possível
        if cols_int_existentes:
            tabela_por_operadora["SOMA INTEGRAÇÃO"] = tabela_por_operadora[cols_int_existentes].sum(axis=1)

        st.dataframe(
            tabela_por_operadora.style.format("{:,.2f}"),
            use_container_width=True
        )

if __name__ == "__main__":
    main()