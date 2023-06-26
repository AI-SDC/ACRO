* test_file.do
* file to demonstrate how ACRO code works
*
* Created September 2020 by Felix and Lizzie

* use the 'test_data supplied with the code, or amend to your own file

* quietly {
 noisily {

  * stage 0: create folders and adopath

  local working_folder = "C:\Users\fj-ritchie\OneDrive - UWE Bristol (Staff)\consulting\GOPA\output checking\deliverable 2 ACRO"

  adopath+ "`working_folder'"

  * stage 1: set up

		capture log close
  log using "`working_folder'\test_log", replace

  safe_setup "`working_folder'" default test_results nosuppress
		
  use "`working_folder'\test_data", clear

  * Example 1: create some outputs using named sheets 
		******************************************************
		
  safe table year survivor if year>2013, contents(freq mean inc_activity sd inc_activity) output_sheet("activity") suppress
  safe table year survivor if year>2013, contents(freq mean inc_activity max inc_activity) output_sheet("max_act") suppress
		sort grant_type
  by grant_type: safe table year survivor if year>2013, contents(freq mean inc_activity max inc_activity) output_sheet("small_act") suppress exception("It's not feaible to identify the charities from this information")
		
  * Example 2: showing how you can ue macros to switch safe checking on and off easily
  ************************************************************************************
		* this loops through twice, the first as regular Stata output, and the second as 'safe' output with options
  forvalues nn = 1/2 {
		  local do_safe = ""
				local options = ""
		  if `nn'==2 {
				  local do_safe = "safe"
						local options = `" suppress exception("trust me, I'm a professor")"'
				}
				
				* note tha here we are using the automatic sheet naming option - we haven't specified sheet names
				sort grant_type
				`do_safe' tab year survivor , chi2 expected 
				by grant_type: `do_safe' tab year survivor , chi2 expected
				`do_safe' table year survivor , by(grant_type)
				`do_safe' table year survivor , by(grant_type) `options'
				
		}
		
		* Example 3 a weighted output
		safe table year survivor [pweight=wgt],  output_sheet("weighted")
		
		* example 4: regression and graph
  safe regress inc_activity inc_grants inc_donations total_costs
		safe twoway (scatter inc_grants inc_activity) , output_sheet("graph_test")
						
		* Example 5: a bit of code which doesn't do appear in 'safe' asnd so is ignored
		safe desc

		safe_finalise
		
		log close
}
   
