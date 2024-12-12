"""
This file is based on the WISDEM file of the same name: https://github.com/WISDEM/WISDEM
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio


def save_data(fname, prob, npz_file=True, mat_file=True, xls_file=True):
    # Remove file extension
    froot = Path(fname).with_suffix("")

    # Get all OpenMDAO inputs and outputs into a dictionary
    var_dict = prob.model.list_inputs(prom_name=True, units=True, desc=True, out_stream=None)
    out_dict = prob.model.list_outputs(prom_name=True, units=True, desc=True, out_stream=None)
    var_dict.extend(out_dict)

    # Pickle the full archive so that we can load it back in if we need
    with froot.with_suffix(".pkl").open("wb") as f:
        pickle.dump(var_dict, f)

    # Reduce to variables we can save for matlab or python
    if npz_file or mat_file:
        array_dict = {}
        for k in range(len(var_dict)):
            unit_str = var_dict[k][1]["units"]
            if unit_str is None or unit_str == "Unavailable":
                unit_str = ""
            elif len(unit_str) > 0:
                unit_str = "_" + unit_str

            iname = var_dict[k][1]["prom_name"] + unit_str
            value = var_dict[k][1]["val"]

            if iname in array_dict:
                continue

            if isinstance(value, (np.ndarray, float, int, np.float64, np.int64)):
                array_dict[iname] = value
            elif isinstance(value, bool):
                array_dict[iname] = np.bool_(value)
            elif isinstance(value, str):
                array_dict[iname] = np.str_(value)
            elif isinstance(value, list):
                temp_val = np.empty(len(value), dtype=object)
                temp_val[:] = value[:]
                array_dict[iname] = temp_val
            # else:
            #    print(var_dict[k])

    # Save to numpy compatible
    if npz_file:
        kwargs = {key: array_dict[key] for key in array_dict.keys()}
        np.savez_compressed(froot.with_suffix(".npz"), **kwargs)

    # Save to matlab compatible
    if mat_file:
        sio.savemat(froot.with_suffix(".mat"), array_dict, long_field_names=True)

    if xls_file:
        data = {}
        data["variables"] = []
        data["units"] = []
        data["values"] = []
        data["description"] = []
        for k in range(len(var_dict)):
            unit_str = var_dict[k][1]["units"]
            if unit_str is None:
                unit_str = ""

            iname = var_dict[k][1]["prom_name"]
            if iname in data["variables"]:
                continue

            data["variables"].append(iname)
            data["units"].append(unit_str)
            data["values"].append(var_dict[k][1]["val"])
            data["description"].append(var_dict[k][1]["desc"])
        df = pd.DataFrame(data)
        df.to_excel(froot.with_suffix(".xlsx"), index=False)
        df.to_csv(froot.with_suffix(".csv"), index=False)


def load_data(fname, prob):
    # Remove file extension
    froot = Path(fname).with_suffix("")

    # Load in the pickled data
    with froot.with_suffix(".pkl").open("rb") as f:
        var_dict = pickle.load(f)

    # Store into Problem object
    for k in range(len(var_dict)):
        iname = var_dict[k][0]
        iname2 = var_dict[k][1]["prom_name"]
        value = var_dict[k][1]["val"]
        try:
            prob.set_val(iname, value)
        except:  # FIXME: What is this catching? Delete comment when resolved  # noqa: E722
            pass
        try:
            prob.set_val(iname2, value)
        except:  # FIXME: What is this catching? Delete comment when resolved  # noqa: E722
            pass

    return prob
