* acro.ado
* Stata interface to python acro package
* created by Jim Smith June 2023 @james.smith@uwe.ac.uk
* inspired by the original safe.ado written by Felix Ritchie and lizzie Green 2020


*********************************************************************************
* main program code                                                             *
*********************************************************************************
	
capture program drop acro
program acro2, rclass
  syntax anything [if] [in] [fweight  aweight  pweight  iweight] [, *] 
  display `"here"' 
  display `" anything is `anything'"'
  tokenize `anything'
  local command `1'
  macro shift
  local rest `*'
  display `" command is |`command'| newvarlist is |`rest'|"'
  display `" if is  `if'"'
  display `" in is `in'"'
  display `" weights are: `fweight', `aweight', `pweight', `iweight' "'
  display `" exp is `exp'"'
  display `"options is `options'"'  
  python: acrohandler("`command'", "`rest'","`if'","`exp'","`weights'","`options'")
  

version 18
python
from sfi import Data, Macro, Missing, SFIToolkit, Scalar
import acro
import numpy as np
import pandas as pd
import acro_parser 
myacro="empty"
def acrohandler(command, varlist,exclusion,exp,weights,options):
	if debug:
		outline =( 'in python acrohandler function: ',
			f'command = {command}',
			f'varlist={varlist}',
			f'if = {exclusion}',
			f'exp = {exp}',
			f'weights={weights}',
			f'options={options}'
		)
	    SFIToolkit.displayln(outline)	
 
    
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
    acro_outstr = acro_parser.parse_and_run (the_data,command,varlist,exclusion,exp,weights,options)
    SFIToolkit.display(acro_outstr)
end

