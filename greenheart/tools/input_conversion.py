'''
Converts input files between different types
'''


import os
from pathlib import Path
import pandas as pd
import yaml


def csv_to_yaml(filepath):
    # Read csv into dataframe
    temp_df = pd.read_csv(filepath, index_col=0)
    # Create dictionary from dataframe
    temp_dict = temp_df.to_dict(orient='index')
    # Define yaml filepath based on original filepath
    yaml_filepath = filepath[:-3] + "yaml"
    # Open yamlfile in overwrite mode, create new file if does not exist
    yaml_file = open(yaml_filepath, mode='w+')
    # Dump temp_dict into yaml file and close file
    yaml.dump(temp_dict, yaml_file, default_flow_style=False)
    yaml_file.close()