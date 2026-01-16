import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px
import cloudscraper
from bs4 import BeautifulSoup
import re

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão Profissional", page_icon="⚽", layout="wide")

# --- CSS Personalizado ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
    .stButton button {width: 100%; border-radius: 5px; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 1. ROBÔ DE BUSCA (Estratégia "Sites Leves") ---
@st.cache_data(ttl=3600)
def buscar_jogos_do_dia():
    """Busca jogos em sites com menos proteção anti-bot"""
    jogos = []
    scraper = cloudscraper.create_scraper()
    
    # --- FONTE 1: JogosDeHoje.org (Site leve, alta taxa de sucesso) ---
    try:
        url = "https://www.jogosdehoje.org"
        response = scraper.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Procura por cartões de jogos
            cards = soup.find_all('div', class_='match-card')
            
            for card in cards:
                try:
                    # Tenta extrair nomes
                    times = card.find_all('span', class_='team-name')
                    if len(times) >= 2:
                        casa = times[0].get_text(strip=True)
                        fora = times[1].get_text(strip=True)
                        
                        # Tenta liga
                        liga = "Jogos de Hoje"
                        header = card.find_previous('h3')
                        if header: liga = header.get_text(strip=True)

                        jogos.append({
                            "Liga": liga,
                            "Jogo_Completo": f"{casa} x {fora}",
                            "Search_Key": f"{casa} {fora}".lower()
                        })
                except: continue
    except Exception as e:
        print(f"Fonte 1 falhou: {e}")

    # --- FONTE 2: O Tempo (Portal de Notícias - Backup) ---
    if not jogos:
        try:
            url_reserva = "https://www.otempo.com.br/sports/futebol/jogos-de-hoje"
            response = scraper.get(url_reserva)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Varredura genérica em tabelas
            linhas = soup.find_all('tr')
            for linha in linhas:
                texto = linha.get_text(" ", strip=True)
                # Procura padrão "Time A x Time B" ou "Time A vs Time B"
                if ' x ' in texto or ' vs ' in texto:
                    partes = re.split(r' x | vs ', texto)
                    if len(partes) >= 2:
                        # Limpa caracteres estranhos e pega nomes curtos
                        casa = partes[0].split()[-1] if len(partes[0].split()) > 0 else "Casa"
                        # Lógica simples para pegar nomes (pode precisar ajuste dependendo do site)
                        # Como fallback, pegamos a linha inteira como "Jogo"
                        jogos.append({
                            "Liga": "Lista O Tempo",
                            "Jogo_Completo": texto, # Salva a linha toda para garantir
                            "Search_Key": texto.lower()
                        })
        except Exception as e:
            print(f"Fonte 2 falhou: {e}")

    return pd.DataFrame(jogos)

# --- 2. Conexão Google Sheets ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except gspread.exceptions.WorksheetNotFound:
        st.error("🚨 ERRO: Não encontrei a aba 'Registros'.")
        return None
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
        st.toast("✅ Aposta Registrada!", icon="🚀")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("📊 Gestão Profissional")

# Session State
if 'form_liga' not in st.session_state: st.session_state.form_liga = ""
if 'form_jogo' not in st.session_state: st.session_state.form_jogo = ""

# --- ÁREA DE BUSCA (TOPO) ---
with st.expander("🔍 **Localizar Jogo Automaticamente**", expanded=True):
    c_search1, c_search2 = st.columns([3, 1])
    termo_busca = c_search1.text_input("Digite o time:", placeholder="Ex: Flamengo")
    
    if c_search2.button("Buscar Jogo"):
        with st.spinner("Buscando em sites acessíveis..."):
            df_jogos = buscar_jogos_do_dia()
            
            if not df_jogos.empty and termo_busca:
                # Busca 'fuzzy' (aproximada) simples
                res = df_jogos[df_jogos['Search_Key'].str.contains(termo_busca.lower())]
                
                if len(res) >= 1:
                    jogo_ok = res.iloc[0]
                    st.session_state.form_liga = jogo_ok['Liga']
                    st.session_state.form_jogo = jogo_ok['Jogo_Completo']
                    st.success(f"✅ Encontrado: {jogo_ok['Jogo_Completo']}")
                    st.rerun()
                else:
                    st.warning(f"❌ Não achei '{termo_busca}' nas listas de hoje.")
                    st.caption("Nota: Tente digitar apenas o nome principal do time.")
            elif termo_busca == "":
                st.warning("Digite o nome do time.")
            else:
                st.error("⚠️ Não consegui acessar as fontes de dados no momento. Preencha manualmente.")

# --- DASHBOARD ---
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial

if not df.empty:
    df['Lucro_Real'] = pd.to_numeric(df['Lucro_Real'], errors='coerce').fillna(0)
    df['Valor_Entrada'] = pd.to_numeric(df['Valor_Entrada'], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    col2.metric("Entradas", len(df))
    
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0
    col3.metric("ROI", f"{roi:.2f}%")
    
    fechadas = df[df['Resultado'].isin(['Green', 'Red'])]
    qtd = len(fechadas)
    greens = len(fechadas[fechadas['Resultado'] == 'Green'])
    wr = (greens / qtd * 100) if qtd > 0 else 0
    col4.metric("Winrate", f"{wr:.1f}%")

st.divider()

# --- FORMULÁRIO ---
st.subheader("📝 Registrar Nova Entrada")

with st.container(border=True):
    # Finanças
    cf1, cf2, cf3 = st.columns(3)
    valor_entrada = cf1.number_input("Valor Entrada (R$)", min_value=0.0, value=20.0, step=1.0)
    valor_retorno = cf2.number_input("Retorno Total (R$)", min_value=0.0, value=28.0, step=1.0)
    
    odd_calc = 0.0
    if valor_entrada > 0: odd_calc = valor_retorno / valor_entrada
    cf3.text_input("Odd Calculada", value=f"{odd_calc:.3f}", disabled=True)

    # Detalhes
    cd1, cd2, cd3 = st.columns(3)
    liga_input = cd1.text_input("Liga", value=st.session_state.form_liga)
    jogo_input = cd2.text_input("Jogo (Casa x Fora)", value=st.session_state.form_jogo)
    data_input = cd3.date_input("Data", date.today())

    # Opções
    co1, co2, co3 = st.columns(3)
    mercado_input = co1.selectbox("Mercado", ["Match Odds", "Over Gols", "Under Gols", "Handicap", "Ambas Marcam", "Outros"])
    resultado_input = co2.selectbox("Resultado", ["Pendente", "Green", "Red", "Reembolso"])
    obs_input = co3.text_input("Obs / Método")

    if st.button("💾 Salvar na Planilha", type="primary"):
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
    tab1, tab2 = st.tabs(["Histórico", "Gráfico"])
    with tab1:
        st.dataframe(df.iloc[::-1], use_container_width=True)
    with tab2:
        df_g = df.copy()
        df_g['Acumulado'] = banca_inicial + df_g['Lucro_Real'].cumsum()
        st.plotly_chart(px.line(df_g, y='Acumulado', markers=True), use_container_width=True)
