import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Profissional", page_icon="💼", layout="wide")

# --- CSS Personalizado ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
    .stButton button {width: 100%; border-radius: 5px; font-weight: bold;}
    /* Destaque para o lucro positivo */
    .metric-green {color: #00e676;}
    .metric-red {color: #ff1744;}
</style>
""", unsafe_allow_html=True)

# --- 1. Função de ROBÔ DE BUSCA (Blindada) ---
@st.cache_data(ttl=3600) # Guarda os dados por 1 hora
def buscar_jogos_do_dia():
    """Busca jogos de hoje com proteção anti-bloqueio"""
    url = "https://www.placardefutebol.com.br/jogos-de-hoje"
    # Cabeçalhos para simular um navegador real e evitar erro 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            st.error(f"⚠️ O site de jogos não respondeu (Erro {response.status_code}).")
            return pd.DataFrame()

        soup = BeautifulSoup(response.content, 'html.parser')
        jogos = []
        
        # Tenta encontrar os jogos na estrutura atual do site
        items = soup.find_all('div', class_='match-list-item')
        if not items:
            items = soup.find_all('a', class_='match-list-item') # Tentativa alternativa

        for item in items:
            try:
                # Extrai nomes dos times limpando espaços extras
                casa_elem = item.find(class_='team-home')
                fora_elem = item.find(class_='team-away')
                
                if casa_elem and fora_elem:
                    time_casa = casa_elem.get_text(strip=True)
                    time_fora = fora_elem.get_text(strip=True)
                    
                    # Tenta achar a liga (elemento pai anterior)
                    liga = "Jogos de Hoje"
                    parent_liga = item.find_previous(class_='match-list-league')
                    if parent_liga:
                        liga = parent_liga.get_text(strip=True)

                    jogos.append({
                        "Liga": liga,
                        "Jogo_Completo": f"{time_casa} x {time_fora}",
                        "Search_Key": f"{time_casa} {time_fora}".lower()
                    })
            except:
                continue
                    
        return pd.DataFrame(jogos)
    except Exception as e:
        st.error(f"Erro ao buscar lista de jogos: {e}")
        return pd.DataFrame()

# --- 2. Conexão Google Sheets ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Tenta abrir a planilha e a aba específica
        return client.open("ControlBET").worksheet("Registros")
    except gspread.exceptions.WorksheetNotFound:
        st.error("🚨 ERRO: Não encontrei a aba 'Registros'. Por favor, renomeie a aba na sua planilha para 'Registros' (com R maiúsculo).")
        return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet:
        return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("✅ Aposta Salva com Sucesso!", icon="💾")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("📊 Gestão Profissional de Banca")

# Inicializa variaveis de sessão (memória temporária para o formulário)
if 'form_liga' not in st.session_state: st.session_state.form_liga = ""
if 'form_jogo' not in st.session_state: st.session_state.form_jogo = ""

# --- 1. BUSCA INTELIGENTE DE JOGOS ---
with st.expander("🔍 **Localizar Jogo Automaticamente**", expanded=True):
    c_search1, c_search2 = st.columns([3, 1])
    termo_busca = c_search1.text_input("Digite o time:", placeholder="Ex: Flamengo")
    
    if c_search2.button("Buscar Jogo"):
        with st.spinner("Buscando jogos..."):
            df_jogos = buscar_jogos_do_dia()
            
            if not df_jogos.empty and termo_busca:
                # Filtra
                res = df_jogos[df_jogos['Search_Key'].str.contains(termo_busca.lower())]
                
                if len(res) == 1:
                    jogo_ok = res.iloc[0]
                    st.session_state.form_liga = jogo_ok['Liga']
                    st.session_state.form_jogo = jogo_ok['Jogo_Completo']
                    st.success(f"✅ Jogo carregado: {jogo_ok['Jogo_Completo']}")
                    st.rerun()
                elif len(res) > 1:
                    st.warning("Encontrei mais de um jogo. Copie o nome exato abaixo:")
                    st.dataframe(res[['Liga', 'Jogo_Completo']], hide_index=True)
                else:
                    st.error("Nenhum jogo encontrado hoje com esse nome.")
            elif termo_busca == "":
                st.warning("Digite algo para buscar.")
            else:
                st.warning("Não consegui ler a lista de jogos agora.")

# --- 2. DASHBOARD (MÉTRICAS) ---
df = carregar_dados()
banca_inicial = 100.00 # Defina sua banca inicial aqui
saldo_atual = banca_inicial

if not df.empty:
    # Tratamento de erro caso venha vazio
    df['Lucro_Real'] = pd.to_numeric(df['Lucro_Real'], errors='coerce').fillna(0)
    df['Valor_Entrada'] = pd.to_numeric(df['Valor_Entrada'], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
    
    # ROI e Winrate
    fechadas = df[df['Resultado'].isin(['Green', 'Red'])]
    qtd_total = len(fechadas)
    qtd_green = len(fechadas[fechadas['Resultado'] == 'Green'])
    
    winrate = (qtd_green / qtd_total * 100) if qtd_total > 0 else 0.0
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0.0

    # Exibição
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    col2.metric("Winrate", f"{winrate:.1f}%")
    col3.metric("ROI", f"{roi:.2f}%")
    col4.metric("Entradas", len(df))

    st.divider()

# --- 3. FORMULÁRIO DE REGISTRO ---
st.subheader("📝 Registrar Nova Entrada")

with st.container(border=True):
    # Parte Financeira (Calculadora de Odd)
    cf1, cf2, cf3 = st.columns(3)
    valor_entrada = cf1.number_input("Valor Entrada (R$)", min_value=0.0, value=20.0, step=1.0)
    valor_retorno = cf2.number_input("Retorno Total (R$)", min_value=0.0, value=28.0, step=1.0)
    
    odd_calc = 0.0
    if valor_entrada > 0:
        odd_calc = valor_retorno / valor_entrada
    
    cf3.text_input("Odd Calculada", value=f"{odd_calc:.3f}", disabled=True)

    # Detalhes do Jogo
    cd1, cd2, cd3 = st.columns(3)
    liga_input = cd1.text_input("Liga", value=st.session_state.form_liga)
    jogo_input = cd2.text_input("Jogo (Casa x Fora)", value=st.session_state.form_jogo)
    data_input = cd3.date_input("Data do Jogo", date.today())

    # Detalhes da Aposta
    co1, co2, co3 = st.columns(3)
    mercado_input = co1.selectbox("Mercado", ["Match Odds", "Over Gols", "Under Gols", "Handicap", "Ambas Marcam", "Outros"])
    resultado_input = co2.selectbox("Resultado", ["Pendente", "Green", "Red", "Reembolso"])
    obs_input = co3.text_input("Obs / Método")

    # Botão Salvar
    if st.button("💾 Salvar Registro no Sheets", type="primary"):
        if valor_entrada <= 0:
            st.warning("O valor da entrada precisa ser maior que zero.")
        elif not jogo_input:
            st.warning("O campo 'Jogo' é obrigatório.")
        else:
            # Lógica Financeira Final
            lucro_final = 0.0
            if resultado_input == "Green":
                lucro_final = valor_retorno - valor_entrada
            elif resultado_input == "Red":
                lucro_final = -valor_entrada
            
            nova_linha = [
                data_input.strftime("%d/%m/%Y"),
                liga_input,
                jogo_input,
                mercado_input,
                valor_entrada,
                valor_retorno,
                f"{odd_calc:.3f}",
                resultado_input,
                lucro_final,
                obs_input
            ]
            salvar_registro(nova_linha)

# --- 4. HISTÓRICO E GRÁFICOS ---
if not df.empty:
    st.divider()
    tab_list, tab_graph = st.tabs(["📋 Histórico Recente", "📈 Evolução da Banca"])
    
    with tab_list:
        st.dataframe(
            df[['Data', 'Jogo', 'Mercado', 'Odd_Calc', 'Valor_Entrada', 'Resultado', 'Lucro_Real', 'Obs']].iloc[::-1],
            use_container_width=True
        )
    
    with tab_graph:
        df_graf = df.copy()
        df_graf['Saldo_Acumulado'] = banca_inicial + df_graf['Lucro_Real'].cumsum()
        
        # Cria gráfico bonito com Plotly
        fig = px.line(df_graf, y='Saldo_Acumulado', title="Curva de Crescimento", markers=True)
        fig.update_layout(yaxis_title="Banca (R$)", xaxis_title="Volume de Apostas")
        fig.add_hline(y=banca_inicial, line_dash="dash", line_color="gray", annotation_text="Banca Inicial")
        
        st.plotly_chart(fig, use_container_width=True)
