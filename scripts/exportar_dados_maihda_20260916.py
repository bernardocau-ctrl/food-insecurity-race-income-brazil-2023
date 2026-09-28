# -*- coding: utf-8 -*-
"""
exportar_dados_maihda_20260916.py

Prepara os microdados PNADC T4 2023 para o MAIHDA do Artigo 3: define os
estratos interseccionais (raca x sexo x instrucao x renda x situacao
domiciliar) e exporta um CSV enxuto para o R (lme4) ajustar o modelo
multinivel. Reusa preparar() de analise_bivariada_e_regressao_v2.py -- nao
reconstroi as variaveis do zero.

Estratos: negra (2) x mulher (2) x instrucao (4: sem_fund/fund_med/
medio_comp/superior) x renda (5: q1/q2/q3/q4/mais_2sm) x rural (2) = 160
estratos possiveis.

Saida: resultados/dados_maihda_2023.csv
"""
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import pandas as pd

from analise_bivariada_e_regressao_v2 import ler_microdados, preparar

BASE = Path(__file__).parent
OUT = BASE / "resultados" / "dados_maihda_2023.csv"


def instrucao_categ(row):
    if row["sem_fund"] == 1:
        return "sem_fund"
    if row["fund_med"] == 1:
        return "fund_med"
    if row["medio_comp"] == 1:
        return "medio_comp"
    return "superior"


def renda_categ(row):
    if row["renda_q1"] == 1:
        return "q1"
    if row["renda_q2"] == 1:
        return "q2"
    if row["renda_q3"] == 1:
        return "q3"
    if row["renda_q4"] == 1:
        return "q4"
    return "mais_2sm"


def main():
    df = ler_microdados()
    resp = preparar(df)
    del df

    resp["raca_cat"] = resp["negra"].map({1: "negra", 0: "nao_negra"})
    resp["sexo_cat"] = resp["mulher"].map({1: "mulher", 0: "homem"})
    resp["instrucao_cat"] = resp.apply(instrucao_categ, axis=1)
    resp["renda_cat"] = resp.apply(renda_categ, axis=1)
    resp["rural_cat"] = resp["rural"].map({1: "rural", 0: "urbano"})

    resp["estrato"] = (
        resp["raca_cat"] + "__" + resp["sexo_cat"] + "__" + resp["instrucao_cat"]
        + "__" + resp["renda_cat"] + "__" + resp["rural_cat"]
    )

    slim = resp[[
        "estrato", "raca_cat", "sexo_cat", "instrucao_cat", "renda_cat", "rural_cat",
        "peso", "upa", "ia_total", "ia_grave",
    ]].copy()

    n_estratos = slim["estrato"].nunique()
    tam = slim.groupby("estrato").size()
    print(f"N domicílios: {len(slim):,}")
    print(f"N estratos observados: {n_estratos} (de até 160 possíveis)")
    print(f"Tamanho de estrato: mínimo={tam.min()}, mediana={tam.median():.0f}, "
          f"máximo={tam.max()}")
    print(f"Estratos com menos de 10 observações: {(tam < 10).sum()}")
    print(f"Estratos com menos de 30 observações: {(tam < 30).sum()}")

    slim.to_csv(OUT, index=False, encoding="utf-8")
    print(f"\nSalvo: {OUT}")


if __name__ == "__main__":
    main()
