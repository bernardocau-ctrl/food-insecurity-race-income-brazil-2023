# -*- coding: utf-8 -*-
"""d11a_export_R_reg.py: exporta as covariaveis (codificacao do codigo original) para a validacao independente das regressoes em R (d11b)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from d_config import *
from d2_dados import Dados
D = Dados()
band = np.select([D.vdi == 1, D.vdi == 2, D.vdi == 3, D.vdi == 4], [0, 1, 2, 3], default=4)
ex = pd.DataFrame({"V1028": D.w, "y_any": D.y["ia_total"], "y_sev": D.y["ia_grave"], "negra": D.negra, "mulher": D.female, "edu4": D.edu4, "rural": D.rural, "band": band, "sem_fund": (D.edu4 == 0).astype(int),
                   "rq1": (band == 0).astype(int), "rq2": (band == 1).astype(int), "rq3": (band == 2).astype(int), "rq4": (band == 3).astype(int), "cell_inc": D.cell(D.ses_le(1))})
ex.to_csv(CACHE / "R_input_reg.csv", index=False); print("ok", len(ex))
