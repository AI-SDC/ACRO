# install.packages("reticulate")
library(reticulate)  # import Python modules

acro = import("acro")
ac = acro$ACRO()

acro_crosstab = function(index, columns, values=NULL, aggfunc=NULL)
{
    "ACRO crosstab"
    table = ac$crosstab(index, columns, values=values, aggfunc=aggfunc)
    return(table)
}

acro_pivot_table = function(data, values=NULL, index=NULL, columns=NULL, aggfunc="mean")
{
    "ACRO pivot table"
    table = ac$pivot_table(data, values=values, index=index, columns=columns, aggfunc=aggfunc)
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
    } else if (family == "probit") {
        model = ac$probitr(formula, data)
    } else {
        stop("Invalid family. Options = {'logit', 'probit'}");
    }
    model$summary()
}

acro_finalise = function(filename)
{
    "Write outputs to file"
    ac$finalise(filename)
}
