"""
File with commands to manage the stata-acro interface
Jim Smith 2023 @james.smith@uwe.ac.uk
MIT licenses apply.
"""
import pandas as pd
import statsmodels.iolib.summary as sm_iolib_summary

from acro import ACRO, acro_regression, add_constant, stata_config
from acro.utils import prettify_table_string


def apply_stata_ifstmt(raw: str, all_data: pd.DataFrame) -> pd.DataFrame:
    """
    Parses an if statement from stata format
    then uses it to subset a dataframe by contents.
    """
    if len(raw) == 0:
        return all_data

    # add braces around each clause- keeping any in the original
    raw = "( " + raw + ")"
    raw = raw.replace("&", ") & (")
    raw = raw.replace("|", ") | (")
    # put spaces around operators to ease parsing
    for operator in [">", "<", "==", ">=", "<=", "!="]:
        raw = raw.replace(operator, " " + operator + " ")

    # apply exclusion
    some_data = all_data.query(raw)
    return some_data


def parse_location_token(token: str, last: int) -> int:
    """
    Parses index position tokens from stata syntax
    stata allows f and F for first item  and l/L for last.
    """
    lookup: dict = {"f": 0, "F": 0, "l": last, "L": last}
    if token in ["f", "F", "l", "L"]:
        pos = lookup[token]
    else:
        try:
            pos = int(token)
            if pos > 0:
                pos -= 1
        except ValueError:
            print("valuerror")
            pos = 0
    return pos


def apply_stata_expstmt(raw: str, all_data: pd.DataFrame) -> pd.DataFrame:
    """
    Parses an in exp statement from stata and uses it
    to subset a dataframe by set of row indices.
    """
    last = len(all_data) - 1
    if "/" not in raw:
        pos = parse_location_token(raw, last)
        if pos < 0:
            start = max(0, last + pos + 1)
            end = last
        else:
            start = 0
            end = min(pos, last)

    else:
        token: list = raw.split("/")
        # first index
        start = parse_location_token(token[0], last)
        if start < 0:
            start = last + 1 + start  # -1==last
        # last index
        end = parse_location_token(token[1], last)
        if end < 0:
            end = last + end  # -1==last
        # enforce start <=end
        if start > end:
            end = last

    return all_data.iloc[start : end + 1]


def find_brace_contents(word: str, raw: str):
    """
    Given a word followed by a (
    finds and returns as a list of strings
    the rest of the contents up to the closing ).
    first returned value is True/False depending on parsing ok.
    """
    idx = raw.find(word)
    if idx == -1:
        return False, f"{word} not found"
    idx += len(word) + 1
    substr = ""
    while idx < len(raw) and raw[idx] != ")":
        substr += raw[idx]
        idx += 1

    if idx == len(raw):
        return False, "phrase not completed"
    return True, substr


def parse_table_details(varlist: list, varnames: list, options: str) -> dict:
    """Function to parse stata-16 style table calls
    Note this is not for latest version of stata, syntax here:
    https://www.stata.com/manuals16/rtable.pdf
    >> table rowvar [colvar [supercolvar] [if] [in] [weight] [, options].
    """
    details: dict = {"errmsg": "", "rowvars": list([]), "colvars": list([])}
    details["rowvars"] = [varlist.pop(0)]
    details["colvars"] = list(reversed(varlist))
    # by() contents are super-rows
    found, superrows = find_brace_contents("by", options)
    if found and len(superrows) > 0:
        extras = superrows.split()
        for word in extras:
            if word not in varnames:
                details[
                    "errmsg"
                ] = f"Error: word {word} in by-list is not a variables name"
                return details
            if word not in details["rowvars"]:
                details["rowvars"].insert(0, word)

    # contents can be variable names or aggregation functions
    details["aggfuncs"], details["values"] = list([]), list([])
    found, content = find_brace_contents("contents", options)
    if found and len(content) > 0:
        contents = content.split()
        for word in contents:
            if word in varnames:
                if word not in details["values"]:
                    details["values"].append(word)
            else:
                if word not in details["aggfuncs"]:
                    details["aggfuncs"].append(word)

    # default values
    details["totals"] = False
    details["suppress"] = False
    details["totals"] = "nototals" not in options
    details["suppress"] = "nosuppress" not in options

    return details


def parse_and_run(  # pylint: disable=too-many-arguments,too-many-locals
    mydata: pd.DataFrame,
    command: str,
    varlist_as_str: str,
    exclusion: str,
    exp: str,
    weights: str,
    options: str,
) -> pd.DataFrame:
    """
    Takes a dataframe and the parsed stata command line.
    Runs the appropriate command on a pre-existing ACRO object stata_acro
    Returns the result as a formatted string.
    """
    # sanity checking
    # can only call init if acro object has not been created
    if command != "init" and isinstance(
        stata_config.stata_acro, str
    ):  # pragma: no cover
        return "You must run acro init before any other acro commands"

    # Sometime_TODO de-abbreviate according to
    # https://www.stata.com/manuals13/u11.pdf#u11.1.3ifexp

    varlist: list = varlist_as_str.split()
    # print(f' split varlist is {varlist}')

    # data reduction
    # print(f'before in {mydata.shape}')
    if len(exp) > 0:
        mydata = apply_stata_expstmt(exp, mydata)
    # print(f'after in, before if {mydata.shape}')
    if len(exclusion) > 0:
        mydata = apply_stata_ifstmt(exclusion, mydata)
    # print(f'after both {mydata.shape}')

    # now look at the commands
    outcome = ""
    if command in ["init", "finalise", "print_outputs"]:
        outcome = run_session_command(command, varlist)
    elif command in ["remove_output", "rename_output", "add_comments", "add_exception"]:
        outcome = run_output_command(command, varlist)
    elif command == "table":
        outcome = run_table_command(mydata, varlist, weights, options)

    elif command in ["regress", "probit", "logit"]:
        outcome = run_regression(command, mydata, varlist)
    else:
        outcome = f"acro command not recognised: {command}"
    return outcome


def run_session_command(command: str, varlist: list) -> str:
    """Runs session commands that are data-independent."""
    outcome = ""

    if command == "init":
        # initialise the acro object
        stata_config.stata_acro = ACRO()
        outcome = "acro analysis session created\n"

    elif command == "finalise":
        suffix = "json"
        out_dir = "stata_outputs"
        if len(varlist) == 1:
            out_dir = varlist[0]
        if len(varlist) == 2:
            out_dir = varlist[0]
            preference = varlist[1]
            if preference == "xlsx":
                suffix = "xlsx"
        stata_config.stata_acro.finalise(out_dir, suffix)
        outcome = "outputs and stata_outputs.json written\n"

    elif command == "print_outputs":
        stata_config.stata_acro.print_outputs()
    else:  # pragma: no cover
        outcome = f"unrecognised session management command {command}\n"
    return outcome


def run_output_command(command: str, varlist: list) -> str:
    """Runs outcome-level commands
    first element of varlist is output affected
    rest (if relevant) is string passed to command.
    """
    if len(varlist) == 0:
        return "syntax error: please pass the name of the output to be changed"

    the_output = varlist.pop(0)
    # safety
    if (  # pylint:disable=consider-iterating-dictionary
        the_output not in stata_config.stata_acro.results.results.keys()
    ):
        return f"no output with name  {the_output} in current acro session.\n"

    if command == "remove_output":
        stata_config.stata_acro.remove_output(the_output)
        outcome = f"output {the_output} removed.\n"
    elif command in ["rename_output", "add_comments", "add_exception"]:
        # more arguments needed
        the_str = " ".join(varlist)
        if len(the_str) == 0:
            return f"not enough arguments provided for command {command}.\n"
        if command == "rename_output":
            stata_config.stata_acro.rename_output(the_output, the_str)
            outcome = f"output {the_output} renamed to {the_str}.\n"
        elif command == "add_comments":
            stata_config.stata_acro.add_comments(the_output, the_str)
            outcome = f"Comments added to output {the_output}.\n"
        elif command == "add_exception":
            stata_config.stata_acro.add_exception(the_output, the_str)
            outcome = f"Exception request added to output {the_output}.\n"
    else:  # pragma: no cover
        outcome = f"unrecognised outcome management command {command}\n"

    return outcome


def run_table_command(  # pylint: disable=too-many-arguments,too-many-locals
    data: pd.DataFrame,
    varlist: list,
    weights: str,
    options: str,
) -> str:
    """
    Converts a stata table command into an acro.crosstab
    then returns a prettified versaion of the cross_tab dataframe.
    """
    weights_empty = len(weights) == 0
    if not weights_empty:  # pragma
        return f"weights not currently implemented for _{weights}_\n"

    varnames = data.columns
    details = parse_table_details(varlist, varnames, options)
    if len(details["errmsg"]) > 0:
        return details["errmsg"]

    aggfuncs = list(map(lambda x: x.replace("sd", "std"), details["aggfuncs"]))
    rows, cols = [], []
    # don't pass single aggfunc as a list
    if len(aggfuncs) == 1:
        aggfuncs = aggfuncs[0]

    for row in details["rowvars"]:
        rows.append(data[row])
    for col in details["colvars"]:
        cols.append(data[col])
    if len(aggfuncs) > 0 and len(details["values"]) > 0:
        # sanity checking
        # if len(rows) > 1 or len(cols) > 1:
        #     msg = (
        #         "acro crosstab with an aggregation function "
        #         " does not currently support hierarchies within rows or columns"
        #     )
        #     return msg

        if len(details["values"]) > 1:
            msg = (
                "pandas crosstab can  aggregate over multiple functions "
                "but only over one feature/attribute: provided as 'value'"
            )
            return msg
        val = details["values"][0]
        values = data[val]

        safe_output = stata_config.stata_acro.crosstab(
            index=rows,
            columns=cols,
            aggfunc=aggfuncs,
            values=values,
            margins=details["totals"],
            margins_name="Total",
        )

    else:
        safe_output = stata_config.stata_acro.crosstab(
            index=rows,
            columns=cols,
            # suppress=details['suppress'],
            margins=details["totals"],
            margins_name="Total",
        )
    options_str = ""
    formatting = [
        "cellwidth",
        "csepwidth",
        "stubwidth",
        "scsepwidth",
        "center",
        "left",
    ]
    if any(word in options for word in formatting):
        options_str = "acro does not currently support table formatting commands.\n "
    return options_str + prettify_table_string(safe_output) + "\n"


def run_regression(command: str, data: pd.DataFrame, varlist: list) -> str:
    """Interprets and runs appropriate regression command."""
    # get components of formula
    depvar = varlist[0]
    indep_vars = varlist[1:]
    new_data = data[varlist].dropna()
    x_var = new_data[indep_vars]
    x_var = add_constant(x_var)
    res_str = ""
    if command == "regress":
        y_var = new_data[depvar]
        results = stata_config.stata_acro.ols(y_var, x_var)
        res_str = get_regr_results(results, "OLS Regression")
    elif command == "probit":
        y_var = new_data[depvar].astype("category").cat.codes  # numeric
        y_var.name = depvar
        results = stata_config.stata_acro.probit(y_var, x_var)
        res_str = get_regr_results(results, "Probit Regression")
    elif command == "logit":
        y_var = new_data[depvar].astype("category").cat.codes  # numeric
        y_var.name = depvar
        results = stata_config.stata_acro.logit(y_var, x_var)
        res_str = get_regr_results(results, "Logit Regression")
    else:  # pragma: no cover
        res_str = f"unrecognised regression command {command}\n"
    return res_str


def get_regr_results(results: sm_iolib_summary.Summary, title: str) -> str:
    """Translates statsmodels.io.summary object into prettified table."""
    res_str = title + "\n"
    for table in acro_regression.get_summary_dataframes(results.summary().tables):
        res_str += prettify_table_string(table, separator=",") + "\n"
        res_str += f"{results.summary().extra_txt}\n"
    return res_str
