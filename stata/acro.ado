* acro.ado
* Stata interface to python acro package
* created by Jim Smith June 2023 @james.smith@uwe.ac.uk
* inspired by the original safe.ado written by Felix Ritchie and lizzie Green 2020

*********************************************************************************
* main program code                                                             *
*********************************************************************************

capture program drop acro
program acro, rclass

  syntax anything [if] [in] [fweight  aweight  pweight  iweight] [, *]
  local stata_version = c(version)
  *display "`stata_version'"
  *display `"here"'
  *display `" anything is `anything'"'
  tokenize `anything'
  local command `1'
  macro shift
  local rest `*'
  *display `" command is |`command'| newvarlist is |`rest'|"'
  *display `" if is  `if'"'
  *display `" in is `in'"'
  *display `" weights are: `fweight', `aweight', `pweight', `iweight' "'
  *display `" exp is `exp'"'
  *display `"options is `options'"'
  *display `"stata_version is `stata_version'"'
  python: acrohandler("`command'", "`rest'","`if'","`exp'","`weights'","`options'", "`stata_version'")
end

python:
from sfi import Data, SFIToolkit

import numpy as np
import pandas as pd
import acro
import acro.stata_config

from acro import acro_stata_parser

debug = False
def acrohandler(command, varlist,exclusion,exp,weights,options, stata_version):
    if debug:
        outline = 'in python acrohandler function: '
        outline +=    f'command = {command} '
        outline +=    f'varlist={varlist} '
        outline +=    f'if = {exclusion} '
        outline +=    f'exp = {exp} '
        outline +=    f'weights={weights} '
        outline +=    f'options={options} '
        outline +=    f'my_version={my_version} '
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
    acro_outstr = acro_stata_parser.parse_and_run (the_data,command,varlist,exclusion,exp,weights,options,stata_version)
    SFIToolkit.display(acro_outstr)
end
