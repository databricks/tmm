# Databricks notebook source
# This is an exploratory notebook. It is not executed as part of the pipeline.
# Use it to explore data produced by the pipeline.
#
# You can freely use SQL and Python here, just as you do in the pipeline's .sql and .py files.

spark.sql("SELECT * FROM dlt_test.test.sample_trips_apr_29_843")
