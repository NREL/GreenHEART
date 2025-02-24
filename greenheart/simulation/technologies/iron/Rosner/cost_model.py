"""
Direct Reduced Iron (DRI) model developed by Rosner et al.
Energy Environ. Sci., 2023, 16, 4121
doi.org/10.1039/d3ee01077e
"""

from pathlib import Path

import numpy as np
import pandas as pd
from hopp.utilities import load_yaml

from greenheart.simulation.technologies.iron.load_top_down_coeffs import load_top_down_coeffs


CD = Path(__file__).parent

# Get model locations loaded up to refer to
model_locs_fp = CD / "../model_locations.yaml"
model_locs = load_yaml(model_locs_fp)

capital_costs = {}


def main(config):
    # Import 'top-down' costs
    top_down_coeffs = load_top_down_coeffs()

    model_year = 2022  # Rosner paper: All economic data in 2022 $

    start_year = config.params["operational_year"]
    end_year = start_year + config.params["plant_life"]
    end_year = min(end_year, top_down_coeffs["years"][-1])
    td_start_idx = np.where(top_down_coeffs["years"] == start_year)[0][0]
    td_end_idx = np.where(top_down_coeffs["years"] == end_year)[0][0]

    # Get plant performances into data frame/series with performance names as index
    perf_df = config.performance.performances_df.set_index("Name")
    perf_ds = perf_df.loc[:, "Model"]

    plant_capacity_mtpy = config.params["plant_capacity_mtpy"]  # In metric tonnes per year

    # Convert iron to steel if needed
    if config.params["capacity_denominator"] == "iron":
        steel_cap = perf_ds["Steel Production"]
        iron_cap = perf_ds["Pig Iron Production"]
        plant_capacity_mtpy *= steel_cap / iron_cap

    lcoh = config.params["lcoh"]

    # Set up dataframe to store costs
    cols = ["Product", "Name", "Type", "Unit", config.site["name"]]
    costs_df = pd.DataFrame([], columns=cols)

    # If re-fitting the model, load an inputs dataframe, otherwise, load up the coeffs
    if config.model["refit_coeffs"]:
        input_df = pd.read_csv(CD / config.model["inputs_fp"])
        products = np.unique(input_df.loc[:, "Product"].values)
        coeff_df = pd.read_csv(CD / config.model["coeffs_fp"], index_col=0)

        for product in products:
            prod_rows = np.where(input_df.loc[:, "Product"].values == product)[0]
            prod_df = input_df.iloc[prod_rows, :]
            product_col = np.where(coeff_df.columns.values == product)[0]

            remove_rows = ["Capacity Factor", "Pig Iron", "Steel Liquid"]
            keep_rows = np.where(
                np.logical_not([i in remove_rows for i in prod_df.loc[:, "Name"].values])
            )
            prod_df = prod_df.iloc[keep_rows]

            keys = prod_df.iloc[:, 1]  # Extract name
            values = prod_df.iloc[:, 4:19]  # Extract values for cost re-fitting

            # Create dictionary with keys for name and arrays of values
            array_dict = {
                key: np.array(row)
                for key, row in zip(keys, values.itertuples(index=False, name=None))
            }

            # This determines that costs are a function of steel slab output
            x = np.log(array_dict["Steel Slab"])

            del array_dict["Steel Slab"]

            for key in array_dict:
                y = np.log(array_dict[key])
                # Fit the curve
                coeffs = np.polyfit(x, y, 1)

                # Extract coefficients
                a = np.exp(coeffs[1])
                b = coeffs[0]

                # Ensure all values are real
                a = 0 if np.isnan(a) else a
                b = 0 if np.isnan(b) else b

                # Store the parameters in the coeff dataframe
                lin_row = np.where(
                    np.logical_and(coeff_df.index.values == key, coeff_df.loc[:, "Coeff"] == "lin")
                )[0][0]
                exp_row = np.where(
                    np.logical_and(coeff_df.index.values == key, coeff_df.loc[:, "Coeff"] == "exp")
                )[0][0]
                coeff_df.iloc[lin_row, product_col] = a
                coeff_df.iloc[exp_row, product_col] = b

        coeff_df.to_csv(CD / config.model["coeffs_fp"])
    coeff_df = pd.read_csv(CD / config.model["coeffs_fp"], index_col=[0, 1, 2, 3])
    product = config.product_selection

    prod_coeffs = coeff_df[[product]].reset_index()

    # Add unique capital items based on the "Name" column for product
    for item_name in prod_coeffs[prod_coeffs["Type"] == "capital"]["Name"].unique():
        # Filter for this item and get the lin and exp coefficients
        item_data = prod_coeffs[
            (prod_coeffs["Name"] == item_name) & (prod_coeffs["Type"] == "capital")
        ]
        lin_coeff = item_data[item_data["Coeff"] == "lin"][product].values[0]
        exp_coeff = item_data[item_data["Coeff"] == "exp"][product].values[0]

        # Calculate the capital cost for the item
        capital_costs[item_name] = lin_coeff * plant_capacity_mtpy**exp_coeff

    total_plant_cost = sum(capital_costs.values())

    for cost_name, cost in capital_costs.items():
        new_cost = [product, cost_name, "capital", str(model_year) + " $", cost]
        costs_df.loc[len(costs_df)] = new_cost

    # -------------------------------Fixed O&M Costs------------------------------

    # Import Peters opex model
    if config.model["refit_coeffs"]:
        input_df = pd.read_csv(CD / "../Peters" / model_locs["cost"]["Peters"]["inputs"])
        keys = input_df.iloc[:, 0]  # Extract name
        values = input_df.iloc[:, 3:16]  # Extract values for cost re-fitting

        # Create dictionary with keys for name and arrays of values
        array_dict = {
            key: np.array(row) for key, row in zip(keys, values.itertuples(index=False, name=None))
        }

        x = np.log(array_dict["Plant Size"])
        y = np.log(array_dict["Operating Labor"])

        # Fit the curve
        coeffs = np.polyfit(x, y, 1)

        # Extract coefficients
        Peters_coeffs_lin = np.exp(coeffs[1])
        Peters_coeffs_exp = coeffs[0]

    else:
        coeff_df = pd.read_csv(
            CD / "../Peters" / model_locs["cost"]["Peters"]["coeffs"], index_col=[0, 1, 2, 3]
        )
        Peters_coeffs = coeff_df["A"]
        Peters_coeffs_lin = Peters_coeffs.loc["Annual Operating Labor Cost", :, "lin"].values[0]
        Peters_coeffs_exp = Peters_coeffs.loc["Annual Operating Labor Cost", :, "exp"].values[0]

    # Peters model - employee-hours/day/process step * # of process steps
    fixed_costs = {}

    cost = (
        365
        * (
            prod_coeffs.loc[prod_coeffs["Name"] == "% Skilled Labor", product].values[0]
            / 100
            * np.mean(top_down_coeffs["Skilled Labor Cost"]["values"][td_start_idx:td_end_idx])
            + prod_coeffs.loc[prod_coeffs["Name"] == "% Unskilled Labor", product].values[0]
            / 100
            * np.mean(top_down_coeffs["Unskilled Labor Cost"]["values"][td_start_idx:td_end_idx])
        )
        * prod_coeffs.loc[prod_coeffs["Name"] == "Processing Steps", product].values[0]
        * Peters_coeffs_lin
        * (plant_capacity_mtpy / 365 * 1000) ** Peters_coeffs_exp
    )
    labor_cost_annual_operation = cost
    fixed_costs["labor_cost_annual_operation"] = cost

    cost = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Maintenance Labor Cost", product].values[0]
        * total_plant_cost
    )
    labor_cost_maintenance = cost
    fixed_costs["labor_cost_maintenance"] = cost

    cost = prod_coeffs.loc[
        prod_coeffs["Name"] == "Administrative & Support Labor Cost", product
    ].values[0] * (labor_cost_annual_operation + labor_cost_maintenance)
    labor_cost_admin_support = cost
    fixed_costs["labor_cost_admin_support"] = cost

    cost = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Property Tax & Insurance", product].values[0]
        * total_plant_cost
    )
    property_tax_insurance = cost
    fixed_costs["property_tax_insurance"] = cost

    cost = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Maintenance Materials", product].values[0]
        * plant_capacity_mtpy
    )
    maintenance_materials = cost
    fixed_costs["maintenance_materials"] = cost

    (
        labor_cost_annual_operation
        + labor_cost_maintenance
        + labor_cost_admin_support
        + property_tax_insurance
        + maintenance_materials
    )

    for cost_name, cost in fixed_costs.items():
        new_cost = [product, cost_name, "fixed opex", str(model_year) + " $ per year", cost]
        costs_df.loc[len(costs_df)] = new_cost

    # ---------------------- Owner's (Installation) Costs --------------------------
    if config.product_selection == "ng_dri" or "h2_dri" or "ng_dri_eaf" or "h2_dri_eaf":
        labor_cost_fivemonth = (
            5
            / 12
            * (labor_cost_annual_operation + labor_cost_maintenance + labor_cost_admin_support)
        )
    else:
        labor_cost_fivemonth = 0

    (
        prod_coeffs.loc[prod_coeffs["Name"] == "Maintenance Materials", product].values[0]
        * plant_capacity_mtpy
        / 12
    )
    non_fuel_consumables_onemonth = (
        plant_capacity_mtpy
        * (
            perf_ds["Raw Water Withdrawal"] * top_down_coeffs["Raw Water"]["values"][td_start_idx]
            + perf_ds["Lime"] * top_down_coeffs["Lime"]["values"][td_start_idx]
            + perf_ds["Carbon (Coke)"] * top_down_coeffs["Carbon"]["values"][td_start_idx]
            + perf_ds["Iron Ore"] * top_down_coeffs["Iron Ore Pellets"]["values"][td_start_idx]
            + perf_ds["Reformer Catalyst"]
            * top_down_coeffs["Reformer Catalyst"]["values"][td_start_idx]
        )
        / 12
    )

    (
        plant_capacity_mtpy
        * perf_ds["Slag"]
        * top_down_coeffs["Slag Disposal"]["values"][td_start_idx]
        / 12
    )

    (
        plant_capacity_mtpy
        * (
            perf_ds["Hydrogen"] * lcoh * 1000
            + perf_ds["Natural Gas"] * top_down_coeffs["Natural Gas"]["values"][td_start_idx]
            + perf_ds["Electricity"] * top_down_coeffs["Electricity"]["values"][td_start_idx]
        )
        / 12
    )
    preproduction_cost = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Preproduction", product].values[0]
        * total_plant_cost
    )

    fuel_consumables_60day_supply_cost = non_fuel_consumables_onemonth * 12 / 365 * 60

    spare_parts_cost = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Spare Parts", product].values[0] * total_plant_cost
    )
    land_cost = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Land", product].values[0] * plant_capacity_mtpy
    )
    misc_owners_costs = (
        prod_coeffs.loc[prod_coeffs["Name"] == "Other Owners's Costs", product].values[0]
        * total_plant_cost
    )

    installation_cost = (
        labor_cost_fivemonth
        + preproduction_cost
        + fuel_consumables_60day_supply_cost
        + spare_parts_cost
        + misc_owners_costs
    )

    new_cost = [product, "Land cost", "other", str(model_year) + " $ per year", land_cost]
    costs_df.loc[len(costs_df)] = new_cost

    new_cost = [
        product,
        "Installation cost",
        "other",
        str(model_year) + " $ per year",
        installation_cost,
    ]
    costs_df.loc[len(costs_df)] = new_cost

    return costs_df
