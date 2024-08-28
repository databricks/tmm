# Databricks notebook source
# MAGIC %md
# MAGIC #### Step 0: Start Compute  
# MAGIC Top right -> Connect -> ML-Compute-#######

# COMMAND ----------

# MAGIC %md
# MAGIC # Welcome to the Databricks ML Workshop!
# MAGIC #### Today we're going to cover some key areas on how you do machine learning while on the lakehouse.
# MAGIC
# MAGIC We'll be using some financial data and putting ourselves in the shoes of a data scientist/ML engineer to see what 
# MAGIC tools are available to use within the lakehouse and how they all tie together.  
# MAGIC
# MAGIC Some highlights that we'll hit:
# MAGIC
# MAGIC #### Data Prep and DataOps
# MAGIC * Read/Write with Delta
# MAGIC * Bounce between SQL and Python
# MAGIC * Visualizations
# MAGIC * Saving to Feature Store
# MAGIC #### Experimentation and ModelOps
# MAGIC * Set up MLflow experiment
# MAGIC * Run experiment and train model
# MAGIC * Browse results
# MAGIC * Register Model
# MAGIC * AutoML
# MAGIC * Explore MLflow Model Registry
# MAGIC #### Deployment and DevOps
# MAGIC * Model Registry
# MAGIC * Batch Inference
# MAGIC * Model Serving

# COMMAND ----------

# MAGIC %pip install databricks-feature-engineering
# MAGIC
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

#Lets set up the user specific prefixes

#Ideally we'd be using a Unity Catalog here - but for workshop purposes we'll use the default catalog
#If you run this notebook on UC, you can simply point to your catalog here
catalog = "_demo_catalog"
dbutils.widgets.text("catalog", catalog)

#This is just getting the user ID for the workshop so everyone is split
user_id = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
user_id = ''.join(filter(str.isdigit, user_id))

#schema_name = 'user' + user_id
schema_name = 'staging'
dbutils.widgets.text("schema_name", schema_name)

# COMMAND ----------

# MAGIC %sql
# MAGIC --To ensure everyone in the workshop has a good experience, we'll break everyone into their own schema
# MAGIC --If this errors, please go to the above cell and change "schema_name" then rerun
# MAGIC CREATE SCHEMA ${catalog}.${schema_name}

# COMMAND ----------

# MAGIC %md
# MAGIC ### Data Prep and DataOps
# MAGIC Our example dataset exists on our workspace already as a directory of parquet files.  
# MAGIC In practice, we could be looking at ingest from any number of locations, such as a Delta Live Table, but this was chosen for simplicity 

# COMMAND ----------

# MAGIC %md
# MAGIC #### Uncomment this to load data into a new UC volume
# MAGIC !cp -r /databricks-datasets/samples/lending_club/ /Volumes/_demo_catalog/staging/demo_volume/

# COMMAND ----------

#load in the loan data from the parquet dir 
loan = spark.read.parquet('/Volumes/_demo_catalog/staging/demo_volume/lending_club/parquet')

#then save it as a delta table for future use
loan.write.format("delta").mode("overwrite").saveAsTable(f"{catalog}.{schema_name}.loan_data")

# COMMAND ----------

#we can do spark queries for some very basic exploration
data = spark.table(f"{catalog}.{schema_name}.loan_data").limit(1000000)
display(data)

#but if we're writing SQL, we can do better

# COMMAND ----------

# MAGIC %sql
# MAGIC Select * from ${catalog}.${schema_name}.loan_data limit 1000

# COMMAND ----------

# MAGIC %md
# MAGIC What if I want to explore my data via a UI?

# COMMAND ----------

pip install bamboolib

# COMMAND ----------

import bamboolib as bam
#Jump into bamboolib and explore the dataframe
df_explore = spark.table(f"{catalog}.{schema_name}.loan_data").limit(1000000).toPandas()
df_explore

# COMMAND ----------

import pandas as pd; import numpy as np
# Reload data
df_explore = spark.table(f"{catalog}.{schema_name}.loan_data").limit(1000000).toPandas()
# Step: Drop columns with missing values
df_explore = df_explore.dropna(how='all', axis=1)
# Step: Group by addr_state and calculate new column(s)
df_annual_income = df_explore.groupby(['addr_state']).agg(annual_inc_mean=('annual_inc', 'mean')).reset_index()

# COMMAND ----------

#Lets take our data and visualize it inline
display(df_annual_income)

# COMMAND ----------

# MAGIC %md
# MAGIC #### Now lets take our loan data and set up an example problem to solve
# MAGIC Since we have a large dataset lets focus the problem down to a specific ask.  
# MAGIC Can we reasonably estimate, given the provided data, a specific loan's status?  
# MAGIC
# MAGIC We're going to define an account that has been 'charged_off' - in which the creditor has stopped trying to collect debts from an account as a 'bad_loan'

# COMMAND ----------

# MAGIC %md
# MAGIC #### Let's use this data to populate our Feature Store
# MAGIC
# MAGIC For others, including our future selves, to be able to make use of these features and better track lineage, let's put our newly created features into the feature store.

# COMMAND ----------

# MAGIC %sql
# MAGIC Drop table if exists ${catalog}.${schema_name}.loan_features;
# MAGIC Create table ${catalog}.${schema_name}.loan_features
# MAGIC AS /*Copy data from existing_table and cast columns to original's data type*/
# MAGIC SELECT 
# MAGIC     MONOTONICALLY_INCREASING_ID() AS id, /*add new column with unique increasing id*/
# MAGIC     CASE 
# MAGIC         WHEN loan_status in ("Default", "Charged Off")
# MAGIC         THEN 'true' 
# MAGIC         WHEN loan_status in ("Fully Paid")
# MAGIC         THEN 'false'
# MAGIC         END AS bad_loan,
# MAGIC     CAST(num_rev_accts as INT) as num_rev_accts, 
# MAGIC     CAST(annual_inc as DOUBLE) as annual_inc, 
# MAGIC     CAST(inq_last_12m as INT) as inq_last_12m, 
# MAGIC     CAST(total_il_high_credit_limit as DOUBLE) as total_il_high_credit_limit, 
# MAGIC     CAST(grade as STRING) as grade, 
# MAGIC     CAST(last_pymnt_amnt as DOUBLE) as last_pymnt_amnt, 
# MAGIC     CAST(total_rec_int as DOUBLE) as total_rec_int, 
# MAGIC     CAST(recoveries as DOUBLE) as recoveries 
# MAGIC from ${catalog}.${schema_name}.loan_data 
# MAGIC where loan_status in ("Default", "Charged Off","Fully Paid")
# MAGIC   and num_rev_accts IS NOT NULL 
# MAGIC   AND annual_inc IS NOT NULL
# MAGIC   AND inq_last_12m IS NOT NULL 
# MAGIC   AND total_il_high_credit_limit IS NOT NULL 
# MAGIC   AND grade IS NOT NULL 
# MAGIC   AND last_pymnt_amnt IS NOT NULL 
# MAGIC   AND total_rec_int IS NOT NULL 
# MAGIC   AND recoveries IS NOT NULL;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE ${catalog}.${schema_name}.loan_features ALTER COLUMN id SET NOT NULL

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE ${catalog}.${schema_name}.loan_features ADD CONSTRAINT pk_loan_features PRIMARY KEY(id)

# COMMAND ----------

#Re-load the full dataset from our delta table
df = spark.table(f"{catalog}.{schema_name}.loan_data").limit(1000000)

#Create new feature "bad_loan" representing accounts that have been charged off
loan_stats_df = df.filter(df.loan_status.isin(["Default", "Charged Off", "Fully Paid"])).withColumn("bad_loan",(df.loan_status == "Charged Off").cast("string"))
loan_stats_df = loan_stats_df.toPandas()

#Remove null data
loan_stats_df = loan_stats_df.dropna(how='all', axis=1)

#Create unique key 
loan_stats_df['id'] = loan_stats_df.index

display(loan_stats_df)

# COMMAND ----------

from databricks.feature_engineering import FeatureEngineeringClient

fe = FeatureEngineeringClient()

try:
  #drop table if exists
  fe.drop_table(f"{catalog}.{schema_name}.loan_features")
except:
  pass

#Need to make this a spark dataframe
#loan_stats_df = spark.createDataFrame(loan_stats_df)

loan_feature_table = fe.create_table(
  name=f"{catalog}.{schema_name}.loan_features",
  primary_keys="id",
  schema=loan_stats_df.schema,
  description='Feature table for loan data related to lending club dataset'
)

#actually write the table to the feature store
fe.write_table(df=loan_stats_df, name=f"{catalog}.{schema_name}.loan_features", mode='merge')

# COMMAND ----------

# MAGIC %md
# MAGIC #### Lets go look at the Feature Store in the sidebar to see where our table ended up

# COMMAND ----------

# MAGIC %md
# MAGIC ### Experimentation and ModelOps
# MAGIC Now that we've done some data exploration and we've extracted our features into the feature store, lets do something with them.
# MAGIC
# MAGIC We have data and a goal, can we classify these loans?

# COMMAND ----------

#first lets build a simple dataset that brings in our loans that we want to categorize
#since we're building the training dataset, we're assuming the outcome exists here as well (bad_loan)

loan_ids = spark.sql(f"select id, bad_loan from {catalog}.{schema_name}.loan_features")
display(loan_ids)

# COMMAND ----------

# MAGIC %md
# MAGIC Now that we have the loans we want to use for our training dataset, lets go grab the corresponding features from our feature store

# COMMAND ----------

import mlflow
from databricks.feature_store import FeatureLookup
from mlflow.tracking import MlflowClient
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup

fe = FeatureEngineeringClient()

# Assigning our target column/features to make changing them easier in the long term

# Picked a couple features that to an untrained financial eye might work. This is not to de-value feature engineering as it is often a very important and time consuming process.
selected_features = ["num_rev_accts","annual_inc","inq_last_12m","total_il_high_credit_limit","grade","last_pymnt_amnt","total_rec_int","recoveries"]
target_col = "bad_loan"

# Here we're doing some feature lookups by providing the loan id as well as the features we'd like to use
feature_lookups = [
    FeatureLookup(
      table_name = f"{catalog}.{schema_name}.loan_features",
      feature_names = selected_features,
      lookup_key = 'id'
    )
  ]

# Create a training set using training DataFrame and features from Feature Store
# The training DataFrame must contain all lookup keys from the set of feature lookups,
# in this case 'id'. It must also contain all labels used
# for training, in this case 'bad_loan' which is our target_col.
training_set = fe.create_training_set(
  df=loan_ids,
  feature_lookups = feature_lookups,
  label = target_col
)

# Load our training set into a dataframe
df_cleaned = training_set.load_df().toPandas()

# COMMAND ----------

# Take a look at the data 
df_cleaned

# COMMAND ----------

# MAGIC %md
# MAGIC Now that our data looks ready to go, lets use a popular library to train a classifier and see if we can create a model with just a few inputs that can reliably estimate if a loan's status is bad.  
# MAGIC
# MAGIC For this example, we're going to use LightGBM. LightGBM is a gradient boosting framework that uses tree based learning algorithms. It is one of many, many approaches/methods one could use to train a model with this data and we use it here simply as an example. 
# MAGIC

# COMMAND ----------

import lightgbm
from lightgbm import LGBMClassifier
help(LGBMClassifier)
# Tip: Hide result on the top right menu will let you tuck these results away without deleting the cell

# COMMAND ----------

# MAGIC %md
# MAGIC First off we take our data and split into test, training, and validation sets

# COMMAND ----------

from sklearn.model_selection import train_test_split

X = df_cleaned.drop(target_col, axis=1)
y = df_cleaned[target_col]

X_train, X_rem, y_train, y_rem = train_test_split(X,y, train_size=0.8)
X_val, X_test, y_val, y_test = train_test_split(X_rem,y_rem, test_size=0.5)

# COMMAND ----------

# MAGIC %md
# MAGIC Pipeline creation for numerical values. Lets you define what to do for numerical values generally as well if imputed values if values are missing

# COMMAND ----------

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

num_imputers = []
num_imputers.append(("impute_mean", SimpleImputer(), ["num_rev_accts","annual_inc","inq_last_12m","total_il_high_credit_limit","last_pymnt_amnt","total_rec_int","recoveries"]))

numerical_pipeline = Pipeline(steps=[
    ("converter", FunctionTransformer(lambda df: df.apply(pd.to_numeric, errors="coerce"))),
    ("imputers", ColumnTransformer(num_imputers)),
    ("standardizer", StandardScaler()),
])

numerical_transformers = [("numerical", numerical_pipeline, ["num_rev_accts","annual_inc","inq_last_12m","total_il_high_credit_limit","last_pymnt_amnt","total_rec_int","recoveries"])]

# COMMAND ----------

# MAGIC %md
# MAGIC Pipeline creation for categorical values. Lets us apply one hot encoding to turn our categorical values into useful values for training our model.

# COMMAND ----------

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

one_hot_imputers = []

one_hot_pipeline = Pipeline(steps=[
    ("imputers", ColumnTransformer(one_hot_imputers, remainder="passthrough")),
    ("one_hot_encoder", OneHotEncoder(handle_unknown="ignore")),
])

categorical_one_hot_transformers = [("onehot", one_hot_pipeline, ["grade"])]

# COMMAND ----------

# MAGIC %md
# MAGIC Bring pipelines together and define the preprocessor

# COMMAND ----------

from sklearn.compose import ColumnTransformer

transformers =  numerical_transformers + categorical_one_hot_transformers 

preprocessor = ColumnTransformer(transformers, remainder="passthrough", sparse_threshold=1)

# COMMAND ----------

# MAGIC %md
# MAGIC Define the model training code and log it within an mlflow run. More specifics in comments.

# COMMAND ----------

import mlflow
from mlflow.models import Model, infer_signature, ModelSignature
from mlflow.pyfunc import PyFuncModel
from mlflow import pyfunc
import sklearn
from sklearn import set_config
from sklearn.pipeline import Pipeline

from hyperopt import hp, tpe, fmin, STATUS_OK, Trials

# Create a separate pipeline to transform the validation dataset. This is used for early stopping.
mlflow.sklearn.autolog(disable=True)
pipeline_val = Pipeline([
    ("preprocessor", preprocessor)
])
pipeline_val.fit(X_train, y_train)
X_val_processed = pipeline_val.transform(X_val)

def objective(params):
  with mlflow.start_run(run_name="lightgbm") as mlflow_run:
    lgbmc_classifier = LGBMClassifier(**params)

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", lgbmc_classifier),
    ])

    # Enable automatic logging of input samples, metrics, parameters, and models
    mlflow.sklearn.autolog(
        log_input_examples=True,
        silent=True)

    model.fit(X_train, y_train, classifier__callbacks=[lightgbm.early_stopping(5), lightgbm.log_evaluation(0)], classifier__eval_set=[(X_val_processed,y_val)])
    
    # Log metrics for the training set
    mlflow_model = Model()
    pyfunc.add_to_model(mlflow_model, loader_module="mlflow.sklearn")
    pyfunc_model = PyFuncModel(model_meta=mlflow_model, model_impl=model)
    training_eval_result = mlflow.evaluate(
        model=pyfunc_model,
        data=X_train.assign(**{str(target_col):y_train}),
        targets=target_col,
        model_type="classifier",
        evaluator_config = {"log_model_explainability": False,
                            "metric_prefix": "training_" , "pos_label": "true" }
    )
    skdtc_training_metrics = training_eval_result.metrics
    # Log metrics for the validation set
    val_eval_result = mlflow.evaluate(
        model=pyfunc_model,
        data=X_val.assign(**{str(target_col):y_val}),
        targets=target_col,
        model_type="classifier",
        evaluator_config = {"log_model_explainability": False,
                            "metric_prefix": "val_" , "pos_label": "true" }
    )
    skdtc_val_metrics = val_eval_result.metrics
    # Log metrics for the test set
    test_eval_result = mlflow.evaluate(
        model=pyfunc_model,
        data=X_test.assign(**{str(target_col):y_test}),
        targets=target_col,
        model_type="classifier",
        evaluator_config = {"log_model_explainability": False,
                            "metric_prefix": "test_" , "pos_label": "true" }
    )
    skdtc_test_metrics = test_eval_result.metrics

    loss = -skdtc_val_metrics["val_f1_score"]

    # Truncate metric key names so they can be displayed together
    skdtc_val_metrics = {k.replace("val_", ""): v for k, v in skdtc_val_metrics.items()}
    skdtc_test_metrics = {k.replace("test_", ""): v for k, v in skdtc_test_metrics.items()}

    return {
      "loss": loss,
      "status": STATUS_OK,
      "val_metrics": skdtc_val_metrics,
      "test_metrics": skdtc_test_metrics,
      "model": model,
      "run": mlflow_run,
    }

# COMMAND ----------

# MAGIC %md
# MAGIC Hyperparameter space for tweaking.

# COMMAND ----------

space = {
  "colsample_bytree": 0.7979588834646815,
  "lambda_l1": 5.306329351338439,
  "lambda_l2": 0.11832169194981441,
  "learning_rate": 0.12138700420184056,
  "max_bin": 120,
  "max_depth": 15,
  "min_child_samples": 341,
  "n_estimators": 301,
  "num_leaves": 5,
  "path_smooth": 32.45970837009079,
  "subsample": 0.5624796079129128,
  "random_state": 259237676,
}

# COMMAND ----------

# MAGIC %md
# MAGIC Run the trials!

# COMMAND ----------

trials = Trials()
fmin(objective,
     space=space,
     algo=tpe.suggest,
     max_evals=1,  # Increase this when widening the hyperparameter search space.
     trials=trials)

best_result = trials.best_trial["result"]
model = best_result["model"]
mlflow_run = best_result["run"]

display(
  pd.DataFrame(
    [best_result["val_metrics"], best_result["test_metrics"]],
    index=["validation", "test"]))

set_config(display="diagram")
model

# COMMAND ----------

# MAGIC %md
# MAGIC Lets check to see what features were the most important in training our model

# COMMAND ----------

from shap import KernelExplainer, summary_plot
# SHAP cannot explain models using data with nulls.
# To enable SHAP to succeed, both the background data and examples to explain are imputed with the mode (most frequent values).
mode = X_train.mode().iloc[0]

# Sample background data for SHAP Explainer. Increase the sample size to reduce variance.
train_sample = X_train.sample(n=min(10, X_train.shape[0]), random_state=259237676).fillna(mode)

# Sample some rows from the validation set to explain. Increase the sample size for more thorough results.
example = X_val.sample(n=min(10, X_val.shape[0]), random_state=259237676).fillna(mode)

# Use Kernel SHAP to explain feature importance on the sampled rows from the validation set.
predict = lambda x: model.predict_proba(pd.DataFrame(x, columns=X_train.columns))
explainer = KernelExplainer(predict, train_sample, link="logit")
shap_values = explainer.shap_values(example, l1_reg=False)
summary_plot(shap_values, example, class_names=model.classes_)

# COMMAND ----------

# MAGIC %md
# MAGIC Let's register the model

# COMMAND ----------

from mlflow import MlflowClient
client = MlflowClient()

mlflow.set_registry_uri("databricks-uc")

model_name = f"{catalog}.{schema_name}.{schema_name}-loan_estimator"
model_uri = f"runs:/{ mlflow_run.info.run_id }/model"

registered_model_version = mlflow.register_model(model_uri, model_name)
mlflow.set_registered_model_alias(model_name, "Champion", 1)

# COMMAND ----------

# MAGIC %md
# MAGIC With the model now registered, lets see how we can reference it from within a notebook

# COMMAND ----------

model = mlflow.pyfunc.load_model(model_uri=model_uri)

#Call the model object to predict loan status using validation set
predictions = model.predict(X_val)

#Make copy of the validation set then append predictions
validation_set = X_val.copy()
validation_set['predictions'] = predictions

display(validation_set)

# COMMAND ----------

# MAGIC %md
# MAGIC That's not all we can do, since our model is registered we can also pull artifacts into our notebook to describe the model's results

# COMMAND ----------

import uuid
from IPython.display import Image
import os

# Create temp directory to download MLflow model artifact
eval_temp_dir = os.path.join(os.environ["SPARK_LOCAL_DIRS"], "tmp", str(uuid.uuid4())[:8])
os.makedirs(eval_temp_dir, exist_ok=True)

# Download the artifact
eval_path = mlflow.artifacts.download_artifacts(run_id=mlflow_run.info.run_id, dst_path=eval_temp_dir)

# COMMAND ----------

eval_roc_curve_path = os.path.join(eval_path, "val_roc_curve_plot.png")
display(Image(filename=eval_roc_curve_path))

# COMMAND ----------

eval_pr_curve_path = os.path.join(eval_path, "val_precision_recall_curve_plot.png")
display(Image(filename=eval_pr_curve_path))

# COMMAND ----------

# MAGIC %md 
# MAGIC Now before we go and see how we can serve this model to the masses, what if we **didn't** have to do all that work?  
# MAGIC
# MAGIC Let's go take a look at AutoML!
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC ### Deployment and DevOps
# MAGIC For demonstration purposes, most of this will take place in the UI, but note that (most) everything we show can also be done in code or via APIs!
