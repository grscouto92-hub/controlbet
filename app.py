import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import time
from streamlit_option_menu import option_menu

# --- Configuração da Página ---
st.set_page_config(page_title="ControlBET", layout="wide", page_icon="⚽")

# --- CSS VISUAL (AJUSTE DE TOPO) ---
st.markdown("""
<style>
    /* Empurra o conteúdo para baixo para não ficar atrás do menu */
    .block-container {
        padding-top: 4rem;
        padding-bottom: 5rem;
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
            
            # Filtra pelo usuário
            df_user = df[df['Usuario'] == usuario_ativo].copy()
            
            # Cria um índice original para sabermos qual linha atualizar depois
            # (Isso ajuda a identificar a aposta dentro da lista filtrada)
            df_user['Index_Original'] = df_user.index
            
            return df_user
                
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
        
        # Remove as linhas antigas desse usuário
        if 'Usuario' in todos_dados.columns:
            todos_dados = todos_dados[todos_dados['Usuario'] != usuario_ativo]
        
        # Remove a coluna auxiliar se existir antes de salvar
        if 'Index_Original' in df_usuario.columns:
            df_usuario = df_usuario.drop(columns=['Index_Original'])
            
        # Junta os dados de outros usuários com os dados atualizados deste usuário
        df_final = pd.concat([todos_dados, df_usuario], ignore_index=True)
        
        sheet.clear()
        sheet.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        return True
    return False

# --- Inicialização de Sessão ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = ""
    
# Controle de Edição
if 'edit_mode' not in st.session_state:
    st.session_state['edit_mode'] = False
    st.session_state['edit_index'] = None

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
                    else:
                        st.error("Usuário ou senha incorretos")
                else:
                    st.error("Erro no cadastro ou planilha vazia")
    
    with tab2:
        with st.form("new"):
            nu = st.text_input("Novo Usuário")
            np = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Criar Conta", type="primary", use_container_width=True):
                if nu and np:
                    ok, msg = criar_novo_usuario(nu, np)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("Preencha todos os campos")
    st.stop()

# =========================================================
# ÁREA LOGADA
# =========================================================
usuario = st.session_state['usuario_atual']

with st.sidebar:
    st.markdown(f"**Usuário:** {usuario}")
    if st.button("Sair (Logout)"):
        st.session_state['logado'] = False
        st.rerun()

# --- MENU HORIZONTAL ---
selected = option_menu(
    menu_title=None,
    options=["Registrar", "Apostas", "Relatórios"],
    icons=["pencil-square", "list-check", "graph-up-arrow"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "icon": {"color": "#ff4b4b", "font-size": "18px"}, 
        "nav-link": {"font-size": "15px", "text-align": "center", "margin":"5px", "--hover-color": "#cccccc"},
        "nav-link-selected": {"background-color": "#ff4b4b"},
    }
)

# --- ABA 1: REGISTRAR ---
if selected == "Registrar":
    # Reseta o modo de edição se trocar de aba
    st.session_state['edit_mode'] = False
    
    st.subheader("📝 Registrar Entrada")
    
    c1, c2 = st.columns([1, 2])
    with c1: data_aposta = st.date_input("Data", date.today())
    with c2: evento = st.text_input("Evento (Ex: Fla x Flu)")
    
    mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL)
    
    c3, c4, c5 = st.columns(3)
    with c3: stake = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
    with c4: retorno = st.number_input("Retorno (R$)", min_value=0.0, step=10.0)
    with c5:
        if stake > 0 and retorno > 0:
            st.metric("Odd", f"{retorno/stake:.2f}")
        else:
            st.write("Odd: 0.00")

    resultado = st.selectbox("Resultado", ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"])
    
    if st.button("💾 Salvar Aposta", type="primary", use_container_width=True):
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
                st.success("Salvo com sucesso!")
                time.sleep(1)
                st.rerun()
        else:
            st.error("Verifique os valores e o nome do evento.")

# --- ABA 2: APOSTAS (LISTA E EDIÇÃO) ---
elif selected == "Apostas":
    st.subheader("🗂️ Gerenciar Apostas")
    df = carregar_apostas(usuario)
    
    if df.empty:
        st.info("Nenhuma aposta encontrada.")
    else:
        # Se NÃO estiver editando, mostra a lista para escolher
        if not st.session_state['edit_mode']:
            # Cria uma coluna bonita para o Selectbox
            df['Label'] = df['Data'].astype(str) + " | " + df['Time/Evento'] + " | " + df['Resultado']
            
            # Selectbox para escolher qual editar
            escolha = st.selectbox("🔍 Selecione a aposta para editar:", df['Label'].tolist(), index=None, placeholder="Clique aqui para buscar...")
            
            if escolha:
                # Pega o índice real da aposta escolhida
                index_selecionado = df[df['Label'] == escolha].index[0]
                st.session_state['edit_mode'] = True
                st.session_state['edit_index'] = index_selecionado
                st.rerun()
            
            st.divider()
            st.caption("Visão Geral:")
            # Mostra a tabela apenas para visualização rápida
            st.dataframe(df.drop(columns=['Label', 'Index_Original'], errors='ignore'), hide_index=True, use_container_width=True)

        # Se ESTIVER editando, mostra o formulário (parecido com o registrar)
        else:
            idx = st.session_state['edit_index']
            linha_atual = df.loc[idx]
            
            st.markdown(f"**Editando:** {linha_atual['Time/Evento']}")
            
            # Formulário de Edição
            with st.container(border=True):
                # Tenta converter a data string para objeto data
                try:
                    data_padrao = datetime.strptime(linha_atual['Data'], '%Y-%m-%d').date()
                except:
                    data_padrao = date.today()

                col_e1, col_e2 = st.columns([1, 2])
                with col_e1: nova_data = st.date_input("Data", data_padrao)
                with col_e2: novo_evento = st.text_input("Evento", linha_atual['Time/Evento'])
                
                # Tenta achar o index do mercado na lista, se não achar usa o primeiro
                try:
                    idx_mercado = MERCADOS_FUTEBOL.index(linha_atual['Mercado'])
                except:
                    idx_mercado = 0
                novo_mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL, index=idx_mercado)
                
                col_e3, col_e4 = st.columns(2)
                with col_e3: novo_stake = st.number_input("Valor (Stake)", min_value=0.0, value=float(linha_atual['Stake']), step=10.0)
                with col_e4: novo_retorno = st.number_input("Retorno Potencial", min_value=0.0, value=float(linha_atual['Retorno_Potencial']), step=10.0)
                
                # Resultado atual
                opcoes_res = ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"]
                try:
                    idx_res = opcoes_res.index(linha_atual['Resultado'])
                except:
                    idx_res = 0
                novo_resultado = st.selectbox("Resultado", opcoes_res, index=idx_res)

                # Botões de Ação
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("⬅️ Voltar", use_container_width=True):
                        st.session_state['edit_mode'] = False
                        st.session_state['edit_index'] = None
                        st.rerun()
                
                with col_b2:
                    if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        # Calcula novo lucro
                        novo_lucro = 0.0
                        if novo_resultado == "Green (Venceu)": novo_lucro = novo_retorno - novo_stake
                        elif novo_resultado == "Red (Perdeu)": novo_lucro = -novo_stake
                        
                        # Atualiza o DataFrame na memória
                        df.at[idx, 'Data'] = str(nova_data)
                        df.at[idx, 'Time/Evento'] = novo_evento
                        df.at[idx, 'Mercado'] = novo_mercado
                        df.at[idx, 'Stake'] = novo_stake
                        df.at[idx, 'Retorno_Potencial'] = novo_retorno
                        df.at[idx, 'Odd'] = round(novo_retorno/novo_stake, 2) if novo_stake > 0 else 0
                        df.at[idx, 'Resultado'] = novo_resultado
                        df.at[idx, 'Lucro/Prejuizo'] = novo_lucro
                        
                        # Remove colunas auxiliares antes de salvar
                        if 'Label' in df.columns: df = df.drop(columns=['Label'])
                        
                        # Salva no Google Sheets
                        if atualizar_planilha_usuario(df, usuario):
                            st.success("Aposta atualizada!")
                            st.session_state['edit_mode'] = False
                            st.session_state['edit_index'] = None
                            time.sleep(1)
                            st.rerun()

# --- ABA 3: RELATÓRIOS ---
elif selected == "Relatórios":
    # Reseta o modo de edição se trocar de aba
    st.session_state['edit_mode'] = False

    st.subheader("📊 Performance")
    df = carregar_apostas(usuario)
    
    if not df.empty:
        lucro = df["Lucro/Prejuizo"].sum()
        roi = (lucro / df["Stake"].sum()) * 100 if df["Stake"].sum() > 0 else 0
        
        c1, c2 = st.columns(2)
        c1.metric("Lucro", f"R$ {lucro:.2f}")
        c2.metric("ROI", f"{roi:.2f}%")
        
        df['Acumulado'] = df['Lucro/Prejuizo'].cumsum()
        st.plotly_chart(px.line(df, y='Acumulado', title="Evolução da Banca"), use_container_width=True)
        st.plotly_chart(px.pie(df, names='Mercado', values='Stake', title="Distribuição por Mercado"), use_container_width=True)
    else:
        st.info("Registre apostas para ver os gráficos.")
