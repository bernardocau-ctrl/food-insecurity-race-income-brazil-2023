# -*- coding: utf-8 -*-
"""run_all.py: reproduz TODA a rodada D a partir do microdado bruto, na ordem D-4 -> D-1/D-2 -> D-3/D-5 -> matriz e tabelas.
Uso (de qualquer diretorio):  python scripts/rodada_d/run_all.py      [opcional: variavel de ambiente RSCRIPT com o caminho do Rscript]
Tempo aproximado: 6 a 8 minutos. Requisitos: Python 3.12 (numpy, pandas, scipy, statsmodels, python-docx), R 4.x com o pacote survey."""
import glob, os, subprocess, sys, time
from pathlib import Path
here = Path(__file__).resolve().parent
rs = os.environ.get("RSCRIPT") or next(iter(sorted(glob.glob("C:/Program Files/R/R-*/bin/Rscript.exe"))[::-1]), "Rscript")
steps = [(sys.executable, "d0_extrair.py"), (sys.executable, "d8_testes_integridade.py --autoteste"), (sys.executable, "d3_D4_desenho.py"), (rs, "d3b_validacao_R_survey.R"), (sys.executable, "d3c_decisao_principal.py"), (sys.executable, "d9_estrato_solitario.py"), (sys.executable, "d4a_testes_codigo.py"),
         (sys.executable, "d4b_D1_D2.py"), (sys.executable, "d5_D3_D5.py"), (sys.executable, "d6_matriz_e_tabelas.py"), (sys.executable, "d10_documentacao_amostra.py"), (sys.executable, "d7_relatorios.py")]
for exe, script in steps:
    t = time.time(); print(f">>> {Path(exe).name} {script}", flush=True)
    parts = script.split(); r = subprocess.run([exe, str(here / parts[0])] + parts[1:], cwd=str(here), env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode: sys.exit(f"falhou: {script}")
    print(f"    ok ({time.time() - t:.0f}s)", flush=True)
