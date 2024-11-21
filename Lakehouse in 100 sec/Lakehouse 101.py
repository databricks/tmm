# Databricks notebook source
# read bakehouse.sales.transactions and write it as parquet
df = spark.read.table("bakehouse.sales.transactions")
df.limit(250).write.mode("overwrite").parquet("/tmp/cookies_tx.parquet")


# COMMAND ----------

# DBTITLE 1,read parquet, create UC managed Delta Table
#read parquet and write to demo_frank.cookies.transactions
df = spark.read.parquet("/tmp/cookies_tx.parquet")
df = df.filter(df.quantity > 3)
df.write.mode("overwrite").saveAsTable("demo_frank.lakehouse.transactions")

# COMMAND ----------

# DBTITLE 1,Lakehouse: DataScience Notbooks, Files, Parquet
# Data manipulation
import pandas as pd
import numpy as np

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

# Time handling
from datetime import datetime, timedelta
from pyspark.sql.functions import hour, date_format, month

# Assuming 'df' is your existing Spark DataFrame
# First let's add some useful time-based columns in Spark
enriched_df = df.withColumn('hour', hour('dateTime')) \
                .withColumn('day_of_week', date_format('dateTime', 'EEEE')) \
                .withColumn('month', month('dateTime'))

# Convert to pandas for analysis
pdf = enriched_df.toPandas()

# Fun sales analysis
def sales_insights(data):
    # Top products by revenue
    top_products = data.groupby('product')['totalPrice'].sum().sort_values(ascending=False)
    
    # Busiest hours
    rush_hours = data.groupby('hour')['transactionID'].count()
    peak_hour = rush_hours.idxmax()
    
    # Payment preferences
    payment_split = data['paymentMethod'].value_counts(normalize=True) * 100
    payment_methods = "\n        ".join([f"{method:<12} {percentage:>5.1f}%" 
                                       for method, percentage in payment_split.items()])
    
    # Average basket size
    avg_basket = data.groupby('transactionID')['quantity'].sum().mean()

    print(f"""
    🏪 Store Analytics Dashboard 🏪
    =============================
    
    🌟 Top 3 Products:
    1. {top_products.index[0]:<15} ${top_products.iloc[0]:>10,.2f}
    2. {top_products.index[1]:<15} ${top_products.iloc[1]:>10,.2f}
    3. {top_products.index[2]:<15} ${top_products.iloc[2]:>10,.2f}
    
    ⏰ Peak Hour: {peak_hour}:00 ({rush_hours[peak_hour]:,} transactions)
    
    💳 Payment Methods:

        {payment_methods}
    
    🛒 Average Items per Transaction: {avg_basket:>5.1f}
    """)
    
    return data

# Run the analysis
analyzed_data = sales_insights(pdf)

# COMMAND ----------

# DBTITLE 1,DWH: SQL editor, UC catalog etc
'''

SELECT 
  product,
  quantity,
  paymentMethod 
FROM 
  demo_frank.lakehouse.transactions 
  --  TIMESTAMP AS OF '2024-11-21T00:00:00Z'
  VERSION AS OF 1
WHERE 
  paymentMethod = "visa" 
LIMIT 
  15;

'''

