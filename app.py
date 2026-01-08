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

# --- CSS VISUAL (MODO ESCURO + CARDS FLAT + BOTÕES COMPACTOS) ---
st.markdown("""
<style>
    /* Espaçamento do Topo */
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 5rem;
    }
    
    /* === ESTILO DOS CARDS DE MÉTRICAS === */
    div[data-testid="stMetric"] {
        background-color: transparent !important;
        border: 1px solid #444444 !important;
        padding: 10px !important;
        border-radius: 8px !important;
        color: white !important;
    }
    div[data-testid="stMetric"] label { color: #e0e0e0 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #ffffff !important; }

    /* === RESPONSIVO CELULAR === */
    @media (max-width: 640px) {
        .nav-link { font-size: 12px !important; padding: 8px 6px !important; margin: 0px !important; }
        .bi { font-size: 14px !important; margin-right: 2px !important; }
        div[data-testid="stVerticalBlock"] > div { width: 100% !important; }
        
        /* Ajuste para botões de ação caberem na mesma linha no celular */
        div[data-testid="column"] { min-width: 0px !important; }
        button { padding: 0.25rem 0.5rem !important; }
    }
    
    /* Ajuste fino para os cards de aposta */
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
                    else: st.error(msg)
    st.stop()

# =========================================================
# APP LOGADO
# =========================================================
usuario = st.session_state['usuario_atual']

with st.sidebar:
    st.markdown(f"**Trader:** {usuario}")
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

# --- MENU PRINCIPAL (ALTERADO PARA KPI's) ---
selected = option_menu(
    menu_title=None,
    options=["Novo", "Apostas", "KPI's"], 
    icons=["plus-circle", "list-check", "graph-up-arrow"], 
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "transparent"},
        "icon": {"font-size": "16px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px 2px", "--hover-color": "#cccccc"},
        "nav-link-selected": {"background-color": "#ff4b4b"},
    }
)

# --- ABA 1: NOVO (Com limpeza automática de campos) ---
if selected == "Novo":
    st.session_state['edit_mode'] = False
    st.subheader("📝 Registrar")
    
    # 1. Inicializa variáveis no Session State se não existirem
    if 'n_data' not in st.session_state: st.session_state.n_data = date.today()
    if 'n_evento' not in st.session_state: st.session_state.n_evento = ""
    if 'n_mercado' not in st.session_state: st.session_state.n_mercado = MERCADOS_FUTEBOL[0]
    if 'n_stake' not in st.session_state: st.session_state.n_stake = 0.0
    if 'n_retorno' not in st.session_state: st.session_state.n_retorno = 0.0
    if 'n_resultado' not in st.session_state: st.session_state.n_resultado = "Pendente"

    # 2. Construção dos Inputs vinculados às Keys
    c1, c2 = st.columns([1, 2])
    data_aposta = c1.date_input("Data", key="n_data")
    evento = c2.text_input("Evento", key="n_evento")
    
    mercado = st.selectbox("Mercado", MERCADOS_FUTEBOL, key="n_mercado")
    
    c3, c4, c5 = st.columns(3)
    stake = c3.number_input("Stake", min_value=0.0, step=10.0, format="%.2f", key="n_stake")
    retorno = c4.number_input("Retorno", min_value=0.0, step=10.0, format="%.2f", key="n_retorno")
    
    with c5:
        if stake > 0 and retorno > 0: 
            st.metric("Odd", f"{retorno/stake:.2f}")
        else: 
            st.write("Odd: 0.00")
        
    resultado = st.selectbox("Resultado", ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"], key="n_resultado")
    
    # 3. Lógica do Botão Salvar
    if st.button("💾 Salvar", type="primary", use_container_width=True):
        if stake > 0 and retorno >= stake and evento:
            lucro = 0.0
            if "Green" in resultado: lucro = retorno - stake
            elif "Red" in resultado: lucro = -stake
            
            nova = {
                "Usuario": usuario, 
                "Data": str(data_aposta), 
                "Esporte": "Futebol",
                "Time/Evento": evento, 
                "Mercado": mercado, 
                "Odd": round(retorno/stake, 2) if stake > 0 else 0,
                "Stake": stake, 
                "Retorno_Potencial": retorno, 
                "Resultado": resultado, 
                "Lucro/Prejuizo": lucro
            }
            
            if salvar_aposta(nova):
                st.success("Aposta registrada!")
                
                # --- LIMPEZA FORÇADA DOS CAMPOS ---
                # Isso atualiza o Session State antes do rerun, garantindo que os campos voltem vazios
                st.session_state['n_evento'] = ""
                st.session_state['n_stake'] = 0.0
                st.session_state['n_retorno'] = 0.0
                st.session_state['n_resultado'] = "Pendente"
                # Opcional: manter data e mercado para facilitar lançamentos em sequência
                # st.session_state['n_data'] = date.today() 
                
                time.sleep(0.5)
                st.rerun()
        else: 
            st.error("Verifique: Stake > 0 e nome do Evento preenchido.")

# --- ABA 2: APOSTAS (LISTA COM AÇÕES RÁPIDAS) ---
elif selected == "Apostas":
    st.subheader("🗂️ Histórico")
    df = carregar_apostas(usuario)
    
    if df.empty: st.info("Sem apostas.")
    else:
        # --- LISTA VISUAL ---
        if not st.session_state['edit_mode']:
            st.caption("Ações Rápidas: ✅Green | ❌Red | 🔄Reembolso | ✏️Editar | 🗑️Excluir")
            
            # Ordenação
            try: df = df.sort_values(by='Data', ascending=False)
            except: pass
            
            for index, row in df.iterrows():
                res = row['Resultado']
                cor, icone = "gray", "⏳"
                if "Green" in res: cor, icone = "green", "✅"
                elif "Red" in res: cor, icone = "red", "❌"
                elif "Reembolso" in res: cor, icone = "orange", "🔄"

                with st.container(border=True):
                    # --- LINHA 1: INFORMAÇÕES ---
                    st.markdown(f"**{row['Time/Evento']}**")
                    c_info1, c_info2 = st.columns([2, 1])
                    with c_info1:
                        st.markdown(f"<small>{row['Data']} | {row['Mercado']}</small>", unsafe_allow_html=True)
                    with c_info2:
                        if "Green" in res: st.markdown(f":green[**+ R$ {row['Lucro/Prejuizo']:.2f}**]")
                        elif "Red" in res: st.markdown(f":red[**R$ {row['Lucro/Prejuizo']:.2f}**]")
                        else: st.markdown(f"**{res}**")

                    st.divider() # Linha separadora visual

                    # --- LINHA 2: BOTÕES DE AÇÃO RÁPIDA ---
                    b_green, b_red, b_refund, b_edit, b_del = st.columns(5)
                    
                    # 1. GREEN
                    if b_green.button("✅", key=f"g_{index}", help="Marcar como Green"):
                        df.at[index, 'Resultado'] = "Green (Venceu)"
                        df.at[index, 'Lucro/Prejuizo'] = float(row['Retorno_Potencial']) - float(row['Stake'])
                        atualizar_planilha_usuario(df, usuario)
                        st.rerun()

                    # 2. RED
                    if b_red.button("❌", key=f"r_{index}", help="Marcar como Red"):
                        df.at[index, 'Resultado'] = "Red (Perdeu)"
                        df.at[index, 'Lucro/Prejuizo'] = -float(row['Stake'])
                        atualizar_planilha_usuario(df, usuario)
                        st.rerun()

                    # 3. REEMBOLSO
                    if b_refund.button("🔄", key=f"rem_{index}", help="Marcar como Reembolso"):
                        df.at[index, 'Resultado'] = "Reembolso"
                        df.at[index, 'Lucro/Prejuizo'] = 0.0
                        atualizar_planilha_usuario(df, usuario)
                        st.rerun()

                    # 4. EDITAR (Abre formulário)
                    if b_edit.button("✏️", key=f"ed_{index}", help="Editar detalhes"):
                        st.session_state['edit_mode'] = True
                        st.session_state['edit_index'] = index
                        st.rerun()

                    # 5. EXCLUIR
                    if b_del.button("🗑️", key=f"del_{index}", help="Excluir aposta"):
                        df = df.drop(index)
                        atualizar_planilha_usuario(df, usuario)
                        st.success("Excluído!")
                        time.sleep(0.5)
                        st.rerun()

        # --- MODO EDIÇÃO ---
        else:
            idx = st.session_state['edit_index']
            if idx not in df.index:
                st.session_state['edit_mode'] = False
                st.rerun()
            
            row = df.loc[idx]
            st.markdown(f"**Editando:** {row['Time/Evento']}")
            with st.container(border=True):
                try: d_padrao = row['Data']
                except: d_padrao = date.today()
                
                c1, c2 = st.columns([1,2])
                n_data = c1.date_input("Data", d_padrao)
                n_evento = c2.text_input("Evento", row['Time/Evento'])
                
                try: i_merc = MERCADOS_FUTEBOL.index(row['Mercado'])
                except: i_merc = 0
                n_merc = st.selectbox("Mercado", MERCADOS_FUTEBOL, index=i_merc)
                
                c3, c4 = st.columns(2)
                n_stake = c3.number_input("Stake", value=float(row['Stake']), step=10.0)
                n_ret = c4.number_input("Retorno", value=float(row['Retorno_Potencial']), step=10.0)
                
                l_res = ["Pendente", "Green (Venceu)", "Red (Perdeu)", "Reembolso"]
                try: i_res = l_res.index(row['Resultado'])
                except: i_res = 0
                n_res = st.selectbox("Resultado", l_res, index=i_res)
                
                cb1, cb2 = st.columns(2)
                if cb1.button("⬅️ Voltar", use_container_width=True):
                    st.session_state['edit_mode'] = False
                    st.rerun()
                if cb2.button("💾 Atualizar", type="primary", use_container_width=True):
                    lucro = 0.0
                    if "Green" in n_res: lucro = n_ret - n_stake
                    elif "Red" in n_res: lucro = -n_stake
                    
                    df.at[idx, 'Data'] = str(n_data)
                    df.at[idx, 'Time/Evento'] = n_evento
                    df.at[idx, 'Mercado'] = n_merc
                    df.at[idx, 'Stake'] = n_stake
                    df.at[idx, 'Retorno_Potencial'] = n_ret
                    df.at[idx, 'Odd'] = round(n_ret/n_stake, 2) if n_stake > 0 else 0
                    df.at[idx, 'Resultado'] = n_res
                    df.at[idx, 'Lucro/Prejuizo'] = lucro
                    
                    if atualizar_planilha_usuario(df, usuario):
                        st.success("Atualizado!")
                        st.session_state['edit_mode'] = False
                        time.sleep(1)
                        st.rerun()

# --- ABA 3: KPI's (NOME ATUALIZADO) ---
elif selected == "KPI's":
    st.session_state['edit_mode'] = False
    st.subheader("📊 KPI's Profissionais")
    
    df = carregar_apostas(usuario)
    
    if df.empty:
        st.warning("Sem dados para analisar. Registre algumas apostas!")
    else:
        with st.expander("📅 Filtros de Data", expanded=True):
            col_d1, col_d2 = st.columns(2)
            d_inicio = col_d1.date_input("Início", date.today() - timedelta(days=30))
            d_fim = col_d2.date_input("Fim", date.today())
        
        mask = (df['Data'] >= d_inicio) & (df['Data'] <= d_fim)
        df_filtered = df.loc[mask]
        
        if df_filtered.empty:
            st.info("Nenhuma aposta neste período.")
        else:
            df_resolvidas = df_filtered[df_filtered['Resultado'].isin(["Green (Venceu)", "Red (Perdeu)"])]
            
            lucro_total = df_filtered["Lucro/Prejuizo"].sum()
            total_apostado = df_filtered["Stake"].sum()
            num_apostas = len(df_filtered)
            
            roi = (lucro_total / total_apostado * 100) if total_apostado > 0 else 0.0
            
            win_count = len(df_resolvidas[df_resolvidas['Resultado'] == "Green (Venceu)"])
            total_res = len(df_resolvidas)
            winrate = (win_count / total_res * 100) if total_res > 0 else 0.0
            
            odd_media = df_filtered[df_filtered['Odd'] > 0]['Odd'].mean()
            if pd.isna(odd_media): odd_media = 0.0
            
            lucro_medio = lucro_total / num_apostas if num_apostas > 0 else 0
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Lucro Total", f"R$ {lucro_total:.2f}", delta=f"{lucro_total:.2f}")
            k2.metric("ROI (%)", f"{roi:.2f}%", delta_color="normal")
            k3.metric("Winrate", f"{winrate:.1f}%")
            k4.metric("Odd Média", f"{odd_media:.2f}")
            
            k5, k6, k7, k8 = st.columns(4)
            k5.metric("Total Apostado", f"R$ {total_apostado:.2f}")
            k6.metric("Nº Apostas", f"{num_apostas}")
            k7.metric("Lucro Médio/Bet", f"R$ {lucro_medio:.2f}")
            
            if lucro_total > 0:
                st.success(f"🚀 Você está LUCROU R$ {lucro_total:.2f} neste período!")
            elif lucro_total < 0:
                st.error(f"⚠️ Atenção! Prejuízo de R$ {lucro_total:.2f}. Revise sua gestão.")
