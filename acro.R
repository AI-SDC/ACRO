library(reticulate)  # import Python modules
library(admiraldev)
library(stringr)

acro <- import("acro")
ac <- acro$ACRO()

acro_crosstab <- function(index, columns, values=NULL, aggfunc=NULL)
{
    "ACRO crosstab"
    table = ac$crosstab(index, columns, values=values, aggfunc=aggfunc)
    return(table)
}

acro_table <- function(index, columns, dnn=NULL, deparse.level=0, ...)
{
    "ACRO crosstab without aggregation function"
    if (is.null(dnn)) {
        if (deparse.level == 0) {
        rownames <- list("")
        colnames <- list("")
        } else if (deparse.level == 1) {
            tryCatch({
                index_symbol <- assert_symbol(substitute(index))
                rownames <- list(deparse(index_symbol))},
                error = function(e) {
                    rownames <<- list("")
            })
            tryCatch({
                column_symbol <- assert_symbol(substitute(columns))
                colnames <- list(deparse(column_symbol))},
                error = function(e) {
                    colnames <<- list("")
            })
        } else if (deparse.level == 2) {
            rownames <- list(deparse((substitute(index))))
            colnames <- list(deparse(substitute(columns)))
        }
    }
    else {
        rownames <- list(dnn[1])
        colnames <- list(dnn[2])
    }

    table <- ac$crosstab(index, columns, rownames=rownames, colnames=colnames)
    # Check for any unused arguments
      if (length(list(...)) > 0) {
        warning("Unused arguments were provided: ", paste0(names(list(...)), collapse = ", "), "\n", "To find more help about the function use: acro_help(\"acro_table\")\n")
      }
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

acro_help <- function(command, family="")
{
    "Get the help documentation of the functions"
    # mapping the r commands to their corresponding python commands
    command_map <- c("acro_table" = "crosstab", "acro_lm" = "olsr",
                    "acro_glm" = ifelse(family %in% c("", "logit"), "logitr", "probitr"))

    # get the command
    command <- ifelse(command %in% names(command_map), command_map[command], sub("acro_", "", command))
    command <- ac[[command]]
    py_help(command)
}
