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
  local command = `"`0'"'
  python: acrohandler("`command'")

end

version 18
python
from sfi import Data, Macro, Missing, SFIToolkit, Scalar
import acro
import numpy as np
import pandas as pd
import acro_parser 
myacro="empty"
def acrohandler(varlist):
    debug=False
    # parse command line

    if(debug):
        command_list = varlist.split()
        n_args= len(command_list)
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
    the_data= pd.DataFrame(Data.get(missingval=np.nan),columns=colnames)
    
    if debug:
        contents = the_data.describe()
        contents.to_csv("contents.csv") 

    #now do the acro part
    acro_outstr = acro_parser.parse_and_run (the_data,varlist)
    SFIToolkit.display(acro_outstr)
end

