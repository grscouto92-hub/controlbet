import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px
import requests
from bs4 import BeautifulSoup # Biblioteca de Raspagem

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", page_icon="🦁", layout="wide")

# --- CSS Otimizado ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
    .stButton button {width: 100%; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# --- 1. Função de ROBÔ (Web Scraping) ---
@st.cache_data(ttl=3600) # Guarda os dados por 1 hora para não ficar lento
def buscar_jogos_do_dia():
    """Busca jogos de hoje no Placar de Futebol (Fonte mais leve que Redscores)"""
    url = "https://www.placardefutebol.com.br/jogos-de-hoje"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        jogos = []
        
        # Procura pelos blocos de jogos (a estrutura do site pode mudar, mas essa é a atual)
        # Iterando por campeonatos
        container_jogos = soup.find_all('div', class_='container-content')
        
        for container in container_jogos:
            liga = container.find('h3', class_='match-list-league')
            nome_liga = liga.text.strip() if liga else "Liga Desconhecida"
            
            items = container.find_all('div', class_='match-list-item')
            for item in items:
                try:
                    time_casa = item.find('div', class_='team-home').find('a').text.strip()
                    time_fora = item.find('div', class_='team-away').find('a').text.strip()
                    hora = item.find('span', class_='status-name').text.strip()
                    
                    # Filtra apenas jogos que ainda não aconteceram ou estão rolando
                    # (Opcional, aqui pegamos todos)
                    
                    jogos.append({
                        "Liga": nome_liga,
                        "Time_Casa": time_casa,
                        "Time_Fora": time_fora,
                        "Jogo_Completo": f"{time_casa} x {time_fora}",
                        "Hora": hora,
                        "Search_Key": f"{time_casa} {time_fora}".lower() # Para facilitar a busca
                    })
                except:
                    continue
                    
        return pd.DataFrame(jogos)
    except Exception as e:
        st.error(f"Erro ao buscar jogos: {e}")
        return pd.DataFrame()

# --- 2. Conexão Google Sheets ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet: return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("✅ Aposta salva!", icon="🚀")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("💼 Gestão Profissional")

# Inicializa variaveis de sessão para o preenchimento automático funcionar
if 'form_liga' not in st.session_state: st.session_state.form_liga = ""
if 'form_jogo' not in st.session_state: st.session_state.form_jogo = ""
if 'form_hora' not in st.session_state: st.session_state.form_hora = datetime.now().time()

# --- ÁREA DE BUSCA INTELIGENTE ---
with st.expander("🔍 **Localizar Jogo Automaticamente (Jogos de Hoje)**", expanded=True):
    col_search1, col_search2 = st.columns([3, 1])
    termo_busca = col_search1.text_input("Digite o nome de um time (Ex: Flamengo)", placeholder="Digite e aperte Enter ou Buscar")
    
    if col_search2.button("Buscar Jogo"):
        df_jogos = buscar_jogos_do_dia()
        if not df_jogos.empty and termo_busca:
            # Filtra onde o termo aparece (no casa ou fora)
            resultados = df_jogos[df_jogos['Search_Key'].str.contains(termo_busca.lower())]
            
            if len(resultados) == 1:
                # Achou 1 jogo exato
                jogo_encontrado = resultados.iloc[0]
                st.session_state.form_liga = jogo_encontrado['Liga']
                st.session_state.form_jogo = jogo_encontrado['Jogo_Completo']
                # Tenta converter hora string para objeto time, se falhar usa agora
                try:
                    hora_str = jogo_encontrado['Hora'].replace('h', ':')
                    st.session_state.form_hora = datetime.strptime(hora_str, '%H:%M').time()
                except:
                    pass
                st.success(f"Jogo encontrado: {jogo_encontrado['Jogo_Completo']}")
            elif len(resultados) > 1:
                st.warning("Encontrei mais de um jogo com esse nome. Seja mais específico.")
                st.dataframe(resultados[['Liga', 'Jogo_Completo', 'Hora']], hide_index=True)
            else:
                st.error("Nenhum jogo encontrado para hoje com esse nome.")
        else:
            st.warning("Digite um time para buscar.")

# --- DASHBOARD E MÉTRICAS ---
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial

if not df.empty:
    df['Lucro_Real'] = pd.to_numeric(df['Lucro_Real'], errors='coerce').fillna(0)
    df['Valor_Entrada'] = pd.to_numeric(df['Valor_Entrada'], errors='coerce').fillna(0)
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual += lucro_total
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0
    c2.metric("ROI", f"{roi:.2f}%")
    c3.metric("Entradas", len(df))

st.divider()

# --- FORMULÁRIO DE REGISTRO ---
st.subheader("📝 Registrar Nova Aposta")

# Container para organizar inputs
c_fin1, c_fin2, c_fin3 = st.columns(3)
with c_fin1:
    valor_entrada = st.number_input("Valor Entrada (R$)", value=20.0, step=5.0)
with c_fin2:
    valor_retorno = st.number_input("Retorno Total (R$)", value=28.0, step=1.0)
with c_fin3:
    odd_calc = valor_retorno / valor_entrada if valor_entrada > 0 else 0
    st.text_input("Odd Calculada", value=f"{odd_calc:.3f}", disabled=True)

c_det1, c_det2, c_det3 = st.columns(3)
with c_det1:
    # Usa session_state para preencher automático se a busca achou algo
    liga = st.text_input("Liga", value=st.session_state.form_liga)
with c_det2:
    jogo = st.text_input("Jogo (Casa x Fora)", value=st.session_state.form_jogo)
with c_det3:
    data_jogo = st.date_input("Data", date.today())

c_opt1, c_opt2, c_opt3 = st.columns(3)
with c_opt1:
    mercado = st.selectbox("Mercado", ["Match Odds", "Over 0.5 HT", "Over Gols", "Under Gols", "Handicap", "Outro"])
with c_opt2:
    resultado = st.selectbox("Resultado", ["Pendente", "Green", "Red", "Reembolso"])
with c_opt3:
    obs = st.text_input("Obs (Ex: Método X)")

if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
    lucro = 0.0
    if resultado == "Green": lucro = valor_retorno - valor_entrada
    elif resultado == "Red": lucro = -valor_entrada
    
    nova_aposta = [
        data_jogo.strftime("%d/%m/%Y"),
        liga,
        jogo,
        mercado,
        valor_entrada,
        valor_retorno,
        f"{odd_calc:.3f}",
        resultado,
        lucro,
        obs
    ]
    salvar_registro(nova_aposta)

# --- VISUALIZAÇÃO DE DADOS ---
if not df.empty:
    st.divider()
    st.dataframe(df.iloc[::-1], use_container_width=True)
