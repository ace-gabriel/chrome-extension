from pprint import pprint
import pandas as pd
import math
from numpy import irr

PURCHASE_PRICE = 319990
RENT = 2200
PROPERTY_TAX = 0.01025
HOA = 0
RENT_GROWTH = 0.05
HOME_PRICE_APPRECIATION = 0.061

VACCANCY_RATE = 0.05
PROPERTY_MANAGEMENT_FEE = 0.08
LEASING_COMMISSION = 0.026
INSURANCE_COST = 0.056
REPAIR = 0.04

CAP_EX = 0.03

ACQUISITION_COST = 0.015
DISPOSTITION_COST = 0.035

UNLEVERAGED_CASH_FLOW_STR = "Unleveraged Cash Flow"
GROSS_RENT_STR = "Gross Rent"
ECNOMIC_VACANCY_FACTOR_STR = "Economic Vacancy Factor"
EXPECTED_RENT = "Expected Rent"

PROPERTY_MANAGEMENT_STR = "Property Management"
LEASING_FEES_STR = "Leasing Fees"
HOA_FEES = "HOA Fees"
PROPERTY_TAXES_STR = "Propert Taxes"
INSURANCE_STR = "Insurance"
REPAIRS_STR = "Repairs & Maintance"
CAPEX_STR = "CapEx"
TOTAL_EXPENSES_STR = "Total Expenses"
TOTAL_OPERATING_CASH_FLOW_STR = "Total Operating Cash"

INDEXES = [
  UNLEVERAGED_CASH_FLOW_STR,
  GROSS_RENT_STR,
  ECNOMIC_VACANCY_FACTOR_STR,
  EXPECTED_RENT,
  PROPERTY_MANAGEMENT_STR,
  LEASING_FEES_STR,
  HOA_FEES,
  PROPERTY_TAXES_STR,
  INSURANCE_STR,
  REPAIRS_STR,
  CAPEX_STR,
  TOTAL_EXPENSES_STR,
  TOTAL_OPERATING_CASH_FLOW_STR
]

def cal_current_operation_flow(purchase_price, rent, year):

  current_valuation = purchase_price * math.pow(1+HOME_PRICE_APPRECIATION, year)

  monthly_rent = rent*math.pow(1+RENT_GROWTH, year)
  gross_rent = monthly_rent * 12
  ecomonic_vacancy_factor = gross_rent * VACCANCY_RATE
  expected_rent = gross_rent - ecomonic_vacancy_factor

  property_managnement = expected_rent * PROPERTY_MANAGEMENT_FEE * -1
  leasing_fees = expected_rent * LEASING_COMMISSION * -1
  hoa_fees = HOA * 12 * -1
  property_tax = current_valuation * PROPERTY_TAX * -1
  insurance = expected_rent * INSURANCE_COST * -1
  repairs = expected_rent * REPAIR * -1
  capex = expected_rent * CAP_EX * -1
  total_expenses = property_managnement + leasing_fees + hoa_fees + property_tax + insurance + repairs + capex

  total_operating_cash_flow = expected_rent + total_expenses

  result = pd.Series({
    UNLEVERAGED_CASH_FLOW_STR: total_operating_cash_flow,
    GROSS_RENT_STR: gross_rent,
    ECNOMIC_VACANCY_FACTOR_STR: ecomonic_vacancy_factor,
    EXPECTED_RENT: expected_rent,
    PROPERTY_MANAGEMENT_STR: property_managnement,
    LEASING_FEES_STR: leasing_fees,
    HOA_FEES: hoa_fees,
    PROPERTY_TAXES_STR: property_tax,
    INSURANCE_STR: insurance,
    REPAIRS_STR: repairs,
    CAPEX_STR: capex,
    TOTAL_EXPENSES_STR: total_expenses,
    TOTAL_OPERATING_CASH_FLOW_STR: total_operating_cash_flow
  }, index = INDEXES)


  return result

def cashflow(purchase_price = PURCHASE_PRICE, rent=RENT, years=5):
  net_cash_flow = []
  df = pd.DataFrame(columns=[range(0,years)],index=INDEXES)
  net_purchase_price = purchase_price * (1+ACQUISITION_COST)
  net_cash_flow.append(net_purchase_price * -1.0)
  series = []
  for year in xrange(0, years):
    series.append(cal_current_operation_flow(purchase_price, rent, year))
  df = pd.concat(series, axis=1, keys=range(1, years+1))
  df = pd.DataFrame.transpose(df)
  net_sale_price = purchase_price * math.pow(1+HOME_PRICE_APPRECIATION, years) * (1 - DISPOSTITION_COST)
  net_cash_flow += df[UNLEVERAGED_CASH_FLOW_STR].tolist()
  net_cash_flow[-1] += net_sale_price
  irr_value = round(irr(net_cash_flow), 4)
  cap_rate = round(abs(1.0*net_cash_flow[1] / net_cash_flow[0]), 4)
  #pprint(df)

  return irr_value * 100
