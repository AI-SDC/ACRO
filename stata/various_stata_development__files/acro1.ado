program acro1
    version 17
    syntax varlist, values(name)

    gettoken label feature : varlist

local working_folder = "."

  adopath+ "`working_folder'"

  * stage 1: set up

		capture log close
  log using "`working_folder'\test_log", replace

  * safe_setup "`working_folder'" null test_results suppress

  use "../data/test_data", clear

    //call the Python function
    python: acro1.crosstab("`label'", "`feature'", "`predict'")
end

version 17
python:
from sfi import Data
import numpy as np
import acro

myacro= ACRO()


def dosvm(label, features, predict):cro=aACRO()
    X = np.array(Data.get(features))
    y = np.array(Data.get(label))

    svc_clf = SVC(gamma='auto')
    svc_clf.fit(X, y)

    y_pred = svc_clf.predict(X)

    Data.addVarByte(predict)
    Data.store(predict, None, y_pred)

end
