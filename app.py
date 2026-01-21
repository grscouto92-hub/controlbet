import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", page_icon="📈", layout="centered")

# --- CSS Otimizado (Visual e Layout) ---
st.markdown("""
<style>
    /* Ajuste de Espaçamento Geral */
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    
    /* Estilo do Botão de Link (SofaScore) */
    a.link-btn {
        text-decoration: none; padding: 12px 20px; color: white !important;
        background-color: #374df5; border-radius: 8px; border: 1px solid #374df5;
        display: block; text-align: center; width: 100%;
        font-weight: bold; font-size: 16px; transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    a.link-btn:hover {background-color: #2b3bb5; border-color: #2b3bb5;}

    /* --- TRUQUE PARA FORÇAR BOTÕES LADO A LADO NO MOBILE --- */
    /* Isso força as colunas a não empilharem em telas pequenas */
    [data-testid="column"] {
        width: calc(33.3% - 1rem) !important;
        flex: 1 1 calc(33.3% - 1rem) !important;
        min-width: 33.3% !important;
    }

    /* Estilo Geral dos Botões */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 700;
        height: 3em;
        border: 1px solid transparent;
        transition: all 0.2s;
    }

    /* Cores Específicas para os Botões (Baseado no Texto/Emoji) */
    /* Como não podemos colocar ID no botão, estilizamos todos e usamos o python para diferenciar o container */
</style>
""", unsafe_allow_html=True)

# --- LISTAS PRONTAS ---
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

# --- ATUALIZAR STATUS ---
def atualizar_status(indice_df, novo_resultado, lucro_calculado):
    sheet = conectar_gsheets()
    if sheet:
        # Ajuste de índice: Linha 1 é cabeçalho + índice começa em 0 = Linha + 2
        numero_linha = indice_df + 2 
        # Colunas H(8) e I(9). Se mudar a ordem na planilha, mude aqui.
        sheet.update_cell(numero_linha, 8, novo_resultado)
        sheet.update_cell(numero_linha, 9, lucro_calculado)
        
        st.toast(f"Atualizado para {novo_resultado}!", icon="🔄")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("💼 Gestão de Banca Pro")

df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial
lucro_total = 0.0

if not df.empty:
    for col in ['Lucro_Real', 'Valor_Entrada', 'Valor_Retorno']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
    
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Banca", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0.0
    c2.metric("ROI", f"{roi:.2f}%")
    
    resolvidas = df[df['Resultado'].isin(['Green', 'Red'])]
    winrate = (len(resolvidas[resolvidas['Resultado']=='Green']) / len(resolvidas) * 100) if not resolvidas.empty else 0
    c3.metric("Winrate", f"{winrate:.1f}%")

st.divider()

# Botão SofaScore
col_btn, _ = st.columns([1, 1])
with col_btn:
    st.markdown(f'<a href="https://www.sofascore.com/pt/" target="_blank" class="link-btn">📊 Abrir SofaScore</a>', unsafe_allow_html=True)

st.divider()

# Formulário (Sanfona Fechada por Padrão)
with st.expander("📝 Registrar Nova Entrada", expanded=False):
    with st.form("form_registro"):
        st.caption("💰 DADOS")
        cf1, cf2, cf3 = st.columns(3)
        valor_entrada = cf1.number_input("Entrada (R$)", value=20.0, step=1.0)
        valor_retorno = cf2.number_input("Retorno (R$)", value=28.0, step=1.0)
        
        odd_calc = 0.0
        if valor_entrada > 0: odd_calc = valor_retorno / valor_entrada
        cf3.markdown(f"<br><b>Odd: {odd_calc:.3f}</b>", unsafe_allow_html=True)

        st.caption("⚽ JOGO")
        cd1, cd2 = st.columns(2)
        liga_sel = cd1.selectbox("Liga", LIGAS_COMUNS)
        jogo_txt = cd2.text_input("Jogo", placeholder="Ex: Fla x Vasco")
        
        cm1, cm2 = st.columns(2)
        data_sel = cm1.date_input("Data", date.today())
        mercado_sel = cm2.selectbox("Mercado", MERCADOS_COMUNS)
        obs_txt = st.text_input("Obs")

        if st.form_submit_button("💾 Salvar Aposta"):
            if valor_entrada > 0 and jogo_txt:
                salvar_registro([
                    data_sel.strftime("%d/%m/%Y"), liga_sel, jogo_txt, mercado_sel,
                    valor_entrada, valor_retorno, f"{odd_calc:.3f}",
                    "Pendente", 0.0, obs_txt
                ])
            else:
                st.warning("Preencha dados obrigatórios.")

# --- LISTA DE CARDS ---
st.subheader("📋 Minhas Apostas")

if not df.empty:
    tab_pend, tab_hist, tab_graf = st.tabs(["⏳ Pendentes", "🗂️ Histórico", "📈 Gráfico"])
    
    # ABA PENDENTES (CARDS COLORIDOS E LADO A LADO)
    with tab_pend:
        df_pendentes = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        
        if df_pendentes.empty:
            st.info("Tudo resolvido! Nenhuma pendência.")
        
        for index, row in df_pendentes.iterrows():
            with st.container(border=True):
                # Cabeçalho
                col_topo1, col_topo2 = st.columns([3, 1])
                col_topo1.markdown(f"**⚽ {row['Jogo']}**")
                col_topo1.caption(f"{row['Data']} • {row['Mercado']}")
                col_topo2.markdown(f"**R$ {row['Valor_Entrada']}**")
                col_topo2.caption(f"
