# -*- coding: utf-8 -*-
"""
figuras_artigo3_20260925.py

Gera as figuras do manuscrito em ingles (SSM) a partir dos CSVs de
dados/v2_20260925. Nenhum numero e' digitado a mao: tudo vem dos CSVs.

  fig2_race_gaps_income.png     RR ajustado e diferenca absoluta (pp) da raca por faixa de renda
  fig1_interaction_scales.png   RERI e razao de razoes (RoR) dos 4 pares x 2 desfechos
  fig3_gradient.png             prevalencia por n. de desvantagens x raca
  fig4_maihda_strata.png        160 estratos: prob. prevista completa vs. aditiva
  figS1_race_gaps_education.png (suplementar)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
D = BASE / "dados" / "v2_20260925"
OUT = BASE / "MANUSCRITO_EN_SSM_20260925" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# paleta de Okabe-Ito (segura para daltonismo)
BLUE, ORANGE, GREEN, RED, GREY, SKY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#666666", "#56B4E9"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 0.8, "figure.dpi": 100,
    "savefig.dpi": 300, "axes.titlesize": 9.5, "axes.titleweight": "bold",
})
OUTC = {"ia_total": "Any food insecurity", "ia_grave": "Severe food insecurity"}
INC = ["q1", "q2", "q3", "q4", "q5"]
INC_LAB = ["≤1/4", ">1/4–1/2", ">1/2–1", ">1–2", ">2"]
EDU = ["sem_fund", "fund_med", "medio_comp", "superior"]
EDU_LAB = ["≤Incomplete\nprimary", "Complete primary/\nincomplete secondary", "Complete\nsecondary", "Tertiary"]


def panel_label(ax, s):
    ax.text(-0.14, 1.06, s, transform=ax.transAxes, fontsize=11, fontweight="bold")


def race_gap_fig(strata_col, cats, labels, fname, xlabel):
    t6 = pd.read_csv(D / "t6_estratificado.csv")
    t6 = t6[(t6.exposicao == "negra") & (t6.estratificado_por == strata_col)]
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.6), sharex=True)
    for i, d in enumerate(["ia_total", "ia_grave"]):
        s = t6[t6.desfecho == d].set_index("estrato").loc[cats]
        x = np.arange(len(cats))
        ax = axes[i, 0]
        ax.errorbar(x, s.rr_ajustado, yerr=[s.rr_ajustado - s.lo, s.hi - s.rr_ajustado],
                    fmt="o-", color=BLUE, capsize=3, lw=1.4, ms=5)
        ax.axhline(1, color=GREY, lw=0.8, ls="--")
        ax.set_ylabel("Adjusted risk ratio\n(Black vs non-Black)")
        ax.set_title(OUTC[d])
        if i == 0: panel_label(ax, "a")
        else: panel_label(ax, "c")
        ax = axes[i, 1]
        ax.errorbar(x, s.dif_pp, yerr=[s.dif_pp - s.dif_pp_lo, s.dif_pp_hi - s.dif_pp],
                    fmt="s-", color=RED, capsize=3, lw=1.4, ms=5)
        ax.axhline(0, color=GREY, lw=0.8, ls="--")
        ax.set_ylabel("Absolute gap\n(percentage points)")
        ax.set_title(OUTC[d])
        if i == 0: panel_label(ax, "b")
        else: panel_label(ax, "d")
    for ax in axes[1]:
        ax.set_xticks(np.arange(len(cats)))
        ax.set_xticklabels(labels)
        ax.set_xlabel(xlabel)
    fig.tight_layout()
    fig.savefig(OUT / fname, bbox_inches="tight")
    plt.close(fig)


def fig2_scales():
    t2 = pd.read_csv(D / "t2_pares.csv")
    pares = list(dict.fromkeys(t2.par))
    short = {"Race x Sex (woman)": "Race × sex\n(woman)",
             "Race x Education (<= incomplete primary)": "Race × education\n(≤ incomplete primary)",
             "Race x Income (<= 1/4 MW per capita)": "Race × income\n(≤ 1/4 MW)",
             "Race x Residence (rural)": "Race × residence\n(rural)"}
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9), sharey=True)
    ypos = {}
    y = 0
    for p in pares[::-1]:
        for d in ["ia_grave", "ia_total"]:
            ypos[(p, d)] = y
            y += 1
        y += 0.6
    col = {"ia_total": BLUE, "ia_grave": RED}
    for k, (ax, (m, lo, hi, ref, ttl, xl)) in enumerate(zip(
            axes, [("reri", "reri_lo_delta", "reri_hi_delta", 0, "Additive scale: RERI\n(> 0 = super-additive)", "RERI"),
                   ("ror", "ror_lo", "ror_hi", 1, "Multiplicative scale: ratio of ratios\n(< 1 = sub-multiplicative)", "Ratio of risk ratios")])):
        for _, r in t2.iterrows():
            yy = ypos[(r.par, r.desfecho)]
            ax.errorbar(r[m], yy, xerr=[[r[m] - r[lo]], [r[hi] - r[m]]], fmt="o", color=col[r.desfecho], capsize=3, ms=5, lw=1.3)
        if m == "reri":
            for _, r in t2.iterrows():
                yy = ypos[(r.par, r.desfecho)]
                ax.plot(r.reri_esperado_nulo_mult, yy, marker="D", mfc="none", mec=GREY, ms=5.5, ls="none")
        ax.axvline(ref, color=GREY, lw=0.8, ls="--")
        ax.set_title(ttl)
        ax.set_xlabel(xl)
        panel_label(ax, "ab"[k])
    axes[0].set_yticks([np.mean([ypos[(p, "ia_total")], ypos[(p, "ia_grave")]]) for p in pares[::-1]])
    axes[0].set_yticklabels([short[p] for p in pares[::-1]])
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", color=BLUE, ls="none", label="Any food insecurity"),
         Line2D([], [], marker="o", color=RED, ls="none", label="Severe food insecurity"),
         Line2D([], [], marker="D", mfc="none", mec=GREY, ls="none", label="RERI expected if purely multiplicative")]
    axes[0].legend(handles=h, loc="upper right", fontsize=7.2, frameon=False, bbox_to_anchor=(1.0, 0.86))
    fig.tight_layout()
    fig.savefig(OUT / "fig1_interaction_scales.png", bbox_inches="tight")
    plt.close(fig)


def fig3_gradient():
    t4 = pd.read_csv(D / "t4_gradiente_prev.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.5))
    for ax, d, l in zip(axes, ["ia_total", "ia_grave"], "ab"):
        s = t4[t4.desfecho == d]
        x = s.n_desv
        for g, c, lab, off in [("nao_negra", GREEN, "Non-Black", -0.05), ("negra", BLUE, "Black", 0.05)]:
            ax.errorbar(x + off, s[g + "_pct"], yerr=[s[g + "_pct"] - s[g + "_lo"], s[g + "_hi"] - s[g + "_pct"]],
                        fmt="o-", color=c, capsize=3, lw=1.4, ms=5, label=lab)
        ax.set_xticks(range(5))
        ax.set_xlabel("Number of disadvantages (0–4)")
        ax.set_ylabel("Prevalence (%)")
        ax.set_title(OUTC[d])
        panel_label(ax, l)
        ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_gradient.png", bbox_inches="tight")
    plt.close(fig)


def fig4_maihda():
    m3 = pd.read_csv(D / "m3_maihda_estratos.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8))
    for ax, d, l in zip(axes, ["ia_total", "ia_grave"], "ab"):
        s = m3[m3.desfecho == d].sort_values("p_completo").reset_index(drop=True)
        x = np.arange(len(s))
        ax.plot(x, s.p_aditivo * 100, "o", mfc="none", mec=ORANGE, ms=5.2, mew=1.0, ls="none", label="Additive main effects only")
        ax.plot(x, s.p_completo * 100, ".", color=BLUE, ms=3.2, ls="none", label="Full model (main effects + stratum residual)")
        ax.set_xlabel("Intersectional strata (n = 160), ranked by predicted risk")
        ax.set_ylabel("Predicted prevalence (%)")
        ax.set_title(OUTC[d])
        panel_label(ax, l)
        if d == "ia_total":
            ax.legend(frameon=False, loc="upper left", fontsize=7.2)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_maihda_strata.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    race_gap_fig("renda", INC, INC_LAB, "fig2_race_gaps_income.png", "Per capita household income (minimum wages)")
    race_gap_fig("instrucao", EDU, EDU_LAB, "figS1_race_gaps_education.png", "Education of reference person")
    fig2_scales()
    fig3_gradient()
    fig4_maihda()
    print("figuras em", OUT)
