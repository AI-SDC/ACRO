"""
file with commands to manage the stata-acro interface
Jim Smith 2023 @james.smith@uwe.ac.uk
MIT licenses apply
"""
import pandas as pd
import statsmodels.iolib.summary as sm_iolib_summary

from acro import ACRO, add_constant
from acro.utils import prettify_table_string
from acro.utils import get_summary_dataframes


def apply_stata_ifstmt(raw: str, all_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    parses an if statment from stata format
    then uses it to subset a dataframe by contents
    '''
    if len(raw) == 0:
        return all_data

    # add braces aroubd each clause- keeping any in the original
    raw = "( " + raw + ")"
    raw = raw.replace("&", ") & (")
    raw = raw.replace("|", ") | (")
    # put spaces around operators to ease parsing
    for operator in [">", "<", "==", ">=", "<=", "!="]:
        raw = raw.replace(operator, " " + operator + " ")

    # replace variable names with df["varname"]
    for vname in all_data.columns:
        raw = raw.replace(vname, 'all_data["' + vname + '"]')

    # print(raw)
    # apply exclusion
    some_data = all_data[eval(raw)]#pylint: disable=eval-used
    return some_data


def apply_stata_expstmt(raw: str, all_data: pd.DataFrame) -> pd.DataFrame:
    '''
    parses an in exp statemnt from stata and uses it
    to subset a dataframe by set of row indices
    '''
    # stata allows f and F for first item  and l/L for last
    last = len(all_data) - 1

    token = raw.split("/")
    # first index
    if token[0] == "f" or token[0] == "F":
        start = 0
    else:
        start = int(token[0])
    if start < 0:
        start = last + 1 + start
    # last
    if "/" not in raw:
        end = last
    else:
        if token[1] == "l" or token[1] == "L":
            token[1] = last
        end = int(token[1])
        if end < 0:
            end = last + 1 + end
    # enforce start <=end
    if start > end:
        end = last

    return all_data.iloc[start:end]


def find_brace_contents(word: str, raw: str) -> (bool, str):
    '''
    given a word followed by a ( 
    finds and retirns as a list of strings
    the rest of the contents up to the closing )
    '''
    idx = raw.find(word)
    if idx == -1:
        return False, f"{word} not found"
    idx += len(word) + 1
    substr = ""
    while raw[idx] != ")" and idx < len(raw):
        substr += raw[idx]
        idx += 1

    if idx == len(raw):
        return False, "phrase nor completed"
    return True, substr


def parse_table_details(varlist: list, varnames: list, options: str) -> dict:
    """Function to parse stata-13 style table calls
    Note this is not for latest version of stata, syntax here:
    https://www.stata.com/manuals13/rtable.pdf
    >> table rowvar [colvar [supercolvar] [if] [in] [weight] [, options].
    """
    details = {"errmsg": ""}
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
    details["aggfuncs"], details["values"] = [], []
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
    details["totals"] = not "nototals" in options
    details["suppress"] = not "nosuppress" in options

    return details


def parse_and_run( #pylint: disable=too-many-arguments,too-many-locals
    data: pd.DataFrame,
    command: str,
    varlist: str,
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

    # Sometime_TODO de-abbreviate according to
    # https://www.stata.com/manuals13/u11.pdf#u11.1.3ifexp

    varlist = varlist.split()
    # print(f' split varlist is {varlist}')

    # data reduction
    if len(exclusion) > 0:
        data = apply_stata_ifstmt(exclusion, data)
    if len(exp) > 0:
        data = apply_stata_expstmt(exp, data)

    # now look at the commands
    outcome = ""
    if command in ["init","finalise","print_outputs"]:
        outcome= run_session_command(command)

    elif command == "table":
        outcome =run_table_command(data,varlist,weights,options)

    elif command in ["regress","probit","logit"]:
        outcome = run_regression(command,data, varlist)
    else:
        outcome=f"acro command not recognised: {command}"
    return outcome

def run_session_command(command:str)->str:
    '''runs session commands that are data-independent'''
    #global variable is created by stata python session
    global stata_acro #pylint: disable=global-variable-undefined
    outcome=""
    if command == "init":
        # initialise the acro object
        stata_acro = ACRO()
        outcome= "acro analysis session created\n"

    elif command == "finalise":
        stata_acro.finalise("stata_out", "json")
        outcome= "outputs and stata_out.json written\n"

    elif command == "print_outputs":
        stata_acro.print_outputs()
    else:
        outcome= f"unrecognised session management command {command}\n"
    return outcome

def run_table_command(   #pylint: disable=too-many-arguments,too-many-locals
    data: pd.DataFrame,
    varlist: list,
    weights: str,
    options: str,)->str:
    ''' 
    converts a stata table command into an acro.crosstab
    then returns a prettified versaion of the cross_tab dataframe
    '''
    weights_empty=len(weights)==0
    if not weights_empty:
        return f"weights not currently implemented for _{weights}_\n"

    varnames = data.columns
    details = parse_table_details(varlist, varnames, options)
    if len(details["errmsg"]) > 0:
        return details["errmsg"]

    aggfuncs = list(map(lambda x: x.replace("sd", "std"), details["aggfuncs"]))
    rows, cols = [], []
    for row in details["rowvars"]:
        rows.append(data[row])
    for col in details["colvars"]:
        cols.append(data[col])
    if len(aggfuncs) > 0 and len(details["values"]) > 0:
        safe_output = stata_acro.crosstab(
            index=rows,
            columns=cols,
            aggfunc=aggfuncs,
            values=details["values"],
            # suppress=details['suppress'],
            margins=details["totals"],
            margins_name="Total",
        )
    else:
        safe_output = stata_acro.crosstab(
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
        options_str = (
            "acro does not currently support table formatting commands.\n "
        )
    return options_str + prettify_table_string(safe_output) + "\n"

def run_regression(command:str,data:pd.DataFrame,varlist:list)->str:
    '''
    interprets and runs appropriate regression comand
    '''
    #get components of formula
    depvar = varlist[0]
    indep_vars = varlist[1:]
    new_data = data[varlist].dropna()
    x_var = new_data[indep_vars]
    x_var = add_constant(x_var)
    res_str=""
    if   command== "regress":
        y_var = new_data[depvar]
        results = stata_acro.ols(y_var, x_var)
        res_str=get_regr_results(results,"OLS Regression")
    elif command == "probit":
        y_var = new_data[depvar].astype("category").cat.codes  # numeric
        y_var.name = depvar
        results = stata_acro.probit(y_var, x_var)
        res_str = get_regr_results(results,"Probit Regression")
    elif command == "logit":
        y_var = new_data[depvar].astype("category").cat.codes  # numeric
        y_var.name = depvar
        results = stata_acro.logit(y_var, x_var)
        res_str = get_regr_results(results,"Logit Regression")
    else:
        res_str=f"unrecognised regression command {command}\n"
    return res_str

def get_regr_results(results:sm_iolib_summary.Summary,title:str)->str:
    '''
    translates statsmodels.io.summary object into prettified table
    '''
    res_str= title+"\n"
    for table in get_summary_dataframes(results.summary().tables):
        res_str += prettify_table_string(table,seperator=',') +"\n"
        res_str += f'{results.summary().extra_txt}\n'
    return res_str
