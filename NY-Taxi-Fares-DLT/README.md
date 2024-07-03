# NYC Taxi Fare Data Analysis Pipeline

## Overview
This Delta Live Tables (DLT) pipeline processes NYC taxi ride data, demonstrating data ingestion, transformation, and analysis using a medallion architecture approach.

## Pipeline Structure

### Bronze Layer
- **Table**: `taxi_raw_records`
- **Source**: `samples.nyctaxi.trips`
- **Key Feature**: Data quality check to ensure positive trip distances

### Silver Layer
1. **Table**: `flagged_rides`
   - Identifies potentially fraudulent or unusual rides
   - Filters for same zip code rides or short trips with high fares

2. **Materialized View**: `weekly_stats`
   - Calculates weekly averages for fare amounts and trip distances

### Gold Layer
- **Materialized View**: `top_n`
  - Joins `flagged_rides` and `weekly_stats`
  - Presents top 3 rides by fare amount for investigation

## Key Features
- Streaming data processing
- Data quality checks using DLT expectations
- Streaming Tables for ingestion
- Materialized views for efficient querying
- Demonstration of medallion architecture principles


## Getting Started
1. Create a new DLT pipeline in your Databricks workspace
2. Copy the provided SQL code into a new notebook
3. Configure the pipeline settings (serverless compute, Unity Catalog)
4. Run the pipeline and explore the results in Unity Catalog

## Requirements
- Databricks workspace with Unity Catalog enabled
- Access to the `samples.nyctaxi.trips` dataset

This pipeline serves as a practical example of building data analytics workflows using Delta Live Tables, showcasing real-time data processing, data quality management, and business-ready data presentation.
