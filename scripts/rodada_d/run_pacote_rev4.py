# -*- coding: utf-8 -*-
"""
run_pacote_rev4.py: reproduz TODO o pacote IJE rev4 a partir do microdado bruto:
rodada D (run_all.py) -> regressoes com C (d11) -> validacao independente em R (d11a-d11c) -> figuras -> coerencia -> manuscrito, suplemento e tabelas
-> auditorias -> verificacao do resumo -> matriz rev3->rev4 -> notas (d13).
Uso (de qualquer diretorio):  python scripts/rodada_d/run_pacote_rev4.py [--limpo]
--limpo: antes de rodar, guarda um instantaneo das saidas, APAGA cache, saidas da rodada D, dados/v3_rodadaD_C e saidas rev4, regera tudo e compara com o instantaneo
(CSV/JSON/MD byte a byte; .docx pelo texto; .xlsx pelas abas). Os CSV historicos (dados/v2_20260925) nunca sao apagados.
Tempo: ~30 minutos. Requer Python 3.12 (numpy, pandas, scipy, statsmodels, python-docx, openpyxl, matplotlib) e R 4.x com survey e jsonlite.
"""
import glob, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import pandas as pd
from docx import Document

HERE = Path(__file__).resolve().parent; SC = HERE.parent; ART = SC.parent
OUT = ART / "MANUSCRITO_IJE_20260925"; RD = OUT / "rodada_D"; V3 = ART / "dados" / "v3_rodadaD_C"; CACHE = ART / "dados" / "rodada_d_cache"
RS = os.environ.get("RSCRIPT") or next(iter(sorted(glob.glob("C:/Program Files/R/R-*/bin/Rscript.exe"))[::-1]), "Rscript")
PY = sys.executable
STEPS = [(PY, HERE / "run_all.py"), (PY, HERE / "d11_regressoes_C.py"), (PY, HERE / "d11a_export_R_reg.py"), (RS, HERE / "d11b_validacao_R_regressoes.R"), (PY, HERE / "d11c_comparar_validacao_R.py"),
         (PY, SC / "figuras_ije_20260925.py"), (PY, SC / "coerencia_ije_rev4.py"), (PY, SC / "montar_ije_20260925.py"), (PY, SC / "auditoria_estimativas_rev4.py"), (PY, SC / "auditoria_submissao_rev4.py"),
         (PY, SC / "verificacao_abstract_rev4.py"), (PY, SC / "matriz_numeros_rev3_rev4.py"), (PY, SC / "d13_entregaveis_rev4.py")]
COMPARAR = ["*.csv", "*.json"]
EXCL = {"00_ambiente_e_execucao.json", "_reproducao_comparacao.json", "RELATORIO_TECNICO_RODADA_D.md"}


def arquivos():
    """arquivos de saida comparaveis (caminho relativo a ART)"""
    out = []
    for base, pats in ((RD, ["*.csv", "*.json"]), (V3, ["*.csv"]), (OUT / "auditoria", ["*.csv", "*.json"]), (OUT, ["F_abstract_number_check_rev4.csv", "H_matriz_numeros_rev3_para_rev4.csv", "C_coherence_checks_rev4.csv"])):
        for pat in pats: out += [p for p in base.glob(pat) if p.name not in EXCL]
    out += [OUT / "A_Manuscript_IJE_rev4.docx", OUT / "B_Supplementary_material_IJE_rev4.docx", OUT / "Tables_1-3_IJE_rev4.docx", OUT / "C_Traceability_table_rev4.xlsx", OUT / "H_matriz_numeros_rev3_para_rev4.xlsx"]
    return [p for p in out if p.exists()]


def texto_docx(p):
    d = Document(str(p)); t = [x.text for x in d.paragraphs]
    for tb in d.tables:
        for r in tb.rows: t += [c.text for c in r.cells]
    return "\n".join(t)


def xlsx_abas(p): return {k: v.fillna("").astype(str).values.tolist() for k, v in pd.read_excel(p, sheet_name=None).items()}


def snapshot(dest):
    for p in arquivos():
        rel = p.relative_to(ART); (dest / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest / rel)


def limpar():
    shutil.rmtree(CACHE, ignore_errors=True); shutil.rmtree(V3, ignore_errors=True)
    for p in list(RD.glob("*")):
        if p.name != "PROTOCOLO_RODADA_D.md" and p.is_file(): p.unlink()
    for p in (OUT / "auditoria").glob("*"):
        if p.is_file() and p.name.endswith("_rev4.csv") or p.name in ("auditoria_submissao_resumo_rev4.md",): p.unlink()
    for p in OUT.glob("*_rev4.*"): p.unlink()
    for n in ("H_matriz_numeros_rev3_para_rev4.csv", "H_matriz_numeros_rev3_para_rev4.xlsx", "H_matriz_resumo.json", "EMENDA_METODOLOGICA_pos_protocolo.md", "RELATORIO_REPRODUCAO_rev4.md", "CONTAGEM_DE_PALAVRAS_rev4.md", "BLOQUEADORES_rev4.md", "DIVIDA_TECNICA_separada.md", "_reproducao_comparacao.json"):
        (OUT / n).unlink(missing_ok=True)


def comparar(snap):
    difer = []; n = 0
    for p in arquivos():
        q = snap / p.relative_to(ART)
        if not q.exists(): difer.append(f"{p.name} (novo)"); continue
        n += 1
        if p.suffix == ".docx": ok = texto_docx(p) == texto_docx(q)
        elif p.suffix == ".xlsx": ok = xlsx_abas(p) == xlsx_abas(q)
        else: ok = p.read_bytes() == q.read_bytes()
        if not ok: difer.append(p.name)
    return n, difer


if __name__ == "__main__":
    limpo = "--limpo" in sys.argv; snap = None
    if limpo:
        snap = Path(tempfile.mkdtemp(prefix="snap_rev4_")); snapshot(snap); limpar(); print("instantaneo em", snap, "| saidas apagadas", flush=True)
    for exe, script in STEPS:
        t = time.time(); print(f">>> {Path(exe).name} {script.name}", flush=True)
        r = subprocess.run([str(exe), str(script)], cwd=str(HERE), env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if r.returncode: sys.exit(f"falhou: {script.name}")
        print(f"    ok ({time.time() - t:.0f}s)", flush=True)
    if snap is not None:
        n, dif = comparar(snap)
        res = {"n_comparados": n, "n_diferentes": len(dif), "diferentes": dif, "resumo": f"{n - len(dif)} de {n} arquivos idênticos ({len(dif)} diferentes)"}
        (OUT / "_reproducao_comparacao.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8"); print(res["resumo"], dif)
        subprocess.run([str(PY), str(SC / "d13_entregaveis_rev4.py")], cwd=str(HERE), check=True)
        shutil.rmtree(snap, ignore_errors=True)
