# -*- coding: utf-8 -*-
"""
d0_extrair.py
Le o microdado PNADC T4 2023 com as POSICOES DO LAYOUT OFICIAL (input_PNADC_trimestre4_20251010.txt) e grava, para as pessoas
de referencia (V2005 = 01), as variaveis usadas, o Estrato, o peso V1028 (15 caracteres) e os 200 pesos replicados.
Saida (cache, regeneravel): dados/rodada_d_cache/analitico.npz e analitico_sem_replicados.csv.gz;
documentacao: rodada_D/01_layout_variaveis_usadas.csv e 01_fluxo_amostra_reproduzido.csv.
Nao estima nada.
"""
import zipfile, sys, io
import numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *

lay = parse_layout()
REP = [f"V1028{i:03d}" for i in range(1, R_REPS + 1)]
NEED = ["UF", "UPA", "Estrato", "V1008", "V1014", "V1016", "V1022", "V1028", "V2005", "V2007", "V2009", "V2010", "VD3004", "VDI5009", "SD17001"] + REP
miss = [v for v in NEED if v not in lay]
assert not miss, miss
CH = 40000


def field(arr, name):
    a = lay[name]["pos"] - 1; w = lay[name]["largura"]
    return np.ascontiguousarray(arr[:, a:a + w]).view(f"S{w}").ravel()


tot = 0; keep = {k: [] for k in NEED}; nlin_chunks = []; ALL = {"UPA": [], "V1008": [], "V1014": [], "V2005": []}
n_v2005 = {}
with zipfile.ZipFile(ZIP) as z:
    txt = [n for n in z.namelist() if n.upper().endswith(".TXT")][0]
    with z.open(txt) as f:
        first = f.readline(); L = len(first)
    with z.open(txt) as f:
        while True:
            buf = f.read(L * CH)
            if not buf: break
            assert len(buf) % L == 0, "linha incompleta"
            arr = np.frombuffer(buf, dtype=np.uint8).reshape(-1, L)
            assert (arr[:, -1] == 10).all(), "terminador de linha inesperado"
            tot += len(arr)
            v2005 = field(arr, "V2005")
            for _k in ALL: ALL[_k].append(field(arr, _k))
            for k, c in zip(*np.unique(v2005, return_counts=True)): n_v2005[k.decode().strip()] = n_v2005.get(k.decode().strip(), 0) + int(c)
            m = np.char.strip(v2005) == b"01"
            sub = arr[m]
            for v in NEED:
                keep[v].append(field(sub, v))
print("linhas brutas:", tot, "| comprimento da linha (com terminador):", L)
S = {v: np.concatenate(keep[v]) for v in NEED}
# ---- integridade da identificacao de domicilio e pessoa de referencia (TODAS as linhas do arquivo)
al = pd.DataFrame({k: np.char.strip(np.concatenate(v)).astype(str) for k, v in ALL.items()})
al["chave"] = al["UPA"] + "|" + al["V1008"] + "|" + al["V1014"]
al["resp"] = (al["V2005"] == "01").astype(int)
por_dom = al.groupby("chave")["resp"].sum()
al["_seq"] = al.groupby("UPA")["resp"].cumsum(); al["_id_reconstruido"] = al["UPA"] + "_" + al["_seq"].astype(str)
par = al[["chave", "_id_reconstruido"]].drop_duplicates()
INTEG = {"linhas_pessoas": int(len(al)), "n_chaves_oficiais_UPA_V1008_V1014": int(al["chave"].nunique()), "dom_com_0_responsavel": int((por_dom == 0).sum()), "dom_com_1_responsavel": int((por_dom == 1).sum()),
         "dom_com_2mais_responsaveis": int((por_dom >= 2).sum()), "n_linhas_V2005_01": int(al["resp"].sum()), "n_ids_reconstruidos_pelo_codigo_antigo": int(al["_id_reconstruido"].nunique()),
         "pares_distintos_chave_id": int(len(par)), "id_reconstruido_equivale_a_chave_oficial": bool(len(par) == al["chave"].nunique() == al["_id_reconstruido"].nunique()),
         "V2005_distribuicao": {k: int(v) for k, v in al["V2005"].value_counts().sort_index().items()}}

n = len(S["V2005"])
dec = lambda a: np.char.strip(a.astype(str)) if a.dtype.kind == "S" else a
dfs = pd.DataFrame({v: np.char.decode(S[v], "latin1") for v in NEED if v not in REP})
for c in dfs.columns: dfs[c] = dfs[c].str.strip()
dfs["V1028"] = dfs["V1028"].astype(float)
# --- fluxo e checagens de identificacao
chave = dfs["UPA"] + "|" + dfs["V1008"] + "|" + dfs["V1014"]
fluxo = [("Registros de pessoas no arquivo bruto", tot), ("Linhas com V2005 = 01 (pessoa de referencia)", n),
         ("Chaves de domicilio distintas (UPA+V1008+V1014) entre as pessoas de referencia", int(chave.nunique())),
         ("Pessoas de referencia com SD17001 em 1-4", int(dfs["SD17001"].isin(list("1234")).sum())),
         ("Pessoas de referencia com V1028 numerico > 0", int((dfs["V1028"] > 0).sum())),
         ("UPAs distintas", int(dfs["UPA"].nunique())), ("Estratos distintos (variavel oficial Estrato)", int(dfs["Estrato"].nunique())),
         ("Estratos com uma unica UPA", int((dfs.groupby("Estrato")["UPA"].nunique() == 1).sum()))]
pd.DataFrame(fluxo, columns=["etapa", "n"]).to_csv(OUTD / "01_fluxo_amostra_reproduzido.csv", index=False, encoding="utf-8-sig")
assert n == 173676 and dfs["SD17001"].isin(list("1234")).all()
# --- pesos replicados
W = np.empty((n, R_REPS));
for j, v in enumerate(REP): W[:, j] = np.char.strip(S[v]).astype(float)
chk = {"faltantes": int(np.isnan(W).sum()), "colunas_todas_zero": int((W.sum(0) == 0).sum()), "colunas_identicas_ao_peso_final": int(sum(np.allclose(W[:, j], dfs["V1028"].values) for j in range(R_REPS))),
       "n_colunas": R_REPS, "soma_pesos_final": float(dfs["V1028"].sum()), "media_das_somas_replicadas": float(W.sum(0).mean()), "cv_somas_replicadas": float(W.sum(0).std(ddof=1) / W.sum(0).mean()),
       "proporcao_de_pesos_replicados_zero": float((W == 0).mean())}
print(chk)
# --- layout usado
rows = []
for v in ["UF", "UPA", "Estrato", "V1008", "V1014", "V1016", "V1022", "V1028", "V2005", "V2007", "V2010", "VD3004", "VDI5009", "SD17001", "V1028001", "V1028200"]:
    a = lay[v]; nd = int(dfs[v].nunique()) if v in dfs.columns else None
    rows.append({"variavel": v, "posicao_inicial_1based": a["pos"], "largura": a["largura"], "tipo": a["tipo"], "descricao_layout_IBGE": a["descricao"], "valores_distintos_nas_pessoas_de_referencia": nd})
pd.DataFrame(rows).to_csv(OUTD / "01_layout_variaveis_usadas.csv", index=False, encoding="utf-8-sig")
# --- codigos de estrato: fatorizacao
dfs["estrato_id"] = pd.factorize(dfs["Estrato"])[0]; dfs["upa_id"] = pd.factorize(dfs["UPA"])[0]
# ordem original preservada; alinhamento com o arquivo derivado usado nas analises originais
der = pd.read_csv(ART / "dados" / "dados_maihda_2023.csv", usecols=["upa", "peso"])
alinh = bool(len(der) == n and (der["upa"].astype(str).values == dfs["UPA"].values).all())
peso14 = np.array([float(x[:14]) for x in dfs["V1028"].map(lambda v: f"{v:015.8f}")]) if False else None
chk.update({"derivado_original_alinhado_linha_a_linha_pela_UPA": alinh, "derivado_peso_max_dif_relativa_vs_V1028_15": float((np.abs(der["peso"].values - dfs["V1028"].values) / dfs["V1028"].values).max()) if alinh else None})
dfs.to_csv(CACHE / "analitico_sem_replicados.csv.gz", index=False)
np.savez_compressed(CACHE / "pesos_replicados.npz", W=W)
(OUTD / "01_integridade_amostra.json").write_text(json.dumps(INTEG, ensure_ascii=False, indent=1), encoding="utf-8")
(OUTD / "01_checagens_pesos_replicados.json").write_text(json.dumps(chk, ensure_ascii=False, indent=1), encoding="utf-8")
log_execucao("d0_extrair.py", {"linhas_brutas": tot, "pessoas_de_referencia": n})
print("ok")
