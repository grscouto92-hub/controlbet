import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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

# --- Conexão Google Sheets ---
def conectar_google_sheets(nome_aba):
    """Conecta em uma aba específica da planilha"""
    try:
        # Pega as credenciais da nuvem (Secrets)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            # Tenta abrir a aba. Se não achar a planilha ou aba, retorna erro.
            # IMPORTANTE: O nome da planilha deve ser exato.
            sheet = client.open("Gestão Banca Apostas").worksheet(nome_aba)
            return sheet
        else:
            st.error("Credenciais não encontradas nos Secrets.")
            return None
    except Exception as e:
        st.error(f"Erro ao conectar na aba '{nome_aba}': {e}")
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
            df = pd.DataFrame(sheet.get_all_records())
            # Verifica se já existe (se a tabela não estiver vazia)
            if not df.empty and 'Usuario' in df.columns and novo_usuario in df['Usuario'].astype(str).values:
                return False, "Usuário já existe!"
            
            sheet.append_row([str(novo_usuario), str(nova_senha)])
            return True, "Conta criada com sucesso!"
        except Exception as e:
            return False, f"Erro: {e}"
    return False, "Erro de conexão"

# --- Funções de Dados (Apostas) ---
def carregar_apostas(usuario_ativo):
    # Tente "Página1" (Excel pt-br) ou "Sheet1" (padrão inglês/novo sheets)
    # Se der erro no seu, troque "Página1" por "Sheet1" aqui embaixo
    sheet = conectar_google_sheets("Página1") 
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Se vazio, cria estrutura
        if df.empty: 
            return pd.DataFrame(columns=["Usuario","Data","Esporte","Time/Evento","Mercado","Odd","Stake","Retorno_Potencial","Resultado","Lucro/Prejuizo"])
        
        # Converte números para evitar erros de cálculo
        for col in ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # Filtra pelo usuário logado
        if 'Usuario' in df.columns:
            return df[df['Usuario'] == usuario_ativo]
            
    return pd.DataFrame()

def salvar_aposta(nova_linha):
    sheet = conectar_google_sheets("Página1")
    if sheet:
        # Ordem exata das colunas
        ordem = ["Usuario", "Data", "Esporte", "Time/Evento", "Mercado", "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"]
        linha = [str(nova_linha.get(c, "")) for c in ordem]
        sheet.append_row(linha)
        return True
    return False

def atualizar_planilha_usuario(df_usuario, usuario_ativo):
    sheet = conectar_google_sheets("Página1")
    if sheet:
        todos_dados = pd.DataFrame(sheet.get_all_records())
        # Remove as linhas antigas desse usuário da memória
        if 'Usuario' in todos_dados.columns:
            todos_dados = todos_dados[todos_dados['Usuario'] != usuario_ativo]
        
        # Junta o que restou (outros usuários) com o novo dataframe editado (deste usuário)
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
    
    tab1, tab2 = st.tabs(["Entrar (Login)", "Criar Nova Conta"])
    
    # --- LOGIN ---
    with tab1:
        with st.form("login_form"):
            user_login = st.text_input("Usuário")
            pass_login = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Acessar Sistema")
            
            if btn_login:
                df_users = carregar_usuarios()
                if not df_users.empty and 'Usuario' in df_users.columns:
                    usuario_encontrado = df_users[
                        (df_users['Usuario'].astype(str) == user_login) & 
                        (df_users['Senha'].astype(str) == pass_login)
                    ]
                    if not usuario_encontrado.empty:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = user_login
                        st.success("Login realizado!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.error("Nenhum usuário cadastrado ou erro na planilha de Credenciais.")

    # --- CRIAR CONTA ---
    with tab2:
        st.header("Cadastre-se")
        with st.form("signup_form"):
            new_user = st.text_input("Escolha um Usuário")
            new_pass = st.text_input("Escolha uma Senha", type="password")
            new_pass_confirm = st.text_input("Confirme a Senha", type="password")
            btn_create = st.form_submit_button("Criar Conta")
            
            if btn_create:
                if new_pass != new_pass_confirm:
                    st.error("As senhas não coincidem!")
                elif new_user == "":
                    st.error("O usuário não pode ser vazio.")
                else:
                    sucesso, msg = criar_novo_usuario(new_user, new_pass)
                    if sucesso:
                        st.success(msg + " Agora faça login na aba ao lado.")
                    else:
                        st.error(msg)
    
    st.stop() # Bloqueia o resto do app até logar

# =========================================================
# ÁREA LOGADA (SÓ APARECE DEPOIS DO LOGIN)
# =========================================================

usuario = st.session_state['usuario_atual']

# Barra Lateral
st.sidebar.markdown(f"### 👤 Olá, {usuario}")
if st.sidebar.button("Sair (Logout)"):
    st.session_state['logado'] = False
    st.rerun()

st.sidebar.divider()
pagina = st.sidebar.radio("Navegação:", ["📝 Registrar Aposta", "🗂️ Gerenciar Apostas", "📊 Relatórios"])

# --- PÁGINA 1: REGISTRAR (COMPLETA) ---
if pagina == "📝 Registrar Aposta":
    st.title("📝 Registrar Nova Entrada")
    st.markdown("Preencha os dados. A Odd é calculada automaticamente.")

    # Layout de colunas igual ao original
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_aposta = st.date_input("Data do Jogo", date.today())
        # Esporte fixo
        st.markdown("**Esporte:** Futebol ⚽")
    
    with col2:
        evento = st.text_input("Jogo / Evento (Ex: Brasil x Argentina)")
        mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL)
    
    with col3:
        # Inputs fora do formulário para cálculo dinâmico
        stake = st.number_input("Valor Investido (R$)", min_value=0.0, step=10.0, value=0.0)
        retorno_potencial = st.number_input("Retorno Total (Se ganhar)", min_value=0.0, step=10.0, value=0.0)
        
        # Cálculo Imediato da Odd
        if stake > 0 and retorno_potencial > 0:
            odd_calculada = retorno_potencial / stake
            st.info(f"📊 **Odd Calculada:** {odd_calculada:.2f}")
        else:
            odd_calculada = 0.0
            st.warning("Preencha valor e retorno para ver a Odd.")

    resultado = st.selectbox("Resultado Inicial", ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"])
    
    st.markdown("---")
    
    # Botão de Salvar
    if st.button("✅ Salvar Aposta na Nuvem"):
        # Validações
        if stake <= 0 or retorno_potencial <= 0:
            st.error("Erro: Valores devem ser maiores que zero.")
        elif retorno_potencial < stake:
            st.error("Erro: Retorno menor que o investimento.")
        elif evento == "":
            st.error("Erro: Digite o nome do jogo.")
        else:
            # Lógica de Lucro
            lucro = 0.0
            if resultado == "Green (Venceu)":
                lucro = retorno_potencial - stake
            elif resultado == "Red (Perdeu)":
                lucro = -stake
            
            nova_aposta = {
                "Usuario": usuario, # Vincula ao usuário logado
                "Data": str(data_aposta),
                "Esporte": "Futebol",
                "Time/Evento": evento,
                "Mercado": mercado,
                "Odd": round(odd_calculada, 2),
                "Stake": stake,
                "Retorno_Potencial": retorno_potencial,
                "Resultado": resultado,
                "Lucro/Prejuizo": lucro
            }
            
            if salvar_aposta(nova_aposta):
                st.success("Aposta registrada com sucesso!")
                time.sleep(1.5)
                st.rerun() # Limpa a tela

# --- PÁGINA 2: GERENCIAR ---
elif pagina == "🗂️ Gerenciar Apostas":
    st.title("🗂️ Minhas Apostas")
    df = carregar_apostas(usuario)
    
    if not df.empty:
        # Tabela Editável
        df_editado = st.data_editor(
            df, 
            num_rows="dynamic",
            column_config={
                "Usuario": st.column_config.TextColumn("Dono", disabled=True),
                "Lucro/Prejuizo": st.column_config.NumberColumn("Lucro", disabled=True),
                "Odd": st.column_config.NumberColumn("Odd", disabled=True),
                "Resultado": st.column_config.SelectboxColumn("Resultado", options=["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"]),
                "Mercado": st.column_config.SelectboxColumn("Mercado", options=MERCADOS_FUTEBOL)
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("💾 Salvar Edições"):
            # Recalcula lucros antes de salvar
            def recalcular_linha(row):
                try:
                    s = float(row['Stake'])
                    r = float(row['Retorno_Potencial'])
                    res = row['Resultado']
                    if res == "Green (Venceu)": return r - s
                    elif res == "Red (Perdeu)": return -s
                    return 0.0
                except: return 0.0

            df_editado['Lucro/Prejuizo'] = df_editado.apply(recalcular_linha, axis=1)
            
            if atualizar_planilha_usuario(df_editado, usuario):
                st.success("Planilha Atualizada!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Você ainda não registrou nenhuma aposta.")

# --- PÁGINA 3: RELATÓRIOS ---
elif pagina == "📊 Relatórios":
    st.title(f"📊 Relatórios de Performance - {usuario}")
    df = carregar_apostas(usuario)
    
    if not df.empty:
        # Cálculos de Métricas
        total_apostas = len(df)
        lucro_liquido = df["Lucro/Prejuizo"].sum()
        total_investido = df["Stake"].sum()
        roi = (lucro_liquido / total_investido) * 100 if total_investido > 0 else 0
        
        greens = len(df[df["Resultado"] == "Green (Venceu)"])
        reds = len(df[df["Resultado"] == "Red (Perdeu)"])
        finalizadas = greens + reds
        win_rate = (greens / finalizadas) * 100 if finalizadas > 0 else 0

        # Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lucro Total", f"R$ {lucro_liquido:.2f}", delta_color="normal")
        col2.metric("ROI", f"{roi:.2f}%")
        col3.metric("Taxa de Acerto", f"{win_rate:.1f}%")
        col4.metric("Total Apostas", total_apostas)

        st.markdown("---")

        # Gráfico 1: Evolução
        df['Lucro Acumulado'] = df['Lucro/Prejuizo'].cumsum()
        fig_evolucao = px.line(df, y='Lucro Acumulado', title="Crescimento da Banca", markers=True)
        st.plotly_chart(fig_evolucao, use_container_width=True)

        # Gráficos 2 e 3: Pizza e Barras
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            fig_pizza = px.pie(df, names='Mercado', values='Stake', title='Distribuição por Mercado')
            st.plotly_chart(fig_pizza, use_container_width=True)
        
        with c_graf2:
            cores = {"Green (Venceu)": "green", "Red (Perdeu)": "red", "Pendente": "grey", "Reembolso": "orange"}
            fig_bar = px.bar(df, x='Resultado', y='Stake', title='Volume por Resultado', color='Resultado', color_discrete_map=cores)
            st.plotly_chart(fig_bar, use_container_width=True)
            
    else:
        st.info("Registre algumas apostas para ver seus gráficos!")
