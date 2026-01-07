import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca - 4G", layout="wide", page_icon="⚽")

# --- Lista de Mercados ---
MERCADOS_FUTEBOL = [
    "Match Odds (1x2) - Casa", "Match Odds (1x2) - Empate", "Match Odds (1x2) - Fora",
    "Over 0.5 Gols", "Under 0.5 Gols", "Over 1.5 Gols", "Under 1.5 Gols",
    "Over 2.5 Gols", "Under 2.5 Gols", "Ambas Marcam - Sim", "Ambas Marcam - Não",
    "Empate Anula (DNB)", "Dupla Chance", "Handicap Asiático", "Handicap Europeu",
    "Escanteios", "Cartões", "Placar Correto", "Múltipla", "Outro"
]

# --- Conexão com Google Sheets ---
def conectar_google_sheets():
    # Define o escopo de permissão
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Pega as credenciais dos "Segredos" do Streamlit Cloud
    # Se estiver rodando local para teste, você precisará configurar o arquivo .streamlit/secrets.toml
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Abre a planilha pelo nome (Crie uma planilha no Google com este nome EXATO)
    # Ou use .open_by_key('ID_DA_PLANILHA')
    sheet = client.open("Gestão Banca Apostas").sheet1 
    return sheet

def carregar_dados():
    try:
        sheet = conectar_google_sheets()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        # Garante que as colunas numéricas sejam números
        cols_num = ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return pd.DataFrame(columns=["Data", "Esporte", "Time/Evento", "Mercado", "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"])

def salvar_aposta_sheets(nova_linha_dict):
    try:
        sheet = conectar_google_sheets()
        # Converte valores para string/formato aceito pelo Sheets se necessário, 
        # mas gspread lida bem com int/float.
        # A ordem deve bater com a ordem das colunas na planilha se usar append_row sem especificar chaves,
        # mas vamos transformar o dict em lista na ordem correta das colunas
        ordem_colunas = ["Data", "Esporte", "Time/Evento", "Mercado", "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"]
        linha = [str(nova_linha_dict.get(c, "")) for c in ordem_colunas]
        sheet.append_row(linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def atualizar_planilha_inteira(df):
    try:
        sheet = conectar_google_sheets()
        sheet.clear() # Limpa tudo
        # Adiciona cabeçalho e dados
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False

# --- Lógica de Interface (Resumida para o exemplo) ---
# ... (Aqui entra todo o código visual igual ao anterior, mudando apenas as chamadas de salvar) ...

# ----------------------------------------------------------------------------------
# ATENÇÃO: COPIE AQUI O RESTANTE DO CÓDIGO DA VERSÃO ANTERIOR (Sidebar, Páginas),
# MAS ONDE TIVER "carregar_dados()", use a função nova acima.
# ONDE TIVER "salvar_dados()", use "atualizar_planilha_inteira(df_editado)"
# ONDE TIVER "pd.concat...", use "salvar_aposta_sheets(nova_aposta)"
# ----------------------------------------------------------------------------------

# Exemplo rápido da parte de Registrar para você testar:
st.sidebar.header("Menu")
pagina = st.sidebar.radio("Ir para", ["Registrar", "Ver Dados"])

if pagina == "Registrar":
    st.title("Registrar Aposta (Na Nuvem ☁️)")
    with st.form("form"):
        evento = st.text_input("Evento")
        stake = st.number_input("Valor", value=10.0)
        btn = st.form_submit_button("Salvar")
        if btn:
            # Dados simplificados pro exemplo
            aposta = {
                "Data": str(date.today()), "Esporte": "Futebol", "Time/Evento": evento,
                "Mercado": "Match Odds", "Odd": 2.0, "Stake": stake, 
                "Retorno_Potencial": stake*2, "Resultado": "Pendente", "Lucro/Prejuizo": 0.0
            }
            if salvar_aposta_sheets(aposta):
                st.success("Salvo no Google Sheets!")

elif pagina == "Ver Dados":
    st.title("Lendo direto do Google Sheets")
    df = carregar_dados()
    st.dataframe(df)