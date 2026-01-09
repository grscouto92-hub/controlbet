import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime

# --- Configuração da Página (OBRIGATÓRIO SER A PRIMEIRA LINHA STREAMLIT) ---
st.set_page_config(page_title="GuiTips | Canal Oficial", page_icon="🦁", layout="centered")

# --- CSS Personalizado ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    
    /* Estilo dos Cards Normais */
    .tip-card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        color: #ffffff !important;
        position: relative;
    }
    
    /* Estilo para Cards Bloqueados (Blur) */
    .tip-card-locked {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #555; /* Cinza */
        position: relative;
    }
    
    .blur-content {
        filter: blur(5px);
        opacity: 0.4;
        pointer-events: none;
        user-select: none;
    }

    /* O Botão/Overlay de Desbloqueio */
    .unlock-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 10;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 12px;
    }

    .btn-telegram {
        background-color: #0088cc;
        color: white !important;
        padding: 12px 24px;
        border-radius: 50px;
        text-decoration: none;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0, 136, 204, 0.5);
        transition: transform 0.2s;
        border: 1px solid rgba(255,255,255,0.3);
        font-size: 0.9rem;
    }
    .btn-telegram:hover {
        transform: scale(1.05);
        background-color: #0099e6;
    }

    /* Classes auxiliares */
    .tip-header { display: flex; justify-content: space-between; color: #aaaaaa; font-size: 0.8rem; margin-bottom: 8px; }
    .tip-match { font-size: 1.1rem; font-weight: bold; color: #ffffff !important; margin-bottom: 10px; }
    .tip-bet { background-color: #2b2b2b; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #383838; color: #ffffff !important; }
    .tip-odd { color: #00e676 !important; font-weight: bold; font-size: 1.1rem; }
    .tip-confidence { font-size: 0.75rem; color: #ffd700; background-color: #333333; padding: 4px 8px; border-radius: 4px; margin-right: 10px; font-weight: bold; display: inline-flex; align-items: center; border: 1px solid #555; }
    .tip-analysis { color: #dddddd !important; }
    .tip-footer { color: #dddddd !important; }
    .status-green { border-left-color: #00e676 !important; }
    .status-red { border-left-color: #ff1744 !important; }
    .status-pending { border-left-color: #ff9100 !important; }
    
    /* CTA Lateral */
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(0, 230, 118, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); } }
    .cta-button { display: block; width: 100%; padding: 12px; background-color: #00e676; color: #000 !important; text-align: center; font-weight: bold; text-decoration: none; border-radius: 8px; margin-bottom: 20px; animation: pulse 2s infinite; text-transform: uppercase; letter-spacing: 1px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #0e1117; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #262730; color: #ff4b4b !important; }
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
    
    if status == "Green": css_class, icone = "status-green", "✅ Green"
    elif status == "Red": css_class, icone = "status-red", "❌ Red"
    elif status == "Anulada": icone = "🔄 Anulada"

    html_confianca = f'<span class="tip-confidence">🎯 {confianca}</span>' if confianca else ""

    html_card = f"""
    <div class="tip-card {css_class}">
        <div class="tip-header">
            <span>⚽ {row['Liga']}</span>
            <span>{row['Data']} • {row['Hora']}</span>
        </div>
        <div class="tip-match">{row['Jogo']}</div>
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

def exibir_card_bloqueado(row):
    link_telegram = "https://t.me/SEU_LINK_AQUI"
    
    # Separando as strings para evitar erro de indentação e HTML mal formatado
    conteudo_borrado = f"""
        <div class="tip-header">
            <span>⚽ {row['Liga']}</span>
            <span>{row['Data']} • {row['Hora']}</span>
        </div>
        <div class="tip-match">{row['Jogo']}</div>
        <div class="tip-bet">
            <span>Aposta Secreta VIP</span>
            <span class="tip-odd">@1.90</span>
        </div>
        <div class="tip-analysis" style="margin-top: 12px;">
            💡 Análise exclusiva para membros do grupo gratuito...
        </div>
    """
    
    overlay_botao = f"""
        <div class="unlock-overlay">
            <div style="font-size: 2rem; margin-bottom: 10px;">🔒</div>
            <a href="{link_telegram}" target="_blank" class="btn-telegram">
                VER NO TELEGRAM GRÁTIS
            </a>
            <div style="margin-top: 8px; font-size: 0.8rem; color: #ccc;">
                Toque para desbloquear
            </div>
        </div>
    """

    html_locked = f"""
    <div class="tip-card-locked">
        <div class="blur-content">
            {conteudo_borrado}
        </div>
        {overlay_botao}
    </div>
    """
    st.markdown(html_locked, unsafe_allow_html=True)

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
        # Se der erro aqui, ele será mostrado na tela em vez de tela preta
        st.error(f"Erro ao carregar tips: {e}")
        return pd.DataFrame()

# --- Lógica Principal ---
def main():
    if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0

    col_logo, col_title = st.columns([1, 4])
    with col_logo: st.markdown("# 🦁")
    with col_title:
        st.markdown("### GuiTips")
        st.caption("Análises profissionais de Futebol")

    df = carregar_tips()
    if df.empty:
        st.warning("Não foi possível carregar os dados ou conectar à planilha.")
        return

    # Sidebar
    with st.sidebar:
        st.markdown("""<a href="https://t.me/seulink" target="_blank" class="cta-button">🚀 GRUPO VIP (Entrar)</a>""", unsafe_allow_html=True)
        st.divider()
        st.header("🔍 Filtros")
        busca_time = st.text_input("Buscar Time ou Jogo", placeholder="Ex: Flamengo")
        filtro_liga = st.multiselect("Filtrar por Liga", df['Liga'].unique().tolist())
        
        if filtro_liga: df = df[df['Liga'].isin(filtro_liga)]
        if busca_time: df = df[df['Jogo'].str.contains(busca_time, case=False, na=False)]

    # Estatísticas
    df_res = df[df['Status'].isin(['Green', 'Red'])]
    greens = len(df_res[df_res['Status'] == 'Green'])
    total = len(df_res)
    winrate = (greens / total * 100) if total > 0 else 0
    lucro = df_res['Lucro'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Winrate", f"{winrate:.0f}%")
    c2.metric("Greens", f"{greens}")
    c3.metric("Finalizadas", f"{total}")
    c4.metric("Lucro (U)", f"{lucro:+.2f}")

    st.divider()

    aba_jogos, aba_historico = st.tabs(["🔥 Jogos Abertos", "📊 Histórico e Gráficos"])
    df_pendentes = df[~df['Status'].isin(['Green', 'Red', 'Anulada'])]
    df_historico = df[df['Status'].isin(['Green', 'Red', 'Anulada'])]

    # --- ABA 1: LÓGICA DO BLOQUEIO ---
    with aba_jogos:
        st.markdown("##### Próximas Entradas")
        
        if df_pendentes.empty:
            st.info("Nenhuma entrada pendente.")
        else:
            # Ordena: Mais recentes no topo
            df_pendentes = df_pendentes.iloc[::-1]
            
            for i, (index, row) in enumerate(df_pendentes.iterrows()):
                esta_filtrando = (filtro_liga or busca_time)
                
                # Se filtrar, mostra tudo. Se não, bloqueia a partir da 2ª.
                if esta_filtrando:
                    exibir_card(row)
                else:
                    if i == 0:
                        st.markdown("**🏆 Tip do Dia (Liberada):**")
                        exibir_card(row)
                    else:
                        if i == 1: st.markdown("---") 
                        exibir_card_bloqueado(row)

    # --- ABA 2: HISTÓRICO ---
    with aba_historico:
        if not df_res.empty:
            try: df_res['Data_Dt'] = pd.to_datetime(df_res['Data'], dayfirst=True, errors='coerce')
            except: df_res['Data_Dt'] = pd.NaT
            df_chart = df_res.dropna(subset=['Data_Dt']).copy()
            
            st.markdown("##### 📈 Evolução da Banca")
            df_diario = df_chart.groupby('Data_Dt')['Lucro'].sum().reset_index().sort_values('Data_Dt')
            df_diario['Acumulado'] = df_diario['Lucro'].cumsum()
            fig_line = px.line(df_diario, x='Data_Dt', y='Acumulado', markers=True)
            fig_line.update_traces(line_color='#00e676', line_width=3)
            fig_line.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            fig_line.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=300)
            st.plotly_chart(fig_line, use_container_width=True)

            st.markdown("##### 📅 Resultado Mensal")
            df_chart['Mes_Ano'] = df_chart['Data_Dt'].dt.strftime('%m/%Y')
            df_chart['Ano_Mes_Sort'] = df_chart['Data_Dt'].dt.strftime('%Y-%m')
            df_mensal = df_chart.groupby(['Ano_Mes_Sort', 'Mes_Ano'])['Lucro'].sum().reset_index().sort_values('Ano_Mes_Sort')
            colors = ['#00e676' if x >= 0 else '#ff1744' for x in df_mensal['Lucro']]
            fig_bar = px.bar(df_mensal, x='Mes_Ano', y='Lucro', text_auto='.2f')
            fig_bar.update_traces(marker_color=colors, textfont_size=12, textposition="outside")
            fig_bar.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0), height=300, xaxis_title=None, yaxis_title="Lucro (U)")
            st.plotly_chart(fig_bar, use_container_width=True)
            st.divider()

        st.markdown("##### Últimos Resultados")
        if df_historico.empty:
            st.info("Nenhum histórico disponível.")
        else:
            df_historico = df_historico.iloc[::-1]
            ITENS_POR_PAGINA = 10
            total_paginas = max(1, (len(df_historico) - 1) // ITENS_POR_PAGINA + 1)
            if st.session_state.pagina_atual >= total_paginas: st.session_state.pagina_atual = total_paginas - 1
            if st.session_state.pagina_atual < 0: st.session_state.pagina_atual = 0
            inicio = st.session_state.pagina_atual * ITENS_POR_PAGINA
            df_pagina = df_historico.iloc[inicio:inicio + ITENS_POR_PAGINA]
            for i, row in df_pagina.iterrows(): exibir_card(row)
            if total_paginas > 1:
                st.markdown("---")
                c_prev, c_info, c_next = st.columns([1, 2, 1])
                with c_prev: 
                    if st.button("⬅️ Anterior", disabled=(st.session_state.pagina_atual == 0)): 
                        st.session_state.pagina_atual -= 1
                        st.rerun()
                with c_info: st.markdown(f"<div style='text-align:center'>Página {st.session_state.pagina_atual + 1}/{total_paginas}</div>", unsafe_allow_html=True)
                with c_next: 
                    if st.button("Próxima ➡️", disabled=(st.session_state.pagina_atual == total_paginas - 1)): 
                        st.session_state.pagina_atual += 1
                        st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666; font-size: 12px;'>⚠️ Aposte com responsabilidade. +18.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # ISSO AQUI VAI IMPEDIR A TELA PRETA:
        st.error(f"Ocorreu um erro fatal na aplicação: {e}")
        st.info("Dica: Verifique se você instalou o 'plotly' e se a indentação do código está correta.")
