## file with commands to manage the stata-acro interface
import numpy as np
import pandas as pd

from acro import ACRO, add_constant


def parse_and_run(df: pd.DataFrame, varlist: str) -> pd.DataFrame:
    """
    Takes a dataframe and the stata command line split into a list
    Interprets the command line and runs the appropriate
    command on a pre-existing ACRO object myacro
    returns the result as a pandas dataframe
    """
    global myacro

    # now the main part parsing the command line
    ##TODO this is going to need to be more complex
    ## to account for stata key words
    ## for now just split on white spaces
    command_list = varlist.split()
    n_args = len(command_list)
    command = command_list[0]

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

    elif command == "table":
        if n_args == 3:
            rowvar = f"{command_list[1]}"
            colvar = f"{command_list[2]}"

            safe_output = myacro.crosstab(df[rowvar], df[colvar])
            return safe_output.to_string() + "\n"

        else:
            outstring = f" there were {n_args} commands:\n"
            for i in range(n_args):
                outstring += f"{command_list[i]}\n"
            outstring += "not all of these supported yet\n"
            return outstring

    elif command == "regress":
        depvar = command_list[1]
        indep_vars = []
        for newvar in range(2, n_args):
            indep_vars.append(command_list[newvar])
        new_df = df[[depvar] + indep_vars].dropna()
        y = new_df[depvar]
        x = new_df[indep_vars]
        x = add_constant(x)
        results = myacro.ols(y, x)
        res_str = results.summary().as_csv()
        return res_str

    elif command == "probit":
        depvar = command_list[1]
        indep_vars = []
        for newvar in range(2, n_args):
            indep_vars.append(command_list[newvar])
        new_df = df[[depvar] + indep_vars].dropna()
        y = new_df[depvar].astype("category").cat.codes  # numeric
        y.name = depvar
        x = new_df[indep_vars]
        x = add_constant(x)
        results = myacro.probit(y, x)
        res_str = results.summary().as_csv()
        return res_str

    else:
        return f"acro command not recognised: {command_list[0]}"
