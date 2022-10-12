# install.packages("reticulate")
# install.packages("haven")
library(haven)  # read .dta
library(reticulate)  # import Python modules

# load data
data = read_dta("data/test_data.dta")
head(data)
# extract relevant columns
df = data[, c("inc_activity", "inc_grants", "inc_donations", "total_costs")]
# drop rows with missing values
df = df[complete.cases(df), ]
# fit linear model
model = lm(formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=df)
summary(model)

#' ACRO linear model
acro_lm <- function(formula, data)
{
  acro = import("acro")
  ac = acro$ACRO()
  model = ac$olsr(formula, data)
  model$summary()
}

acro_lm(formula="inc_activity ~ inc_grants + inc_donations + total_costs", data=df)
