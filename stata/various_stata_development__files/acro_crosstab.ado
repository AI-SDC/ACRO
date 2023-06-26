program acro_crosstab , rclass byable(recall, noheader)

  version 17

  syntax varlist(min=1 max=2) [if] [in] [fweight  aweight  pweight  iweight] [ suppress no_write *]
  marksample touse ,strok
 noisily
{
  display `"The arguments are: `0'"'
  extract_parameter "contents"
  local the_contents = r(extract)
  
  * call the Python function
   python  acro_crosstab(varlist,the_contents)
}
end

version 17
python 
from sfi import Data, Macro, Missing, SFIToolkit
import acro

#def acro_crosstab( features,varlist,values, aggfuncs="mean"):
def acro_crosstab( varlist,values, aggfuncs="mean"):
    #df = np.array(Data.get())
    print('hello world')
    #what have we been given? 
    starters= "In func we have been given:\n"
    starters +=f' varlist: {varlist}\n'
    starters += f'aggfuncs: {aggfuncs}\n'
    SFIToolkit.displayln(starters)

    #myacro=ACRO()
    #the_table= acro.crosstab(df.rowvar,df.colvar,values=df.values,aggfunc=aggfunction)


    #write report to screen
    #feedback = "table is:\n"
    #feedback += f'the_table + "\n"
    #feedback += "======================"
    #feedback += "current outputs from myacro.print_ouptputs() ======\n" 
    #feedback += f'myacro.print_outputs()' 
    #feedback += "========================="
    #myacro.finalise('stata_test_results.xlsx')
    #feedback += "sdc outputs written to stata_test_results.xlsx" 
    #SFIToolkit.displayln(feedback)

end
