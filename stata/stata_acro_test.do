quietly{
adopath +"."

version 16
use "../data/test_data", clear


** start the session ******
noisily display `"***********************************************"'
noisily display `" Creating acro session"'
noisily acro init

noisily display `""'

**** basic tabulation
noisily display `"************ Tables      ************"'
noisily display `"calling table survivor grant_type directly"'
noisily table survivor grant_type
noisily display `""'
noisily display `"now calling: acro table survivor grant_type"'
noisily acro table survivor grant_type

noisily display `""'

**** complex tabulation
noisily display `"************ Tables with hierarchical rows     ************"'
noisily display `"calling table year grant_type, by(survivor)"'
noisily table year grant_type, by(survivor)
noisily display `""'
noisily display `"now calling: acro table year grant_type, by(survivor)"'
noisily acro table year grant_type, by(survivor)

noisily display `""'
noisily display `""'

**** complex tabulation
noisily display `"************ Tables with hierarchical columns     ************"'
noisily display `"calling table year survivor grant_type, contents(count inc_grants sd inc_grants)"'
noisily table year survivor grant_type, contents(count inc_grants sd inc_grants)
noisily display `""'
noisily display `"now calling: acro table year survivor grant_type, contents(count inc_grants sd inc_grants)"'
noisily acro table year survivor grant_type, contents(count inc_grants sd inc_grants)

noisily display `""'
noisily display `""'
**** tabulation with contents
* acro table year survivor if year>2013, contents(freq mean inc_activity sd inc_activity)

noisily display `""'
noisily display `""'
noisily display `"***********   Regressions  *******************************"'
** linear
noisily display `""'
noisily display `" ***** stata:  regress inc_activity inc_grants inc_donations total_costs"'
noisily regress inc_activity inc_grants inc_donations total_costs

noisily display `""'
noisily display `"acro : acro regress inc_activity inc_grants inc_donations total_costs"'
noisily acro regress inc_activity inc_grants inc_donations total_costs


noisily display `""'
noisily display `""'
** probit
noisily display`"**** stata: probit survivor inc_activity inc_grants inc_donations total_costs "'
noisily probit survivor inc_activity inc_grants inc_donations total_costs
noisily display `""'
noisily display `""'
noisily display `"** acro: acro probit survivor inc_activity inc_grants inc_donations total_costs "'
noisily acro probit survivor inc_activity inc_grants inc_donations total_costs

noisily display `""'
noisily display `""'
**logit
tsset index year
*acro xtreg inc_activity inc_grants inc_donations total_costs , re

*display `"now calling: acro table survivor grant_type if year>2013"'
*acro table survivor grant_type if year>2013



noisily display `""'
noisily display `""'
noisily display `" *********list the session contents using :acro print_outputs *****"'
noisily acro print_outputs


noisily display `""'
noisily display `" ************* end the session : acro finalise.   *******"'
noisily acro finalise


}
