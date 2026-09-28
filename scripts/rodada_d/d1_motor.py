# -*- coding: utf-8 -*-
"""
d1_motor.py: motor de estimacao (numpy) para a rodada D. Estimandos como funcoes das 4 prevalencias de celula theta = (p00, p10, p01, p11),
variancia por (A) linearizacao com UPA, (B) linearizacao com UPA em Estrato, (C) pesos replicados (bootstrap de Rao-Wu-Yue, IBGE).
Formulas
  celula c = negra + 2*ses: 0=(0,0) referencia, 1=(1,0) so raca, 2=(0,1) so SES, 3=(1,1) ambos
  p_k = sum_i w_i y_i 1[c_i=k] / sum_i w_i 1[c_i=k]
  RR_k = p_k / p_00 ; RERI = RR_11 - RR_10 - RR_01 + 1 ; RERI_esperado = (RR_10 - 1)(RR_01 - 1) ; RoR = RR_11 / (RR_10 RR_01)
  componentes (pp): raca = p10 - p00 ; SES = p01 - p00 ; interacao = p11 - p10 - p01 + p00 ; conjunta = p11 - p00 ; participacao = interacao / conjunta
  identidade: interacao = RERI * p00
Variancia
  A: V = n/(n-1) sum_j (t_j - tbar)(t_j - tbar)'  , t_j = total das funcoes de influencia na UPA j (todas as UPAs entram, inclusive as sem casos)
  B: V = sum_h n_h/(n_h-1) sum_{j in h}(t_j - tbar_h)(t_j - tbar_h)' ; estrato com 1 UPA: centrado na media global (lonely.psu="adjust")
  C: V = sum_r (theta_r - theta)^2 / (R - 1) , centrado na estimativa da amostra completa (survey::svrepdesign(type="bootstrap", mse=TRUE), R = 200)
  Delta (A, B): J V J' com J por diferencas finitas centrais das funcoes derivadas.
"""
import numpy as np
from d_config import Z

DER = ["p00", "p10", "p01", "p11", "rr10", "rr01", "rr11", "reri", "reri_esperado", "ror", "comp_raca_pp", "comp_ses_pp", "interacao_pp", "conjunta_pp", "participacao_pct",
       "log_rr10", "log_rr01", "log_rr11", "log_ror"]
LOGSCALE = {"rr10": "log_rr10", "rr01": "log_rr01", "rr11": "log_rr11", "ror": "log_ror"}


def derived(th):
    """th: (...,4) prevalencias em proporcao. Devolve (...,len(DER)); p em %, componentes em pp."""
    th = np.asarray(th, float); p00, p10, p01, p11 = th[..., 0], th[..., 1], th[..., 2], th[..., 3]
    rr10, rr01, rr11 = p10 / p00, p01 / p00, p11 / p00
    inter = (p11 - p10 - p01 + p00) * 100; conj = (p11 - p00) * 100
    ror = rr11 / (rr10 * rr01)
    out = [p00 * 100, p10 * 100, p01 * 100, p11 * 100, rr10, rr01, rr11, rr11 - rr10 - rr01 + 1, (rr10 - 1) * (rr01 - 1), ror,
           (p10 - p00) * 100, (p01 - p00) * 100, inter, conj, inter / conj * 100, np.log(rr10), np.log(rr01), np.log(rr11), np.log(ror)]
    return np.stack(out, axis=-1)


def cell_theta(w, y, cell, mask=None):
    """prevalencia ponderada nas 4 celulas (proporcao)."""
    if mask is not None: w, y, cell = w[mask], y[mask], cell[mask]
    num = np.bincount(cell, weights=w * y, minlength=4); den = np.bincount(cell, weights=w, minlength=4)
    with np.errstate(divide="ignore", invalid="ignore"): return num / den


def influence(w, y, cell, mask=None):
    """funcoes de influencia (n,4) das prevalencias de celula; linhas fora da mascara = 0."""
    n = len(w); Zm = np.zeros((n, 4)); m = np.ones(n, bool) if mask is None else mask
    th = cell_theta(w, y, cell, m); den = np.bincount(cell[m], weights=w[m], minlength=4)
    for k in range(4):
        i = m & (cell == k); Zm[i, k] = w[i] * (y[i] - th[k]) / den[k]
    return Zm, th


def psu_totals(Zm, psu, n_psu):
    return np.stack([np.bincount(psu, weights=Zm[:, k], minlength=n_psu) for k in range(Zm.shape[1])], axis=1)


def cov_psu_only(T):
    n = len(T); D = T - T.mean(0); return n / (n - 1) * D.T @ D


def cov_strat(T, strat_of_psu, lonely="adjust"):
    """T: (n_psu,k) totais por UPA; strat_of_psu: (n_psu,) inteiro do estrato. Estrato com 1 UPA: centrado na media global (adjust)."""
    k = T.shape[1]; V = np.zeros((k, k)); gm = T.mean(0); nlonely = 0
    for h in np.unique(strat_of_psu):
        Th = T[strat_of_psu == h]; nh = len(Th)
        if nh == 1:
            nlonely += 1
            if lonely == "adjust": D = Th - gm; V += D.T @ D          # centrado na media global (survey: lonely.psu="adjust"); politica padrao
            elif lonely == "certainty": pass                            # contribuicao zero (survey: lonely.psu="certainty")
            else: raise ValueError(lonely)
        else: D = Th - Th.mean(0); V += nh / (nh - 1) * D.T @ D
    return V, nlonely


def jacobian(fun, th, h=1e-6):
    th = np.asarray(th, float); f0 = fun(th); J = np.zeros((len(f0), len(th)))
    for k in range(len(th)):
        e = np.zeros_like(th); s = h * max(abs(th[k]), 1e-3); e[k] = s
        J[:, k] = (fun(th + e) - fun(th - e)) / (2 * s)
    return J


def se_delta(th, V):
    J = jacobian(derived, th); return np.sqrt(np.clip(np.diag(J @ V @ J.T), 0, None))


def ci_from(est, se, z=Z):
    """IC por quantidade: PRs e RoR na escala log; demais na escala linear. Devolve dict nome -> (est, lo, hi, se_log_ou_linear)."""
    out = {}
    for i, nm in enumerate(DER):
        if nm.startswith("log_"): continue
        if nm in LOGSCALE:
            j = DER.index(LOGSCALE[nm]); out[nm] = (est[i], np.exp(est[j] - z * se[j]), np.exp(est[j] + z * se[j]), se[j])
        else: out[nm] = (est[i], est[i] - z * se[i], est[i] + z * se[i], se[i])
    return out


def prev_logit_ci(p, se_p, z=Z):
    lg = np.log(p / (1 - p)); sl = se_p / (p * (1 - p)); f = lambda x: 1 / (1 + np.exp(-x)); return f(lg - z * sl), f(lg + z * sl)


# ---------------------------------------------------------------- padronizacao (g-computation)
def _expit(x): return 1 / (1 + np.exp(-x))


def logit_fit(X, y, w, tol=1e-11, maxit=60):
    """regressao logistica ponderada por IRLS (equacoes de escore: X' w (y - mu) = 0). Linhas com w=0 sao ignoradas."""
    m = w > 0; X, y, w = X[m], y[m], w[m]; b = np.zeros(X.shape[1]); ok = False
    b[0] = np.log(np.average(y, weights=w) / (1 - np.average(y, weights=w)))
    for it in range(maxit):
        eta = X @ b; mu = _expit(eta); v = mu * (1 - mu); Wt = w * v
        z = eta + (y - mu) / v; A = X.T @ (X * Wt[:, None]); bn = np.linalg.solve(A, X.T @ (Wt * z))
        if np.max(np.abs(bn - b)) < tol: b = bn; ok = True; break
        b = bn
    return b, ok, it + 1


def std_theta(w, y, cell, covs, mask=None):
    """prevalencias padronizadas nas 4 celulas: media ponderada, sobre todos os domicilios, da probabilidade prevista com a celula fixada.
    covs: (n,q) covariaveis (ja codificadas); q = 0 reproduz as prevalencias brutas."""
    if mask is not None: w, y, cell, covs = w[mask], y[mask], cell[mask], covs[mask]
    n = len(w); C = np.zeros((n, 3));
    for k in (1, 2, 3): C[:, k - 1] = (cell == k)
    X = np.column_stack([np.ones(n), C, covs]) if covs.shape[1] else np.column_stack([np.ones(n), C])
    b, ok, it = logit_fit(X, y, w)
    th = np.empty(4); W = w.sum()
    for k in range(4):
        Xk = X.copy(); Xk[:, 1:4] = 0
        if k > 0: Xk[:, k] = 1
        th[k] = np.sum(w * _expit(Xk @ b)) / W
    return th, ok, it, b


# ---------------------------------------------------------------- rotinas de alto nivel (usadas por D-1 a D-5)
def run_raw(D, ses, y_name, mask=None):
    """estimativas brutas das 4 celulas e SE das configuracoes A, B e C (C: funcoes recalculadas em cada replica)."""
    y = D.y[y_name]; cell = D.cell(ses); Rn = D.W.shape[1]
    th = cell_theta(D.w, y, cell, mask); est = derived(th)
    Zm, _ = influence(D.w, y, cell, mask); T = psu_totals(Zm, D.upa, D.n_psu)
    seA = se_delta(th, cov_psu_only(T)); VB, nl = cov_strat(T, D.strat_of_psu); seB = se_delta(th, VB)
    ths = np.array([cell_theta(D.W[:, r], y, cell, mask) for r in range(Rn)]); ders = derived(ths)
    fail = int((~np.isfinite(ders)).any(1).sum()); seC = np.sqrt(np.nansum((ders - est) ** 2, 0) / (Rn - 1))
    m = np.ones(D.n, bool) if mask is None else mask
    return {"est": est, "se": {"A": seA, "B": seB, "C": seC}, "ders": ders, "fail": fail, "n_cell": np.bincount(cell[m], minlength=4), "th": th, "lonely": nl}


def run_std(D, ses, y_name, mask=None):
    """estimativas padronizadas (g-computation) com as covariaveis de D-1; replicas: o modelo e' reajustado com cada peso replicado."""
    y = D.y[y_name]; cell = D.cell(ses); C = D.covs_std(); Rn = D.W.shape[1]
    th, ok, it, b = std_theta(D.w, y, cell, C, mask); est = derived(th)
    ders = np.full((Rn, len(DER)), np.nan); bs = np.full((Rn, len(b)), np.nan); nonconv = 0
    for r in range(Rn):
        try:
            tr, okr, itr, br = std_theta(D.W[:, r], y, cell, C, mask)
            if not okr: nonconv += 1
            ders[r] = derived(tr); bs[r] = br
        except Exception:
            nonconv += 1
    fail = int((~np.isfinite(ders)).any(1).sum()); seC = np.sqrt(np.nansum((ders - est) ** 2, 0) / (Rn - 1))
    m = np.ones(D.n, bool) if mask is None else mask
    return {"est": est, "se": {"C": seC}, "ders": ders, "fail": fail, "nonconv_full": (not ok), "nonconv_reps": nonconv, "iter_full": it, "coef": b, "coef_reps": bs, "n_cell": np.bincount(cell[m], minlength=4)}
