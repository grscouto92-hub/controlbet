import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import plotly.express as px

# --- 1. Configuração da Página ---
st.set_page_config(page_title="Gestão Banca Pro", page_icon="📈", layout="wide")

# --- 2. Conexão Google Sheets (COM CACHE) ---
def conectar_gsheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Tenta pegar dos secrets (nuvem) ou local
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    # Abre a planilha pelo nome e depois a aba 'Diario'
    return client.open("ControlBET").worksheet("Diario")

# --- 3. Função para Carregar Dados ---
def carregar_dados():
    try:
        sheet = conectar_gsheets()
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return pd.DataFrame()

# --- 4. Função para Salvar Nova Aposta ---
def salvar_aposta(dados_nova_aposta):
    try:
        sheet = conectar_gsheets()
        # Transforma os dados em uma lista na ordem das colunas
        linha = [
            dados_nova_aposta["Data"],
            dados_nova_aposta["Hora"],
            dados_nova_aposta["Liga"],
            dados_nova_aposta["Jogo"],
            dados_nova_aposta["Mercado"],
            dados_nova_aposta["Odd"],
            dados_nova_aposta["Valor_Entrada"],
            dados_nova_aposta["Resultado"],
            dados_nova_aposta["Obs"]
        ]
        sheet.append_row(linha)
        st.success("✅ Aposta Registrada com Sucesso!")
        st.cache_data.clear() # Limpa o cache para recarregar os dados novos
        st.rerun() # Atualiza a tela
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- 5. Interface Principal ---
st.title("📈 Painel de Controle - Profissional")

# --- SIDEBAR: Formulário de Registro ---
with st.sidebar:
    st.header("📝 Nova Entrada")
    with st.form("form_aposta", clear_on_submit=True):
        data_input = st.date_input("Data", datetime.now())
        hora_input = st.time_input("Hora", datetime.now())
        liga = st.text_input("Liga/Campeonato")
        jogo = st.text_input("Jogo (Casa x Fora)")
        mercado = st.selectbox("Mercado", ["Match Odds", "Over 0.5 HT", "Over 1.5", "Under 2.5", "Ambas Marcam", "Outro"])
        odd = st.number_input("Odd", min_value=1.01, step=0.01, value=1.40)
        valor = st.number_input("Valor (R$)", min_value=1.0, step=1.0, value=20.0) # Seu padrão agressivo
        resultado = st.selectbox("Status", ["Pendente", "Green", "Red", "Reembolso"])
        obs = st.text_area("Obs (Análise GF)")
        
        btn_enviar = st.form_submit_button("Registrar Aposta")
        
        if btn_enviar:
            nova_aposta = {
                "Data": data_input.strftime("%d/%m/%Y"),
                "Hora": hora_input.strftime("%H:%M"),
                "Liga": liga,
                "Jogo": jogo,
                "Mercado": mercado,
                "Odd": float(odd),
                "Valor_Entrada": float(valor),
                "Resultado": resultado,
                "Obs": obs
            }
            salvar_aposta(nova_aposta)

# --- DASHBOARD CENTRAL ---
df = carregar_dados()

if not df.empty:
    # 1. Tratamento de Dados
    # Converte colunas numéricas (substitui vírgula por ponto se houver)
    for col in ['Odd', 'Valor_Entrada']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

    # Calcula Lucro/Prejuízo Individual
    def calc_lucro(row):
        status = row['Resultado'].strip().title()
        stake = row['Valor_Entrada']
        odd = row['Odd']
        if status == 'Green': return (stake * odd) - stake
        elif status == 'Red': return -stake
        else: return 0.0

    df['Lucro_R$'] = df.apply(calc_lucro, axis=1)
    
    # 2. Métricas Gerais
    banca_inicial = 100.00 # Sua banca inicial fixa
    lucro_acumulado = df['Lucro_R$'].sum()
    banca_atual = banca_inicial + lucro_acumulado
    
    apostas_resolvidas = df[df['Resultado'].isin(['Green', 'Red'])]
    total_resolvidas = len(apostas_resolvidas)
    total_greens = len(apostas_resolvidas[apostas_resolvidas['Resultado'] == 'Green'])
    winrate = (total_greens / total_resolvidas * 100) if total_resolvidas > 0 else 0
    roi = (lucro_acumulado / df['Valor_Entrada'].sum() * 100) if not df.empty else 0

    # Exibição dos Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Banca Atual", f"R$ {banca_atual:.2f}", delta=f"{lucro_acumulado:.2f}")
    c2.metric("Winrate", f"{winrate:.1f}%")
    c3.metric("ROI", f"{roi:.2f}%")
    c4.metric("Total Apostas", len(df))

    st.markdown("---")

    # 3. Gráfico de Crescimento
    st.subheader("🚀 Curva de Crescimento")
    df['Saldo_Acumulado'] = banca_inicial + df['Lucro_R$'].cumsum()
    
    # Cria um índice numérico para o gráfico ficar sequencial
    df = df.reset_index()
    
    fig = px.line(df, x=df.index, y='Saldo_Acumulado', markers=True, 
                  labels={'index': 'Quantidade de Apostas', 'Saldo_Acumulado': 'Banca (R$)'})
    fig.update_traces(line_color='#00e676' if lucro_acumulado >= 0 else '#ff1744')
    st.plotly_chart(fig, use_container_width=True)

    # 4. Tabela de Registros
    st.subheader("📋 Histórico Recente")
    st.dataframe(
        df[['Data', 'Jogo', 'Mercado', 'Odd', 'Valor_Entrada', 'Resultado', 'Lucro_R$', 'Obs']].sort_index(ascending=False),
        use_container_width=True
    )

else:
    st.info("👈 Use a barra lateral para registrar sua primeira aposta!")
