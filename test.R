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

# data frames are autoconverted to pandas dataframes
y = data.frame(y)
str(y)
# import acro
acro = import("acro")
ac = acro$ACRO()
#fit linear model
#y = acro$add_constant(y)
model = ac$ols(y, y)
model$summary()
