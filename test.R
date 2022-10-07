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
# convert list to values
y = unlist(df["inc_activity"])
# fit linear model
model = lm(y ~ ., data=df[c(2,3,4)])
summary(model)

# import acro
acro = import("acro")
ac = acro$ACRO()
# data frames are auto-converted to pandas dataframes
y = data.frame(y=df[c(1)])
x = data.frame(x1=df[c(2)], x2=df[c(3)], x3=df[c(4)])
x = acro$add_constant(x)
# fit linear model
model = ac$ols(y, x)
model$summary()
