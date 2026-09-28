# -*- coding: utf-8 -*-
"""d2_dados.py: carrega o analitico gerado por d0_extrair.py e define as variaveis EXATAMENTE como o codigo original (preparar()),
com os codigos documentados. Nao muda definicao de exposicao, desfecho, populacao analitica ou pesos."""
import numpy as np, pandas as pd
from d_config import *


class Dados:
    def __init__(self):
        df = pd.read_csv(CACHE / "analitico_sem_replicados.csv.gz", dtype=str)
        n = len(df); self.n = n
        num = lambda c: pd.to_numeric(df[c], errors="coerce").values
        self.w = pd.to_numeric(df["V1028"]).values.astype(float)
        self.W = np.load(CACHE / "pesos_replicados.npz")["W"]
        sd = num("SD17001"); self.y = {"ia_total": (sd >= 2).astype(float), "ia_grave": (sd == 4).astype(float)}
        v2010 = num("V2010"); self.v2010 = v2010; self.negra = np.isin(v2010, [2, 4]).astype(int)   # codigo original: 2 e 4; 9 (ignorado) fica em nao negro
        self.vdi = num("VDI5009")                                                                    # 1..7 e 9 (ignorado; cai em '>2 SM' no codigo original)
        vd = num("VD3004"); self.edu4 = np.select([np.isin(vd, [1, 2]), np.isin(vd, [3, 4]), vd == 5], [0, 1, 2], default=3)  # 0 sem_fund,1 fund_med,2 medio,3 superior
        self.female = (num("V2007") == 2).astype(int); self.rural = (num("V1022") == 2).astype(int)
        self.upa = pd.factorize(df["UPA"])[0]; self.n_psu = self.upa.max() + 1
        self.estr = pd.factorize(df["Estrato"])[0]
        s = np.zeros(self.n_psu, int); s[self.upa] = self.estr; self.strat_of_psu = s
        assert (s[self.upa] == self.estr).all(), "UPA em mais de um estrato"
        self.df = df
        self.ign_raca = (self.v2010 == 9); self.ign_renda = (self.vdi == 9)

    # exposicoes
    def ses_le(self, cut):
        """cut: 1 -> <=1/4 SM (VDI5009=1); 2 -> <=1/2 SM (1-2); 3 -> <=1 SM (1-3); codigo 9 nunca e' 'baixa renda' (como no codigo original)"""
        return np.isin(self.vdi, list(range(1, cut + 1))).astype(int)

    def ses_edu(self): return (self.edu4 == 0).astype(int)

    def cell(self, ses): return (self.negra + 2 * np.asarray(ses)).astype(int)

    def covs_std(self):
        """covariaveis do modelo padronizado (D-1): sexo registrado, escolaridade 4 categorias (3 indicadores), residencia rural"""
        E = np.column_stack([(self.edu4 == k) for k in (1, 2, 3)]).astype(float)
        return np.column_stack([self.female, E, self.rural]).astype(float)
