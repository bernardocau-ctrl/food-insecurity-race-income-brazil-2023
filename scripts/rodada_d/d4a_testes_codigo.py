# -*- coding: utf-8 -*-
"""d4a_testes_codigo.py: testes de correcao do motor (rodar antes de D-1): (1) padronizacao sem covariaveis == prevalencias brutas;
(2) IRLS logistico ponderado == statsmodels GLM Binomial (freq_weights); (3) identidade RERI x p00 == contraste; (4) funcao de influencia
soma zero e SE de A para a prevalencia geral == formula fechada."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
from d1_motor import *
from d2_dados import Dados
import statsmodels.api as sm
D = Dados(); res = {}
for y_name in ("ia_total", "ia_grave"):
    y = D.y[y_name]; cell = D.cell(D.ses_le(1)); raw = cell_theta(D.w, y, cell)
    ths, ok, it, b = std_theta(D.w, y, cell, np.zeros((D.n, 0)))
    res[f"1_std_sem_covariaveis_vs_bruto_{y_name}_max_dif"] = float(np.abs(ths - raw).max())
    C = D.covs_std(); n = D.n; X = np.column_stack([np.ones(n), (cell == 1), (cell == 2), (cell == 3), C]).astype(float)
    b1, ok1, it1 = logit_fit(X, y, D.w)
    g = sm.GLM(y, X, family=sm.families.Binomial(), freq_weights=D.w).fit()
    res[f"2_IRLS_vs_statsmodels_{y_name}_max_dif_coef"] = float(np.abs(b1 - g.params).max()); res[f"2_convergiu_{y_name}"] = bool(ok1)
    d = derived(raw); res[f"3_identidade_{y_name}_dif"] = float(abs(d[DER.index('reri')] * d[DER.index('p00')] - d[DER.index('interacao_pp')]))
Zm, th = influence(D.w, D.y["ia_total"], np.zeros(D.n, int))
res["4_influencia_soma_por_celula_max"] = float(np.abs(Zm.sum(0)).max())
assert all(v < 1e-7 for k, v in res.items() if isinstance(v, float)), res
res["status"] = "PASS"; print(json.dumps(res, indent=1)); (OUTD / "D_testes_codigo.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); log_execucao("d4a_testes_codigo.py", res)
