## file with commands to manage the stata-acro interface
import numpy as np
import pandas as pd
from acro import ACRO, add_constant

def apply_stata_ifstmt(raw:str, df:pd.DataFrame)->pd.Dataframe:
    if len(raw==0):
        return df
    else:
        #add braces aroubd each clause- keeping any in the original
        raw= "( " + raw + ")"
        raw= raw.replace("&",") & (")
        raw= raw.replace("|",") | (")
        #put spaces aroubd operators to ease parsing
        for operator in [">","<","==",">=","<=","!="]:
            raw=raw.replace(operator,' '+operator+' ') 

        #replace variable names with df["varname"]
        for vname in df.columns:
            raw=raw.replace(vname,'df["'+vname+'"]')

        #print(raw)
        #apply exclusion
        df2 = df[eval(raw)]
        return df2
    
    
def apply_stata_expstmt(raw:str,df:pd.Dataframe)->pd.DataFrame:
    #stata allows f and F for first item  and l/L for last
    last=len(df)-1
    
    token= string.split("/")
    #firsrt index
    if token[0]=='f' or token[0]=='F':
        start=0
    start = int(token[0])
    if start < 0:
        start= last + 1 + start
    #last    
    if "/" not in string:
        end = last
    else:
        if token[1]=='l' or token[1]=='L':
            token[1]=last
        end= int(token[1])
        if end <0:
            end=length + 1 + end
    #enforce start <=end
    if(start>end):
        end=length
        
    return df.iloc[start:end]

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

    
    # data reduction
    if len(exclusion>0):
        df = apply_stata_if(exclusion,df)
    if len(exp>0):
        df = apply_stata_expstmt(raw,df)
    
    #now look at the commands
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
    
    # now statistical commands
    elif command =='table':
        if len(options)==0:
            rowvar=f'{varlist[0]}'
            colvar= f'{varlist[1]}'
            
 
             
            if 'nototals' in options:
                safe_output=myacro.crosstab(df[rowvar],df[colvar])
            else:
                safe_output=myacro.crosstab(df[rowvar],df[colvar],
                                        margins=True,
                                       margins_name='Total',)
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
