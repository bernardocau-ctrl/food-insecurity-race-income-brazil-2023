# -*- coding: utf-8 -*-
"""matriz_numeros_rev3_rev4.py: matriz "numero anterior (rev3) -> numero final (rev4) -> arquivo/coluna de origem -> metodo de variancia".
Une as abas de rastreabilidade C_Traceability_table_rev3.xlsx e C_Traceability_table_rev4.xlsx (cada numero impresso registra arquivo, filtro e coluna).
Saidas: H_matriz_numeros_rev3_para_rev4.csv/.xlsx e H_matriz_resumo.json"""
import json, re
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "MANUSCRITO_IJE_20260925"
SHEETS = ["Abstract", "Text_Intro_Methods", "Text_Results_Discussion", "Tables", "Supplement_Table_S2"]


def load(path):
    x = pd.read_excel(path, sheet_name=None); frames = []
    for s in SHEETS:
        if s in x:
            d = x[s].copy(); d["sheet"] = s; d["occ"] = d.groupby(["sheet", "item"]).cumcount(); frames.append(d)
    return pd.concat(frames, ignore_index=True)


a = load(OUT / "C_Traceability_table_rev3.xlsx"); b = load(OUT / "C_Traceability_table_rev4.xlsx")
NUM = re.compile(r"−?-?\d[\d  ]*\.?\d*")
def toks(s): return [t.replace("−", "-").replace(" ", "").replace(" ", "") for t in NUM.findall(re.sub(r"95%", "", str(s)))]
def variance_rev3(src):
    s = str(src)
    if "m1_maihda" in s or "m2_maihda" in s or "m3_maihda" in s or "calcula_auc" in s: return "MAIHDA: unweighted mixed model"
    if "t2_pares" in s or "t6_estrat" in s or "t3_conj" in s or "atenuacao" in s or "t1_desc" in s or "t5_grad" in s or "t7_tri" in s or "t4_grad" in s:
        return "A (earlier): clustered on PSU; Taylor linearization / delta method / robust sandwich"
    return "not applicable"
m = a.merge(b, on=["sheet", "item", "occ"], how="outer", suffixes=("_rev3", "_rev4"), indicator=True)
rows = []
for _, r in m.iterrows():
    prev = r.get("printed_rev3"); new = r.get("printed_rev4"); mg = r["_merge"]
    if mg == "both":
        tp, tn = toks(prev), toks(new)
        if str(prev) == str(new): tipo = "no change"
        elif tp and tn and tp[0] == tn[0] and len(tp) == len(tn): tipo = "point estimate unchanged; interval or rounding of the interval changed (variance method)"
        else: tipo = "printed value changed"
    elif mg == "right_only": tipo = "new in rev4 (added analysis or component interval)"
    else: tipo = "removed from the text (cut or replaced)"
    rows.append({"sheet": r["sheet"], "location_rev4": r.get("location_rev4", ""), "item": r["item"], "previous_number_rev3": prev if mg != "right_only" else "", "final_number_rev4": new if mg != "left_only" else "",
                 "change_type": tipo, "source_rev4_file_filter_column": r.get("source_rev4", "") if mg != "left_only" else "", "variance_method_rev4": r.get("variance_method", "") if mg != "left_only" else "",
                 "source_rev3": r.get("source_rev3", "") if mg != "right_only" else "", "variance_method_rev3": variance_rev3(r.get("source_rev3", "")) if mg != "right_only" else ""})
M = pd.DataFrame(rows); M.to_csv(OUT / "H_matriz_numeros_rev3_para_rev4.csv", index=False, encoding="utf-8-sig")
with pd.ExcelWriter(OUT / "H_matriz_numeros_rev3_para_rev4.xlsx", engine="openpyxl") as w:
    M.to_excel(w, sheet_name="Matrix", index=False); M[M.change_type.str.startswith(("point estimate", "printed value"))].to_excel(w, sheet_name="Changed values", index=False)
res = {"linhas": len(M), "por_tipo": M.change_type.value_counts().to_dict(), "valores_impressos_alterados_ponto_estimado": int((M.change_type == "printed value changed").sum())}
# sem dados historicos (v2) nas fontes da rev4 e todas as fontes com metodo de variancia identificado
b_src = b["source"].astype(str); res["fontes_rev4_apontando_para_v2_20260925"] = int(b_src.str.contains("v2_20260925").sum())
res["fontes_rev4_sem_metodo_de_variancia_identificado"] = int((b.get("variance_method", pd.Series(dtype=str)).astype(str) == "").sum()) if "variance_method" in b else "coluna ausente"
res["fontes_rev4_por_metodo"] = b["variance_method"].value_counts().to_dict() if "variance_method" in b else {}
(OUT / "H_matriz_resumo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(res, ensure_ascii=False, indent=1))
print(M[M.change_type == "printed value changed"][["sheet", "item", "previous_number_rev3", "final_number_rev4"]].to_string())
