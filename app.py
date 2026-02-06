import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Pro", page_icon="🦁", layout="centered")

# --- CSS PERSONALIZADO (Dark Mode & Cards Estilo App) ---
st.markdown("""
<style>
    /* Fundo Geral */
    .stApp { background-color: #0e1117; color: white; }
    
    /* Container do Card */
    .card-bet {
        background-color: #161b22;
        border-radius: 15px;
        padding: 20px;
        border: 1px solid #30363d;
        margin-bottom: 15px;
    }

    /* Badge "AO VIVO" ou "SIMPLES" */
    .badge {
        background-color: #00c805;
        color: white;
        padding: 2px 8px;
        border-radius: 5px;
        font-size: 10px;
        font-weight: bold;
        margin-right: 5px;
    }

    /* Texto do Jogo e Mercado */
    .jogo-titulo { font-size: 20px; font-weight: bold; margin-top: 10px; color: #ffffff; }
    .mercado-sub { font-size: 16px; color: #8b949e; margin-bottom: 15px; }

    /* Caixa de Valores (O retângulo interno cinza) */
    .info-box {
        background-color: #f0f2f5;
        border-radius: 10px;
        padding: 12px;
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        color: #1f2328;
    }
    .info-item { text-align: left; }
    .info-label { font-size: 11px; color: #656d76; text-transform: uppercase; font-weight: bold; }
    .info-value { font-size: 15px; font-weight: 800; color: #1f2328; }

    /* Estilização dos Botões Estilo Imagem */
    div.stButton > button {
        border-radius: 8px !important;
        height: 45px !important;
        font-weight: bold !important;
        border: none !important;
    }
    
    /* Botão WIN (Verde) */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
        background-color: #008134 !important; color: white !important;
    }
    /* Botão LOSS (Vermelho) */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background-color: #e82a39 !important; color: white !important;
    }
    /* Botão NULA (Cinza) */
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button {
        background-color: #6e7681 !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS (Conforme os passos anteriores) ---
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

def atualizar_status(indice_df, novo_resultado, lucro_calculado):
    sheet = conectar_gsheets()
    if sheet:
        linha = int(indice_df) + 2
        sheet.update_cell(linha, 8, novo_resultado)
        sheet.update_cell(linha, 9, float(lucro_calculado))
        st.cache_data.clear()
        st.rerun()

def deletar_registro(indice_df):
    sheet = conectar_gsheets()
    if sheet:
        sheet.delete_rows(int(indice_df) + 2)
        st.cache_data.clear()
        st.rerun()

# --- INTERFACE PRINCIPAL ---
df = carregar_dados()
st.title("Apostas 🦁")

if not df.empty:
    tab1, tab2 = st.tabs(["⌛ Ativo", "🗂️ Todos"])

    with tab1:
        df_pend = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        
        for index, row in df_pend.iterrows():
            # Renderização do Card HTML personalizado
            st.markdown(f"""
            <div class="card-bet">
                <div>
                    <span class="badge" style="background-color: #30363d;">✔️ SIMPLES</span>
                    <span class="badge">AO VIVO</span>
                </div>
                <div class="jogo-titulo">{row['Jogo']}</div>
                <div class="mercado-sub">{row['Mercado']}</div>
                <div class="info-box">
                    <div class="info-item">
                        <div class="info-label">ODDS TOTAIS</div>
                        <div class="info-value">{row['Odd_Calc']}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">APOSTA</div>
                        <div class="info-value">{row['Valor_Entrada']} R$</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">PRÊMIO POT.</div>
                        <div class="info-value">{row['Valor_Retorno']} R$</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Botões de Ação (Abaixo do Card)
            c1, c2, c3, c4 = st.columns([1, 1, 1, 0.4])
            with c1:
                if st.button("✔ WIN", key=f"w_{index}"):
                    atualizar_status(index, "Green", row['Valor_Retorno'] - row['Valor_Entrada'])
            with c2:
                if st.button("✖ LOSS", key=f"l_{index}"):
                    atualizar_status(index, "Red", -row['Valor_Entrada'])
            with c3:
                if st.button("NULA", key=f"n_{index}"):
                    atualizar_status(index, "Reembolso", 0.0)
            with c4:
                if st.button("🗑️", key=f"d_{index}"):
                    deletar_registro(index)
            st.markdown("<br>", unsafe_allow_html=True)

    with tab2:
        # Histórico (Estilo similar mas sem botões de resultado)
        df_hist = df[df['Resultado'] != 'Pendente'].sort_index(ascending=False)
        for index, row in df_hist.iterrows():
            cor_res = "#00c805" if row['Resultado'] == "Green" else "#ff4b4b"
            st.markdown(f"""
            <div class="card-bet">
                <div style="display: flex; justify-content: space-between;">
                    <span class="badge" style="background-color: {cor_res}">{row['Resultado']}</span>
                    <span style="color: #8b949e; font-size: 12px;">{row['Data']}</span>
                </div>
                <div class="jogo-titulo">{row['Jogo']}</div>
                <div class="info-box" style="margin-top:15px;">
                    <div class="info-item">
                        <div class="info-label">LUCRO REAL</div>
                        <div class="info-value" style="color: {cor_res}">R$ {row['Lucro_Real']}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">MERCADO</div>
                        <div class="info-value">{row['Mercado']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Excluir Registro", key=f"del_h_{index}", use_container_width=True):
                deletar_registro(index)

else:
    st.info("Nenhuma aposta encontrada.")

# Formulário de Nova Aposta (Expander)
with st.sidebar:
    st.header("Nova Entrada")
    with st.form("add_bet"):
        jogo = st.text_input("Jogo")
        liga = st.selectbox("Liga", ["Brasileirão", "Premier League", "Champions", "Outras"])
        mercado = st.text_input("Mercado (Ex: Over 0.5 HT)")
        entrada = st.number_input("Valor Entrada", value=10.0)
        retorno = st.number_input("Retorno Potencial", value=19.0)
        if st.form_submit_button("Salvar Aposta"):
            from datetime import date
            sheet = conectar_gsheets()
            odd = retorno / entrada if entrada > 0 else 0
            sheet.append_row([date.today().strftime("%d/%m/%Y"), liga, jogo, mercado, entrada, retorno, f"{odd:.2f}", "Pendente", 0.0])
            st.rerun()
