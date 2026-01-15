import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca", page_icon="📊", layout="wide")

# --- CSS para remover espaços vazios e focar no conteúdo ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
</style>
""", unsafe_allow_html=True)

# --- Conexão Google Sheets ---
def conectar_gsheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Substitua 'Registros' pelo nome da aba exata que você criou
        return client.open("ControlBET").worksheet("Registros")
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# --- Carregar Dados ---
def carregar_dados():
    sheet = conectar_gsheets()
    if sheet:
        dados = sheet.get_all_records()
        return pd.DataFrame(dados)
    return pd.DataFrame()

# --- Salvar Dados ---
def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("✅ Aposta salva com sucesso!", icon="💾")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("💼 Controle de Banca Profissional")

# 1. Carregamento e Cálculos Prévios
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial

if not df.empty:
    # Tratamento de erro caso venha vazio ou texto
    df['Lucro_Real'] = pd.to_numeric(df['Lucro_Real'], errors='coerce').fillna(0)
    df['Valor_Entrada'] = pd.to_numeric(df['Valor_Entrada'], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
    
    # Métricas de Performance
    apostas_fechadas = df[df['Resultado'].isin(['Green', 'Red'])]
    qtd_total = len(apostas_fechadas)
    qtd_green = len(apostas_fechadas[apostas_fechadas['Resultado'] == 'Green'])
    winrate = (qtd_green / qtd_total * 100) if qtd_total > 0 else 0.0
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0.0
else:
    lucro_total = 0
    winrate = 0
    roi = 0

# 2. Exibição das Métricas no Topo
col1, col2, col3, col4 = st.columns(4)
col1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f} total")
col2.metric("Winrate", f"{winrate:.1f}%")
col3.metric("ROI", f"{roi:.2f}%")
col4.metric("Total Entradas", len(df))

st.markdown("---")

# 3. Formulário de Registro (Na Tela Principal)
st.subheader("📝 Registrar Nova Entrada")

with st.container(border=True):
    # Linha 1: Dados Financeiros (Onde a mágica da Odd acontece)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        valor_entrada = st.number_input("Valor da Entrada (R$)", min_value=0.0, value=20.0, step=1.0)
    with c2:
        valor_retorno = st.number_input("Retorno Potencial (R$)", min_value=0.0, value=28.0, step=1.0, help="Quanto volta se der Green?")
    
    # Cálculo Automático da Odd
    odd_calculada = 0.0
    if valor_entrada > 0:
        odd_calculada = valor_retorno / valor_entrada
    
    with c3:
        # Mostra a odd calculada mas bloqueada para edição (apenas leitura)
        st.text_input("Odd Calculada (Automática)", value=f"{odd_calculada:.3f}", disabled=True)

    # Linha 2: Dados do Jogo
    c4, c5, c6 = st.columns(3)
    with c4:
        data_jogo = st.date_input("Data do Jogo", datetime.now())
    with c5:
        liga = st.text_input("Campeonato / Liga")
    with c6:
        jogo = st.text_input("Jogo (Casa x Fora)")

    # Linha 3: Detalhes e Resultado
    c7, c8, c9 = st.columns(3)
    with c7:
        mercado = st.selectbox("Mercado", ["Match Odds", "Over Gols", "Under Gols", "Handicap", "Ambas Marcam", "Outros"])
    with c8:
        resultado = st.selectbox("Resultado", ["Pendente", "Green", "Red", "Reembolso"])
    with c9:
        obs = st.text_input("Observação (Opcional)")

    # Botão de Enviar
    if st.button("💾 Registrar Aposta", use_container_width=True, type="primary"):
        if valor_entrada <= 0:
            st.warning("O valor da entrada deve ser maior que zero.")
        else:
            # Lógica do Lucro Real
            lucro_real = 0.0
            if resultado == "Green":
                lucro_real = valor_retorno - valor_entrada
            elif resultado == "Red":
                lucro_real = -valor_entrada
            elif resultado == "Reembolso":
                lucro_real = 0.0
            # Se for Pendente, lucro é 0 até atualizar

            nova_linha = [
                data_jogo.strftime("%d/%m/%Y"),
                liga,
                jogo,
                mercado,
                valor_entrada,
                valor_retorno,
                f"{odd_calculada:.3f}", # Salva formatado com 3 casas
                resultado,
                lucro_real,
                obs
            ]
            salvar_registro(nova_linha)

# 4. Histórico e Gráfico (Abaixo do formulário)
if not df.empty:
    st.markdown("---")
    tab1, tab2 = st.tabs(["📋 Histórico Recente", "📈 Gráfico de Evolução"])
    
    with tab1:
        # Mostra do mais recente para o mais antigo
        st.dataframe(df.iloc[::-1], use_container_width=True)
    
    with tab2:
        # Gráfico simples de evolução
        df_chart = df.copy()
        df_chart['Saldo_Acumulado'] = banca_inicial + df_chart['Lucro_Real'].cumsum()
        fig = px.line(df_chart, y='Saldo_Acumulado', title="Crescimento da Banca")
        st.plotly_chart(fig, use_container_width=True)
