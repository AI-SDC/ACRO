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
# prepare exog, endog
y = unlist(data.frame(y=df[c(1)]))
x = data.frame(x1=df[c(2)], x2=df[c(3)], x3=df[c(4)])
# fit linear model
model = lm(y ~ ., data=x)
summary(model)

#' ACRO linear model
acro_lm <- function(y, x)
{
  acro = import("acro")
  ac = acro$ACRO()
  x = acro$add_constant(x)
  model = ac$ols(y, x)
  model$summary()
}

acro_lm(y, x)
