# Databricks notebook source
# MAGIC %pip install --quiet astropy  mpld3 cartopy
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql.functions import col
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.coordinates import SkyCoord
import mpld3
import numpy as np

# Read the Unity Catalog table
swift_notices_df = spark.read.table("demo_frank.nasa.raw_events")

# Convert the DataFrame to a Pandas DataFrame for plotting
pdf = swift_notices_df.toPandas()

# Extract the required columns
ra = pdf['NEXT_POINT_RA'].str.extract(r'([\d\.]+)d', expand=False).astype(float)
dec = pdf['NEXT_POINT_DEC'].str.extract(r'([-\d\.]+)d', expand=False).astype(float)
merit = pdf['MERIT'].astype(float)  # Convert merit to numeric
target_name = pdf['TGT_NAME']

# Extract the observation time in minutes
obs_time = pdf['OBS_TIME'].str.extract(r'(?:\d+\.\d+\s+\[sec\]\s+\(=)(\d+\.\d+)(?:\s+\[min\]\))', expand=False).astype(float)

# Create a SkyCoord object for the target coordinates
target_coords = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')

# Create a scatter plot
fig, ax = plt.subplots(figsize=(10, 8))
scatter = ax.scatter(target_coords.ra.deg, target_coords.dec.deg, s=obs_time, c=merit, cmap='viridis', alpha=0.7)

# Set the plot title and labels
ax.set_title('SWIFT Pointing Directions')
ax.set_xlabel('Right Ascension (deg)')
ax.set_ylabel('Declination (deg)')

# Create interactive labels using mpld3
labels = target_name.tolist()
tooltip = mpld3.plugins.PointLabelTooltip(scatter, labels=labels)
mpld3.plugins.connect(fig, tooltip)

# Create a color bar
cbar = fig.colorbar(scatter, ax=ax)
cbar.set_label('Merit')

# Add zooming functionality using the zoom_button plugin
zoom_button = mpld3.plugins.MousePosition(fontsize=12)
mpld3.plugins.connect(fig, zoom_button)

# Display the interactive plot using mpld3
mpld3.display()
