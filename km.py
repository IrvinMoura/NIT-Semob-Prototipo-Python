import streamlit as st
import pandas as pd
import plotly.express as px
from unidecode import unidecode
import io

# ---------------- Funções auxiliares ----------------
def calcular_km_falha(operadora, km_percorrido):
    """Aplica ajuste de falha com base no nome da operadora."""
    nome_norm = unidecode(str(operadora)).lower()
    if 'sao joao' in nome_norm or 'são joão' in nome_norm or 'saojoao' in nome_norm:
        return km_percorrido * 1.04
    if 'rosa' in nome_norm:
        return km_percorrido * 1.07
    return km_percorrido

def calcular_km_ociosa(km_falha):
    return km_falha * 1.05

def adicionar_linha_total(df):
    """Calcula o total de Km Percorrido, Km Falha, Km Ociosa e adiciona como última linha."""
    if df is None or df.empty:
        return df
    
    # Se o DataFrame já tiver 'Total Geral (Km)' (pode acontecer na re-execução), removemos
    if 'Total Geral (Km)' in df.index:
        df = df.drop('Total Geral (Km)')
    
    total_row = df[['Km Percorrido', 'Km Falha', 'Km Ociosa']].sum()
    total_df = pd.DataFrame(total_row).T
    total_df.index = ['Total Geral (Km)']
    
    # Concatena a linha de total com o DataFrame original, mantendo o índice do tipo de veículo
    result_df = pd.concat([df, total_df])
    return result_df

def formatar_br(val):
    """Formata um float para o padrão brasileiro (milhar com ponto, decimal com vírgula)."""
    # Se for float/int, formata com vírgula para milhares e ponto para decimal
    if isinstance(val, (float, int)):
        return "{:,.2f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")
    return val

# ---------------- Conversão / helpers HTML ----------------
def _styler_to_html(df, float_format="{:,.2f}"):
    """Retorna HTML da tabela formatada com pandas Styler (evita repetição)."""
    
    # MODIFICAÇÃO: Usamos .style.format() e passamos formatar_br como função de formatação
    # A função formatar_br será aplicada apenas às colunas numéricas automaticamente
    styler = df.style.format(formatar_br).set_table_attributes('border="1" class="dataframe table-striped table-hover"')
        
    # Se a última linha for 'Total Geral (Km)', aplica um estilo para destacá-la no HTML
    if 'Total Geral (Km)' in df.index:
        
        # Adiciona classe CSS para a linha de total
        def highlight_total_row(row):
            if row.name == 'Total Geral (Km)':
                return ['font-weight: bold; background-color: #e0f7fa;'] * len(row)
            return [''] * len(row)
        
        styler.apply(highlight_total_row, axis=1)

    return styler.to_html()

def create_full_html_report_single_table(table_df, title_table, fig=None, selected_operadora="Operadora"):
    """
    Cria relatório HTML contendo:
    - Tabela (table_df) com um título (title_table)
    - Opcionalmente: gráfico (fig) adicionado APÓS as tabelas
    Usa a ordem: tabelas primeiro → depois gráfico.
    """
    # montar bloco da tabela (ou mensagem caso vazio)
    if (table_df is None) or table_df.empty:
        bloco_table_html = f"<h2>{title_table}</h2><p><i>Nenhum dado disponível para esta operadora.</i></p>"
    else:
        # ADICIONAR LINHA DE TOTAL ANTES DE GERAR HTML
        final_df = adicionar_linha_total(table_df)
        bloco_table_html = f"<h2>{title_table}</h2>" + _styler_to_html(final_df)

    # gráfico (colocar no final se fornecido)
    grafico_html = ""
    if fig is not None:
        # incluir plotly js no primeiro uso
        grafico_html = "<h2>Gráfico Resumo (Total Geral)</h2>" + fig.to_html(full_html=False, include_plotlyjs='cdn')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Relatório - {selected_operadora}</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 18px; color: #333; }}
            h1 {{ color: #007bff; }}
            h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 22px; }}
            p {{ margin: 8px 0 14px 0; }}
            .dataframe {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }}
            .dataframe th, .dataframe td {{ padding: 8px; text-align: right; border: 1px solid #ddd; word-wrap: break-word; }}
            .dataframe th {{ background-color: #f2f2f2; text-align: left; }}
            .js-plotly-plot {{ width: 70% !important; margin: 0 auto; height: auto; }}
            .table-block {{ page-break-inside: avoid; margin-bottom: 18px; }}
            .total-row {{ font-weight: bold; background-color: #e0f7fa; }} /* Estilo para a linha de total no HTML puro */
        </style>
    </head>
    <body>
        <h1>Relatório - {selected_operadora}</h1>

        <div class="table-block">
            {bloco_table_html}
        </div>

        {grafico_html}
    </body>
    </html>
    """
    return html_content.encode('utf-8')

def create_full_html_report_tables_then_chart(tables_ordered_dict, fig=None, report_title="Relatório Consolidado"):
    """
    Cria relatório HTML contendo várias tabelas (em ordem) e, ao final, o gráfico (se for fornecido).
    tables_ordered_dict: Ordered dict-like {section_title: dataframe_or_None}
    fig: plotly figure opcional (será incluído no final)
    A ordem das chaves é respeitada.
    """
    # montar blocos de tabela
    body_parts = []
    for title, df in tables_ordered_dict.items():
        if (df is None) or df.empty:
            block = f"<h2>{title}</h2><p><i>Nenhum dado disponível para esta operadora.</i></p>"
        else:
            # ADICIONAR LINHA DE TOTAL ANTES DE GERAR HTML
            final_df = adicionar_linha_total(df)
            block = f"<h2>{title}</h2>" + _styler_to_html(final_df)
        body_parts.append(f'<div class="table-block">{block}</div>')

    grafico_html = ""
    if fig is not None:
        grafico_html = "<h2>Gráfico Resumo (Total Geral)</h2>" + fig.to_html(full_html=False, include_plotlyjs='cdn')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{report_title}</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 18px; color: #333; }}
            h1 {{ color: #007bff; }}
            h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 22px; }}
            p {{ margin: 8px 0 14px 0; }}
            .dataframe {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }}
            .dataframe th, .dataframe td {{ padding: 8px; text-align: right; border: 1px solid #ddd; word-wrap: break-word; }}
            .dataframe th {{ background-color: #f2f2f2; text-align: left; }}
            .js-plotly-plot {{ width: 70% !important; margin: 0 auto; height: auto; }}
            .table-block {{ page-break-inside: avoid; margin-bottom: 18px; }}
            .total-row {{ font-weight: bold; background-color: #e0f7fa; }} /* Estilo para a linha de total no HTML puro */
        </style>
    </head>
    <body>
        <h1>{report_title}</h1>

        {"".join(body_parts)}

        {grafico_html}
    </body>
    </html>
    """
    return html_content.encode('utf-8')

# ---------------- Aplicação principal ----------------
def main():
    st.title('Análise de Quilometragem')
    st.markdown('Faça o upload do seu arquivo de texto (.txt) para visualizar a quilometragem percorrida, com falhas e ociosa.')

    uploaded_file = st.file_uploader("Escolha um arquivo de Texto (.txt)", type=['txt'])

    if uploaded_file:
        try:
            # --- Leitura adaptativa ---
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
            except Exception:
                uploaded_file.seek(0)
                try:
                    df = pd.read_csv(uploaded_file, sep=';')
                except Exception:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep='\t')

            st.success('Arquivo carregado com sucesso!')

            # --- Padronização de colunas ---
            col_map = {
                'Nome Operadora': ['Nome Operadora', 'Nome Garagem'],
                'Distância': ['Distância', 'Distancia'],
                'Passageiros': ['Passageiros'],
                'Intervalo Viagem': ['Intervalo Viagem'],
                'Desc. Tipo Veículo': ['Desc. Tipo Veículo', 'Tipo Veiculo', 'Tipo de Veículo'],
                'Código Externo Linha': ['Código Externo Linha', 'Codigo Externo Linha', 'codigo externo linha'],
                'Viagem': ['Viagem'] 
            }

            rename_dict = {}
            for new_name, possible_names in col_map.items():
                for col in df.columns:
                    normalized_col = unidecode(col).lower()
                    normalized_possible = [unidecode(p).lower() for p in possible_names]
                    if any(p in normalized_col for p in normalized_possible):
                        rename_dict[col] = new_name
                        break
            df.rename(columns=rename_dict, inplace=True)

            required_cols = list(col_map.keys())
            missing_cols = [c for c in required_cols if c not in df.columns]

            if missing_cols:
                st.error("Colunas ausentes: " + ", ".join(missing_cols))
                st.write("Colunas encontradas:", df.columns.tolist())
                return

            # --- Filtros e tratamento ---
            df = df[~df['Nome Operadora'].str.contains('VIAFEIRA', case=False, na=False)].copy()
            df = df[df['Viagem'] == 'Nor.'].copy()

            intervalo_td = pd.to_timedelta(df['Intervalo Viagem'], errors='coerce')
            df['Intervalo_min'] = intervalo_td.dt.total_seconds() / 60.0
            mask_na = df['Intervalo_min'].isna()
            df.loc[mask_na, 'Intervalo_min'] = pd.to_numeric(df.loc[mask_na, 'Intervalo Viagem'], errors='coerce')

            df['Passageiros'] = pd.to_numeric(df['Passageiros'], errors='coerce').fillna(0)
            df['Código Externo Linha'] = df['Código Externo Linha'].astype(str).str.strip()
            df['Codigo_Num'] = pd.to_numeric(df['Código Externo Linha'].str.extract(r'(\d+)')[0], errors='coerce')
            df['Distância (km)'] = pd.to_numeric(df['Distância'], errors='coerce').fillna(0) / 1000.0

            especiais_mask = df['Codigo_Num'].isin([128, 129])
            remover_mask = (df['Passageiros'] == 0) & (df['Intervalo_min'] < 5)
            df_filtered = df[ especiais_mask | (~remover_mask) ].copy()

            # --- Sidebar ---
            st.sidebar.header('Filtros')

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
                        df_to_filter = df_to_filter[
                            (df_to_filter['Data Coleta'] >= start_date) & 
                            (df_to_filter['Data Coleta'] <= end_date)
                        ].copy()

            operadoras = ['Total Geral'] + sorted(df_to_filter['Nome Operadora'].unique().astype(str))
            selected_operadora = st.sidebar.selectbox("Selecione a Operadora", operadoras)

            df_final = (
                df_to_filter if selected_operadora == 'Total Geral'
                else df_to_filter[df_to_filter['Nome Operadora'] == selected_operadora]
            ).copy()

            if df_final.empty:
                st.warning("Nenhum dado encontrado com os filtros aplicados.")
                return

            # --- TABELAS: calcular por tipo de veículo (para exibição antes do gráfico) ---
            # tipo_km contém: Nome Operadora, Desc. Tipo Veículo, Distância (km)
            tipo_km = df_final.groupby(['Nome Operadora', 'Desc. Tipo Veículo'])['Distância (km)'].sum().reset_index()
            tipo_km.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
            tipo_km['Km Falha'] = tipo_km.apply(lambda r: calcular_km_falha(r['Nome Operadora'], r['Km Percorrido']), axis=1)
            tipo_km['Km Ociosa'] = tipo_km['Km Falha'].apply(calcular_km_ociosa)

            # Montar tabela_final conforme seleção (usada também no relatório)
            if selected_operadora == "Total Geral":
                tabela_final = tipo_km.groupby('Desc. Tipo Veículo')[['Km Percorrido', 'Km Falha', 'Km Ociosa']].sum().reset_index()
                tabela_final = tabela_final.sort_values(by='Km Percorrido', ascending=False).set_index('Desc. Tipo Veículo')
            else:
                tabela_final = tipo_km[tipo_km['Nome Operadora'] == selected_operadora].drop(columns=['Nome Operadora'])
                tabela_final = tabela_final.sort_values(by='Km Percorrido', ascending=False).set_index('Desc. Tipo Veículo')

            # -------- Exibição: TABELAS PRIMEIRO --------
            st.header(f"Detalhamento de Quilometragem por Tipo de Veículo - {selected_operadora}")

            if selected_operadora == "Total Geral":
                # São João
                mask_sj = df_to_filter['Nome Operadora'].astype(str).str.contains('sao joao|são joão|saojoao', case=False, na=False)
                if mask_sj.any():
                    tipo_km_sj = df_to_filter[mask_sj].groupby('Desc. Tipo Veículo')['Distância (km)'].sum().reset_index()
                    tipo_km_sj.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                    tipo_km_sj['Km Falha'] = tipo_km_sj['Km Percorrido'].apply(lambda x: calcular_km_falha('São João', x))
                    tipo_km_sj['Km Ociosa'] = tipo_km_sj['Km Falha'].apply(calcular_km_ociosa)
                    tabela_sj = tipo_km_sj.sort_values(by='Km Percorrido', ascending=False).set_index('Desc. Tipo Veículo')
                    
                    st.subheader("Operadora — São João")
                    # CORREÇÃO: Usar .style.format(formatar_br, subset=...)
                    tabela_sj_com_total = adicionar_linha_total(tabela_sj)
                    st.dataframe(tabela_sj_com_total.style.format(formatar_br, subset=['Km Percorrido', 'Km Falha', 'Km Ociosa']).apply(
                        lambda row: ['font-weight: bold; background-color: #e0f7fa;'] * len(row) if row.name == 'Total Geral (Km)' else [''] * len(row), axis=1), 
                        use_container_width=True)
                else:
                    st.subheader("Operadora — São João")
                    st.info("Nenhum dado disponível para esta operadora.")

                # Rosa
                mask_rosa = df_to_filter['Nome Operadora'].astype(str).str.contains('rosa', case=False, na=False)
                if mask_rosa.any():
                    tipo_km_rosa = df_to_filter[mask_rosa].groupby('Desc. Tipo Veículo')['Distância (km)'].sum().reset_index()
                    tipo_km_rosa.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                    tipo_km_rosa['Km Falha'] = tipo_km_rosa['Km Percorrido'].apply(lambda x: calcular_km_falha('Rosa', x))
                    tipo_km_rosa['Km Ociosa'] = tipo_km_rosa['Km Falha'].apply(calcular_km_ociosa)
                    tabela_rosa = tipo_km_rosa.sort_values(by='Km Percorrido', ascending=False).set_index('Desc. Tipo Veículo')
                    
                    st.subheader("Operadora — Rosa")
                    # CORREÇÃO: Usar .style.format(formatar_br, subset=...)
                    tabela_rosa_com_total = adicionar_linha_total(tabela_rosa)
                    st.dataframe(tabela_rosa_com_total.style.format(formatar_br, subset=['Km Percorrido', 'Km Falha', 'Km Ociosa']).apply(
                        lambda row: ['font-weight: bold; background-color: #e0f7fa;'] * len(row) if row.name == 'Total Geral (Km)' else [''] * len(row), axis=1),
                        use_container_width=True)
                else:
                    st.subheader("Operadora — Rosa")
                    st.info("Nenhum dado disponível para esta operadora.")

                # Total Geral (consolidada)
                st.subheader("Tabela Consolidada — Total Geral")
                # CORREÇÃO: Usar .style.format(formatar_br, subset=...)
                tabela_final_com_total = adicionar_linha_total(tabela_final)
                st.dataframe(tabela_final_com_total.style.format(formatar_br, subset=['Km Percorrido', 'Km Falha', 'Km Ociosa']).apply(
                    lambda row: ['font-weight: bold; background-color: #e0f7fa;'] * len(row) if row.name == 'Total Geral (Km)' else [''] * len(row), axis=1),
                    use_container_width=True)
            else:
                # Apenas a operadora selecionada
                st.subheader(f"Tabela — {selected_operadora}")
                if tabela_final is None or tabela_final.empty:
                    st.info("Nenhum dado disponível para esta operadora.")
                else:
                    # CORREÇÃO: Usar .style.format(formatar_br, subset=...)
                    tabela_final_com_total = adicionar_linha_total(tabela_final)
                    st.dataframe(tabela_final_com_total.style.format(formatar_br, subset=['Km Percorrido', 'Km Falha', 'Km Ociosa']).apply(
                        lambda row: ['font-weight: bold; background-color: #e0f7fa;'] * len(row) if row.name == 'Total Geral (Km)' else [''] * len(row), axis=1),
                        use_container_width=True)

            # -------- Agora o gráfico (APÓS as tabelas) --------
            st.markdown("---")
            st.header("Gráfico Resumo de Quilometragem")

            # --- Agrupamento para gráfico (mantendo lógica anterior) ---
            operadoras_km = df_final.groupby('Nome Operadora')['Km Percorrido'].sum().reset_index() if 'Km Percorrido' in df_final.columns else None
            # Note: quando df_final corresponde a Total Geral, recomputamos a partir de df_to_filter
            if selected_operadora == 'Total Geral':
                operadoras_km = df_to_filter.groupby('Nome Operadora')['Distância (km)'].sum().reset_index()
                operadoras_km.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                operadoras_km['Km Falha'] = operadoras_km.apply(
                    lambda r: calcular_km_falha(r['Nome Operadora'], r['Km Percorrido']), axis=1
                )
                operadoras_km['Km Ociosa'] = operadoras_km['Km Falha'].apply(calcular_km_ociosa)

                data_plot = pd.DataFrame({
                    'Nome Operadora': ['Total Geral'],
                    'Km Percorrido': [operadoras_km['Km Percorrido'].sum()],
                    'Km Falha': [operadoras_km['Km Falha'].sum()],
                    'Km Ociosa': [operadoras_km['Km Ociosa'].sum()]
                })
                title_prefix = "Métricas de Quilometragem (Total Geral)"
            else:
                # quando é uma operadora específica, usamos os valores já em tabela_final
                # reconstruir valores para o gráfico com base na soma da tabela_final
                if tabela_final is not None and not tabela_final.empty:
                    kp = tabela_final['Km Percorrido'].sum()
                    kf = tabela_final['Km Falha'].sum()
                    ko = tabela_final['Km Ociosa'].sum()
                else:
                    kp = kf = ko = 0.0
                data_plot = pd.DataFrame({
                    'Nome Operadora': [selected_operadora],
                    'Km Percorrido': [kp],
                    'Km Falha': [kf],
                    'Km Ociosa': [ko]
                })
                title_prefix = f"Métricas de Quilometragem - {selected_operadora}"

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
                text_auto='.2f',
                color_discrete_map={
                    "Km Percorrido": "#1f77b4", 
                    "Km Falha": "#ff7f0e", 
                    "Km Ociosa": "#2ca02c" 
                }
            )

            # Ajuste de layout para evitar conflito entre rótulo e eixo no PDF
            fig.update_layout(
                height=500,
                width=700,
                autosize=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=90, r=40, t=70, b=40)
            )
            fig.update_traces(marker=dict(line=dict(width=0)))
            fig.update_traces(textposition='outside')

            st.plotly_chart(fig, use_container_width=True)

            # ------------------- DOWNLOAD (relatório simples: segue comportamento da tela) -------------------
            st.markdown("---")
            # Se for Total Geral -> montar um dict com as 3 tabelas (São João, Rosa, Total)
            if selected_operadora == "Total Geral":
                # preparar as 3 tabelas (em ordem)
                tables_dict = {}

                # São João
                mask_sj = df_to_filter['Nome Operadora'].astype(str).str.contains('sao joao|são joão|saojoao', case=False, na=False)
                if mask_sj.any():
                    tipo_km_sj = df_to_filter[mask_sj].groupby('Desc. Tipo Veículo')['Distância (km)'].sum().reset_index()
                    tipo_km_sj.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                    tipo_km_sj['Km Falha'] = tipo_km_sj['Km Percorrido'].apply(lambda x: calcular_km_falha('São João', x))
                    tipo_km_sj['Km Ociosa'] = tipo_km_sj['Km Falha'].apply(calcular_km_ociosa)
                    tabela_sj = tipo_km_sj.sort_values(by='Km Percorrido', ascending=False).set_index('Desc. Tipo Veículo')
                    tables_dict["Operadora — São João"] = tabela_sj
                else:
                    tables_dict["Operadora — São João"] = None

                # Rosa
                mask_rosa = df_to_filter['Nome Operadora'].astype(str).str.contains('rosa', case=False, na=False)
                if mask_rosa.any():
                    tipo_km_rosa = df_to_filter[mask_rosa].groupby('Desc. Tipo Veículo')['Distância (km)'].sum().reset_index()
                    tipo_km_rosa.rename(columns={'Distância (km)': 'Km Percorrido'}, inplace=True)
                    tipo_km_rosa['Km Falha'] = tipo_km_rosa['Km Percorrido'].apply(lambda x: calcular_km_falha('Rosa', x))
                    tipo_km_rosa['Km Ociosa'] = tipo_km_rosa['Km Falha'].apply(calcular_km_ociosa)
                    tabela_rosa = tipo_km_rosa.sort_values(by='Km Percorrido', ascending=False).set_index('Desc. Tipo Veículo')
                    tables_dict["Operadora — Rosa"] = tabela_rosa
                else:
                    tables_dict["Operadora — Rosa"] = None

                # Total Geral
                tables_dict["Tabela Consolidada — Total Geral"] = tabela_final if (tabela_final is not None and not tabela_final.empty) else None

                html_consolidado = create_full_html_report_tables_then_chart(tables_dict, fig=fig, report_title="Relatório Consolidado - São João / Rosa / Total")
                st.download_button(
                    label="📘 Baixar Relatório (São João, Rosa, Total) - HTML",
                    data=html_consolidado,
                    file_name="Relatorio_SaoJoao_Rosa_Total.html",
                    mime="text/html"
                )
            else:
                # relatório com apenas a tabela da operadora selecionada e depois o gráfico
                # tabela já está em tabela_final
                html_single = create_full_html_report_single_table(tabela_final, f"Tabela — {selected_operadora}", fig=fig, selected_operadora=selected_operadora)
                st.download_button(
                    label=f"📄 Baixar Relatório ({selected_operadora}) - HTML",
                    data=html_single,
                    file_name=f"Relatorio_{selected_operadora}.html",
                    mime="text/html"
                )

            st.info("Abra o HTML e aperte **Ctrl+P → Salvar como PDF** para gerar o PDF colorido.")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")

if __name__ == '__main__':
    main()