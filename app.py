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

# --- CSS VISUAL (RESPONSIVO PARA CELULAR) ---
st.markdown("""
<style>
    /* Ajuste para o conteúdo não ficar escondido atrás do menu */
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 5rem;
    }

    /* CSS RESPONSIVO: Ajustes específicos para Celular (telas < 640px) */
    @media (max-width: 640px) {
        /* Diminui a fonte dos botões do menu */
        .nav-link {
            font-size: 12px !important;
            padding: 8px 6px !important; 
            margin: 0px !important;
        }
        
        /* Diminui o ícone */
        .bi {
            font-size: 14px !important;
            margin-right: 2px !important;
        }

        /* Ajuste do container para usar 100% da largura no celular */
        div[data-testid="stVerticalBlock"] > div {
            width: 100% !important;
        }
    }
    
    /* Melhora visual dos Cards de aposta */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
            
            df_user = df[df['Usuario'] == usuario_ativo].copy()
            try:
                df_user = df_user.sort_index(ascending=False)
            except: pass
            
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
        if 'Usuario' in todos_dados.columns:
            todos_dados = todos_dados[todos_dados['Usuario'] != usuario_ativo]
        
        df_final = pd.concat([todos_dados, df_usuario], ignore_index=True)
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
                    else: st.error("Usuário ou senha incorretos")
                else: st.error("Erro no cadastro")
    with tab2:
        with st.form("new"):
            nu = st.text_input("Novo Usuário")
            np = st.text_input("Senha", type="password")
            if st.form_submit_button("Criar Conta", type="primary", use_container_width=True):
                if nu and np:
                    ok, msg = criar_novo_usuario(nu, np)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else: st.error("Preencha todos os campos")
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

# --- MENU (ÍCONES BRANCOS QUANDO SELECIONADO) ---
selected = option_menu(
    menu_title=None,
    options=["Novo", "Apostas", "Dash"], 
    icons=["plus-circle", "list-check", "graph-up-arrow"], 
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        
        # TRUQUE AQUI: Removi a cor fixa ("color": "red") do ícone.
        # Agora ele obedece a cor do texto:
        # - Se selecionado: Texto Branco -> Ícone Branco
        # - Não selecionado: Texto Cinza -> Ícone Cinza
        "icon": {"font-size": "16px"}, 
        
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px 2px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#ff4b4b"},
    }
)

# --- ABA 1: NOVO (REGISTRAR) ---
if selected == "Novo":
    st.session_state['edit_mode'] = False
    st.subheader("📝 Novo Registro")
    c1, c2 = st.columns([1, 2])
    with c1: data_aposta = st.date_input("Data", date.today())
    with c2: evento = st.text_input("Evento (Ex: Fla x Flu)")
    mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL)
    c3, c4, c5 = st.columns(3)
    with c3: stake = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
    with c4: retorno = st.number_input("Retorno (R$)", min_value=0.0, step=10.0)
    with c5:
        if stake > 0 and retorno > 0: st.metric("Odd", f"{retorno/stake:.2f}")
        else: st.write("Odd: 0.00")
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
                st.success("Salvo!")
                time.sleep(1)
                st.rerun()
        else: st.error("Verifique os valores.")

# --- APOSTAS (LISTA VISUAL) ---
elif selected == "Apostas":
    st.subheader("🗂️ Histórico")
    df = carregar_apostas(usuario)
    
    if df.empty:
        st.info("Nenhuma aposta encontrada.")
    else:
        # === MODO LISTA VISUAL (FEED) ===
        if not st.session_state['edit_mode']:
            st.caption("Toque em ✏️ para editar.")
            
            for index, row in df.iterrows():
                res = row['Resultado']
                icone = "⏳"
                if "Green" in res: icone = "✅"
                elif "Red" in res: icone = "❌"
                elif "Reembolso" in res: icone = "🔄"

                with st.container(border=True):
                    col_info, col_btn = st.columns([5, 1])
                    
                    with col_info:
                        st.markdown(f"**{row['Time/Evento']}**")
                        st.markdown(f"<small>{row['Data']} | {row['Mercado']}</small>", unsafe_allow_html=True)
                        
                        if "Green" in res:
                            st.markdown(f":green[**+ R$ {row['Lucro/Prejuizo']:.2f}**] {icone}")
                        elif "Red" in res:
                            st.markdown(f":red[**R$ {row['Lucro/Prejuizo']:.2f}**] {icone}")
                        else:
                            st.markdown(f"**{res}** {icone}")

                    with col_btn:
                        st.write("") 
                        if st.button("✏️", key=f"btn_edit_{index}"):
                            st.session_state['edit_mode'] = True
                            st.session_state['edit_index'] = index
                            st.rerun()

        # === MODO EDIÇÃO ===
        else:
            idx = st.session_state['edit_index']
            if idx not in df.index:
                st.session_state['edit_mode'] = False
                st.rerun()

            linha_atual = df.loc[idx]
            st.markdown(f"**Editando:** {linha_atual['Time/Evento']}")
            
            with st.container(border=True):
                try: data_padrao = datetime.strptime(linha_atual['Data'], '%Y-%m-%d').date()
                except: data_padrao = date.today()

                col_e1, col_e2 = st.columns([1, 2])
                with col_e1: nova_data = st.date_input("Data", data_padrao)
                with col_e2: novo_evento = st.text_input("Evento", linha_atual['Time/Evento'])
                
                try: idx_mercado = MERCADOS_FUTEBOL.index(linha_atual['Mercado'])
                except: idx_mercado = 0
                novo_mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL, index=idx_mercado)
                
                col_e3, col_e4 = st.columns(2)
                with col_e3: novo_stake = st.number_input("Stake", min_value=0.0, value=float(linha_atual['Stake']), step=10.0)
                with col_e4: novo_retorno = st.number_input("Retorno", min_value=0.0, value=float(linha_atual['Retorno_Potencial']), step=10.0)
                
                opcoes_res = ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"]
                try: idx_res = opcoes_res.index(linha_atual['Resultado'])
                except: idx_res = 0
                novo_resultado = st.selectbox("Resultado", opcoes_res, index=idx_res)

                c_b1, c_b2 = st.columns(2)
                with c_b1:
                    if st.button("⬅️ Voltar", use_container_width=True):
                        st.session_state['edit_mode'] = False
                        st.session_state['edit_index'] = None
                        st.rerun()
                
                with c_b2:
                    if st.button("💾 Salvar", type="primary", use_container_width=True):
                        novo_lucro = 0.0
                        if novo_resultado == "Green (Venceu)": novo_lucro = novo_retorno - novo_stake
                        elif novo_resultado == "Red (Perdeu)": novo_lucro = -novo_stake
                        
                        df.at[idx, 'Data'] = str(nova_data)
                        df.at[idx, 'Time/Evento'] = novo_evento
                        df.at[idx, 'Mercado'] = novo_mercado
                        df.at[idx, 'Stake'] = novo_stake
                        df.at[idx, 'Retorno_Potencial'] = novo_retorno
                        df.at[idx, 'Odd'] = round(novo_retorno/novo_stake, 2) if novo_stake > 0 else 0
                        df.at[idx, 'Resultado'] = novo_resultado
                        df.at[idx, 'Lucro/Prejuizo'] = novo_lucro
                        
                        if atualizar_planilha_usuario(df, usuario):
                            st.success("Atualizado!")
                            st.session_state['edit_mode'] = False
                            st.session_state['edit_index'] = None
                            time.sleep(1)
                            st.rerun()

# --- RELATÓRIOS ---
elif selected == "Dash":
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
    else: st.info("Sem dados para gráficos.")

