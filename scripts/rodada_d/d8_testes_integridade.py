# -*- coding: utf-8 -*-
"""
d8_testes_integridade.py: testes automatizados de integridade da amostra e do desenho (falham com codigo de saida 1 se algum quebrar).
Testes: (1) 173.676 pessoas responsaveis; (2) chave oficial UPA+V1008+V1014 unica; (3) exatamente um responsavel por domicilio;
(4) EBIA valida (SD17001 em 1-4) e peso numerico > 0 em todos; (5) Estrato com 573 valores, nome/posicao oficiais, constante dentro da UPA;
(6) 200 colunas de pesos replicados presentes no layout e nos dados, sem faltantes; (7) ID reconstruido == chave oficial;
(8) COLSPECS/NOMES do leitor legado == layout oficial (teria falhado com o rotulo antigo "V1008" em 20-23 e o peso de 14 caracteres);
(9) o leitor legado corrigido reproduz a amostra e os pesos originais (rel. <= 1e-8).
`--autoteste` prova que cada teste FALHA quando o dado e' corrompido (testes de mutacao). Uso: python d8_testes_integridade.py [--autoteste]
"""
import ast, copy, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *

HELPER = ROOT / "analise_bivariada_e_regressao_v2.py"
ESPERADO = {"n_responsaveis": 173676, "n_estratos": 573, "n_replicados": 200}


def _lista(src, nome):
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == nome: return ast.literal_eval(node.value)


def contexto():
    df = pd.read_csv(CACHE / "analitico_sem_replicados.csv.gz", dtype=str)
    src = HELPER.read_text(encoding="utf-8")
    return {"integ": json.loads((OUTD / "01_integridade_amostra.json").read_text(encoding="utf-8")), "df": df, "W": np.load(CACHE / "pesos_replicados.npz")["W"], "lay": parse_layout(),
            "colspecs": _lista(src, "COLSPECS"), "nomes": _lista(src, "NOMES")}


def t1_n_responsaveis(c):
    assert c["integ"]["n_linhas_V2005_01"] == ESPERADO["n_responsaveis"], f"V2005=01: {c['integ']['n_linhas_V2005_01']}"
    assert len(c["df"]) == ESPERADO["n_responsaveis"], f"linhas analiticas: {len(c['df'])}"


def t2_chave_oficial_unica(c):
    d = c["df"]; k = d["UPA"] + "|" + d["V1008"] + "|" + d["V1014"]
    assert k.is_unique, f"chave oficial repetida em {int(k.duplicated().sum())} linhas"
    assert c["integ"]["n_chaves_oficiais_UPA_V1008_V1014"] == c["integ"]["n_linhas_V2005_01"], "n de chaves != n de responsaveis"


def t3_um_responsavel_por_domicilio(c):
    i = c["integ"]
    assert i["dom_com_0_responsavel"] == 0 and i["dom_com_2mais_responsaveis"] == 0, f"0 resp: {i['dom_com_0_responsavel']}; 2+ resp: {i['dom_com_2mais_responsaveis']}"
    assert i["dom_com_1_responsavel"] == i["n_chaves_oficiais_UPA_V1008_V1014"], "domicilios com exatamente 1 responsavel != n de chaves"


def t4_ebia_e_peso(c):
    d = c["df"]; assert d["SD17001"].isin(list("1234")).all(), "SD17001 fora de 1-4"
    w = pd.to_numeric(d["V1028"], errors="coerce"); assert w.notna().all() and (w > 0).all(), "peso ausente ou <= 0"


def t5_estrato(c):
    d = c["df"]; L = c["lay"]["Estrato"]
    assert (L["pos"], L["largura"]) == (21, 7), f"layout do Estrato: {L}"
    assert d["Estrato"].nunique() == ESPERADO["n_estratos"], f"Estrato com {d['Estrato'].nunique()} valores"
    assert (d.groupby("UPA")["Estrato"].nunique() == 1).all(), "Estrato nao e' constante dentro da UPA"


def t6_pesos_replicados(c):
    nomes = [f"V1028{i:03d}" for i in range(1, ESPERADO["n_replicados"] + 1)]
    faltam = [n for n in nomes if n not in c["lay"]]; assert not faltam, f"colunas ausentes no layout: {faltam[:3]}"
    W = c["W"]; assert W.shape == (len(c["df"]), ESPERADO["n_replicados"]), f"matriz de pesos replicados {W.shape}"
    assert np.isfinite(W).all(), "pesos replicados faltantes ou nao finitos"
    assert (W.sum(0) > 0).all(), "coluna de peso replicado toda zerada"


def t7_id_reconstruido(c):
    assert c["integ"]["id_reconstruido_equivale_a_chave_oficial"], "ID reconstruido difere da chave oficial"


def t8_colspecs_do_leitor_legado(c):
    erros = []
    for nome, (a, b) in zip(c["nomes"], c["colspecs"]):
        if nome in c["lay"]:
            L = c["lay"][nome]
            if (a + 1, b - a) != (L["pos"], L["largura"]): erros.append(f"{nome}: leitor ({a + 1}, {b - a}) x oficial ({L['pos']}, {L['largura']})")
    assert not erros, "; ".join(erros)
    assert len(c["nomes"]) == len(c["colspecs"]), "NOMES e COLSPECS com tamanhos diferentes"


def t9_leitor_legado_reproduz(c):
    """executa ler_microdados()+preparar() do leitor legado corrigido (subprocesso) e compara com a amostra e os pesos originais"""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "r.pkl"
        code = f"import sys; sys.path.insert(0, r'{ROOT}'); import analise_bivariada_e_regressao_v2 as m; r = m.preparar(m.ler_microdados()); r[['upa','peso','ebia','negra','dom_id']].to_pickle(r'{out}')"
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT))
        assert r.returncode == 0, r.stderr[-400:]
        x = pd.read_pickle(out)
    assert len(x) == ESPERADO["n_responsaveis"], f"preparar() devolveu {len(x)} linhas"
    der = pd.read_csv(ART / "dados" / "dados_maihda_2023.csv", usecols=["upa", "peso"])
    assert (der["upa"].astype(str).values == x["upa"].astype(str).values).all(), "UPA em ordem diferente do derivado original"
    rel = float((np.abs(der["peso"].values - x["peso"].values) / der["peso"].values).max())
    assert rel <= 1e-8, f"peso: diferenca relativa maxima {rel:.2e} vs derivado original"
    c["_t9_dif_rel_peso_vs_derivado_original"] = rel


TESTES = [t1_n_responsaveis, t2_chave_oficial_unica, t3_um_responsavel_por_domicilio, t4_ebia_e_peso, t5_estrato, t6_pesos_replicados, t7_id_reconstruido, t8_colspecs_do_leitor_legado]
LENTOS = [t9_leitor_legado_reproduz]


def rodar(c, testes):
    res = []
    for t in testes:
        try: t(c); res.append((t.__name__, True, ""))
        except AssertionError as e: res.append((t.__name__, False, str(e)))
    return res


def mutar(c, nome):
    m = {k: (v.copy() if hasattr(v, "copy") else copy.deepcopy(v)) for k, v in c.items() if not k.startswith("_")}
    d = m["df"]
    if nome == "remove_um_responsavel": m["df"] = d.iloc[:-1]; m["W"] = m["W"][:-1]; m["integ"]["n_linhas_V2005_01"] -= 1
    elif nome == "chave_duplicada": d.loc[d.index[1], ["UPA", "V1008", "V1014"]] = d.loc[d.index[0], ["UPA", "V1008", "V1014"]].values
    elif nome == "domicilio_com_2_responsaveis": m["integ"]["dom_com_2mais_responsaveis"] = 1; m["integ"]["dom_com_1_responsavel"] -= 1
    elif nome == "peso_ausente": d.loc[d.index[5], "V1028"] = ""
    elif nome == "ebia_invalida": d.loc[d.index[5], "SD17001"] = "9"
    elif nome == "estrato_com_572_valores": d.loc[d["Estrato"] == d["Estrato"].iloc[0], "Estrato"] = d["Estrato"].iloc[-1]
    elif nome == "falta_coluna_replicada": del m["lay"]["V1028137"]
    elif nome == "matriz_replicados_199": m["W"] = m["W"][:, :199]
    elif nome == "id_reconstruido_diferente": m["integ"]["id_reconstruido_equivale_a_chave_oficial"] = False
    elif nome == "rotulo_antigo_V1008_em_20_23": m["nomes"] = [("V1008" if n == "Estrato" else n) for n in m["nomes"]]; m["colspecs"] = [(20, 23) if cs == (20, 27) else cs for cs in m["colspecs"]]; m["nomes"] = [n for n in m["nomes"]]
    elif nome == "peso_de_14_caracteres": m["colspecs"] = [(49, 63) if cs == (49, 64) else cs for cs in m["colspecs"]]
    m["df"] = m["df"] if isinstance(m["df"], pd.DataFrame) else d
    return m


MUTACOES = {"remove_um_responsavel": "t1_n_responsaveis", "chave_duplicada": "t2_chave_oficial_unica", "domicilio_com_2_responsaveis": "t3_um_responsavel_por_domicilio", "peso_ausente": "t4_ebia_e_peso",
            "ebia_invalida": "t4_ebia_e_peso", "estrato_com_572_valores": "t5_estrato", "falta_coluna_replicada": "t6_pesos_replicados", "matriz_replicados_199": "t6_pesos_replicados",
            "id_reconstruido_diferente": "t7_id_reconstruido", "rotulo_antigo_V1008_em_20_23": "t8_colspecs_do_leitor_legado", "peso_de_14_caracteres": "t8_colspecs_do_leitor_legado"}

if __name__ == "__main__":
    c = contexto(); res = rodar(c, TESTES + LENTOS); rows = [{"teste": n, "resultado": "PASS" if ok else "FALHA", "detalhe": msg} for n, ok, msg in res]
    out = {"testes": rows, "t9_dif_rel_peso_vs_derivado_original": c.get("_t9_dif_rel_peso_vs_derivado_original")}
    if "--autoteste" in sys.argv:
        auto = []
        for mut, alvo in MUTACOES.items():
            r = dict((n, ok) for n, ok, _ in rodar(mutar(c, mut), TESTES))
            auto.append({"mutacao": mut, "teste_que_deve_falhar": alvo, "falhou_como_esperado": (r[alvo] is False), "outros_testes_que_falharam": [k for k, v in r.items() if v is False and k != alvo]})
        out["autoteste_mutacao"] = auto
    (OUTD / "D8_testes_integridade.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUTD / "D8_testes_integridade.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows).to_string())
    if "--autoteste" in sys.argv: print(pd.DataFrame(out["autoteste_mutacao"]).to_string())
    log_execucao("d8_testes_integridade.py", {"todos_pass": all(r["resultado"] == "PASS" for r in rows)})
    bad = [r for r in rows if r["resultado"] != "PASS"] + ([a for a in out.get("autoteste_mutacao", []) if not a["falhou_como_esperado"]])
    sys.exit(1 if bad else 0)
