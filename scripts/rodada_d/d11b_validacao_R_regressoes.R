# Validacao independente (R) das regressoes e da padronizacao com a configuracao C.
# Entradas: dados/rodada_d_cache/R_input_reg.csv e R_pesos_replicados.bin. Saida: rodada_D/R11_validacao_regressoes_R.csv
suppressMessages(library(survey))
args <- commandArgs(trailingOnly = FALSE)
here <- dirname(sub("--file=", "", args[grep("--file=", args)]))
root <- normalizePath(here); while (!dir.exists(file.path(root, "dados_ibge"))) { p <- dirname(root); if (p == root) stop("raiz nao encontrada"); root <- p }
art <- file.path(root, "artigos", "03_ARTIGO3_INTERSECCIONALIDADE_RACA_IA")
cache <- file.path(art, "dados", "rodada_d_cache"); outd <- file.path(art, "MANUSCRITO_IJE_20260925", "rodada_D")
d <- read.csv(file.path(cache, "R_input_reg.csv")); n <- nrow(d); R <- 200
Wm <- t(matrix(readBin(file.path(cache, "R_pesos_replicados.bin"), "double", n * R), nrow = R, ncol = n)); colnames(Wm) <- sprintf("r%03d", 1:R)
dd <- cbind(d, Wm)
des <- svrepdesign(data = dd, type = "bootstrap", weights = ~V1028, repweights = "^r[0-9]{3}$", mse = TRUE)
out <- list(); add <- function(item, est, se) out[[length(out) + 1]] <<- data.frame(item = item, est = est, se = se)
m <- svymean(~y_any + y_sev, des); add("prev_total_any", coef(m)[1], SE(m)[1]); add("prev_total_sev", coef(m)[2], SE(m)[2])
for (y in c("y_any", "y_sev")) for (b in c(0, 4)) {
  sub <- subset(des, band == b); f <- svyglm(as.formula(paste0(y, " ~ negra + mulher + factor(edu4) + rural")), sub, family = quasipoisson())
  add(paste0("t6_negra_band", b, "_", y, "_logPR"), coef(f)["negra"], SE(f)["negra"])
}
f <- svyglm(y_any ~ negra + rq1 + rq2 + rq3 + rq4 + mulher + sem_fund + rural, des, family = quasipoisson()); add("aten_negra_full_any_logPR", coef(f)["negra"], SE(f)["negra"])
f <- svyglm(y_any ~ negra + mulher + sem_fund + rq1 + rural + negra:mulher + negra:sem_fund + negra:rq1 + negra:rural, des, family = quasipoisson()); add("t3_negra_rq1_any_logPR", coef(f)["negra:rq1"], SE(f)["negra:rq1"])
f <- svyglm(y_sev ~ negra + mulher + sem_fund + rq1 + rural + negra:mulher + negra:sem_fund + negra:rq1 + negra:rural, des, family = quasipoisson()); add("t3_negra_rq1_sev_logPR", coef(f)["negra:rq1"], SE(f)["negra:rq1"])
# padronizacao (g-computation) com glm binomial; replicas: refit em cada peso replicado
dd$cellf <- factor(dd$cell_inc, levels = 0:3); dd$edu4f <- factor(dd$edu4)
stdfun <- function(w, y) {
  keep <- w > 0; ws <- w[keep] / mean(w[keep])   # pesos reescalados para media 1 no ajuste (estimativas invariantes; evita divergencia numerica do glm com pesos grandes)
  fit <- suppressWarnings(glm(as.formula(paste0(y, " ~ cellf + mulher + edu4f + rural")), data = dd[keep, ], family = quasibinomial(), weights = ws))
  th <- sapply(0:3, function(k) { nd <- dd; nd$cellf <- factor(k, levels = 0:3); sum(w * predict(fit, newdata = nd, type = "response")) / sum(w) })
  p00 <- th[1]; p10 <- th[2]; p01 <- th[3]; p11 <- th[4]
  c(reri = p11 / p00 - p10 / p00 - p01 / p00 + 1, log_ror = log(p11 * p00 / (p10 * p01)), inter_pp = (p11 - p10 - p01 + p00) * 100, joint_pp = (p11 - p00) * 100)
}
for (y in c("y_any", "y_sev")) {
  th0 <- stdfun(dd$V1028, y); thr <- t(sapply(1:R, function(r) stdfun(dd[[sprintf("r%03d", r)]], y)))
  se <- sqrt(colSums((sweep(thr, 2, th0))^2) / (R - 1)); for (k in seq_along(th0)) add(paste0("std_", names(th0)[k], "_", y), th0[k], se[k])
}
res <- do.call(rbind, out); rownames(res) <- NULL; write.csv(res, file.path(outd, "R11_validacao_regressoes_R.csv"), row.names = FALSE); cat("ok\n")
