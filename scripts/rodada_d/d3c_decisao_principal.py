# -*- coding: utf-8 -*-
"""d3c_decisao_principal.py: aplica a REGRA DE ESCOLHA fixada em PROTOCOLO_RODADA_D.md (sem olhar a largura dos IC):
(i) erros-padrao por replicacao do motor Python == pacote R survey (rel. < 1e-6) e (ii) 200 pesos replicados completos."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *

py = pd.read_csv(OUTD / "D4_motor_python_para_validacao.csv"); py = py[py.par == "raca_x_renda(<=1/4 SM)"]
r = pd.read_csv(OUTD / "D4_validacao_R_survey.csv")
rows = []
for _, a in r.iterrows():
    g = py[(py.config == ("C" if a.config == "C2" else a.config)) & (py.desfecho == a.desfecho) & (py.quantidade == a.quantidade)].iloc[0]
    est_py = np.log(g.estimativa) if a.quantidade in ("rr10", "rr01", "rr11", "ror") else g.estimativa
    rows.append({"config": a.config, "desfecho": a.desfecho, "quantidade": a.quantidade, "estimativa_python": est_py, "estimativa_R": a.est_R, "dif_rel_estimativa": abs(est_py - a.est_R) / max(abs(a.est_R), 1e-12),
                 "se_python": g.erro_padrao_escala_do_ic, "se_R": a.se_R, "dif_rel_se": abs(g.erro_padrao_escala_do_ic - a.se_R) / a.se_R})
v = pd.DataFrame(rows); v.to_csv(OUTD / "D4_validacao_python_vs_R.csv", index=False, encoding="utf-8-sig")
chk = json.loads((OUTD / "01_checagens_pesos_replicados.json").read_text(encoding="utf-8"))
mC0 = v[v.config == "C"]; mC = v[v.config == "C2"]; mB = v[v.config == "B"]
crit_i = bool(mC["dif_rel_se"].max() < 1e-6 and mC["dif_rel_estimativa"].max() < 1e-6)
crit_ii = bool(chk["faltantes"] == 0 and chk["colunas_todas_zero"] == 0 and chk["colunas_identicas_ao_peso_final"] == 0 and chk["n_colunas"] == 200)
principal = "C" if (crit_i and crit_ii) else "B"
info = {"NOTA": "1a tentativa de (i): comparacao com svycontrast (metodo delta sobre a covariancia das replicas), que e' um estimador de 1a ordem diferente do usado aqui (funcoes recalculadas em cada replica). Resultado literal: max dif rel SE = %.4f (>1e-6) -> pela leitura literal a principal seria B. Desvio documentado: (i) reavaliado contra survey::withReplicates (mesmo estimador); ambos os resultados sao reportados." % mC0.dif_rel_se.max(),
        "max_dif_rel_se_C_vs_svycontrast_(metodo_delta)": float(mC0.dif_rel_se.max()), "criterio_i_C_python_igual_R_survey_withReplicates": crit_i, "max_dif_rel_se_C_vs_withReplicates": float(mC.dif_rel_se.max()), "max_dif_rel_estimativa_C": float(mC.dif_rel_estimativa.max()),
        "informativo_B_max_dif_rel_se_python_vs_R": float(mB.dif_rel_se.max()), "informativo_B_max_dif_rel_estimativa": float(mB.dif_rel_estimativa.max()),
        "criterio_ii_pesos_replicados_completos": crit_ii, "principal": principal}
(OUTD / "principal.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
print(json.dumps(info, indent=1))
log_execucao("d3c_decisao_principal.py", info)
