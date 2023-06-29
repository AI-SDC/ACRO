capture program drop acro2
program  acro2, rclass
 syntax anything [if] [in] [fweight  aweight  pweight  iweight] [, *]
  display `"here"'
  display `" anything is `anything'"'
  tokenize `anything'
  local command `1'
  macro shift
  local rest `*'
  display `" command is |`command'| newvarlist is |`rest'|"'
  display `" if is  `if'"'
  display `" in is `in'"'
  display `" weights are: `fweight', `aweight', `pweight', `iweight' "'
  display `" exp is `exp'"'
  display `"options is `options'"'
  python: acrohandler2("`command'", "`rest'","`if'","`exp'","`weights'","`options'")
  python: simple()
end

python:

def simple():
	pass

def acrohandler2(command, varlist,exclusion,exp,weights,options):
	print( 'in python acrohandler function: ',
			f'command = {command}',
			f'varlist={varlist}',
			f'if = {exclusion}',
			f'exp = {exp}',
			f'weights={weights}',
			f'options={options}'
		)
end
