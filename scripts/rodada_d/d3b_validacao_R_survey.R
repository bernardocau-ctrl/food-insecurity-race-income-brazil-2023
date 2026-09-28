# Validacao independente (R, pacote survey) do motor Python de D-4.
# Entradas: dados/rodada_d_cache/R_input.csv e R_pesos_replicados.bin (gerados por d3_D4_desenho.py).
# Saida: rodada_D/D4_validacao_R_survey.csv (erros-padrao de survey para as configuracoes B e C).
# Executar a partir de qualquer diretorio: Rscript d3b_validacao_R_survey.R
suppressMessages(library(survey))
args <- commandArgs(trailingOnly = FALSE)
here <- dirname(sub("--file=", "", args[grep("--file=", args)]))
root <- normalizePath(here); while (!dir.exists(file.path(root, "dados_ibge"))) { p <- dirname(root); if (p == root) stop("raiz nao encontrada"); root <- p }
art <- file.path(root, "artigos", "03_ARTIGO3_INTERSECCIONALIDADE_RACA_IA")
cache <- file.path(art, "dados", "rodada_d_cache"); outd <- file.path(art, "MANUSCRITO_IJE_20260925", "rodada_D")
options(survey.lonely.psu = "adjust")
d <- read.csv(file.path(cache, "R_input.csv"), colClasses = c(UPA = "character", Estrato = "character"))
n <- nrow(d); R <- 200
Wm <- t(matrix(readBin(file.path(cache, "R_pesos_replicados.bin"), "double", n * R), nrow = R, ncol = n))
colnames(Wm) <- sprintf("r%03d", 1:R); d <- cbind(d, Wm)
desB <- svydesign(ids = ~UPA, strata = ~Estrato, weights = ~V1028, data = d, nest = TRUE)
desC <- svrepdesign(data = d, type = "bootstrap", weights = ~V1028, repweights = "^r[0-9]{3}$", mse = TRUE)
cat("survey", as.character(packageVersion("survey")), "| R", R.version.string, "| scale C:", desC$scale, "| mse:", desC$mse, "| n replicates:", ncol(desC$repweights), "\n")
ex <- list(p00 = quote(`0` * 100), p10 = quote(`1` * 100), p01 = quote(`2` * 100), p11 = quote(`3` * 100),
           rr10 = quote(log(`1` / `0`)), rr01 = quote(log(`2` / `0`)), rr11 = quote(log(`3` / `0`)),
           reri = quote(`3` / `0` - `1` / `0` - `2` / `0` + 1), reri_esperado = quote((`1` / `0` - 1) * (`2` / `0` - 1)), ror = quote(log(`3` * `0` / (`1` * `2`))),
           comp_raca_pp = quote((`1` - `0`) * 100), comp_ses_pp = quote((`2` - `0`) * 100), interacao_pp = quote((`3` - `1` - `2` + `0`) * 100),
           conjunta_pp = quote((`3` - `0`) * 100), participacao_pct = quote((`3` - `1` - `2` + `0`) / (`3` - `0`) * 100))
out <- list()
for (cfg in c("B", "C")) {
  des <- if (cfg == "B") desB else desC
  for (y in c("y_any", "y_sev")) {
    m <- svyby(as.formula(paste0("~", y)), ~factor(cell_inc), des, svymean, covmat = TRUE)
    names(coef(m))
    cc <- svycontrast(m, ex)
    out[[paste(cfg, y)]] <- data.frame(config = cfg, desfecho = ifelse(y == "y_any", "ia_total", "ia_grave"), quantidade = names(ex), est_R = as.numeric(coef(cc)), se_R = as.numeric(SE(cc)))
  }
}
# C2: mesma estimacao que o motor Python (funcoes nao lineares recalculadas em CADA replica): survey::withReplicates
for (y in c("y_any", "y_sev")) {
  th <- function(w, data) {
    yy <- data[[y]]; p <- sapply(0:3, function(k) sum(w * yy * (data$cell_inc == k)) / sum(w * (data$cell_inc == k)))
    p00 <- p[1]; p10 <- p[2]; p01 <- p[3]; p11 <- p[4]
    c(p00 * 100, p10 * 100, p01 * 100, p11 * 100, log(p10 / p00), log(p01 / p00), log(p11 / p00), p11 / p00 - p10 / p00 - p01 / p00 + 1, (p10 / p00 - 1) * (p01 / p00 - 1), log(p11 * p00 / (p10 * p01)),
      (p10 - p00) * 100, (p01 - p00) * 100, (p11 - p10 - p01 + p00) * 100, (p11 - p00) * 100, (p11 - p10 - p01 + p00) / (p11 - p00) * 100)
  }
  wr <- withReplicates(desC, th)
  out[[paste("C2", y)]] <- data.frame(config = "C2", desfecho = ifelse(y == "y_any", "ia_total", "ia_grave"), quantidade = names(ex), est_R = as.numeric(coef(wr)), se_R = as.numeric(SE(wr)))
}
res <- do.call(rbind, out); write.csv(res, file.path(outd, "D4_validacao_R_survey.csv"), row.names = FALSE)
cat("ok\n")
writeLines(capture.output(sessionInfo()), file.path(outd, "00_R_sessionInfo.txt"))
# configuracao do desenho replicado, para documentacao (nomes das colunas, fator de escala, centragem)
cfg <- list(colunas_replicadas_primeira = "V1028001", colunas_replicadas_ultima = "V1028200", n_replicas = ncol(desC$repweights), tipo = desC$type, mse = desC$mse,
            scale = desC$scale, scale_igual_1_sobre_R_menos_1 = isTRUE(all.equal(desC$scale, 1 / (ncol(desC$repweights) - 1))), rscales_todos_1 = all(desC$rscales == 1),
            survey_versao = as.character(packageVersion("survey")), R = R.version.string,
            formula_variancia = "V = scale * sum_r rscales_r * (theta_r - theta_completa)^2  (mse = TRUE: centrado na estimativa da amostra completa)")
writeLines(jsonlite::toJSON(cfg, auto_unbox = TRUE, pretty = TRUE, digits = NA), file.path(outd, "D4_R_survey_config_replicas.json"))
