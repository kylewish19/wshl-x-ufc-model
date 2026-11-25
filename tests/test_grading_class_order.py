import numpy as np
import pytest
from sklearn.metrics import log_loss
from wshlx_ufc.grading import grade_multiclass

def test_explicit_method_order():
    classes=["KO","SUB","DEC"]
    y=["SUB","KO","DEC","SUB"]
    p=np.array([[.1,.8,.1],[.7,.15,.15],[.1,.1,.8],[.6,.2,.2]])
    expected=-np.log([.8,.7,.8,.2]).mean()
    g=grade_multiclass(y,p,classes)
    assert g.logloss==pytest.approx(expected)
    assert g.accuracy==.75 and g.class_recall["SUB"]==.5
    order=[2,0,1]
    ordered=grade_multiclass(y,p[:,order],[classes[i] for i in order])
    assert ordered.logloss==pytest.approx(g.logloss)
    assert ordered.brier==pytest.approx(g.brier)
    assert ordered.logloss==pytest.approx(log_loss(y,p[:,order],labels=["DEC","KO","SUB"]))
def test_six_state_unsorted_and_missing_class():
    c=["A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC"]
    p=np.array([[.6,.1,.1,.1,.05,.05],[.05,.05,.1,.1,.1,.6]])
    assert grade_multiclass(["A_KO","B_DEC"],p,c).logloss==pytest.approx(-np.log(.6))
def test_zero_probabilities_and_invalid_classes():
    g=grade_multiclass(["SUB"],np.array([[1.,0.,0.]]),["KO","SUB","DEC"])
    assert np.isfinite(g.logloss) and g.logloss>30
    with pytest.raises(ValueError):grade_multiclass(["SUB"],np.array([[1.,0.,0.]]),["KO","KO","DEC"])
    with pytest.raises(ValueError):grade_multiclass(["UNKNOWN"],np.array([[1.,0.,0.]]),["KO","SUB","DEC"])
