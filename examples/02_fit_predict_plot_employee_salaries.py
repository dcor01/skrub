"""
Predicting the salary of employees
==================================

The `employee salaries <https://catalog.data.gov/dataset/employee-salaries-2016>`_
dataset contains information
about annual salaries (year 2016) for more than 9,000 employees of the 
Montgomery County (Maryland, US). In this example, we are interested
in predicting the column *Current Annual Salary*
depending on a mix of clean columns and a dirty column.
We choose to benchmark different categorical encodings for
the dirty column *Employee Position Title*, that contains
dirty categorical data.

"""

################################################################################
# Data Importing and preprocessing
# --------------------------------
#
# We first download the dataset:
from dirty_cat.datasets import fetch_employee_salaries
employee_salaries = fetch_employee_salaries()
print(employee_salaries['DESCR'])


################################################################################
# Then we load it:
import pandas as pd
df = employee_salaries['data']

################################################################################
# Now, let's carry out some basic preprocessing:
df['Date First Hired'] = pd.to_datetime(df['date_first_hired'])
df['Year First Hired'] = df['Date First Hired'].apply(lambda x: x.year)
# drop rows with NaN in gender
df.dropna(subset=['gender'], inplace=True)

target_column = 'Current Annual Salary'
y = df[target_column].values.ravel()

#########################################################################
# Choosing columns
# -----------------
# For categorical columns that are supposed to be clean, it is "safe" to
# use one hot encoding to transform them:

clean_columns = {
    'gender': 'one-hot',
    'department_name': 'one-hot',
    'assignment_category': 'one-hot',
    'Year First Hired': 'numerical'}

#########################################################################
# We then choose the categorical encoding methods we want to benchmark
# and the dirty categorical variable:

encoding_methods = ['one-hot', 'target', 'similarity', 'minhash',
                    'gap']
dirty_column = 'employee_position_title'
#########################################################################


#########################################################################
# Creating a learning pipeline
# ----------------------------
# The encoders for both clean and dirty data are first imported:

from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import OneHotEncoder
from dirty_cat import SimilarityEncoder, TargetEncoder, MinHashEncoder,\
    GapEncoder

encoders_dict = {
    'one-hot': OneHotEncoder(handle_unknown='ignore', sparse=False),
    'similarity': SimilarityEncoder(similarity='ngram'),
    'target': TargetEncoder(handle_unknown='ignore'),
    'minhash': MinHashEncoder(n_components=100),
    'gap': GapEncoder(n_components=100),
    'numerical': FunctionTransformer(None)}

# We then create a function that takes one key of our ``encoders_dict``,
# returns a pipeline object with the associated encoder,
# as well as a gradient-boosting regressor

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


def make_pipeline(encoding_method):
    # static transformers from the other columns
    transformers = [(enc + '_' + col, encoders_dict[enc], [col])
                    for col, enc in clean_columns.items()]
    # adding the encoded column
    transformers += [(encoding_method, encoders_dict[encoding_method],
                      [dirty_column])]
    pipeline = Pipeline([
        # Use ColumnTransformer to combine the features
        ('union', ColumnTransformer(
            transformers=transformers,
            remainder='drop')),
        ('clf', HistGradientBoostingRegressor())
    ])
    return pipeline


#########################################################################
# Fitting each encoding methods with a RidgeCV
# --------------------------------------------
# Eventually, we loop over the different encoding methods,
# instantiate each time a new pipeline, fit it
# and store the returned cross-validation score:

# explicitly require this experimental feature
from sklearn.experimental import enable_hist_gradient_boosting  # noqa
# now you can import normally from ensemble
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score
import numpy as np

all_scores = dict()

cv = KFold(n_splits=5, random_state=12, shuffle=True)
scoring = 'r2'
for method in encoding_methods:
    pipeline = make_pipeline(method)
    scores = cross_val_score(pipeline, df, y, cv=cv, scoring=scoring)
    print('{} encoding'.format(method))
    print('{} score:  mean: {:.3f}; std: {:.3f}\n'.format(
        scoring, np.mean(scores), np.std(scores)))
    all_scores[method] = scores

#########################################################################
# Plotting the results
# --------------------
# Finally, we plot the scores on a boxplot:
# We notice that the MinHashEncoder does not performs as well compared to 
# other encoding methods.
# There are two reasons for that: the MinHashEncoder performs better
# with tree-based models than linear models (
# :ref:`see example 03<sphx_glr_auto_examples_03_fit_predict_plot_midwest_survey.py>`)
# , and also
# increasing `n_components` improves performances. `n_components` around 300 
# tend to lead to good prediction performance, but with more computational
# cost.

import seaborn
import matplotlib.pyplot as plt
plt.figure(figsize=(4, 3))
ax = seaborn.boxplot(data=pd.DataFrame(all_scores), orient='h')
plt.ylabel('Encoding', size=20)
plt.xlabel('Prediction accuracy     ', size=20)
plt.yticks(size=20)
plt.tight_layout()



