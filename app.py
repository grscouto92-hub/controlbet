import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import time
from streamlit_option_menu import option_menu

# --- Configuração da Página ---
st.set_page_config(page_title="ControlBET", layout="wide", page_icon="⚽")

# --- CSS VISUAL (MODO ESCURO/CLARO CORRIGIDO) ---
st.markdown("""
<style>
    /* Ajuste do topo */
    .block-container {
        padding-top: 4rem;
        padding-bottom: 5rem;
    }
    
    /* FORÇA BRUTA NO BOTÃO - COMPATIBILIDADE TOTAL */
    div.stButton > button {
        color: #000000 !important; /* Texto Preto */
        background-color: #ffffff !important; /* Fundo Branco */
        border: 1px solid #cccccc !important; /* Borda Cinza */
        font-weight: bold !important;
    }
    
    /* Garante que o texto interno também seja preto */
    div.stButton > button p {
        color: #000000 !important;
    }
    
    /* Efeito Hover (Passar o mouse) */
    div.stButton > button:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
        background-color: #f0f2f6 !important;
    }
    
    div.stButton > button:hover p {
        color: #ff4b4b !important;
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
        
        try:
            return client.open("ControlBET").worksheet(nome_aba)
        except Exception as e:
            return None
    except Exception as e:
        st.error(f"Erro de conexão geral: {e}")
        return None

# --- Funções de Leitura e Escrita ---

def carregar_usuarios():
    sheet = conectar_google_sheets("Credenciais")
    if sheet:
        return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def criar_novo_usuario(novo_usuario, nova_senha):
    sheet = conectar_google_sheets("Credenciais")
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            # Verifica duplicidade com segurança
            if not df.empty and 'Usuario' in df.columns:
                lista_usuarios = df['Usuario'].astype(str).values
                if str(novo_usuario) in lista_usuarios:
                    return False, "Usuário já existe!"
            
            sheet.append_row([str(novo_usuario), str(nova_senha)])
            return True, "Conta criada com sucesso!"
        except Exception as e:
            return False, f"Erro: {e}"
    return False, "Erro ao conectar"

def carregar_apostas(usuario_ativo):
    """Lê os dados tratando erros de cabeçalho e convertendo números"""
    sheet = conectar_google_sheets("Dados") 
    
    if sheet:
        try:
            dados_brutos = sheet.get_all_values()
            
            if not dados_brutos:
                cols = ["Usuario","Data","Esporte","Time/Evento","Mercado","Odd","Stake","Retorno_Potencial","Resultado","Lucro/Prejuizo"]
                return pd.DataFrame(columns=cols)

            header = dados_brutos[0]
            rows = dados_brutos[1:]
            df = pd.DataFrame(rows, columns=header)
            
            if "Usuario" not in df.columns:
                cols = ["Usuario","Data","Esporte","Time/Evento","Mercado","Odd","Stake","Retorno_Potencial","Resultado","Lucro/Prejuizo"]
                return pd.DataFrame(columns=cols)

            for col in ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            return df[df['Usuario'] == usuario_ativo]
                
        except Exception as e:
            st.error(f"Erro ao processar planilha: {e}")
            return pd.DataFrame()
            
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
        todos_dados = pd.DataFrame(sheet.get_all_records())
        if 'Usuario' in todos_dados.columns:
            todos_dados = todos_dados[todos_dados['Usuario'] != usuario_ativo]
        
        df_final = pd.concat([todos_dados, df_usuario], ignore_index=True)
        sheet.clear()
        sheet.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        return True
    return False

# --- Inicialização de Sessão ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = ""

# =========================================================
# TELA DE LOGIN / CADASTRO
# =========================================================
if not st.session_state['logado']:
    st.title("⚽ ControlBET")
    
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
    
    with tab1:
        with st.form("login"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Entrar", use_container_width=True):
                df = carregar_usuarios()
                if not df.empty and 'Usuario' in df.columns:
                    df['Usuario'] = df['Usuario'].astype(str)
                    df['Senha'] = df['Senha'].astype(str)
                    
                    match = df[(df['Usuario']==u) & (df['Senha']==p)]
                    if not match.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = u
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")
                else:
                    st.error("Erro no cadastro ou planilha vazia")
    
    with tab2:
        with st
