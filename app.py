import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import plotly.graph_objects as go

# --- Configuração da Página ---
st.set_page_config(page_title="GuiTips | Canal Oficial", page_icon="🦁", layout="centered")

# --- CSS Personalizado ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    
    /* Estilo dos Cards */
    .tip-card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        color: #ffffff !important;
    }
    .tip-header {
        display: flex;
        justify-content: space-between;
        color: #aaaaaa;
        font-size: 0.8rem;
        margin-bottom: 8px;
    }
    .tip-match {
        font-size: 1.1rem;
        font-weight: bold;
        color: #ffffff !important;
        margin-bottom: 10px;
    }
    .tip-bet {
        background-color: #2b2b2b;
        padding: 10px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #383838;
        color: #ffffff !important;
    }
    .tip-odd {
        color: #00e676 !important;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .tip-analysis { color: #dddddd !important; }
    .tip-footer { color: #dddddd !important; }

    /* Cores de Status */
    .status-green { border-left-color: #00e676 !important; }
    .status-red { border-left-color: #ff1744 !important; }
    .status-pending { border-left-color: #ff9100 !important; }
    
    /* Ajuste nas abas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #0e1117; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #262730; color: #ff4b4b !important; }
</style>
""", unsafe_allow_html=True)

# --- Funções Auxiliares ---
def limpar_numero(valor):
    """Converte strings como '1,50' ou 'R$ 1.50' para float 1.50"""
    if isinstance(valor, (int, float)):
        return valor
    try:
        return float(str(valor).replace(',', '.'))
    except:
        return 0.0

def calcular_resultado(row):
    """Calcula o lucro/prejuízo da linha"""
    status = str(row['Status']).strip().title()
    odd = limpar_numero(row['Odd'])
    unidades = limpar_numero(row['Unidades'])
    
    if status == 'Green':
        return (odd - 1) * unidades
    elif status == 'Red':
        return -unidades
    else:
        return 0.0

def exibir_card(row):
    """Gera o HTML do card para uma linha específica"""
    status = str(row['Status']).strip().title()
    
    css_class = "status-pending"
    icone = "⏳ Pendente"
    
    if status == "Green": 
        css_class = "status-green"
        icone = "✅ Green"
    elif status == "Red": 
        css_class = "status-red"
        icone = "❌ Red"
    elif status == "Anulada":
        icone = "🔄 Anulada"

    html_card = f"""
    <div class="tip-card {css_class}">
        <div class="tip-header">
            <span>⚽ {row['Liga']}</span>
            <span>{row['Data']} • {row['Hora']}</span>
        </div>
        <div class="tip-match">
            {row['Jogo']}
        </div>
        <div class="tip-bet">
            <span>{row['Aposta']}</span>
            <span class="tip-odd">@{row['Odd']}</span>
        </div>
        <div class="tip-analysis" style="margin-top: 12px; font-size: 0.9rem;">
            💡 <i>"{row['Analise']}"</i>
        </div>
        <div class="tip-footer" style="margin-top: 10px; font-size: 0.85rem; text-align: right; font-weight: bold;">
            {icone} | Unidades: {row['Unidades']}
        </div>
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)

# --- Conexão Google Sheets ---
@st.cache_data(ttl=60) 
def carregar_tips():
    try:
        if "gcp_service_account" not in st.secrets:
            return pd.DataFrame()
        
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("ControlBET").worksheet("Tips")
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        
        # Pré-processamento dos dados
        if not df.empty:
            df['Odd_Num'] = df['Odd'].apply(limpar_numero)
            df['Unid_Num'] = df['Unidades'].apply(limpar_numero)
            df['Lucro'] = df.apply(calcular_resultado, axis=1)
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar tips: {e}")
        return pd.DataFrame()

# --- Lógica Principal ---
def main():
    # 1. Cabeçalho
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.markdown("# 🦁")
    with col_title:
        st.markdown("### GuiTips")
        st.caption("Análises profissionais de Futebol")

    # Carrega dados
    df = carregar_tips()
    
    if df.empty:
        st.warning("Não foi possível carregar os dados ou a planilha está vazia.")
        return

    # --- SIDEBAR (Filtros) ---
    with st.sidebar:
        st.header("Filtros")
        todas_ligas = df['Liga'].unique().tolist()
        filtro_liga = st.multiselect("Selecione a Liga", todas_ligas)
        
        if filtro_liga:
            df = df[df['Liga'].isin(filtro_liga)]

    # --- ESTATÍSTICAS DO TOPO ---
    df_res = df[df['Status'].isin(['Green', 'Red'])]
    
    greens = len(df_res[df_res['Status'] == 'Green'])
    total_resolvidas = len(df_res)
    winrate = (greens / total_resolvidas * 100) if total_resolvidas > 0 else 0
    lucro_total = df_res['Lucro'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Winrate", f"{winrate:.0f}%")
    c2.metric("Greens", f"{greens}")
    c3.metric("Finalizadas", f"{total_resolvidas}")
    c4.metric("Lucro (U)", f"{lucro_total:+.2f}")

    st.divider()

    # --- ABAS DE NAVEGAÇÃO ---
    aba_jogos, aba_historico = st.tabs(["🔥 Jogos Abertos", "📊 Histórico e Gráficos"])

    # Separa os DataFrames
    df_pendentes = df[~df['Status'].isin(['Green', 'Red', 'Anulada'])]
    df_historico = df[df['Status'].isin(['Green', 'Red', 'Anulada'])]

    # --- ABA 1: JOGOS ABERTOS ---
    with aba_jogos:
        st.markdown("##### Próximas Entradas")
        if df_pendentes.empty:
            st.info("Nenhuma entrada pendente no momento.")
        else:
            df_pendentes = df_pendentes.iloc[::-1]
            for i, row in df_pendentes.iterrows():
                exibir_card(row)

    # --- ABA 2: HISTÓRICO ---
    with aba_historico:
        # Gráfico Plotly
        if not df_res.empty:
            st.markdown("##### 📈 Evolução da Banca (Lucro Acumulado)")
            
            # Preparação dos Dados para o Gráfico
            df_chart = df_res.copy()
            
            # Tenta converter Data para formato datetime
            try:
                df_chart['Data_Dt'] = pd.to_datetime(df_chart['Data'], dayfirst=True, errors='coerce')
            except:
                df_chart['Data_Dt'] = df_chart['Data']

            # Remove datas inválidas (NaT) se a conversão falhou em algumas linhas
            df_chart = df_chart.dropna(subset=['Data_Dt'])

            # Agrupamento por Dia (Soma o lucro de todas as tips do mesmo dia)
            df_diario = df_chart.groupby('Data_Dt')['Lucro'].sum().reset_index()
            df_diario = df_diario.sort_values('Data_Dt')
            
            # Cria o acumulado
            df_diario['Acumulado'] = df_diario['Lucro'].cumsum()

            # Criação do Gráfico
            fig = px.line(
                df_diario, 
                x='Data_Dt', 
                y='Acumulado', 
                markers=True,
                title=None
            )
            
            # Estilização
            fig.update_traces(line_color='#00e676', line_width=3, marker_size=8)
            fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)

            fig.update_layout(
                xaxis_title=None, # Remove rótulo X para limpar
                yaxis_title="Unidades (U)",
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                hovermode="x unified",
                margin=dict(l=0, r=0, t=10, b=0),
                height=350
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

        st.markdown("##### Últimos Resultados")
        if df_historico.empty:
            st.info("Nenhum histórico disponível com os filtros atuais.")
        else:
            df_historico = df_historico.iloc[::-1]
            for i, row in df_historico.iterrows():
                exibir_card(row)

    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px;">
        ⚠️ Aposte com responsabilidade. +18.<br>
        <a href="#" style="color: #ff4b4b; text-decoration: none;">Entrar no Grupo VIP Telegram</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
