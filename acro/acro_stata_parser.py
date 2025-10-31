"""
File with commands to manage the stata-acro interface.

Jim Smith 2023 @james.smith@uwe.ac.uk
MIT licenses apply.
"""

import re

import pandas as pd
import statsmodels.iolib.summary as sm_iolib_summary

from acro import ACRO, acro_regression, add_constant, stata_config
from acro.utils import prettify_table_string


def apply_stata_ifstmt(raw: str, all_data: pd.DataFrame) -> pd.DataFrame:
    """Parse an if statement from stata format then use it to subset a dataframe by contents."""
    if len(raw) == 0:
        return all_data
    # lose any stray 'if' keywords that have got across
    raw = raw.replace("if", "")
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
    Parse index position tokens from stata syntax.

    Stata allows f and F for first item  and l/L for last.
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
    """Parse an in exp statement from stata and use it to subset a dataframe by row indices."""
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


def find_brace_word(word: str, raw: str):
    """Return contents as a list of strings between '(' following a word and the closing ')'.

    First returned value is True/False depending on parsing ok.
    """
    result = []
    idx = raw.find(word)
    if idx == -1:
        return False, f"{word} not found"
    while idx != -1:
        substr = ""
        idx += len(word) + 1
        while idx < len(raw) and raw[idx] != ")":
            substr += raw[idx]
            idx += 1

        if idx == len(raw):
            return False, "phrase not completed"

        result.append(substr)
        idx = raw.find(word, idx)

    return True, result


def extract_aggfun_values_from_options(contents_found, content, varnames) -> dict:
    """
    Extract the variables to aggregate, and the aggregation function.

    Parameters
    ----------
        contents_found:bool
            did the user specify what other put in cells?
        content: list(str)
            what did they ask for?

    Returns
    -------
     cell contents: (dictionary)
    """
    # contents can be variable names or aggregation functions
    cell_content: dict = {"aggfuncs": list([]), "values": list([])}
    if contents_found and len(content) > 0:
        for element in content:
            contents = element.split()
            for word in contents:
                if word in varnames:
                    if word not in cell_content["values"]:
                        cell_content["values"].append(word)
                else:
                    if word not in cell_content["aggfuncs"]:
                        cell_content["aggfuncs"].append(word)
    return cell_content


def parse_table_details(
    varlist: list, varnames: list, options: str, stata_version: float
) -> dict:
    """
    Parse table details from Stata and return as dictionary.

    Calls version relevant to stata version.

    Parameters
    ----------
    varlist : list
        list of variable names the researcher wants to form rows/cols in their table
    varnames : list
        list of variable names present in the data
        i.e. columns in the dataframe
    options : str
        string contains 'options' as parsed by Stata
        (everything after the comma)
        to be interpreted in table design
    stata_version : float
        defines how things should be interpreted
        because Stata changed syntax of the table commandfor version 17 onwards
    """
    details: dict = {"errmsg": ""}

    # get the two lists of what is wanted in the rows and columns
    if stata_version < 17:
        details.update(get_rows_cols_v16(varlist, options))
        contents_found, content = find_brace_word("contents", options)

    else:
        details.update(get_rows_cols_v17on(varlist))
        contents_found, content = find_brace_word("statistic", options)

    # check that these make sense
    if len(details["rowvars"]) == 0 or len(details["colvars"]) == 0:
        details["errmsg"] = (
            "acro does not currently support one dimensional tables. "
            "To calculate cross tabulation, you need to provide at "
            "least one row and one column."
        )
        return details

    allvars = details["rowvars"] + details["colvars"]
    unrecognised_vars = list(set(allvars) - set(varnames))
    if len(unrecognised_vars) > 0:
        details["errmsg"] += (
            f"Error: invalid names in table specifier: {unrecognised_vars}"
        )
        return details

    # get what the user wants displaying in the cells
    details.update(
        extract_aggfun_values_from_options(contents_found, content, varnames)
    )

    # default values
    details["totals"] = False
    details["suppress"] = False
    details["totals"] = "nototals" not in options
    details["suppress"] = "nosuppress" not in options

    return details


def get_rows_cols_v16(varlist: list, options: str) -> dict:
    """Parse stata-16 style table calls.

    Note this is not for latest version of stata, syntax here:
    https://www.stata.com/manuals16/rtable.pdf
    >> table rowvar [colvar [supercolvar] [if] [in] [weight] [, options].
    """
    rows_cols: dict = {"errmsg": "", "rowvars": list([]), "colvars": list([])}

    rows_cols["rowvars"] = [varlist.pop(0)]
    rows_cols["colvars"] = list(reversed(varlist))

    # by() contents are super-rows
    by_found, superrows = find_brace_word("by", options)
    if by_found and len(superrows) > 0:
        for row in superrows:
            extras = row.split()
            for word in extras:
                if word not in rows_cols["rowvars"]:
                    rows_cols["rowvars"].insert(0, word)
    return rows_cols


def stata_details_to_list(mydetails) -> list:
    """Split details which can have different formats."""
    if isinstance(mydetails, str):
        return mydetails.split()
    return list(mydetails)


def get_rows_cols_v17on(varlist: list) -> dict:
    """
    Get table details for the syntax used by stata_version >= 17.

    https://www.stata.com/manuals/tablesintro.pdf
    syntax: table (rowspec) (colspec) [ (tabspec) ] [ if ] [ in ] [ weight ] [, options ].
    """
    rows_cols: dict = {}
    rows_cols["rowvars"] = stata_details_to_list(varlist.pop(0))
    rows_cols["colvars"] = stata_details_to_list(varlist.pop(0))

    if varlist:
        rows_cols["tables"] = varlist.pop(0).split()
        # print(f"table is {details['tables']}")

    return rows_cols


def parse_and_run(  # pylint: disable=too-many-arguments
    mydata: pd.DataFrame,
    command: str,
    varlist_as_str: str,
    exclusion: str,
    exp: str,
    weights: str,
    options: str,
    stata_version: str,
) -> pd.DataFrame:
    """
    Run the appropriate command on a pre-existing ACRO object stata_acro.

    Takes a dataframe and the parsed stata command line.
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

    fstata_version = float(stata_version)
    varlist: list = varlist_as_str.split()
    # print(varlist)

    # data reduction
    # print(f'before in {mydata.shape}')
    if len(exp) > 0:
        mydata = apply_stata_expstmt(exp, mydata)
    # print(f'after in, before if {mydata.shape}')
    if len(exclusion) > 0:
        mydata = apply_stata_ifstmt(exclusion, mydata)
    # print(f'after both {mydata.shape}')

    # now look at the commands
    session_commands = [
        "init",
        "finalise",
        "enable_suppression",
        "disable_suppression",
        "print_outputs",
    ]
    output_commands = [
        "custom_output",
        "remove_output",
        "rename_output",
        "add_comments",
        "add_exception",
    ]
    regression_commands = ["regress", "probit", "logit"]
    outcome = ""
    if command in session_commands:
        outcome = run_session_command(command, varlist)
    elif command in output_commands:
        outcome = run_output_command(command, varlist)
    elif command in regression_commands:
        outcome = run_regression(command, mydata, varlist)
    elif command == "table" and fstata_version == 16:
        outcome = run_table_command(mydata, varlist, weights, options, fstata_version)
    elif command == "table" and fstata_version >= 17:
        varlist = extract_strings(varlist_as_str)
        outcome = run_table_command(mydata, varlist, weights, options, fstata_version)

    else:
        outcome = f"acro command not recognised: {command}"
    return outcome


def run_session_command(command: str, varlist: list) -> str:
    """Run session commands that are data-independent."""
    outcome = ""

    if command == "init":
        stata_config.stata_acro = ACRO()
        outcome = "acro analysis session created\n"

    elif command == "enable_suppression":
        stata_config.stata_acro.suppress = True
        outcome = "suppression toggled on for subsequent commands"
    elif command == "disable_suppression":
        stata_config.stata_acro.suppress = False
        outcome = "suppression toggled off for subsequent commands"
    elif command == "finalise":
        suffix = "json"
        out_dir = "stata_outputs"
        if len(varlist) == 1:
            out_dir = varlist[0]
        if len(varlist) == 2:
            out_dir = varlist[0]
            suffix = varlist[1]
        stata_config.stata_acro.finalise(out_dir, suffix)
        outcome = "outputs and stata_outputs.json written\n"

    elif command == "print_outputs":
        stata_config.stata_acro.print_outputs()

    return outcome


def run_output_command(command: str, varlist: list) -> str:
    """Run outcome-level commands.

    First element of varlist is output affected
    rest (if relevant) is string passed to command.
    """
    outcome = ""
    if len(varlist) == 0:
        return "syntax error: please pass the name of the output to be changed"

    the_output = varlist.pop(0)

    if command == "custom_output":
        comment_str = " ".join(varlist)
        stata_config.stata_acro.custom_output(the_output, comment_str)
        outcome = f"file {the_output} with comment {comment_str} added to session."

    # safety- rest of commands need an existing output to work on
    elif (  # pylint:disable=consider-iterating-dictionary
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

    return outcome


def extract_var_within_parentheses(input_string):
    """Extract the words within the first parentheses from a string."""
    string = ""
    string_match = re.match(r"\((.*?)\)", input_string)
    if string_match:
        string = string_match.group(1).strip()
        input_string = input_string[len(string_match.group(0)) :].strip()
    return string, input_string


def extract_var_before_parentheses(input_string):
    """Extract the words before the first parentheses."""
    string = ""
    string_match = re.match(r"^(.*?)\(", input_string)
    if string_match:
        string = string_match.group(1).strip()
        input_string = input_string[len(string_match.group(1)) :].strip()
    return string, input_string


def extract_table_var(input_string):
    """Extract the words within the parentheses.

    If there are no parentheses the string is returned.
    """
    string = ""
    # If the string starts with parentheses
    if input_string.startswith("("):
        string, _ = extract_var_within_parentheses(input_string)
    elif input_string:
        string = input_string.strip()
    return string


def extract_colstring_tablestring(input_string):
    """Extract the column and the tables variables as a string.

    It goes through different options eg. whether the column string is between paranthese or not.
    """
    colstring = ""
    tablestring = ""
    if input_string.startswith("("):
        colstring, input_string = extract_var_within_parentheses(input_string)
        if input_string:
            tablestring = extract_table_var(input_string)

    elif "(" not in input_string:
        words = input_string.split()
        colstring = " ".join(words[:])

    else:
        colstring, input_string = extract_var_before_parentheses(input_string)
        if input_string:
            tablestring = extract_table_var(input_string)
    return colstring, tablestring


def extract_strings(input_string):
    """Extract the index, column and the tables variables as a string.

    It goes through different options eg. whether the index string is between paranthese or not.
    """
    rowstring = ""
    colstring = ""
    tablestring = ""

    # If the string doesn’t have parentheses
    if "(" not in input_string:
        words = input_string.split()
        rowstring = " ".join(words[:-1])
        colstring = words[-1]

    # If the string has parentheses
    else:
        # If there are parentheses at the start of the string
        if input_string.startswith("("):
            rowstring, input_string = extract_var_within_parentheses(input_string)
            colstring, tablestring = extract_colstring_tablestring(input_string)

        else:
            # If there are parentheses at the middle of the string
            rowstring, input_string = extract_var_before_parentheses(input_string)
            colstring, tablestring = extract_colstring_tablestring(input_string)
    varlist = [rowstring, colstring, tablestring]
    return varlist


def creates_datasets(data, details):
    """Return the full dataset if the tables parameter is empty.

    Otherwise, it divides the dataset to small dataset each one is the dataset when
    the tables parameter is equal to one of it is unique values.
    """
    set_of_data = {"Total": data}
    msg = ""
    # if tables var parameter was assigned, each table will
    # be treated as an exclusion which will be applied to the data.
    # The number of datasets will be equal to the number of unique values in the tables var
    # Crosstabulation will be calculate for each dataset
    if "tables" in details and details["tables"] != []:
        # print(f"table is {details['tables']}")
        msg = (
            "You need to manually check all the outputs for the risk of differencing.\n"
        )
        for table in details["tables"]:
            unique_values = data[table].unique()
            # print(f"unique_values are {unique_values}")
            for value in unique_values:
                if isinstance(value, str):
                    exclusion = f"{table}=='{value}'"
                else:  # pragma: no cover
                    exclusion = f"{table}=={value}"
                # print(f"exclusion is {exclusion}")
                my_data = apply_stata_ifstmt(exclusion, data)
                set_of_data[exclusion] = my_data
    return set_of_data, msg


def run_table_command(  # pylint: disable=too-many-locals
    data: pd.DataFrame,
    varlist: list,
    weights: str,
    options: str,
    stata_version: float,
) -> str:
    """Convert a stata table command into an acro.crosstab and return a prettified dataframe."""
    weights_empty = len(weights) == 0
    if not weights_empty:  # pragma
        return f"weights not currently implemented for _{weights}_\n"

    varnames = data.columns
    details = parse_table_details(varlist, varnames, options, stata_version)
    if len(details["errmsg"]) > 0:
        return details["errmsg"]

    aggfuncs = list(map(lambda x: x.replace("sd", "std"), details["aggfuncs"]))
    # don't pass single aggfunc as a list
    if len(aggfuncs) == 1:
        aggfuncs = aggfuncs[0]

    set_of_data, msg = creates_datasets(data, details)

    results = ""
    for exclusion, my_data in set_of_data.items():
        rows, cols = [], []
        # print(f"my data is {my_data}")
        for row in details["rowvars"]:
            rows.append(my_data[row])
        for col in details["colvars"]:
            cols.append(my_data[col])
        # print(f"rows are {rows}")
        # print(f"cols are {cols}")
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
            print(exclusion)
            safe_output = stata_config.stata_acro.crosstab(
                index=rows,
                columns=cols,
                aggfunc=aggfuncs,
                values=values,
                margins=details["totals"],
                margins_name="Total",
            )

        else:
            print(exclusion)
            safe_output = stata_config.stata_acro.crosstab(
                index=rows,
                columns=cols,
                # suppress=details['suppress'],
                margins=details["totals"],
                margins_name="Total",
            )
        results += f"{exclusion}\n{prettify_table_string(safe_output)}\n"

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
            options_str = (
                "acro does not currently support table formatting commands.\n "
            )
    return msg + options_str + results


def run_regression(command: str, data: pd.DataFrame, varlist: list) -> str:
    """Interpret and run appropriate regression command."""
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
    """Translate statsmodels.io.summary object into prettified table."""
    res_str = title + "\n"
    for table in acro_regression.get_summary_dataframes(results.summary().tables):
        res_str += prettify_table_string(table, separator=",") + "\n"
        res_str += f"{results.summary().extra_txt}\n"
    return res_str
