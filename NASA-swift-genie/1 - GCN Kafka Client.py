# Databricks notebook source
# MAGIC %pip install  --quiet gcn-kafka 
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

d_catalog = "demo_frank"
d_schema = "nasa"
d_table = "raw_events" 

f_schema = f"{d_catalog}.{d_schema}"
f_table = f"{f_schema}.{d_table}"

print(f"schema: {f_schema}, table: {f_table}")



# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {f_schema}; ")

# COMMAND ----------

import pandas as pd

def msg_to_pd(msg):
    lines = msg.split('\n')
    data = {}
    comments = ''
    for line in lines:
        if line.strip():
            key_value = line.split(':')
            if key_value[0].strip() == 'COMMENTS':
                comments += key_value[1].strip() + ' '
            else:
                data[key_value[0].strip()] = key_value[1].strip()
    data['COMMENTS'] = comments.strip()
    df = pd.DataFrame(data, index=[0])
    df['all_text'] = df.astype(str).apply(', '.join, axis=1)
    return df


# COMMAND ----------

def save_df(pdf, table_name):
    df = spark.createDataFrame(pdf)
    df.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(table_name)


# Drop duplicate rows based on all columns
# deduplicated_table = delta_table.dropDuplicates()    

# COMMAND ----------

import datetime, time
from gcn_kafka import Consumer
from pyspark.sql.types import StructType


#config = {'max.poll.interval.ms': 600000, 'session.timeout.ms': 90000}

client_id = dbutils.secrets.get(scope="nasa-gcn", key="client_id")
client_secret = dbutils.secrets.get(scope="nasa-gcn", key="client_secret")

config = {'group.id': '',
          'auto.offset.reset': 'earliest' }

consumer = Consumer(config, 
                    client_id=client_id,
                    client_secret=client_secret)


topics = ['gcn.classic.text.SWIFT_POINTDIR']

print(f'subscribing to: {topics}')

consumer.subscribe(topics)

while True:
    
    print(f'consume({datetime.datetime.now()})', end='')
    
    for message in consumer.consume(timeout=1):
        if message.error():
            print(message.error())
            continue
        
        #regular output
        print(f'topic={message.topic()}, offset={message.offset()} \n')
        msg = message.value().decode('UTF-8')
        
        print(f'msg = {msg}')

        pdf = msg_to_pd(msg)
        save_df(pdf,f_table)
        
    print(f'- done')
    time.sleep(20)

# COMMAND ----------

'''
msg = TITLE:           GCN/SWIFT NOTICE
NOTICE_DATE:     Fri 03 May 24 04:16:31 UT
NOTICE_TYPE:     SWIFT Pointing Direction
NEXT_POINT_RA:   213.407d {+14h 13m 38s} (J2000)
NEXT_POINT_DEC:  +70.472d {+70d 28' 20"} (J2000)
NEXT_POINT_ROLL:   2.885d
SLEW_TIME:       15420.00 SOD {04:17:00.00} UT
SLEW_DATE:       20433 TJD;   124 DOY;   24/05/03
OBS_TIME:        900.00 [sec]   (=15.0 [min])
TGT_NAME:        RX J1413.6+7029 
TGT_NUM:         3111759,   Seg_Num: 10
MERIT:           60.00
INST_MODES:      BAT=0=0x0  XRT=7=0x7  UVOT=12525=0x30ED
SUN_POSTN:        40.78d {+02h 43m 07s}  +15.81d {+15d 48' 31"}
SUN_DIST:         93.68 [deg]   Sun_angle= -11.5 [hr] (East of Sun)
MOON_POSTN:      338.61d {+22h 34m 27s}  -12.48d {-12d 28' 49"}
MOON_DIST:       113.09 [deg]
MOON_ILLUM:      31 [%]
GAL_COORDS:      113.36, 45.10 [deg] galactic lon,lat of the pointing direction
ECL_COORDS:      143.56, 69.70 [deg] ecliptic lon,lat of the pointing direction
COMMENTS:        SWIFT Slew Notice to a preplanned target.  
COMMENTS:        Note that preplanned targets are overridden by any new BAT Automated Target.  
COMMENTS:        Note that preplanned targets are overridden by any TOO Target if the TOO has a higher Merit Value.  
COMMENTS:        The spacecraft longitude,latitude at Notice_time is 247.70,10.86 [deg].  
COMMENTS:        This Notice was ground-generated -- not flight-generated.

'''

# COMMAND ----------

# MAGIC %md
# MAGIC ### GCN/SWIFT NOTICE
# MAGIC
# MAGIC **NOTICE_DATE**: Fri 03 May 24 00:35:16 UT  
# MAGIC **NOTICE_TYPE**: SWIFT Pointing Direction
# MAGIC
# MAGIC #### Next Pointing Direction
# MAGIC - **Right Ascension (RA)**: 38.074d {+02h 32m 18s} (J2000)
# MAGIC - **Declination (DEC)**: -57.795d {-57d 47' 40"} (J2000)
# MAGIC - **Roll Angle**: 352.562d
# MAGIC
# MAGIC #### Slew Information
# MAGIC - **Slew Time**: 2160.00 SOD {00:36:00.00} UT
# MAGIC - **Slew Date**: 20433 TJD; 124 DOY; 24/05/03
# MAGIC - **Observation Time**: 600.00 [sec] (=10.0 [min])
# MAGIC
# MAGIC #### Target Information
# MAGIC - **Target Name**: 2MASS J0232-5746
# MAGIC - **Target Number**: 3112532, Seg_Num: 242
# MAGIC - **Merit**: 40.00
# MAGIC
# MAGIC #### Instrument Modes
# MAGIC - **BAT**: 0 = 0x0
# MAGIC - **XRT**: 0 = 0x0
# MAGIC - **UVOT**: 396 = 0x18C
# MAGIC
# MAGIC #### Solar and Lunar Positions
# MAGIC - **Sun Position**: 40.63d {+02h 42m 32s} +15.76d {+15d 45' 49"}
# MAGIC - **Sun Distance**: 73.48 [deg], Sun_angle = 0.2 [hr] (West of Sun)
# MAGIC - **Moon Position**: 336.57d {+22h 26m 17s} -13.44d {-13d 26' 22"}
# MAGIC - **Moon Distance**: 63.70 [deg]
# MAGIC - **Moon Illumination**: 33 [%]
# MAGIC
# MAGIC #### Coordinates
# MAGIC - **Galactic Coordinates**: 279.87, -54.58 [deg]
# MAGIC - **Ecliptic Coordinates**: 355.23, -65.10 [deg]
# MAGIC
# MAGIC #### Comments
# MAGIC - SWIFT Slew Notice to a preplanned target.
# MAGIC - Note that preplanned targets are overridden by any new BAT Automated Target.
# MAGIC - Note that preplanned targets are overridden by any TOO Target if the TOO has a higher Merit Value.
# MAGIC - The spacecraft longitude, latitude at Notice_time is 185.06, -20.61 [deg].
# MAGIC - This Notice was ground-generated -- not flight-generated.
