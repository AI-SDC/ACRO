* acro.ado
* Stata interface to python acro package
* created by Jim Smith June 2023 @james.smith@uwe.ac.uk
* inspired by the original safe.ado written by Felix Ritchie and lizzie Green 2020


*********************************************************************************
* main program code                                                             *
*********************************************************************************
	
capture program drop acro
program  acro, rclass
  version 18
  *syntax varlist
  local command = `"`0'"'
  display `"command is "  `command' " "'
  *display `command'
  python: acrohandler("`command'")

end

version 18
python
from sfi import Data, Macro, Missing, SFIToolkit, Scalar
import acro
import pandas as pd

def acrohandler(varlist):
    debug=False
    # parse command line
    command_list = varlist.split()
    n_args= len(command_list)
    if(debug):
        theline= f'acrohandler received this command: {varlist}\n'
        SFIToolkit.displayln(theline)
        theline += f'which it split into {n_args} tokens:\n'
        for tok in range(n_args):
            theline+= f'  _{command_list[tok]}_\n'
        with open ("pyout.txt",mode="w") as f:
            f.write(theline) 
        SFIToolkit.displayln("command line parsed")
    
    #make data object
    nvars= Data.getVarCount()
    colnames= []
    for col in range(nvars):
        colnames.append(Data.getVarName(col))
    if debug:
        SFIToolkit.displayln(f'var names are {colnames}')
    the_data= pd.DataFrame(Data.get(),columns=colnames)
    
    if debug:
        contents = the_data.describe()
        contents.to_csv("contents.csv") 

    #now do the acro part
    myacro=acro.ACRO()
    if command_list[0]=='table':
        if n_args==3:
            rowvar=f'{command_list[1]}'
            colvar= f'{command_list[2]}'
            safetable=myacro.crosstab(the_data[rowvar],the_data[colvar])
            SFIToolkit.display(safetable.to_string()+'\n')
        #myacro.print_outputs()
    myacro.finalise("stata_outs.json")


end
