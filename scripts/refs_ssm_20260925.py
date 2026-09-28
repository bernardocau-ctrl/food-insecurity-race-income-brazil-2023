# -*- coding: utf-8 -*-
"""Referencias do manuscrito: chave -> DOI (todos conferidos em PubMed/Crossref em 25/09/2026).
Metadados (autores, periodico, volume, paginas) vem do Crossref e ficam em cache local."""
import json, urllib.request, time
from pathlib import Path

DOIS = {
 "crenshaw1991": "10.2307/1229039", "bowleg2012": "10.2105/AJPH.2012.300750",
 "bauer2014": "10.1016/j.socscimed.2014.03.022", "bauer2019": "10.1016/j.socscimed.2019.03.018",
 "bauer2021": "10.1016/j.ssmph.2021.100798", "mahendran2022": "10.1016/j.ssmph.2022.101032",
 "jackson2016": "10.1007/s00127-016-1276-6", "rothman1980": "10.1093/oxfordjournals.aje.a113015",
 "knol2012": "10.1093/ije/dyr218", "vanderweele2014": "10.1515/em-2013-0005",
 "zou2004": "10.1093/aje/kwh090", "zou2013": "10.1177/0962280211427759",
 "andersson2005": "10.1007/s10654-005-7835-x", "merlo2018": "10.1016/j.socscimed.2017.12.026",
 "evans2018": "10.1016/j.socscimed.2017.11.011", "evans2024a": "10.1016/j.ssmph.2024.101664", "evans2024b": "10.1016/j.socscimed.2024.116898",
 "bell2024": "10.1016/j.socscimed.2024.116955", "nieves2023": "10.1016/j.healthplace.2023.103029",
 "humbert2024": "10.1371/journal.pone.0297561", "fivian2024": "10.1016/j.advnut.2024.100237",
 "heidari2016": "10.1186/s41073-016-0007-6", "horstmann2022": "10.3390/ijerph19127493",
 "vonelm2007": "10.1016/s0140-6736(07)61602-x", "linkphelan1995": "10.2307/2626958",
 "phelanlink2015": "10.1146/annurev-soc-073014-112305", "williams2019": "10.1146/annurev-publhealth-040218-043750",
 "bailey2017": "10.1016/S0140-6736(17)30569-X", "werneck2016": "10.1590/s0104-129020162610",
 "costa2026": "10.1590/1413-81232026314.09512025", "farmer2005": "10.1016/j.socscimed.2004.04.026",
 "assari2018": "10.1111/sipr.12042", "bakhtiari2022": "10.1007/s40615-021-01178-2",
 "bell2020": "10.1016/j.ssmph.2020.100561", "gundersen2015": "10.1377/hlthaff.2015.0645",
 "perezescamilla2004": "10.1093/jn/134.8.1923", "broussard2019": "10.1016/j.foodpol.2019.01.003",
 "ivers2011": "10.3945/ajcn.111.012617", "smith2017": "10.1016/j.worlddev.2017.01.006",
 "buvinic1997": "10.1086/452273", "silva2022a": "10.1590/0102-311xpt255621",
 "silva2022b": "10.1590/0102-311xpt178422", "santos2022": "10.1590/0102-311xpt130422",
 "santos2023": "10.1371/journal.pgph.0002324", "miguel2025": "10.1590/0102-311xen076325",
 "luiz2025": "10.1186/s12889-025-24427-z", "luiz2026": "10.1590/0102-311xpt165825",
 "ferreira2025": "10.1590/0102-311xpt095724", "cezimbra2022": "10.1590/0102-311xpt152322",
 "cezimbra2026a": "10.1177/03795721261442246", "cezimbra2026b": "10.1590/0102-311xpt115125", "zubizarreta2022": "10.1016/j.socscimed.2022.114871", "silva2023": "10.1371/journal.pone.0287593",
 "frohlich2008": "10.2105/AJPH.2007.114777", "lua2026": "10.1038/s41467-026-73892-6",
 "fao2025": "10.4060/cd6008en",
 "wilkes2024": "10.1016/j.socscimed.2023.116495", "evans2020": "10.1016/j.socscimed.2019.112499", "lizotte2020": "10.1016/j.socscimed.2019.112500", "bashir2026": "10.1016/j.socscimed.2026.119150", "dhunna2021": "10.17269/s41997-021-00539-y", "berning2024": "10.1002/aepp.13332", "fanton2026": "10.1590/0102-311xen161425", "axelsson2018": "10.1016/j.ssmph.2018.03.005", "reynolds2021": "10.1111/ppe.12744", "brown2016": "10.1177/0022146516645165", "kim2026": "10.1016/j.socscimed.2025.118714",
}
# ano de impressao (quando difere do 'issued' do Crossref) e sufixos para desambiguar
ANO = {"berning2024": 2024, "reynolds2021": 2021, "kim2026": 2026, "zou2013": 2013, "costa2026": 2026, "merlo2018": 2018, "evans2018": 2018, "cezimbra2026a": 2026, "cezimbra2026b": 2026}
SUFIXO = {"evans2024a": "a", "evans2024b": "b", "silva2022a": "a", "silva2022b": "b", "cezimbra2026a": "a", "cezimbra2026b": "b"}
CACHE = Path(__file__).parent / "refs_cache_20260925.json"

def carregar():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    for k, doi in DOIS.items():
        if k in cache: continue
        url = "https://api.crossref.org/works/" + doi
        for tent in range(3):
            try:
                r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "refcheck/1.0"}), timeout=40))["message"]
                cache[k] = r; break
            except Exception as e:
                time.sleep(2)
        else:
            cache[k] = None
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache

if __name__ == "__main__":
    c = carregar()
    for k in DOIS:
        r = c[k]
        if not r: print("FALHOU", k); continue
        au = r.get("author", [])
        yr = r.get("issued", {}).get("date-parts", [[None]])[0][0]
        print(f"{k:16s} {(au[0].get('family') if au else r.get('publisher'))!s:14s} n={len(au):2d} {ANO.get(k, yr)} | {r.get('container-title', [''])[0][:38]} {r.get('volume')}({r.get('issue')}) {r.get('page') or r.get('article-number')}")
