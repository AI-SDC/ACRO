capture program drop engage
program engage
  di "" 
  di as err "==press <return> to continue==" _request(dummy)
  di ""
end



************************************************************
* Simple introduction to using acro for Stata researchers. *
*                                                          * 
* Author: Jim Smith. 2026                                  * 
************************************************************

quietly {
noisily display  " {title:ACRO demonstration}"

noisily display as txt "This is a simple do-file to get you started with using the {bf:{it:acro}} package to add disclosure risk control  to your analysis."
noisily display as txt"This is an interactive demonstration, so occasionally you will be prompted to hit <return> to either:" 
noisily display as txt " - display the next piece of  information or " 
noisily display as txt " - run the next code snippet."
noisily display "" 



noisily display as err "{bf:In displaying some of the examples below we have used the terms 'dollar' 'backtick_' and '_tick'}"
noisily display as err " You will need to replace them with the appropriate symbols in your actual code" 

noisily engage 


noisily display  " {title:A: The basic concepts}"

noisily display "" 

noisily display as text   "{bf:1 A research {it:session}:}"
noisily display as text   "by which we mean the activity of running a series of commands (interactively or via a script) that:"
 noisily display as text  " -  ingest some data,"
 noisily display as text  " -  manipulate it, and then"
 noisily display as text  " -  produce (and store) some outputs."
noisily display "" 

noisily display as text  "{bf:2 Types of commands:}"
noisily display as text  "Whether interactive, or just running a final script, we can think of the commands that get run in a session as dividing into:"
 noisily display as text  " - {it:manipulation} commands that load and transform data into the shape you want"
 noisily display as text  " - {it:feedback} commands that report on your data - but are never intended to be exported."
 noisily display as text  "   - in Stata these might use the variables window, or the {it:display} command"
 noisily display as text  " - {it:query} commands that produce an output from your data (table/plot/regression model etc.) "
 noisily display as text  "     that you might want to export from the Trusted Research Environment (TRE)"
noisily display "" 


 noisily display as text  " {bf:3 Risk Assessment vs decision making:}"
 noisily display as text  " SACRO stands for Semi-Automated Checking of Research Outputs."
 noisily display as text  " The prefix 'Semi' is important here - because in a principles-based system humans should make {it:decisions} about output requests. "
 noisily display as text  " To help with that we provide the SACRO-Viewer, which collates all the relevant information for them."
noisily display "" 

noisily display as text  " A key part of that information is the  {it:Risk Assessment}."
 noisily display as text  " - Since it involves calculating metrics and comparing them to thresholds (the TRE's risk appetite)"
 noisily display as text  "    it can be done automatically, at the time an output query runs on the data."
 noisily display as text  " - This is what the ACRO tool does when you use it as part of your workflow."
noisily display "" 

noisily engage

noisily display as text  " {bf:4 What ACRO does}"
noisily display as text  " The ACRO package aims to support you in producing {it:Safe Outputs} within minimal changes to your work flow."
noisily display as text  " To do that we provide:"
noisily display as text  " - drop-in replacements for the most commonly used {it:output commands},"
noisily display as text  "   - keeping the same syntax as the originals, and"
noisily display as text  "   - supporting as many of the options as we can"
noisily display as txt "       (features supported will increase over time in response to demand)."
noisily display as text  " - a set of {it:session-management} commands to help you manage the set of files you request for output."
noisily display as text  "{bf:Important to note} that currently acro outputs results (tables, details of regression models etc.) as {it:.csv} files. "
noisily display as text  "   - In other words we separate the processes of {it:creating} outputs - which must be done {it:inside} the TRE."
noisily display as text  "     from the process of {it:formatting} them for publication - which can be done {it:outside} the TRE with your preferred toolchain."
noisily display as text  "   - ACRO handles creation. We are interested in hearing from researchers whether it is important to support them with formatting."

noisily display ""
 
 noisily display as text "{bf: 5 What ACRO doesn't support (yet)}"
 noisily display as text  " - Weightings as an option when creating tables/regressions"
 noisily display as text  "   We would greatly appreciate input on which versions peope use most" 
 noisily display as text  "   so we can plan their implementation"  
 noisily display as text  " - Abbreviations/synonyms e.g. {cmd:reg} for {cmd:regress} etc." 
 noisily display as text  "   this would make a nice (and easy) job for someone who wanted to get involved supporting this initiative!"
 noisily display as text  " - Statements that combined manipulation and query commands, for example,"
 noisily display as text  "   {it: xi: regress wage i.year age}"
 noisily display as text  "   {bf:Workaround} You can achieve this by creating the dummy variables {bf:before} calling your query command:"
 noisily display as text  "   {it: xi year}"
 noisily display as text  "   {it: regress wage  backtick_ds _I*_tick age} "
 noisily display as text  "   NB: ACRO needs to be passed an explicit list of independent variables rather than Stata's i.year shortcut" 
 noisily display as text  "   The easiest way to avoid listing the indicator variables manually is to use the macro ds_I* as shown"
 noisily display as text  "     - Stata will expand this automatically before it gets passed to acro"
 noisily display as text  "   See that Stata manual https://www.stata.com/manuals15/rxi.pdf for further discussion"
 
 
 noisily engage
   
 

noisily display as text "{title:B Getting Started with the demonstration}"

noisily display as text ""

noisily display as text "{bf:Step 1: Setting up the environment with the tools we will use}"

noisily display as text "The acro package should be installed in your system"
noisily display as text " and you will just need to tell Stata where to find the {it:acro.ado} file that handles the interaction between Stata and the back-end Python package".
noisily display as text "Depending on how {it:acro} has been set up for you, this may be installed system-wide, or you may need to have it in your working directory "
noisily display as text `"{cmd:adopath + "."}"'

adopath +"."

noisily display as text "We will also set the version of Stata to use version 18  - feel free to edit this file and change this"
noisily display as text "{cmd:version 18}"

noisily version 18

noisily display as text ""

noisily display as text "{title:Step 2 Starting an ACRO session}"

noisily display as text " To do this we create an acro object by running the command below."
noisily display as text ""
noisily display as text `"{cmd:acro init, config(default) }"'
noisily display as text `"{cmd:acro disable_suppression }"'
noisily display as txt ""


noisily display as text " You can leave out the default parameters, but this example  shows how you can:"
noisily display as text " - provide the name of a {it:config} (risk appetite) file the TRE may have asked you to use"
noisily display as text " - turn automatic suppression on or off right from the start of your session"
noisily display as text ""
noisily display as text " Note that when the cell runs it should report (in a different coloured font/background)"
noisily display as text " - what version of acro is running: {bf:this should be 0.4.12}"
noisily display as text " - the TRE's risk appetite: that defines the rules your outputs will be checked against."
noisily display as text " - whether suppression is automatically applied to disclosive outputs."

noisily display as text ""


noisily acro init, config(default) 
noisily acro disable_suppression

noisily display as text ""
noisily display as text ""


noisily display as text "{title: Step 3: Loading some test data}"

noisily display as text ""
noisily display as text " The following stages in this step just do standard ingestion and manipulation commands to load some data into Stata ready to be queried."
noisily display as text " We will use some open-source data about nursery admissions."
noisily display as text ""
noisily display as text " {bf:There is no change to your workflow here}"
noisily display as text " - Do whatever you want in this step!"
noisily display as text " - We just assume you end up with your data in Stata."

noisily display as text `"{cmd:use "../data/nursery_data" }"'

noisily use "../data/nursery_dataset", clear

noisily engage

noisily display as text ""

noisily display as text "{title:C Producing tables that are 'Safe Outputs}"

noisily display as text " {bf:{it:acro}} aims to reproduce the functionality of the Stata {bf:table} command by mapping it across to the equivalent crosstab() command provided by the industry-standard Python package {it:Pandas}."

noisily display as text "{bf:Important to note} the syntax remains the same as in Stata, just with the prefix {bf:acro} - except for two differences:"
noisily display as text "1. We do not currently support the weights options "
noisily display as text "   - we need more input from researchers about how much of a priority these are,"
noisily display as text "    especially as the functionality can be recreated by creating extra variables in Stata."
noisily display as text "2. We do not support abbreviations (creating a lookup table for this would be a nice first issue if someone wanted to contribute)."
noisily display as text ""

noisily display as text "The code should automatically accomodate the syntax from Stata versions <=16 and 17+" 
noisily display as text "  - in the examples below we will show the syntax from versions 17 and beyond,"
noisily display as text " So the syntax is {bf: acro table  rowvars colvars [if] [in]  [, *]}"
noisily display as text ""

noisily display as text "and you can specify what the table cells contain by:"
noisily display as text "    - providing a statistic - for example: mean, count, std deviation, median etc."
noisily display as text "    - specifying what variable to report on"

noisily display as text " The acro version uses Stata functionality to interact with python, and all the pandas code."
noisily display as text " - but it adds extra code that checks for disclosure risks depending on the statistic you ask for."
noisily display as text ""

noisily engage


noisily display as text "{title:Example 1 A simple 2-D table of frequencies stratified by two variables}"


noisily display as text "{cmd:acro table recommend parents}"
noisily display ""

noisily acro table recommend parents

noisily engage

noisily display as text "{bf:How to understand this output}"
noisily display as text " The top part (in red font) is the risk analysis produced by acro."
noisily display as text " It is telling us that:"
noisily display as text " - the overall summary is {bf:fail} because 4 cells are failing the 'minimum threshold' check"
noisily display as text " - then it is showing which cells failed so you can choose how to respond"
noisily display as text " - finally it is telling us that is has saved the table and risk assessment to our acro session with id 'output_0'"
noisily display as text ""
noisily display as text " The part below is the normal output produced by python mimicking the the Stata {bf:table} function."
noisily display as text " - As this is such a small table it is not hard to spot the four problematic cells with zero or low counts"
noisily display as text " - but of course this might be harder for a bigger table."
noisily display as text ""

noisily display as text "{bf:How to respond to this input}"
noisily display as text "There are basically three choices:"
noisily display as text "1. We might decide these low numbers reveal something where the public interest outweighs the disclosure risk."
noisily display as text "Rather than being a strict rules-based system, acro lets you attach an 'exception request' to a named output, to send a message to the output checkers."
noisily display as text "For example, you could type:"
noisily display as text `"  {cmd:acro add_exception "output_0" "I think you should let me have this because..."}"'
noisily display as text ""

noisily display as text "2. We redesign our data so that table so that none of the cells in the resulting table represent fewer than {it:n} people (10 for the default risk appetite)"
noisily display as text "For example, we could recode {it:'very_recommend'} and {it:'priority'} into one label."
noisily display as text "But maybe it is revealing that the {it:'recommend'} value is not used?"
noisily display as text ""

noisily display as text "3. We can redact the disclosive cells - and {bf:acro will do this for us}."
noisily display as text "We simply enable the option to suppress disclosive cells and re-run the query."
noisily display as text ""
noisily display as text "The command below shows option 3."
noisily display as text "When you run the cell below you should see that:"
noisily display as text " - the status now changes to {it:review} (so the output-checker knows what has been applied)"
noisily display as text " - the code automatically adds an exception request saying that suppression has been applied"
noisily display as text " - and, most importantly,  the cells are redacted."

noisily display as text `"{cmd:acro enable_suppression }"'
noisily display as text `"{cmd:acro table recommend parents }"'


noisily engage



noisily acro enable_suppression
noisily display ""
noisily acro table recommend parents


noisily display as text "{title: An example of a more complex table}"

noisily display as text " Just to demonstrate  the sort of tables that can be made, make something more complex."
noisily display as text `"{cmd:acro enable_suppression }"'

noisily display as text `"{cmd:acro  table (parents finance) recommend, statistic(mean children) statistic (mode children) margins('total')}"'
noisily display as text ""

noisily display as text " Going through the parameters in order:"
noisily display as text " - passing a list of variable names to 'rowvars'  (rather than a single variable/column name) tells it we want a hierarchy within the rows."
noisily display as text "   - we can do the same to columns as well (or instead) if we want to"
noisily display as text " - the two {bf:statistic()} options specify reporting the  mean  (which introduces additional risks of {it:dominance})and mode  of the number of children"
noisily display as text "   We are aware of (and working on) some rare issues when reporting standard devistions in a suppressed table"
noisily display as text " - setting {cmd:margins(total)} tells it to display row and column sub-totals"
noisily display as text ""
noisily display as text " It's worth noting that including the totals there are  6 columns in the risk assessment and 5 in the suppressed table."
noisily display as text " This is because after suppression has replaced numbers with 'NaN', pandas removes the fully suppressed column ('recommend') from the table."
noisily display as text ""
noisily display as text "{bf: This highlights a wider issue about Stata's inconsistent treatment of missing values}"
noisily display as text "For reasons best known to itself, Stata sometimes (but not always) interprets missing numerical values as {bf:extremely high numbers}"
noisily display as text "    so in one example we saw recently it reported a lot of people aged 250 years and above ..."
noisily display as text "By contrast Pandas removes records with missing values if needed, whis is more sane"
noisily display as text " {bf: You can replicate Stata's behaviour} by explicitly mapping missing values (represented as .) to a suitably high number"

noisily display as text ""

noisily engage

noisily acro enable_suppression

noisily acro table (parents finance) recommend, statistic(mean children) statistic (mode children) margins('total')

noisily engage


noisily display as text " {title:D What other sorts of analysis does ACRO currently support?}"

noisily display as text " We are continually adding support for more types of analysis as users prioritise them."
noisily display as text ""
noisily display as text " ACRO currently supports:"
noisily display as text " - {bf:Tables} via {cmd:acro table ...} as described above."
noisily display as text "    - supported statistics are:  {it:mean, median, sum, std, count, mode}."
noisily display as text " - {bf:Regression}  via:  {cmd:acro regress...}, {cmd:acro logit ...} and {cmd:acro probit ...} using standard Stata syntax"
noisily display as text ""
noisily display as text "We are aware that"
noisily display as text "-  the python and R 'front-ends' to acro support more types of analysis,"
noisily display as text "-  that some Stata users would like acro to support weighted analysis."
noisily display as text "We welcome feedback, and suggestions for the next prioritise the development team."
noisily display as text "Offers to contribute code are especially welcome!"
noisily display as text "There is more help on how to use all of these available from the {it:acro cheat sheet} or (if have have internet access) from www.sacro-tools.org"

noisily engage 

noisily display as text ""

noisily display as text "{title: E ACRO functionality to let users manage their outputs}"

noisily display as text ""

noisily display as text " As explained above, you need to create an {it:acro session} whenever your code is run."
noisily display as text ""
noisily display as text " After that, every time you run an acro {it:query} command both the output and the risk assessment are saved as part of the acro session."
noisily display as text ""
noisily display as text " But we recognise that:"
noisily display as text " - You may not want to request release of all your outputs - for example, the first table we produced above."
noisily display as text " - It is  good practice to provide a more informative name than just {it:output_n} for the .csv files that acro produces"
noisily display as text " - It helps the output checker if you provide some comments saying what the outputs are."
noisily display as text " - You might want to add more things to the bundles of files you want to take out, such as:"
noisily display as text "    - outputs from analyses that acro doesn't currently support"
noisily display as text "    - your code itself (which many journals want)"
noisily display as text "    - maybe a version of your paper in pdf/word format etc."
noisily display as text ""
noisily display as text " Therefore acro provides the following commands for  'session management'"


noisily display as text ""

noisily display as text "{bf: 1 Listing the  current contents of an  ACRO session}"
noisily display as text " This output is not beautiful (there's a GUI come soon) but should let you identify outputs you want to rename,comment on, or delete"
noisily display as text "{cmd:acro print_outputs}"
noisily engage


noisily acro print_outputs

noisily engage

noisily display as text "{bf:2 Remove some ACRO outputs before finalising}"
noisily display as text " At the start of this demo we made a disclosive output -it's the first one with status {it:fail}."
noisily display as text ""
noisily display as text " We don't want to waste the output checker's time so lets remove it."
noisily display as text `"{cmd:acro remove_output "output_0"}"'


acro remove_output "output_0"

noisily engage



noisily display as text "{bf: 3 Rename ACRO outputs before finalising}"
noisily display as text " This is an example of renaming the outputs to provide  more descriptive names."
noisily display as text `"{cmd:rename_output output_1 "crosstab_recommendation_vs_parents"}"'
noisily display as text `"{cmd:rename_output output_2 "mean_children_by_parents_finance_recommendation"}"'


noisily acro rename_output output_1 "crosstab_recommendation_vs_parents"
noisily acro rename_output output_2 "mean_children_by_parents_finance_recommendation"

noisily engage

noisily display as text "{bf: 4 Add a comment to output}"
noisily display as text " This is an example of adding a comment to outputs.
noisily display as text " It can be used to provide a description or to pass additional information to the TRE staff."
noisily display as text " They will see it alongside your file in the output checking viewer - rather than having it in an email somewhere.

noisily display as text ""
noisily display as text `"{cmd:acro add_comments "mean_children_by_parents_finance_recommendation" "too few cases of recommend to report"}"'

noisily acro add_comments "mean_children_by_parents_finance_recommendation" "too few cases of recommend to report"


noisily engage 

noisily display as text "{bf: 5. Request an exception}"
noisily display as text " An example of providing a reason why an exception should be made"

noisily display as text `"e.g.: {cmd:acro add_exception "output_n" "This is evidence of systematic bias"}"'

noisily engage 
noisily display as text "{bf: 6 Adding a custom output.}"

noisily display as text " As mentioned above you might want to request release of all sorts of things"
noisily display as text " - including your code,"
noisily display as text " - or outputs from analyses *acro* doesn't support (yet)"
noisily display as text "'
noisily display as text " In ACRO we can add a file to our session with a comment describing what it is."
noisily display as text `"{cmd:acro custom_output "acro_demo_2026.do" "this is the code that produced this session"}"'

noisily acro custom_output "acro_demo_2026.do" "This is the code that produced this session"

noisily engage


noisily display as text " {title:F Finishing your session and producing a folder of files to release.}"

noisily display as text " This is an example of the function {bf:finalise()} which the users must call at the end of each session."
noisily display as text " - It takes each output and saves it to a CSV file (or the original file type for custom outputs)"
noisily display as text " - It also saves the SDC analysis for each output to a json file."
noisily display as text " - It adds checksums for everything - so we know they've not been edited."
noisily display as text " - It puts them all in a folder with the name you supply."
noisily display as text ""
noisily display as text " {bf:ACRO will not overwrite previous sessions}"
noisily display as text ""
noisily display as text " So every time you call finalise on a session you need to either:"
noisily display as text "   - delete the previous folder (by adding Stata commands to remove), or"
noisily display as text "   - provide a new folder name manually, or"
noisily display as text " - create a const (e.g. macro) programmatically to hold the folder name"

noisily display ""
noisily display as text "The code snippet below shows how to add the current time and date to a folder name."
noisily display as text "Please remember the comments above about substituting symbols for dollar backtick_ and _tick"


noisily local suffix = subinstr("$S_DATE", " ", "_", .) + "_" + subinstr("$S_TIME",":","_",.)
noisily display as txt `"{cmd:local suffix = subinstr("dollarS_DATE", " ", "_", .) + "_" + subinstr("dollarS_TIME",":","_",.)}"'

noisily local myfoldername= "my_acro_outputs_v1_" + "`suffix'"
noisily display as text `"{cmd:local myfoldername= "my_acro_outputs_v1_" + "backtick_suffix_tick"}"'

noisily display as text `"{cmd:acro finalise "backtick_myfoldername_tick"}"'

noisily acro finalise "`myfoldername'"
}



