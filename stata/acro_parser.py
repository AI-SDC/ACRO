## file with commands to manage the stata-acro interface

import numpy as np
import pandas as pd
import acro



def parse_and_run(df:pd.DataFrame, command_list:str)->pd.DataFrame:
    """
    Takes a dataframe and the stata command line split into a list
    Interprets the command line and runs the appropriate
    command on a pre-existing ACRO object myacro
    returns the result as a pandas dataframe
    """
    global myacro

    #now the main part parsing the command line  
    n_args = len(command_list)
    #session  management first  
    if command_list[0] == 'init':
        #initialise the acro object
        myacro = acro.ACRO()
        return  "acro analysis session created"

    elif command_list[0] == 'finalise':
        myacro.finalise("stata_out.json")
        return "outputs and stata_out.json written"

    elif command_list[0]== 'print_outputs':
        myacro.print_outputs()
        return  "outputs on screen?"
    elif command_list[0]=='table':
        if n_args==3:
            rowvar=f'{command_list[1]}'
            colvar= f'{command_list[2]}'
             
            safe_output=myacro.crosstab(df[rowvar],df[colvar])
            return  safe_output.to_string()+'\n'
        else:
            return "parser for more complex table requests not completed yet\n"
    
    
    else:
        return f'acro command not recognised: {command_list[0]}'
