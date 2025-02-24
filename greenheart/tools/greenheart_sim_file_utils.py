from greenheart.tools.data_loading_utils import (
    load_dill_pickle,
    check_create_folder,
    dump_data_to_pickle,
)


# from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig


def save_physics_results_greenheart_setup(config, wind_cost_results):
    # from setup_greenheart_simulation() if config.save_pre_iron (line 556)
    lat = config.hopp_config["site"]["data"]["lat"]
    lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config["site"]["data"]["year"]
    site_res_id = f"{lat:.3f}_{lon:.3f}_{year:d}"

    # Write outputs needed for future runs in .pkls
    pkl_fn = site_res_id + ".pkl"
    output_names = ["config", "wind_cost_results"]
    output_data = [config, wind_cost_results]
    output_data_dict = dict(zip(output_names, output_data))

    for output_name, data in output_data_dict.items():
        path = config.run_full_simulation_fn + "/" + output_name + "/"
        check_create_folder(path)
        output_filepath = path + pkl_fn
        dump_data_to_pickle(data, output_filepath)


def load_physics_greenheart_setup(config):
    lat = config.hopp_config["site"]["data"]["lat"]
    lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config["site"]["data"]["year"]
    site_res_id = f"{lat:.3f}_{lon:.3f}_{year:d}"

    # Read in outputs from previously-saved .pkls
    pkl_fn = site_res_id + ".pkl"
    config_fpath = config.run_full_simulation_fn + "/" + "config" + "/" + pkl_fn
    wind_cost_fpath = config.run_full_simulation_fn + "/" + "wind_cost_results" + "/" + pkl_fn
    config = load_dill_pickle(config_fpath)
    wind_cost_results = load_dill_pickle(wind_cost_fpath)
    return config, wind_cost_results


def save_physics_results_greenheart_simulation(
    config,
    lcoh,
    lcoe,
    electrolyzer_physics_results,
    wind_annual_energy_kwh,
    solar_pv_annual_energy_kwh,
    energy_shortfall_hopp,
):
    # from setup_greenheart_simulation() if config.save_pre_iron (line 1071)
    lat = config.hopp_config["site"]["data"]["lat"]
    lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config["site"]["data"]["year"]
    site_res_id = f"{lat:.3f}_{lon:.3f}_{year:d}"

    # Write outputs needed for future runs in .pkls
    pkl_fn = site_res_id + ".pkl"
    output_names = [
        "lcoe",
        "lcoh",
        "electrolyzer_physics_results",
        "wind_annual_energy_kwh",
        "solar_pv_annual_energy_kwh",
        "energy_shortfall_hopp",
    ]
    output_data = [
        lcoe,
        lcoh,
        electrolyzer_physics_results,
        wind_annual_energy_kwh,
        solar_pv_annual_energy_kwh,
    ]
    output_data_dict = dict(zip(output_names, output_data))
    for output_name, data in output_data_dict.items():
        path = config.run_full_simulation_fn + "/" + output_name + "/"
        check_create_folder(path)
        output_filepath = path + pkl_fn
        dump_data_to_pickle(data, output_filepath)


def load_physics_greenheart_simulation(config):
    lat = config.hopp_config["site"]["data"]["lat"]
    lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config["site"]["data"]["year"]
    site_res_id = f"{lat:.3f}_{lon:.3f}_{year:d}"

    # Read in outputs from previously-saved .pkls
    pkl_fn = site_res_id + ".pkl"
    lcoh_fpath = config.run_full_simulation_fn + "/" + "lcoh" + "/" + pkl_fn
    lcoe_fpath = config.run_full_simulation_fn + "/" + "lcoe" + "/" + pkl_fn
    elec_phys_fpath = (
        config.run_full_simulation_fn + "/" + "electrolyzer_physics_results" + "/" + pkl_fn
    )
    wind_fpath = config.run_full_simulation_fn + "/" + "wind_annual_energy_kwh" + "/" + pkl_fn
    solar_fpath = config.run_full_simulation_fn + "/" + "solar_pv_annual_energy_kwh" + "/" + pkl_fn
    lcoh = load_dill_pickle(lcoh_fpath)
    lcoe = load_dill_pickle(lcoe_fpath)
    electrolyzer_physics_results = load_dill_pickle(elec_phys_fpath)
    wind_annual_energy_kwh = load_dill_pickle(wind_fpath)
    solar_pv_annual_energy_kwh = load_dill_pickle(solar_fpath)
    return (
        lcoh,
        lcoe,
        electrolyzer_physics_results,
        wind_annual_energy_kwh,
        solar_pv_annual_energy_kwh,
    )


def save_iron_ore_results(
    config, iron_ore_config, iron_ore_performance, iron_ore_costs, iron_ore_finance
):
    # lat = config.hopp_config["site"]["data"]["lat"]
    # lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config["site"]["data"]["year"]
    perf_df = iron_ore_performance.performances_df.set_index("Name")
    perf_ds = perf_df.loc[:, iron_ore_config["iron_ore"]["site"]["name"]]
    lat = perf_ds["Latitude"]
    lon = perf_ds["Longitude"]

    site_res_id = f"{lat:.3f}_{lon:.3f}_{year:d}"
    pkl_fn = site_res_id + ".pkl"
    output_names = ["iron_ore_performance", "iron_ore_costs", "iron_ore_finance"]
    output_data = [iron_ore_performance, iron_ore_costs, iron_ore_finance]
    output_data_dict = dict(zip(output_names, output_data))
    for output_name, data in output_data_dict.items():
        path = config.iron_out_fn + "/" + output_name + "/"
        check_create_folder(path)
        output_filepath = path + pkl_fn
        dump_data_to_pickle(data, output_filepath)


def save_iron_results(config, iron_performance, iron_costs, iron_finance, iron_CI=None):
    lat = config.hopp_config["site"]["data"]["lat"]
    lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config["site"]["data"]["year"]
    site_res_id = f"{lat:.3f}_{lon:.3f}_{year:d}"
    pkl_fn = site_res_id + ".pkl"

    output_names = ["iron_performance", "iron_costs", "iron_finance"]
    output_data = [iron_performance, iron_costs, iron_finance]
    if iron_CI is not None:
        output_names.append("iron_CI")
        output_data.append(iron_CI)
    output_data_dict = dict(zip(output_names, output_data))
    for output_name, data in output_data_dict.items():
        path = config.iron_out_fn + "/" + output_name + "/"
        check_create_folder(path)
        output_filepath = path + pkl_fn
        dump_data_to_pickle(data, output_filepath)
