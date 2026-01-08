import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="GuiTips | Canal Oficial", page_icon="🦁", layout="centered")

# --- CSS Personalizado ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    
    /* Estilo dos Cards */
    .tip-card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        color: #ffffff !important;
    }
    .tip-header {
        display: flex;
        justify-content: space-between;
        color: #aaaaaa;
        font-size: 0.8rem;
        margin-bottom: 8px;
    }
    .tip-match {
        font-size: 1.1rem;
        font-weight: bold;
        color: #ffffff !important;
        margin-bottom: 10px;
    }
    .tip-bet {
        background-color: #2b2b2b;
        padding: 10px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #383838;
        color: #ffffff !important;
    }
    
    /* Destaques dentro da aposta */
    .tip-odd {
        color: #00e676 !important;
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    /* Badge de Confiança */
    .tip-confidence {
        font-size: 0.75rem;
        color: #ffd700;
        background-color: #333333;
        padding: 4px 8px;
        border-radius: 4px;
        margin-right: 10px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
        border: 1px solid #555;
    }

    .tip-analysis { color: #dddddd !important; }
    .tip-footer { color: #dddddd !important; }

    /* Cores de Status */
    .status-green { border-left-color: #00e676 !important; }
    .status-red { border-left-color: #ff1744 !important; }
    .status-pending { border-left-color: #ff9100 !important; }
    
    /* Ajuste nas abas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #0e1117; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #262730; color: #ff4b4b !important; }

    /* ANIMAÇÃO BOTÃO PULSE (CTA) */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 230, 118, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }
    }
    .cta-button {
        display: block;
        width: 100%;
        padding: 12px;
        background-color: #00e676; /* Verde Neon */
        color: #000 !important;
        text-align: center;
        font-weight: bold;
        text-decoration: none;
        border-radius: 8px;
        margin-bottom: 20px;
        animation: pulse 2s infinite;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .cta-button:hover {
        background-color: #00c853;
        color: #000 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Funções Auxiliares ---
def limpar_numero(valor):
    if isinstance(valor, (int, float)): return valor
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_resultado(row):
    status = str(row['Status']).strip().title()
    odd = limpar_numero(row['Odd'])
    unidades = limpar_numero(row['Unidades'])
    
    if status == 'Green': return (odd - 1) * unidades
    elif status == 'Red': return -unidades
    else: return 0.0

def exibir_card(row):
    status = str(row['Status']).strip().title()
    confianca = str(row.get('Confiança', '')).strip()
    
    css_class = "status-pending"
    icone = "⏳ Pendente"
    
    if status == "Green": 
        css_class = "status-green"
        icone = "✅ Green"
    elif status == "Red": 
        css_class = "status-red"
        icone = "❌ Red"
    elif status == "Anulada":
        icone = "🔄 Anulada"

    html_confianca = ""
    if confianca:
        html_confianca = f'<span class="tip-confidence">🎯 {confianca}</span>'

    html_card = f"""
    <div class="tip-card {css_class}">
        <div class="tip-header">
            <span>⚽ {row['Liga']}</span>
            <span>{row['Data']} • {row['Hora']}</span>
        </div>
        <div class="tip-match">
            {row['Jogo']}
        </div>
        <div class="tip-bet">
            <div style="display: flex; flex-direction: column;">
                <span style="font-weight: 500;">{row['Aposta']}</span>
            </div>
            <div style="display: flex; align-items: center;">
                {html_confianca}
                <span class="tip-odd">@{row['Odd']}</span>
            </div>
        </div>
        <div class="tip-analysis" style="margin-top: 12px; font-size: 0.9rem;">
            💡 <i>"{row['Analise']}"</i>
        </div>
        <div class="tip-footer" style="margin-top: 10px; font-size: 0.85rem; text-align: right; font-weight: bold;">
            {icone} | Unidades: {row['Unidades']}
        </div>
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)

# --- Conexão Google Sheets ---
@st.cache_data(ttl=60) 
def carregar_tips():
    try:
        if "gcp_service_account" not in st.secrets: return pd.DataFrame()
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("ControlBET").worksheet("Tips")
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df['Odd_Num'] = df['Odd'].apply(limpar_numero)
            df['Unid_Num'] = df['Unidades'].apply(limpar_numero)
            df['Lucro'] = df.apply(calcular_resultado, axis=1)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar tips: {e}")
        return pd.DataFrame()

# --- Lógica Principal ---
def main():
    # Inicializa estado da paginação se não existir
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 0

    # 1. Cabeçalho
    col_logo, col_title = st.columns([1, 4])
    with col_logo: st.markdown("# 🦁")
    with col_title:
        st.markdown("### GuiTips")
        st.caption("Análises profissionais de Futebol")

    df = carregar_tips()
    if df.empty:
        st.warning("Não foi possível carregar os dados.")
        return

    # --- SIDEBAR COMPLETA ---
    with st.sidebar:
        # CTA BUTTON (Piscante)
        st.markdown("""
            <a href="https://t.me/seulink" target="_blank" class="cta-button">
                🚀 GRUPO VIP (Entrar)
            </a>
        """, unsafe_allow_html=True)

        st.divider()
        st.header("🔍 Filtros")
        
        # Busca por Texto
        busca_time = st.text_input("Buscar Time ou Jogo", placeholder="Ex: Flamengo")

        # Filtro de Liga
        todas_ligas = df['Liga'].unique().tolist()
        filtro_liga = st.multiselect("Filtrar por Liga", todas_ligas)
        
        # Aplicação dos Filtros
        if filtro_liga:
            df = df[df['Liga'].isin(filtro_liga)]
        
        if busca_time:
            # Filtra onde a coluna 'Jogo' contém o texto digitado (case insensitive)
            df = df[df['Jogo'].str.contains(busca_time, case=False, na=False)]

    # --- ESTATÍSTICAS ---
    df_res = df[df['Status'].isin(['Green', 'Red'])]
    greens = len(df_res[df_res['Status'] == 'Green'])
    total_resolvidas = len(df_res)
    winrate = (greens / total_resolvidas * 100) if total_resolvidas > 0 else 0
    lucro_total = df_res['Lucro'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Winrate", f"{winrate:.0f}%")
    c2.metric("Greens", f"{greens}")
    c3.metric("Finalizadas", f"{total_resolvidas}")
    c4.metric("Lucro (U)", f"{lucro_total:+.2f}")

    st.divider()

    # --- ABAS ---
    aba_jogos, aba_historico = st.tabs(["🔥 Jogos Abertos", "📊 Histórico e Gráficos"])

    df_pendentes = df[~df['Status'].isin(['Green', 'Red', 'Anulada'])]
    df_historico = df[df['Status'].isin(['Green', 'Red', 'Anulada'])]

    # --- ABA 1: JOGOS ABERTOS ---
    with aba_jogos:
        st.markdown("##### Próximas Entradas")
        if df_pendentes.empty:
            st.info("Nenhuma entrada encontrada.")
        else:
            df_pendentes = df_pendentes.iloc[::-1]
            for i, row in df_pendentes.iterrows():
                exibir_card(row)

    # --- ABA 2: HISTÓRICO ---
    with aba_historico:
        if not df_res.empty:
            # Tenta converter data
            try:
                df_res['Data_Dt'] = pd.to_datetime(df_res['Data'], dayfirst=True, errors='coerce')
            except:
                df_res['Data_Dt'] = pd.NaT

            # Remove datas invalidas para gráficos
            df_chart = df_res.dropna(subset=['Data_Dt']).copy()

            # 1. GRÁFICO DE EVOLUÇÃO (LINHA)
            st.markdown("##### 📈 Evolução da Banca")
            df_diario = df_chart.groupby('Data_Dt')['Lucro'].sum().reset_index().sort_values('Data_Dt')
            df_diario['Acumulado'] = df_diario['Lucro'].cumsum()
            
            fig_line = px.line(df_diario, x='Data_Dt', y='Acumulado', markers=True)
            fig_line.update_traces(line_color='#00e676', line_width=3)
            fig_line.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            fig_line.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=300)
            st.plotly_chart(fig_line, use_container_width=True)

            # 2. GRÁFICO MENSAL (BARRAS) - NOVO!
            st.markdown("##### 📅 Resultado Mensal")
            df_chart['Mes_Ano'] = df_chart['Data_Dt'].dt.strftime('%m/%Y')
            df_chart['Ano_Mes_Sort'] = df_chart['Data_Dt'].dt.strftime('%Y-%m') # Coluna auxiliar para ordenar
            
            df_mensal = df_chart.groupby(['Ano_Mes_Sort', 'Mes_Ano'])['Lucro'].sum().reset_index()
            df_mensal = df_mensal.sort_values('Ano_Mes_Sort')

            # Cores condicionais (Verde se lucro > 0, Vermelho se < 0)
            colors = ['#00e676' if x >= 0 else '#ff1744' for x in df_mensal['Lucro']]

            fig_bar = px.bar(df_mensal, x='Mes_Ano', y='Lucro', text_auto='.2f')
            fig_bar.update_traces(marker_color=colors, textfont_size=12, textposition="outside")
            fig_bar.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=300, xaxis_title=None, yaxis_title="Lucro (U)")
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.divider()

        # --- PAGINAÇÃO DO HISTÓRICO ---
        st.markdown("##### Últimos Resultados")
        
        if df_historico.empty:
            st.info("Nenhum histórico disponível.")
        else:
            # Ordena do mais recente
            df_historico = df_historico.iloc[::-1]
            
            # Configuração da Paginação
            ITENS_POR_PAGINA = 10
            total_itens = len(df_historico)
            total_paginas = max(1, (total_itens - 1) // ITENS_POR_PAGINA + 1)
            
            # Garante que a página atual é válida
            if st.session_state.pagina_atual >= total_paginas:
                st.session_state.pagina_atual = total_paginas - 1
            if st.session_state.pagina_atual < 0:
                st.session_state.pagina_atual = 0

            # Fatiamento do DataFrame
            inicio = st.session_state.pagina_atual * ITENS_POR_PAGINA
            fim = inicio + ITENS_POR_PAGINA
            df_pagina = df_historico.iloc[inicio:fim]

            # Exibição dos cards da página atual
            for i, row in df_pagina.iterrows():
                exibir_card(row)
            
            # Botões de Navegação (Só mostra se tiver mais de 1 página)
            if total_paginas > 1:
                st.markdown("---")
                col_prev, col_info, col_next = st.columns([1, 2, 1])
                
                with col_prev:
                    if st.button("⬅️ Anterior", disabled=(st.session_state.pagina_atual == 0)):
                        st.session_state.pagina_atual -= 1
                        st.rerun() # Recarrega a página
                
                with col_info:
                    st.markdown(f"<div style='text-align: center; padding-top: 5px;'>Página <b>{st.session_state.pagina_atual + 1}</b> de <b>{total_paginas}</b></div>", unsafe_allow_html=True)
                
                with col_next:
                    if st.button("Próxima ➡️", disabled=(st.session_state.pagina_atual == total_paginas - 1)):
                        st.session_state.pagina_atual += 1
                        st.rerun() # Recarrega a página

    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px;">
        ⚠️ Aposte com responsabilidade. +18.<br>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
