import streamlit as st
import pandas as pd
import plotly.express as px
from unidecode import unidecode
import io
import base64

def main():
    # Configuração de Página
    st.set_page_config(layout="wide")

    # Funções utilitárias
    def format_brazil(number):
        """Formata número ao padrão brasileiro."""
        formatted = f"{int(number):,}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted

    def format_table_brazil(df):
        """Aplica formatação brasileira a colunas numéricas."""
        cols_to_exclude = ['Operadora', 'Tipo de Passagem', 'Nome Operadora', 'Nome Linha', 'Código Externo Linha']
        fmt = {col: format_brazil for col in df.columns if col not in cols_to_exclude}
        return df.style.format(fmt)

    # --- UI principal ---
    st.title('🚌 Análise de Passagens de Ônibus')
    st.markdown('Faça o upload da sua planilha para visualizar os dados de passagens e gerar gráficos interativos.')

    uploaded_file = st.file_uploader(
        "Escolha um arquivo Excel (.xlsx), CSV (.csv) ou de Texto (.txt)",
        type=['xlsx', 'csv', 'txt']
    )

    if uploaded_file:
        try:
            # Leitura do arquivo
            file_extension = uploaded_file.name.split('.')[-1].lower()
            if file_extension in ['csv', 'txt']:
                uploaded_file.seek(0)
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
                    except Exception:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, sep=';')
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success('✅ Arquivo carregado com sucesso!')

            # Mapeamento e normalização de colunas
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
            for new_name, possibles in col_map.items():
                normalized = [unidecode(p).lower() for p in possibles]
                for col in df.columns:
                    if unidecode(col).lower() in normalized:
                        rename_dict[col] = new_name
                        break

            df.rename(columns=rename_dict, inplace=True)

            required_cols = list(col_map.keys())
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                st.error(f'❌ Colunas não encontradas: {", ".join(missing)}')
                st.write("Colunas encontradas:", df.columns.tolist())
                st.stop()

            # Conversão de colunas numéricas
            numeric_cols = ['Inteiras', 'VT', 'VT Integração', 'Gratuidade',
                            'Passagens', 'Passagens Integração',
                            'Estudantes', 'Estudantes Integração']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

            # Criação de colunas unificadas
            df['Passagens_Inteiras'] = df['Inteiras']
            df['Passagens_VT'] = df['VT']
            df['Passagens_Gratuidade'] = df['Gratuidade']
            df['Passagens_Social'] = df['Passagens']
            df['Passagens_Estudantes'] = df['Estudantes']
            df['Passagens_Integracao'] = (df['VT Integração'] + 
                                        df['Passagens Integração'] + 
                                        df['Estudantes Integração'])

            total_geral_passagens = (
                df['Passagens_Inteiras'].sum() +
                df['Passagens_VT'].sum() +
                df['Passagens_Gratuidade'].sum() +
                df['Passagens_Social'].sum() +
                df['Passagens_Estudantes'].sum() +
                df['Passagens_Integracao'].sum()
            )

            # Filtros
            st.sidebar.header('Filtros')
            operadoras = ['Todas'] + sorted(df['Nome Operadora'].unique())
            selected_operadora = st.sidebar.selectbox('Operadora', operadoras)

            if selected_operadora != 'Todas':
                linhas_disponiveis = df[df['Nome Operadora'] == selected_operadora]['Nome Linha'].unique()
            else:
                linhas_disponiveis = df['Nome Linha'].unique()

            linhas = ['Todas'] + sorted(linhas_disponiveis)
            selected_linha = st.sidebar.selectbox('Linha', linhas)

            df_filtered = df.copy()
            if selected_operadora != 'Todas':
                df_filtered = df_filtered[df_filtered['Nome Operadora'] == selected_operadora]
            if selected_linha != 'Todas':
                df_filtered = df_filtered[df_filtered['Nome Linha'] == selected_linha]

            is_dark_mode = st.get_option("theme.base") == "dark"
            plotly_template = "plotly_dark" if is_dark_mode else "plotly_white"

            if not df_filtered.empty:
                # Gráfico 1
                st.header('📊 Tipos de Passagens')
                total_data = {
                    'Tipo de Passagem': ['Inteiras', 'VT', 'Gratuidade', 'Social', 'Estudantes', 'Integração'],
                    'Quantidade': [
                        df_filtered['Passagens_Inteiras'].sum(),
                        df_filtered['Passagens_VT'].sum(),
                        df_filtered['Passagens_Gratuidade'].sum(),
                        df_filtered['Passagens_Social'].sum(),
                        df_filtered['Passagens_Estudantes'].sum(),
                        df_filtered['Passagens_Integracao'].sum()
                    ]
                }
                total_df = pd.DataFrame(total_data)
                fig_tipos = px.bar(
                    total_df,
                    x='Tipo de Passagem',
                    y='Quantidade',
                    title='Quantidade de Passagens por Tipo',
                    labels={'Quantidade': 'Total de Passagens'},
                    color='Tipo de Passagem',
                    text='Quantidade',
                    template=plotly_template
                )
                fig_tipos.update_traces(texttemplate='%{text}', textposition='outside')
                fig_tipos.update_layout(margin=dict(t=50), height=500)
                st.plotly_chart(fig_tipos, use_container_width=True)

                # CSS do card
                if is_dark_mode:
                    neon_color = "#4682b4"
                    bg_color = "#121212"
                    text_color = "#a2c3df"
                    shadow_strength = "0 0 35px"
                else:
                    neon_color = "#4682b4"
                    bg_color = "#a2c3df"
                    text_color = "#000000"
                    shadow_strength = "0 0 15px"

                st.markdown(
                    f"""
                    <style>
                    .total-box {{
                        background-color: {bg_color};
                        color: {text_color};
                        padding: 15px;
                        border-radius: 16px;
                        text-align: center;
                        border: 2px solid {neon_color};
                        box-shadow: {shadow_strength} {neon_color};
                        margin: 15px 0;
                    }}
                    .total-number {{
                        font-size: 2.8em;
                        font-weight: 900;
                        margin: 0;
                        color: black;
                    }}
                    .total-label {{
                        font-size: 1.3em;
                        font-weight: 700;
                        margin-top: 8px;
                        opacity: 0.95;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2, col3 = st.columns([1, 3, 1])
                with col2:
                    st.markdown(
                        f"""
                        <div class="total-box">
                        <p class="total-label">TOTAL GERAL DE PASSAGEIROS</p>
                        <p class="total-number">{format_brazil(total_geral_passagens)}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                st.markdown('---')

                # Gráfico 2 + Aggregação por Operadora
                st.header('🏢 Total de Passagens por Operadora')
                cols_sum = ['Passagens_Inteiras', 'Passagens_VT', 'Passagens_Gratuidade',
                            'Passagens_Social', 'Passagens_Estudantes', 'Passagens_Integracao']
                df_op = df_filtered.groupby('Nome Operadora')[cols_sum].sum().reset_index()
                df_op['Total'] = df_op[cols_sum].sum(axis=1)
                df_op.columns = ['Operadora', 'Inteiras', 'VT', 'Gratuidade', 'Social', 'Estudantes', 'Integração', 'Total']

                fig_op = px.bar(
                    df_op,
                    x='Operadora',
                    y='Total',
                    title='Comparativo de Passagens por Operadora',
                    labels={'Total': 'Total de Passagens'},
                    color='Operadora',
                    text='Total',
                    template=plotly_template
                )
                fig_op.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_op.update_layout(margin=dict(t=50), height=500)
                st.plotly_chart(fig_op, use_container_width=True)

                st.subheader('Tabela por Operadora')

                styled = format_table_brazil(df_op)
                try:
                    st.data_editor(
                        styled,
                        use_container_width=True,
                        hide_index=True,
                        disabled=df_op.columns
                    )
                except:
                    st.dataframe(
                        df_op.style.format({c: "{:,.0f}" for c in df_op.columns if c != 'Operadora'}),
                        use_container_width=True
                    )

                # --- EXPORTAÇÃO HTML (Opção A) ---
                st.markdown("---")
                st.header("📥 Exportar relatório")

                # Preparar o HTML
                html_parts = []
                # Cabeçalho
                html_parts.append("<h1>Análise de Passagens de Ônibus</h1>")

                # Gráfico 1
                html_parts.append("<h2>Quantidade de Passagens por Tipo</h2>")
                html_parts.append(f"""
                <div style="transform: scaleX(0.8); transform-origin: left top; width: 100%;">
                    {fig_tipos.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})}
                </div>
                """)

                # Card total geral
                html_parts.append(f"""
                <div style="
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 12px;
                    border-radius: 12px;
                    text-align: center;
                    border: 1px solid {neon_color};
                    box-shadow: 0 0 6px {neon_color};
                    margin: 12px auto;
                    max-width: 420px;">
                    
                    <h3 style="
                        margin: 6px 0;
                        font-size: 18px;
                        font-weight: 700;
                        color: {text_color};">
                        TOTAL GERAL DE PASSAGEIROS
                    </h3>
                    
                    <p style="
                        font-size: 22px;
                        font-weight: 800;
                        margin: 4px 0;
                        color: black;">
                        {format_brazil(total_geral_passagens)}
                    </p>
                </div>
                """)

                # Gráfico 2
                html_parts.append("<h2>Total de Passagens por Operadora</h2>")
                html_parts.append(fig_op.to_html(full_html=False, include_plotlyjs=False, config={'responsive': True}))

                # Tabela
                html_parts.append("<h3>Tabela por Operadora</h3>")
                # Usar pandas to_html para a tabela (sem índice extra)
                html_parts.append(df_op.to_html(index=False))

                full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Relatório de Passagens</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1, h2, h3 {{ color: #003366; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                        table, th, td {{
                            border: 1px solid #ccc;
                        }}
                        th, td {{
                            padding: 8px;
                            text-align: center;
                            font-size: 14px;
                        }}
                        th {{
                            background-color: #f2f2f2;
                        }}
                        @media print {{
                        img, .js-plotly-plot-svg {{
                            max-width: 100% !important;
                            height: auto !important;
                        }}
                        h1, h2, h3 {{ page-break-after: avoid; }}
                        table {{ page-break-inside: auto; }}
                        tr    {{ page-break-inside: avoid; page-break-after: auto; }}
                        thead {{ display: table-header-group; }}
                        tfoot {{ display: table-footer-group; }}
                        }}
                    </style>
                </head>
                <body>
                    {''.join(html_parts)}
                </body>
                </html>
                """

                st.download_button(
                    label="📄 Baixar Relatório em HTML",
                    data=full_html,
                    file_name="relatorio_passagens.html",
                    mime="text/html"
                )

                st.info("Depois de baixar o HTML, abra no navegador e use **Ctrl+P → Salvar como PDF**.")

            else:
                st.warning('⚠️ Nenhum dado para os filtros selecionados.')

        except Exception as e: 
            st.error(f"❌ Erro ao processar o arquivo: {e}")
