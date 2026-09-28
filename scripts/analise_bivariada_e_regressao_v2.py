# -*- coding: utf-8 -*-
"""
analise_bivariada_e_regressao_v2.py

Analise bivariada formal (razoes de prevalencia com IC95% + teste de associacao)
e regressao logistica revisada (com peso amostral via var_weights + erros-padrao
robustos a conglomerado -- clustering por UPA), a partir dos microdados PNADC T4 2023.

Corrige a limitacao da versao anterior (rodar_regressao_logistica.py), que usava
freq_weights (infla N para a soma dos pesos, produzindo IC artificialmente
estreitos). Aqui o peso e' normalizado e usado como var_weights, com erros-padrao
sanduiche agrupados por UPA (unidade primaria de amostragem) -- nao ha ajuste
para estratificacao (variavel de estrato nao extraida do arquivo publico).

Saidas:
  resultados/bivariada_determinantes_2023.csv
  resultados/regressao_logistica_2023_v2_robusta.csv
"""

import warnings
warnings.filterwarnings("ignore")

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

BASE = Path(__file__).parent
ZIP_23 = BASE / "dados_ibge" / "microdados_pnad" / "PNADC_2023_trimestre4_20251010.zip"
OUT_DIR = BASE / "resultados"

# NOTA (25/09/2026). Ate esta data a coluna lida nas posicoes 20-23 chamava-se "V1008" e o peso V1028 era lido com 14 caracteres.
#  * A coluna "V1008" antiga NAO era a V1008 oficial (28-29): era o PREFIXO DE 3 CARACTERES da variavel Estrato (81 valores; o Estrato completo tem 573),
#    constante dentro da UPA. O microdado publico TEM o estrato e 200 pesos replicados (V1028001-V1028200).
#  * O peso oficial tem 15 caracteres; a leitura antiga perdia a ultima casa decimal (diferenca relativa maxima 9e-9). Os CSVs ja gerados NAO foram refeitos;
#    uma nova execucao muda os pesos a partir da 9a casa decimal (verificado em scripts/rodada_d/d8_testes_integridade.py).
#  * O ID de domicilio reconstruido em preparar() e' equivalente a chave oficial UPA+V1008+V1014 (verificado nos 173.676 domicilios).
COLSPECS = [
    # Posicoes 0-based [ini, fim) derivadas do layout OFICIAL do IBGE (dados_ibge/pnadc_documentacao/input_PNADC_trimestre4_20251010.txt,
    # '@posicao 1-based + largura'). Nomes = nomes oficiais completos. Corrigido em 25/09/2026 (ver NOTA abaixo).
    (0, 4),      # Ano
    (4, 5),      # Trimestre
    (5, 7),      # UF
    (7, 9),      # Capital
    (11, 20),    # UPA (unidade primaria de amostragem; conglomerado)     @12  $9
    (20, 27),    # Estrato (variavel oficial de estratificacao)           @21  $7
    (27, 29),    # V1008 (numero de selecao do domicilio)                 @28  $2
    (29, 31),    # V1014 (painel / grupo de amostra)                      @30  $2
    (32, 33),    # V1022 situacao domicilio 1=urbano 2=rural              @33  $1
    (49, 64),    # V1028 peso COM calibracao, 15 caracteres               @50  15
    (88, 90),    # V2001 numero moradores
    (92, 94),    # V2005 condicao no domicilio (01=responsavel)
    (94, 95),    # V2007 sexo 1=M 2=F
    (103, 106),  # V2009 idade
    (106, 107),  # V2010 cor/raca
    (1094, 1095),  # S17001
    (1112, 1113),  # VD2004 especie domicilio
    (1115, 1116),  # VD3004 instrucao
    (1278, 1279),  # VDI5009 faixa renda per capita
    (1313, 1314),  # SD17001 EBIA derivada
]
NOMES = [
    "Ano", "Trimestre", "UF", "Capital", "UPA", "Estrato", "V1008", "V1014",
    "V1022", "V1028", "V2001", "V2005", "V2007", "V2009", "V2010",
    "S17001", "VD2004", "VD3004", "VDI5009", "SD17001",
]


def ler_microdados():
    print("Lendo microdados PNADC T4 2023...")
    with zipfile.ZipFile(ZIP_23) as z:
        txts = [n for n in z.namelist() if n.upper().endswith(".TXT")]
        with z.open(txts[0]) as f:
            df = pd.read_fwf(f, colspecs=COLSPECS, names=NOMES,
                              encoding="latin1", dtype=str, header=None)
    print(f"  linhas brutas: {len(df):,}")
    return df


def preparar(df):
    # ATENCAO (historico): a coluna lida nas posicoes 20-23 (antes chamada "V1008") NAO era a V1008 do IBGE: sao os 3 primeiros caracteres do Estrato, constantes dentro da UPA.
    # A V1008 oficial (pos. 28-29) e a V1014 (30-31) nao sao lidas aqui. O ID reconstruido abaixo equivale a chave oficial UPA+V1008+V1014 (verificado em 25/09/2026).
    # [comentario antigo] V1008 (posicao 20-23) NAO diferencia domicilios dentro da mesma UPA
    # nos dados extraidos (fica constante), ao contrario do que a documentacao
    # do projeto assumia. Isso e a causa-raiz do bug ja conhecido em
    # serie_ChefiaFem.csv (quase 100% = 1) e afeta igualmente qualquer variavel
    # agregada por domicilio (crianca5, idoso60) construida com UPA+V1008.
    # Correcao: reconstruir o id do domicilio por contagem sequencial de
    # ocorrencias de V2005=='01' (responsavel) dentro de cada UPA -- o arquivo
    # vem ordenado com o responsavel na primeira linha de cada domicilio.
    # Verificado: produz exatamente 173.676 domicilios (= linhas V2005=='01')
    # e prevalencias de IA por idoso60/crianca5 batendo com o SIDRA (9557/9559/9560).
    df["_is_resp"] = (df["V2005"].str.strip() == "01").astype(int)
    df["_dom_seq"] = df.groupby("UPA")["_is_resp"].cumsum()
    df["_dom_id"] = df["UPA"].str.strip() + "_" + df["_dom_seq"].astype(str)
    df["_idade"] = pd.to_numeric(df["V2009"], errors="coerce")

    doms_crianca5 = set(df[df["_idade"] <= 4]["_dom_id"].unique())
    doms_idoso60 = set(df[df["_idade"] >= 60]["_dom_id"].unique())

    resp = df[df["V2005"].str.strip() == "01"].copy()
    resp = resp[resp["SD17001"].str.strip().isin(["1", "2", "3", "4"])]
    print(f"  responsaveis com EBIA coletada: {len(resp):,}")

    resp["peso"] = pd.to_numeric(resp["V1028"], errors="coerce")
    resp["ebia"] = pd.to_numeric(resp["SD17001"], errors="coerce")
    resp["dom_id"] = resp["_dom_id"]
    resp["upa"] = resp["UPA"].str.strip()

    resp["mulher"] = (pd.to_numeric(resp["V2007"], errors="coerce") == 2).astype(int)
    raca = pd.to_numeric(resp["V2010"], errors="coerce")
    resp["negra"] = raca.isin([2, 4]).astype(int)
    resp["rural"] = (pd.to_numeric(resp["V1022"], errors="coerce") == 2).astype(int)

    # VD3004 tem 7 categorias (ver dicionario_pnad_sa_trimestre4.json). O
    # agrupamento abaixo em 4 grupos está correto; o que estava errado era a
    # descrição — corrigida em 08/08/2026.
    instr = pd.to_numeric(resp["VD3004"], errors="coerce")
    resp["sem_fund"] = instr.isin([1, 2]).astype(int)    # sem instrução + fund. incompleto
    resp["fund_med"] = instr.isin([3, 4]).astype(int)    # fund. completo + médio incompleto
    resp["medio_comp"] = (instr == 5).astype(int)        # médio completo (só o 5)
    # referencia: instr 6 ou 7 = superior incompleto OU completo

    renda = pd.to_numeric(resp["VDI5009"], errors="coerce")
    resp["renda_q1"] = (renda == 1).astype(int)
    resp["renda_q2"] = (renda == 2).astype(int)
    resp["renda_q3"] = (renda == 3).astype(int)
    resp["renda_q4"] = (renda == 4).astype(int)
    # referencia: renda >= 5 (>2 SM)

    moradores = pd.to_numeric(resp["V2001"], errors="coerce")
    resp["dom_2a3"] = moradores.between(2, 3).astype(int)
    resp["dom_4a5"] = moradores.between(4, 5).astype(int)
    resp["dom_6mais"] = (moradores >= 6).astype(int)

    resp["crianca5"] = resp["dom_id"].isin(doms_crianca5).astype(int)
    resp["idoso60"] = resp["dom_id"].isin(doms_idoso60).astype(int)

    resp["ia_total"] = (resp["ebia"] >= 2).astype(int)
    resp["ia_grave"] = (resp["ebia"] == 4).astype(int)

    resp = resp.dropna(subset=["peso", "ebia", "renda_q1", "mulher", "negra",
                                "sem_fund", "rural"])
    print(f"  apos limpeza: {len(resp):,} domicilios")
    return resp


# ---------------------------------------------------------------------------
# Analise bivariada: RP (razao de prevalencia) com IC95% via Poisson robusta
# (log-binomial aproximado), erros-padrao agrupados por UPA, + teste de Wald
# (equivalente ao qui-quadrado, mas robusto a peso e conglomerado).
# ---------------------------------------------------------------------------

def rp_ic95(df, var_bin, desfecho="ia_total"):
    """RP (grupo exposto vs. nao exposto) com IC95%, ajustado por peso (var_weights)
    e erro-padrao robusto agrupado por UPA. Retorna dict com RP, IC, p, prevalencias."""
    sub = df.dropna(subset=[var_bin, desfecho, "peso", "upa"]).copy()
    sub = sub[sub["peso"] > 0]
    w = sub["peso"] / sub["peso"].mean()

    formula = f"{desfecho} ~ {var_bin}"
    model = smf.glm(formula, data=sub, family=sm.families.Poisson(), var_weights=w)
    res = None
    for attempt in [
        lambda: model.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}),
        lambda: model.fit(cov_type="HC1"),
        lambda: model.fit(cov_type="HC0"),
        lambda: model.fit(),
    ]:
        try:
            res = attempt()
            break
        except np.linalg.LinAlgError:
            continue
    if res is None:
        raise RuntimeError("Todas as tentativas de ajuste falharam (matriz singular).")

    coef = res.params[var_bin]
    se = res.bse[var_bin]
    rp = np.exp(coef)
    ic_low = np.exp(coef - 1.96 * se)
    ic_high = np.exp(coef + 1.96 * se)
    p = res.pvalues[var_bin]

    prev_exp = np.average(sub.loc[sub[var_bin] == 1, desfecho],
                           weights=sub.loc[sub[var_bin] == 1, "peso"]) * 100
    prev_nexp = np.average(sub.loc[sub[var_bin] == 0, desfecho],
                            weights=sub.loc[sub[var_bin] == 0, "peso"]) * 100
    n = len(sub)

    return {
        "n": n, "prev_exposto": round(prev_exp, 1), "prev_referencia": round(prev_nexp, 1),
        "RP": round(rp, 2), "IC95_low": round(ic_low, 2), "IC95_high": round(ic_high, 2),
        "p_valor": p,
    }


def wald_chi2_categorica(df, dummies, desfecho="ia_total"):
    """Teste de associacao global (equivalente ao qui-quadrado) para uma variavel
    categorica representada por variaveis dummy, via teste de Wald conjunto
    numa regressao log-binomial robusta (peso + cluster UPA)."""
    sub = df.dropna(subset=dummies + [desfecho, "peso", "upa"]).copy()
    sub = sub[sub["peso"] > 0]
    w = sub["peso"] / sub["peso"].mean()

    formula = f"{desfecho} ~ " + " + ".join(dummies)
    model = smf.glm(formula, data=sub, family=sm.families.Poisson(), var_weights=w)
    res = None
    for attempt in [
        lambda: model.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}),
        lambda: model.fit(cov_type="HC1"),
        lambda: model.fit(cov_type="HC0"),
        lambda: model.fit(),
    ]:
        try:
            res = attempt()
            break
        except np.linalg.LinAlgError:
            continue
    if res is None:
        raise RuntimeError("Todas as tentativas de ajuste falharam (matriz singular).")

    hyp = " , ".join([f"{d} = 0" for d in dummies])
    wald = res.wald_test(hyp, scalar=True)
    stat = float(wald.statistic)
    df_num = len(dummies)
    p = float(wald.pvalue)
    return stat, df_num, p


def main():
    df_raw = ler_microdados()
    df = preparar(df_raw)

    determinantes = [
        ("Sexo (mulher vs. homem)", "mulher", None),
        ("Cor/raça (preta+parda vs. branca)", "negra", None),
        ("Área rural (vs. urbana)", "rural", None),
        ("Sem instrução/fund. incompleto (vs. superior inc. ou compl.)", "sem_fund",
         ["sem_fund", "fund_med", "medio_comp"]),
        ("Renda ≤ 1/4 SM (vs. > 2 SM)", "renda_q1",
         ["renda_q1", "renda_q2", "renda_q3", "renda_q4"]),
        ("Presença de criança <5 anos", "crianca5", None),
        ("Presença de idoso ≥60 anos", "idoso60", None),
        ("6+ moradores (vs. 1 morador)", "dom_6mais",
         ["dom_2a3", "dom_4a5", "dom_6mais"]),
    ]

    linhas = []
    for desfecho in ["ia_total", "ia_grave"]:
        print(f"\n=== Desfecho: {desfecho} ===")
        for label, varbin, grupo in determinantes:
            r = rp_ic95(df, varbin, desfecho)
            row = {"determinante": label, "desfecho": desfecho, **r}
            if grupo:
                stat, dfree, p_wald = wald_chi2_categorica(df, grupo, desfecho)
                row["wald_chi2"] = round(stat, 1)
                row["wald_gl"] = dfree
                row["wald_p"] = p_wald
            else:
                # variavel binaria: teste de Wald da propria RP (1 gl) ja calculado
                row["wald_chi2"] = None
                row["wald_gl"] = 1
                row["wald_p"] = r["p_valor"]
            linhas.append(row)
            print(f"  {label}: RP={r['RP']} (IC95% {r['IC95_low']}-{r['IC95_high']}) p={r['p_valor']:.2e}")

    result = pd.DataFrame(linhas)
    out_csv = OUT_DIR / "bivariada_determinantes_2023.csv"
    result.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\nSalvo: {out_csv}")

    # -----------------------------------------------------------------------
    # Regressao logistica revisada: peso amostral via var_weights + cluster UPA
    # -----------------------------------------------------------------------
    print("\n=== Regressao logistica revisada (var_weights + cluster robust UPA) ===")
    FORMULA = (
        "ia_total ~ renda_q1 + renda_q2 + renda_q3 + renda_q4 "
        "+ mulher + negra + rural "
        "+ sem_fund + fund_med + medio_comp "
        "+ dom_2a3 + dom_4a5 + dom_6mais "
        "+ idoso60 + crianca5"
    )
    FORMULA2 = FORMULA.replace("ia_total", "ia_grave")

    w = df["peso"] / df["peso"].mean()

    try:
        m1 = smf.glm(FORMULA, data=df, family=sm.families.Binomial(), var_weights=w) \
            .fit(cov_type="cluster", cov_kwds={"groups": df["upa"]})
    except np.linalg.LinAlgError:
        print("  (fallback: HC1, cluster falhou por matriz singular)")
        m1 = smf.glm(FORMULA, data=df, family=sm.families.Binomial(), var_weights=w).fit(cov_type="HC1")
    try:
        m2 = smf.glm(FORMULA2, data=df, family=sm.families.Binomial(), var_weights=w) \
            .fit(cov_type="cluster", cov_kwds={"groups": df["upa"]})
    except np.linalg.LinAlgError:
        print("  (fallback: HC1, cluster falhou por matriz singular)")
        m2 = smf.glm(FORMULA2, data=df, family=sm.families.Binomial(), var_weights=w).fit(cov_type="HC1")

    def or_table(model, nome):
        params = model.params
        conf = model.conf_int()
        conf.columns = ["IC_lower", "IC_upper"]
        t = pd.DataFrame({"coef": params}).join(conf)
        t["OR"] = np.exp(t["coef"])
        t["OR_lower"] = np.exp(t["IC_lower"])
        t["OR_upper"] = np.exp(t["IC_upper"])
        t["p_valor"] = model.pvalues
        t["modelo"] = nome
        t = t.drop(columns=["coef", "IC_lower", "IC_upper"])
        t = t[t.index != "Intercept"]
        return t

    tab1 = or_table(m1, "M1_IA_total")
    tab2 = or_table(m2, "M2_IA_grave")
    result2 = pd.concat([tab1, tab2])

    label_map = {
        "renda_q1": "Renda ≤ ¼ SM (ref.: > 2 SM)",
        "renda_q2": "Renda ¼–½ SM",
        "renda_q3": "Renda ½–1 SM",
        "renda_q4": "Renda 1–2 SM",
        "mulher": "Responsável mulher (ref.: homem)",
        "negra": "Cor/raça negra (preta+parda) (ref.: branca)",
        "rural": "Área rural (ref.: urbana)",
        "sem_fund": "Sem instrução / fund. incompleto (ref.: superior inc. ou compl.)",
        "fund_med": "Fund. completo / médio incompleto",
        "medio_comp": "Médio completo",
        "dom_2a3": "2–3 moradores (ref.: 1 morador)",
        "dom_4a5": "4–5 moradores",
        "dom_6mais": "≥ 6 moradores",
        "idoso60": "Presença de idoso ≥60 anos (ref.: sem idoso)",
        "crianca5": "Presença de criança <5 anos (ref.: sem criança)",
    }
    result2.index = [label_map.get(i, i) for i in result2.index]

    out_csv2 = OUT_DIR / "regressao_logistica_2023_v2_robusta.csv"
    result2.to_csv(out_csv2, encoding="utf-8-sig")
    print(f"Salvo: {out_csv2}")

    print(f"\nN M1: {int(m1.nobs):,} | pseudo-R2 nao disponivel para GLM ponderado (usar deviance)")
    print(f"Deviance M1: {m1.deviance:.1f} | Null deviance: {m1.null_deviance:.1f}")
    pr2_1 = 1 - m1.deviance / m1.null_deviance
    pr2_2 = 1 - m2.deviance / m2.null_deviance
    print(f"Pseudo-R2 (McFadden aprox., baseado em deviance) M1: {pr2_1:.4f}")
    print(f"Pseudo-R2 (McFadden aprox., baseado em deviance) M2: {pr2_2:.4f}")

    print("\n===== Comparação OR M1 (versão anterior não-ponderada vs. robusta) =====")
    for var in tab1.index:
        r = tab1.loc[var]
        print(f"  {var}: OR={r['OR']:.2f} (IC95% {r['OR_lower']:.2f}-{r['OR_upper']:.2f}) p={r['p_valor']:.2e}")


if __name__ == "__main__":
    main()
