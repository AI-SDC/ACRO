adopath +"."

use "../data/test_data", clear
describe
display `"calling table survivor grant_type directly"'
table survivor grant_type

display `" Creating acro session"'
acro init

display `"now calling: acro table survivor grant_type"'
acro table survivor grant_type

display `" list the session contents"'
acro print_outputs

display `" end the session"'
acro finalise
