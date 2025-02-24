"""
Direct Reduced Grade (DR-Grade) iron ore model developed by Jonathan Martin at NREL
in conjunction with UMN-Duluth's NRRI (Brett Spigarelli, Rod Johnson, Matt Aro)
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


def main(config):
    # Import 'top-down' costs
    load_top_down_coeffs()

    # --------------- capital items ----------------
    # If re-fitting the model, load an inputs dataframe, otherwise, load up the coeffs
    if config.model["refit_coeffs"]:
        input_df = pd.read_csv(CD / config.model["inputs_fp"])

        # Right now all the performance modeling is constant
        input_df.insert(3, "Coeff", np.full((len(input_df),), "constant"))

        coeff_df = input_df
        coeff_df.to_csv(CD / config.model["coeffs_fp"])

    else:
        coeff_df = pd.read_csv(CD / config.model["coeffs_fp"], index_col=0)

    prod = config.product_selection
    site = config.site["name"]

    rows = np.where(coeff_df.loc[:, "Product"] == prod)[0]
    col = np.where(coeff_df.columns == site)[0]
    cols = [0, 1, 2, 3, 4]
    cols.extend(list(col))

    if len(rows) == 0:
        raise ValueError(f'Product "{prod}" not found in coeffs data!')
    if len(cols) == 0:
        raise ValueError(f'Site "{site}" not found in coeffs data!')

    prod_df = coeff_df.iloc[rows, cols]

    # Convert per unit wet long ton to per unit dry metric tonne
    prod_df = prod_df.set_index("Name")
    for name, item in prod_df.iterrows():
        unit = item["Unit"]
        if "per wlt" in unit:
            LT_idx = unit.index("per wlt")
            if len(unit) == LT_idx + 7:
                new_unit = unit[:LT_idx] + "per mt"
            else:
                new_unit = unit[:LT_idx] + "per mt" + unit[(LT_idx + 7) :]
            LT_value = item[site]
            mt_value = (
                LT_value
                / 1.016047  # Long tons to metric tons
                / 0.98
            )  # Wet tons to dry tons (2% moisture)
            prod_df.loc[name, site] = mt_value
            prod_df.loc[name, "Unit"] = new_unit
        if "wltpy" in unit:
            LT_idx = unit.index("wltpy")
            if len(unit) == LT_idx + 5:
                new_unit = unit[:LT_idx] + "mtpy"
            else:
                new_unit = unit[:LT_idx] + "mtpy" + unit[(LT_idx + 5) :]
            LT_value = item[site]
            mt_value = (
                LT_value
                * 1.016047  # Long tons to metric tons
                * 0.98
            )  # Wet tons to dry tons (2% moisture)
            prod_df.loc[name, site] = mt_value
            prod_df.loc[name, "Unit"] = new_unit
    prod_df = prod_df.reset_index().set_index("Product").reset_index()

    # Right now, the there is no need to scale the coefficients.
    # cost_df will contain the same values as coeff_df
    # This will change when scaling/extrapolating mining operations
    prod_df = coeff_df.iloc[rows, cols]
    length, width = prod_df.shape
    cost_cols = list(prod_df.columns.values)
    cost_cols.remove("Coeff")
    col_idxs = list(range(width))
    col_idxs.remove(3)
    cost_df = pd.DataFrame([], columns=cost_cols)
    for row in range(length):
        if prod_df.iloc[row, 3] == "constant":
            cost_df.loc[len(cost_df)] = prod_df.iloc[row, col_idxs]

    return cost_df
