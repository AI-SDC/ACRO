# file with commands to manage the stata-acro interface
import pandas as pd

from acro import ACRO, add_constant


def apply_stata_ifstmt(raw: str, df: pd.DataFrame) -> pd.DataFrame:
    if len(raw == 0):
        return df
    else:
        # add braces aroubd each clause- keeping any in the original
        raw = "( " + raw + ")"
        raw = raw.replace("&", ") & (")
        raw = raw.replace("|", ") | (")
        # put spaces aroubd operators to ease parsing
        for operator in [">", "<", "==", ">=", "<=", "!="]:
            raw = raw.replace(operator, " " + operator + " ")

        # replace variable names with df["varname"]
        for vname in df.columns:
            raw = raw.replace(vname, 'df["' + vname + '"]')

        # print(raw)
        # apply exclusion
        df2 = df[eval(raw)]
        return df2


def apply_stata_expstmt(raw: str, df: pd.DataFrame) -> pd.DataFrame:
    # stata allows f and F for first item  and l/L for last
    last = len(df) - 1

    token = raw.split("/")
    # first index
    if token[0] == "f" or token[0] == "F":
        start = 0
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

    return df.iloc[start:end]


def find_brace_contents(word: str, raw: str) -> (bool, str):
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
    else:
        return True, substr


def parse_table_details(varlist: list, varnames: list, options: str) -> dict:
    """function to parse stata-13 style table calls
    Note this is not for latest version of stata, syntax here:
    https://www.stata.com/manuals13/rtable.pdf
    >> table rowvar [colvar [supercolvar] [if] [in] [weight] [, options]
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
    details["totals"] = False if "nototals" in options else True
    details["suppress"] = False if "nosuppress" in options else True

    return details


def parse_and_run(
    df: pd.DataFrame,
    command: str,
    varlist: str,
    exclusion: str,
    exp: str,
    weights: str,
    options: str,
) -> pd.DataFrame:
    """
    Takes a dataframe and the parsed stata command line.
    Runs the appropriate command on a pre-existing ACRO object myacro
    Returns the result as a formatted string.
    """

    # TODO de-abbreviate according to
    # https://www.stata.com/manuals13/u11.pdf#u11.1.3ifexp

    global myacro
    varlist = varlist.split()
    # print(f' split varlist is {varlist}')

    # data reduction
    if len(exclusion) > 0:
        df = apply_stata_ifstmt(exclusion, df)
    if len(exp) > 0:
        df = apply_stata_expstmt(exp, df)

    # now look at the commands
    # session  management first
    if command == "init":
        # initialise the acro object
        myacro = ACRO()
        return "acro analysis session created\n"

    elif command == "finalise":
        myacro.finalise("stata_out.json")
        return "outputs and stata_out.json written\n"

    elif command == "print_outputs":
        myacro.print_outputs()
        return ""

    # now statistical commands
    elif command == "table":
        varnames = df.columns

        details = parse_table_details(varlist, varnames, options)
        if len(details["errmsg"]) > 0:
            return details["errmsg"]
        else:
            aggfuncs = list(map(lambda x: x.replace("sd", "std"), details["aggfuncs"]))
            rows, cols = [], []
            for row in details["rowvars"]:
                rows.append(df[row])
            for col in details["colvars"]:
                cols.append(df[col])
            if len(aggfuncs) > 0 and len(details["values"]) > 0:
                safe_output = myacro.crosstab(
                    index=rows,
                    columns=cols,
                    aggfunc=aggfuncs,
                    values=details["values"],
                    # suppress=details['suppress'],
                    margins=details["totals"],
                    margins_name="Total",
                )
            else:
                safe_output = myacro.crosstab(
                    index=rows,
                    columns=cols,
                    # suppress=details['suppress'],
                    margins=details["totals"],
                    margins_name="Total",
                )
            return safe_output.to_string() + "\n"

    elif command == "regress":
        depvar = varlist[0]
        indep_vars = varlist[1:]
        new_df = df[varlist].dropna()
        y = new_df[depvar]
        x = new_df[indep_vars]
        x = add_constant(x)
        results = myacro.ols(y, x)
        res_str = results.summary().as_csv()
        return res_str

    elif command == "probit":
        depvar = varlist[0]
        indep_vars = varlist[1:]
        new_df = df[varlist].dropna()
        y = new_df[depvar].astype("category").cat.codes  # numeric
        y.name = depvar
        x = new_df[indep_vars]
        x = add_constant(x)
        results = myacro.probit(y, x)
        res_str = results.summary().as_csv()
        return res_str

    else:
        return f"acro command not recognised: {command}"
