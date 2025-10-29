quietly{
adopath +"."
*** version 19
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
noisily display `"************ Tables with hierarchical rows -both ways of specifying    ************"'
noisily display `"calling table finance housing parents"'
noisily table finance housing parents
noisily display `""'
noisily display `"now calling: acro table finance housing parents"'
noisily acro table finance housing parents

noisily display `""'
noisily display `""'

noisily display `"calling table (finance housing) parents"'
noisily table (finance housing) parents
noisily display `""'
noisily display `"now calling: acro table finance housing parents"'
noisily acro table (finance housing) parents

noisily display `""'
noisily display `""'

**** complex tabulation
noisily display `"************ Tables with hierarchical columns - both ways of specifying    ************"'
noisily display `"calling table finance housing parents, statistic(mean children) statistic(sd children)"'
noisily table finance housing parents, statistic(mean children) statistic(sd children)
noisily display `""'
noisily display `"now calling: acro table finance housing parents, statistic(mean children) statistic(sd children)"'
noisily acro table finance housing parents, statistic(mean children) statistic(sd children)

noisily display `""'
noisily display `""'

noisily display `"calling table finance (housing parents), statistic(mean children) statistic(sd children)"'
noisily table finance (housing parents), statistic(mean children) statistic(sd children)
noisily display `""'
noisily display `"now calling: acro table finance (housing parents), statistic(mean children) statistic(sd children)"'
noisily acro table finance (housing parents), statistic(mean children) statistic(sd children)

noisily display `""'
noisily display `""'


quit


noisily display `"***********  table  with if statements *************
noisily display `"calling  table housing finance without exclusion"'
noisily table housing finance
noisily display `"calling  table housing finance if (children == 4)"'
noisily table housing finance if (children==4)
noisily display `""'
noisily acro table housing finance if (children==4)









noisily display `""'
noisily display `""'
noisily display `"***********   Regressions  *******************************"'
noisily display `" create integer version of recommend via : encode recommend, gen(recommend_n)"'

encode recommend, gen(recommend_n)
** linear
noisily display `""'
noisily display `" ***** stata:  regress recommend_n children"'
noisily regress recommend_n children

noisily display `""'
noisily display `"acro : regress recommend_n children"'
noisily acro regress recommend_n children

noisily display `""'
noisily display `""'
noisily display `" *********list the session contents using :acro print_outputs *****"'
noisily acro print_outputs


noisily display `""'
noisily display `" ************* end the session : acro finalise.   *******"'
noisily acro finalise


}
