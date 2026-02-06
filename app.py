import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", page_icon="📈", layout="centered")

# --- CSS PRO (Visual Compacto e Botões Horizontais) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    h1 {font-size: 1.8rem !important;}
    h3 {font-size: 1.2rem !important;}

    /* Forçar colunas lado a lado no mobile */
    div[data-testid="column"] {
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }

    /* Estilo dos Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 12px !important;
        margin-bottom: 8px !important;
        background-color: #f9f9f9;
        border-radius: 10px;
    }

    /* Estilo dos Botões */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        height: 2.4em;
        font-size: 0.85rem;
        padding: 0px !important;
    }
    
    /* Botão Link SofaScore */
    a.link-btn {
        text-decoration: none; padding: 10px; color: white !important;
        background-color: #374df5; border-radius: 8px;
        display: block; text-align: center; font-weight: bold; font-size: 14px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES E LISTAS ---
LIGAS_COMUNS = ["Brasileirão A", "Brasileirão B", "Copa do Brasil", "Premier League", "La Liga", "Serie A (ITA)", "Bundesliga", "Champions", "Libertadores", "Sul-Americana", "Outra"]
MERCADOS_COMUNS = ["Match Odds", "Over 1.5", "Over 2.5", "Over 0.5 HT", "Under 2.5", "Ambas Marcam", "Handicap", "Empate Anula"]

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_gsheets():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("⚠️ Sem credenciais configuradas.")
            return None
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet: 
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("Salvo!", icon="💾")
        st.cache_data.clear()
        st.rerun()

def atualizar_status(indice_df, novo_resultado, lucro_calculado):
    sheet = conectar_gsheets()
    if sheet:
        linha = int(indice_df) + 2 
        sheet.update_cell(linha, 8, novo_resultado)
        sheet.update_cell(linha, 9, float(lucro_calculado))
        st.toast(f"{novo_resultado}!", icon="✅")
        st.cache_data.clear()
        st.rerun()

def deletar_registro(indice_df):
    sheet = conectar_gsheets()
    if sheet:
        linha = int(indice_df) + 2
        sheet.delete_rows(linha)
        st.toast("Excluído!", icon="🗑️")
        st.cache_data.clear()
        st.rerun()

# --- APP PRINCIPAL ---
st.title("Gestão Pro 🦁")

df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial
lucro_total = 0.0

# Processamento de Dados
if not df.empty:
    for col in ['Lucro_Real', 'Valor_Entrada', 'Valor_Retorno']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total

# 1. Métricas de Topo
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Banca", f"R$ {saldo_atual:.0f}", delta=f"{lucro_total:.0f}")
roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if not df.empty and df['Valor_Entrada'].sum() > 0 else 0
col_m2.metric("ROI", f"{roi:.1f}%")
resolvidas = df[df['Resultado'].isin(['Green', 'Red'])] if not df.empty else pd.DataFrame()
winrate = (len(resolvidas[resolvidas['Resultado']=='Green']) / len(resolvidas) * 100) if not resolvidas.empty else 0
col_m3.metric("Winrate", f"{winrate:.0f}%")

st.markdown("---")

# 2. Entrada de Dados
c_sofa, c_form = st.columns([1, 2])
with c_sofa:
    st.markdown('<a href="https://www.sofascore.com/pt/" target="_blank" class="link-btn">⚽ SofaScore</a>', unsafe_allow_html=True)

with c_form:
    with st.expander("➕ Nova Aposta", expanded=False):
        with st.form("novo_reg", clear_on_submit=True):
            cl1, cl2 = st.columns([1.5, 1])
            jogo_txt = cl1.text_input("Jogo", placeholder="Time A x Time B")
            liga_sel = cl2.selectbox("Liga", LIGAS_COMUNS)
            
            cv1, cv2 = st.columns(2)
            valor_entrada = cv1.number_input("Entrada R$", value=10.0, step=5.0)
            valor_retorno = cv2.number_input("Retorno R$", value=19.0, step=1.0)
            
            cd1, cd2 = st.columns(2)
            mercado_sel = cd1.selectbox("Mercado", MERCADOS_COMUNS)
            data_sel = cd2.date_input("Data", date.today())
            
            odd = valor_retorno / valor_entrada if valor_entrada > 0 else 0
            st.caption(f"Odd Calculada: {odd:.2f}")

            if st.form_submit_button("Registrar Aposta", use_container_width=True):
                salvar_registro([
                    data_sel.strftime("%d/%m/%Y"), liga_sel, jogo_txt, mercado_sel,
                    valor_entrada, valor_retorno, f"{odd:.2f}",
                    "Pendente", 0.0, ""
                ])

# 3. Listagem em Abas
if not df.empty:
    tab_pend, tab_hist = st.tabs(["⏳ Pendentes", "🗂️ Histórico"])
    
    with tab_pend:
        df_pend = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        if df_pend.empty:
            st.info("Nenhuma aposta pendente.")
        else:
            for index, row in df_pend.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['Jogo']}** | <span style='color:gray'>{row['Mercado']}</span>", unsafe_allow_html=True)
                    st.caption(f"💰 R${row['Valor_Entrada']} → 🎯 R${row['Valor_Retorno']} (Odd: {row['Odd_Calc']})")
                    
                    b1, b2, b3, b4 = st.columns([1, 1, 1, 0.6])
                    with b1:
                        if st.button("WIN", key=f"win_{index}"):
                            atualizar_status(index, "Green", row['Valor_Retorno'] - row['Valor_Entrada'])
                    with b2:
                        if st.button("LOSS", key=f"loss_{index}"):
                            atualizar_status(index, "Red", -row['Valor_Entrada'])
                    with b3:
                        if st.button("NULA", key=f"null_{index}"):
                            atualizar_status(index, "Reembolso", 0.0)
                    with b4:
                        if st.button("🗑️", key=f"del_p_{index}"):
                            deletar_registro(index)

    with tab_hist:
        df_res = df[df['Resultado'] != 'Pendente'].sort_index(ascending=False)
        if df_res.empty:
            st.info("Ainda não há apostas finalizadas.")
        else:
            # Evolução Simples
            df_plot = df_res.sort_index()
            df_plot['Banca_Evol'] = banca_inicial + df_plot['Lucro_Real'].cumsum()
            st.plotly_chart(px.line(df_plot, y='Banca_Evol', height=150), use_container_width=True)

            for index, row in df_res.iterrows():
                cor = "#28a745" if row['Resultado'] == "Green" else "#dc3545" if row['Resultado'] == "Red" else "#6c757d"
                with st.container(border=True):
                    st.markdown(f"**{row['Jogo']}**")
                    ch1, ch2, ch3 = st.columns([1.5, 1, 0.5])
                    with ch1:
                        st.markdown(f"<span style='color:{cor}; font-weight:bold'>{row['Resultado']}: R${row['Lucro_Real']:.2f}</span>", unsafe_allow_html=True)
                        st.caption(f"{row['Data']} | {row['Mercado']}")
                    with ch2:
                        st.caption(f"Odd: {row['Odd_Calc']}")
                        st.caption(f"{row['Liga']}")
                    with ch3:
                        if st.button("🗑️", key=f"del_h_{index}"):
                            deletar_registro(index)
else:
    st.info("Boas-vindas! Registre sua primeira aposta para começar.")
