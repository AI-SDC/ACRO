## file with commands to manage the stata-acro interface
import numpy as np
import pandas as pd
from acro import ACRO, add_constant



def parse_and_run(df:pd.DataFrame,
                  command:str,
                  varlist:str,
                  exclusion:str,
                  exp:str,
                  weights:str,
                  options:str)->pd.DataFrame:
    """
    Takes a dataframe and the parsed stata command line.
    Runs the appropriate command on a pre-existing ACRO object myacro
    Returns the result as a formatted string.
    """
    global myacro
    varlist= varlist.split()
    print(f' split varlist is {varlist}')

    #session  management first  
    if command == 'init':
        #initialise the acro object
        myacro = ACRO()
        return  "acro analysis session created\n"

    elif command == 'finalise':
        myacro.finalise("stata_out.json")
        return "outputs and stata_out.json written\n"

    elif command == 'print_outputs':
        myacro.print_outputs()
        return  ""
    
    elif command =='table':
        if len(options)==0:
            rowvar=f'{varlist[0]}'
            colvar= f'{varlist[1]}'
            
            ##TODO: add code to deal woith contents
            ##TODO add code to deal with super row/col vars
             
            safe_output=myacro.crosstab(df[rowvar],df[colvar])
            return  safe_output.to_string()+'\n'
        
        else:
            outstring = f' there were {n_args} commands:\n'
            for i in range(n_args):
                outstring += f'{command_list[i]}\n'
            outstring += "not all of these supported yet\n"
            return outstring
    
    
    elif command == 'regress':
        depvar = varlist[0]
        indep_vars=varlist[1:]
        new_df = df[varlist].dropna()
        y = new_df[depvar]
        x = new_df[indep_vars]
        x = add_constant(x)
        results = myacro.ols(y,x)
        res_str= results.summary().as_csv()
        return res_str
   
    elif command == 'probit':
        depvar = varlist[0]
        indep_vars=varlist[1:]
        new_df = df[varlist].dropna()
        y = new_df[depvar].astype("category").cat.codes  # numeric
        y.name = depvar
        x = new_df[indep_vars]
        x = add_constant(x)
        results = myacro.probit(y,x)
        res_str= results.summary().as_csv()
        return res_str
    
    else:
        return f'acro command not recognised: {command_list[0]}'
