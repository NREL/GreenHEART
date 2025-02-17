"""
Created on Wed Oct 19 12:13:58 2022

@author: ereznic2
"""

import pandas as pd
import ProFAST


# mat_n_heat_integration = 1


def run_profast_for_steel(
    plant_capacity_mtpy,
    plant_capacity_factor,
    plant_life,
    levelized_cost_of_hydrogen,
    electricity_cost,
    grid_prices_interpolated_USDperMWh,
    natural_gas_cost,
    lime_unitcost,
    carbon_unitcost,
    iron_ore_pellet_unitcost,
    o2_heat_integration,
):
    # # Steel plant capacity in metric tons per year (eventually import to function)
    # plant_capacity_mtpy = 1162077
    # plant_capacity_factor = 0.9
    # levelized_cost_of_hydrogen = 10

    # # Should connect these to something (AEO, Cambium, etc.)
    # natural_gas_cost = 4                        # $/MMBTU
    # electricity_cost = 48.92                    # $/MWh
    # plant_life = 30
    # lime_unitcost = 155.34
    # carbon_unitcost = 218.74
    # iron_ore_pellet_unitcost = 230.52

    model_year_CEPCI = 596.2
    equation_year_CEPCI = 708.8

    steel_production_mtpy = plant_capacity_mtpy * plant_capacity_factor

    # # Hydrogen cost
    # levelized_cost_of_hydrogen = 7              # $/kg
    # natural_gas_cost = 4                        # $/MMBTU
    # electricity_cost = 48.92                    # $/MWh

    # --------------------- Capital costs and Total Plant Cost ---------------------

    capex_eaf_casting = (
        model_year_CEPCI / equation_year_CEPCI * 352191.5237 * plant_capacity_mtpy**0.456
    )
    capex_shaft_furnace = (
        model_year_CEPCI / equation_year_CEPCI * 489.68061 * plant_capacity_mtpy**0.88741
    )
    capex_oxygen_supply = (
        model_year_CEPCI / equation_year_CEPCI * 1715.21508 * plant_capacity_mtpy**0.64574
    )
    if o2_heat_integration == 1:
        capex_h2_preheating = (
            model_year_CEPCI
            / equation_year_CEPCI
            * (1 - 0.4)
            * (45.69123 * plant_capacity_mtpy**0.86564)
        )  # Optimistic ballpark estimate of 60% reduction in preheating
        capex_cooling_tower = (
            model_year_CEPCI
            / equation_year_CEPCI
            * (1 - 0.3)
            * (2513.08314 * plant_capacity_mtpy**0.63325)
        )  # Optimistic ballpark estimate of 30% reduction in cooling
        oxygen_market_price = 0.03  # $/kgO2
    else:
        capex_h2_preheating = (
            model_year_CEPCI / equation_year_CEPCI * 45.69123 * plant_capacity_mtpy**0.86564
        )
        capex_cooling_tower = (
            model_year_CEPCI / equation_year_CEPCI * 2513.08314 * plant_capacity_mtpy**0.63325
        )
        oxygen_market_price = 0  # $/kgO2
    excess_oxygen = 395  # excess kg O2/metric ton of steel
    capex_piping = (
        model_year_CEPCI / equation_year_CEPCI * 11815.72718 * plant_capacity_mtpy**0.59983
    )
    capex_elec_instr = (
        model_year_CEPCI / equation_year_CEPCI * 7877.15146 * plant_capacity_mtpy**0.59983
    )
    capex_buildings_storage_water = (
        model_year_CEPCI / equation_year_CEPCI * 1097.81876 * plant_capacity_mtpy**0.8
    )
    capex_misc = model_year_CEPCI / equation_year_CEPCI * 7877.1546 * plant_capacity_mtpy**0.59983

    total_plant_cost = (
        capex_eaf_casting
        + capex_shaft_furnace
        + capex_oxygen_supply
        + capex_h2_preheating
        + capex_cooling_tower
        + capex_piping
        + capex_elec_instr
        + capex_buildings_storage_water
        + capex_misc
    )

    # -------------------------------Fixed O&M Costs------------------------------

    labor_cost_annual_operation = (
        69375996.9
        * ((plant_capacity_mtpy / 365 * 1000) ** 0.25242)
        / ((1162077 / 365 * 1000) ** 0.25242)
    )
    labor_cost_maintenance = 0.00863 * total_plant_cost
    labor_cost_admin_support = 0.25 * (labor_cost_annual_operation + labor_cost_maintenance)

    property_tax_insurance = 0.02 * total_plant_cost

    (
        labor_cost_annual_operation
        + labor_cost_maintenance
        + labor_cost_admin_support
        + property_tax_insurance
    )

    # -------------------------- Feedstock and Waste Costs -------------------------

    maintenance_materials_unitcost = 7.72  # $/metric ton of annual steel slab production at real CF
    raw_water_unitcost = 0.59289  # $/metric ton of raw water
    lime_unitcost = lime_unitcost  # $/metric ton of lime
    carbon_unitcost = carbon_unitcost  # $/metric ton of Carbon
    slag_disposal_unitcost = 37.63  # $ metric ton of Slag
    iron_ore_pellet_unitcost = iron_ore_pellet_unitcost  # $/metric tone of Ore

    # ---------------Feedstock Consumtion and Waste/Emissions Production-----------

    iron_ore_consumption = 1.62927  # metric tons of iron ore/metric ton of steel production
    raw_water_consumption = 0.80367  # metric tons of raw water/metric ton of steel production
    lime_consumption = 0.01812  # metric tons of lime/metric ton of steel production
    carbon_consumption = 0.0538  # metric tons of carbon/metric ton of steel production
    hydrogen_consumption = 0.06596  # metric tons of hydrogen/metric ton of steel production
    natural_gas_consumption = 0.71657  # GJ-LHV/metric ton of steel production
    electricity_consumption = 0.5502  # MWh/metric ton of steel production

    slag_production = 0.17433  # metric tons of slag/metric ton of steel production

    # ---------------------- Owner's (Installation) Costs --------------------------
    labor_cost_fivemonth = (
        5 / 12 * (labor_cost_annual_operation + labor_cost_maintenance + labor_cost_admin_support)
    )

    (maintenance_materials_unitcost * plant_capacity_mtpy / 12)
    (
        plant_capacity_mtpy
        * (
            raw_water_consumption * raw_water_unitcost
            + lime_consumption * lime_unitcost
            + carbon_consumption * carbon_unitcost
            + iron_ore_consumption * iron_ore_pellet_unitcost
        )
        / 12
    )

    (plant_capacity_mtpy * slag_disposal_unitcost * slag_production / 12)

    (
        0.25
        * plant_capacity_mtpy
        * (
            hydrogen_consumption * levelized_cost_of_hydrogen * 1000
            + natural_gas_consumption * natural_gas_cost / 1.05505585
            + electricity_consumption * electricity_cost
        )
        / 12
    )
    two_percent_tpc = 0.02 * total_plant_cost

    fuel_consumables_60day_supply_cost = (
        plant_capacity_mtpy
        * (
            raw_water_consumption * raw_water_unitcost
            + lime_consumption * lime_unitcost
            + carbon_consumption * carbon_unitcost
            + iron_ore_consumption * iron_ore_pellet_unitcost
        )
        / 365
        * 60
    )

    spare_parts_cost = 0.005 * total_plant_cost

    land_cost = 0.775 * plant_capacity_mtpy
    misc_owners_costs = 0.15 * total_plant_cost

    installation_cost = (
        labor_cost_fivemonth
        + two_percent_tpc
        + fuel_consumables_60day_supply_cost
        + spare_parts_cost
        + misc_owners_costs
    )

    # total_overnight_capital_cost = total_plant_cost + total_owners_cost

    financial_assumptions = pd.read_csv(
        "H2_Analysis/financial_inputs.csv", index_col=None, header=0
    ).set_index(["Parameter"])
    financial_assumptions = financial_assumptions["Hydrogen/Steel/Ammonia"]

    # Set up ProFAST
    pf = ProFAST.ProFAST()

    install_years = 3
    analysis_start = [*grid_prices_interpolated_USDperMWh][0] - install_years

    # Fill these in - can have most of them as 0 also
    gen_inflation = 0.00
    pf.set_params(
        "commodity",
        {
            "name": "Steel",
            "unit": "metric tons",
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
    pf.set_params("total income tax rate", financial_assumptions["total income tax rate"])
    pf.set_params("capital gains tax rate", financial_assumptions["capital gains tax rate"])
    pf.set_params("sell undepreciated cap", True)
    pf.set_params("tax losses monetized", True)
    pf.set_params("general inflation rate", gen_inflation)
    pf.set_params(
        "leverage after tax nominal discount rate",
        financial_assumptions["leverage after tax nominal discount rate"],
    )
    pf.set_params(
        "debt equity ratio of initial financing",
        financial_assumptions["debt equity ratio of initial financing"],
    )
    pf.set_params("debt type", "Revolving debt")
    pf.set_params("debt interest rate", financial_assumptions["debt interest rate"])
    pf.set_params("cash onhand", 1)

    # ----------------------------------- Add capital items to ProFAST ----------------
    pf.add_capital_item(
        name="EAF & Casting",
        cost=capex_eaf_casting,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="Shaft Furnace",
        cost=capex_shaft_furnace,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="Oxygen Supply",
        cost=capex_oxygen_supply,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="H2 Pre-heating",
        cost=capex_h2_preheating,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="Cooling Tower",
        cost=capex_cooling_tower,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="Piping", cost=capex_piping, depr_type="MACRS", depr_period=7, refurb=[0]
    )
    pf.add_capital_item(
        name="Electrical & Instrumentation",
        cost=capex_elec_instr,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="Buildings, Storage, Water Service",
        cost=capex_buildings_storage_water,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )
    pf.add_capital_item(
        name="Other Miscellaneous Costs",
        cost=capex_misc,
        depr_type="MACRS",
        depr_period=7,
        refurb=[0],
    )

    total_capex = (
        capex_eaf_casting
        + capex_shaft_furnace
        + capex_oxygen_supply
        + capex_h2_preheating
        + capex_cooling_tower
        + capex_piping
        + capex_elec_instr
        + capex_buildings_storage_water
        + capex_misc
    )

    # -------------------------------------- Add fixed costs--------------------------------
    pf.add_fixed_cost(
        name="Annual Operating Labor Cost",
        usage=1,
        unit="$/year",
        cost=labor_cost_annual_operation,
        escalation=gen_inflation,
    )
    pf.add_fixed_cost(
        name="Maintenance Labor Cost",
        usage=1,
        unit="$/year",
        cost=labor_cost_maintenance,
        escalation=gen_inflation,
    )
    pf.add_fixed_cost(
        name="Administrative & Support Labor Cost",
        usage=1,
        unit="$/year",
        cost=labor_cost_admin_support,
        escalation=gen_inflation,
    )
    pf.add_fixed_cost(
        name="Property tax and insurance",
        usage=1,
        unit="$/year",
        cost=0.02 * total_plant_cost,
        escalation=0.0,
    )
    # Putting property tax and insurance here to zero out depcreciation/escalation. Could instead
    # put it in set_params if we think that is more accurate

    # ---------------------- Add feedstocks, note the various cost options-------------------
    pf.add_feedstock(
        name="Maintenance Materials",
        usage=1.0,
        unit="Units per metric ton of steel",
        cost=maintenance_materials_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Raw Water Withdrawal",
        usage=raw_water_consumption,
        unit="metric tons of water per metric ton of steel",
        cost=raw_water_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Lime",
        usage=lime_consumption,
        unit="metric tons of lime per metric ton of steel",
        cost=lime_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Carbon",
        usage=carbon_consumption,
        unit="metric tons of carbon per metric ton of steel",
        cost=carbon_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Iron Ore",
        usage=iron_ore_consumption,
        unit="metric tons of iron ore per metric ton of steel",
        cost=iron_ore_pellet_unitcost,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Hydrogen",
        usage=hydrogen_consumption,
        unit="metric tons of hydrogen per metric ton of steel",
        cost=levelized_cost_of_hydrogen * 1000,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Natural Gas",
        usage=natural_gas_consumption,
        unit="GJ-LHV per metric ton of steel",
        cost=natural_gas_cost / 1.05505585,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Electricity",
        usage=electricity_consumption,
        unit="MWh per metric ton of steel",
        cost=grid_prices_interpolated_USDperMWh,
        escalation=gen_inflation,
    )
    pf.add_feedstock(
        name="Slag Disposal",
        usage=slag_production,
        unit="metric tons of slag per metric ton of steel",
        cost=slag_disposal_unitcost,
        escalation=gen_inflation,
    )

    pf.add_coproduct(
        name="Oxygen sales",
        usage=excess_oxygen,
        unit="kg O2 per metric ton of steel",
        cost=oxygen_market_price,
        escalation=gen_inflation,
    )
    # Not sure if ProFAST can work with negative cost i.e., revenues so, will add the reduction at
    # the end
    # if o2_heat_integration == 1:
    #     pf.addfeedstock(
    #         name="Oxygen Sales",
    #         usage=excess_oxygen,
    #         unit="kilograms of oxygen per metric ton of steel",
    #         cost=-oxygen_market_price,
    #         escalation=gen_inflation,
    #     )
    # ------------------------------ Sovle for breakeven price ---------------------------

    sol = pf.solve_price()

    summary = pf.summary_vals

    price_breakdown = pf.get_cost_breakdown()

    price_breakdown_eaf_casting = price_breakdown.loc[
        price_breakdown["Name"] == "EAF & Casting", "NPV"
    ].tolist()[0]
    price_breakdown_shaft_furnace = price_breakdown.loc[
        price_breakdown["Name"] == "Shaft Furnace", "NPV"
    ].tolist()[0]
    price_breakdown_oxygen_supply = price_breakdown.loc[
        price_breakdown["Name"] == "Oxygen Supply", "NPV"
    ].tolist()[0]
    price_breakdown_h2_preheating = price_breakdown.loc[
        price_breakdown["Name"] == "H2 Pre-heating", "NPV"
    ].tolist()[0]
    price_breakdown_cooling_tower = price_breakdown.loc[
        price_breakdown["Name"] == "Cooling Tower", "NPV"
    ].tolist()[0]
    price_breakdown_piping = price_breakdown.loc[
        price_breakdown["Name"] == "Piping", "NPV"
    ].tolist()[0]
    price_breakdown_elec_instr = price_breakdown.loc[
        price_breakdown["Name"] == "Electrical & Instrumentation", "NPV"
    ].tolist()[0]
    price_breakdown_buildings_storage_water = price_breakdown.loc[
        price_breakdown["Name"] == "Buildings, Storage, Water Service", "NPV"
    ].tolist()[0]
    price_breakdown_misc = price_breakdown.loc[
        price_breakdown["Name"] == "Other Miscellaneous Costs", "NPV"
    ].tolist()[0]
    price_breakdown_installation = price_breakdown.loc[
        price_breakdown["Name"] == "Installation cost", "NPV"
    ].tolist()[0]

    price_breakdown_labor_cost_annual = price_breakdown.loc[
        price_breakdown["Name"] == "Annual Operating Labor Cost", "NPV"
    ].tolist()[0]
    price_breakdown_labor_cost_maintenance = price_breakdown.loc[
        price_breakdown["Name"] == "Maintenance Labor Cost", "NPV"
    ].tolist()[0]
    price_breakdown_labor_cost_admin_support = price_breakdown.loc[
        price_breakdown["Name"] == "Administrative & Support Labor Cost", "NPV"
    ].tolist()[0]
    # price_breakdown_proptax_ins = price_breakdown.loc[
    #     price_breakdown["Name"] == "Property tax and insurance", "NPV"
    # ].tolist()[0]

    price_breakdown_maintenance_materials = price_breakdown.loc[
        price_breakdown["Name"] == "Maintenance Materials", "NPV"
    ].tolist()[0]
    price_breakdown_water_withdrawal = price_breakdown.loc[
        price_breakdown["Name"] == "Raw Water Withdrawal", "NPV"
    ].tolist()[0]
    price_breakdown_lime = price_breakdown.loc[price_breakdown["Name"] == "Lime", "NPV"].tolist()[0]
    price_breakdown_carbon = price_breakdown.loc[
        price_breakdown["Name"] == "Carbon", "NPV"
    ].tolist()[0]
    price_breakdown_iron_ore = price_breakdown.loc[
        price_breakdown["Name"] == "Iron Ore", "NPV"
    ].tolist()[0]
    if levelized_cost_of_hydrogen < 0:
        price_breakdown_hydrogen = (
            -1 * price_breakdown.loc[price_breakdown["Name"] == "Hydrogen", "NPV"].tolist()[0]
        )
    else:
        price_breakdown_hydrogen = price_breakdown.loc[
            price_breakdown["Name"] == "Hydrogen", "NPV"
        ].tolist()[0]
    price_breakdown_natural_gas = price_breakdown.loc[
        price_breakdown["Name"] == "Natural Gas", "NPV"
    ].tolist()[0]
    price_breakdown_electricity = price_breakdown.loc[
        price_breakdown["Name"] == "Electricity", "NPV"
    ].tolist()[0]
    price_breakdown_slag = price_breakdown.loc[
        price_breakdown["Name"] == "Slag Disposal", "NPV"
    ].tolist()[0]
    price_breakdown_taxes = (
        price_breakdown.loc[price_breakdown["Name"] == "Income taxes payable", "NPV"].tolist()[0]
        - price_breakdown.loc[price_breakdown["Name"] == "Monetized tax losses", "NPV"].tolist()[0]
    )
    if o2_heat_integration == 1:
        price_breakdown_O2sales = price_breakdown.loc[
            price_breakdown["Name"] == "Oxygen sales", "NPV"
        ].tolist()[0]
    else:
        price_breakdown_O2sales = 0

    if gen_inflation > 0:
        price_breakdown_taxes = (
            price_breakdown_taxes
            + price_breakdown.loc[
                price_breakdown["Name"] == "Capital gains taxes payable", "NPV"
            ].tolist()[0]
        )

    # price_breakdown_financial = (
    #     price_breakdown.loc[price_breakdown["Name"] == "Non-depreciable assets", "NPV"].tolist()[0]  # noqa: E501
    #     + price_breakdown.loc[price_breakdown["Name"] == "Cash on hand reserve", "NPV"].tolist()[0]  # noqa: E501
    #     + price_breakdown.loc[
    #         price_breakdown["Name"] == "Property tax and insurance", "NPV"
    #     ].tolist()[0]
    #     + price_breakdown.loc[price_breakdown["Name"] == "Repayment of debt", "NPV"].tolist()[0]
    #     + price_breakdown.loc[price_breakdown["Name"] == "Interest expense", "NPV"].tolist()[0]
    #     + price_breakdown.loc[price_breakdown["Name"] == "Dividends paid", "NPV"].tolist()[0]
    #     - price_breakdown.loc[
    #         price_breakdown["Name"] == "Sale of non-depreciable assets", "NPV"
    #     ].tolist()[0]
    #     - price_breakdown.loc[price_breakdown["Name"] == "Cash on hand recovery", "NPV"].tolist()[0]  # noqa: E501
    #     - price_breakdown.loc[price_breakdown["Name"] == "Inflow of debt", "NPV"].tolist()[0]
    #     - price_breakdown.loc[price_breakdown["Name"] == "Inflow of equity", "NPV"].tolist()[0]
    # )

    # Calculate financial expense associated with equipment
    price_breakdown_financial_equipment = (
        price_breakdown.loc[price_breakdown["Name"] == "Repayment of debt", "NPV"].tolist()[0]
        + price_breakdown.loc[price_breakdown["Name"] == "Interest expense", "NPV"].tolist()[0]
        + price_breakdown.loc[price_breakdown["Name"] == "Dividends paid", "NPV"].tolist()[0]
        - price_breakdown.loc[price_breakdown["Name"] == "Inflow of debt", "NPV"].tolist()[0]
        - price_breakdown.loc[price_breakdown["Name"] == "Inflow of equity", "NPV"].tolist()[0]
    )

    # Calculate remaining financial expenses
    price_breakdown_financial_remaining = (
        price_breakdown.loc[price_breakdown["Name"] == "Non-depreciable assets", "NPV"].tolist()[0]
        + price_breakdown.loc[price_breakdown["Name"] == "Cash on hand reserve", "NPV"].tolist()[0]
        + price_breakdown.loc[
            price_breakdown["Name"] == "Property tax and insurance", "NPV"
        ].tolist()[0]
        - price_breakdown.loc[
            price_breakdown["Name"] == "Sale of non-depreciable assets", "NPV"
        ].tolist()[0]
        - price_breakdown.loc[price_breakdown["Name"] == "Cash on hand recovery", "NPV"].tolist()[0]
    )

    price_breakdown_check = (
        price_breakdown_eaf_casting
        + price_breakdown_shaft_furnace
        + price_breakdown_oxygen_supply
        + price_breakdown_h2_preheating
        + price_breakdown_cooling_tower
        + price_breakdown_piping
        + price_breakdown_elec_instr
        + price_breakdown_buildings_storage_water
        + price_breakdown_misc
        + price_breakdown_installation
        + price_breakdown_labor_cost_annual
        + price_breakdown_labor_cost_maintenance
        + price_breakdown_labor_cost_admin_support
        + price_breakdown_maintenance_materials
        + price_breakdown_water_withdrawal
        + price_breakdown_lime
        + price_breakdown_carbon
        + price_breakdown_iron_ore
        + price_breakdown_hydrogen
        + price_breakdown_natural_gas
        + price_breakdown_electricity
        + price_breakdown_slag
        + price_breakdown_taxes
        + price_breakdown_financial_equipment
        + price_breakdown_financial_remaining
        + price_breakdown_O2sales
    )
    # a neater way to implement is add to price_breakdowns but I am not sure if ProFAST can
    # handle negative costs

    bos_savings = (price_breakdown_labor_cost_admin_support) * 0.3
    steel_price_breakdown = {
        "Steel price: EAF and Casting CAPEX ($/metric ton)": price_breakdown_eaf_casting,
        "Steel price: Shaft Furnace CAPEX ($/metric ton)": price_breakdown_shaft_furnace,
        "Steel price: Oxygen Supply CAPEX ($/metric ton)": price_breakdown_oxygen_supply,
        "Steel price: H2 Pre-heating CAPEX ($/metric ton)": price_breakdown_h2_preheating,
        "Steel price: Cooling Tower CAPEX ($/metric ton)": price_breakdown_cooling_tower,
        "Steel price: Piping CAPEX ($/metric ton)": price_breakdown_piping,
        "Steel price: Electrical & Instrumentation ($/metric ton)": price_breakdown_elec_instr,
        "Steel price: Buildings, Storage, Water Service CAPEX ($/metric ton)": price_breakdown_buildings_storage_water,  # noqa: E501
        "Steel price: Miscellaneous CAPEX ($/metric ton)": price_breakdown_misc,
        "Steel price: Annual Operating Labor Cost ($/metric ton)": price_breakdown_labor_cost_annual,  # noqa: E501
        "Steel price: Maintenance Labor Cost ($/metric ton)": price_breakdown_labor_cost_maintenance,  # noqa: E501
        "Steel price: Administrative & Support Labor Cost ($/metric ton)": price_breakdown_labor_cost_admin_support,  # noqa: E501
        "Steel price: Installation Cost ($/metric ton)": price_breakdown_installation,
        "Steel price: Maintenance Materials ($/metric ton)": price_breakdown_maintenance_materials,
        "Steel price: Raw Water Withdrawal ($/metric ton)": price_breakdown_water_withdrawal,
        "Steel price: Lime ($/metric ton)": price_breakdown_lime,
        "Steel price: Carbon ($/metric ton)": price_breakdown_carbon,
        "Steel price: Iron Ore ($/metric ton)": price_breakdown_iron_ore,
        "Steel price: Hydrogen ($/metric ton)": price_breakdown_hydrogen,
        "Steel price: Natural gas ($/metric ton)": price_breakdown_natural_gas,
        "Steel price: Electricity ($/metric ton)": price_breakdown_electricity,
        "Steel price: Slag Disposal ($/metric ton)": price_breakdown_slag,
        "Steel price: Taxes ($/metric ton)": price_breakdown_taxes,
        "Steel price: Equipment Financing ($/metric ton)": price_breakdown_financial_equipment,
        "Steel price: Remaining Financial ($/metric ton)": price_breakdown_financial_remaining,
        "Steel price: Oxygen sales ($/metric ton)": price_breakdown_O2sales,
        "Steel price: Total ($/metric ton)": price_breakdown_check,
        "(-) Steel price: BOS savings ($/metric ton)": bos_savings,
    }

    price_breakdown = price_breakdown.drop(columns=["index", "Amount"])

    return (
        sol,
        summary,
        price_breakdown,
        steel_production_mtpy,
        steel_price_breakdown,
        total_capex,
    )
