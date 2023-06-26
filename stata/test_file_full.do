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

  safe_setup "`working_folder'" null test_results suppress
		
  use "`working_folder'\test_data", clear

  * Example 1: create some table outputs using named sheets, allowing for combinations of if, by and weights 
		*************************************************************************************************************

  safe table year survivor if year>2013, contents(freq mean inc_activity sd inc_activity) output_sheet("activity") suppress
  safe table year survivor if year>2013, contents(freq mean inc_activity max inc_activity) output_sheet("max_w_sup") suppress
  safe table year survivor if year>2013, contents(freq mean inc_activity max inc_activity) output_sheet("max_no_sup") nosuppress
		sort grant_type
  by grant_type: safe table year survivor if year>2013, contents(freq mean inc_activity max inc_activity) output_sheet("act_by") suppress exception("It's not feaible to identify the charities from this information")
		sort grant_type
  by grant_type: safe table year survivor if year>2013 [pweight=wgt], contents(freq mean inc_activity max inc_activity) output_sheet("act_by_wgt") suppress
		sort grant_type
  by grant_type: safe tab year survivor, chi gamma output_sheet("small_act") suppress exception("I don't think it's feasible to identify the charities from this information")
		
  * Example 2: showing how you can ue macros to switch safe checking on and off easily
  ************************************************************************************
		* switch the 'if' to 1 or 0 to swap between safe and regular output
  local do_safe = ""
  local options = ""
  if 1 {
		  local do_safe = "safe"
				local options = `" nosuppress exception("trust me, I'm a professor")"'
		}
				
		* note tha here we are using hte automatic sheet naming option - we haven't specified sheet names
		sort grant_type
		by grant_type: `do_safe' tab year survivor , chi2 expected
		`do_safe' table year survivor , by(grant_type) `options'
		`do_safe' table year survivor , by(grant_type) `options'
		
		* Example 3: running various sorts of regression/estimation model
		******************************************************************

  safe regress inc_activity inc_grants inc_donations total_costs
	 safe probit survivor inc_activity inc_grants inc_donations total_costs
		tsset index year
	 safe xtreg inc_activity inc_grants inc_donations total_costs , re 		
		
		* these illustrate how 'by' estimation appears as a separate estimate on each sheet, indexed A, B,...
		sort grant_type
	 by grant_type: safe regress inc_activity inc_grants inc_donations total_costs
		* and this illustrates how a model can fail (in this case, not enough observations to satisfy the d.o.f. requirement
		sort grant_type
	 by grant_type: safe regress inc_activity inc_grants inc_donations total_costs if year>2013


  * Example 4: graphs - these are alwys set for 'review'
		**************************************************************************
		safe twoway (scatter inc_grants inc_activity) , output_sheet("graph_test")
  safe twoway (scatter inc_grants inc_activity) , by(grant_type) output_sheet("by_graph_test")
	
		safe_finalise
		
		log close
}
   
