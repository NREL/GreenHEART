import numpy as np
import ProFAST

import greenheart.tools.profast_tools as pf_tools
from greenheart.tools.inflation.inflate import inflate_cpi, inflate_cepci
from greenheart.simulation.technologies.iron.load_top_down_coeffs import load_top_down_coeffs


def main(config):
    # First thing - get iron pellet cost from previous modules
    iron_ore_pellet_unitcost_tonne = config.params["lco_iron_ore_tonne"]
    if "iron_transport_tonne" in config.params.keys():
        iron_transport_cost_tonne = config.params["iron_transport_tonne"]
        ore_profit_pct = config.params["ore_profit_pct"]
        iron_ore_pellet_unitcost_tonne = (
            iron_ore_pellet_unitcost_tonne + iron_transport_cost_tonne
        ) * (1 + ore_profit_pct / 100)

    # Determine years for analyzing cost
    operational_year = config.params["operational_year"]
    install_years = config.params["installation_years"]
    plant_life = config.params["plant_life"]
    cost_year = config.params["cost_year"]
    analysis_start = operational_year - install_years

    # Get feedstock costs from input sheets
    coeff_dict = load_top_down_coeffs(
        [
            "Raw Water",
            "Lime",
            "Carbon",
            "Slag Disposal",
            "Hydrogen",
            "Natural Gas",
            "Electricity",
            "Inflation Rate",
        ]
    )

    years = list(coeff_dict["years"])
    start_idx = years.index(analysis_start)
    if len(years) > (start_idx + plant_life + install_years + 1):
        end_idx = years.index(analysis_start + plant_life + install_years + 1)
        indices = list(np.arange(start_idx, end_idx))
    else:
        end_idx = len(years) - 1
        indices = list(np.arange(start_idx, end_idx))
        repeats = start_idx + plant_life + install_years + 2 - len(years)
        for _i in range(repeats):
            indices.append(end_idx)

    raw_water_unitcost_tonne = coeff_dict["Raw Water"]["values"][indices].astype(float)
    lime_unitcost_tonne = coeff_dict["Lime"]["values"][indices].astype(float)
    carbon_unitcost_tonne = coeff_dict["Carbon"]["values"][indices].astype(float)
    slag_disposal_unitcost_tonne = coeff_dict["Slag Disposal"]["values"][indices].astype(float)
    hydrogen_cost_kg = coeff_dict["Hydrogen"]["values"][indices].astype(float)
    natural_gas_prices_MMBTU = coeff_dict["Natural Gas"]["values"][indices].astype(float)
    electricity_cost_kwh = coeff_dict["Electricity"]["values"][indices].astype(float)
    gen_inflation_pct = coeff_dict["Inflation Rate"]["values"][indices].astype(float)
    gen_inflation = np.mean(gen_inflation_pct) / 100

    # TODO figure out oxygen sales...
    # oxygen_market_price = 0.03
    # if config.product_selection in ['ng_eaf','h2_eaf']:
    #     excess_oxygen = 0
    # else:
    #     excess_oxygen = 395

    # Choose whether to override top-down electricity, hydrogen, and TODO: natural gas
    electricity_cost_kwh = config.params["lcoe"]  # Originally in $/kWh
    lcoe_dollar_MWH = electricity_cost_kwh * 1000
    hydrogen_cost_kg = config.params["lcoh"]  # Originally in $/kg
    lcoh_dollar_metric_tonne = hydrogen_cost_kg * 1000
    # TODO: Natural Gas
    natural_gas_prices_GJ = natural_gas_prices_MMBTU * 1.05506  # Convert to GJ

    # Get plant performances into data frame/series with performance names as index
    performance = config.performance
    perf_df = performance.performances_df.set_index("Name")
    perf_ds = perf_df.loc[:, "Model"]

    plant_capacity_mtpy = config.params["plant_capacity_mtpy"]  # In metric tonnes per year
    plant_capacity_factor = perf_ds["Capacity Factor"] / 100  # Fractional

    # Get reduction plant costs into data frame/series with cost names as index
    costs = config.cost
    cost_df = costs.costs_df.set_index("Name")
    cost_ds = cost_df.loc[:, config.site["name"]]
    cost_names = cost_df.index.values
    cost_types = cost_df.loc[:, "Type"].values
    cost_units = cost_df.loc[:, "Unit"].values

    installation_cost = cost_ds["Installation cost"]
    land_cost = cost_ds["Land cost"]

    if "pf" in config.params:
        pf = pf_tools.create_and_populate_profast(config.params["pf"])
    else:
        # Set up ProFAST
        pf = ProFAST.ProFAST("blank")

    product_name = config.params["capacity_denominator"]
    module_label = config.product_selection

    # apply all params passed through from config
    for param, val in config.params["financial_assumptions"].items():
        pf.set_params(param, val)

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
    pf.set_params("license and permit", {"value": 00, "escalation": gen_inflation})
    pf.set_params("rent", {"value": 0, "escalation": gen_inflation})
    pf.set_params("property tax and insurance", 0)
    pf.set_params("admin expense", 0)
    pf.set_params("sell undepreciated cap", True)
    pf.set_params("tax losses monetized", True)
    pf.set_params("general inflation rate", gen_inflation)
    pf.set_params("debt type", "Revolving debt")
    pf.set_params("cash onhand", 1)

    # ----------------------------------- Add capital items to ProFAST ----------------
    capital_idxs = np.where(cost_types == "capital")[0]
    for idx in capital_idxs:
        name = cost_names[idx]
        unit = cost_units[idx]  # Units for capital costs should be "<YYYY> $""
        source_year = int(unit[:4])
        source_year_cost = cost_ds.iloc[idx]
        cost = inflate_cepci(source_year_cost, source_year, cost_year)

        pf.add_capital_item(
            name=f"{module_label}: {name}",
            cost=cost,
            depr_type="MACRS",
            depr_period=7,
            refurb=[0],
        )

    # -------------------------------------- Add fixed costs--------------------------------
    fixed_idxs = np.where(cost_types == "fixed opex")[0]
    for idx in fixed_idxs:
        name = cost_names[idx]
        unit = cost_units[idx]  # Units for fixed opex costs should be "<YYYY> $ per year"
        source_year = int(unit[:4])
        source_year_cost = cost_ds.iloc[idx]
        cost = inflate_cpi(source_year_cost, source_year, cost_year)
        pf.add_fixed_cost(
            name=f"{module_label}: {name}",
            usage=1,
            unit="$/year",
            cost=cost,
            escalation=gen_inflation,
        )
    # Putting property tax and insurance here to zero out depcreciation/escalation.
    # Could instead put it in set_params if we think that is more accurate

    # ---------------------- Add feedstocks, note the various cost options-------------------
    pf.add_feedstock(
        name=f"{module_label}: Raw Water Withdrawal",
        usage=perf_ds["Raw Water Withdrawal"],
        unit="metric tonnes of water per metric tonne of iron",
        cost=raw_water_unitcost_tonne,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Lime",
        usage=perf_ds["Lime"],
        unit="metric tonnes of lime per metric tonne of iron",
        cost=lime_unitcost_tonne,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Carbon",
        usage=perf_ds["Carbon (Coke)"],
        unit="metric tonnes of carbon per metric tonne of iron",
        cost=carbon_unitcost_tonne,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Iron Ore",
        usage=perf_ds["Iron Ore"],
        unit="metric tonnes of iron ore per metric tonne of iron",
        cost=iron_ore_pellet_unitcost_tonne,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Hydrogen",
        usage=perf_ds["Hydrogen"],
        unit="metric tonnes of hydrogen per metric tonne of iron",
        cost=lcoh_dollar_metric_tonne,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Natural Gas",
        usage=perf_ds["Natural Gas"],
        unit="GJ-LHV per metric tonne of iron",
        cost=natural_gas_prices_GJ,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Electricity",
        usage=perf_ds["Electricity"],
        unit="MWh per metric tonne of iron",
        cost=lcoe_dollar_MWH,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name=f"{module_label}: Slag Disposal",
        usage=perf_ds["Slag"],
        unit="metric tonnes of slag per metric tonne of iron",
        cost=slag_disposal_unitcost_tonne,
        escalation=gen_inflation,
    )

    # pf.add_coproduct(
    #     name=f"{module_label}: Oxygen sales",
    #     usage=excess_oxygen,
    #     unit="kg O2 per metric tonne of iron",
    #     cost=oxygen_market_price,
    #     escalation=gen_inflation,
    # )

    # ------------------------------ Set up outputs ---------------------------

    sol = pf.solve_price()
    summary = pf.get_summary_vals()
    price_breakdown = pf.get_cost_breakdown()

    return sol, summary, price_breakdown, pf
