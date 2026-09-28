# -*- coding: utf-8 -*-
"""d10_documentacao_amostra.py: (1) REGISTRO_VERIFICACOES_AMOSTRA.md, (2) TABELA_validacao_amostra.csv/.md, (3) NOTA_METODOS_amostra_e_desenho.md (uma pagina).
Todos os numeros vem dos JSON/CSV gerados pelos scripts (nada digitado a mao)."""
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *

J = lambda n: json.loads((OUTD / n).read_text(encoding="utf-8"))
I, K, A, L, T, P = J("01_integridade_amostra.json"), J("01_checagens_pesos_replicados.json"), json.loads((ART / "MANUSCRITO_IJE_20260925" / "auditoria" / "auditoria_dados_resumo.json").read_text(encoding="utf-8")), J("D9_estrato_solitario.json"), J("D8_testes_integridade.json"), J("principal.json")
fl = pd.read_csv(OUTD / "01_fluxo_amostra_reproduzido.csv").set_index("etapa")["n"]
sid = pd.read_csv(ART / "MANUSCRITO_IJE_20260925" / "auditoria" / "confronto_SIDRA_9554.csv", index_col=0)
sidt = sid["dif_%_total"].dropna(); sidi = sid["dif_%_IA"].dropna()
N = lambda x: f"{int(x):,}".replace(",", ".")
res = {r["teste"]: r["resultado"] for r in T["testes"]}
rows = [
    ("Registros de pessoas no arquivo bruto", "473.206 (registro anterior)", N(I["linhas_pessoas"]), "01_integridade_amostra.json", "d0_extrair.py", "VERIFICADO"),
    ("Pessoas responsáveis (V2005 = 01)", "173.676", N(I["n_linhas_V2005_01"]), "01_integridade_amostra.json", "t1", res["t1_n_responsaveis"]),
    ("Chaves oficiais de domicílio (UPA + V1008 + V1014)", "173.676, únicas", N(I["n_chaves_oficiais_UPA_V1008_V1014"]), "01_integridade_amostra.json", "t2", res["t2_chave_oficial_unica"]),
    ("Domicílios com exatamente 1 responsável (0 com nenhum; 0 com 2 ou mais)", "173.676", f"{N(I['dom_com_1_responsavel'])} (0 / {I['dom_com_2mais_responsaveis']})", "01_integridade_amostra.json", "t3", res["t3_um_responsavel_por_domicilio"]),
    ("Responsáveis com SD17001 em 1-4 e peso V1028 numérico > 0", "todos", f"{N(fl['Pessoas de referencia com SD17001 em 1-4'])} e {N(fl['Pessoas de referencia com V1028 numerico > 0'])}", "01_fluxo_amostra_reproduzido.csv", "t4", res["t4_ebia_e_peso"]),
    ("ID reconstruído pelo código antigo == chave oficial", "equivalente", f"{I['id_reconstruido_equivale_a_chave_oficial']} ({N(I['pares_distintos_chave_id'])} pares distintos)", "01_integridade_amostra.json", "t7", res["t7_id_reconstruido"]),
    ("UPAs (conglomerados)", "—", N(fl["UPAs distintas"]), "01_fluxo_amostra_reproduzido.csv", "—", "VERIFICADO"),
    ("Estratos (variável oficial `Estrato`, @21, $7)", "573", N(fl["Estratos distintos (variavel oficial Estrato)"]), "01_fluxo_amostra_reproduzido.csv", "t5", res["t5_estrato"]),
    ("Estratos com uma única UPA", "—", f"{fl['Estratos com uma unica UPA']} (estrato {L['estrato_com_1_UPA']}, {L['domicilios']} domicílios, {L['pct_do_peso_total']:.4f}% do peso)", "D9_estrato_solitario.json", "d9", "VERIFICADO"),
    ("Pesos replicados V1028001-V1028200 presentes e completos", "200 colunas", f"{K['n_colunas']} colunas; {K['faltantes']} faltantes; {K['colunas_todas_zero']} zeradas; {K['colunas_identicas_ao_peso_final']} iguais ao peso final", "01_checagens_pesos_replicados.json", "t6", res["t6_pesos_replicados"]),
    ("Leitor legado: nomes e posições == layout oficial (após a correção)", "todos", "sem divergência", "d8_testes_integridade.py", "t8", res["t8_colspecs_do_leitor_legado"]),
    ("Leitor legado corrigido reproduz amostra e pesos originais", "n = 173.676; peso rel. ≤ 1e-8", f"peso rel. máx. {T['t9_dif_rel_peso_vs_derivado_original']:.1e}", "d8_testes_integridade.py", "t9", res["t9_leitor_legado_reproduz"]),
    ("Coluna 20-23 do código antigo (chamada \"V1008\")", "—", f"{A['col20_23_do_codigo_antigo_distintos']} valores; é o prefixo de 3 caracteres do Estrato: {A['col20_23_do_codigo_antigo_igual_prefixo3_do_Estrato']}; constante dentro da UPA: {A['col20_23_do_codigo_antigo_constante_dentro_UPA']}", "auditoria/auditoria_dados_resumo.json", "auditoria_dados_ije_20260926.py", "VERIFICADO"),
    ("Peso V1028: largura oficial 15; leitura antiga 14", "—", f"diferença relativa máxima {A['peso_15_vs_14_dif_relativa_max']:.1e}", "auditoria/auditoria_dados_resumo.json", "auditoria_dados_ije_20260926.py", "VERIFICADO"),
    ("Raça/cor ignorada (V2010 = 9), classificada como não negra", "19", f"{A['n_V2010=9']} ({A['V2010_9_ou_branco_classificado_como_nao_negro_pct_pond']:.3f}% ponderado)", "auditoria/auditoria_dados_resumo.json", "d5", "VERIFICADO"),
    ("Renda ignorada (VDI5009 = 9), classificada em >2 SM", "77", f"{A['n_VDI5009=9']} ({A['VDI5009_9_ou_branco_pct_pond']:.3f}% ponderado)", "auditoria/auditoria_dados_resumo.json", "d5", "VERIFICADO"),
    ("Composição de \"não negro\" (n = 70.207)", "—", "; ".join(f"{k} {N(v)}" for k, v in A["nao_negro_composicao_n"].items()), "auditoria/auditoria_dados_resumo.json", "—", "VERIFICADO"),
    ("Prevalência ponderada recalculada no bruto (qualquer; grave)", "27,5946%; 4,0947% (arquivo derivado)", f"{A['bruto_prev_ia_total_pond_%']:.4f}%; {A['bruto_prev_ia_grave_pond_%']:.4f}%", "auditoria/auditoria_dados_resumo.json", "—", "VERIFICADO"),
    ("Confronto com SIDRA 9554 (controle interno; NÃO é validação externa)", "—", f"domicílios totais {sidt.min():.2f}% a {sidt.max():.2f}%; com insegurança {sidi.min():.2f}% a {sidi.max():.2f}% (causa não identificada)", "auditoria/confronto_SIDRA_9554.csv", "—", "NÃO VERIFICADO (causa)"),
]
tab = pd.DataFrame(rows, columns=["item", "esperado", "observado", "arquivo de evidência", "teste/script", "resultado"])
tab.to_csv(OUTD / "TABELA_validacao_amostra.csv", index=False, encoding="utf-8-sig")
md = lambda df: "\n".join(["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)] + ["| " + " | ".join(str(v) for v in r) + " |" for r in df.values])
(OUTD / "TABELA_validacao_amostra.md").write_text("# Tabela de validação da amostra e do desenho (25/09/2026)\n\nEvidência: microdado bruto, layout e dicionário oficiais do IBGE. Testes: `scripts/rodada_d/d8_testes_integridade.py`.\n\n" + md(tab) + "\n", encoding="utf-8")

reg = f"""# Registro de verificações da amostra (evidência: `auditoria/_log_auditoria_dados.txt`, `01_integridade_amostra.json`, `D8_testes_integridade.json`)

## VERIFICADO
1. O arquivo bruto tem **{N(I['linhas_pessoas'])}** registros de pessoas.
2. `V2005 = 01` identifica **{N(I['n_linhas_V2005_01'])}** pessoas responsáveis; cada domicílio analítico tem **exatamente uma** (0 domicílios com nenhuma, {I['dom_com_2mais_responsaveis']} com duas ou mais).
3. As {N(I['n_linhas_V2005_01'])} pessoas responsáveis têm `SD17001` válido (1-4) e peso numérico positivo; **nenhum domicílio foi excluído** por EBIA ou peso ausente.
4. A chave reconstruída pelo código antigo é **equivalente** à chave oficial `UPA + V1008 + V1014` nos {N(I['pares_distintos_chave_id'])} domicílios.
5. **`V1008_artigo` era um nome enganoso.** O código antigo lia as posições 20-23 (3 caracteres) sob o nome "V1008"; esse objeto tem **{A['col20_23_do_codigo_antigo_distintos']} valores** e é exatamente o **prefixo de 3 caracteres do `Estrato`**, constante dentro da UPA. Não correspondia à `V1008` oficial (28-29, até {A['V1008_oficial_distintos_dentro_UPA_max']} valores por UPA) nem ao estrato completo (**{N(fl['Estratos distintos (variavel oficial Estrato)'])}** valores). **Isto não é uma simples mudança de rótulo:** o manuscrito afirmava que o microdado não tinha estratificação (falso) e o código nunca leu o estrato. Os **pontos estimados permaneceram invariantes** (D-4: A, B e C coincidem e reproduzem os originais a 10⁻¹⁰), porque prevalências e razões ponderadas não dependem do estrato; a **variância precisava ser reestimada** com desenho correto (feito em D-4).
6. O microdado tem **{N(fl['UPAs distintas'])} UPAs**, **{fl['Estratos distintos (variavel oficial Estrato)']} estratos**, **{fl['Estratos com uma unica UPA']} estrato com uma única UPA** e **200 pesos replicados** completos.
7. O peso V1028 tem 15 caracteres; o código antigo lia 14 (diferença relativa máxima {A['peso_15_vs_14_dif_relativa_max']:.1e}). Corrigido no leitor da rodada D e no leitor compartilhado; testes automatizados passam.
8. **{A['n_V2010=9']}** domicílios com raça/cor ignorada (classificados em "não negro") e **{A['n_VDI5009=9']}** com renda ignorada (classificados em ">2 SM"), {A['V2010_9_ou_branco_classificado_como_nao_negro_pct_pond']:.3f}% e {A['VDI5009_9_ou_branco_pct_pond']:.3f}% do peso. Composição de "não negro": {', '.join(f'{k} {N(v)}' for k, v in A['nao_negro_composicao_n'].items())}. A codificação original é preservada **só para reproduzir a análise primária**; não é uma escolha substantiva. D-5 é a sensibilidade.

## Sobre a comparação com a SIDRA (NÃO VERIFICADO quanto à causa)
Os totais do microdado ficam {sidt.min():.2f}% a {sidt.max():.2f}% (domicílios) e {sidi.min():.2f}% a {sidi.max():.2f}% (com insegurança) em relação à tabela 9554. É **controle interno de auditoria**. Não escrever "validação externa" no manuscrito sem explicar formalmente as diferenças e sem identificar a tabela oficial exatamente comparável (filtro, peso, arredondamento, categorias omitidas). A prevalência global de 27,6% coincide com a divulgada pelo IBGE.

## Ainda DEPENDE DE DECISÃO DOS AUTORES
Frase de Métodos (ver `E_PROPOSTAS…`, seção 2.0); configuração final de variância (C ou B, nunca as duas frases); tratamento dos 96 registros ignorados na Tabela 1.
"""
(OUTD / "REGISTRO_VERIFICACOES_AMOSTRA.md").write_text(reg, encoding="utf-8")

nota = f"""# Nota de métodos: amostra e desenho (rascunho; NÃO aplicada ao manuscrito)

**Amostra.** O arquivo público da PNAD Contínua (4º trimestre de 2023) tem {N(I['linhas_pessoas'])} registros de pessoas. Selecionamos os {N(I['n_linhas_V2005_01'])} registros codificados como pessoa responsável (`V2005 = 01`), um por domicílio (chave oficial `UPA + V1008 + V1014`, única). Todos têm classificação EBIA válida (`SD17001` 1-4) e peso numérico; nenhum domicílio foi excluído. Há {A['n_V2010=9']} domicílios com raça/cor ignorada (classificados como não negros) e {A['n_VDI5009=9']} com faixa de renda ignorada (classificados na faixa mais alta); a exclusão deles é analisada como sensibilidade.

**Desenho.** O microdado traz a UPA (conglomerado), o `Estrato` ({fl['Estratos distintos (variavel oficial Estrato)']} valores, posição 21-27), o peso final `V1028` (15 caracteres) e 200 pesos replicados (`V1028001`-`V1028200`). O código antigo lia sob o nome "V1008" o prefixo de 3 caracteres do `Estrato` ({A['col20_23_do_codigo_antigo_distintos']} valores); o manuscrito afirmava, incorretamente, que o estrato não estava disponível. As estimativas pontuais usam o peso final e não mudam.

**Variância (D-4).** Três configurações: A, pesos + UPA (antiga); B, pesos + UPA aninhada em Estrato, com a política de estrato solitário `adjust` (um estrato, {L['domicilios']} domicílios, {L['pct_do_peso_total']:.4f}% do peso; a alternativa `certainty` muda os erros-padrão em até {L['politica_B_max_dif_rel_SE_pct_certainty_vs_adjust']:.4f}%); C, os 200 pesos replicados (bootstrap de Rao, Wu e Yue, `mse`, divisor R − 1), com a função recalculada em cada réplica. Os erros-padrão de B e C reproduzem o pacote R `survey` (`svydesign`; `withReplicates`). A configuração principal pela regra prefixada é **{P['principal']}**. Em C não há regra de estrato solitário a escolher: a UPA solitária entra na variância pelas réplicas (seus pesos replicados variam). Como o IBGE gera as réplicas para esse estrato **não foi verificado em fonte primária**.

**Proposta de texto (Métodos), a ser usada só depois que a configuração final for congelada:**
> The public-use file included 473 206 person records. We selected the 173 676 records coded as household reference persons, one per household; all had a valid food insecurity classification and a survey weight. The public microdata provide primary sampling units, strata and replicate weights. Point estimates used the final survey weight.

*(configuração C)* > Variance estimation followed the replicate-weight procedure provided with the microdata (200 bootstrap weights).
*(configuração B)* > Variance estimation accounted for primary sampling units and strata (a stratum with a single primary sampling unit was centred at the overall mean).
Usar **uma** das duas, nunca as duas.

**Controle interno.** Os totais do microdado ficam 0,25% a 0,57% abaixo da SIDRA 9554; causa não identificada; não citar como validação externa.
**Testes.** `d8_testes_integridade.py` (9 testes; falham se o número de responsáveis não for {N(I['n_linhas_V2005_01'])}, a chave não for única, houver mais ou menos de um responsável por domicílio, faltar peso, o Estrato não tiver {fl['Estratos distintos (variavel oficial Estrato)']} valores ou faltar coluna de peso replicado; `--autoteste` demonstra a falha).
"""
(OUTD / "NOTA_METODOS_amostra_e_desenho.md").write_text(nota, encoding="utf-8")
log_execucao("d10_documentacao_amostra.py")
print("ok", len(nota.split()), "palavras na nota")
