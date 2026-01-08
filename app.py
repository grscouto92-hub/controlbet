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
st.set_page_config(page_title="ControlBET Pro", layout="wide", page_icon="📈")

# --- CSS VISUAL PROFISSIONAL ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    
    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
        padding: 15px !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label { color: #aaaaaa !important; font-size: 0.9rem !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 600; }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0e1117;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #262730;
        border-bottom: 2px solid #ff4b4b;
    }
    
    /* Card Styles for History */
    .bet-card {
        background-color: #151515;
        border-left: 5px solid #444;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- Lista de Mercados ---
MERCADOS_FUTEBOL = [
    "Match Odds (1x2)", "Over/Under Gols", "BTTS (Ambas Marcam)",
    "Handicap Asiático", "Handicap Europeu", "Empate Anula (DNB)",
    "Dupla Chance", "Cantos (Escanteios)", "Cartões", 
    "Placar Correto", "Jogador (Prop)", "Múltipla", "Outro"
]

# --- Conexão Google Sheets (COM CACHE) ---
def conectar_google_sheets(nome_aba):
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("ERRO CRÍTICO: Credenciais não encontradas nos Secrets.")
            return None
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        try: return client.open("ControlBET").worksheet(nome_aba)
        except: return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# --- Funções de Dados ---

# Cache para evitar ler a planilha a cada segundo (TTL de 30 segundos)
@st.cache_data(ttl=30)
def carregar_dados_usuario(usuario_ativo):
    sheet = conectar_google_sheets("Dados") 
    if sheet:
        try:
            dados_brutos = sheet.get_all_values()
            if not dados_brutos: return pd.DataFrame()
            
            header = dados_brutos[0]
            rows = dados_brutos[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Filtra usuário
            if 'Usuario' in df.columns:
                df = df[df['Usuario'] == usuario_ativo].copy()
            
            # Garante colunas numéricas
            cols_num = ['Odd', 'Stake', 'Retorno_Potencial', 'Lucro/Prejuizo']
            for col in cols_num:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            # Tratamento de Data
            if 'Data' in df.columns:
                df['Data_Obj'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=False)
                df['Data'] = df['Data_Obj'].dt.date
                df = df.sort_values(by='Data_Obj', ascending=False)

            # Garante coluna nova se não existir (Retrocompatibilidade)
            if 'Competicao' not in df.columns:
                df['Competicao'] = "Geral"

            return df
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

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

def salvar_aposta(nova_linha):
    sheet = conectar_google_sheets("Dados")
    if sheet:
        # Define a ordem exata das colunas na planilha
        ordem = ["Usuario", "Data", "Esporte", "Competicao", "Time/Evento", "Mercado", "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"]
        linha = [str(nova_linha.get(c, "")) for c in ordem]
        sheet.append_row(linha)
        carregar_dados_usuario.clear() # Limpa o cache para atualizar na hora
        return True
    return False

def atualizar_planilha_usuario(df_usuario, usuario_ativo):
    sheet = conectar_google_sheets("Dados")
    if sheet:
        # Pega todos os dados brutos para não apagar outros usuários
        todos_dados = sheet.get_all_records()
        df_todos = pd.DataFrame(todos_dados)
        
        # Remove os dados antigos DESTE usuário
        if not df_todos.empty and 'Usuario' in df_todos.columns:
            df_outros = df_todos[df_todos['Usuario'] != usuario_ativo]
        else:
            df_outros = pd.DataFrame()
        
        # Prepara o DF do usuário atual para salvar
        df_save = df_usuario.copy()
        if 'Data_Obj' in df_save.columns: df_save = df_save.drop(columns=['Data_Obj'])
        if 'Data' in df_save.columns: df_save['Data'] = df_save['Data'].astype(str)
        
        # Garante a ordem correta das colunas
        colunas_ordem = ["Usuario", "Data", "Esporte", "Competicao", "Time/Evento", "Mercado", "Odd", "Stake", "Retorno_Potencial", "Resultado", "Lucro/Prejuizo"]
        
        # Adiciona colunas faltantes no df_save se houver
        for col in colunas_ordem:
            if col not in df_save.columns: df_save[col] = ""
            
        df_save = df_save[colunas_ordem]
        
        # Concatena
        df_final = pd.concat([df_outros, df_save], ignore_index=True)
        
        # Salva
        sheet.clear()
        sheet.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        carregar_dados_usuario.clear() # Limpa cache
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
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("⚽ ControlBET Pro")
        st.markdown("### Gestão de Banca Profissional")
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Dashboard", type="primary", use_container_width=True):
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
                    else: st.error("Erro no sistema de login")
        with tab2:
            with st.form("new"):
                nu = st.text_input("Novo Usuário")
                np = st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta", use_container_width=True):
                    if nu and np:
                        ok, msg = criar_novo_usuario(nu, np)
                        if ok: st.success(msg)
                        else: st.error(msg)
    st.stop()

# =========================================================
# APP LOGADO
# =========================================================
usuario = st.session_state['usuario_atual']

# --- SIDEBAR ---
with st.sidebar:
    st.title("Painel de Controle")
    st.markdown(f"👤 **Trader:** {usuario}")
    st.divider()
    
    # Gestão de Banca
    st.markdown("💰 **Gestão de Banca**")
    banca_inicial = st.number_input("Banca Inicial (R$)", value=1000.0, step=100.0, help="Valor inicial para cálculo de crescimento")
    
    df_sidebar = carregar_dados_usuario(usuario)
    lucro_sidebar = df_sidebar["Lucro/Prejuizo"].sum() if not df_sidebar.empty else 0.0
    banca_atual = banca_inicial + lucro_sidebar
    
    cor_banca = "green" if lucro_sidebar >= 0 else "red"
    st.markdown(f"""
    <div style="background-color: #262730; padding: 10px; border-radius: 5px; border: 1px solid #444;">
        <small>Banca Atual</small><br>
        <span style="font-size: 20px; font-weight: bold; color: {cor_banca}">R$ {banca_atual:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if st.button("Sair / Logout", use_container_width=True):
        st.session_state['logado'] = False
        st.rerun()

# --- MENU SUPERIOR ---
selected = option_menu(
    menu_title=None,
    options=["Novo Registro", "Diário de Apostas", "Dashboard Pro"], 
    icons=["plus-square", "journals", "graph-up"], 
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px 5px", "--hover-color": "#333333"},
        "nav-link-selected": {"background-color": "#ff4b4b"},
    }
)

# --- ABA 1: NOVO REGISTRO ---
if selected == "Novo Registro":
    st.session_state['edit_mode'] = False
    
    col_main, col_help = st.columns([3, 1])
    with col_main:
        st.subheader("📝 Registrar Entrada")
        
        # Inicializa session state para inputs
        defaults = {
            'n_data': date.today(), 'n_comp': "", 'n_evento': "", 
            'n_mercado': MERCADOS_FUTEBOL[0], 'n_stake': 0.0, 
            'n_retorno': 0.0, 'n_resultado': "Pendente"
        }
        for k, v in defaults.items():
            if k not in st.session_state: st.session_state[k] = v

        def salvar_callback():
            s_stake = st.session_state.n_stake
            s_retorno = st.session_state.n_retorno
            s_resultado = st.session_state.n_resultado
            
            if s_stake > 0 and st.session_state.n_evento:
                lucro = 0.0
                if "Green" in s_resultado: lucro = s_retorno - s_stake
                elif "Red" in s_resultado: lucro = -s_stake
                
                nova = {
                    "Usuario": usuario, 
                    "Data": str(st.session_state.n_data), 
                    "Esporte": "Futebol",
                    "Competicao": st.session_state.n_comp.upper(), 
                    "Time/Evento": st.session_state.n_evento, 
                    "Mercado": st.session_state.n_mercado, 
                    "Odd": round(s_retorno/s_stake, 2) if s_stake > 0 else 0,
                    "Stake": s_stake, 
                    "Retorno_Potencial": s_retorno, 
                    "Resultado": s_resultado, 
                    "Lucro/Prejuizo": lucro
                }
                
                if salvar_aposta(nova):
                    st.session_state['msg_sucesso'] = True
                    # Limpa campos chave
                    st.session_state.n_evento = ""
                    st.session_state.n_stake = 0.0
                    st.session_state.n_retorno = 0.0
                else:
                    st.session_state['msg_erro'] = "Erro ao conectar com Google Sheets."
            else:
                st.session_state['msg_erro'] = "Preencha o Evento e Stake > 0."

        # Formulário
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 1.5, 2])
            c1.date_input("Data", key="n_data")
            c2.text_input("Competição (Ex: Premier League)", key="n_comp")
            c3.text_input("Jogo / Evento (Ex: Man City x Chelsea)", key="n_evento")
            
            c4, c5 = st.columns([2, 1])
            c4.selectbox("Mercado", MERCADOS_FUTEBOL, key="n_mercado")
            c5.selectbox("Resultado Inicial", ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"], key="n_resultado")

            st.markdown("---")
            st.caption("Cálculo de Stake e Odds")
            
            c6, c7, c8 = st.columns(3)
            # AQUI ESTAVA O ERRO ANTERIOR - CORRIGIDO
            stake = c6.number_input("Valor da Aposta", min_value=0.0, step=10.0, format="%.2f", key="n_stake")
            retorno = c7.number_input("Retorno Total", min_value=0.0, step=10.0, format="%.2f", key="n_retorno")
            
            with c8:
                odd_calc = retorno/stake if stake > 0 else 0.0
                st.metric("Odd Calculada", f"{odd_calc:.2f}")

            st.button("💾 Registrar Aposta", type="primary", use_container_width=True, on_click=salvar_callback)

        if st.session_state.get('msg_sucesso'):
            st.success("✅ Aposta registrada!")
            st.session_state['msg_sucesso'] = False
        if st.session_state.get('msg_erro'):
            st.error(f"❌ {st.session_state['msg_erro']}")
            st.session_state['msg_erro'] = None

    with col_help:
        st.info("""
        **Dicas Profissionais:**
        
        📌 **Competição:** Padronize os nomes (ex: use sempre 'Brasileirão A' em vez de 'BR A'). Isso ajuda nos gráficos.
        
        📌 **Stake:** Use stakes fixas ou percentuais da banca para melhor gestão.
        
        📌 **Odd:** O sistema calcula a odd automaticamente baseada no Retorno / Stake.
        """)

# --- ABA 2: DIÁRIO (Listagem e Edição) ---
elif selected == "Diário de Apostas":
    st.subheader("🗂️ Histórico de Entradas")
    df = carregar_dados_usuario(usuario)
    
    if df.empty:
        st.info("Nenhuma aposta registrada. Comece agora!")
    else:
        # Filtro Rápido
        txt_busca = st.text_input("🔍 Buscar por time ou competição", placeholder="Ex: Flamengo")
        if txt_busca:
            df = df[df['Time/Evento'].str.contains(txt_busca, case=False) | df['Competicao'].str.contains(txt_busca, case=False)]

        # MODO VISUALIZAÇÃO
        if not st.session_state['edit_mode']:
            # Cabeçalho da Lista
            col_head1, col_head2, col_head3, col_head4 = st.columns([3, 2, 2, 2])
            col_head1.markdown("**Evento / Competição**")
            col_head2.markdown("**Mercado / Data**")
            col_head3.markdown("**Stake / Odd**")
            col_head4.markdown("**P/L / Status**")
            st.divider()

            for index, row in df.iterrows():
                res = row['Resultado']
                
                # Definição de Cores
                border_color = "#444"
                status_color = "gray"
                if "Green" in res: 
                    border_color = "green"
                    status_color = "#4CAF50"
                elif "Red" in res: 
                    border_color = "red"
                    status_color = "#F44336"
                elif "Reembolso" in res:
                    border_color = "orange"
                    status_color = "#FF9800"

                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                    
                    # Coluna 1: Evento
                    c1.markdown(f"**{row['Time/Evento']}**")
                    c1.caption(f"🏆 {row.get('Competicao', '-')}")
                    
                    # Coluna 2: Mercado
                    c2.text(row['Mercado'])
                    c2.caption(f"📅 {row['Data']}")
                    
                    # Coluna 3: Valores
                    c3.markdown(f"💰 R$ {row['Stake']:.2f}")
                    c3.caption(f"Odd: @{row['Odd']:.2f}")
                    
                    # Coluna 4: Lucro e Ações
                    lucro_val = row['Lucro/Prejuizo']
                    if lucro_val > 0: c4.markdown(f":green[**+R$ {lucro_val:.2f}**]")
                    elif lucro_val < 0: c4.markdown(f":red[**R$ {lucro_val:.2f}**]")
                    else: c4.markdown(f"**R$ {lucro_val:.2f}**")
                    
                    # Botões compactos
                    ca, cb, cc, cd = c4.columns(4)
                    if ca.button("✅", key=f"g_{index}", help="Green"):
                        df.at[index, 'Resultado'] = "Green (Venceu)"
                        df.at[index, 'Lucro/Prejuizo'] = float(row['Retorno_Potencial']) - float(row['Stake'])
                        atualizar_planilha_usuario(df, usuario)
                        st.rerun()
                    if cb.button("❌", key=f"r_{index}", help="Red"):
                        df.at[index, 'Resultado'] = "Red (Perdeu)"
                        df.at[index, 'Lucro/Prejuizo'] = -float(row['Stake'])
                        atualizar_planilha_usuario(df, usuario)
                        st.rerun()
                    if cc.button("✏️", key=f"ed_{index}", help="Editar"):
                        st.session_state['edit_mode'] = True
                        st.session_state['edit_index'] = index
                        st.rerun()
                    if cd.button("🗑️", key=f"dl_{index}", help="Excluir"):
                        df = df.drop(index)
                        atualizar_planilha_usuario(df, usuario)
                        st.rerun()
                    
                    st.markdown(f"<div style='height:1px; background-color:{border_color}; margin-top:5px; margin-bottom:15px; opacity: 0.5'></div>", unsafe_allow_html=True)

        # MODO EDIÇÃO
        else:
            idx = st.session_state['edit_index']
            if idx not in df.index:
                st.session_state['edit_mode'] = False
                st.rerun()
            
            row = df.loc[idx]
            st.markdown(f"### ✏️ Editando: {row['Time/Evento']}")
            
            with st.form("edit_form"):
                try: d_padrao = pd.to_datetime(row['Data']).date()
                except: d_padrao = date.today()

                col1, col2 = st.columns(2)
                n_data = col1.date_input("Data", d_padrao)
                n_comp = col2.text_input("Competição", row.get('Competicao', ''))
                
                col3, col4 = st.columns(2)
                n_evento = col3.text_input("Evento", row['Time/Evento'])
                n_merc = col4.selectbox("Mercado", MERCADOS_FUTEBOL, index=MERCADOS_FUTEBOL.index(row['Mercado']) if row['Mercado'] in MERCADOS_FUTEBOL else 0)

                col5, col6, col7 = st.columns(3)
                n_stake = col5.number_input("Stake", value=float(row['Stake']))
                n_ret = col6.number_input("Retorno Potencial", value=float(row['Retorno_Potencial']))
                
                l_res = ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"]
                try: i_res = l_res.index(row['Resultado'])
                except: i_res = 0
                n_res = col7.selectbox("Resultado", l_res, index=i_res)

                if st.form_submit_button("Atualizar Dados", type="primary"):
                    lucro = 0.0
                    if "Green" in n_res: lucro = n_ret - n_stake
                    elif "Red" in n_res: lucro = -n_stake
                    
                    df.at[idx, 'Data'] = str(n_data)
                    df.at[idx, 'Competicao'] = n_comp.upper()
                    df.at[idx, 'Time/Evento'] = n_evento
                    df.at[idx, 'Mercado'] = n_merc
                    df.at[idx, 'Stake'] = n_stake
                    df.at[idx, 'Retorno_Potencial'] = n_ret
                    df.at[idx, 'Odd'] = round(n_ret/n_stake, 2) if n_stake > 0 else 0
                    df.at[idx, 'Resultado'] = n_res
                    df.at[idx, 'Lucro/Prejuizo'] = lucro
                    
                    atualizar_planilha_usuario(df, usuario)
                    st.success("Atualizado!")
                    st.session_state['edit_mode'] = False
                    time.sleep(1)
                    st.rerun()
            
            if st.button("Cancelar Edição"):
                st.session_state['edit_mode'] = False
                st.rerun()

# --- ABA 3: DASHBOARD PRO ---
elif selected == "Dashboard Pro":
    st.session_state['edit_mode'] = False
    
    df = carregar_dados_usuario(usuario)
    
    if df.empty:
        st.warning("Sem dados suficientes para gerar gráficos.")
    else:
        # --- FILTROS ---
        st.markdown("### 📊 Performance Analytics")
        with st.expander("🔎 Filtros Avançados", expanded=False):
            f1, f2, f3 = st.columns(3)
            d_inicio = f1.date_input("De", date.today() - timedelta(days=30))
            d_fim = f2.date_input("Até", date.today())
            
            competicoes_un = ["Todas"] + list(df['Competicao'].unique())
            f_comp = f3.selectbox("Competição", competicoes_un)
            
            # Aplicando filtros
            mask = (df['Data'] >= d_inicio) & (df['Data'] <= d_fim)
            df_filtered = df.loc[mask]
            
            if f_comp != "Todas":
                df_filtered = df_filtered[df_filtered['Competicao'] == f_comp]
        
        if df_filtered.empty:
            st.info("Nenhum dado encontrado com esses filtros.")
        else:
            # --- KPIs PRINCIPAIS ---
            lucro_periodo = df_filtered["Lucro/Prejuizo"].sum()
            turnover = df_filtered["Stake"].sum()
            roi = (lucro_periodo / turnover * 100) if turnover > 0 else 0.0
            total_bets = len(df_filtered)
            
            df_res = df_filtered[df_filtered['Resultado'].isin(["Green (Venceu)", "Red (Perdeu)"])]
            greens = len(df_res[df_res['Resultado'] == "Green (Venceu)"])
            winrate = (greens / len(df_res) * 100) if len(df_res) > 0 else 0.0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Lucro Líquido", f"R$ {lucro_periodo:.2f}", delta=f"{roi:.2f}% ROI")
            k2.metric("Turnover (Volume)", f"R$ {turnover:.2f}")
            k3.metric("Winrate", f"{winrate:.1f}%", f"{greens} Wins")
            k4.metric("Total Entradas", f"{total_bets}")
            
            st.divider()

            # --- GRÁFICO 1: EVOLUÇÃO DA BANCA ---
            # Ordena por data crescente para acumular
            df_chart = df_filtered.sort_values(by="Data", ascending=True).copy()
            df_chart['Acumulado'] = df_chart['Lucro/Prejuizo'].cumsum()
            
            # Adiciona ponto zero (Opcional, mas bom para visualizar)
            
            fig_evolucao = px.area(
                df_chart, x='Data', y='Acumulado', 
                title="📈 Crescimento da Banca (Acumulado)",
                markers=True,
                color_discrete_sequence=['#00CC96']
            )
            fig_evolucao.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            fig_evolucao.add_hline(y=0, line_dash="dash", line_color="white")
            st.plotly_chart(fig_evolucao, use_container_width=True)
            
            # --- GRÁFICO 2 e 3: ANÁLISE POR SEGMENTO ---
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                # Lucro por Mercado
                df_mercado = df_filtered.groupby("Mercado")["Lucro/Prejuizo"].sum().reset_index()
                df_mercado = df_mercado.sort_values("Lucro/Prejuizo", ascending=False)
                
                fig_merc = px.bar(
                    df_mercado, x="Lucro/Prejuizo", y="Mercado", orientation='h',
                    title="Lucro por Mercado",
                    color="Lucro/Prejuizo",
                    color_continuous_scale=["red", "yellow", "green"]
                )
                fig_merc.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
                st.plotly_chart(fig_merc, use_container_width=True)
                
            with c_chart2:
                # Lucro por Competição (Top 10)
                if 'Competicao' in df_filtered.columns:
                    df_comp = df_filtered.groupby("Competicao")["Lucro/Prejuizo"].sum().reset_index()
                    df_comp = df_comp.sort_values("Lucro/Prejuizo", ascending=False).head(10)
                    
                    fig_comp = px.bar(
                        df_comp, x="Competicao", y="Lucro/Prejuizo",
                        title="Top Performance por Liga",
                        color="Lucro/Prejuizo",
                         color_continuous_scale=["red", "yellow", "green"]
                    )
                    fig_comp.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
                    st.plotly_chart(fig_comp, use_container_width=True)

            # --- GRÁFICO 4: GESTÃO DE RISCO (Scatter) ---
            st.subheader("🎯 Gestão de Risco (Odd vs Stake)")
            df_risk = df_filtered[df_filtered['Stake'] > 0]
            if not df_risk.empty:
                fig_risk = px.scatter(
                    df_risk, x="Odd", y="Stake", color="Resultado",
                    size="Stake", hover_data=["Time/Evento"],
                    color_discrete_map={"Green (Venceu)": "green", "Red (Perdeu)": "red", "Reembolso": "orange", "Pendente": "gray"},
                    title="Dispersão: Onde estão seus Greens e Reds?"
                )
                fig_risk.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
                st.plotly_chart(fig_risk, use_container_width=True)
