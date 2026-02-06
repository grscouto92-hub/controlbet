import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Pro", page_icon="🦁", layout="centered")

# --- Inicialização do Estado do "Olhinho" ---
if 'mostrar_saldo' not in st.session_state:
    st.session_state.mostrar_saldo = True

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0b0e11;
        font-family: 'Inter', sans-serif;
        color: white;
    }

    /* Estilo do Topo (Saldo) */
    .saldo-container {
        text-align: center;
        padding: 20px 0;
    }
    .saldo-label { color: #929aa5; font-size: 14px; margin-bottom: 5px; }
    .saldo-valor { color: #ffffff; font-size: 38px; font-weight: 800; margin: 0; }
    
    /* Cards */
    .card-bet {
        background-color: #1e2329;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 12px;
        border: 1px solid #2b3139;
    }

    .info-box {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 12px;
        display: flex;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    .info-column { text-align: left; flex: 1; }
    .info-column:not(:last-child) { border-right: 1px solid #eaecf0; margin-right: 10px; }
    .info-label { font-size: 10px; color: #707a8a; font-weight: 700; margin-bottom: 4px; }
    .info-value { font-size: 15px; color: #1e2329; font-weight: 800; }

    /* Forçar Botões Lado a Lado */
    div[data-testid="stHorizontalBlock"] { gap: 8px !important; }
    button {
        height: 42px !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    /* Cores dos Botões */
    div[data-testid="stHorizontalBlock"] div:nth-child(1) button { background-color: #0ecb81 !important; color: white !important; border: none !important; }
    div[data-testid="stHorizontalBlock"] div:nth-child(2) button { background-color: #f6465d !important; color: white !important; border: none !important; }
    div[data-testid="stHorizontalBlock"] div:nth-child(3) button { background-color: #474d57 !important; color: white !important; border: none !important; }
    div[data-testid="stHorizontalBlock"] div:nth-child(4) button { background-color: transparent !important; color: #929aa5 !important; border: 1px solid #474d57 !important; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds).open("ControlBET").worksheet("Registros")
    except: return None

def carregar_dados():
    sheet = conectar_gsheets()
    return pd.DataFrame(sheet.get_all_records()) if sheet else pd.DataFrame()

# --- LÓGICA FINANCEIRA ---
df = carregar_dados()
banca_inicial = 674.69 # Ajuste seu valor inicial aqui

if not df.empty:
    df['Lucro_Real'] = pd.to_numeric(df['Lucro_Real'], errors='coerce').fillna(0)
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
else:
    lucro_total = 0.0
    saldo_atual = banca_inicial

# --- TOPO: SALDO COM OLHINHO ---
st.markdown('<div class="saldo-container">', unsafe_allow_html=True)
c_saldo, c_eye = st.columns([4, 1])

with c_saldo:
    label = "Saldo da Banca"
    if st.session_state.mostrar_saldo:
        valor_display = f"R$ {saldo_atual:.2f}"
        cor_lucro = "#0ecb81" if lucro_total >= 0 else "#f6465d"
        seta = "▲" if lucro_total >= 0 else "▼"
        sub_label = f"<span style='color:{cor_lucro}; font-weight:bold;'>{seta} R$ {abs(lucro_total):.2f}</span>"
    else:
        valor_display = "R$ ••••••"
        sub_label = "<span style='color:#929aa5;'>Rendimento oculto</span>"
    
    st.markdown(f"<p class='saldo-label'>{label}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='saldo-valor'>{valor_display}</p>", unsafe_allow_html=True)
    st.markdown(sub_label, unsafe_allow_html=True)

with c_eye:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("👁️" if st.session_state.mostrar_saldo else "🙈"):
        st.session_state.mostrar_saldo = not st.session_state.mostrar_saldo
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- CONTEÚDO PRINCIPAL ---
if not df.empty:
    tab_ativo, tab_hist = st.tabs(["⏳ Ativo", "🗂️ Histórico"])

    with tab_ativo:
        df_pend = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        if df_pend.empty:
            st.info("Nenhuma aposta aberta.")
        else:
            for index, row in df_pend.iterrows():
                st.markdown(f"""
                <div class="card-bet">
                    <div class="jogo-titulo">{row['Jogo']}</div>
                    <div class="mercado-sub">{row['Mercado']}</div>
                    <div class="info-box">
                        <div class="info-column"><div class="info-label">ODDS</div><div class="info-value">{row['Odd_Calc']}</div></div>
                        <div class="info-column"><div class="info-label">APOSTA</div><div class="info-value">R$ {row['Valor_Entrada']}</div></div>
                        <div class="info-column"><div class="info-label">PRÊMIO</div><div class="info-value">R$ {row['Valor_Retorno']}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                cols = st.columns([1, 1, 1, 0.4])
                if cols[0].button("WIN", key=f"w{index}"):
                    # Chame sua função atualizar_status aqui
                    pass
                if cols[1].button("LOSS", key=f"l{index}"):
                    # Chame sua função atualizar_status aqui
                    pass
                if cols[2].button("NULA", key=f"n{index}"):
                    # Chame sua função atualizar_status aqui
                    pass
                if cols[3].button("🗑️", key=f"d{index}"):
                    # Chame sua função deletar_registro aqui
                    pass

    with tab_hist:
        df_hist = df[df['Resultado'] != 'Pendente'].sort_index(ascending=False)
        for index, row in df_hist.iterrows():
            cor = "#0ecb81" if row['Resultado'] == "Green" else "#f6465d"
            st.markdown(f"""
            <div class="card-bet">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="background:{cor}; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:800;">{row['Resultado']}</span>
                    <span style="color:#929aa5; font-size:10px;">{row['Data']}</span>
                </div>
                <div class="jogo-titulo" style="font-size:16px;">{row['Jogo']}</div>
                <div style="color:{cor}; font-weight:800; font-size:14px; margin-top:5px;">+ R$ {row['Lucro_Real']}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.warning("Aguardando dados...")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🦁 Nova Aposta")
    with st.form("f_nova"):
        f_j = st.text_input("Jogo")
        f_m = st.text_input("Mercado")
        f_e = st.number_input("Entrada", value=10.0)
        f_r = st.number_input("Retorno", value=19.0)
        if st.form_submit_button("Lançar"):
            # Lógica para salvar no GSheets
            st.rerun()
