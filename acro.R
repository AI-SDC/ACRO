library(reticulate)  # import Python modules

acro <- import("acro")
ac <- acro$ACRO()

acro_crosstab <- function(index, columns, values=NULL, aggfunc=NULL)
{
    "ACRO crosstab"
    table = ac$crosstab(index, columns, values=values, aggfunc=aggfunc)
    return(table)
}

acro_pivot_table <- function(data, values=NULL, index=NULL, columns=NULL, aggfunc="mean")
{
    "ACRO pivot table"
    table = ac$pivot_table(data, values=values, index=index, columns=columns, aggfunc=aggfunc)
    return(table)
}

acro_lm <- function(formula, data)
{
    "ACRO linear model"
    model = ac$olsr(formula, data)
    model$summary()
}

acro_glm <- function(formula, data, family)
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

acro_rename_output <- function(old, new)
{
    "Rename an output"
    ac$rename_output(old, new)
}

acro_remove_output <- function(name)
{
    "Remove an output"
    ac$remove_output(name)
}

acro_add_comments <- function(name, comment)
{
    "Add comments to an output"
    ac$add_comments(name, comment)
}

acro_custom_output <- function(filename, comment=NULL)
{
    "Add an unsupported output"
    ac$custom_output(filename, comment)
}

acro_add_exception <- function(name, reason)
{
    "Add an exception request to an output"
    ac$add_exception(name, reason)
}

acro_print_outputs <- function()
{
    "Prints outputs to console"
    ac$print_outputs()
}

acro_finalise <- function(path, ext)
{
    "Write outputs to file"
    ac$finalise(path, ext)
}
