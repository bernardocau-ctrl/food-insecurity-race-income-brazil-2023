# -*- coding: utf-8 -*-
"""
ms_numeros_20260925.py

Carrega os CSVs de dados/v2_20260925 (+ os CSVs de 16/09 usados so' para
conferencia/suplemento) e expoe funcoes de formatacao. O manuscrito NUNCA
recebe numero digitado a mao: tudo passa por aqui.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata

import os
BASE = Path(__file__).resolve().parent.parent
DVER = os.environ.get("IJE_DATA_VERSION", "v3_rodadaD_C")   # v3_rodadaD_C = variancia por pesos replicados (configuracao C); v2_20260925 = versao historica (A)
D = BASE / "dados" / DVER
D16 = BASE / "dados"
DRD = BASE / "MANUSCRITO_IJE_20260925" / "rodada_D"      # saidas auditadas da rodada D (sensibilidades)

t1 = pd.read_csv(D / "t1_descritiva.csv")
t2 = pd.read_csv(D / "t2_pares.csv")
t3 = pd.read_csv(D / "t3_conjunto.csv")
t4 = pd.read_csv(D / "t4_gradiente_prev.csv")
t5 = pd.read_csv(D / "t5_gradiente_modelos.csv")
t6 = pd.read_csv(D / "t6_estratificado.csv")
t7 = pd.read_csv(D / "t7_tripla.csv")
m1 = pd.read_csv(D / "m1_maihda_geral.csv").set_index("desfecho")
m2 = pd.read_csv(D / "m2_maihda_coef.csv").rename(columns={"or": "oddsr"})
m3 = pd.read_csv(D / "m3_maihda_estratos.csv")
aten = pd.read_csv((D if (D / "atenuacao_renda_raca_sexo_2023.csv").exists() else D16) / "atenuacao_renda_raca_sexo_2023.csv")
reg = pd.read_csv(D16 / "interseccional_2023_parte2.csv")
boot = pd.concat([
    pd.read_csv(D16 / "interseccional_2023.csv"),
    pd.read_csv(D16 / "interseccional_2023_parte2.csv"),
    pd.read_csv(D16 / "interseccional_2023_parte3.csv")], ignore_index=True)
dm = pd.read_csv(D16 / "dados_maihda_2023.csv", usecols=["estrato", "ia_total", "ia_grave"])
rd_std = pd.read_csv(DRD / "D1_padronizado_vs_bruto_raca_renda.csv") if (DRD / "D1_padronizado_vs_bruto_raca_renda.csv").exists() else None
rd_cut = pd.read_csv(DRD / "D3_sensibilidade_corte_renda.csv") if (DRD / "D3_sensibilidade_corte_renda.csv").exists() else None
rd_ign = pd.read_csv(DRD / "D5_ignorados_comparacao_completa.csv") if (DRD / "D5_ignorados_comparacao_completa.csv").exists() else None
rd_ign_sum = pd.read_csv(DRD / "D5_maiores_diferencas_por_classe.csv") if (DRD / "D5_maiores_diferencas_por_classe.csv").exists() else None

MINUS = "−"


def f1(x): return f"{x:.1f}".replace("-", MINUS)
def f2(x): return f"{x:.2f}".replace("-", MINUS)
def f3(x): return f"{x:.3f}".replace("-", MINUS)
def n0(x): return f"{int(round(x)):,}"


def ci(lo, hi, dec=2):
    fmt = {1: f1, 2: f2, 3: f3}[dec]
    return f"{fmt(lo)} to {fmt(hi)}" if lo < 0 else f"{fmt(lo)}–{fmt(hi)}"


def est_ci(x, lo, hi, dec=2):
    fmt = {1: f1, 2: f2, 3: f3}[dec]
    return f"{fmt(x)} (95% CI {ci(lo, hi, dec)})"


def est_ci_short(x, lo, hi, dec=2):
    fmt = {1: f1, 2: f2, 3: f3}[dec]
    return f"{fmt(x)} ({ci(lo, hi, dec)})"


def pfmt(p):
    if p < 0.001: return "<0.001"
    if p < 0.01: return f"{p:.3f}"
    return f"{p:.2f}"


# ---------------------------------------------------------------- acessores
def T1(var, cat):
    r = t1[(t1.variavel == var) & (t1.categoria == cat)].iloc[0]
    return r


def T2(par_kw, desf):
    r = t2[t2.par.str.contains(par_kw, regex=False) & (t2.desfecho == desf)].iloc[0]
    return r


def T3(termo, desf):
    return t3[(t3.termo == termo) & (t3.desfecho == desf)].iloc[0]


def T6(expo, por, estrato, desf):
    return t6[(t6.exposicao == expo) & (t6.estratificado_por == por) & (t6.estrato == estrato) & (t6.desfecho == desf)].iloc[0]


def T4(desf, k):
    return t4[(t4.desfecho == desf) & (t4.n_desv == k)].iloc[0]


def T5(desf, escala_kw):
    return t5[(t5.desfecho == desf) & t5.escala.str.contains(escala_kw)].iloc[0]


def T7(dim, desf):
    return t7[(t7.terceira_dimensao == dim) & (t7.desfecho == desf)].iloc[0]


def ATEN(var, esp, desf):
    return aten[(aten.variavel == var) & (aten.especificacao == esp) & (aten.desfecho == desf)].iloc[0]


def auc(y, s):
    r = rankdata(s)
    n1 = y.sum(); n0_ = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0_)


def calcula_auc():
    out = {}
    for y in ["ia_total", "ia_grave"]:
        mm = m3[m3.desfecho == y].set_index("estrato")
        dd = dm[["estrato", y]].copy()
        yy = dd[y].to_numpy()
        row = {}
        for col in ["p_nulo_shrunk", "p_aditivo", "p_completo"]:
            row[col] = auc(yy, dd["estrato"].map(mm[col]).to_numpy())
        renda = dd["estrato"].str.split("__").str[3]
        row["renda"] = auc(yy, dd.groupby(renda)[y].transform("mean").to_numpy())
        out[y] = row
    return out


AUC = calcula_auc()
N_STRATA = dm.groupby("estrato").size()
