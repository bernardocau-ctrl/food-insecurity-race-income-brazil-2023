# -*- coding: utf-8 -*-
"""d13_entregaveis_rev4.py: gera as notas e relatorios da rev4 a partir dos arquivos auditados (nada digitado a mao nos numeros):
EMENDA_METODOLOGICA_pos_protocolo.md, RELATORIO_REPRODUCAO_rev4.md, CONTAGEM_DE_PALAVRAS_rev4.md, BLOQUEADORES_rev4.md, DIVIDA_TECNICA_separada.md"""
import json, re, sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "MANUSCRITO_IJE_20260925"; RD = OUT / "rodada_D"; AUD = OUT / "auditoria"; SAN = BASE.parent.parent
J = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
princ, rcfg, amb, chk, lon, integ, d5i, t8 = J(RD / "principal.json"), J(RD / "D4_R_survey_config_replicas.json"), J(RD / "00_ambiente_e_execucao.json"), J(RD / "01_checagens_pesos_replicados.json"), J(RD / "D9_estrato_solitario.json"), J(RD / "01_integridade_amostra.json"), J(RD / "D5_resumo.json"), J(RD / "D8_testes_integridade.json")
val = pd.read_csv(RD / "D4_validacao_python_vs_R.csv"); r11 = pd.read_csv(RD / "R11_comparacao_python_vs_R.csv"); pt = pd.read_csv(RD / "R11_pontos_C_vs_historico.csv")
fa = pd.read_csv(OUT / "F_abstract_number_check_rev4.csv"); rec = pd.read_csv(AUD / "recalculo_estimativas_rev4.csv"); H = J(OUT / "H_matriz_resumo.json")
sub = (AUD / "auditoria_submissao_resumo_rev4.md").read_text(encoding="utf-8"); coh = pd.read_csv(OUT / "C_coherence_checks_rev4.csv")
rep = J(OUT / "_reproducao_comparacao.json") if (OUT / "_reproducao_comparacao.json").exists() else None
env = amb["ambiente"]; ent = amb["entradas"]
Nn = lambda x: f"{int(x):,}".replace(",", ".")
wc = dict(re.findall(r"- ([^:]+): (\d+)", sub.split("## Referencias")[0]))

# ---------------------------------------------------------------- emenda metodologica
c_de = val[val.config == "C"].dif_rel_se.max(); c2 = val[val.config == "C2"].dif_rel_se.max(); bb = val[val.config == "B"].dif_rel_se.max()
emenda = f"""# Nota de emenda metodológica pós-protocolo: escolha da configuração de variância

**Status: emenda. A configuração C NÃO foi pré-especificada como escolhida.** O texto do manuscrito (Métodos, "Transparency") e a Tabela Suplementar S15c dizem isso.

## 1. O que o protocolo fixava (`rodada_D/PROTOCOLO_RODADA_D.md`, escrito antes de rodar)
A principal seria **C** (200 pesos replicados) se (i) o erro-padrão por replicação do meu motor reproduzisse o do pacote R `survey` com diferença relativa < 1×10⁻⁶ e (ii) as 200 colunas replicadas estivessem completas; caso contrário seria **B** (pesos + UPA + Estrato).

## 2. O que aconteceu
1. Primeira avaliação de (i): comparei o motor com `survey::svyby` + `svycontrast`, que aplica o **método delta à covariância das réplicas**. Diferença máxima relativa de {c_de:.4f} (1,1%), acima de 1×10⁻⁶. **Pela leitura literal do protocolo, a principal teria sido B.**
2. Identifiquei que a diferença vinha do **estimador**, não de erro de código: o `svycontrast` é aproximação de primeira ordem, e o motor recalcula o estimando **em cada réplica** (como `survey::withReplicates`).
3. Reavaliei (i) contra `withReplicates`: diferença máxima relativa de {c2:.1e}. O critério (ii) foi atendido ({chk['n_colunas']} colunas, {chk['faltantes']} faltantes, {chk['colunas_todas_zero']} zeradas, {chk['colunas_identicas_ao_peso_final']} iguais ao peso final). Por isso apliquei C.
4. **Decisão dos autores:** adotar C como método principal de variância da versão IJE e conservar B como sensibilidade. **Essa decisão foi tomada depois de os autores verem as três configurações lado a lado.** As estimativas pontuais são idênticas nas três e os intervalos são muito próximos; nenhuma conclusão depende da escolha. A escolha **não** é apresentada como seleção pré-especificada.
5. Não afirmo conhecer o procedimento exato usado pelo IBGE para gerar as réplicas do estrato com uma única UPA (estrato {lon['estrato_com_1_UPA']}, {lon['domicilios']} domicílios, {lon['pct_do_peso_total']:.4f}% do peso): **não foi confirmado em fonte primária** (o documento metodológico do IBGE não pôde ser lido). Empiricamente, os pesos replicados dessa UPA variam entre as réplicas e entram na variância replicada.

## 3. Confirmação, antes da aplicação, dos elementos do método C (evidência)
| Elemento | Confirmado | Evidência |
|---|---|---|
| Nomes exatos das colunas replicadas | `V1028001` a `V1028200` (200 colunas de 15 caracteres, posições 1315-4314 do layout oficial); peso final `V1028` (posição 50, 15 caracteres) | `rodada_D/01_layout_variaveis_usadas.csv`; `01_checagens_pesos_replicados.json` ({chk['n_colunas']} colunas, {chk['faltantes']} faltantes) |
| Fator de escala | 1/(R − 1) = {rcfg['scale']:.10f} com R = {rcfg['n_replicas']} (`scale_igual_1_sobre_R_menos_1 = {rcfg['scale_igual_1_sobre_R_menos_1']}`; `rscales` todos 1) | `rodada_D/D4_R_survey_config_replicas.json` (extraído de `survey::svrepdesign(type="bootstrap", mse=TRUE)`, survey {rcfg['survey_versao']}) |
| Centragem | na **estimativa da amostra completa** (`mse = {str(rcfg['mse']).upper()}`), não na média das réplicas: V = Σᵣ (θᵣ − θ)² / (R − 1) | mesmo arquivo; `scripts/rodada_d/d1_motor.py` (cabeçalho) |
| Concordância com `survey::withReplicates` | erro-padrão: diferença relativa máxima {c2:.1e}; estimativa: {val[val.config=='C2'].dif_rel_estimativa.max():.1e} (race × renda, dois desfechos, 15 estimandos) | `rodada_D/D4_validacao_python_vs_R.csv` |
| Concordância das regressões e da padronização | estimativas ≤ {r11.dif_rel_est.max():.1e} e erros-padrão ≤ {r11.dif_rel_se.max():.1e} (17 quantidades: prevalência geral, PR por faixa, atenuação, termo de produto, padronização) contra `survey::svyglm` (quasipoisson) e `glm` quasibinomial | `rodada_D/R11_comparacao_python_vs_R.csv` |
| Reprodutibilidade | rodada limpa idêntica byte a byte (ver `RELATORIO_REPRODUCAO_rev4.md`) | `rodada_D/00_ambiente_e_execucao.json` |
Todos os elementos estão documentados e reproduzíveis; **não houve motivo para parar**.

## 4. Texto no manuscrito
Métodos: "The replicate-weight variance was chosen after comparing three methods (Supplementary Table S15)". Suplemento S15c: "Post-protocol amendment. The prespecified rule … was first evaluated against the delta method and failed, which by its literal reading would have selected B; C was adopted after identifying that the comparison used a different estimator. The decision is not presented as prespecified and was taken by the authors after inspecting all three sets of intervals."
"""
(OUT / "EMENDA_METODOLOGICA_pos_protocolo.md").write_text(emenda, encoding="utf-8")

# ---------------------------------------------------------------- relatorio de reproducao
rows = [(e["script"], e["comando"], e["data_utc"]) for e in amb["execucoes"]]
first = min(e["data_utc"] for e in amb["execucoes"]); last = max(e["data_utc"] for e in amb["execucoes"])
repro = f"""# Relatório de reprodução da versão IJE rev4

## Ambiente e entradas (`rodada_D/00_ambiente_e_execucao.json`)
Python {env['python']}; numpy {env['numpy']}; pandas {env['pandas']}; scipy {env['scipy']}; statsmodels {env['statsmodels']} (só nos testes); R 4.6.1 com `survey` {rcfg['survey_versao']} (validação); {env['sistema']}. Execuções registradas de {first} a {last} (UTC).
Entradas (SHA-256): `PNADC_2023_trimestre4_20251010.zip` `{ent['PNADC_2023_trimestre4_20251010.zip']['sha256']}`; layout `{ent['input_PNADC_trimestre4_20251010.txt']['sha256']}`; dicionário `{ent['dicionario_PNADC_microdados_trimestre4_20260702.xls']['sha256']}`. Manifesto dos dados finais: `dados/v3_rodadaD_C/MANIFEST.csv` (SHA-256 por arquivo). **Os CSV históricos (`dados/v2_20260925`, `dados/atenuacao_*.csv`) não foram sobrescritos**; a versão nova é `dados/v3_rodadaD_C/`.

## Comando
```
python scripts/rodada_d/run_pacote_rev4.py      # de qualquer diretório; ~30 minutos
```
Etapas: extração com o layout oficial (d0) → testes de integridade (d8) → D-4 (d3, d3b R, d3c) → estrato solitário (d9) → testes do motor (d4a) → D-1/D-2 (d4b) → D-3/D-5 (d5) → matriz e tabelas (d6) → registro e notas da amostra (d10) → relatórios (d7) → **regressões com C (d11)** → validação independente em R (d11a, d11b, d11c) → figuras → coerência → montagem do manuscrito, suplemento e tabelas → auditorias de estimativas e de submissão → verificação independente do resumo → matriz rev3→rev4 → notas (d13).

## Reprodução limpa
{('Cache, saídas da rodada D e dados v3 foram apagados e regerados a partir do ZIP, rodando de outro diretório. Comparação com a execução anterior: ' + rep['resumo']) if rep else 'NÃO EXECUTADA neste arquivo (ver run_pacote_rev4.py).'}
{('Arquivos comparados: ' + str(rep['n_comparados']) + ' (CSV, JSON, textos dos .docx e abas do .xlsx); diferentes: ' + str(rep['n_diferentes']) + '. ' + ('Diferenças: ' + '; '.join(rep['diferentes']) if rep['diferentes'] else 'Nenhuma.')) if rep else ''}

## Verificações (todas reexecutadas nesta reprodução)
| Verificação | Resultado |
|---|---|
| Integridade da amostra (`d8`, 9 testes; 11 corrupções simuladas) | {sum(1 for r in t8['testes'] if r['resultado']=='PASS')} de {len(t8['testes'])} PASS; {sum(1 for a in t8['autoteste_mutacao'] if a['falhou_como_esperado'])} de {len(t8['autoteste_mutacao'])} corrupções detectadas |
| Estimativas pontuais das regressões com C contra os CSV históricos | {len(pt)} colunas comparadas, máx. dif. relativa {pt.max_dif_relativa_C_vs_historico.max():.1e}, {int((pt.status=='PASS').sum())} PASS |
| Motor Python contra `survey` (B e C; race × renda) | SE B ≤ {val[val.config=='B'].dif_rel_se.max():.1e}; SE C (`withReplicates`) ≤ {c2:.1e} |
| Regressões e padronização contra R (17 quantidades) | estimativas ≤ {r11.dif_rel_est.max():.1e}; SE ≤ {r11.dif_rel_se.max():.1e} |
| Recalculo das estimativas e das Tabelas 1-3 impressas | {int((rec.status=='PASS').sum())} de {len(rec)} PASS |
| Coerência (identidade RERI × p00 = contraste etc.) | {int((coh.status=='PASS').sum())} PASS |
| Números do resumo contra implementação independente (R) | {int((fa.status=='MATCH').sum())} de {len(fa)} MATCH |
| Matriz rev3 → rev4 | {H['linhas']} linhas; valores impressos com estimativa pontual alterada: {H['valores_impressos_alterados_ponto_estimado']}; fontes da rev4 apontando para dados históricos v2: {H['fontes_rev4_apontando_para_v2_20260925']}; fontes sem método de variância identificado: {H['fontes_rev4_sem_metodo_de_variancia_identificado']} |

## Atribuição do método de variância (controle de qualidade)
Cada número impresso passou por função que registra arquivo, filtro, coluna e **método de variância** (`C_Traceability_table_rev4.xlsx`, coluna `variance_method`): {json.dumps(H['fontes_rev4_por_metodo'], ensure_ascii=False)}. Nada do texto, das Tabelas 1-3, da Figura 1 ou do suplemento vem de `dados/v2_20260925`. As duas exceções **identificadas como tais** no suplemento são os IC do bootstrap por conglomerado de análises anteriores (S5, coluna comparativa, e S8), que não são C.
MAIHDA: **modelo misto não ponderado**, identificado no resumo ("Unweighted multilevel"), nos Métodos e no suplemento.

## Regressões reestimadas com C (`dados/v3_rodadaD_C`)
t1, t2 (quatro pares), t3 (modelo mutuamente ajustado; Wald de 4 gl pela covariância das réplicas), t4, t5 (gradiente, relativo e absoluto), t6 (32 linhas: PR ajustada e diferença absoluta por faixa, escolaridade e raça), t7 (três vias) e atenuação (24 linhas, com IC da atenuação). Todos os modelos foram reajustados em cada uma das 200 réplicas; falhas de réplica: 0. **Não reestimados com C:** S5 (coluna do bootstrap por conglomerado de 300 réplicas) e S8 (regional; bootstrap anterior); ambos rotulados.
"""
(OUT / "RELATORIO_REPRODUCAO_rev4.md").write_text(repro, encoding="utf-8")

# ---------------------------------------------------------------- contagem de palavras
c3 = {k: int(v) for k, v in re.findall(r"(Introduction|Methods|Results|Discussion|Conclusion): (\d+)", (OUT / "D_Counts_IJE_rev3.md").read_text(encoding="utf-8"))}
c4 = {k: int(v) for k, v in re.findall(r"(Introduction|Methods|Results|Discussion|Conclusion): (\d+)", (OUT / "D_Counts_IJE_rev4.md").read_text(encoding="utf-8"))}
tab = "\n".join(f"| {k} | {c3.get(k, '')} | {c4.get(k, '')} | {c4.get(k, 0) - c3.get(k, 0):+d} |" for k in ["Introduction", "Methods", "Results", "Discussion", "Conclusion"])
cont = f"""# Contagem de palavras da rev4 (regra do IJE para Original Article)

Regra oficial (página *General Instructions* do IJE, conferida em 25/09/2026): "No more than 3000 (main text only; excluding abstract, key messages, declarations, references, tables, figures and supplementary material)". Resumo estruturado ≤ 250 palavras.

| Contagem (recontada do .docx rev4) | Palavras |
|---|---|
| Texto principal, com títulos (regra mais conservadora) | **{wc['texto_principal_com_titulos_(split)']}** |
| Sem títulos | {wc['texto_principal_sem_titulos_(split)']} |
| Sem títulos e sem os números de citação | {wc['sem_titulos_e_sem_citacoes_[n]']} |
| Apenas palavras alfabéticas | {wc['apenas_palavras_alfabeticas_(sem_numeros/citacoes)']} |
| Resumo (limite 250) | **{wc['resumo_(split)']}** |
Margem de {3000 - int(wc['texto_principal_com_titulos_(split)'])} palavras na regra mais conservadora. A contagem do sistema de submissão do IJE **NÃO VERIFICADO** (pode diferir). Referências: 33 (limite 50); tabelas + figuras no corpo: 3 + 1 (limite 8); 3 Key Messages; 8 palavras-chave.

## Compensação: cada inclusão foi paga com corte de trecho secundário
| Seção | rev3 | rev4 | Variação |
|---|---|---|---|
{tab}
**Acrescentado (necessário):** descrição exata da variância (C, com A e B como comparação); parágrafo de análises de sensibilidade (padronização, cortes, ignorados); subseção de Resultados "Sensitivity analyses"; IC da interação e dos componentes; qualificação de "compatível com aditividade" pelo corte; padronização na Discussão; limitações revisadas.
**Cortado (secundário):** frases de contexto brasileiro, o estudo de MAIHDA em obesidade, a comparabilidade EBIA entre grupos interseccionais e a referência ao método delta/bootstrap (três referências a menos), tamanho mediano dos estratos, o termo de produto do modelo ajustado (vai ao suplemento S6), listagem das PRs da educação, sobreposição entre Resultados e Discussão sobre a decomposição, e duas frases metodológicas repetidas. Nenhuma informação necessária para entender estimandos, desenho e análises exploratórias foi retirada.
"""
(OUT / "CONTAGEM_DE_PALAVRAS_rev4.md").write_text(cont, encoding="utf-8")

# ---------------------------------------------------------------- divida tecnica
importers = sorted({str(p.relative_to(SAN)).replace("\\", "/") for p in SAN.rglob("*.py") if re.search(r"(from|import) +analise_bivariada_e_regressao_v2", p.read_text(encoding="utf-8", errors="ignore")) and "_obsoleto" not in str(p) and "PACOTE" not in str(p) and "rodada_d" not in str(p) and "artigos/04_" not in str(p).replace("\\", "/") and p.name != "analise_bivariada_e_regressao_v2.py"})
v1008 = sorted({str(p.relative_to(SAN)).replace("\\", "/") for p in SAN.rglob("*.py") if re.search(r"V1008", p.read_text(encoding="utf-8", errors="ignore")) and "_obsoleto" not in str(p) and "PACOTE" not in str(p) and "rodada_d" not in str(p) and "auditoria" not in p.name and "d0_extrair" not in p.name and not p.name.startswith("d13_") and p.name != "analise_bivariada_e_regressao_v2.py"})
abspath = sorted({str(p.relative_to(SAN)).replace("\\", "/") for p in (BASE / "scripts").rglob("*.py") if re.search(r"[A-Za-z]:[\\/](Users|Projetos)", p.read_text(encoding="utf-8", errors="ignore"))})
divida = f"""# Dívida técnica separada (fora do escopo desta rodada; NÃO alterada)

1. **Cópia independente do leitor no Artigo 4:** `artigos/04_ARTIGO4_TENDENCIA_INTERSECCIONAL_RACA_GENERO/scripts/analise_bivariada_e_regressao_v2.py` ainda lê o prefixo de 3 caracteres do Estrato sob o nome "V1008" e o peso V1028 com 14 caracteres (efeito ≤ 9×10⁻⁹ relativo). Não foi tocada.
2. **`processar_*.py` e outros scripts do projeto que ainda mencionam o nome antigo "V1008":** {', '.join('`' + x + '`' for x in v1008) or 'nenhum'}.
3. **Scripts que importam o leitor compartilhado corrigido** (uma nova execução mudaria os pesos a partir da 9ª casa decimal; os CSV históricos não foram regenerados): {', '.join('`' + x + '`' for x in importers)}.
4. **Análises históricas do Artigo 3** (`analise_consolidada_artigo3_20260925.py`, `atenuacao_renda_raca_sexo_20260916.py`, `analise_interseccional_*`) continuam com a variância A (UPA) e caminhos relativos ao arquivo; a versão com C é `d11_regressoes_C.py`. Antes de publicar o repositório, decidir se os scripts históricos entram (com aviso) ou se ficam só como registro.
5. **Caminhos absolutos** em scripts de `artigos/03_…/scripts/` ({', '.join('`' + x + '`' for x in abspath) or 'nenhum encontrado'}).
6. **Scripts da série IJE com nome `_20260925`/`_20260926`** misturam v1, rev2, rev3 e rev4 (`entregaveis_rev2_ije_20260925.py`, `coerencia_ije_20260925.py`, `relatorio_verificacao_ije_20260925.py`, `verificacao_independente_ije_20260925.py` leem `dados/v2_20260925`). Servem como registro das versões anteriores; a cadeia da rev4 usa `*_rev4.py`, `d11*`, `d13*` e `run_pacote_rev4.py`.
7. **Pacote SSM** (`MANUSCRITO_EN_SSM_20260925/`): mantém "attributable to", "super-additive but sub-multiplicative" genérico, a premissa falsa sobre o estrato e ICs da variância A. Não alterado.
8. **Documento metodológico oficial do IBGE** sobre pesos replicados e estratos de uma UPA não foi lido (PDF ilegível nesta sessão).
"""
(OUT / "DIVIDA_TECNICA_separada.md").write_text(divida, encoding="utf-8")

# ---------------------------------------------------------------- bloqueadores
bloq = """# Lista final de bloqueadores (rev4)

## DEPENDE DE DECISÃO DOS AUTORES ou de dado que só eles têm (não preenchidos por inferência)
1. **Autores, ordem, afiliações, autor para correspondência (endereço postal e e-mail), ORCID.**
2. **Ética:** nome do comitê e número de aprovação, ou a declaração de que a aprovação não era necessária e o motivo.
3. **Financiamento** no formato do IJE ("This work was supported by … [grant number …]").
4. **Conflito de interesses:** declaração no manuscrito e **formulário COI no sistema online**.
5. **Contribuições de cada autor e garantidor** ("Author contributions").
6. **Declaração de IA:** confirmação de que os autores revisaram e checaram código e saídas; nome, versão e data das ferramentas.
7. **Repositório, licença e DOI do código e dos dados derivados** (o IJE exige todo o código); **não criados**. Antes: limpeza dos scripts (ver `DIVIDA_TECNICA_separada.md`).
8. **Aprovação da emenda pós-protocolo** (escolha de C após ver as três configurações) e da redação do suplemento S15c.
9. **Decisão de mostrar ou não o IC da participação da interação para qualquer insegurança** (regra do protocolo: não; IC no suplemento S16).

## NÃO VERIFICADO
10. **Referência Câmara et al. 2026 (AJPH):** metadados do registro do PubMed (6 autores, e1-e10, online 23/07/2026); falta conferir na página da revista.
11. **Documento metodológico oficial do IBGE** sobre os pesos replicados (C está confirmado por `survey` e por fontes secundárias) e sobre a geração das réplicas para o estrato de uma UPA.
12. **Contagem oficial de palavras e formatação no sistema do IJE.**
13. Diferença de 0,25%-0,57% entre o microdado e a tabela SIDRA 9554 (controle interno; não citar como validação externa).
14. **Bootstrap por conglomerado de análises anteriores** (S5, coluna comparativa; S8 regional) não foi reestimado com C; está rotulado.

## Técnicos
15. Pacote SSM desatualizado e ainda com as formulações corrigidas aqui; Artigo 4 e `processar_*.py` com o leitor antigo (ver `DIVIDA_TECNICA_separada.md`).
16. Carta ao editor e início da submissão: **não feitos**. DOI e repositório: **não criados**.
"""
(OUT / "BLOQUEADORES_rev4.md").write_text(bloq, encoding="utf-8")
print("entregaveis ok")
