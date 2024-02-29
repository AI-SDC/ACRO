quietly{
adopath +"."

version 16
use "../data/nursery_dataset", clear


** start the session ******
noisily display `"***********************************************"'
noisily display `" Creating acro session"'
noisily acro init

noisily display `""'

**** basic tabulation
noisily display `"************ Tables      ************"'
noisily display `"calling table finance parents directly"'
noisily table finance parents
noisily display `""'
noisily display `"now calling: acro table finance parents"'
noisily acro table finance parents

noisily display `""'

**** complex tabulation
noisily display `"************ Tables with hierarchical rows     ************"'
noisily display `"calling table finance housing parents, by(social)"'
noisily table finance housing parents, by(social)
noisily display `""'
noisily display `"now calling: acro table finance housing parents, by(social)"'
noisily acro table finance housing parents, by(social)

noisily display `""'
noisily display `""'

**** complex tabulation
noisily display `"************ Tables with hierarchical columns     ************"'
noisily display `"calling table finance housing parents, contents(mean children sd children)"'
noisily table finance housing parents, contents(mean children sd children)
noisily display `""'
noisily display `"now calling: acro table finance housing parents, contents(mean children sd children)"'
noisily acro table finance housing parents, contents(mean children sd children)

noisily display `""'
noisily display `""'

**** tabulation with contents
* acro table year survivor if year>2013, contents(freq mean inc_activity sd inc_activity)

noisily display `""'
noisily display `""'
noisily display `"***********   Regressions  *******************************"'
** linear
noisily display `""'
noisily display `" ***** stata:  recommend children"'
noisily regress recommend children

noisily display `""'
noisily display `"acro : recommend children"'
noisily acro regress recommend children

noisily display `""'
noisily display `""'
noisily display `" *********list the session contents using :acro print_outputs *****"'
noisily acro print_outputs


noisily display `""'
noisily display `" ************* end the session : acro finalise.   *******"'
noisily acro finalise


}
