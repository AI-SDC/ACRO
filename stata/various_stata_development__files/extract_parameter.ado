* extract_parameter.ado
* Stata program to extract the parameter value associaed with an option mame in a list
* V01 created July 2020 by Felix Ritchie
* Last modified:
*  dd.mm.yy vxx who what

* to use this program, send a string with the parametr you want extracted in
* brackets after the value to identify eg
*   extract_parameter filename "opt1 opt2 filename("myfile") other_opt"
*   => r(extract) = "myfile"
* the parameter must be in brackets straight after the parameter name - no spaces
* NB if parameter not found (or there is a space before the bracket) the return is ".", NOT a null string

capture program drop extract_parameter

program extract_parameter, rclass
  args param long_text

		local param_pos = strpos(`"`long_text'"', "`param'(")
		local pvalue = "."
		if `param_pos' > 0 {
		  * value found
				local param_len = strlen("`param'")+1
		  local long_text = substr(`"`long_text'"',`param_pos'+`param_len',.)
				local end_pos = strpos(`"`long_text'"', ")")
				if `end_pos' >0 {
  				local pvalue = substr(`"`long_text'"', 1,`end_pos'-1)
				}
		}
		return local extract = `"`pvalue'"'
end


