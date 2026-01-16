import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px
import cloudscraper
from bs4 import BeautifulSoup

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", page_icon="⚽", layout="wide")

# --- CSS Otimizado ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 26px; font-weight: bold;}
    .stButton button {width: 100%; border-radius: 8px; font-weight: bold; height: 3em;}
    input[type=number] {font-weight: bold; color: #4caf50;}
</style>
""", unsafe_allow_html=True)

# --- 1. ROBÔ DE BUSCA (Alvo: JogosDeHojeNaTV) ---
@st.cache_data(ttl=1800) # Cache de 30 minutos
def buscar_jogos_tv():
    """Busca jogos especificamente no site jogosdehojenatv.com.br"""
    jogos = []
    scraper = cloudscraper.create_scraper() # Disfarce de navegador
    
    url = "https://www.jogosdehojenatv.com.br/"
    
    try:
        response = scraper.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # O site geralmente organiza em listas ou divs. 
            # Vamos procurar elementos que contêm informações de partidas.
            # Estratégia Genérica para esse site: procurar linhas com horário e times
            
            # Tenta encontrar os containers de jogos (a estrutura pode variar, então buscamos amplo)
            linhas = soup.find_all(['li', 'div'], class_=lambda x: x and ('game' in x or 'partida' in x or 'list' in x))
            
            # Se não achar por classe, pega todas as listas
            if not linhas:
                linhas = soup.find_all('li')

            for linha in linhas:
                texto = linha.get_text(" ", strip=True)
                
                # Verifica se tem cara de jogo (tem " x " ou " vs " e um horário no começo)
                if ' x ' in texto or ' vs ' in texto:
                    # Tenta limpar o texto para pegar os times
                    # Exemplo de texto: "15:00 Campeonato Inglês: Time A x Time B ESPN"
                    
                    # Separa campeonato (geralmente antes dos times)
                    liga = "Futebol TV"
                    partes = texto.split(':')
                    
                    # Tentativa de extrair dados
                    nome_jogo = texto # Padrão
                    
                    # Se tiver separador de hora (ex: 15:00 ...)
                    if len(partes) > 1:
                        # Pega o pedaço que tem o " x "
                        for pedaco in partes:
                            if ' x ' in pedaco:
                                nome_jogo = pedaco.strip()
                                # Remove o nome do canal de TV do final se tiver
                                nome_jogo = nome_jogo.split(' ao vivo')[0]
                                break
                    
                    jogos.append({
                        "Liga": liga,
                        "Jogo_Completo": nome_jogo,
                        "Search_Key": nome_jogo.lower()
                    })
        else:
            print(f"Site retornou código: {response.status_code}")
            
    except Exception as e:
        print(f"Erro no scraper: {e}")

    # Remove duplicatas
    df = pd.DataFrame(jogos)
    if not df.empty:
        df = df.drop_duplicates(subset=['Search_Key'])
    
    return df

# --- 2. Conexão Google Sheets ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except Exception as e:
        st.error(f"Erro de conexão (Planilha): {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet: return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("✅ Aposta Registrada!", icon="💰")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("💼 Gestão de Banca Profissional")

# Session State para preencher campos
if 'form_liga' not in st.session_state: st.session_state.form_liga = ""
if 'form_jogo' not in st.session_state: st.session_state.form_jogo = ""

# --- ÁREA DE BUSCA (Apedidos: JogosDeHojeNaTV) ---
with st.expander("🔍 **Localizar Jogo (Busca Automática)**", expanded=True):
    c1, c2 = st.columns([3, 1])
    termo_busca = c1.text_input("Digite o time:", placeholder="Ex: Flamengo")
    
    if c2.button("Buscar Jogo"):
        with st.spinner("Consultando jogosdehojenatv.com.br..."):
            df_jogos = buscar_jogos_tv()
            
            if not df_jogos.empty and termo_busca:
                # Filtra
                res = df_jogos[df_jogos['Search_Key'].str.contains(termo_busca.lower())]
                
                if len(res) >= 1:
                    jogo_ok = res.iloc[0]
                    st.session_state.form_jogo = jogo_ok['Jogo_Completo']
                    st.session_state.form_liga = "Jogos de Hoje" # O site mistura ligas, definimos genérico
                    st.success(f"✅ Achei: {jogo_ok['Jogo_Completo']}")
                    st.rerun()
                else:
                    st.warning(f"O time '{termo_busca}' não aparece na lista de hoje da TV.")
            elif termo_busca == "":
                st.warning("Digite o nome do time.")
            else:
                st.error("Não consegui ler a lista do site agora. Ele pode estar bloqueando acessos de nuvem.")

# --- DASHBOARD ---
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial
lucro_total = 0.0

if not df.empty:
    for col in ['Lucro_Real', 'Valor_Entrada']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual += lucro_total
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    col2.metric("Entradas", len(df))
    
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0
    col3.metric("ROI", f"{roi:.2f}%")
    
    fechadas = df[df['Resultado'].isin(['Green', 'Red'])]
    qtd = len(fechadas)
    winrate = (len(fechadas[fechadas['Resultado'] == 'Green']) / qtd * 100) if qtd > 0 else 0
    col4.metric("Winrate", f"{winrate:.1f}%")

st.divider()

# --- FORMULÁRIO ---
st.subheader("📝 Nova Entrada")

with st.container(border=True):
    # Finanças
    cf1, cf2, cf3 = st.columns(3)
    valor_entrada = cf1.number_input("Valor Entrada (R$)", min_value=0.0, value=20.0, step=1.0)
    valor_retorno = cf2.number_input("Retorno Total (R$)", min_value=0.0, value=28.0, step=1.0)
    
    odd_calc = 0.0
    if valor_entrada > 0: odd_calc = valor_retorno / valor_entrada
    
    with cf3:
        st.markdown(f"<div style='background:#f0f2f6;padding:10px;text-align:center;border-radius:5px'><b>Odd: {odd_calc:.3f}</b></div>", unsafe_allow_html=True)

    # Detalhes
    cd1, cd2, cd3 = st.columns(3)
    liga_input = cd1.text_input("Liga", value=st.session_state.form_liga)
    jogo_input = cd2.text_input("Jogo (Casa x Fora)", value=st.session_state.form_jogo)
    data_input = cd3.date_input("Data", date.today())

    # Opções
    co1, co2, co3 = st.columns(3)
    mercado_input = co1.selectbox("Mercado", ["Match Odds", "Over 0.5 HT", "Over 1.5/2.5", "Under Gols", "Ambas Marcam", "Handicap", "Outro"])
    resultado_input = co2.selectbox("Resultado", ["Pendente", "Green", "Red", "Reembolso"])
    obs_input = co3.text_input("Obs")

    if st.button("💾 CONFIRMAR REGISTRO", type="primary"):
        if valor_entrada > 0 and jogo_input:
            lucro_final = 0.0
            if resultado_input == "Green": lucro_final = valor_retorno - valor_entrada
            elif resultado_input == "Red": lucro_final = -valor_entrada
            
            linha = [
                data_input.strftime("%d/%m/%Y"),
                liga_input, jogo_input, mercado_input,
                valor_entrada, valor_retorno, f"{odd_calc:.3f}",
                resultado_input, lucro_final, obs_input
            ]
            salvar_registro(linha)
        else:
            st.warning("Preencha Valor e Jogo.")

# --- HISTÓRICO ---
if not df.empty:
    st.divider()
    t1, t2 = st.tabs(["Histórico", "Gráfico"])
    with t1:
        st.dataframe(df.iloc[::-1], use_container_width=True)
    with t2:
        dfig = df.copy()
        dfig['Saldo'] = banca_inicial + dfig['Lucro_Real'].cumsum()
        st.plotly_chart(px.line(dfig, y='Saldo', markers=True), use_container_width=True)
