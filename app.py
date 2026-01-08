import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import time
from streamlit_option_menu import option_menu

# --- Configuração da Página ---
st.set_page_config(page_title="ControlBET", layout="wide", page_icon="⚽")

# --- CSS VISUAL (MODO ESCURO + CARDS TRANSPARENTES) ---
st.markdown("""
<style>
    /* Espaçamento do Topo */
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 5rem;
    }
    
    /* === ESTILO DOS CARDS DE MÉTRICAS (ODD, LUCRO, ROI) === */
    /* Agora eles imitam o st.container: fundo transparente e borda sutil */
    div[data-testid="stMetric"] {
        background-color: transparent !important; /* Fundo do site (Escuro) */
        border: 1px solid #444444 !important;    /* Borda Cinza Escura (Visível no Dark) */
        padding: 10px !important;
        border-radius: 8px !important;
        color: white !important;                 /* Texto Branco */
    }

    /* Garante que os valores dentro do card sejam legíveis no modo escuro */
    div[data-testid="stMetric"] label {
        color: #e0e0e0 !important; /* Título cinza claro */
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important; /* Valor branco brilhante */
    }

    /* === RESPONSIVO CELULAR === */
    @media (max-width: 640px) {
        .nav-link { font-size: 12px !important; padding: 8px 6px !important; margin: 0px !important; }
        .bi { font-size: 14px !important; margin-right: 2px !important; }
        div[data-testid="stVerticalBlock"] > div { width: 100% !important; }
    }
    
    /* Ajuste fino para os cards de aposta (feed) ficarem harmônicos */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #444444 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Lista de Mercados ---
MERCADOS_FUTEBOL = [
    "Match Odds (1x2) - Casa", "Match Odds (1x2) - Empate", "Match Odds (1x2) - Fora",
    "Over 0.5 Gols", "Under 0.5 Gols", "Over 1.5 Gols", "Under 1.5 Gols",
    "Over 2.5 Gols", "Under 2.5 Gols", "Ambas Marcam - Sim", "Ambas Marcam - Não",
    "Empate Anula (DNB)", "Dupla Chance", "Handicap Asiático", "Handicap Europeu",
    "Escanteios", "Cartões", "Placar Correto", "Múltipla / Combinada", "Outro"
]

# --- Conexão Google Sheets ---
def conectar_google_sheets(nome_aba):
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("ERRO: Credenciais não encontradas nos Secrets.")
            return None
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        try: return client.open("ControlBET").worksheet(nome_aba)
        except: return None
    except: return None

# --- Funções de Dados ---
def carregar_usuarios():
    sheet = conectar_google_sheets("Credenciais")
    if sheet: return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def criar_novo_usuario(novo_usuario, nova_senha):
    sheet = conectar_google_sheets("Credenciais")
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty and 'Usuario' in df.columns:
                if str(novo_usuario) in df['Usuario'].astype(str).values:
                    return False, "Usuário já existe!"
            sheet.append_row([str(novo_usuario), str(nova_senha)])
            return True, "Conta criada!"
        except Exception as e: return False, f"Erro: {e}"
    return False, "Erro ao conectar"

def carregar_apostas(usuario_ativo):
    sheet = conectar_google_sheets("Dados") 
    if sheet:
        try:
            dados_brutos = sheet.get_all_values()
            if not dados_brutos: return pd.DataFrame()
            
            header = dados_brutos[0]
            rows = dados_brutos[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Limpeza e Conversão de Tipos
            cols_num = ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']
            for col in cols_num:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            # Filtra usuário
            if 'Usuario' in df.columns:
                df = df[df['Usuario'] == usuario_ativo].copy()

            # Converte Data
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.date
                
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def salvar_aposta(nova_linha):
    sheet = conectar_google_sheets("Dados")
    if sheet:
        ordem = ["Usuario", "Data", "Esporte", "Time/Evento", "Mercado", "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"]
        linha = [str(nova_linha.get(c, "")) for c in ordem]
        sheet.append_row(linha)
        return True
    return False

def atualizar_planilha_usuario(df_usuario, usuario_ativo):
    sheet = conectar_google_sheets("Dados")
    if sheet:
        todos = pd.DataFrame(sheet.get_all_records())
        if 'Usuario' in todos.columns:
            todos = todos[todos['Usuario'] != usuario_ativo]
        
        # Converte data para string antes de salvar
        if 'Data' in df_usuario.columns:
            df_usuario['Data'] = df_usuario['Data'].astype(str)
            
        df_final = pd.concat([todos, df_usuario], ignore_index=True)
        sheet.clear()
        sheet.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        return True
    return False

# --- Sessão ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = ""
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
    st.session_state['edit_index'] = None

# =========================================================
# LOGIN
# =========================================================
if not st.session_state['logado']:
    st.title("⚽ ControlBET")
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
    with tab1:
        with st.form("login"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                df = carregar_usuarios()
                if not df.empty and 'Usuario' in df.columns:
                    df['Usuario'] = df['Usuario'].astype(str)
                    df['Senha'] = df['Senha'].astype(str)
                    match = df[(df['Usuario']==u) & (df['Senha']==p)]
                    if not match.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = u
                        st.rerun()
                    else: st.error("Dados inválidos")
                else: st.error("Erro no sistema")
    with tab2:
        with st.form("new"):
            nu = st.text_input("Novo Usuário")
            np = st.text_input("Senha", type="password")
            if st.form_submit_button("Criar Conta", type="primary", use_container_width=True):
                if nu and np:
                    ok, msg = criar_novo_usuario(nu, np)
                    if ok: st.success(msg)
