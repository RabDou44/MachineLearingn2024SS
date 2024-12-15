from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, RobustScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline, make_pipeline
import numpy as np 
import pandas as pd
import copy
import time 

from random_forest import RandomForest

from sklearn.model_selection import train_test_split, cross_validate
from sklearn.metrics import mean_squared_error


def get_pipeline(feature_structure, clf = RandomForest()):

    """
    Returns a pipeline that preprocesses the data and then applies the classifier.
    Parameters
    -----------
    feature_structure: dict
        A dictionary containing the feature structure of the data. The keys are 'bin', 'cat', 'cont', 'ord', and 'target'.
    clf: sklearn classifier
        The classifier to use in the pipeline.
    """
    if not isinstance(feature_structure, dict):
        raise TypeError("feature_structure should be a dictionary")

    required_keys = {'bin', 'cat', 'cont', 'ord', 'target'}
    if not required_keys.issubset(feature_structure.keys()):
        raise ValueError(f"feature_structure must contain the keys: {required_keys}")

    if not isinstance(clf, BaseEstimator):
        raise TypeError("clf should be an instance of a scikit-learn classifier")

    categorical_preprocessor = Pipeline(
        steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])

    numerical_preprocessor = Pipeline([
        ("imputation_mean", SimpleImputer(missing_values=np.nan, strategy="mean")),
        ('scaler', RobustScaler())
    ])  

    ordinal_preprocessor = Pipeline([
        ("ordinal", OrdinalEncoder()),
    ])

    preprocessor = ColumnTransformer([
        ('categorical', categorical_preprocessor, feature_structure['cat']),
        ('numerical', numerical_preprocessor, feature_structure['cont']),
        ('ordinal', ordinal_preprocessor, feature_structure['ord'])
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
        model_cv = get_pipeline(feature_structure, clf)
        
        # Cross-validation
        res_cv, model_cv = perform_cv(X, y, model_cv)
        
        results = append_results(results, model_cv, res_cv)
    
    return pd.DataFrame(results)

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
    cv_results = cross_validate(model_cv, X, y, cv=5, scoring=["neg_mean_squared_error","r2"], verbose=1, return_estimator=True)
    whole_time = time.time() - start_time
    res = {"mse": -np.nanmean(cv_results["test_neg_mean_squared_error"]),
           "r2": np.nanmean(cv_results["test_r2"]),
            "timing": whole_time}
    best_estimator = cv_results["estimator"][np.argmax(cv_results["test_neg_mean_squared_error"])]
    print(res)
    return (res, best_estimator) 


def append_results(results, model, res_model):
    """
    Appends the results of the cross-validation to the results dictionary.

    Parameters
    -----------
    results: dict
        The dictionary containing the results.
    model: sklearn pipeline
        The pipeline used for modelling .
    res_model: dict
        The results of the model evaluation.
    """
    model_cv_name = str(model.steps[1][1]) + "_CV"

    if results:
        results["model"] += [model_cv_name]
        for key in res_model.keys():
            results[key] += [res_model[key]]
    else:
        results = {
            "model": [ model_cv_name],
            "mse": [res_model["mse"]],
            "r2": [res_model["r2"]],
            "timing": [res_model["timing"]]
        }
    return results


# TODO: Adapt to regression if it is worth the effort
import re

def beautify_name(name):
    if name.startswith("SVC"):
        match = re.search(r'kernel=\'([a-zA-Z0-9_]+)\'', name)
        return f"SVC {match.group(1)}" if match else "SVC rbf"
    if name.startswith("KNeighbors"):
        match = re.search(r'n_neighbors=(\d+)', name)
        return f"k={match.group(1)}" if match else "k=5"
    return f"depth={re.search(r'max_depth=(\d+)', name).group(1)}"
            
def results_to_latex(results, caption, label):
    holdout, cv = results.iloc[::2, :], results.iloc[1::2, :]
    data = {}
    for i in range(0, 2*len(holdout), 2):
        instance_name = beautify_name(holdout.at[i, "model"])
        
        for col in holdout.columns[1:]:
            if col + " holdout" not in data:
                data[col + " holdout"] = {}
                data[col + " cv"] = {}
            data[col + " holdout"][instance_name] = holdout.at[i, col]
            data[col + " cv"][instance_name] = cv.at[i+1, col]
            
    df = pd.DataFrame(data)
    columns = []
    for col in df.columns:
        split = col.split(" ")
        config, metric = split[0], split[1]
        columns.append((config, metric))

    df.columns = pd.MultiIndex.from_tuples(columns, names=['Splitting', 'Metric'])
    latex = df.to_latex(float_format="%.3f")
    latex = latex.replace("lrrrrrrrrrr", "|l|rr|rr|rr|rr|rr|")
    latex = latex.replace("{r}", "{c|}")
    latex = latex.replace("Splitting", "")
    latex = latex.replace("Metric", "Parameters")
    latex = latex.replace("midrule", "hline")
    latex = "\\begin{table}[H]\n\\centering\n\\resizebox{0.8\\textwidth}{!}{\n" + latex + "}\n\\caption{" + caption + "}\n\\label{tab:" + label + "}\n\\end{table}"

    return latex