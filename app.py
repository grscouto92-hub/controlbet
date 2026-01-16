import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", page_icon="📈", layout="wide")

# --- CSS Otimizado (Visual Limpo) ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 26px; font-weight: bold;}
    .stButton button {width: 100%; border-radius: 8px; font-weight: bold; height: 3em;}
    /* Estilo do Botão de Link */
    a.link-btn {
        text-decoration: none; padding: 12px 20px; color: white !important;
        background-color: #374df5; /* Azul SofaScore */
        border-radius: 8px; border: 1px solid #374df5;
        display: block; text-align: center; width: 100%;
        font-weight: bold; font-size: 16px; transition: 0.3s;
    }
    a.link-btn:hover {background-color: #2b3bb5; border-color: #2b3bb5;}
</style>
""", unsafe_allow_html=True)

# --- LISTAS PRONTAS (Agilidade) ---
LIGAS_COMUNS = [
    "Brasileirão Série A", "Brasileirão Série B", "Copa do Brasil",
    "Premier League (ING)", "La Liga (ESP)", "Serie A (ITA)", "Bundesliga (ALE)",
    "Champions League", "Libertadores", "Sul-Americana", "Outra"
]

MERCADOS_COMUNS = [
    "Match Odds (Vencedor)", "Over 1.5 Gols", "Over 2.5 Gols", "Over 0.5 HT",
    "Under 2.5 Gols", "Ambas Marcam", "Handicap Asiático", "Empate Anula", "Outro"
]

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_gsheets():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("⚠️ Configuração de credenciais do Google não encontrada.")
            return None
            
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except Exception as e:
        st.error(f"Erro ao conectar na Planilha: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet: return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("✅ Aposta Salva!", icon="💰")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("💼 Gestão de Banca Profissional")

# 1. Carregar Dados
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial
lucro_total = 0.0

if not df.empty:
    for col in ['Lucro_Real', 'Valor_Entrada']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0.0
    c2.metric("ROI", f"{roi:.2f}%")
    
    resolvidas = df[df['Resultado'].isin(['Green', 'Red'])]
    winrate = (len(resolvidas[resolvidas['Resultado']=='Green']) / len(resolvidas) * 100) if not resolvidas.empty else 0
    c3.metric("Winrate", f"{winrate:.1f}%")
    c4.metric("Entradas", len(df))

st.divider()

# 2. ÁREA DE CONSULTA RÁPIDA (SofaScore)
col_btn, col_vazia = st.columns([1, 2]) # Botão ocupa 1/3 da tela para não ficar gigante
with col_btn:
    st.markdown(f'<a href="https://www.sofascore.com/pt/" target="_blank" class="link-btn">📊 Abrir SofaScore (Jogos de Hoje)</a>', unsafe_allow_html=True)

st.divider()

# 3. FORMULÁRIO DE REGISTRO
st.subheader("📝 Registrar Nova Entrada")

with st.container(border=True):
    # Finanças
    st.caption("💰 DADOS FINANCEIROS")
    cf1, cf2, cf3 = st.columns(3)
    valor_entrada = cf1.number_input("Entrada (R$)", min_value=0.0, value=20.0, step=1.0)
    valor_retorno = cf2.number_input("Retorno Total (R$)", min_value=0.0, value=28.0, step=1.0)
    
    odd_calc = 0.0
    if valor_entrada > 0: odd_calc = valor_retorno / valor_entrada
    cf3.markdown(f"<div style='text-align:center; padding:5px; background:#e0f2f1; border-radius:5px;'><b>Odd Calculada<br>{odd_calc:.3f}</b></div>", unsafe_allow_html=True)

    # Detalhes
    st.caption("⚽ DADOS DO JOGO")
    cd1, cd2, cd3 = st.columns(3)
    liga_sel = cd1.selectbox("Liga", LIGAS_COMUNS)
    jogo_txt = cd2.text_input("Jogo (Casa x Fora)", placeholder="Ex: Flamengo x Vasco")
    data_sel = cd3.date_input("Data", date.today())

    # Resultado
    st.caption("📊 STATUS")
    co1, co2, co3 = st.columns(3)
    mercado_sel = co1.selectbox("Mercado", MERCADOS_COMUNS)
    res_sel = co2.selectbox("Resultado", ["Pendente", "Green", "Red", "Reembolso"])
    obs_txt = co3.text_input("Obs / Estratégia")

    if st.button("💾 CONFIRMAR REGISTRO", type="primary"):
        if valor_entrada > 0 and jogo_txt:
            lucro_final = 0.0
            if res_sel == "Green": lucro_final = valor_retorno - valor_entrada
            elif res_sel == "Red": lucro_final = -valor_entrada
            
            salvar_registro([
                data_sel.strftime("%d/%m/%Y"), liga_sel, jogo_txt, mercado_sel,
                valor_entrada, valor_retorno, f"{odd_calc:.3f}",
                res_sel, lucro_final, obs_txt
            ])
        else:
            st.warning("Preencha o valor e o nome do jogo.")

# 4. HISTÓRICO
if not df.empty:
    st.divider()
    t1, t2 = st.tabs(["📋 Lista de Apostas", "📈 Gráfico de Lucro"])
    with t1:
        st.dataframe(df.iloc[::-1], use_container_width=True)
    with t2:
        df_g = df.copy()
        df_g['Saldo'] = banca_inicial + df_g['Lucro_Real'].cumsum()
        st.plotly_chart(px.line(df_g, y='Saldo', markers=True, title="Crescimento da Banca"), use_container_width=True)
