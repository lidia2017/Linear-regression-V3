# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 23:24:11 2021

@author: lghosh
"""

# modelop.schema.0: input_schema.avsc
# modelop.schema.1: output_schema.avsc

import pandas as pd
import numpy as np
from scipy.special import logit
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.linear_model import LinearRegression
from aequitas.preprocessing import preprocess_input_df
from aequitas.group import Group
from aequitas.bias import Bias
from scipy.stats import binom_test
from scipy.stats import kstest
from scipy.stats import ttest_1samp
from scipy.stats import ks_2samp
import shap
import pickle


#modelop.init
def begin():
    global explainer, lr_model, features, train, numerical_features
    train = pd.read_csv('training_data.csv')
    numerical_features = train.select_dtypes(['int64', 'float64']).columns
    model_artifacts = pickle.load(open('Regression_Model_v3.pkl', 'rb'))
    explainer = model_artifacts['explainer']
    lr_model = model_artifacts['reg_model']
    features = model_artifacts['features']
    pass

#modelop.score
def action(datum):
    datum = pd.DataFrame(datum, index=[0])
    #prep_datum = preprocess(datum)
    #datum = pd.concat([datum, prep_datum], axis=1)
    datum['prediction'] = prediction(datum)
    yield datum.loc[:, ['id', 'prediction']] \
            .to_dict(orient='records')[0]
'''
def preprocess(data):
    prep_data = pd.DataFrame(index=data.index)
    prep_data["logit_int_rate"] = data.int_rate.apply(logit)
    prep_data["log_annual_inc"] = data.annual_inc.apply(np.log)
    prep_data["log_credit_age"] = data.credit_age.apply(np.log)
    prep_data["log_loan_amnt"] = data.loan_amnt.apply(np.log)
    prep_data["rent_indicator"] = data.home_ownership.isin(['RENT']).astype(int)
    return prep_data
'''

def prediction(data):
    return lr_model.predict_proba(data.loc[:, features])[:,1]

#modelop.metrics
def metrics(data):
    metrics = {}
    '''
    prep_data = preprocess(data)
    data = pd.concat([data, prep_data], axis=1)
    data.loc[:, 'probabilities'] = prediction(data)
    data.loc[:, 'predictions'] = data.probabilities \
                                     .apply(lambda x: threshold > x) \
                                     .astype(int)
    '''
    ks_tests = [ks_2samp(train.loc[:, feat], data.loc[:, feat]) \
                for feat in numerical_features]
    pvalues = [x[1] for x in ks_tests]
    list_of_pval = [f"{feat}_p-value" for feat in numerical_features]
    ks_pvalues = dict(zip(list_of_pval, pvalues))
    
    adjusted_predictions = data['predicted_price']
    actuals = data['price']
    mse = mean_squared_error(adjusted_predictions, actuals)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(adjusted_predictions, actuals)
    metrics['shap'] = get_shap_values(data)
    metrics['MSE'] = mse
    metrics['RMSE'] = rmse
    metrics['MAE'] = mae
    metrics['drift_metrics'] = ks_pvalues
    yield metrics
    
'''
       f1 = f1_score(data.loan_status, data.predictions)
       cm = confusion_matrix(data.loan_status, data.predictions)
       labels = ['Fully Paid', 'Charged Off']
       cm = matrix_to_dicts(cm, labels)
       fpr, tpr, thres = roc_curve(data.loan_status, data.probabilities)
       auc_val = roc_auc_score(data.loan_status, data.probabilities)
       rc = [{'fpr': x[0], 'tpr': x[1]} for x in list(zip(fpr, tpr))]
       metrics['f1_score'] = f1
       metrics['confusion_matrix'] = cm
       metrics['auc'] = auc_val
       metrics['ROC'] = rc
       metrics['bias'] = get_bias_metrics(data)

       metrics['drift_metrics'] = get_drift_metrics(data)
     '''
   

'''
def is_validated(data):
    return ('loan_status' in data.columns)
'''

'''
def get_bias_metrics(data):
    bias = Bias()
    group = Group()
    old_columns = ['predictions', 'loan_status', 'forty_plus_indicator']
    new_columns = ['score', 'label_value', 'forty_plus_indicator']
    scored_data = data.loc[:, old_columns]
    renamer = dict(zip(scored_data.columns, new_columns))
    scored_data = scored_data.rename(columns = renamer)

    data_processed, _ = preprocess_input_df(scored_data)
    xtab, _ = group.get_crosstabs(data_processed)
    attribute_columns = ['attribute_name', 'attribute_value']
    absolute_metrics = group.list_absolute_metrics(xtab)
    absolute_metrics_df = xtab[attribute_columns + absolute_metrics].round(2)
    bias_df = bias.get_disparity_predefined_groups(
        xtab,
        original_df=data_processed,
        ref_groups_dict={'forty_plus_indicator': 'Under Forty'},
        alpha=0.05, mask_significance=True
    )
    calculated_disparities = bias.list_disparities(bias_df)
    disparity_metrics_df = bias_df[attribute_columns + calculated_disparities]
    abs_metrics = absolute_metrics_df.where(pd.notnull(absolute_metrics_df),
                                            None).to_dict(orient='records')
    disp_metrics = disparity_metrics_df.where(pd.notnull(disparity_metrics_df),
                                            None).to_dict(orient='records')
    return dict(absolute_metrics = abs_metrics,
                disparity_metrics = disp_metrics)
'''

def get_shap_values(data):
    shap_values = explainer.shap_values(data.loc[:, features])
    shap_values = np.mean(abs(shap_values), axis=0).tolist()
    shap_values = dict(zip(features, shap_values))
    sorted_shap_values = {k: v for k, v in sorted(shap_values.items(),
                                                  key=lambda x: x[1])}
    return sorted_shap_values

'''
def get_drift_metrics(data):
    num_of_renters = data.rent_indicator.sum()
    size_of_sample = data.shape[0]
    rent_feat_binom_pvalue = binom_test(x=num_of_renters, 
                                        n=size_of_sample, 
                                        p=rent_ratio)

    logit_int_rate_pvalue = ttest_1samp(a=data.logit_int_rate,
                                        popmean=logit_int_rate_mean)[1]
    pred_log_probs = lr_model.predict_log_proba(X=data.loc[:, features])[:, 1]
    neg_log_probs = -1*pred_log_probs
    output_logprob_pvalue = kstest(neg_log_probs, 
                                   'gamma', 
                                   args=gamma_args)[1]
    drift_metrics = dict(renters_binom_pvalue=rent_feat_binom_pvalue,
                         output_logprob_pvalue=output_logprob_pvalue,
                        logit_int_rate_ttest_pvalue=logit_int_rate_pvalue)
                
    return drift_metrics


def matrix_to_dicts(matrix, labels):
    cm = []
    for idx, label in enumerate(labels):
        cm.append(dict(zip(labels, matrix[idx, :].tolist())))
    return cm
'''