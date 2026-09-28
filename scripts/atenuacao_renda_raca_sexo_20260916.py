# -*- coding: utf-8 -*-
"""
atenuacao_renda_raca_sexo_20260916.py

Pergunta do autor: no Artigo 1, controlamos renda (por UF) para ver quanto
sobrava do efeito de NOVA4 sobre IA -- e achamos atenuacao de 77,6%. Se
fizessemos o mesmo aqui (nivel individual, PNADC 2023), quanto sobra do
efeito de "ser negra" e de "ser mulher" sobre IA depois de controlar por
renda?

Compara tres versoes do RR de negra (e de mulher), todas por Poisson com
peso amostral e erro-padrao robusto por UPA:
  1. Bruto (nenhum controle)
  2. Controlando so por renda (5 categorias)
  3. Controlando por renda + instrucao + rural (as outras 3 dimensoes do
     Artigo 3) -- equivalente ao efeito do modelo conjunto

Saida: resultados/atenuacao_renda_raca_sexo_2023.csv
"""
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path

import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

from analise_bivariada_e_regressao_v2 import ler_microdados, preparar

BASE = Path(__file__).parent
OUT = BASE / "resultados" / "atenuacao_renda_raca_sexo_2023.csv"


def rr_variavel(df, formula, var, desfecho):
    sub = df.dropna(subset=["peso", "upa"]).copy()
    w = sub["peso"] / sub["peso"].mean()
    model = smf.glm(formula, data=sub, family=sm.families.Poisson(), var_weights=w)
    res = None
    for attempt in [
        lambda: model.fit(cov_type="cluster", cov_kwds={"groups": sub["upa"]}),
        lambda: model.fit(cov_type="HC1"),
        lambda: model.fit(),
    ]:
        try:
            res = attempt()
            break
        except np.linalg.LinAlgError:
            continue
    beta = res.params[var]
    rr = np.exp(beta)
    ic_lo = np.exp(beta - 1.96 * res.bse[var])
    ic_hi = np.exp(beta + 1.96 * res.bse[var])
    p = res.pvalues[var]
    return beta, rr, ic_lo, ic_hi, p


def main():
    df = ler_microdados()
    resp = preparar(df)
    del df

    linhas = []
    for desfecho in ["ia_total", "ia_grave"]:
        print(f"\n=== {desfecho} ===")
        for var, rotulo in [("negra", "Negra"), ("mulher", "Mulher"),
                            ("sem_fund", "Sem instrução"), ("rural", "Rural")]:
            # outras dimensões de identidade, exceto a própria var (evita
            # duplicar coluna na fórmula e mede "tudo o mais" de forma
            # consistente com o modelo conjunto/MAIHDA)
            outras_identidade = [c for c in ["negra", "mulher", "sem_fund", "rural"]
                                  if c != var]
            especificacoes = [
                ("bruto", f"{desfecho} ~ {var}"),
                ("so_renda", f"{desfecho} ~ {var} + renda_q1 + renda_q2 + renda_q3 + renda_q4"),
                ("renda_e_demais",
                 f"{desfecho} ~ {var} + renda_q1 + renda_q2 + renda_q3 + renda_q4 "
                 f"+ {' + '.join(outras_identidade)}"),
            ]
            beta_bruto = None
            for nome_spec, formula in especificacoes:
                beta, rr, lo, hi, p = rr_variavel(resp, formula, var, desfecho)
                if nome_spec == "bruto":
                    beta_bruto = beta
                    atenuacao = 0.0
                else:
                    atenuacao = 100 * (1 - beta / beta_bruto)
                print(f"  {rotulo:8s} [{nome_spec:22s}] RR={rr:.3f} "
                      f"(IC95% {lo:.3f}-{hi:.3f}) p={p:.4f}  "
                      f"atenuação do coeficiente vs. bruto: {atenuacao:.1f}%")
                linhas.append({
                    "desfecho": desfecho, "variavel": rotulo, "especificacao": nome_spec,
                    "beta": beta, "rr": rr, "ic95_low": lo, "ic95_high": hi, "p_valor": p,
                    "atenuacao_pct": atenuacao,
                })

    import pandas as pd
    pd.DataFrame(linhas).to_csv(OUT, index=False)
    print(f"\nSalvo: {OUT}")


if __name__ == "__main__":
    main()
