# ... (Mantenha suas funções de conexão e salvar_registro)

# --- ABA PENDENTES (Mantida como Cards) ---
with tab_pend:
    df_pendentes = df[df['Resultado'] == 'Pendente'].copy()
    if df_pendentes.empty:
        st.info("Nenhuma aposta pendente.")
    else:
        for index, row in df_pendentes.sort_index(ascending=False).iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['Jogo']}** | <span style='color:gray'>{row['Mercado']}</span>", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                c1.caption(f"💰 R$ {row['Valor_Entrada']}")
                c2.caption(f"🎯 R$ {row['Valor_Retorno']}")
                c3.caption(f"📈 {row['Odd_Calc']}")

                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("WIN", key=f"w_{index}", use_container_width=True):
                        lucro = row['Valor_Retorno'] - row['Valor_Entrada']
                        atualizar_status(index, "Green", lucro)
                with b2:
                    if st.button("LOSS", key=f"l_{index}", use_container_width=True):
                        atualizar_status(index, "Red", -row['Valor_Entrada'])
                with b3:
                    if st.button("NULA", key=f"n_{index}", use_container_width=True):
                        atualizar_status(index, "Reembolso", 0.0)

# --- ABA HISTÓRICO (AGORA EM CARDS) ---
with tab_hist:
    df_resolvidas = df[df['Resultado'] != 'Pendente'].copy()
    
    if df_resolvidas.empty:
        st.info("Nenhum histórico disponível.")
    else:
        # Gráfico de evolução no topo
        df_resolvidas['Evolução'] = banca_inicial + df_resolvidas['Lucro_Real'].cumsum()
        st.plotly_chart(px.line(df_resolvidas, y='Evolução', height=180), use_container_width=True)
        
        st.markdown("### Registros Recentes")
        
        # Inverter para mostrar os mais novos primeiro
        for index, row in df_resolvidas.sort_index(ascending=False).iterrows():
            # Define a cor da borda ou do texto baseada no resultado
            cor = "#28a745" if row['Resultado'] == "Green" else "#dc3545" if row['Resultado'] == "Red" else "#6c757d"
            emoji = "✅" if row['Resultado'] == "Green" else "❌" if row['Resultado'] == "Red" else "🔄"
            
            with st.container(border=True):
                # Cabeçalho do Card: Jogo e Resultado
                st.markdown(f"{emoji} **{row['Jogo']}**")
                
                # Detalhes em colunas
                col1, col2, col3 = st.columns([1.5, 1, 0.5])
                
                with col1:
                    st.caption(f"📅 {row['Data']} | {row['Mercado']}")
                    st.markdown(f"<span style='color:{cor}; font-weight:bold'>Lucro: R$ {row['Lucro_Real']:.2f}</span>", unsafe_allow_html=True)
                
                with col2:
                    # Informação de Odd no histórico
                    st.caption(f"Odd: {row['Odd_Calc']}")
                    st.caption(f"Liga: {row['Liga']}")
                
                with col3:
                    # Botão para apagar se algo estiver errado
                    if st.button("🗑️", key=f"del_h_{index}", help="Excluir este registro"):
                        deletar_registro(index)

# --- FUNÇÃO DE DELETAR (Adicione ao topo do código) ---
def deletar_registro(indice_df):
    sheet = conectar_gsheets()
    if sheet:
        # O gspread usa índice 1, e o header é a linha 1. Logo, df index 0 é linha 2.
        linha_real = indice_df + 2
        sheet.delete_rows(linha_real)
        st.toast("Registro removido!", icon="🗑️")
        st.cache_data.clear()
        st.rerun()
