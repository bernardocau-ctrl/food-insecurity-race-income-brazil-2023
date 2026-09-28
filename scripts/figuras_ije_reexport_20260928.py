# -*- coding: utf-8 -*-
"""
figuras_ije_reexport_20260928.py

Copia de figuras_ije_20260925.py (NAO alterado) que reexporta as seis figuras com largura fisica >=300mm
a >=300dpi, para atender ao requisito do IJE ("minimum resolution of 300dpi at a minimum width of 300mm
(3600 pixels)"). NAO muda nenhum dado, cor, escala ou interpretacao -- so escala o figsize (polegadas) e
todo tamanho absoluto de fonte/traco/marcador pelo mesmo fator (1.7x), preservando as proporcoes visuais
ja inspecionadas nesta revisao. dpi permanece 500 (ja acima do minimo de 300).

Saida de teste em MANUSCRITO_IJE_20260925/figures_reexport_teste/ -- NAO sobrescreve os arquivos ja
publicados em figures/. So depois de medir e inspecionar visualmente os seis arquivos de saida daqui e
que os arquivos definitivos sao substituidos (passo separado, decisao do autor).
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

S = 1.7  # fator de escala uniforme (figsize e todo tamanho absoluto), ver PLANO_REEXPORTACAO_FIGURAS.md

BASE = Path(__file__).resolve().parent.parent
import os
D = BASE / "dados" / os.environ.get("IJE_DATA_VERSION", "v3_rodadaD_C")
OUT = BASE / "MANUSCRITO_IJE_20260925" / "figures_reexport_teste"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, GREEN, RED, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#666666"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9 * S, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.linewidth": 0.8 * S, "savefig.dpi": 500, "axes.titlesize": 9.5 * S, "axes.titleweight": "bold"})
OUTC = {"ia_total": "Any food insecurity", "ia_grave": "Severe food insecurity"}
INC = ["q1", "q2", "q3", "q4", "q5"]; INC_LAB = ["≤1/4", ">1/4–1/2", ">1/2–1", ">1–2", ">2"]
EDU = ["sem_fund", "fund_med", "medio_comp", "superior"]
EDU_LAB = ["≤Incomplete\nprimary", "Complete primary/\nincomplete secondary", "Complete\nsecondary", "Tertiary"]
SHORT = {"Race x Sex (woman)": "Race × sex\n(woman)", "Race x Education (<= incomplete primary)": "Race × education\n(≤ incomplete primary)",
         "Race x Income (<= 1/4 MW per capita)": "Race × income\n(≤ 1/4 MW)", "Race x Residence (rural)": "Race × residence\n(rural)"}


def panel(ax, s): ax.text(-0.12, 1.08, s, transform=ax.transAxes, fontsize=11 * S, fontweight="bold")


def interaction_fig(pares, fname, size):
    t2 = pd.read_csv(D / "t2_pares.csv"); t2 = t2[t2.par.isin(pares)]
    fig, axes = plt.subplots(1, 2, figsize=(size[0] * S, size[1] * S), sharey=True)
    ypos = {}; y = 0
    for p in pares[::-1]:
        for d in ["ia_grave", "ia_total"]:
            ypos[(p, d)] = y; y += 1
        y += 0.6
    col = {"ia_total": BLUE, "ia_grave": RED}
    spec = [("reri", "reri_lo_delta", "reri_hi_delta", 0, "Additive scale: RERI", "RERI (computed from prevalence ratios)"),
            ("ror", "ror_lo", "ror_hi", 1, "Multiplicative scale: ratio of PRs", "Ratio of prevalence ratios")]
    for k, (ax, (m, lo, hi, ref, ttl, xl)) in enumerate(zip(axes, spec)):
        for _, r in t2.iterrows():
            yy = ypos[(r.par, r.desfecho)]
            ax.errorbar(r[m], yy, xerr=[[r[m] - r[lo]], [r[hi] - r[m]]], fmt="o", color=col[r.desfecho], capsize=3 * S, ms=5 * S, lw=1.3 * S)
            if m == "reri":
                ax.plot(r.reri_esperado_nulo_mult, yy, marker="D", mfc="none", mec=GREY, ms=5.5 * S, ls="none")
        ax.axvline(ref, color=GREY, lw=0.8 * S, ls="--"); ax.set_title(ttl); ax.set_xlabel(xl); panel(ax, "ab"[k])
    axes[0].set_yticks([np.mean([ypos[(p, "ia_total")], ypos[(p, "ia_grave")]]) for p in pares[::-1]])
    axes[0].set_yticklabels([SHORT[p] for p in pares[::-1]])
    h = [Line2D([], [], marker="o", color=BLUE, ls="none", label="Any food insecurity"),
         Line2D([], [], marker="o", color=RED, ls="none", label="Severe food insecurity"),
         Line2D([], [], marker="D", mfc="none", mec=GREY, ls="none", label="RERI expected if joint effects were multiplicative")]
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.legend(handles=h, loc="lower center", ncol=3, fontsize=7.6 * S, frameon=False)
    fig.savefig(OUT / fname, bbox_inches="tight"); plt.close(fig)


def race_gap_fig(strata_col, cats, labels, fname, xlabel):
    t6 = pd.read_csv(D / "t6_estratificado.csv")
    t6 = t6[(t6.exposicao == "negra") & (t6.estratificado_por == strata_col)]
    fig, axes = plt.subplots(2, 2, figsize=(7.4 * S, 5.6 * S), sharex=True)
    for i, d in enumerate(["ia_total", "ia_grave"]):
        s = t6[t6.desfecho == d].set_index("estrato").loc[cats]; x = np.arange(len(cats))
        ax = axes[i, 0]
        ax.errorbar(x, s.rr_ajustado, yerr=[s.rr_ajustado - s.lo, s.hi - s.rr_ajustado], fmt="o-", color=BLUE, capsize=3 * S, lw=1.4 * S, ms=5 * S)
        ax.axhline(1, color=GREY, lw=0.8 * S, ls="--"); ax.set_ylabel("Adjusted prevalence ratio\n(Black vs non-Black)"); ax.set_title(OUTC[d]); panel(ax, "ac"[i])
        ax = axes[i, 1]
        ax.errorbar(x, s.dif_pp, yerr=[s.dif_pp - s.dif_pp_lo, s.dif_pp_hi - s.dif_pp], fmt="s-", color=RED, capsize=3 * S, lw=1.4 * S, ms=5 * S)
        ax.axhline(0, color=GREY, lw=0.8 * S, ls="--"); ax.set_ylabel("Crude absolute difference\n(percentage points)"); ax.set_title(OUTC[d]); panel(ax, "bd"[i])
    for ax in axes[1]:
        ax.set_xticks(np.arange(len(cats)))
        # rotacao para evitar a sobreposicao horizontal entre categorias adjacentes que ja existia na
        # figura publicada (achado desta rodada, pre-existente, nao introduzido pelo fator de escala) --
        # mesmo texto das categorias, so a orientacao muda; nenhuma palavra foi alterada.
        ax.set_xticklabels([lb.replace("\n", " ") for lb in labels], rotation=22, ha="right", rotation_mode="anchor")
        ax.set_xlabel(xlabel)
    fig.tight_layout(); fig.savefig(OUT / fname, bbox_inches="tight"); plt.close(fig)


def gradient_fig():
    t4 = pd.read_csv(D / "t4_gradiente_prev.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.4 * S, 3.5 * S))
    for ax, d, l in zip(axes, ["ia_total", "ia_grave"], "ab"):
        s = t4[t4.desfecho == d]; x = s.n_desv
        for g, c, lab, off in [("nao_negra", GREEN, "Non-Black", -0.05), ("negra", BLUE, "Black", 0.05)]:
            ax.errorbar(x + off, s[g + "_pct"], yerr=[s[g + "_pct"] - s[g + "_lo"], s[g + "_hi"] - s[g + "_pct"]], fmt="o-", color=c, capsize=3 * S, lw=1.4 * S, ms=5 * S, label=lab)
        ax.set_xticks(range(5)); ax.set_xlabel("Number of disadvantages (0–4)"); ax.set_ylabel("Prevalence (%)"); ax.set_title(OUTC[d]); panel(ax, l)
        ax.legend(frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT / "figS4_gradient.png", bbox_inches="tight"); plt.close(fig)


def maihda_fig():
    m3 = pd.read_csv(D / "m3_maihda_estratos.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.6 * S, 3.8 * S))
    for ax, d, l in zip(axes, ["ia_total", "ia_grave"], "ab"):
        s = m3[m3.desfecho == d].sort_values("p_completo").reset_index(drop=True); x = np.arange(len(s))
        ax.plot(x, s.p_aditivo * 100, "o", mfc="none", mec=ORANGE, ms=5.2 * S, mew=1.0 * S, ls="none", label="Additive (logit-scale) main effects only")
        ax.plot(x, s.p_completo * 100, ".", color=BLUE, ms=3.2 * S, ls="none", label="Full model (main effects + stratum residual)")
        ax.set_xlabel("Intersectional strata (n = 160), ranked by predicted prevalence"); ax.set_ylabel("Predicted prevalence (%)"); ax.set_title(OUTC[d]); panel(ax, l)
        if d == "ia_total": ax.legend(frameon=False, loc="upper left", fontsize=7.2 * S)
    fig.tight_layout()
    # tight_layout() sozinho deixa pouco espaco entre os dois paineis para o rotulo do eixo x, que a este
    # fator de escala (S=1.7) fica largo o bastante para colidir entre "a" e "b" (achado desta rodada,
    # nao presente nas outras cinco figuras); alargar o espaco entre paineis depois do tight_layout corrige.
    fig.subplots_adjust(wspace=0.5)
    fig.savefig(OUT / "figS5_maihda_strata.png", bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    inc = "Race x Income (<= 1/4 MW per capita)"; edu = "Race x Education (<= incomplete primary)"
    interaction_fig([inc, edu], "fig1_interaction_scales.png", (7.6, 3.4))
    race_gap_fig("renda", INC, INC_LAB, "figS1_race_gaps_income.png", "Per capita household income (minimum wages)")
    race_gap_fig("instrucao", EDU, EDU_LAB, "figS2_race_gaps_education.png", "Education of reference person")
    interaction_fig(list(SHORT.keys()), "figS3_interaction_all_pairs.png", (7.6, 3.9))
    gradient_fig(); maihda_fig()
    print("figuras de teste em", OUT)
