import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Gestão de Banca Pro", page_icon="📈", layout="centered")

# --- CSS Otimizado ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 26px; font-weight: bold;}
    .stButton button {width: 100%; border-radius: 8px; font-weight: bold; height: 3em;}
    
    /* Botão Link SofaScore */
    a.link-btn {
        text-decoration: none; padding: 12px 20px; color: white !important;
        background-color: #374df5; border-radius: 8px; border: 1px solid #374df5;
        display: block; text-align: center; width: 100%;
        font-weight: bold; font-size: 16px; transition: 0.3s;
    }
    a.link-btn:hover {background-color: #2b3bb5; border-color: #2b3bb5;}

    /* Cores Específicas para os Botões dos Cards */
    div[data-testid="column"] button:contains("✅") {background-color: #dbfadd; color: #1b5e20; border: 1px solid #1b5e20;}
    div[data-testid="column"] button:contains("❌") {background-color: #ffebee; color: #b71c1c; border: 1px solid #b71c1c;}
    div[data-testid="column"] button:contains("🔄") {background-color: #f5f5f5; color: #616161; border: 1px solid #616161;}
</style>
""", unsafe_allow_html=True)

# --- LISTAS ---
LIGAS_COMUNS = [
    "Brasileirão Série A", "Brasileirão Série B", "Copa do Brasil",
    "Premier League (ING)", "La Liga (ESP)", "Serie A (ITA)", "Bundesliga (ALE)",
    "Champions League", "Libertadores", "Sul-Americana", "Outra"
]

MERCADOS_COMUNS = [
    "Match Odds (Vencedor)", "Over 1.5 Gols", "Over 2.5 Gols", "Over 0.5 HT",
    "Under 2.5 Gols", "Ambas Marcam", "Handicap Asiático", "Empate Anula", "Outro"
]

# --- CONEXÃO GOOGLE SHEETS ---
def conectar_gsheets():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("⚠️ Configuração de credenciais do Google não encontrada.")
            return None
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("ControlBET").worksheet("Registros")
    except Exception as e:
        st.error(f"Erro ao conectar na Planilha: {e}")
        return None

def carregar_dados():
    sheet = conectar_gsheets()
    if sheet: return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

def salvar_registro(dados):
    sheet = conectar_gsheets()
    if sheet:
        sheet.append_row(dados)
        st.toast("✅ Aposta Salva!", icon="💰")
        st.cache_data.clear()
        st.rerun()

# --- NOVA FUNÇÃO: ATUALIZAR STATUS PELO CARD ---
def atualizar_status(indice_df, novo_resultado, lucro_calculado):
    sheet = conectar_gsheets()
    if sheet:
        # O índice do DataFrame começa em 0.
        # No Google Sheets: Linha 1 é cabeçalho.
        # Então índice 0 do DF = Linha 2 do Sheets.
        numero_linha = indice_df + 2 
        
        # Atualiza Coluna H (8) = Resultado e Coluna I (9) = Lucro_Real
        # Nota: Se você mudou a ordem das colunas, ajuste os números abaixo
        sheet.update_cell(numero_linha, 8, novo_resultado) # Coluna H
        sheet.update_cell(numero_linha, 9, lucro_calculado) # Coluna I
        
        st.toast(f"Aposta atualizada para {novo_resultado}!", icon="🔄")
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA PRINCIPAL ---
st.title("💼 Gestão de Banca Pro")

# 1. Dados e KPIs
df = carregar_dados()
banca_inicial = 100.00
saldo_atual = banca_inicial
lucro_total = 0.0

if not df.empty:
    for col in ['Lucro_Real', 'Valor_Entrada', 'Valor_Retorno']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    lucro_total = df['Lucro_Real'].sum()
    saldo_atual = banca_inicial + lucro_total
    
    # KPIs Topo
    c1, c2, c3 = st.columns(3)
    c1.metric("Banca Atual", f"R$ {saldo_atual:.2f}", delta=f"{lucro_total:.2f}")
    
    roi = (lucro_total / df['Valor_Entrada'].sum() * 100) if df['Valor_Entrada'].sum() > 0 else 0.0
    c2.metric("ROI", f"{roi:.2f}%")
    
    resolvidas = df[df['Resultado'].isin(['Green', 'Red'])]
    winrate = (len(resolvidas[resolvidas['Resultado']=='Green']) / len(resolvidas) * 100) if not resolvidas.empty else 0
    c3.metric("Winrate", f"{winrate:.1f}%")

st.divider()

# 2. Link SofaScore
col_btn, _ = st.columns([1, 1])
with col_btn:
    st.markdown(f'<a href="https://www.sofascore.com/pt/" target="_blank" class="link-btn">📊 Abrir SofaScore</a>', unsafe_allow_html=True)

st.divider()

# 3. Formulário de Registro (Expander para economizar espaço)
with st.expander("📝 Registrar Nova Entrada", expanded=False):
    with st.form("form_registro"):
        st.caption("💰 DADOS FINANCEIROS")
        cf1, cf2, cf3 = st.columns(3)
        valor_entrada = cf1.number_input("Entrada (R$)", min_value=0.0, value=20.0, step=1.0)
        valor_retorno = cf2.number_input("Retorno (R$)", min_value=0.0, value=28.0, step=1.0)
        
        odd_calc = 0.0
        if valor_entrada > 0: odd_calc = valor_retorno / valor_entrada
        cf3.write(f"**Odd: {odd_calc:.3f}**")

        st.caption("⚽ DADOS DO JOGO")
        cd1, cd2 = st.columns(2)
        liga_sel = cd1.selectbox("Liga", LIGAS_COMUNS)
        jogo_txt = cd2.text_input("Jogo", placeholder="Ex: Fla x Vasco")
        
        cm1, cm2 = st.columns(2)
        data_sel = cm1.date_input("Data", date.today())
        mercado_sel = cm2.selectbox("Mercado", MERCADOS_COMUNS)
        obs_txt = st.text_input("Obs")

        # Status inicial é sempre Pendente ao criar
        if st.form_submit_button("💾 Salvar Aposta"):
            if valor_entrada > 0 and jogo_txt:
                salvar_registro([
                    data_sel.strftime("%d/%m/%Y"), liga_sel, jogo_txt, mercado_sel,
                    valor_entrada, valor_retorno, f"{odd_calc:.3f}",
                    "Pendente", 0.0, obs_txt
                ])
            else:
                st.warning("Preencha dados obrigatórios.")

# 4. LISTA DE CARDS INTERATIVOS
st.subheader("📋 Minhas Apostas")

if not df.empty:
    tab_pendentes, tab_todos, tab_grafico = st.tabs(["⏳ Pendentes", "🗂️ Histórico", "📈 Gráfico"])
    
    # --- ABA PENDENTES (CARDS INTERATIVOS) ---
    with tab_pendentes:
        # Filtra e ordena (Pendentes antigos primeiro, ou novos primeiro, a seu gosto)
        df_pendentes = df[df['Resultado'] == 'Pendente'].sort_index(ascending=False)
        
        if df_pendentes.empty:
            st.info("Nenhuma aposta pendente. Bom trabalho!")
        
        for index, row in df_pendentes.iterrows():
            # Card Container
            with st.container(border=True):
                # Cabeçalho do Card
                col_topo1, col_topo2 = st.columns([3, 1])
                col_topo1.markdown(f"**⚽ {row['Jogo']}**")
                col_topo1.caption(f"{row['Liga']} • {row['Data']}")
                col_topo2.markdown(f"**R$ {row['Valor_Entrada']}**")
                
                st.text(f"M: {row['Mercado']} (@ {row['Odd_Calc']})")
                
                # Botões de Ação
                c_green, c_red, c_refund = st.columns(3)
                
                # Lógica: Green (Lucro = Retorno - Entrada), Red (Lucro = -Entrada)
                if c_green.button("✅ Green", key=f"g_{index}"):
                    lucro = row['Valor_Retorno'] - row['Valor_Entrada']
                    atualizar_status(index, "Green", lucro)
                
                if c_red.button("❌ Red", key=f"r_{index}"):
                    lucro = -row['Valor_Entrada']
                    atualizar_status(index, "Red", lucro)
                    
                if c_refund.button("🔄 Reembolso", key=f"re_{index}"):
                    atualizar_status(index, "Reembolso", 0.0)

    # --- ABA TODOS (HISTÓRICO GERAL) ---
    with tab_todos:
        # Mostra todos, ordenados do mais novo para o mais antigo
        for index, row in df.sort_index(ascending=False).iterrows():
            status = row['Resultado']
            
            # Define cor da borda lateral baseada no status
            cor_status = "gray"
            if status == "Green": cor_status = "green"
            elif status == "Red": cor_status = "red"
            elif status == "Pendente": cor_status = "orange"
            
            # Visual do Card Simples (Sem botões)
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{row['Jogo']}**")
                c1.caption(f"{row['Data']} | {row['Mercado']}")
                
                saldo_txt = f"R$ {row['Lucro_Real']:.2f}"
                if status == "Green": 
                    c2.success(saldo_txt)
                elif status == "Red": 
                    c2.error(saldo_txt)
                else:
                    c2.info(status)

    # --- ABA GRÁFICO ---
    with tab_grafico:
        df_g = df.copy()
        df_g['Saldo'] = banca_inicial + df_g['Lucro_Real'].cumsum()
        st.plotly_chart(px.line(df_g, y='Saldo', markers=True), use_container_width=True)
