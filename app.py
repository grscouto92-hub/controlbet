import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials # <--- BIBLIOTECA NOVA
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", layout="wide", page_icon="⚽")

# --- Lista de Mercados (Futebol) ---
MERCADOS_FUTEBOL = [
    "Match Odds (1x2) - Casa", "Match Odds (1x2) - Empate", "Match Odds (1x2) - Fora",
    "Over 0.5 Gols", "Under 0.5 Gols", "Over 1.5 Gols", "Under 1.5 Gols",
    "Over 2.5 Gols", "Under 2.5 Gols", "Ambas Marcam - Sim", "Ambas Marcam - Não",
    "Empate Anula (DNB)", "Dupla Chance", "Handicap Asiático", "Handicap Europeu",
    "Escanteios (Cantos)", "Cartões", "Placar Correto (CS)", "Múltipla / Combinada", "Outro"
]

# --- Conexão Google Sheets (ATUALIZADA) ---
def conectar_google_sheets(nome_aba):
    """Conecta em uma aba específica da planilha usando google-auth"""
    try:
        # Verifica se as credenciais existem
        if "gcp_service_account" not in st.secrets:
            st.error("ERRO: Credenciais não encontradas. Verifique os 'Secrets' no Streamlit Cloud.")
            return None

        # Configuração das Credenciais (Padrão Novo)
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Carrega o JSON dos secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Cria as credenciais compatíveis com gspread v6
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Tenta abrir a planilha e a aba
        # IMPORTANTE: O nome deve ser IDÊNTICO ao do Google Sheets
        try:
            sheet = client.open("ControlBET").worksheet(nome_aba)
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("ERRO: Planilha 'ControlBET' não encontrada. Verifique o nome ou se compartilhou com o email do robô.")
            return None
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"ERRO: Aba '{nome_aba}' não encontrada dentro da planilha.")
            return None

    except Exception as e:
        st.error(f"Erro desconhecido ao conectar: {e}")
        return None

# --- Funções de Autenticação (Login/Cadastro) ---
def carregar_usuarios():
    sheet = conectar_google_sheets("Credenciais")
    if sheet:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def criar_novo_usuario(novo_usuario, nova_senha):
    sheet = conectar_google_sheets("Credenciais")
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            # Verifica se já existe
            if not df.empty and 'Usuario' in df.columns:
                lista_usuarios = df['Usuario'].astype(str).values
                if novo_usuario in lista_usuarios:
                    return False, "Usuário já existe!"
            
            sheet.append_row([str(novo_usuario), str(nova_senha)])
            return True, "Conta criada com sucesso!"
        except Exception as e:
            return False, f"Erro ao salvar: {e}"
    return False, "Erro de conexão"

# --- Funções de Dados (Apostas) ---
def carregar_apostas(usuario_ativo):
    # Se sua aba chamar Sheet1, mude aqui embaixo
    sheet = conectar_google_sheets("Dados") 
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty: 
            return pd.DataFrame(columns=["Usuario","Data","Esporte","Time/Evento","Mercado","Odd","Stake","Retorno_Potencial","Resultado","Lucro/Prejuizo"])
        
        # Converte números
        colunas_num = ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']
        for col in colunas_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # Filtra pelo usuário
        if 'Usuario' in df.columns:
            return df[df['Usuario'] == usuario_ativo]
            
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

# --- Inicialização da Sessão ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = ""

# =========================================================
# TELA DE LOGIN / CADASTRO
# =========================================================
if not st.session_state['logado']:
    st.title("🔐 Gestão de Banca - Acesso")
    
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
    
    with tab1:
        with st.form("login_form"):
            user_login = st.text_input("Usuário")
            pass_login = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Entrar")
            
            if btn_login:
                df_users = carregar_usuarios()
                if not df_users.empty and 'Usuario' in df_users.columns:
                    # Filtro seguro convertendo tudo para string
                    users_str = df_users['Usuario'].astype(str)
                    pass_str = df_users['Senha'].astype(str)
                    
                    usuario_encontrado = df_users[
                        (users_str == user_login) & (pass_str == pass_login)
                    ]
                    
                    if not usuario_encontrado.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = user_login
                        st.success("Logado com sucesso!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Erro ao ler usuários. Verifique se a aba 'Credenciais' existe e tem as colunas 'Usuario' e 'Senha'.")

    with tab2:
        st.header("Cadastre-se")
        with st.form("signup_form"):
            new_user = st.text_input("Novo Usuário")
            new_pass = st.text_input("Nova Senha", type="password")
            confirm_pass = st.text_input("Confirme a Senha", type="password")
            btn_create = st.form_submit_button("Criar Conta")
            
            if btn_create:
                if new_pass != confirm_pass:
                    st.error("Senhas não conferem!")
                elif new_user == "":
                    st.error("Digite um nome de usuário.")
                else:
                    sucesso, msg = criar_novo_usuario(new_user, new_pass)
                    if sucesso:
                        st.success("Conta criada! Vá para a aba 'Entrar'.")
                    else:
                        st.error(msg)
    
    st.stop()

# =========================================================
# ÁREA LOGADA
# =========================================================
usuario = st.session_state['usuario_atual']

st.sidebar.markdown(f"### 👤 {usuario}")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

st.sidebar.divider()
pagina = st.sidebar.radio("Menu", ["📝 Registrar Aposta", "🗂️ Gerenciar Apostas", "📊 Relatórios"])

if pagina == "📝 Registrar Aposta":
    st.title("📝 Registrar Entrada")
    col1, col2, col3 = st.columns(3)
    with col1:
        data_aposta = st.date_input("Data", date.today())
        st.markdown("**Futebol** ⚽")
    with col2:
        evento = st.text_input("Jogo (Ex: Brasil x Argentina)")
        mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL)
    with col3:
        stake = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
        retorno = st.number_input("Retorno (R$)", min_value=0.0, step=10.0)
        if stake > 0 and retorno > 0:
            st.info(f"Odd: {retorno/stake:.2f}")

    resultado = st.selectbox("Resultado", ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"])
    
    if st.button("✅ Salvar"):
        if stake > 0 and retorno >= stake and evento:
            lucro = 0.0
            if resultado == "Green (Venceu)": lucro = retorno - stake
            elif resultado == "Red (Perdeu)": lucro = -stake
            
            nova = {
                "Usuario": usuario, "Data": str(data_aposta), "Esporte": "Futebol",
                "Time/Evento": evento, "Mercado": mercado, "Odd": round(retorno/stake, 2),
                "Stake": stake, "Retorno_Potencial": retorno, "Resultado": resultado, "Lucro/Prejuizo": lucro
            }
            if salvar_aposta(nova):
                st.success("Registrado!")
                time.sleep(1)
                st.rerun()
        else:
            st.error("Verifique os dados.")

elif pagina == "🗂️ Gerenciar Apostas":
    st.title("🗂️ Gerenciar")
    df = carregar_apostas(usuario)
    if not df.empty:
        df_edit = st.data_editor(
            df, num_rows="dynamic",
            column_config={"Usuario": st.column_config.TextColumn(disabled=True)},
            hide_index=True, use_container_width=True
        )
        if st.button("💾 Salvar"):
            df_edit['Lucro/Prejuizo'] = df_edit.apply(lambda x: x['Retorno_Potencial'] - x['Stake'] if x['Resultado'] == "Green (Venceu)" else (-x['Stake'] if x['Resultado'] == "Red (Perdeu)" else 0), axis=1)
            if atualizar_planilha_usuario(df_edit, usuario):
                st.success("Salvo!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Sem apostas.")

elif pagina == "📊 Relatórios":
    st.title("📊 Dashboard")
    df = carregar_apostas(usuario)
    if not df.empty:
        lucro = df["Lucro/Prejuizo"].sum()
        roi = (lucro / df["Stake"].sum()) * 100 if df["Stake"].sum() > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Lucro", f"R$ {lucro:.2f}")
        c2.metric("ROI", f"{roi:.2f}%")
        c3.metric("Entradas", len(df))
        
        st.markdown("---")
        df['Acumulado'] = df['Lucro/Prejuizo'].cumsum()
        st.plotly_chart(px.line(df, y='Acumulado', title="Evolução"), use_container_width=True)
        st.plotly_chart(px.pie(df, names='Mercado', values='Stake', title="Mercados"), use_container_width=True)

