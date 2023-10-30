library(reticulate)  # import Python modules
library(admiraldev)
library(png)
library(grid)

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
        row_names <- list("")
        col_names <- list("")
        } else if (deparse.level == 1) {
            tryCatch({
                index_symbol <- assert_symbol(substitute(index))
                row_names <- list(deparse(index_symbol))},
                error = function(e) {
                    row_names <- list("")
            })
            tryCatch({
                column_symbol <- assert_symbol(substitute(columns))
                col_names <- list(deparse(column_symbol))},
                error = function(e) {
                    col_names <- list("")
            })
        } else if (deparse.level == 2) {
            row_names <- list(deparse((substitute(index))))
            col_names <- list(deparse(substitute(columns)))
        }
    }
    else {
        row_names <- list(dnn[1])
        col_names <- list(dnn[2])
    }

    table <- ac$crosstab(index, columns, rownames=row_names, colnames=col_names)
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

acro_hist <- function(data, column, breaks=10, freq=TRUE, col=NULL, filename="histogram.png"){
    "ACRO histogram"
    histogram = ac$hist(data=data, column=column, bins=breaks, density=freq, color=col, filename=filename)
    # Load the saved histogram
    image <- readPNG(histogram)
    grid.raster(image)
}

acro_surv_func <- function(time, status, output, filename="kaplan-meier.png"){
    "Estimates the survival function. Produce either a plot of table"
    results = ac$surv_func(time=time, status=status, output=output, filename=filename)
    if (output=="plot"){
        # Loasd the saved survival plot
        image <- readPNG(results[[2]])
        grid.raster(image)
        }
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
