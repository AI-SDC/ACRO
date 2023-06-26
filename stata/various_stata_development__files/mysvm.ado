program mysvm
    version 17
    syntax varlist, predict(name)

    gettoken label feature : varlist

    //call the Python function
    python: dosvm("`label'", "`feature'", "`predict'")
end

version 17
python:
from sfi import Data, SFIToolkit
import numpy as np
from sklearn.svm import SVC

def dosvm(label, features, predict):
    X = np.array(Data.get(features))
    y = np.array(Data.get(label))
    
    svc_clf = SVC(gamma='auto')
    svc_clf.fit(X, y)
    theline = f'python got this for features {features}'
    with open ("svm_ado_out.txt",mode="a") as f:
        f.write(theline)
    SFIToolkit.displayln("output file created")    
    y_pred = svc_clf.predict(X)
    SFIToolkit.displayln("model run")
    Data.addVarByte(predict)
    Data.store(predict, None, y_pred)

end
