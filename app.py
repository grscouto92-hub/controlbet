import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuração da Página ---
st.set_page_config(page_title="GuiTips | Canal Oficial", page_icon="🦁", layout="centered")

# --- 2. Tentativa de Importar Plotly ---
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# --- 3. CSS Otimizado (Sem classes que causam bugs) ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* CARD PRINCIPAL */
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
        display: flex; justify-content: space-between;
        color: #aaaaaa; font-size: 0.8rem; margin-bottom: 8px;
    }
    
    .tip-match {
        font-size: 1.1rem; font-weight: bold;
        color: #ffffff !important; margin-bottom: 10px;
    }
    
    .tip-bet {
        background-color: #2b2b2b;
        padding: 10px; border-radius: 8px;
        display: flex; justify-content: space-between; align-items: center;
        border: 1px solid #383838;
        color: #ffffff !important;
    }
    
    .tip-odd {
        color: #00e676 !important;
        font-weight: bold; font-size: 1.1rem;
    }
    
    /* Badge de Confiança */
    .tip-confidence {
        font-size: 0.75rem; color: #ffd700;
        background-color: #333333; padding: 4px 8px;
        border-radius: 4px; margin-right: 10px;
        font-weight: bold; display: inline-flex; align-items: center;
        border: 1px solid #555;
    }

    .tip-analysis { margin-top: 12px; font-size: 0.9rem; color: #dddddd !important; }
    .tip-footer { margin-top: 10px; font-size: 0.85rem; text-align: right; font-weight: bold; color: #dddddd !important; }
    
    /* Botão CTA Lateral */
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(0, 230, 118, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); } }
    .cta-button { 
        display: block; width: 100%; padding: 12px; 
        background-color: #00e676; color: #000 !important; 
        text-align: center; font-weight: bold; text-decoration: none; 
        border-radius: 8px; margin-bottom: 20px; 
        animation: pulse 2s infinite; text-transform: uppercase; letter-spacing: 1px; 
    }

    /* Cores de Status */
    .status-green { border-left-color: #00e676 !important; }
    .status-red { border-left-color: #ff1744 !important; }
    .status-pending { border-left-color: #ff9100 !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. Funções Auxiliares ---
def limpar_numero(valor):
    if isinstance(valor, (int, float)): return valor
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_resultado(row):
    status = str(row['Status']).strip().title()
    odd = limpar_numero(row['Odd'])
    unidades = limpar_numero(row['Unidades'])
    if status == 'Green': return (odd - 1) * unidades
    elif status == 'Red': return -unidades
    else: return 0.0

def exibir_card(row):
    status = str(row['Status']).strip().title()
    confianca = str(row.get('Confiança', '')).strip()
    
    css_class, icone = "status-pending", "⏳ Pendente"
    if status == "Green": css_class, icone = "status-green", "✅ Green"
    elif status == "Red": css_class, icone = "status-red", "❌ Red"
    elif status == "Anulada": icone = "🔄 Anulada"

    # Monta o HTML da confiança se existir
    html_confianca = f'<span class="tip-confidence">🎯 {confianca}</span>' if confianca else ""

    # HTML Simplificado (Sem textwrap e com formatação direta para evitar erro visual)
    st.markdown(f"""
<div class="tip-card {css_class}">
    <div class="tip-header">
        <span>⚽ {row['Liga']}</span>
        <span>{row['Data']} • {row['Hora']}</span>
    </div>
    <div class="tip-match">{row['Jogo']}</div>
    <div class="tip-bet">
        <div style="display: flex; flex-direction: column;">
            <span style="font-weight: 500;">{row['Aposta']}</span>
        </div>
        <div style="display: flex; align-items: center;">
            {html_confianca}
            <span class="tip-odd">@{row['Odd']}</span>
        </div>
    </div>
    <div class="tip-analysis">
        💡 <i>"{row['Analise']}"</i>
    </div>
    <div class="tip-footer">
        {icone} | Unidades: {row['Unidades']}
    </div>
</div>
""", unsafe_allow_html=True)

# --- 5. Conexão Google Sheets ---
@st.cache_data(ttl=60) 
def carregar_tips():
    try:
        if "gcp_service_account" not in st.secrets: return pd.DataFrame()
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("ControlBET").worksheet("Tips")
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        if not df.empty:
            df['Odd_Num'] = df['Odd'].apply(limpar_numero)
            df['Unid_Num'] = df['Unidades'].apply(limpar_numero)
            df['Lucro'] = df.apply(calcular_resultado, axis=1)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return pd.DataFrame()

# --- 6. Lógica Principal ---
def main():
    if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 0

    col_logo, col_title = st.columns([1, 4])
    with col_logo: st.markdown("# 🦁")
    with col_title:
        st.markdown("### GuiTips")
        st.caption("Análises profissionais de Futebol")

    if not HAS_PLOTLY:
        st.warning("⚠️ Plotly não instalado.")

    df = carregar_tips()
    if df.empty:
        st.info("Carregando dados...")
        return

    # Sidebar
    with st.sidebar:
        st.markdown("""<a href="https://t.me/seulink" target="_blank" class="cta-button">🚀 GRUPO VIP (Entrar)</a>""", unsafe_allow_html=True)
        st.divider()
        st.header("🔍 Filtros")
        busca_time = st.text_input("Buscar Time", placeholder="Ex: Flamengo")
        filtro_liga = st.multiselect("Filtrar por Liga", df['Liga'].unique().tolist())
        
        if filtro_liga: df = df[df['Liga'].isin(filtro_liga)]
        if busca_time: df = df[df['Jogo'].str.contains(busca_time, case=False, na=False)]

    # Estatísticas
    df_res = df[df['Status'].isin(['Green', 'Red'])]
    greens = len(df_res[df_res['Status'] == 'Green'])
    total = len(df_res)
    winrate = (greens / total * 100) if total > 0 else 0
    lucro = df_res['Lucro'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Winrate", f"{winrate:.0f}%")
    c2.metric("Greens", f"{greens}")
    c3.metric("Final.", f"{total}")
    c4.metric("Lucro", f"{lucro:+.1f}")

    st.divider()

    aba_jogos, aba_historico = st.tabs(["🔥 Jogos Abertos", "📊 Histórico"])
    
    df_pendentes = df[~df['Status'].isin(['Green', 'Red', 'Anulada'])].copy() # .copy() evita aviso de SettingWithCopy
    df_historico = df[df['Status'].isin(['Green', 'Red', 'Anulada'])]

    # --- ABA 1: Jogos Abertos (COM ORDENAÇÃO POR DATA) ---
    with aba_jogos:
        st.markdown("##### Próximas Entradas")
        if df_pendentes.empty:
            st.info("Nenhuma entrada pendente.")
        else:
            # 1. Cria coluna datetime temporária para ordenar corretamente
            try:
                # Junta Data e Hora para criar um objeto de data que o Python entende
                df_pendentes['Data_Hora_Sort'] = pd.to_datetime(
                    df_pendentes['Data'] + ' ' + df_pendentes['Hora'], 
                    format='%d/%m/%Y %H:%M', 
                    dayfirst=True, 
                    errors='coerce'
                )
                # 2. Ordena Ascendente (Do mais antigo/próximo para o futuro)
                df_pendentes = df_pendentes.sort_values('Data_Hora_Sort', ascending=True)
            except Exception as e:
                # Se falhar a conversão, usa a ordem padrão invertida
                df_pendentes = df_pendentes.iloc[::-1]

            # 3. Exibe os cards já ordenados
            for i, row in df_pendentes.iterrows():
                exibir_card(row)

    # --- ABA 2: Histórico ---
    with aba_historico:
        if HAS_PLOTLY and not df_res.empty:
            try:
                df_res['Data_Dt'] = pd.to_datetime(df_res['Data'], dayfirst=True, errors='coerce')
                df_chart = df_res.dropna(subset=['Data_Dt']).copy()
                df_diario = df_chart.groupby('Data_Dt')['Lucro'].sum().reset_index().sort_values('Data_Dt')
                df_diario['Acumulado'] = df_diario['Lucro'].cumsum()
                
                fig = px.line(df_diario, x='Data_Dt', y='Acumulado', markers=True)
                fig.update_traces(line_color='#00e676', line_width=3)
                fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0), height=250, xaxis_title=None, yaxis_title="Lucro (U)")
                st.markdown("##### 📈 Evolução")
                st.plotly_chart(fig, use_container_width=True)
            except: pass

        st.markdown("##### Últimos Resultados")
        if df_historico.empty:
            st.info("Nenhum histórico disponível.")
        else:
            df_historico = df_historico.iloc[::-1]
            ITENS_POR_PAGINA = 10
            total_paginas = max(1, (len(df_historico) - 1) // ITENS_POR_PAGINA + 1)
            
            if st.session_state.pagina_atual >= total_paginas: st.session_state.pagina_atual = total_paginas - 1
            if st.session_state.pagina_atual < 0: st.session_state.pagina_atual = 0
            
            inicio = st.session_state.pagina_atual * ITENS_POR_PAGINA
            df_pagina = df_historico.iloc[inicio:inicio + ITENS_POR_PAGINA]
            
            for i, row in df_pagina.iterrows(): exibir_card(row)
            
            if total_paginas > 1:
                st.markdown("---")
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1: 
                    if st.button("⬅️", key="prev"): 
                        st.session_state.pagina_atual -= 1
                        st.rerun()
                with c2: st.markdown(f"<div style='text-align:center; padding-top:5px'>{st.session_state.pagina_atual + 1}/{total_paginas}</div>", unsafe_allow_html=True)
                with c3: 
                    if st.button("➡️", key="next"): 
                        st.session_state.pagina_atual += 1
                        st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666; font-size: 12px;'>⚠️ Aposte com responsabilidade. +18.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
