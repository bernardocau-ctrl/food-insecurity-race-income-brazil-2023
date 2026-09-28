# -*- coding: utf-8 -*-
"""
auditoria_dados_ije_20260926.py
ETAPA 1 da auditoria (dados e amostra). NAO estima nada do artigo: reconta registros do microdado bruto
(PNADC T4 2023) e confronta com (a) o codigo preparar() de analise_bivariada_e_regressao_v2.py,
(b) o layout e o dicionario OFICIAIS do IBGE (baixados de ftp.ibge.gov.br em 25/09/2026),
(c) o arquivo derivado dados/dados_maihda_2023.csv e (d) a tabela SIDRA 9554.
Saida: MANUSCRITO_IJE_20260925/auditoria/ (csv) e imprime o resumo.
"""
import zipfile, io, sys, json
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
SAN = BASE.parent.parent
ZIP = SAN / "dados_ibge" / "microdados_pnad" / "PNADC_2023_trimestre4_20251010.zip"
OUT = BASE / "MANUSCRITO_IJE_20260925" / "auditoria"; OUT.mkdir(exist_ok=True)

# posicoes 0-based [ini, fim) conforme o layout OFICIAL (input_PNADC_trimestre4_20251010.txt, colunas 1-based @pos + largura)
SPEC = {"UPA": (11, 20), "Estrato": (20, 27), "V1008": (27, 29), "V1014": (29, 31), "V1016": (31, 32), "V1022": (32, 33),
        "V1028_15": (49, 64), "V1028_14": (49, 63), "V2001": (88, 90), "V2003": (90, 92), "V2005": (92, 94), "V2007": (94, 95),
        "V2009": (103, 106), "V2010": (106, 107), "VD3004": (1115, 1116), "VDI5009": (1278, 1279), "SD17001": (1313, 1314),
        "V1028001": (1314, 1329)}
# posicoes usadas pelo codigo do artigo (COLSPECS de analise_bivariada_e_regressao_v2.py)
ART = {"col20_23_do_codigo_antigo": (20, 23)}

with zipfile.ZipFile(ZIP) as z:
    txt = [n for n in z.namelist() if n.upper().endswith(".TXT")][0]
    with z.open(txt) as f:
        first = f.readline().decode("latin1").rstrip("\r\n")
    print("arquivo:", txt, "| comprimento da 1a linha:", len(first))
    names = list(SPEC) + list(ART); cols = [SPEC[k] for k in SPEC] + [ART[k] for k in ART]
    with z.open(txt) as f:
        df = pd.read_fwf(f, colspecs=cols, names=names, encoding="latin1", dtype=str, header=None)
for c in df.columns: df[c] = df[c].str.strip()
N = len(df); R = {}
R["linhas_brutas"] = N
print("linhas brutas:", N)

# ---------------- 1. identificacao do domicilio e da pessoa de referencia
df["V2005"] = df["V2005"].fillna("")
df["chave_dom"] = df["UPA"].fillna("") + "|" + df["V1008"].fillna("") + "|" + df["V1014"].fillna("")
R["V2005_distribuicao"] = df["V2005"].value_counts().sort_index().to_dict()
R["n_v2005_01"] = int((df["V2005"] == "01").sum())
R["n_UPA"] = int(df["UPA"].nunique()); R["n_Estrato"] = int(df["Estrato"].nunique())
R["n_chaves_dom_oficiais(UPA+V1008+V1014)"] = int(df["chave_dom"].nunique())
per = df.groupby("chave_dom")["V2005"].apply(lambda s: int((s == "01").sum()))
R["dom_com_0_responsavel"] = int((per == 0).sum()); R["dom_com_1_responsavel"] = int((per == 1).sum()); R["dom_com_2mais_responsavel"] = int((per >= 2).sum())
# id reconstruido pelo codigo do artigo
df["_is_resp"] = (df["V2005"] == "01").astype(int)
df["_dom_seq"] = df.groupby("UPA")["_is_resp"].cumsum()
df["_dom_id"] = df["UPA"] + "_" + df["_dom_seq"].astype(str)
R["n_dom_id_reconstruido"] = int(df["_dom_id"].nunique())
pairs = df[["chave_dom", "_dom_id"]].drop_duplicates()
R["pares_distintos(chave_oficial,id_reconstruido)"] = len(pairs)
R["reconstrucao_equivale_a_chave_oficial"] = bool(len(pairs) == df["chave_dom"].nunique() == df["_dom_id"].nunique())
# "V1008" do artigo e' na verdade o inicio do ESTRATO?
R["col20_23_do_codigo_antigo_distintos"] = int(df["col20_23_do_codigo_antigo"].nunique())
R["col20_23_do_codigo_antigo_igual_prefixo3_do_Estrato"] = bool((df["col20_23_do_codigo_antigo"] == df["Estrato"].str[:3]).mean() > 0.999)
R["col20_23_do_codigo_antigo_constante_dentro_UPA"] = bool((df.groupby("UPA")["col20_23_do_codigo_antigo"].nunique() == 1).all())
R["V1008_oficial_distintos_dentro_UPA_max"] = int(df.groupby("UPA")["V1008"].nunique().max())
R["Estrato_constante_dentro_UPA"] = bool((df.groupby("UPA")["Estrato"].nunique() == 1).all())

# ---------------- 2. EBIA
resp = df[df["V2005"] == "01"].copy()
R["EBIA_SD17001_resp_distribuicao"] = resp["SD17001"].fillna("(branco)").value_counts().sort_index().to_dict()
resp["ebia_ok"] = resp["SD17001"].isin(["1", "2", "3", "4"])
R["resp_com_EBIA_1a4"] = int(resp["ebia_ok"].sum()); R["resp_sem_EBIA"] = int((~resp["ebia_ok"]).sum())
outros = df[df["V2005"] != "01"]
R["nao_resp_com_SD17001_preenchida"] = int(outros["SD17001"].isin(["1", "2", "3", "4"]).sum())
R["dom_sem_responsavel_com_EBIA_em_outra_linha"] = int(df[df["chave_dom"].isin(per[per == 0].index)]["SD17001"].isin(["1", "2", "3", "4"]).sum())

# ---------------- 3. peso
for k in ["V1028_15", "V1028_14"]: resp[k + "_num"] = pd.to_numeric(resp[k], errors="coerce")
R["peso15_NaN_resp"] = int(resp["V1028_15_num"].isna().sum()); R["peso14_NaN_resp"] = int(resp["V1028_14_num"].isna().sum())
rel = ((resp["V1028_15_num"] - resp["V1028_14_num"]).abs() / resp["V1028_15_num"]).dropna()
R["peso_15_vs_14_dif_relativa_max"] = float(rel.max()); R["peso_15_vs_14_dif_relativa_media"] = float(rel.mean())
R["soma_pesos_resp_EBIA_15"] = float(resp.loc[resp.ebia_ok, "V1028_15_num"].sum())
w_all = df.assign(w=pd.to_numeric(df["V1028_15"], errors="coerce")).groupby("chave_dom")["w"].nunique()
R["dom_com_peso_nao_constante_entre_moradores"] = int((w_all > 1).sum())
R["primeiro_peso_replicado_V1028001_presente"] = bool(df["V1028001"].notna().mean() > 0.5)
R["comprimento_linha"] = len(first)

# ---------------- 4. fluxo tal como o codigo do artigo (preparar) e como o texto do manuscrito descreve
r = resp.copy()
r["peso"] = pd.to_numeric(r["V1028_14"], errors="coerce")
fl = []
fl.append(("Registros de pessoas no arquivo bruto (T4 2023)", N))
fl.append(("... com V2005 = 01 (pessoa responsavel)", int((df["V2005"] == "01").sum())))
fl.append(("... responsaveis com SD17001 em 1-4 (EBIA valida)", int(resp["ebia_ok"].sum())))
r2 = r[r.ebia_ok]
fl.append(("... com peso (V1028) numerico", int(r2["peso"].notna().sum())))
# dropna do codigo: colunas derivadas nunca sao NaN (comparacoes), logo nada e excluido por covariavel
r2 = r2[r2["peso"].notna()]
fl.append(("Domicilios analiticos segundo o codigo (preparar)", len(r2)))
fl.append(("(conferencia) domicilios distintos por chave oficial UPA+V1008+V1014 entre esses", int(r2["chave_dom"].nunique())))
fl.append(("(conferencia) UPAs distintas", int(r2["UPA"].nunique())))
fl.append(("(conferencia) Estratos distintos", int(r2["Estrato"].nunique())))
pd.DataFrame(fl, columns=["etapa", "n"]).to_csv(OUT / "fluxo_amostra.csv", index=False, encoding="utf-8-sig")

# ---------------- 5. codigos das variaveis analisadas e como o codigo os classifica
def dist(col):
    c = r2[col].fillna("(branco)").value_counts().sort_index()
    w = r2.groupby(r2[col].fillna("(branco)"))["peso"].sum(); w = (w / w.sum() * 100).reindex(c.index)
    return pd.DataFrame({"codigo": c.index, "n": c.values, "pct_ponderado": w.values.round(3)})
tabs = []
for col, lab in [("V2010", "Cor ou raca (V2010)"), ("VDI5009", "Faixa de renda per capita (VDI5009)"), ("VD3004", "Instrucao (VD3004)"), ("V2007", "Sexo (V2007)"), ("V1022", "Situacao (V1022)")]:
    t = dist(col); t.insert(0, "variavel", lab); tabs.append(t)
cod = pd.concat(tabs); cod.to_csv(OUT / "codigos_variaveis_analiticas.csv", index=False, encoding="utf-8-sig")
racmap = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indigena", "9": "Ignorado"}
# classificacao do artigo
v = pd.to_numeric(r2["V2010"], errors="coerce"); negra = v.isin([2, 4]).astype(int)
R["V2010_9_ou_branco_classificado_como_nao_negro_n"] = int(((v == 9) | v.isna()).sum())
R["V2010_9_ou_branco_classificado_como_nao_negro_pct_pond"] = float(r2.loc[(v == 9) | v.isna(), "peso"].sum() / r2["peso"].sum() * 100)
R["nao_negro_n"] = int((negra == 0).sum())
R["nao_negro_composicao_n"] = {racmap.get(k, k): int(n) for k, n in r2.loc[negra == 0, "V2010"].fillna("(branco)").value_counts().items()}
rd = pd.to_numeric(r2["VDI5009"], errors="coerce")
R["VDI5009_9_ou_branco_n(cai_em_'>2 SM', referencia)"] = int(((rd == 9) | rd.isna()).sum())
R["VDI5009_9_ou_branco_pct_pond"] = float(r2.loc[(rd == 9) | rd.isna(), "peso"].sum() / r2["peso"].sum() * 100)
R["VDI5009_valores_5a7_(>2SM)_n"] = int(rd.isin([5, 6, 7]).sum())
inst = pd.to_numeric(r2["VD3004"], errors="coerce")
R["VD3004_branco_n(cai_em_'superior', referencia)"] = int(inst.isna().sum())
R["VD3004_fora_1a7_n"] = int((~inst.isin([1, 2, 3, 4, 5, 6, 7]) & inst.notna()).sum())
R["V2007_fora_1_2_n"] = int((~pd.to_numeric(r2["V2007"], errors="coerce").isin([1, 2])).sum())
R["V1022_fora_1_2_n"] = int((~pd.to_numeric(r2["V1022"], errors="coerce").isin([1, 2])).sum())
# celulas da analise primaria afetadas
q1 = (rd == 1)
R["cel_renda_q1_n"] = int(q1.sum())
for nm, m in [("VDI5009=9", rd == 9), ("VDI5009 branco", rd.isna()), ("V2010=9", v == 9), ("V2010 branco", v.isna())]:
    R[f"n_{nm}"] = int(m.sum())

# ---------------- 6. confronto com o arquivo derivado usado nas analises (dados_maihda_2023.csv)
der = pd.read_csv(SAN / "artigos" / "03_ARTIGO3_INTERSECCIONALIDADE_RACA_IA" / "dados" / "dados_maihda_2023.csv")
R["derivado_n_linhas"] = len(der); R["derivado_soma_peso"] = float(der["peso"].sum()); R["derivado_n_upa"] = int(der["upa"].nunique())
R["derivado_peso_igual_bruto_V1028_14_(soma)"] = float(r2["peso"].sum())
R["derivado_prev_ia_total_pond_%"] = float((der["ia_total"] * der["peso"]).sum() / der["peso"].sum() * 100)
R["derivado_prev_ia_grave_pond_%"] = float((der["ia_grave"] * der["peso"]).sum() / der["peso"].sum() * 100)
# recomputo direto no bruto
e = pd.to_numeric(r2["SD17001"], errors="coerce")
R["bruto_prev_ia_total_pond_%"] = float(((e >= 2) * r2["peso"]).sum() / r2["peso"].sum() * 100)
R["bruto_prev_ia_grave_pond_%"] = float(((e == 4) * r2["peso"]).sum() / r2["peso"].sum() * 100)
# alinhamento linha a linha: ordem do arquivo e igual?
same_order = (der["upa"].astype(str).values == r2["UPA"].values).all() if len(der) == len(r2) else False
R["derivado_alinhado_linha_a_linha_com_bruto(UPA)"] = bool(same_order)
if same_order:
    R["derivado_peso_max_dif_abs_vs_bruto14"] = float(np.abs(der["peso"].values - r2["peso"].values).max())
    R["derivado_negra_vs_V2010_(2,4)_divergencias"] = int(((der["raca_cat"] == "negra").astype(int).values != negra.values).sum())

# ---------------- 7. SIDRA 9554 (domicilios por cor/raca do responsavel e situacao de SA, 2023)
s = pd.read_csv(SAN / "dados_ibge" / "pnad_continua" / "tabela_9554_EBIA_cor_raca_responsavel.csv", encoding="utf-8-sig")
s = s[(s.periodo == 2023) & (s.localidade_nome == "Brasil")]
s = s.pivot_table(index="categoria_1", columns="categoria_2", values="valor", aggfunc="sum")
R["SIDRA_9554_categorias_raca"] = list(s.index)
sid = s.copy(); sid.columns = [str(c) for c in sid.columns]
sid["_tot"] = sid["Com segurança alimentar"] + sid["Com insegurança alimentar"]; tot_col = "_tot"
mine = r2.assign(raca=r2["V2010"].map(racmap)).groupby("raca")["peso"].sum() / 1000
mine_ia = r2.assign(raca=r2["V2010"].map(racmap), ia=(e >= 2)).groupby(["raca"]).apply(lambda g: (g["peso"] * g["ia"]).sum() / 1000)
cmp = pd.DataFrame({"SIDRA_mil_dom_total": sid[tot_col], "microdado_mil_dom_total(peso14)": mine, "SIDRA_mil_dom_com_IA": sid[[c for c in sid.columns if c.lower().startswith("com inseguran")][0]], "microdado_mil_dom_com_IA": mine_ia})
cmp["dif_%_total"] = (cmp.iloc[:, 1] / cmp.iloc[:, 0] - 1) * 100; cmp["dif_%_IA"] = (cmp.iloc[:, 3] / cmp.iloc[:, 2] - 1) * 100
cmp.to_csv(OUT / "confronto_SIDRA_9554.csv", encoding="utf-8-sig"); print(cmp.round(2).to_string())

# ---------------- 8. desenho amostral
g = r2.groupby("Estrato")["UPA"].nunique()
R["UPAs_por_estrato_min"] = int(g.min()); R["UPAs_por_estrato_mediana"] = float(g.median()); R["estratos_com_1_UPA"] = int((g == 1).sum())
R["dom_por_UPA_min"] = int(r2.groupby("UPA").size().min()); R["dom_por_UPA_mediana"] = float(r2.groupby("UPA").size().median()); R["dom_por_UPA_max"] = int(r2.groupby("UPA").size().max())

json.dump(R, open(OUT / "auditoria_dados_resumo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
print(cod.to_string())
print(pd.DataFrame(fl, columns=["etapa", "n"]).to_string())
