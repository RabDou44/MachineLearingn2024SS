from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline, make_pipeline
import numpy as np 
import pandas as pd
import copy
import time 

from sklearn.model_selection import train_test_split, cross_validate
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def get_pipeline(feature_structure, clf = RandomForestClassifier()):

    """
    Returns a pipeline that preprocesses the data and then applies the classifier.
    Parameters
    -----------
    feature_structure: dict
        A dictionary containing the feature structure of the data. The keys are 'bin', 'cat', 'cont', 'ord', and 'target'.
    clf: sklearn classifier
        The classifier to use in the pipeline.
    TODO: write  check for feature_structure` and `clf` types
    """
    categorical_preprocessor = Pipeline(
        steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])

    numerical_preprocessor = Pipeline([
        ("imputation_mean", SimpleImputer(missing_values=np.nan, strategy="mean")),
        ('scaler', StandardScaler())
    ])  

    preprocessor = ColumnTransformer([
        ('categorical', categorical_preprocessor, feature_structure['cat']),
        ('numerical', numerical_preprocessor, feature_structure['cont'])
    ])

    return Pipeline(steps=[('preprocessor', preprocessor), ('classifier', clf)])


def evaluate_models(data, feature_structure, classifiers):

    """
    Builds a model using the pipeline and returns it
    with split data and specified parameters 

    Parameters
    -----------
    data: pandas DataFrame
        The data to use for training and testing the model.
    feature_structure: dict
        A dictionary containing the feature structure of the data. The keys are 'bin', 'cat', 'cont', 'ord', and 'target'.
    classifiers: list of sklearn to eveluate (with set parameters)
    
    Keyword arguments:
    argument -- description
    Return: return_description
    """

    feature_columns = feature_structure['bin'] + feature_structure['cat'] + feature_structure['cont'] + feature_structure['ord']
    X = data[feature_columns]
    y = data[feature_structure['target']]
    
    results = {}

    for clf in classifiers:
        model_holdout = get_pipeline(feature_structure, clf)
        model_cv = copy.deepcopy( model_holdout)

        # Holdout
        res_holdout, model_holdout = perform_holdout(X, y, model_holdout)

        # Cross-validation
        res_cv, model_cv = perform_cv(X, y, model_cv)

        results = append_results(results, model_holdout, model_cv, res_holdout, res_cv)
    
    return pd.DataFrame(results)

def append_results(results, model_holdout, model_cv, res_holdout, res_cv):
    """
    Appends the results of the holdout and cross-validation to the results dictionary.

    Parameters
    -----------
    results: dict
        The dictionary containing the results.
    model_holdout: sklearn pipeline
        The pipeline used for the holdout evaluation.
    model_cv: sklearn pipeline
        The pipeline used for the cross-validation evaluation.
    res_holdout: dict
        The results of the holdout evaluation.
    res_cv: dict
        The results of the cross-validation evaluation.
    """
    model_cv_name = str(model_cv.steps[1][1]) + "_CV"
    model_holdout_name = str(model_holdout.steps[1][1]) + "_Holdout"

    if results:
        results["model"] += [model_holdout_name, model_cv_name]
        for key in res_holdout.keys():
            results[key] += [res_holdout[key], res_cv[key]]
    else:
        results = {
            "model": [model_holdout_name, model_cv_name],
            "accuracy": [res_holdout["accuracy"], res_cv["accuracy"]],
            "precision": [res_holdout["precision"], res_cv["precision"]],
            "recall": [res_holdout["recall"], res_cv["recall"]],
            "f1-score": [res_holdout["f1-score"], res_cv["f1-score"]],
            "timing": [res_holdout["timing"], res_cv["timing"]]
        }
    return results


def perform_holdout(X, y, clf, random_state=42):
    """
    Builds a model using the pipeline and returns it
    with split data and specified parameters 

    Parameters
    -----------
    X: pandas DataFrame
        The data to use for training and testing the model.
    y: pandas Series
        The target variable.
    clf: sklearn classifier
        The classifier to use in the pipeline.
    random_state: int
        The random state to suse for the train-test split.

    
    Keyword arguments:
    argument -- description
    Return: return a tuple of performance metrics and the model
    """

    model_holdout = clf
    trainX, testX, trainY, testY = train_test_split(X, y, test_size=0.2, random_state=random_state)
    start_time = time.time()
    model_holdout.fit( trainX, trainY)
    pred_y  = model_holdout.predict(testX)
    fitting_time = time.time() - start_time

    results = {"accuracy":accuracy_score(testY, pred_y),  
             "precision": precision_score(testY, pred_y, average="weighted"), 
            "recall":recall_score(testY, pred_y,average="weighted"), 
            "f1-score": f1_score(testY, pred_y, average="weighted"), 
            "timing": fitting_time}

    return results, model_holdout

def perform_cv(X, y, clf): 
    """
    Builds a model using the pipeline and returns it
    with split data and specified parameters 

    Parameters
    -----------
    X: pandas DataFrame
        The data to use for training and testing the model.
    y: pandas Series
        The target variable.
    clf: sklearn classifier
        The classifier to use in the pipeline.
    
    Keyword arguments:
    argument -- description
    Return: return a tuple of performance metrics and the model
    """

    model_cv = clf
    start_time = time.time()
    cv_results = cross_validate(model_cv, X, y, cv=5, scoring=["accuracy", "precision_weighted", "recall_weighted", "f1_weighted"], verbose=1, return_estimator=True)
    whole_time = time.time() - start_time
    res = {"accuracy": np.nanmean(cv_results["test_accuracy"])
           , "precision": np.nanmean(cv_results["test_precision_weighted"]),
           "recall": np.nanmean(cv_results["test_recall_weighted"]),
           "f1-score": np.nanmean(cv_results["test_f1_weighted"]),
              "timing": whole_time}
    best_estimator = cv_results["estimator"][np.argmax(cv_results["test_accuracy"])]

    return (res, best_estimator) 