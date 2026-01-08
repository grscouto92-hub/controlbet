import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime

# --- Configuração da Página ---
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
        /* overflow: hidden; <--- REMOVIDO PARA EVITAR BUGS NO MOBILE */
    }
    
    .blur-content {
        filter: blur(5px);
        opacity: 0.4;
        pointer-events: none; /* Impede clicar no texto borrado */
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
        background: rgba(0, 0, 0, 0.2); /* Fundo levemente escurecido */
        border-radius: 12px; /* Acompanha a borda do card */
    }

    .btn-telegram {
        background-color: #0088cc; /* Azul Telegram */
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

# --- FUNÇÃO 1: Exibe Card Aberto (Normal) ---
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

# --- FUNÇÃO 2: Exibe Card Bloqueado (CORRIGIDA) ---
def exibir_card_bloqueado(row):
    link_telegram = "https://t.me/SEU_LINK_AQUI"
    
    # Separando as strings para evitar erro de indentação/renderização
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

    # Montagem final garantida
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
