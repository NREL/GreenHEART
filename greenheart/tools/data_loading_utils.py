import pandas as pd
import os
import dill

def check_create_folder(filepath):
    if not os.path.isdir(filepath):
        os.makedirs(filepath,exist_ok=True)
        already_exists = False
    else:
        already_exists = True

    return already_exists

def dump_data_to_pickle(data,filepath):
    with open(filepath,"wb") as f:
        dill.dump(data,f)

def load_dill_pickle(filepath):
    with open(filepath,"rb") as f:
        data = dill.load(f)
    return data
