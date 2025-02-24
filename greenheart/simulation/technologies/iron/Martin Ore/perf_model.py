"""
Direct Reduced Iron (DRI) model developed by Rosner et al.
Energy Environ. Sci., 2023, 16, 4121
doi.org/10.1039/d3ee01077e
"""

from pathlib import Path

import numpy as np
import pandas as pd


CD = Path(__file__).parent


def main(config):
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
        if "LT" in unit:
            LT_idx = unit.index("LT")
            if len(unit) == LT_idx + 2:
                new_unit = unit[:LT_idx] + "mt"
            else:
                new_unit = unit[:LT_idx] + "mt" + unit[(LT_idx + 2) :]
            LT_value = item[site]
            mt_value = (
                LT_value
                / 1.016047  # Long tons to metric tons
                / 0.98
            )  # Wet tons to dry tons (2% moisture)
            prod_df.loc[name, site] = mt_value
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
        if prod_df.iloc[row, 3] == "constant":
            perf_df.loc[len(perf_df)] = prod_df.iloc[row, col_idxs]

    return perf_df
