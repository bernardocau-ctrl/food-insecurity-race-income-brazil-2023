# -*- coding: utf-8 -*-
"""
d9_estrato_solitario.py: o estrato com uma unica UPA.
(1) identifica o estrato e mostra o peso que ele carrega; (2) mostra como os pesos replicados tratam essa UPA (variam ou nao);
(3) mede o efeito da POLITICA de estrato solitario na configuracao B (adjust x certainty) nos estimandos principais.
Nao altera resultados.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
from d1_motor import *
from d2_dados import Dados

D = Dados(); Rn = D.W.shape[1]
n_upa_por_estrato = pd.Series(D.upa).groupby(D.estr).nunique()
lonely = n_upa_por_estrato[n_upa_por_estrato == 1].index.tolist(); assert len(lonely) == 1
h = lonely[0]; m = D.estr == h
info = {"estrato_com_1_UPA": str(D.df["Estrato"][m].iloc[0]), "upa": str(D.df["UPA"][m].iloc[0]), "domicilios": int(m.sum()), "peso_total_do_estrato": float(D.w[m].sum()), "pct_do_peso_total": float(D.w[m].sum() / D.w.sum() * 100)}
# como os pesos replicados tratam essa UPA
rel = D.W[m] / D.w[m][:, None]
info["replicados_da_UPA_solitaria"] = {"media_da_razao_peso_replicado_sobre_final": float(rel.mean()), "cv_entre_replicas_da_soma_de_pesos": float(D.W[m].sum(0).std(ddof=1) / D.W[m].sum(0).mean()),
                                        "fracao_de_replicas_com_peso_igual_ao_final": float(np.mean(np.all(np.isclose(D.W[m], D.w[m][:, None]), axis=0))), "fracao_de_replicas_com_todos_os_pesos_zero": float(np.mean(D.W[m].sum(0) == 0))}
# comparacao com estratos tipicos: CV entre replicas da soma de pesos por estrato
cv = []
for hh in np.unique(D.estr):
    mm = D.estr == hh; s = D.W[mm].sum(0); cv.append(s.std(ddof=1) / s.mean() if s.mean() > 0 else np.nan)
info["cv_entre_replicas_da_soma_de_pesos_por_estrato_(mediana; p5-p95)"] = [float(np.nanmedian(cv)), float(np.nanpercentile(cv, 5)), float(np.nanpercentile(cv, 95))]
# efeito da politica na configuracao B
rows = []
for pair, ses in (("raca_x_renda(<=1/4 SM)", D.ses_le(1)), ("raca_x_escolaridade(sem/fund. incompleto)", D.ses_edu())):
    for y_name in ("ia_total", "ia_grave"):
        y = D.y[y_name]; cell = D.cell(ses); th = cell_theta(D.w, y, cell); est = derived(th)
        Zm, _ = influence(D.w, y, cell); T = psu_totals(Zm, D.upa, D.n_psu)
        se = {p: se_delta(th, cov_strat(T, D.strat_of_psu, p)[0]) for p in ("adjust", "certainty")}
        seA = se_delta(th, cov_psu_only(T))
        for i, q in enumerate(DER):
            if q.startswith("log_"): continue
            rows.append({"par": pair, "desfecho": y_name, "quantidade": q, "se_B_adjust": se["adjust"][i], "se_B_certainty": se["certainty"][i], "dif_rel_certainty_vs_adjust_pct": (se["certainty"][i] / se["adjust"][i] - 1) * 100})
r = pd.DataFrame(rows); r.to_csv(OUTD / "D9_estrato_solitario_politica_B.csv", index=False, encoding="utf-8-sig")
info["politica_B_max_dif_rel_SE_pct_certainty_vs_adjust"] = float(r["dif_rel_certainty_vs_adjust_pct"].abs().max())
info["politica_adotada_em_B"] = "adjust (centrado na media global; equivale a survey lonely.psu='adjust'); 'certainty' (contribuicao zero) so como sensibilidade"
info["em_C_pesos_replicados"] = "a variancia vem da dispersao entre as 200 replicas; nao ha regra de estrato solitario a escolher. Como o IBGE construiu as replicas para essa UPA NAO foi verificado em fonte primaria (ver 'replicados_da_UPA_solitaria')."
(OUTD / "D9_estrato_solitario.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(info, ensure_ascii=False, indent=1))
log_execucao("d9_estrato_solitario.py", info)
