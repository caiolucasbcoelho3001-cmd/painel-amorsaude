st.divider()

# =========================
# EXPORTAR PLANILHA FILTRADA
# =========================
st.subheader("📤 Exportar planilha filtrada")

# Cria CSV com todos os pacientes filtrados (não apenas a página atual)
csv_export = alvo.to_csv(index=False, encoding='utf-8-sig')

st.download_button(
    label="📥 Baixar lista filtrada (CSV)",
    data=csv_export,
    file_name=f"Pacientes_Alvo_{especialidade_sel}_{meses}meses.csv",
    mime="text/csv",
    help="Baixa um arquivo com os pacientes filtrados para disparos manuais."
)

st.caption("💡 Dica: o arquivo inclui Nome, CPF, Telefone, Data, Especialidade e Status. Ideal para importação em ferramentas de disparo manual.")
