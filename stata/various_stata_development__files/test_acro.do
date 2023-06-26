adopath +"."

use "../data/test_data", clear
describe
display `"calling acro_crosstab with no params"'
* acro_crosstab
display `"now with just varlist"'
* acro_crosstab survivor grant_type
display `"now with params"'
acro_crosstab survivor grant_type if year>2013, contents(mean inc_activity)
