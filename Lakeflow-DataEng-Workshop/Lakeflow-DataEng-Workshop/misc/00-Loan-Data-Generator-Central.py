# Databricks notebook source
# MAGIC %md
# MAGIC # Data generator for DLT pipeline
# MAGIC This notebook generates (streaming) data for the loan transaction system. 
# MAGIC
# MAGIC

# COMMAND ----------

# DBTITLE 1,Setup and Grant Permissions for Loan Data Catalog
# MAGIC %sql
# MAGIC -- the UC commands below set up the environment, they are idempotent, you can rerun the noteook anytime. 
# MAGIC
# MAGIC CREATE CATALOG IF NOT EXISTS demo ;
# MAGIC USE CATALOG demo ;
# MAGIC CREATE SCHEMA IF NOT EXISTS loan_io ;
# MAGIC USE demo.loan_io ;
# MAGIC
# MAGIC -- needed for keeping things tidy with DLT    
# MAGIC GRANT CREATE SCHEMA, USE SCHEMA, USE CATALOG on CATALOG demo TO `account users`; 
# MAGIC
# MAGIC DROP VOLUME IF EXISTS historical_loans;
# MAGIC DROP VOLUME IF EXISTS raw_transactions;
# MAGIC DROP VOLUME IF EXISTS ref_accounting;
# MAGIC CREATE VOLUME historical_loans;
# MAGIC CREATE VOLUME raw_transactions;
# MAGIC CREATE VOLUME ref_accounting;
# MAGIC
# MAGIC
# MAGIC USE CATALOG demo;
# MAGIC USE SCHEMA loan_io;
# MAGIC
# MAGIC GRANT READ VOLUME ON VOLUME historical_loans TO `account users`;
# MAGIC GRANT READ VOLUME ON VOLUME raw_transactions TO `account users`;
# MAGIC GRANT READ VOLUME ON VOLUME ref_accounting TO `account users`;

# COMMAND ----------

# MAGIC %pip install iso3166 Faker

# COMMAND ----------

dbutils.library.restartPython() 


# COMMAND ----------

# total runtime of the load generator = batch_wait * batch_count
# make sure it coveres the length of the workshop

reset_all_data= False     # False, volumes are dropped now, rerun notebook for restart
batch_wait= 20
num_recs = 33
batch_count= 180

# volumes, must match the ingestion pipeline
output_path =     '/Volumes/demox/loan_io/'
hist_loans =      output_path+'historical_loans'
raw_tx =          output_path+'raw_transactions'
ref_accounting =  output_path+'ref_accounting'



# COMMAND ----------

import pyspark.sql.functions as F


if reset_all_data:
  print(f'cleanup all volume data')
  dbutils.fs.rm(hist_loans, True)
  dbutils.fs.rm(raw_tx, True)
  dbutils.fs.rm(ref_accounting, True)
  
#dbutils.fs.mkdirs(output_path)

def cleanup_folder(path):
  #Cleanup to have something nicer
  for f in dbutils.fs.ls(path):
    if f.name.startswith('_committed') or f.name.startswith('_started') or f.name.startswith('_SUCCESS') :
      dbutils.fs.rm(f.path)

# COMMAND ----------

spark.read.csv('/databricks-datasets/lending-club-loan-stats', header=True) \
      .withColumn('id', F.monotonically_increasing_id()) \
      .withColumn('member_id', (F.rand()*1000000).cast('int')) \
      .withColumn('accounting_treatment_id', (F.rand()*6).cast('int')) \
      .repartition(50).write.mode('overwrite').option('header', True).format('csv').save(hist_loans)

spark.createDataFrame([
  (0, 'held_to_maturity'),
  (1, 'available_for_sale'),
  (2, 'amortised_cost'),
  (3, 'loans_and_recs'),
  (4, 'held_for_hedge'),
  (5, 'fv_designated')
], ['id', 'accounting_treatment']).write.format('delta').mode('overwrite').save(ref_accounting)

#cleanup_folder(hist_loans)
#cleanup_folder(ref_accounting)

# COMMAND ----------

from faker import Faker
from collections import OrderedDict 
import pyspark.sql.functions as F
import uuid
import random

fake = Faker()
base_rates = OrderedDict([("ZERO", 0.5),("UKBRBASE", 0.1),("FDTR", 0.3),(None, 0.01)])
base_rate = F.udf(lambda:fake.random_elements(elements=base_rates, length=1)[0])
fake_country_code = F.udf(fake.country_code)

fake_date = F.udf(lambda:fake.date_time_between(start_date="-2y", end_date="+0y").strftime("%m-%d-%Y %H:%M:%S"))
fake_date_future = F.udf(lambda:fake.date_time_between(start_date="+0y", end_date="+2y").strftime("%m-%d-%Y %H:%M:%S"))
fake_date_current = F.udf(lambda:fake.date_time_this_month().strftime("%m-%d-%Y %H:%M:%S"))
def random_choice(enum_list):
  return F.udf(lambda:random.choice(enum_list))

fake.date_time_between(start_date="-10y", end_date="+30y")

def generate_transactions(num, folder, file_count, mode):
  (spark.range(0,num)
  .withColumn("acc_fv_change_before_taxes", (F.rand()*1000+100).cast('int'))
  .withColumn("purpose", (F.rand()*1000+100).cast('int'))

  .withColumn("accounting_treatment_id", (F.rand()*6).cast('int'))
  .withColumn("accrued_interest", (F.rand()*100+100).cast('int'))
  .withColumn("arrears_balance", (F.rand()*100+100).cast('int'))
  .withColumn("base_rate", base_rate())
  .withColumn("behavioral_curve_id", (F.rand()*6).cast('int'))
  .withColumn("cost_center_code", fake_country_code())
  .withColumn("country_code", fake_country_code())
  .withColumn("date", fake_date())
  .withColumn("end_date", fake_date_future())
  .withColumn("next_payment_date", fake_date_current())
  .withColumn("first_payment_date", fake_date_current())
  .withColumn("last_payment_date", fake_date_current())
  .withColumn("behavioral_curve_id", (F.rand()*6).cast('int'))
  .withColumn("count", (F.rand()*500).cast('int'))
  .withColumn("arrears_balance", (F.rand()*500).cast('int'))
  .withColumn("balance", (F.rand()*500-30).cast('int'))
  .withColumn("imit_amount", (F.rand()*500).cast('int'))
  .withColumn("minimum_balance_eur", (F.rand()*500).cast('int'))
  .withColumn("type", random_choice([
          "bonds","call","cd","credit_card","current","depreciation","internet_only","ira",
          "isa","money_market","non_product","deferred","expense","income","intangible","prepaid_card",
          "provision","reserve","suspense","tangible","non_deferred","retail_bonds","savings",
          "time_deposit","vostro","other","amortisation"
        ])())
  .withColumn("status", random_choice(["active", "cancelled", "cancelled_payout_agreed", "transactional", "other"])())
  .withColumn("guarantee_scheme", random_choice(["repo", "covered_bond", "derivative", "none", "other"])())
  .withColumn("encumbrance_type", random_choice(["be_pf", "bg_dif", "hr_di", "cy_dps", "cz_dif", "dk_gdfi", "ee_dgs", "fi_dgf", "fr_fdg",  "gb_fscs",
                                                 "de_edb", "de_edo", "de_edw", "gr_dgs", "hu_ndif", "ie_dgs", "it_fitd", "lv_dgf", "lt_vi",
                                                 "lu_fgdl", "mt_dcs", "nl_dgs", "pl_bfg", "pt_fgd", "ro_fgdb", "sk_dpf", "si_dgs", "es_fgd",
                                                 "se_ndo", "us_fdic"])())
  .withColumn("purpose", random_choice(['admin','annual_bonus_accruals','benefit_in_kind','capital_gain_tax','cash_management','cf_hedge','ci_service',
                    'clearing','collateral','commitments','computer_and_it_cost','corporation_tax','credit_card_fee','critical_service','current_account_fee',
                    'custody','employee_stock_option','dealing_revenue','dealing_rev_deriv','dealing_rev_deriv_nse','dealing_rev_fx','dealing_rev_fx_nse',
                    'dealing_rev_sec','dealing_rev_sec_nse','deposit','derivative_fee','dividend','div_from_cis','div_from_money_mkt','donation','employee',
                    'escrow','fees','fine','firm_operating_expenses','firm_operations','fx','goodwill','insurance_fee','intra_group_fee','investment_banking_fee',
                    'inv_in_subsidiary','investment_property','interest','int_on_bond_and_frn','int_on_bridging_loan','int_on_credit_card','int_on_ecgd_lending',
                    'int_on_deposit','int_on_derivative','int_on_deriv_hedge','int_on_loan_and_adv','int_on_money_mkt','int_on_mortgage','int_on_sft','ips',
                    'loan_and_advance_fee','ni_contribution','manufactured_dividend','mortgage_fee','non_life_ins_premium','occupancy_cost','operational',
                    'operational_excess','operational_escrow','other','other_expenditure','other_fs_fee','other_non_fs_fee','other_social_contrib',
                    'other_staff_rem','other_staff_cost','overdraft_fee','own_property','pension','ppe','prime_brokerage','property','recovery',
                    'redundancy_pymt','reference','reg_loss','regular_wages','release','rent','restructuring','retained_earnings','revaluation',
                    'revenue_reserve','share_plan','staff','system','tax','unsecured_loan_fee','write_off'])())
  ).repartition(file_count).write.format('json').mode(mode).save(folder)
  #cleanup_folder(raw_tx)
  
# generate_transactions(10000, raw_tx, 10, "overwrite")

# COMMAND ----------

import time

# make sure you understand the total runtime of this notebook (see above)
for i in range(0, batch_count):
  generate_transactions(num_recs, raw_tx, 1, "append")
  print(f'Finished writing batch: {i} with {num_recs} records. Waiting {batch_wait} seconds now.')
  time.sleep(batch_wait)
