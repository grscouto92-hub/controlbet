import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
# from datetime import date # Não está sendo usado, pode remover

# --- Configuração Simples ---
st.set_page_config(page_title="ProTips | Canal Oficial", page_icon="🦁", layout="centered")

# --- CSS para Estilo "Card" (CORRIGIDO) ---
st.markdown("""
<style>
    /* Remover padding excessivo */
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    
    /* Estilo dos Cards de Aposta */
    .tip-card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        color: #ffffff !important; /* <--- FORÇA O TEXTO BRANCO GERAL */
    }
    .tip-header {
        display: flex;
        justify-content: space-between;
        color: #aaaaaa; /* Cor cinza claro para o cabeçalho */
        font-size: 0.8rem;
        margin-bottom: 8px;
    }
    .tip-match {
        font-size: 1.1rem;
        font-weight: bold;
        color: #ffffff !important; /* <--- FORÇA O TÍTULO BRANCO */
        margin-bottom: 10px;
    }
    .tip-bet {
        background-color: #2b2b2b; /* Fundo um pouco mais claro para contraste */
        padding: 10px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #383838;
        color: #ffffff !important; /* <--- FORÇA O TEXTO DA APOSTA BRANCO */
    }
    .tip-odd {
        color: #00e676 !important; /* Verde Neon para a Odd */
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    /* Texto da Análise e Rodapé do Card */
    .tip-analysis, .tip-footer {
        color: #dddddd !important; /* Texto quase branco */
    }

    /* Status Colors */
    .status-green { border-left-color: #00e676 !important; }
    .status-red { border-left-color: #ff1744 !important; }
    .status-pending { border-left-color: #ff9100 !important; }
</style>
""", unsafe_allow_html=True)

# --- Conexão Google Sheets ---
# Usa o cache para não gastar cotas da API a cada F5 do usuário
@st.cache_data(ttl=60) 
def carregar_tips():
    try:
        # Verifica credenciais
        if "gcp_service_account" not in st.secrets:
            return None
        
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Abre a aba "Tips"
        sheet = client.open("ControlBET").worksheet("Tips")
        dados = sheet.get_all_records()
        return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"Erro ao carregar tips: {e}")
        return pd.DataFrame()

# --- Lógica Principal ---
def main():
    # 1. Cabeçalho (Sua Marca)
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.markdown("# 🦁")
    with col_title:
        st.markdown("### Mestre das Tips")
        st.caption("Análises profissionais de Futebol")

    st.divider()

    # 2. Estatísticas Rápidas (Banner)
    df = carregar_tips()
    
    if not df.empty:
        # Filtra apenas Green e Red para estatística
        df_res = df[df['Status'].isin(['Green', 'Red'])]
        greens = len(df_res[df_res['Status'] == 'Green'])
        total = len(df_res)
        winrate = (greens / total * 100) if total > 0 else 0
        
        # Exibe métricas no topo
        m1, m2, m3 = st.columns(3)
        m1.metric("Winrate", f"{winrate:.0f}%")
        m2.metric("Greens", f"{greens}")
        m3.metric("Total Calls", f"{total}")
    
    st.markdown("### 🔥 Palpites do Dia")
    
    # 3. Listagem das Tips
    if df.empty:
        st.info("Aguardando novas entradas...")
    else:
        # Ordena: Mostra as últimas adicionadas primeiro
        df = df.iloc[::-1]

        for i, row in df.iterrows():
            status = row['Status']
            
            # Define classe CSS baseada no status
            css_class = "status-pending"
            icone = "⏳"
            if status == "Green": 
                css_class = "status-green"
                icone = "✅ Green"
            elif status == "Red": 
                css_class = "status-red"
                icone = "❌ Red"

            # HTML do Card (COM NOVAS CLASSES DE COR)
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

    # 4. Rodapé
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px;">
        ⚠️ Aposte com responsabilidade. +18.<br>
        <a href="https://t.me/seulink" style="color: #ff4b4b; text-decoration: none;">Entrar no Grupo VIP Telegram</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
