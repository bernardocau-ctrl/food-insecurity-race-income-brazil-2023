# maihda_v2_20260925.R
#
# Complementa maihda_artigo3_20260916.R para o manuscrito em ingles. Adiciona:
#  (1) coeficientes do Modelo B com IC95% (OR)
#  (2) IC95% do VPC do modelo nulo (perfil de verossimilhanca da SD do intercepto)
#  (3) residuos por estrato (ranef do Modelo B, com erro-padrao condicional):
#      quantos estratos desviam do aditivo alem do esperado por acaso
#  (4) escala de RISCO: probabilidade prevista completa (efeitos principais +
#      residuo) menos probabilidade prevista so' aditiva, em pontos percentuais
#  (5) sensibilidade ao peso amostral: Modelos A e B reajustados com pesos
#      normalizados (pseudo-ponderacao, NAO e' estimador consistente com o
#      desenho; serve so' para ver se VPC/PCV mudam de ordem de grandeza)
#  (6) prevalencia observada por estrato (nao ponderada e ponderada) vs. prevista
#
# Saidas em dados/v2_20260925/.

suppressMessages(library(lme4))

base <- "C:/Projetos/obsidianclaude/03-dissertacao/san/artigos/03_ARTIGO3_INTERSECCIONALIDADE_RACA_IA/dados"
out <- file.path(base, "v2_20260925")
dir.create(out, showWarnings = FALSE)

d <- read.csv(file.path(base, "dados_maihda_2023.csv"), stringsAsFactors = TRUE)
d$estrato <- factor(d$estrato)
d$raca_cat <- relevel(d$raca_cat, ref = "nao_negra")
d$sexo_cat <- relevel(d$sexo_cat, ref = "homem")
d$instrucao_cat <- relevel(d$instrucao_cat, ref = "superior")
d$renda_cat <- relevel(d$renda_cat, ref = "mais_2sm")
d$rural_cat <- relevel(d$rural_cat, ref = "urbano")
d$w <- d$peso / mean(d$peso)

vpc <- function(m) {
  s2 <- as.data.frame(VarCorr(m))$vcov[1]
  s2 / (s2 + pi^2 / 3)
}

ctl <- glmerControl(optimizer = "bobyqa")
res_geral <- list()
res_coef <- list()
res_estr <- list()

for (y in c("ia_total", "ia_grave")) {
  cat("\n=====", y, "=====\n")
  fA <- as.formula(paste0(y, " ~ 1 + (1|estrato)"))
  fB <- as.formula(paste0(y, " ~ raca_cat + sexo_cat + instrucao_cat + renda_cat + rural_cat + (1|estrato)"))
  mA <- glmer(fA, data = d, family = binomial, control = ctl)
  mB <- glmer(fB, data = d, family = binomial, control = ctl)
  vA <- vpc(mA); vB <- vpc(mB)
  s2A <- as.data.frame(VarCorr(mA))$vcov[1]; s2B <- as.data.frame(VarCorr(mB))$vcov[1]
  pcv <- (s2A - s2B) / s2A

  # ATENCAO: profile() altera o objeto mA no lugar (estado C++ do lme4). Tudo que
  # depende de mA (efeitos aleatorios, intercepto) precisa ser extraido ANTES dele.
  reA <- ranef(mA)$estrato
  b0A <- fixef(mA)[1]

  # (2) IC do VPC via perfil da SD do intercepto aleatorio (modelo nulo)
  ci <- tryCatch({
    pr <- profile(mA, which = "theta_", signames = FALSE)
    confint(pr, level = 0.95)
  }, error = function(e) NULL)
  if (!is.null(ci)) {
    sd_lo <- ci[1, 1]; sd_hi <- ci[1, 2]
    vpc_lo <- sd_lo^2 / (sd_lo^2 + pi^2 / 3); vpc_hi <- sd_hi^2 / (sd_hi^2 + pi^2 / 3)
  } else { sd_lo <- sd_hi <- vpc_lo <- vpc_hi <- NA }
  cat(sprintf("VPC nulo=%.4f [%.4f, %.4f] | VPC B=%.4f | PCV=%.4f | s2A=%.4f s2B=%.5f\n",
              vA, vpc_lo, vpc_hi, vB, pcv, s2A, s2B))

  # (1) coeficientes
  cf <- summary(mB)$coefficients
  res_coef[[y]] <- data.frame(desfecho = y, termo = rownames(cf), beta = cf[, 1], se = cf[, 2],
                              or = exp(cf[, 1]), or_lo = exp(cf[, 1] - 1.96 * cf[, 2]),
                              or_hi = exp(cf[, 1] + 1.96 * cf[, 2]), row.names = NULL)

  # (3)+(4)+(6) por estrato
  re <- ranef(mB, condVar = TRUE)$estrato
  se_u <- sqrt(as.numeric(attr(ranef(mB, condVar = TRUE)$estrato, "postVar")))
  est <- rownames(re)
  # preditor linear so' com efeitos principais (aditivo) por estrato
  first <- d[!duplicated(d$estrato), ]
  first <- first[match(est, as.character(first$estrato)), ]
  eta_add <- predict(mB, newdata = first, re.form = NA)
  eta_full <- eta_add + re[, 1]
  # probabilidade nula com encolhimento (Modelo A)
  p_nulo <- plogis(b0A + reA[est, 1])
  # observado por estrato
  ag <- aggregate(cbind(n = 1, y = d[[y]]) ~ estrato, data = transform(d, n = 1), FUN = sum)
  obs_un <- setNames(ag$y / ag$n, ag$estrato)
  wy <- tapply(d$peso * d[[y]], d$estrato, sum); ww <- tapply(d$peso, d$estrato, sum)
  obs_w <- wy / ww
  n_est <- as.integer(table(d$estrato)[est])
  res_estr[[y]] <- data.frame(
    desfecho = y, estrato = est, n = n_est, u = re[, 1], se_u = se_u, z = re[, 1] / se_u,
    p_aditivo = plogis(eta_add), p_completo = plogis(eta_full),
    dif_pp = (plogis(eta_full) - plogis(eta_add)) * 100,
    p_nulo_shrunk = p_nulo, obs_naoponderada = obs_un[est], obs_ponderada = obs_w[est],
    row.names = NULL)
  ee <- res_estr[[y]]
  cat(sprintf("estratos |z|>1.96: %d/160 (esperado por acaso ~8) | max |dif| risco = %.2f pp | mediana |dif| = %.3f pp\n",
              sum(abs(ee$z) > 1.96), max(abs(ee$dif_pp)), median(abs(ee$dif_pp))))
  cat(sprintf("cor(aditivo, obs_ponderada)=%.4f | cor(completo, obs_ponderada)=%.4f | cor(nulo, obs_ponderada)=%.4f\n",
              cor(ee$p_aditivo, ee$obs_ponderada), cor(ee$p_completo, ee$obs_ponderada),
              cor(ee$p_nulo_shrunk, ee$obs_ponderada)))

  # (5) sensibilidade ao peso
  wA <- suppressWarnings(glmer(fA, data = d, family = binomial, weights = w, control = ctl))
  wB <- suppressWarnings(glmer(fB, data = d, family = binomial, weights = w, control = ctl))
  s2wA <- as.data.frame(VarCorr(wA))$vcov[1]; s2wB <- as.data.frame(VarCorr(wB))$vcov[1]
  cat(sprintf("PONDERADO (pseudo): VPC nulo=%.4f | VPC B=%.4f | PCV=%.4f\n", vpc(wA), vpc(wB),
              (s2wA - s2wB) / s2wA))

  res_geral[[y]] <- data.frame(desfecho = y, n = nrow(d), n_estratos = nlevels(d$estrato),
    sigma2_nulo = s2A, sigma2_B = s2B, vpc_nulo = vA, vpc_nulo_lo = vpc_lo, vpc_nulo_hi = vpc_hi,
    vpc_B = vB, pcv = pcv,
    n_z_gt196 = sum(abs(ee$z) > 1.96), max_abs_dif_pp = max(abs(ee$dif_pp)),
    med_abs_dif_pp = median(abs(ee$dif_pp)),
    w_vpc_nulo = vpc(wA), w_vpc_B = vpc(wB), w_pcv = (s2wA - s2wB) / s2wA)
}

write.csv(do.call(rbind, res_geral), file.path(out, "m1_maihda_geral.csv"), row.names = FALSE)
write.csv(do.call(rbind, res_coef), file.path(out, "m2_maihda_coef.csv"), row.names = FALSE)
write.csv(do.call(rbind, res_estr), file.path(out, "m3_maihda_estratos.csv"), row.names = FALSE)
cat("\nFIM\n")
