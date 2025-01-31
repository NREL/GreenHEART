import os
import numpy as np
import pandas as pd
import ProFAST
import greenheart.tools.profast_tools as pf_tools
from greenheart.tools.inflation.inflate import inflate_cpi, inflate_cepci
from greenheart.simulation.technologies.iron.load_top_down_coeffs import load_top_down_coeffs

def main(config):
    
    # TODO: Get feedstock costs from input sheets
    natural_gas_prices = 3.76232 # TODO: Update to read in from greenheart_config
    lime_unitcost = 122.1
    carbon_unitcost = 236.97
    electricity_cost = 48.92
    electricity_cost = config.params['lcoe'] # Originally in $/kWh
    lcoe_dollar_MWH = electricity_cost * 1000
    hydrogen_cost = config.params['lcoh'] # Originally in $/kg
    lcoh_dollar_metric_tonne = hydrogen_cost * 1000
    iron_ore_pellet_unitcost = 207.35
    iron_ore_pellet_unitcost = config.params['lco_iron_ore_tonne']
    oxygen_market_price = 0.03
    raw_water_unitcost = 0.59289
    slag_disposal_unitcost = 37.63
    if config.product_selection == 'ng_eaf' or 'h2_eaf':
        excess_oxygen = 0
    else:
        excess_oxygen = 395

    # Get plant performances into data frame/series with performance names as index
    performance = config.performance
    perf_df = performance.performances_df.set_index('Name')
    perf_ds = perf_df.loc[:,'Model']
    perf_values = perf_df.loc[:,'Model'].values
    perf_names = perf_df.index.values
    perf_types = perf_df.loc[:,'Type'].values 
    perf_units = perf_df.loc[:,'Unit'].values

    plant_capacity_mtpy = config.params['plant_capacity_mtpy'] # In metric tonnes per year
    plant_capacity_factor = perf_ds['Capacity Factor'] # Fractional

    # Get reduction plant costs into data frame/series with cost names as index
    costs = config.cost
    cost_df = costs.costs_df.set_index('Name')
    cost_ds = cost_df.loc[:,config.site['name']]
    cost_names = cost_df.index.values
    cost_types = cost_df.loc[:,'Type'].values
    cost_units = cost_df.loc[:,'Unit'].values

    installation_cost = cost_ds['Installation cost']
    land_cost = cost_ds['Land cost']

    operational_year = config.params['operational_year']
    install_years = config.params['installation_years']
    plant_life = config.params['plant_life']
    gen_inflation = config.params['gen_inflation']
    cost_year = config.params['cost_year']

    analysis_start = operational_year-install_years
    if 'pf' in config.params:
        pf = pf_tools.create_and_populate_profast(config.params['pf'])
    else:
        # Set up ProFAST
        pf = ProFAST.ProFAST("blank")

    # apply all params passed through from config
    for param, val in config.params['financial_assumptions'].items():
        pf.set_params(param, val)

    # Fill these in - can have most of them as 0 also
    if config.product_selection == 'ng_dri' or 'h2_dri':
        product_name = "reduced iron"
    elif config.product_selection == 'ng_eaf' or 'h2_eaf':
        product_name = "steel"
    else:
        raise ValueError("product_selection must be 'ng_dri', 'h2_dri','ng_eaf' or 'h2_eaf' for 'Rosner' model")
    pf.set_params(
        "commodity",
        {
            "name": f"{product_name}",
            "unit": "metric tonnes",
            "initial price": 1000,
            "escalation": gen_inflation,
        },
    )
    pf.set_params("capacity", plant_capacity_mtpy / 365)  # units/day
    pf.set_params("maintenance", {"value": 0, "escalation": gen_inflation})
    pf.set_params("analysis start year", analysis_start)
    pf.set_params("operating life", plant_life)
    pf.set_params("installation months", 12 * install_years)
    pf.set_params(
        "installation cost",
        {
            "value": installation_cost,
            "depr type": "Straight line",
            "depr period": 4,
            "depreciable": False,
        },
    )
    pf.set_params("non depr assets", land_cost)
    pf.set_params(
        "end of proj sale non depr assets",
        land_cost * (1 + gen_inflation) ** plant_life,
    )
    pf.set_params("demand rampup", 5.3)
    pf.set_params("long term utilization", plant_capacity_factor)
    pf.set_params("credit card fees", 0)
    pf.set_params("sales tax", 0)
    pf.set_params(
        "license and permit", {"value": 00, "escalation": gen_inflation}
    )
    pf.set_params("rent", {"value": 0, "escalation": gen_inflation})
    pf.set_params("property tax and insurance", 0)
    pf.set_params("admin expense", 0)
    pf.set_params("sell undepreciated cap", True)
    pf.set_params("tax losses monetized", True)
    pf.set_params("general inflation rate", gen_inflation)
    pf.set_params("debt type", "Revolving debt")
    pf.set_params("cash onhand", 1)

    # ----------------------------------- Add capital items to ProFAST ----------------
    capital_idxs = np.where(cost_types=='capital')[0]
    for idx in capital_idxs:
        name = cost_names[idx]
        unit = cost_units[idx] # Units for capital costs should be "<YYYY> $""
        source_year = int(unit[:4])
        source_year_cost = cost_ds.iloc[idx]
        cost = inflate_cepci(source_year_cost, source_year, cost_year)

        pf.add_capital_item(
                name= f"{config.product_selection}: {name}",
                cost= cost,
                depr_type="MACRS",
                depr_period=7,
                refurb=[0], 
            )

    # -------------------------------------- Add fixed costs--------------------------------
    fixed_idxs = np.where(cost_types=='fixed opex')[0]
    for idx in fixed_idxs:
        name = cost_names[idx]
        unit = cost_units[idx] # Units for fixed opex costs should be "<YYYY> $ per year"
        source_year = int(unit[:4])
        source_year_cost = cost_ds.iloc[idx]
        cost = inflate_cpi(source_year_cost, source_year, cost_year)
        pf.add_fixed_cost(
            name=f"{config.product_selection}: {name}",
            usage=1,
            unit="$/year",
            cost=cost,
            escalation=gen_inflation,
        )
    # Putting property tax and insurance here to zero out depcreciation/escalation. Could instead put it in set_params if
    # we think that is more accurate

    # ---------------------- Add feedstocks, note the various cost options-------------------
    pf.add_feedstock(
        name=f"{config.product_selection}: Raw Water Withdrawal",
        usage=perf_ds['Raw Water Withdrawal'],
        unit="metric tonnes of water per metric tonne of iron",
        cost=raw_water_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Lime",
        usage=perf_ds['Lime'],
        unit="metric tonnes of lime per metric tonne of iron",
        cost=lime_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Carbon",
        usage=perf_ds['Carbon (Coke)'],
        unit="metric tonnes of carbon per metric tonne of iron",
        cost=carbon_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Iron Ore",
        usage=perf_ds['Iron Ore'],
        unit="metric tonnes of iron ore per metric tonne of iron",
        cost=iron_ore_pellet_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Hydrogen",
        usage=perf_ds['Hydrogen'],
        unit="metric tonnes of hydrogen per metric tonne of iron",
        cost=lcoh_dollar_metric_tonne,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Natural Gas",
        usage=perf_ds['Natural Gas'],
        unit="GJ-LHV per metric tonne of iron",
        cost=natural_gas_prices,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Electricity",
        usage=perf_ds['Electricity'],
        unit="MWh per metric tonne of iron",
        cost=lcoe_dollar_MWH,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{config.product_selection}: Slag Disposal",
        usage=perf_ds['Slag'],
        unit="metric tonnes of slag per metric tonne of iron",
        cost=slag_disposal_unitcost,
        escalation=gen_inflation,
    )

    pf.add_coproduct(
        name=f"{config.product_selection}: Oxygen sales",
        usage=excess_oxygen,
        unit="kg O2 per metric tonne of iron",
        cost=oxygen_market_price,
        escalation=gen_inflation,
    )

    # ------------------------------ Set up outputs ---------------------------

    sol = pf.solve_price()
    summary = pf.get_summary_vals()
    price_breakdown = pf.get_cost_breakdown()

    return sol, summary, price_breakdown, pf