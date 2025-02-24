"""
Direct Reduced Iron (DRI) model developed by Rosner et al.
Energy Environ. Sci., 2023, 16, 4121
doi.org/10.1039/d3ee01077e
"""

import copy
from pathlib import Path

import numpy as np
import pandas as pd


CD = Path(__file__).parent


def main(config):
    # If re-fitting the model, load an inputs dataframe, otherwise, load up the coeffs
    if config.model["refit_coeffs"]:
        input_df = pd.read_csv(CD / config.model["inputs_fp"])

        # Right now all the performance modeling is linear
        input_df.insert(3, "Coeff", np.full((len(input_df),), "lin"))

        # Right now, no curve fitting - just copy input DataFrame to make coeff DataFrame
        coeff_df = copy.deepcopy(input_df)

        coeff_df.to_csv(CD / config.model["coeffs_fp"])
    else:
        coeff_df = pd.read_csv(CD / config.model["coeffs_fp"], index_col=0)

    prod = config.product_selection
    site = "Model"

    rows = np.where(coeff_df.loc[:, "Product"] == prod)[0]
    col = np.where(coeff_df.columns == site)[0]
    cols = [0, 1, 2, 3, 4]
    cols.extend(list(col))

    if len(rows) == 0:
        raise ValueError(f'Product "{prod}" not found in coeffs data!')
    if len(cols) == 0:
        raise ValueError(f'Site "{site}" not found in coeffs data!')

    prod_df = coeff_df.iloc[rows, cols]

    # Convert per unit steel to per unit iron
    if config.params["capacity_denominator"] == "iron":
        prod_df = prod_df.set_index("Name")
        steel_cap = prod_df.loc["Steel Production", "Model"]
        iron_cap = prod_df.loc["Pig Iron Production", "Model"]
        for name, item in prod_df.iterrows():
            unit = item["Unit"]
            if "steel" in unit:
                steel_idx = unit.index("steel")
                if len(unit) == steel_idx + 5:
                    new_unit = unit[:steel_idx] + "iron"
                else:
                    new_unit = unit[:steel_idx] + "iron" + unit[steel_idx + 5 :]
                steel_value = item["Model"]
                iron_value = steel_value * steel_cap / iron_cap
                prod_df.loc[name, "Model"] = iron_value
                prod_df.loc[name, "Unit"] = new_unit
        prod_df = prod_df.reset_index().set_index("Product").reset_index()

    # Right now, the there is no need to scale the coefficients.
    # perf_df will contain the same values as coeff_df
    # This will change when scaling/extrapolating mining operations
    length, width = prod_df.shape
    perf_cols = list(prod_df.columns.values)
    perf_cols.remove("Coeff")
    col_idxs = list(range(width))
    col_idxs.remove(3)
    perf_df = pd.DataFrame([], columns=perf_cols)
    for row in range(length):
        if prod_df.iloc[row, 3] == "lin":
            perf_df.loc[len(perf_df)] = prod_df.iloc[row, col_idxs]

    return perf_df
