# Databricks notebook source
# MAGIC %md
# MAGIC # Data generator for DLT pipeline
# MAGIC This notebook will generate data in the given storage path to simulate a data flow. 
# MAGIC 
# MAGIC **Make sure the storage path matches what you defined in your DLT pipeline as input.**
# MAGIC 
# MAGIC 1. Run Cmd 2 to show widgets
# MAGIC 2. Specify Storage path in widget
# MAGIC 3. "Run All" to generate your data
# MAGIC 4. Cmd 5 output should show data being generated into storage path
# MAGIC 5. When finished generating data, "Stop Execution"
# MAGIC 6. To refresh landing zone, run Cmd 7
# MAGIC 
# MAGIC <!-- do not remove -->
# MAGIC <img width="1px" src="https://www.google-analytics.com/collect?v=1&gtm=GTM-NKQ8TT7&tid=UA-163989034-1&cid=555&aip=1&t=event&ec=field_demos&ea=display&dp=%2F42_field_demos%2Ffeatures%2Fdlt%2Fnotebook_dlt_generator&dt=DLT">
# MAGIC <!-- [metadata={"description":"Generate data for the DLT demo",
# MAGIC  "authors":["dillon.bostwick@databricks.com"],
# MAGIC  "db_resources":{},
# MAGIC   "search_tags":{"vertical": "retail", "step": "Data Engineering", "components": ["autoloader", "dlt"]}}] -->

# COMMAND ----------

# DBTITLE 1,Run First for Widgets
dbutils.widgets.text('path', '/demo/dlt_loan', 'Storage Path')
dbutils.widgets.combobox('batch_wait', '30', ['15', '30', '45', '60'], 'Speed (secs between writes)')
dbutils.widgets.combobox('num_recs', '10000', ['5000', '10000', '20000'], 'Volume (# records per writes)')
dbutils.widgets.combobox('batch_count', '100', ['100', '200', '500'], 'Write count (for how long we append data)')

# COMMAND ----------

# MAGIC %pip install iso3166 Faker

# COMMAND ----------

import argparse
import json
import iso3166
import logging
import random
import timeit
from datetime import datetime
from faker import Faker

output_path = dbutils.widgets.get('path')
dbutils.fs.rm(output_path + "/account_schema.json", True)
dbutils.fs.rm(output_path + "/ref_accounting_treatment", True)

spark.createDataFrame([
  (0, 'held_to_maturity'),
  (1, 'available_for_sale'),
  (2, 'amortised_cost'),
  (3, 'loans_and_recs'),
  (4, 'held_for_hedge'),
  (5, 'fv_designated')
], ['id', 'accounting_treatment']).write.format('delta').save(output_path + "/ref_accounting_treatment")

dbutils.fs.put(output_path + "/account_schema.json",
"""{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "title": "Account Schema",
  "description": "An Account represents a financial account that describes the funds that a customer has entrusted to a financial institution in the form of deposits or credit balances.",
  "type": "object",
  "properties": {
    "id": {
      "description": "The unique identifier for the account within the financial institution.",
      "type": "string"
    },
    "date": {
      "description": "The observation or value date for the data in this object. Formatted as YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601.",
      "type": "string",
      "format": "date-time"
    },
    "acc_fv_change_before_taxes": {
      "description": "Accumulated change in fair value before taxes.",
      "type": "integer",
      "monetary": true
    },
    "accounting_treatment_id":{
      "description": "Account treatment ID",
      "type": "integer",
      "monetary": true
    },
    "accrued_interest": {
      "description": "The accrued interest since the last payment date and due at the next payment date. Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "monetary": true
    },
    "arrears_balance": {
      "description": "The balance of the capital amount that is considered to be in arrears (for overdrafts/credit cards). Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "monetary": true
    },
    "asset_liability": {
      "$ref": "https://raw.githubusercontent.com/SuadeLabs/fire/master/v1-dev/common.json#/asset_liability"
    },
    "balance": {
      "description": "The contractual balance on the date and in the currency given. Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "monetary": true
    },
    "base_rate": {
      "description": "The base rate represents the basis of the rate on the balance at the given date as agreed in the terms of the account.",
      "type": "string",
      "enum": ["ZERO", "UKBRBASE", "FDTR"]
    },
    "behavioral_curve_id": {
      "description": "The unique identifier for the behavioral curve used by the financial institution.",
      "type": "string"
    },
    "break_dates": {
      "description": "Dates where this contract can be broken (by either party). Formatted as YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601.",
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "format": "date-time"
      }
    },
    "call_dates": {
      "description": "Dates where this contract can be called (by the customer). Formatted as YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601.",
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "format": "date-time"
      }
    },
    "country_code": {
      "description": "Two-letter country code for account location/jurisdiction. In accordance with ISO 3166-1.",
      "$ref": "https://raw.githubusercontent.com/SuadeLabs/fire/master/v1-dev/common.json#/country_code"
    },
    "cost_center_code": {
      "description": "The organizational unit or sub-unit to which costs/profits are booked.",
      "type": "string"
    },
    "currency_code": {
      "description": "Actual currency of the Account in accordance with ISO 4217 standards. It should be consistent with balance, accrued_interest, guarantee_amount and other monetary amounts.",
      "$ref": "https://raw.githubusercontent.com/SuadeLabs/fire/master/v1-dev/common.json#/currency_code"
    },
    "customer_id": {
      "description": "The unique identifier used by the financial institution to identify the customer that owns the account.",
      "type": "string"
    },
    "end_date": {
      "description": "The end or maturity date of the account. Format should be YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601",
      "type": "string",
      "format": "date-time"
    },
    "encumbrance_amount": {
      "description": "The amount of the account that is encumbered by potential future commitments or legal liabilities. Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "minimum": 0,
      "monetary": true
    },
    "encumbrance_type": {
      "description": "The type of the encumbrance causing the encumbrance_amount.",
      "type": "string",
      "enum": ["repo", "covered_bond", "derivative", "none", "other"]
    },
    "fvh_level": {
      "description": "Fair value hierarchy category according to IFRS 13.93 (b)",
      "type": "integer",
      "minimum": 1,
      "maximum": 3
    },
    "first_payment_date": {
      "description": "The first payment date for interest payments.",
      "type": "string",
      "format": "date-time"
    },
    "guarantee_amount": {
      "description": "The amount of the account that is guaranteed under a Government Deposit Guarantee Scheme. Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "minimum": 0,
      "monetary": true
    },
    "guarantee_scheme": {
      "description": "The Government Deposit Scheme scheme under which the guarantee_amount is guaranteed.",
      "type": "string",
      "enum": [
        "be_pf", "bg_dif", "hr_di", "cy_dps", "cz_dif", "dk_gdfi", "ee_dgs", "fi_dgf", "fr_fdg",  "gb_fscs",
        "de_edb", "de_edo", "de_edw", "gr_dgs", "hu_ndif", "ie_dgs", "it_fitd", "lv_dgf", "lt_vi",
        "lu_fgdl", "mt_dcs", "nl_dgs", "pl_bfg", "pt_fgd", "ro_fgdb", "sk_dpf", "si_dgs", "es_fgd",
        "se_ndo", "us_fdic"
      ]
    },
    "impairment_amount": {
      "description": "The impairment amount is the allowance set aside by the firm that accounts for the event that the asset becomes impaired in the future.",
      "type": "integer",
      "minimum": 0,
      "monetary": true
    },
    "impairment_status": {
      "$ref": "https://raw.githubusercontent.com/SuadeLabs/fire/master/v1-dev/common.json#/impairment_status"
    },
    "insolvency_rank": {
      "description": "The insolvency ranking as per the national legal framework of the reporting institution.",
      "type": "integer",
      "minimum": 1
    },
    "last_payment_date": {
      "description": "The final payment date for interest payments, often coincides with end_date.",
      "type": "string",
      "format": "date-time"
    },
    "ledger_code": {
      "description": "The internal ledger code or line item name.",
      "type": "string"
    },
    "limit_amount": {
      "description": "The minimum balance the customer can go overdrawn in their account.",
      "type": "integer",
      "monetary": true
    },
    "next_payment_date": {
      "description": "The next date at which interest will be paid or accrued_interest balance returned to zero.",
      "type": "string",
      "format": "date-time"
    },
    "next_withdrawal_date": {
      "description": "The next date at which customer is allowed to withdraw money from this account.",
      "type": "string",
      "format": "date-time"
    },
    "on_balance_sheet": {
      "description": "Is the account or deposit reported on the balance sheet of the financial institution?",
      "type": "boolean"
    },
    "prev_payment_date": {
      "description": "The most recent previous date at which interest was paid or accrued_interest balance returned to zero.",
      "type": "string",
      "format": "date-time"
    },
    "product_name": {
      "description": "The name of the product as given by the financial institution to be used for display and reference purposes.",
      "type": "string"
    },
    "purpose": {
      "description": "The purpose for which the account was created or is being used.",
      "type": "string",
      "enum": [
        "admin",
        "annual_bonus_accruals",
        "benefit_in_kind",
        "capital_gain_tax",
        "cash_management",
        "cf_hedge",
        "ci_service",
        "clearing",
        "collateral",
        "commitments",
        "computer_and_it_cost",
        "corporation_tax",
        "credit_card_fee",
        "critical_service",
        "current_account_fee",
        "custody",
        "employee_stock_option",
        "dealing_revenue",
        "dealing_rev_deriv",
        "dealing_rev_deriv_nse",
        "dealing_rev_fx",
        "dealing_rev_fx_nse",
        "dealing_rev_sec",
        "dealing_rev_sec_nse",
        "deposit",
        "derivative_fee",
        "dividend",
        "div_from_cis",
        "div_from_money_mkt",
        "donation",
        "employee",
        "escrow",
        "fees",
        "fine",
        "firm_operating_expenses",
        "firm_operations",
        "fx",
        "goodwill",
        "insurance_fee",
        "intra_group_fee",
        "investment_banking_fee",
        "inv_in_subsidiary",
        "investment_property",
        "interest",
        "int_on_bond_and_frn",
        "int_on_bridging_loan",
        "int_on_credit_card",
        "int_on_ecgd_lending",
        "int_on_deposit",
        "int_on_derivative",
        "int_on_deriv_hedge",
        "int_on_loan_and_adv",
        "int_on_money_mkt",
        "int_on_mortgage",
        "int_on_sft",
        "ips",
        "loan_and_advance_fee",
        "ni_contribution",
        "manufactured_dividend",
        "mortgage_fee",
        "non_life_ins_premium",
        "occupancy_cost",
        "operational",
        "operational_excess",
        "operational_escrow",
        "other",
        "other_expenditure",
        "other_fs_fee",
        "other_non_fs_fee",
        "other_social_contrib",
        "other_staff_rem",
        "other_staff_cost",
        "overdraft_fee",
        "own_property",
        "pension",
        "ppe",
        "prime_brokerage",
        "property",
        "recovery",
        "redundancy_pymt",
        "reference",
        "reg_loss",
        "regular_wages",
        "release",
        "rent",
        "restructuring",
        "retained_earnings",
        "revaluation",
        "revenue_reserve",
        "share_plan",
        "staff",
        "system",
        "tax",
        "unsecured_loan_fee",
        "write_off"
      ]
    },
    "rate": {
      "description": "The full interest rate applied to the account balance in percentage terms. Note that this therefore includes the base_rate (ie. not the spread).",
      "type": "number"
    },
    "rate_type": {
      "description": "Describes the type of interest rate applied to the account.",
      "type": "string",
      "enum": ["fixed", "variable", "tracker", "combined", "preferential"]
    },
    "regulatory_book": {
      "$ref": "https://raw.githubusercontent.com/SuadeLabs/fire/master/v1-dev/common.json#/regulatory_book"
    },
    "reporting_entity_name": {
      "description": "The name of the reporting legal entity for display purposes.",
      "type": "string"
    },
    "reporting_id": {
      "description": "The internal ID for the legal entity under which the account is being reported.",
      "type": "string"
    },
    "risk_country_code": {
      "description": "Two-letter country code describing where the risk for the account resides. In accordance with ISO 3166-1",
      "$ref": "https://raw.githubusercontent.com/SuadeLabs/fire/master/v1-dev/common.json#/country_code"
    },
    "source": {
      "description": "The source(s) where this data originated. If more than one source needs to be stored for data lineage, it should be separated by a dash. eg. Source1-Source2",
      "type": "string"
    },
    "start_date": {
      "description": "The timestamp that the trade or financial product commences. YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601.",
      "type": "string",
      "format": "date-time"
    },
    "status": {
      "description": "Describes if the Account is active or been cancelled.",
      "type": "string",
      "enum": ["active", "cancelled", "cancelled_payout_agreed", "transactional", "other"]
    },
    "type": {
      "description": "This is the type of the account with regards to common regulatory classifications.",
      "type": "string",
      "enum": [
        "bonds",
        "call",
        "cd",
        "credit_card",
        "current",
        "depreciation",
        "internet_only",
        "ira",
        "isa",
        "money_market",
        "non_product",
        "deferred",
        "expense",
        "income",
        "intangible",
        "prepaid_card",
        "provision",
        "reserve",
        "suspense",
        "tangible",
        "non_deferred",
        "retail_bonds",
        "savings",
        "time_deposit",
        "vostro",
        "other",
        "amortisation"
      ]
    },
    "trade_date": {
      "description": "The timestamp that the trade or financial product terms are agreed. YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601.",
      "type": "string",
      "format": "date-time"
    },
    "uk_funding_type": {
      "description": "Funding type calculated according to BIPRU 12.5/12.6",
      "type": "string",
      "enum": ["a", "b"]
    },
    "version_id": {
      "description": "The version identifier of the data such as the firm's internal batch identifier.",
      "type": "string"
    },
    "withdrawal_penalty": {
      "description": "This is the penalty incurred by the customer for an early withdrawal on this account. An early withdrawal is defined as a withdrawal prior to the next_withdrawal_date. Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "monetary": true
    },
    "count": {
      "description": "Describes the number of accounts aggregated into a single row.",
      "type": "integer",
      "minimum": 1
    },
    "minimum_balance_eur": {
      "description": "Indicates the minimum balance, in Euros, of each account within the aggregate. Monetary type represented as a naturally positive integer number of cents/pence.",
      "type": "integer",
      "monetary": true
    },
    "next_repricing_date": {
      "description": "The date on which the interest rate of the account will be re-calculated. YYYY-MM-DDTHH:MM:SSZ in accordance with ISO 8601.",
      "type": "string",
      "format": "date-time"
    },
    "risk_weight_std": {
      "description": "The standardised approach risk weight represented as a decimal/float such that 1.5% is 0.015.",
      "type": "number"
    }
  },
  "required": ["id", "date"],
  "additionalProperties": true
}
""")



fake = Faker()

output_path = dbutils.widgets.get('path')

def random_currency():
    return fake.currency_code()

def random_country():
    country_codes = [c[1] for c in iso3166.countries]
    return random.choice(country_codes)

    accounting_treatments = range(0, 9)
    return random.choice(accounting_treatments)

def random_integer(min, max):
    return random.randrange(min, max)

def random_enum(enum_list):
    return random.choice(enum_list)

def random_word(n):
    return " ".join(fake.words(n))

def random_text(n):
    return fake.text(n)

def random_date():
    d = fake.date_time_between(start_date="-10y", end_date="+30y")
    return d.strftime('%Y-%m-%dT%H:%M:%SZ')

def insert(product, attr, attr_value):
    return product["data"][0].update({attr: attr_value})

def generate_loans(fire_schema, n=100):
    """
    Given a list of fire product schemas (account, loan, derivative_cash_flow,
    security), generate random data and associated random relations (customer,
    issuer, collateral, etc.)
    """
    start_time = timeit.default_timer()

    f = open('/dbfs' + output_path + "/account_schema.json", "r") # output_path + "/" + fire_schema + ".json"
    schema = json.load(f)
    data_type = fire_schema.split("/")[-1].split(".json")[0]
    data = generate_product_fire(schema, data_type, n)

    end_time = timeit.default_timer() - start_time
    logging.warning(
        "Generating FIRE batches and writing to files"
        " took {} seconds".format(end_time)
    )
    return data

def write_batches_to_file(data, output):
    f = open(output, "w")
    for r in data:
        f.write(json.dumps(r) + "\n")
    f.close()

def random_accounting_treatment():
    accounting_treatments = range(0, 9)
    return random.choice(accounting_treatments)

def include_embedded_schema_properties(schema):
    try:
        for i in range(len(schema["allOf"])):
            inherited_schema = schema["allOf"][i]["$ref"].split("/")[-1]
            f = open('/dbfs/' + output_path + "/account_schema.json", "r") # output_path + "/" + inherited_schema
            inherited_schema = json.load(f)
            schema["properties"] = dict(
                schema["properties"].items() +
                inherited_schema["properties"].items()
            )

    except KeyError:
        pass

    return schema

def generate_product_fire(schema, data_type, n):
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    batch = []

    schema = include_embedded_schema_properties(schema)
    schema_attrs = schema["properties"].keys()

    for i in range(n):
        p = {}
        batch.append(p)
        for attr in schema_attrs:

            attr_obj = schema["properties"][attr]

            if attr == "id":
                attr_value = str(i)
                batch[i].update({attr: attr_value})
                continue

            elif attr == "date":
                attr_value = now
                batch[i].update({attr: attr_value})
                continue

            elif attr in ["currency_code", "facility_currency_code"]:
                attr_value = random_currency()
                batch[i].update({attr: attr_value})
                continue

            elif attr in ["country_code", "risk_country_code"]:
                attr_value = random_country()
                batch[i].update({attr: attr_value})
                continue

            elif attr == "accounting_treatment_id":
                attr_value = random_accounting_treatment()
                batch[i].update({attr: attr_value})
                continue

            elif attr in ["isin_code" or "underlying_isin_code"]:
                attr_value = random_text(12)
                batch[i].update({attr: attr_value})
                continue

            elif attr == "reporting_id":
                attr_value = random_text(20)
                batch[i].update({attr: attr_value})
                continue

            else:
                try:
                    attr_type = schema["properties"][attr]["type"]
                except KeyError:
                    continue

                if attr_type == "number":
                    attr_value = random_integer(0, 500) / 100.0
                    batch[i].update({attr: attr_value})
                    continue

                elif attr_type == "integer":
                    try:
                        attr_min = attr_obj["minimum"]
                    except KeyError:
                        attr_min = -10000
                    try:
                        attr_max = attr_obj["maximum"]
                    except KeyError:
                        attr_max = 100000

                    attr_value = random_integer(attr_min, attr_max)
                    batch[i].update({attr: attr_value})
                    continue

                elif attr_type == "string":
                    try:
                        attr_enums = attr_obj["enum"]
                        attr_value = random_enum(attr_enums)

                    except KeyError:
                        try:
                            attr_format = attr_obj["format"]
                            if attr_format == "date-time":
                                attr_value = random_date()
                            else:
                                pass

                        except KeyError:
                            attr_value = random_word(1)

                    batch[i].update({attr: attr_value})
                    continue

                elif attr_type == "boolean":
                    attr_value = random.choice([True, False])
                    batch[i].update({attr: attr_value})
                    continue

                else:
                    continue

    return batch

# COMMAND ----------

import time

dbutils.fs.mkdirs(f'{output_path}/landing')

for i in range(0, int(dbutils.widgets.get('batch_count'))):
  time.sleep(int(dbutils.widgets.get('batch_wait')))
  write_batches_to_file(generate_loans("account", int(dbutils.widgets.get('num_recs'))), f'/dbfs{output_path}/landing/accounts{i}.json')
  print(f'Finished writing batch: {i}')
