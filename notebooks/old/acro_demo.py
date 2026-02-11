"""
ACRO Tests.

Copyright : Maha Albashir, Richard Preen, Jim Smith 2023.
"""

# import libraries
import os

import pandas as pd
from scipy.io.arff import loadarff

from acro import ACRO

# Instantiate ACRO by making an acro object
print(
    "\n Creating an acro object().\n"
    "The TRE's risk appetite is read from default.yml\n"
    "and shown to the researcher and output checker"
)
acro = ACRO(suppress=False)

# Load test data
# The dataset used in this notebook is the nursery dataset from OpenML.
# - In this version, the data can be read directly from the local machine after
#   it has been downloaded.
# - The code below reads the data from a folder called "data" which we assume
#   is at the same level as the folder where you are working.
# - The path might need to be changed if the data has been downloaded and stored elsewhere.
#   - for example use:
#     path = os.path.join("data", "nursery.arff")
#     if the data is in a sub-folder of your work folder

path = os.path.join("../data", "nursery.arff")
data = loadarff(path)
df = pd.DataFrame(data[0])
df = df.select_dtypes([object])
df = df.stack().str.decode("utf-8").unstack()
df.rename(columns={"class": "recommend"}, inplace=True)
df.head()

# Examples of producing tabular output
# We rely on the industry-standard package **pandas** for tabulating data.
# In the next few examples we show:
# - first, how a researcher would normally make a call in pandas, saving the
#   results in a variable that they can view on screen (or save to file?)
# - then how the call is identical in SACRO, except that:
#   - "pd" is replaced by "acro"
#   - the researcher immediately sees a copy of what the TRE output checker will see.

print(
    "\nThese examples show acro wrappers around "
    " standard tabulation routines from the pandas package."
)


# Pandas crosstab
# This is an example of crosstab using pandas.
# We first make the call, then the second line print the outputs to screen.

print("\nCalling crosstab of recommendation by parents using pandas")
table = pd.crosstab(df.recommend, df.parents)
print(table)

# ACRO crosstab
# - This is an example of crosstab using ACRO.
# - The INFO lines show the researcher what will be reported to the output checkers.
# - Then the (suppressed as necessary) table is shown via the print command as before.

print("\nNow the same crosstab call using the ACRO interface")
safe_table = acro.crosstab(df.recommend, df.parents)
print("\nand this is the researchers output")
print(safe_table)

# ACRO crosstab with suppression
# - This is an example of crosstab with suppressing the cells that violate the
#   disclosure tests.
# - Note that you need to change the value of the suppress variable in the acro
#   object to True. Then run the crosstab command.
# - If you wish to continue the research while suppressing the outputs, leave
#   the suppress variable as it is, otherwise turn it off.

print("\nTurn on the suppression variable")
acro.suppress = True
print("\nNow the same crosstab call using the ACRO interface")
safe_table = acro.crosstab(df.recommend, df.parents)
print("\nand this is the researchers output with suppression")
print(safe_table)
print("\nNow turn off the suppression variable")
acro.suppress = False

# ACRO functionality to let users manage their outputs
#
# 1: List current ACRO outputs
# This is an example of using the print_output function to list all the outputs
# created so far

print("\nNow illustrating how users can manage their outputs")
print(
    "\nStart by listing the outputs in the acro memory."
    "For each output the key line is the one starting 'Summary'"
)
acro.print_outputs()

# 2: Remove some ACRO outputs before finalising
# This is an example of deleting some of the ACRO outputs.
# The name of the output that needs to be removed should be passed to the
# function remove_output.
# - The output name can be taken from the outputs listed by the print_outputs function,
# - or by listing the results and choosing the specific output that needs to be removed

print("\nNow removing the first output")
acro.remove_output("output_0")

# 3: Rename ACRO outputs before finalising
# This is an example of renaming the outputs to provide a more descriptive name.

print("\nUsers can rename output files to something more informative")
acro.rename_output("output_1", "cross_tabulation")

# 4: Add a comment to output
# This is an example to add a comment to outputs.
# It can be used to provide a description or to pass additional information to
# the output checkers.

print("\nUsers can add comments which the output checkers will see.")
acro.add_comments("cross_tabulation", "Please let me have this data.")

# 5: (the big one) Finalise ACRO
# This is an example of the function _finalise()_ which the users must call at
# the end of each session.
# - It takes each output and saves it to a CSV file.
# - It also saves the SDC analysis for each output to a json file or Excel file
#   (depending on the extension of the name of the file provided as an input to the function)

print(
    "\nUsers MUST call finalise to send their outputs to the checkers"
    " If they don't, the SDC analysis, and their outputs, are lost."
)
output = acro.finalise("Examples", "json")
