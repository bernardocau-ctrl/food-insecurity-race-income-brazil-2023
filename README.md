[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23019882.svg)](https://doi.org/10.5281/zenodo.23019882)

# Code and derived data — Race, income and household food insecurity in Brazil: joint disparities depend on the scale of interaction

This repository contains the analysis code and derived (non-identifiable, aggregate) data tables underlying
the manuscript submitted to the *International Journal of Epidemiology*. It does not contain the raw
microdata, which are public and available directly from the Brazilian Institute of Geography and Statistics
(IBGE) at https://www.ibge.gov.br (Continuous National Household Sample Survey, PNADC, fourth quarter of
2023).

## What is here

- `scripts/` — the full analysis pipeline: extraction and preparation of the microdata
  (`analise_bivariada_e_regressao_v2.py`), the variance-configuration comparison and replicate-weight
  estimation round (`scripts/rodada_d/`, including independent validation in R against the `survey` package),
  the scripts that produce the manuscript's tables, figures and supplementary material from the derived output
  files, and the audit/coherence-checking scripts used to verify every printed number against its source.
- `dados/v3_rodadaD_C/` — the derived, aggregate output tables (counts, prevalences, model estimates,
  confidence intervals) that the manuscript's tables, figures and text were built from. These contain no
  individual-level data.

## Reproducing the analysis

`scripts/rodada_d/run_pacote_rev4.py` runs the full pipeline end to end, from the raw microdata (which you
must first download from IBGE) through to the final manuscript, supplement, tables and audit reports. It
requires Python 3.12 (numpy, pandas, scipy, statsmodels, python-docx, openpyxl, matplotlib) and R 4.x (survey,
jsonlite, lme4). See the docstring at the top of that script, and `scripts/rodada_d/README_RODADA_D.md`, for
details.

## Variance method

The primary variance estimator (configuration C) uses the 200 replicate weights supplied with the microdata.
This was a post-protocol methodological amendment: the original protocol's literal decision rule would have
selected a different estimator, and configuration C was adopted only after comparing all three candidate
estimators, as documented in the manuscript's Transparency statement and in Supplementary Table S15c. All
three configurations give identical point estimates.

## Citation

If you use this code, please cite it via its Zenodo DOI: 10.5281/zenodo.23019882 (https://doi.org/10.5281/zenodo.23019882). The associated article citation will be added once assigned by the journal.

## Licence

MIT License (see `LICENSE`).

## Authors

Bernardo Castanho Santos Caú (https://orcid.org/0009-0001-8155-5854), Naiara Sperandio
(https://orcid.org/0000-0003-1079-0854). Programa de Pós-Graduação em Segurança Alimentar e Nutricional
(PPGSAN), Universidade Federal do Estado do Rio de Janeiro (UNIRIO).

## Use of AI tools

Portions of this analysis code were written and run with the assistance of an AI coding tool (Claude Code,
Anthropic), under the authors' direction; the authors reviewed and take full responsibility for the code and
its outputs.
