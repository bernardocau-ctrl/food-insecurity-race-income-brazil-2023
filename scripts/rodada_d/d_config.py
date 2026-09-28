# -*- coding: utf-8 -*-
"""d_config.py: caminhos (sem caminhos absolutos), leitura do layout OFICIAL do IBGE e registro de ambiente.
A raiz do projeto e' localizada subindo diretorios ate achar 'dados_ibge/'. Pode ser executado de qualquer diretorio."""
import hashlib, json, platform, re, sys, datetime
from pathlib import Path


def _find_root():
    p = Path(__file__).resolve()
    for q in [p] + list(p.parents):
        if (q / "dados_ibge").is_dir():
            return q
    raise RuntimeError("raiz do projeto (pasta com dados_ibge/) nao encontrada")


ROOT = _find_root()
ART = ROOT / "artigos" / "03_ARTIGO3_INTERSECCIONALIDADE_RACA_IA"
ZIP = ROOT / "dados_ibge" / "microdados_pnad" / "PNADC_2023_trimestre4_20251010.zip"
DOC = ROOT / "dados_ibge" / "pnadc_documentacao"
LAYOUT = DOC / "input_PNADC_trimestre4_20251010.txt"
DICT_XLS = DOC / "dicionario_PNADC_microdados_trimestre4_20260702.xls"
OUTD = ART / "MANUSCRITO_IJE_20260925" / "rodada_D"
CACHE = ART / "dados" / "rodada_d_cache"          # arquivos grandes, regeneraveis, fora do controle de versao
PUBLISHED = ART / "dados" / "v2_20260925"          # CSVs originais (resultado "original")
for d in (OUTD, CACHE):
    d.mkdir(parents=True, exist_ok=True)
Z = 1.959964
R_REPS = 200


def parse_layout():
    """Le o input oficial do IBGE: '@0021 Estrato   $7.   /* Estrato */' -> nome, posicao (1-based), largura, tipo."""
    out = {}
    for line in LAYOUT.read_text(encoding="latin1").splitlines():
        m = re.match(r"^@(\d+)\s+(\w+)\s+(\$?)(\d+)\.(\d*)\s*(?:/\*\s*(.*?)\s*\*/)?", line)
        if m:
            out[m.group(2)] = {"pos": int(m.group(1)), "largura": int(m.group(4)), "tipo": "texto" if m.group(3) else "numerico", "descricao": m.group(6) or ""}
    return out


def sha256(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


def log_execucao(nome_script, extra=None):
    """Acrescenta ao 00_ambiente_e_execucao.json versoes, entradas (SHA-256), comando e data."""
    import numpy, pandas, scipy
    try:
        import statsmodels; sm = statsmodels.__version__
    except Exception:
        sm = None
    f = OUTD / "00_ambiente_e_execucao.json"
    d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"execucoes": []}
    d["ambiente"] = {"python": sys.version.split()[0], "numpy": numpy.__version__, "pandas": pandas.__version__, "scipy": scipy.__version__, "statsmodels": sm, "sistema": platform.platform()}
    d["entradas"] = {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in (ZIP, LAYOUT, DICT_XLS) if p.exists()}
    d["execucoes"].append({"script": nome_script, "comando": "python " + " ".join([Path(sys.argv[0]).name] + sys.argv[1:]), "data_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"), **(extra or {})})
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
