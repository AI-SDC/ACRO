use http://www.stata-press.com/data/r17/iris, clear

describe

mysvm iris seplen sepwid petlen petwid, predict(irispr)

label variable irispr predicted

label values irispr species

tabulate iris irispr, row
