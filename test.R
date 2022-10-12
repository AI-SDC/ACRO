# install.packages("reticulate")
# install.packages("haven")
library(haven)  # read .dta
source("acro.R")

#############
# Load data #
#############

data = read_dta("data/test_data.dta")
head(data)

#################
# Linear Models #
#################

# extract relevant columns
df = data[, c("inc_activity", "inc_grants", "inc_donations", "total_costs")]
# drop rows with missing values
df = df[complete.cases(df), ]

# fit linear model
model = lm(formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=df)
summary(model)

# ACRO linear model
acro_lm(formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=df)

#######################
# Logit/Probit Models #
#######################

# extract relevant columns
df = data[, c("survivor", "inc_activity", "inc_grants", "inc_donations", "total_costs")]
# drop rows with missing values
df = df[complete.cases(df), ]
# convert survivor to numeric
df = transform(df, survivor = as.numeric(survivor))

# fit logit model
model = glm(formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs", data=df, family = binomial(link = "logit"))
summary(model)

# ACRO logit model
acro_glm(formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs", data=df, family="logit")

# fit probit model
model = glm(formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs", data=df, family = binomial(link = "probit"))
summary(model)

# ACRO probit model
acro_glm(formula="survivor ~ inc_activity + inc_grants + inc_donations + total_costs", data=df, family="probit")

############
# Finalise #
############

acro_finalise("r_test.xlsx")
