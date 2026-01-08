import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import time
from streamlit_option_menu import option_menu

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="ControlBET",
    page_icon="⚽",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 3.5rem;
    padding-bottom: 5rem;
}
@media (max-width: 640px) {
    .nav-link { font-size: 12px !important; }
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# MERCADOS
# =========================================================
MERCADOS_FUTEBOL = [
    "Match Odds (1x2) - Casa", "Match Odds (1x2) - Empate", "Match Odds (1x2) - Fora",
    "Over 0.5 Gols", "Under 0.5 Gols", "Over 1.5 Gols", "Under 1.5 Gols",
    "Over 2.5 Gols", "Under 2.5 Gols",
    "Ambas Marcam - Sim", "Ambas Marcam - Não",
    "Empate Anula (DNB)", "Dupla Chance",
    "Handicap Asiático", "Handicap Europeu",
    "Escanteios", "Cartões", "Placar Correto",
    "Múltipla / Combinada", "Outro"
]

# =========================================================
# GOOGLE SHEETS
# =========================================================
def conectar_google_sheets(aba):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open("ControlBET").worksheet(aba)

# =========================================================
# USUÁRIOS
# =========================================================
def carregar_usuarios():
    sheet = conectar_google_sheets("Credenciais")
    return pd.DataFrame(sheet.get_all_records())

def criar_novo_usuario(u, s):
    sheet = conectar_google_sheets("Credenciais")
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty and u in df['Usuario'].astype(str).values:
        return False
    sheet.append_row([u, s])
    return True

# =========================================================
# APOSTAS
# =========================================================
def carregar_apostas(usuario):
    sheet = conectar_google_sheets("Dados")
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)
    if df.empty:
        return df

    df = df[df['Usuario'] == usuario]

    for c in ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    return df.sort_values("Data")

def salvar_aposta(d):
    sheet = conectar_google_sheets("Dados")
    ordem = [
        "Usuario", "Data", "Esporte", "Time/Evento", "Mercado",
        "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"
    ]
    sheet.append_row([str(d[c]) for c in ordem])

def atualizar_planilha(df, usuario):
    sheet = conectar_google_sheets("Dados")
    todos = pd.DataFrame(sheet.get_all_records())
    todos = todos[todos['Usuario'] != usuario]
    df_final = pd.concat([todos, df], ignore_index=True)
    sheet.clear()
    sheet.update([df_final.columns.tolist()] + df_final.values.tolist())

# =========================================================
# SESSÃO
# =========================================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario'] = ""

# =========================================================
# LOGIN
# =========================================================
if not st.session_state['logado']:
    st.title("⚽ ControlBET")

    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])

    with tab1:
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            df = carregar_usuarios()
            if not df[(df['Usuario'] == u) & (df['Senha'] == s)].empty:
                st.session_state['logado'] = True
                st.session_state['usuario'] = u
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

    with tab2:
        nu = st.text_input("Novo Usuário")
        ns = st.text_input("Senha", type="password")
        if st.button("Criar Conta"):
            if criar_novo_usuario(nu, ns):
                st.success("Conta criada!")
            else:
                st.error("Usuário já existe")

    st.stop()

usuario = st.session_state['usuario']

# =========================================================
# MENU
# =========================================================
menu = option_menu(
    None,
    ["Novo", "Apostas", "Dash"],
    icons=["plus-circle", "list", "graph-up"],
    orientation="horizontal"
)

# =========================================================
# NOVA APOSTA
# =========================================================
if menu == "Novo":
    st.subheader("📝 Nova Aposta")

    data = st.date_input("Data", date.today())
    evento = st.text_input("Evento")
    mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL)
    stake = st.number_input("Stake", min_value=0.0)
    retorno = st.number_input("Retorno Potencial", min_value=0.0)
    resultado = st.selectbox("Resultado", ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"])

    if st.button("Salvar"):
        lucro = 0
        if resultado == "Green (Venceu)":
            lucro = retorno - stake
        elif resultado == "Red (Perdeu)":
            lucro = -stake

        salvar_aposta({
            "Usuario": usuario,
            "Data": str(data),
            "Esporte": "Futebol",
            "Time/Evento": evento,
            "Mercado": mercado,
            "Odd": round(retorno / stake, 2) if stake > 0 else 0,
            "Stake": stake,
            "Retorno_Potencial": retorno,
            "Resultado": resultado,
            "Lucro/Prejuizo": lucro
        })
        st.success("Salvo!")
        st.rerun()

# =========================================================
# DASHBOARD PROFISSIONAL
# =========================================================
elif menu == "Dash":
    st.subheader("📊 Dashboard Profissional")

    df = carregar_apostas(usuario)
    if df.empty:
        st.info("Sem dados")
        st.stop()

    with st.expander("🔎 Filtros", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            di = st.date_input("Data Inicial", df['Data'].min().date())
        with c2:
            dfim = st.date_input("Data Final", df['Data'].max().date())
        with c3:
            mercados = st.multiselect("Mercados", df['Mercado'].unique(), default=df['Mercado'].unique())

    df = df[
        (df['Data'].dt.date >= di) &
        (df['Data'].dt.date <= dfim) &
        (df['Mercado'].isin(mercados))
    ]

    total_stake = df['Stake'].sum()
    lucro = df['Lucro/Prejuizo'].sum()
    roi = (lucro / total_stake) * 100 if total_stake > 0 else 0
    winrate = (df['Resultado'].str.contains("Green").sum() / len(df)) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lucro", f"R$ {lucro:.2f}")
    c2.metric("ROI", f"{roi:.2f}%")
    c3.metric("Winrate", f"{winrate:.1f}%")
    c4.metric("Apostas", len(df))

    df['Acumulado'] = df['Lucro/Prejuizo'].cumsum()
    st.plotly_chart(px.line(df, x='Data', y='Acumulado', title="Evolução da Banca"), use_container_width=True)

    lucro_m = df.groupby("Mercado")['Lucro/Prejuizo'].sum().reset_index()
    st.plotly_chart(px.bar(lucro_m, x='Mercado', y='Lucro/Prejuizo', title="Lucro por Mercado"), use_container_width=True)
