# install.packages("reticulate")
library(reticulate)  # import Python modules

acro = import("acro")
ac = acro$ACRO()

acro_pivot_table = function(data, index, values, aggfunc)
{
    "ACRO pivot table"
    table = ac$pivot_table(data, index=index, values=values, aggfunc=aggfunc)
    return(table)
}

acro_lm = function(formula, data)
{
    "ACRO linear model"
    model = ac$olsr(formula, data)
    model$summary()
}

acro_glm = function(formula, data, family)
{
    "ACRO logit/probit model"
    if (family == "logit") {
        model = ac$logitr(formula, data)
    } else {
        model = ac$probitr(formula, data)
    }
    model$summary()
}

acro_finalise = function(filename)
{
    "Write outputs to file"
    ac$finalise(filename)
}
