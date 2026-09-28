# maihda_artigo3_20260916.R
#
# I-MAIHDA para o Artigo 3: insegurança alimentar (IA total e IA grave) por
# estrato interseccional (raça x sexo x instrução x renda x situação
# domiciliar), PNADC T4 2023, n=173.676, 160 estratos.
#
# Modelo A (nulo): so' intercepto aleatorio por estrato -> VPC_A
# Modelo B (efeitos principais): adiciona os 5 termos aditivos -> VPC_B, PCV
#
# Nao pondera pelo peso amostral (V1028) -- o metodo I-MAIHDA, como descrito
# no tutorial de Evans et al. (2024), nao incorpora peso complexo de
# amostragem no procedimento padrao; e uma limitacao a declarar no artigo,
# nao um erro de implementacao.

suppressMessages(library(lme4))

d <- read.csv("resultados/dados_maihda_2023.csv", stringsAsFactors = TRUE)
d$estrato <- factor(d$estrato)

# categoria de referencia explicita em cada fator, para leitura direta dos
# coeficientes do Modelo B
d$raca_cat <- relevel(d$raca_cat, ref = "nao_negra")
d$sexo_cat <- relevel(d$sexo_cat, ref = "homem")
d$instrucao_cat <- relevel(d$instrucao_cat, ref = "superior")
d$renda_cat <- relevel(d$renda_cat, ref = "mais_2sm")
d$rural_cat <- relevel(d$rural_cat, ref = "urbano")

cat("N =", nrow(d), " | estratos =", nlevels(d$estrato), "\n\n")

vpc_logistic <- function(modelo) {
  vc <- as.data.frame(VarCorr(modelo))
  sigma_u2 <- vc$vcov[vc$grp == "estrato"]
  sigma_e2 <- (pi^2) / 3
  sigma_u2 / (sigma_u2 + sigma_e2)
}

ajustar_desfecho <- function(desfecho) {
  cat("========================================\n")
  cat("Desfecho:", desfecho, "\n")
  cat("========================================\n")

  f_nulo <- as.formula(paste0(desfecho, " ~ 1 + (1 | estrato)"))
  f_principal <- as.formula(paste0(
    desfecho,
    " ~ raca_cat + sexo_cat + instrucao_cat + renda_cat + rural_cat + (1 | estrato)"
  ))

  cat("Ajustando Modelo A (nulo)...\n")
  modA <- glmer(f_nulo, data = d, family = binomial, nAGQ = 1,
                control = glmerControl(optimizer = "bobyqa"))
  vpcA <- vpc_logistic(modA)
  cat(sprintf("  VPC (nulo) = %.4f (%.1f%%)\n", vpcA, vpcA * 100))

  cat("Ajustando Modelo B (efeitos principais + estrato)...\n")
  modB <- glmer(f_principal, data = d, family = binomial, nAGQ = 1,
                control = glmerControl(optimizer = "bobyqa"))
  vpcB <- vpc_logistic(modB)
  cat(sprintf("  VPC (com efeitos principais) = %.4f (%.1f%%)\n", vpcB, vpcB * 100))

  sigma_u2_A <- as.data.frame(VarCorr(modA))$vcov[1]
  sigma_u2_B <- as.data.frame(VarCorr(modB))$vcov[1]
  pcv <- (sigma_u2_A - sigma_u2_B) / sigma_u2_A
  cat(sprintf("  PCV = %.4f (%.1f%% da variância entre estratos explicada pelos efeitos aditivos)\n",
              pcv, pcv * 100))
  cat(sprintf("  Variância residual entre estratos NÃO explicada: %.1f%% -- essa é a parte 'genuinamente interseccional'\n",
              (1 - pcv) * 100))

  cat("\nCoeficientes do Modelo B (log-odds, referência: não negra, homem, superior, >2SM, urbano):\n")
  print(round(summary(modB)$coefficients, 4))

  # efeitos aleatorios (predicao por estrato, com encolhimento) do modelo nulo,
  # convertidos para probabilidade prevista, ordenados
  ranef_nulo <- ranef(modA)$estrato
  intercepto <- fixef(modA)[["(Intercept)"]]
  prob_prevista <- plogis(intercepto + ranef_nulo[, 1])
  tab <- data.frame(estrato = rownames(ranef_nulo), prob_prevista = prob_prevista)
  tab <- tab[order(-tab$prob_prevista), ]

  cat("\n--- 5 estratos com MAIOR probabilidade prevista (com encolhimento) ---\n")
  print(head(tab, 5), row.names = FALSE)
  cat("\n--- 5 estratos com MENOR probabilidade prevista (com encolhimento) ---\n")
  print(tail(tab, 5), row.names = FALSE)

  write.csv(tab, paste0("resultados/maihda_estratos_", desfecho, "_20260916.csv"),
            row.names = FALSE)

  list(vpcA = vpcA, vpcB = vpcB, pcv = pcv)
}

res_total <- ajustar_desfecho("ia_total")
cat("\n\n")
res_grave <- ajustar_desfecho("ia_grave")

cat("\n\n================ RESUMO ================\n")
cat(sprintf("IA total : VPC nulo=%.1f%%  VPC c/ efeitos=%.1f%%  PCV=%.1f%%\n",
            res_total$vpcA * 100, res_total$vpcB * 100, res_total$pcv * 100))
cat(sprintf("IA grave : VPC nulo=%.1f%%  VPC c/ efeitos=%.1f%%  PCV=%.1f%%\n",
            res_grave$vpcA * 100, res_grave$vpcB * 100, res_grave$pcv * 100))
