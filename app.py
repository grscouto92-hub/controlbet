import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Pro", page_icon="🦁", layout="centered")

# --- CSS ULTRA PRO (Dark Mode & Botões Horizontais) ---
st.markdown("""
<style>
    /* Fundo escuro e fontes */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0b0e11;
        font-family: 'Inter', sans-serif;
    }

    /* Container Principal do Card */
    .card-bet {
        background-color: #1e2329;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 12px;
        border: 1px solid #2b3139;
    }

    /* Badges Superiores */
    .badge-container { display: flex; gap: 6px; margin-bottom: 10px; }
    .badge-item {
        font-size: 10px;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .badge-simples { background-color: #2b3139; color: #929aa5; }
    .badge-aovivo { background-color: #00c087; color: #ffffff; }

    /* Títulos */
    .jogo-titulo { font-size: 19px; font-weight: 700; color: #ffffff; margin-bottom: 2px; }
    .mercado-sub { font-size: 14px; color: #929aa5; margin-bottom: 16px; }

    /* Caixa de Valores Branca (Estilo App) */
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

    /* BOTÕES LADO A LADO - Forçando o Streamlit */
    div[data-testid="stHorizontalBlock"] {
        gap: 8px !important;
    }

    button {
        height: 42px !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 13px !important;
    }

    /* Customização de Cores dos Botões via Ordem */
    /* WIN */
    div[data-testid="stHorizontalBlock"] div:nth-child(1) button {
        background-color: #0ecb81 !important; color: white !important;
    }
    /* LOSS */
    div[data-testid="stHorizontalBlock"] div:nth-child(2) button {
        background-color: #f6465d !important; color: white !important;
    }
    /* NULA */
    div[data-testid="stHorizontalBlock"] div:nth-child(3) button {
        background-color: #474d57 !important; color: white !important;
    }
    /* DELETE */
    div[data-testid="stHorizontalBlock"] div:nth-child(4) button {
        background-color: transparent !important; color: #929aa5 !important; border: 1px solid #474d57 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS (Conectando ao Sheets) ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except: return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet: return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def atualizar_status(indice_df, resultado, lucro):
    sheet = conectar_gsheets()
    if sheet:
        linha = int(indice_df) + 2
        sheet.update_cell(linha, 8, resultado)
        sheet.update_cell(linha, 9, float(lucro))
        st.cache_data.clear()
        st.rerun()

def deletar_registro(indice_df):
    sheet = conectar_gsheets()
    if sheet:
        sheet.delete_rows(int(indice_df) + 2)
        st.cache_data.clear()
        st.rerun()

# --- INTERFACE PRINCIPAL ---
st.markdown("<h2 style='color:white; margin-bottom:20px;'>Apostas 🦁</h2>", unsafe_allow_html=True)

df = carregar_dados()

if not df.empty:
    tab_ativo, tab_historico = st.tabs(["⏳ Ativo", "🗂️ Histórico"])

    with tab_ativo:
        df_pend = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        
        if df_pend.empty:
            st.info("Nenhuma aposta aberta.")
        
        for index, row in df_pend.iterrows():
            # Card Visual
            st.markdown(f"""
            <div class="card-bet">
                <div class="badge-container">
                    <div class="badge-item badge-simples">SIMPLES</div>
                    <div class="badge-item badge-aovivo">AO VIVO</div>
                </div>
                <div class="jogo-titulo">{row['Jogo']}</div>
                <div class="mercado-sub">{row['Mercado']}</div>
                <div class="info-box">
                    <div class="info-column">
                        <div class="info-label">ODDS</div>
                        <div class="info-value">{row['Odd_Calc']}</div>
                    </div>
                    <div class="info-column">
                        <div class="info-label">APOSTA</div>
                        <div class="info-value">R$ {row['Valor_Entrada']}</div>
                    </div>
                    <div class="info-column">
                        <div class="info-label">PRÊMIO</div>
                        <div class="info-value">R$ {row['Valor_Retorno']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Botões Lado a Lado (Aqui acontece a mágica do CSS acima)
            btn_cols = st.columns([1, 1, 1, 0.4])
            with btn_cols[0]:
                if st.button("WIN", key=f"w{index}"):
                    atualizar_status(index, "Green", row['Valor_Retorno'] - row['Valor_Entrada'])
            with btn_cols[1]:
                if st.button("LOSS", key=f"l{index}"):
                    atualizar_status(index, "Red", -row['Valor_Entrada'])
            with btn_cols[2]:
                if st.button("NULA", key=f"n{index}"):
                    atualizar_status(index, "Reembolso", 0)
            with btn_cols[3]:
                if st.button("🗑️", key=f"d{index}"):
                    deletar_registro(index)

    with tab_historico:
        # Repete o estilo para o histórico mas com o Lucro Real em destaque
        df_hist = df[df['Resultado'] != 'Pendente'].sort_index(ascending=False)
        for index, row in df_hist.iterrows():
            cor_lucro = "#0ecb81" if row['Resultado'] == "Green" else "#f6465d"
            st.markdown(f"""
            <div class="card-bet">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div class="badge-item" style="background-color:{cor_lucro}; color:white;">{row['Resultado']}</div>
                    <div style="color:#929aa5; font-size:11px;">{row['Data']}</div>
                </div>
                <div class="jogo-titulo">{row['Jogo']}</div>
                <div class="mercado-sub">{row['Mercado']}</div>
                <div class="info-box" style="margin-bottom:0px;">
                    <div class="info-column">
                        <div class="info-label">LUCRO REAL</div>
                        <div class="info-value" style="color:{cor_lucro}">R$ {row['Lucro_Real']}</div>
                    </div>
                    <div class="info-column">
                        <div class="info-label">ODD</div>
                        <div class="info-value">{row['Odd_Calc']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Remover do Histórico", key=f"delh{index}", use_container_width=True):
                deletar_registro(index)
            st.markdown("---")

else:
    st.warning("Planilha vazia ou não conectada.")

# --- BARRA LATERAL (Entrada de Dados) ---
with st.sidebar:
    st.title("🦁 Config")
    with st.form("nova_aposta"):
        st.subheader("Nova Entrada")
        f_jogo = st.text_input("Confronto")
        f_liga = st.text_input("Liga")
        f_mercado = st.text_input("Mercado")
        f_entrada = st.number_input("Valor da Aposta", min_value=1.0, value=10.0)
        f_retorno = st.number_input("Retorno Possível", min_value=1.0, value=19.0)
        
        if st.form_submit_button("Lançar Aposta"):
            sheet = conectar_gsheets()
            if sheet:
                odd = f_retorno / f_entrada if f_entrada > 0 else 0
                sheet.append_row([date.today().strftime("%d/%m/%Y"), f_liga, f_jogo, f_mercado, f_entrada, f_retorno, f"{odd:.2f}", "Pendente", 0])
                st.rerun()
