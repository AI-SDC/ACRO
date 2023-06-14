adopath +"."

use "../data/test_data", clear
describe
display `"calling table survivor grant_type directly"'
table survivor grant_type

display `"now calling with table survivor grant_type"'
acro table survivor grant_type
