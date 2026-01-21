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
    /* Reduzir espaços em branco no topo e nas laterais */
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Títulos menores */
    h1 {font-size: 1.8rem !important;}
    h3 {font-size: 1.2rem !important;}

    /* FORÇAR COLUNAS LADO A LADO NO MOBILE (O Segredo) */
    div[data-testid="column"] {
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 0 !important; /* Permite encolher sem quebrar linha */
    }

    /* Estilo dos Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 10px !important; /* Menos borda interna */
        margin-bottom: 8px !important; /* Menos espaço entre cards */
        background-color: #ffffff;
    }

    /* Estilo dos Botões de Ação (Menores e mais bonitos) */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        height: 2.5em; /* Botão mais baixo */
        font-size: 0.9rem;
        padding: 0px !important;
    }
    
    /* Botão Link SofaScore */
    a.link-btn {
        text-decoration: none; padding: 10px; color: white !important;
        background-color: #374df5; border-radius: 8px;
        display: block; text-align: center; font-weight: bold; font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES E LISTAS ---
LIGAS_COMUNS = [
    "Brasileirão A", "Brasileirão B", "Copa do Brasil",
    "Premier League", "La Liga", "Serie A (ITA)", "Bundesliga",
    "Champions", "Libertadores", "Sul-Americana", "Outra"
]

MERCADOS_COMUNS = [
    "Match Odds", "Over 1.5", "Over 2.5", "Over 0.5 HT",
    "Under 2.5", "Ambas Marcam", "Handicap", "Empate Anula"
]

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
    if sheet: return pd.DataFrame(sheet.get_all_records())
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
        linha = indice_df + 2 
        sheet.update_cell(linha, 8, novo_resultado)
        sheet.update_cell(linha, 9, lucro_calculado)
        st.toast(f"{novo_resultado}!", icon="✅")
        st.cache_data.clear()
        st.rerun()

# --- APP PRINCIPAL ---
st.title("Gestão Pro 🦁")

# 1. Carregar Dados
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial
lucro_total = 0.0

if not df.empty:
    for col in ['Lucro_Real', 'Valor_Entrada', 'Valor_Retorno']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total

# 2. Métricas Compactas (Topo)
c1, c2, c3 = st.columns(3)
c1.metric("Banca", f"R$ {saldo_atual:.0f}", delta=f"{lucro_total:.0f}")
roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if not df.empty and df['Valor_Entrada'].sum() > 0 else 0
c2.metric("ROI", f"{roi:.1f}%")
resolvidas = df[df['Resultado'].isin(['Green', 'Red'])]
winrate = (len(resolvidas[resolvidas['Resultado']=='Green']) / len(resolvidas) * 100) if not resolvidas.empty else 0
c3.metric("Winrate", f"{winrate:.0f}%")

st.markdown("---")

# 3. Botão SofaScore e Formulário
c_sofa, c_form = st.columns([1, 2])
with c_sofa:
    st.markdown('<a href="https://www.sofascore.com/pt/" target="_blank" class="link-btn">⚽ SofaScore</a>', unsafe_allow_html=True)

with c_form:
    with st.expander("➕ Nova Aposta", expanded=False):
        with st.form("novo_reg"):
            # Linha 1: Jogo e Liga
            cl1, cl2 = st.columns([1.5, 1])
            jogo_txt = cl1.text_input("Jogo", placeholder="Fla x Vasco")
            liga_sel = cl2.selectbox("Liga", LIGAS_COMUNS, label_visibility="collapsed")
            
            # Linha 2: Valores
            cv1, cv2 = st.columns(2)
            valor_entrada = cv1.number_input("Entrada R$", value=20.0, step=5.0)
            valor_retorno = cv2.number_input("Retorno R$", value=36.0, step=1.0)
            
            # Linha 3: Detalhes
            cd1, cd2 = st.columns(2)
            mercado_sel = cd1.selectbox("Mercado", MERCADOS_COMUNS)
            data_sel = cd2.date_input("Data", date.today())
            
            # Cálculo Odd
            odd = valor_retorno / valor_entrada if valor_entrada > 0 else 0
            st.caption(f"Odd Calculada: {odd:.2f}")

            if st.form_submit_button("Salvar", use_container_width=True):
                salvar_registro([
                    data_sel.strftime("%d/%m/%Y"), liga_sel, jogo_txt, mercado_sel,
                    valor_entrada, valor_retorno, f"{odd:.2f}",
                    "Pendente", 0.0, ""
                ])

st.markdown("---")

# 4. CARDS DE APOSTAS (Compactos e Horizontais)
if not df.empty:
    tab_pend, tab_hist = st.tabs(["⏳ Pendentes", "🗂️ Histórico"])
    
    # --- ABA PENDENTES ---
    with tab_pend:
        df_pendentes = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        
        if df_pendentes.empty:
            st.info("Sem pendências.")
        
        for index, row in df_pendentes.iterrows():
            with st.container(border=True):
                # LINHA 1: Jogo (Negrito) e Mercado
                st.markdown(f"**{row['Jogo']}** <span style='color:gray; font-size:0.9em'> | {row['Mercado']}</span>", unsafe_allow_html=True)
                
                # LINHA 2: Valores (Entrada, Retorno e Odd)
                st.markdown(
                    f"<div style='display:flex; justify-content:space-between; font-size:0.9em; margin-bottom:5px;'>"
                    f"<span>💰 Ent: <b>{row['Valor_Entrada']}</b></span>"
                    f"<span>🎯 Ret: <b>{row['Valor_Retorno']}</b></span>"
                    f"<span>📈 Odd: <b>{row['Odd_Calc']}</b></span>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
                
                # LINHA 3: Botões (Forçados lado a lado)
                b1, b2, b3 = st.columns([1, 1, 1])
                
                # Botão Green (Verde Suave)
                with b1:
                    st.markdown('<style>div.row-widget.stButton > button[kind="secondary"] {background-color: #e8f5e9; border: 1px solid green; color: green;}</style>', unsafe_allow_html=True)
                    if st.button("✅ WIN", key=f"g_{index}"):
                        lucro = row['Valor_Retorno'] - row['Valor_Entrada']
                        atualizar_status(index, "Green", lucro)

                # Botão Red (Vermelho Suave)
                with b2:
                    st.markdown('<style>div.row-widget.stButton > button[kind="secondary"] {background-color: #ffebee; border: 1px solid red; color: red;}</style>', unsafe_allow_html=True)
                    if st.button("❌ LOSS", key=f"r_{index}"):
                        lucro = -row['Valor_Entrada']
                        atualizar_status(index, "Red", lucro)
                
                # Botão Nula (Cinza)
                with b3:
                    if st.button("🔄 NULA", key=f"n_{index}"):
                        atualizar_status(index, "Reembolso", 0.0)

    # --- ABA HISTÓRICO ---
    with tab_hist:
        # Gráfico rápido no topo do histórico
        df_g = df.copy()
        df_g['Saldo'] = banca_inicial + df_g['Lucro_Real'].cumsum()
        st.plotly_chart(px.line(df_g, y='Saldo', height=200), use_container_width=True)
        
        # Lista simples
        st.dataframe(
            df[['Data', 'Jogo', 'Mercado', 'Resultado', 'Lucro_Real']].iloc[::-1],
            use_container_width=True,
            hide_index=True
        )
