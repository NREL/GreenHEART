from __future__ import annotations

import copy
import warnings
from pathlib import Path

import numpy as np
import ORBIT as orbit
import pandas as pd
import numpy_financial as npf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as patches
from hopp.utilities import load_yaml
from hopp.simulation import HoppInterface
from hopp.tools.dispatch import plot_tools
from hopp.simulation.technologies.resource.greet_data import GREETData
from hopp.simulation.technologies.resource.cambium_data import CambiumData

from .finance import adjust_orbit_costs


"""
This function returns the ceiling of a/b (rounded to the nearest greater integer).
The function was copied from https://stackoverflow.com/a/17511341/5128616
"""


def ceildiv(a, b):
    return -(a // -b)


def convert_relative_to_absolute_path(config_filepath, resource_filepath):
    if resource_filepath == "":
        return ""
    else:
        abs_config_filepath = Path(config_filepath).absolute().parent
        return abs_config_filepath / resource_filepath


# Function to load inputs
def get_inputs(
    filename_hopp_config,
    filename_greenheart_config,
    filename_orbit_config,
    filename_turbine_config,
    filename_floris_config=None,
    verbose=False,
    show_plots=False,
    save_plots=False,
):
    ############### load turbine inputs from yaml

    # load turbine inputs
    turbine_config = load_yaml(filename_turbine_config)

    # load hopp inputs
    hopp_config = load_yaml(filename_hopp_config)

    # load eco inputs
    greenheart_config = load_yaml(filename_greenheart_config)

    # convert relative filepath to absolute for HOPP ingestion
    hopp_config["site"]["solar_resource_file"] = convert_relative_to_absolute_path(
        filename_hopp_config, hopp_config["site"]["solar_resource_file"]
    )
    hopp_config["site"]["wind_resource_file"] = convert_relative_to_absolute_path(
        filename_hopp_config, hopp_config["site"]["wind_resource_file"]
    )
    hopp_config["site"]["wave_resource_file"] = convert_relative_to_absolute_path(
        filename_hopp_config, hopp_config["site"]["wave_resource_file"]
    )
    hopp_config["site"]["grid_resource_file"] = convert_relative_to_absolute_path(
        filename_hopp_config, hopp_config["site"]["grid_resource_file"]
    )

    ################ load plant inputs from yaml
    if filename_orbit_config is not None:
        orbit_config = orbit.load_config(filename_orbit_config)

        # print plant inputs if desired
        if verbose:
            print("\nPlant configuration:")
            for key in orbit_config.keys():
                print(key, ": ", orbit_config[key])

        # check that orbit and hopp inputs are compatible
        if (
            orbit_config["plant"]["capacity"]
            != hopp_config["technologies"]["wind"]["num_turbines"]
            * hopp_config["technologies"]["wind"]["turbine_rating_kw"]
            * 1e-3
        ):
            raise (ValueError("Provided ORBIT and HOPP wind plant capacities do not match"))

    # update floris_config file with correct input from other files
    # load floris inputs
    if (
        hopp_config["technologies"]["wind"]["model_name"] == "floris"
    ):  # TODO replace elements of the file
        if filename_floris_config is None:
            raise (ValueError("floris input file must be specified."))
        else:
            floris_config = load_yaml(filename_floris_config)
            floris_config.update({"farm": {"turbine_type": turbine_config}})
    else:
        floris_config = None

    # print turbine inputs if desired
    if verbose:
        print("\nTurbine configuration:")
        for key in turbine_config.keys():
            print(key, ": ", turbine_config[key])

    ############## provide custom layout for ORBIT and FLORIS if desired
    if filename_orbit_config is not None:
        if orbit_config["plant"]["layout"] == "custom":
            # generate ORBIT config from floris layout
            for i, x in enumerate(floris_config["farm"]["layout_x"]):
                floris_config["farm"]["layout_x"][i] = x + 400

            layout_config, layout_data_location = convert_layout_from_floris_for_orbit(
                floris_config["farm"]["layout_x"],
                floris_config["farm"]["layout_y"],
                save_config=True,
            )

            # update orbit_config with custom layout
            # orbit_config = orbit.core.library.extract_library_data(
            #     orbit_config, additional_keys=layout_config
            # )
            orbit_config["array_system_design"]["location_data"] = layout_data_location

    # if hybrid plant, adjust hybrid plant capacity to include all technologies
    total_hybrid_plant_capacity_mw = 0.0
    for tech in hopp_config["technologies"].keys():
        if tech == "grid":
            continue
        elif tech == "wind":
            total_hybrid_plant_capacity_mw += (
                hopp_config["technologies"][tech]["num_turbines"]
                * hopp_config["technologies"][tech]["turbine_rating_kw"]
                * 1e-3
            )
        elif tech == "pv":
            total_hybrid_plant_capacity_mw += (
                hopp_config["technologies"][tech]["system_capacity_kw"] * 1e-3
            )
        elif tech == "wave":
            total_hybrid_plant_capacity_mw += (
                hopp_config["technologies"][tech]["num_devices"]
                * hopp_config["technologies"][tech]["device_rating_kw"]
                * 1e-3
            )

    # initialize dict for hybrid plant
    if filename_orbit_config is not None:
        if total_hybrid_plant_capacity_mw != orbit_config["plant"]["capacity"]:
            orbit_hybrid_electrical_export_config = copy.deepcopy(orbit_config)
            orbit_hybrid_electrical_export_config["plant"]["capacity"] = (
                total_hybrid_plant_capacity_mw
            )
            # allow orbit to set num_turbines later based on the new hybrid capacity and
            # turbinerating
            orbit_hybrid_electrical_export_config["plant"].pop("num_turbines")
        else:
            orbit_hybrid_electrical_export_config = {}

    if verbose:
        print(f"Total hybrid plant rating calculated: {total_hybrid_plant_capacity_mw} MW")

    if filename_orbit_config is None:
        orbit_config = None
        orbit_hybrid_electrical_export_config = {}

    ############## return all inputs

    return (
        hopp_config,
        greenheart_config,
        orbit_config,
        turbine_config,
        floris_config,
        orbit_hybrid_electrical_export_config,
    )


def convert_layout_from_floris_for_orbit(turbine_x, turbine_y, save_config=False):
    turbine_x_km = (np.array(turbine_x) * 1e-3).tolist()
    turbine_y_km = (np.array(turbine_y) * 1e-3).tolist()

    # initialize dict with data for turbines
    turbine_dict = {
        "id": list(range(0, len(turbine_x))),
        "substation_id": ["OSS"] * len(turbine_x),
        "name": list(range(0, len(turbine_x))),
        "longitude": turbine_x_km,
        "latitude": turbine_y_km,
        "string": [0] * len(turbine_x),  # can be left empty
        "order": [0] * len(turbine_x),  # can be left empty
        "cable_length": [0] * len(turbine_x),
        "bury_speed": [0] * len(turbine_x),
    }
    string_counter = -1
    order_counter = 0
    for i in range(0, len(turbine_x)):
        if turbine_x[i] - 400 == 0:
            string_counter += 1
            order_counter = 0

        turbine_dict["order"][i] = order_counter
        turbine_dict["string"][i] = string_counter

        order_counter += 1

    # initialize dict with substation information
    substation_dict = {
        "id": "OSS",
        "substation_id": "OSS",
        "name": "OSS",
        "longitude": np.min(turbine_x_km) - 200 * 1e-3,
        "latitude": np.average(turbine_y_km),
        "string": "",  # can be left empty
        "order": "",  # can be left empty
        "cable_length": "",
        "bury_speed": "",
    }

    # combine turbine and substation dicts
    for key in turbine_dict.keys():
        # turbine_dict[key].append(substation_dict[key])
        turbine_dict[key].insert(0, substation_dict[key])

    # add location data
    file_name = "osw_cable_layout"
    save_location = Path("./input/project/plant/").resolve()
    # turbine_dict["array_system_design"]["location_data"] = data_location
    if save_config:
        if not save_location.exists():
            save_location.mkdir(parents=True)
        # create pandas data frame
        df = pd.DataFrame.from_dict(turbine_dict)

        # df.drop("index")
        df.set_index("id")

        # save to csv
        df.to_csv(save_location / f"{file_name}.csv", index=False)

    return turbine_dict, file_name


def visualize_plant(
    hopp_config,
    greenheart_config,
    turbine_config,
    wind_cost_outputs,
    hopp_results,
    platform_results,
    desal_results,
    h2_storage_results,
    electrolyzer_physics_results,
    design_scenario,
    colors,
    plant_design_number,
    show_plots=False,
    save_plots=False,
    output_dir="./output/",
):
    if isinstance(output_dir, str):
        output_dir = Path(output_dir).resolve()
    # save plant sizing to dict
    component_areas = {}

    plt.rcParams.update({"font.size": 7})

    if hopp_config["technologies"]["wind"]["model_name"] != "floris":
        msg = (
            f"`visualize_plant()` only works with the 'floris' wind model, `model_name`"
            f" {hopp_config['technologies']['wind']['model_name']} has been specified"
        )
        raise NotImplementedError(msg)

    # set colors
    turbine_rotor_color = colors[0]
    turbine_tower_color = colors[1]
    pipe_color = colors[2]
    cable_color = colors[8]
    electrolyzer_color = colors[4]
    desal_color = colors[9]
    h2_storage_color = colors[6]
    substation_color = colors[7]
    equipment_platform_color = colors[1]
    compressor_color = colors[0]
    if hopp_config["site"]["solar"]:
        solar_color = colors[2]
    if hopp_config["site"]["wave"]:
        wave_color = colors[8]
    battery_color = colors[8]

    # set hatches
    solar_hatch = "//"
    wave_hatch = "\\\\"
    battery_hatch = "+"
    electrolyzer_hatch = "///"
    desalinator_hatch = "xxxx"

    # Views
    # offshore plant, onshore plant, offshore platform, offshore turbine

    # get plant location

    # get shore location

    # get cable/pipe locations
    if design_scenario["wind_location"] == "offshore":
        # ORBIT gives coordinates in km, convert to m for (val / 1e3)

        cable_array_points = (
            wind_cost_outputs.orbit_project.phases["ArraySystemDesign"].coordinates * 1e3
        )
        pipe_array_points = (
            wind_cost_outputs.orbit_project.phases["ArraySystemDesign"].coordinates * 1e3
        )

        # get turbine tower base diameter
        tower_base_diameter = wind_cost_outputs.orbit_project.config["turbine"]["tower"][
            "section_diameters"
        ][0]  # in m
        tower_base_radius = tower_base_diameter / 2.0

        # get turbine locations
        turbine_x = (
            wind_cost_outputs.orbit_project.phases["ArraySystemDesign"].turbines_x.flatten() * 1e3
        )
        turbine_x = turbine_x[~np.isnan(turbine_x)]
        turbine_y = (
            wind_cost_outputs.orbit_project.phases["ArraySystemDesign"].turbines_y.flatten() * 1e3
        )
        turbine_y = turbine_y[~np.isnan(turbine_y)]

        # get offshore substation location and dimensions (treated as center)
        substation_x = wind_cost_outputs.orbit_project.phases["ArraySystemDesign"].oss_x * 1e3
        substation_y = wind_cost_outputs.orbit_project.phases["ArraySystemDesign"].oss_y * 1e3

        # [m] just based on a large substation
        # (https://www.windpowerengineering.com/making-modern-offshore-substation/)
        # since the dimensions are not available in ORBIT
        substation_side_length = 20

        # get equipment platform location and dimensions
        equipment_platform_area = platform_results["toparea_m2"]
        equipment_platform_side_length = np.sqrt(equipment_platform_area)

        # [m] (treated as center)
        equipment_platform_x = (
            substation_x - substation_side_length - equipment_platform_side_length / 2
        )
        equipment_platform_y = substation_y

        # get platform equipment dimensions
        if design_scenario["electrolyzer_location"] == "turbine":
            # equipment_footprint_m2
            desal_equipment_area = desal_results["per_turb_equipment_footprint_m2"]
        elif design_scenario["electrolyzer_location"] == "platform":
            desal_equipment_area = desal_results["equipment_footprint_m2"]
        else:
            desal_equipment_area = 0

        desal_equipment_side = np.sqrt(desal_equipment_area)

        # get pipe points
        np.array([substation_x - 1000, substation_x])
        np.array([substation_y, substation_y])

        # get cable points

    else:
        turbine_x = np.array(
            hopp_config["technologies"]["wind"]["floris_config"]["farm"]["layout_x"]
        )
        turbine_y = np.array(
            hopp_config["technologies"]["wind"]["floris_config"]["farm"]["layout_y"]
        )
        cable_array_points = []

    # wind farm area
    turbine_length_x = np.max(turbine_x) - np.min(turbine_x)
    turbine_length_y = np.max(turbine_y) - np.min(turbine_y)
    turbine_area = turbine_length_x * turbine_length_y

    # compressor side # not sized
    compressor_area = 25
    compressor_side = np.sqrt(compressor_area)

    # get turbine rotor diameter
    rotor_diameter = turbine_config["rotor_diameter"]  # in m
    rotor_radius = rotor_diameter / 2.0

    # set onshore substation dimensions
    onshore_substation_x_side_length = 127.25  # [m] based on 1 acre area https://www.power-technology.com/features/making-space-for-power-how-much-land-must-renewables-use/
    onshore_substation_y_side_length = 31.8  # [m] based on 1 acre area https://www.power-technology.com/features/making-space-for-power-how-much-land-must-renewables-use/
    onshore_substation_area = onshore_substation_x_side_length * onshore_substation_y_side_length

    if greenheart_config["h2_storage"]["type"] == "pressure_vessel":
        h2_storage_area = h2_storage_results["tank_footprint_m2"]
        h2_storage_side = np.sqrt(h2_storage_area)
    else:
        h2_storage_side = 0
        h2_storage_area = 0

    electrolyzer_area = electrolyzer_physics_results["equipment_footprint_m2"]
    if design_scenario["electrolyzer_location"] == "turbine":
        electrolyzer_area /= hopp_config["technologies"]["wind"]["num_turbines"]

    electrolyzer_side = np.sqrt(electrolyzer_area)

    # set onshore origin
    onshorex = 50
    onshorey = 50

    wind_buffer = np.min(turbine_x) - (onshorey + 3 * rotor_diameter + electrolyzer_side)
    if "pv" in hopp_config["technologies"].keys():
        wind_buffer -= np.sqrt(hopp_results["hybrid_plant"].pv.footprint_area)
    if "battery" in hopp_config["technologies"].keys():
        wind_buffer -= np.sqrt(hopp_results["hybrid_plant"].battery.footprint_area)
    if wind_buffer < 50:
        onshorey += wind_buffer - 50

    if design_scenario["wind_location"] == "offshore":
        origin_x = substation_x
        origin_y = substation_y
    else:
        origin_x = 0.0
        origin_y = 0.0

    ## create figure
    if design_scenario["wind_location"] == "offshore":
        fig, ax = plt.subplots(2, 2, figsize=(10, 6))
        ax_index_plant = (0, 0)
        ax_index_detail = (1, 0)
        ax_index_wind_plant = (0, 1)
        ax_index_turbine_detail = (1, 1)
    else:
        fig, ax = plt.subplots(1, 2, figsize=(10, 6))
        ax_index_plant = 0
        ax_index_wind_plant = 0
        ax_index_detail = 1
        ax_index_turbine_detail = False

    # plot the stuff

    # onshore plant | offshore plant
    # platform/substation | turbine

    ## add turbines
    def add_turbines(ax, turbine_x, turbine_y, radius, color):
        i = 0
        for x, y in zip(turbine_x, turbine_y):
            if i == 0:
                rlabel = "Wind turbine rotor"
                i += 1
            else:
                rlabel = None
            turbine_patch = patches.Circle(
                (x, y),
                radius=radius,
                color=color,
                fill=False,
                label=rlabel,
                zorder=10,
            )
            ax.add_patch(turbine_patch)

    add_turbines(ax[ax_index_wind_plant], turbine_x, turbine_y, rotor_radius, turbine_rotor_color)
    component_areas["turbine_area_m2"] = turbine_area
    # turbine_patch01_tower = patches.Circle((x, y), radius=tower_base_radius, color=turbine_tower_color, fill=False, label=tlabel, zorder=10)  # noqa: E501
    # ax[0, 1].add_patch(turbine_patch01_tower)
    if design_scenario["wind_location"] == "onshore":
        add_turbines(ax[ax_index_detail], turbine_x, turbine_y, rotor_radius, turbine_rotor_color)

    if ax_index_turbine_detail:
        # turbine_patch11_rotor = patches.Circle((turbine_x[0], turbine_y[0]), radius=rotor_radius, color=turbine_rotor_color, fill=False, label=None, zorder=10)  # noqa: E501
        tlabel = "Wind turbine tower"
        turbine_patch11_tower = patches.Circle(
            (turbine_x[0], turbine_y[0]),
            radius=tower_base_radius,
            color=turbine_tower_color,
            fill=False,
            label=tlabel,
            zorder=10,
        )
        # ax[1, 1].add_patch(turbine_patch11_rotor)
        ax[ax_index_turbine_detail].add_patch(turbine_patch11_tower)

    # add pipe array
    if design_scenario["transportation"] == "hvdc+pipeline" or (
        design_scenario["h2_storage_location"] != "turbine"
        and design_scenario["electrolyzer_location"] == "turbine"
    ):
        i = 0
        for point_string in pipe_array_points:
            if i == 0:
                label = "Array pipes"
                i += 1
            else:
                label = None
            ax[0, 1].plot(
                point_string[:, 0],
                point_string[:, 1] - substation_side_length / 2,
                ":",
                color=pipe_color,
                zorder=0,
                linewidth=1,
                label=label,
            )
            ax[1, 0].plot(
                point_string[:, 0],
                point_string[:, 1] - substation_side_length / 2,
                ":",
                color=pipe_color,
                zorder=0,
                linewidth=1,
                label=label,
            )
            ax[1, 1].plot(
                point_string[:, 0],
                point_string[:, 1] - substation_side_length / 2,
                ":",
                color=pipe_color,
                zorder=0,
                linewidth=1,
                label=label,
            )

    ## add cables
    if (len(cable_array_points) > 1) and (
        design_scenario["h2_storage_location"] != "turbine"
        or design_scenario["transportation"] == "hvdc+pipeline"
    ):
        i = 0
        for point_string in cable_array_points:
            if i == 0:
                label = "Array cables"
                i += 1
            else:
                label = None
            ax[0, 1].plot(
                point_string[:, 0],
                point_string[:, 1] + substation_side_length / 2,
                "-",
                color=cable_color,
                zorder=0,
                linewidth=1,
                label=label,
            )
            ax[1, 0].plot(
                point_string[:, 0],
                point_string[:, 1] + substation_side_length / 2,
                "-",
                color=cable_color,
                zorder=0,
                linewidth=1,
                label=label,
            )
            ax[1, 1].plot(
                point_string[:, 0],
                point_string[:, 1] + substation_side_length / 2,
                "-",
                color=cable_color,
                zorder=0,
                linewidth=1,
                label=label,
            )

    ## add offshore substation
    if design_scenario["wind_location"] == "offshore" and (
        design_scenario["h2_storage_location"] != "turbine"
        or design_scenario["transportation"] == "hvdc+pipeline"
    ):
        substation_patch01 = patches.Rectangle(
            (
                substation_x - substation_side_length,
                substation_y - substation_side_length / 2,
            ),
            substation_side_length,
            substation_side_length,
            fill=True,
            color=substation_color,
            label="Substation*",
            zorder=11,
        )
        substation_patch10 = patches.Rectangle(
            (
                substation_x - substation_side_length,
                substation_y - substation_side_length / 2,
            ),
            substation_side_length,
            substation_side_length,
            fill=True,
            color=substation_color,
            label="Substation*",
            zorder=11,
        )
        ax[0, 1].add_patch(substation_patch01)
        ax[1, 0].add_patch(substation_patch10)

        component_areas["offshore_substation_area_m2"] = substation_side_length**2

    ## add equipment platform
    if design_scenario["wind_location"] == "offshore" and (
        design_scenario["h2_storage_location"] == "platform"
        or design_scenario["electrolyzer_location"] == "platform"
    ):  # or design_scenario["transportation"] == "pipeline":
        equipment_platform_patch01 = patches.Rectangle(
            (
                equipment_platform_x - equipment_platform_side_length / 2,
                equipment_platform_y - equipment_platform_side_length / 2,
            ),
            equipment_platform_side_length,
            equipment_platform_side_length,
            color=equipment_platform_color,
            fill=True,
            label="Equipment platform",
            zorder=1,
        )
        equipment_platform_patch10 = patches.Rectangle(
            (
                equipment_platform_x - equipment_platform_side_length / 2,
                equipment_platform_y - equipment_platform_side_length / 2,
            ),
            equipment_platform_side_length,
            equipment_platform_side_length,
            color=equipment_platform_color,
            fill=True,
            label="Equipment platform",
            zorder=1,
        )
        ax[0, 1].add_patch(equipment_platform_patch01)
        ax[1, 0].add_patch(equipment_platform_patch10)

        component_areas["equipment_platform_area_m2"] = equipment_platform_area

    ## add hvdc cable
    if (
        design_scenario["transportation"] == "hvdc"
        or design_scenario["transportation"] == "hvdc+pipeline"
    ):
        ax[0, 0].plot(
            [onshorex + onshore_substation_x_side_length, 10000],
            [
                onshorey - onshore_substation_y_side_length,
                onshorey - onshore_substation_y_side_length,
            ],
            "--",
            color=cable_color,
            label="HVDC cable",
        )
        ax[0, 1].plot(
            [-50000, substation_x],
            [substation_y - 100, substation_y - 100],
            "--",
            color=cable_color,
            label="HVDC cable",
            zorder=0,
        )
        ax[1, 0].plot(
            [-5000, substation_x],
            [substation_y - 2, substation_y - 2],
            "--",
            color=cable_color,
            label="HVDC cable",
            zorder=0,
        )

    ## add onshore substation
    if (
        design_scenario["transportation"] == "hvdc"
        or design_scenario["transportation"] == "hvdc+pipeline"
    ):
        onshore_substation_patch00 = patches.Rectangle(
            (
                onshorex + 0.2 * onshore_substation_y_side_length,
                onshorey - onshore_substation_y_side_length * 1.2,
            ),
            onshore_substation_x_side_length,
            onshore_substation_y_side_length,
            fill=True,
            color=substation_color,
            label="Substation*",
            zorder=11,
        )
        ax[0, 0].add_patch(onshore_substation_patch00)

        component_areas["onshore_substation_area_m2"] = onshore_substation_area

    ## add transport pipeline
    if design_scenario["transportation"] == "colocated":
        # add hydrogen pipeline to end use
        linetype = "-."
        label = "Pipeline to storage/end-use"
        linewidth = 1.0

        ax[ax_index_plant].plot(
            [onshorex, -10000],
            [onshorey, onshorey],
            linetype,
            color=pipe_color,
            label=label,
            linewidth=linewidth,
            zorder=0,
        )

        ax[ax_index_detail].plot(
            [onshorex, -10000],
            [onshorey, onshorey],
            linetype,
            color=pipe_color,
            label=label,
            linewidth=linewidth,
            zorder=0,
        )
    if (
        design_scenario["transportation"] == "pipeline"
        or design_scenario["transportation"] == "hvdc+pipeline"
        or (
            design_scenario["transportation"] == "hvdc"
            and design_scenario["h2_storage_location"] == "platform"
        )
    ):
        linetype = "-."
        label = "Transport pipeline"
        linewidth = 1.0

        ax[ax_index_plant].plot(
            [onshorex, 1000],
            [onshorey + 2, onshorey + 2],
            linetype,
            color=pipe_color,
            label=label,
            linewidth=linewidth,
            zorder=0,
        )

        if design_scenario["wind_location"] == "offshore":
            ax[ax_index_wind_plant].plot(
                [-5000, substation_x],
                [substation_y + 100, substation_y + 100],
                linetype,
                linewidth=linewidth,
                color=pipe_color,
                label=label,
                zorder=0,
            )
            ax[ax_index_detail].plot(
                [-5000, substation_x],
                [substation_y + 2, substation_y + 2],
                linetype,
                linewidth=linewidth,
                color=pipe_color,
                label=label,
                zorder=0,
            )

            if (
                design_scenario["transportation"] == "hvdc"
                or design_scenario["transportation"] == "hvdc+pipeline"
            ) and design_scenario["h2_storage_location"] == "platform":
                h2cx = onshorex - compressor_side
                h2cy = onshorey - compressor_side + 2
                h2cax = ax[ax_index_plant]
            else:
                h2cx = substation_x - substation_side_length
                h2cy = substation_y
                h2cax = ax[ax_index_detail]

        if design_scenario["wind_location"] == "onshore":
            compressor_patch01 = patches.Rectangle(
                (origin_x, origin_y),
                compressor_side,
                compressor_side,
                color=compressor_color,
                fill=None,
                label="Transport compressor*",
                hatch="+++",
                zorder=20,
            )
            ax[ax_index_plant].add_patch(compressor_patch01)

        compressor_patch10 = patches.Rectangle(
            (h2cx, h2cy),
            compressor_side,
            compressor_side,
            color=compressor_color,
            fill=None,
            label="Transport compressor*",
            hatch="+++",
            zorder=20,
        )
        h2cax.add_patch(compressor_patch10)

        component_areas["compressor_area_m2"] = compressor_area

    ## add plant components
    if design_scenario["electrolyzer_location"] == "onshore":
        electrolyzer_x = onshorex
        electrolyzer_y = onshorey
        electrolyzer_patch = patches.Rectangle(
            (electrolyzer_x, electrolyzer_y),
            electrolyzer_side,
            electrolyzer_side,
            color=electrolyzer_color,
            fill=None,
            label="H$_2$ Electrolyzer",
            zorder=20,
            hatch=electrolyzer_hatch,
        )
        ax[ax_index_plant].add_patch(electrolyzer_patch)
        component_areas["electrolyzer_area_m2"] = electrolyzer_area

        if design_scenario["wind_location"] == "onshore":
            electrolyzer_patch = patches.Rectangle(
                (onshorex - h2_storage_side, onshorey + 4),
                electrolyzer_side,
                electrolyzer_side,
                color=electrolyzer_color,
                fill=None,
                label="H$_2$ Electrolyzer",
                zorder=20,
                hatch=electrolyzer_hatch,
            )
            ax[ax_index_detail].add_patch(electrolyzer_patch)

    elif design_scenario["electrolyzer_location"] == "platform":
        dx = equipment_platform_x - equipment_platform_side_length / 2
        dy = equipment_platform_y - equipment_platform_side_length / 2
        e_side_y = equipment_platform_side_length
        e_side_x = electrolyzer_area / e_side_y
        d_side_y = equipment_platform_side_length
        d_side_x = desal_equipment_area / d_side_y
        electrolyzer_x = dx + d_side_x
        electrolyzer_y = dy

        electrolyzer_patch = patches.Rectangle(
            (electrolyzer_x, electrolyzer_y),
            e_side_x,
            e_side_y,
            color=electrolyzer_color,
            fill=None,
            zorder=20,
            label="H$_2$ Electrolyzer",
            hatch=electrolyzer_hatch,
        )
        ax[ax_index_detail].add_patch(electrolyzer_patch)
        desal_patch = patches.Rectangle(
            (dx, dy),
            d_side_x,
            d_side_y,
            color=desal_color,
            zorder=21,
            fill=None,
            label="Desalinator",
            hatch=desalinator_hatch,
        )
        ax[ax_index_detail].add_patch(desal_patch)
        component_areas["desalination_area_m2"] = desal_equipment_area

    elif design_scenario["electrolyzer_location"] == "turbine":
        electrolyzer_patch11 = patches.Rectangle(
            (turbine_x[0], turbine_y[0] + tower_base_radius),
            electrolyzer_side,
            electrolyzer_side,
            color=electrolyzer_color,
            fill=None,
            zorder=20,
            label="H$_2$ Electrolyzer",
            hatch=electrolyzer_hatch,
        )
        ax[ax_index_turbine_detail].add_patch(electrolyzer_patch11)
        desal_patch11 = patches.Rectangle(
            (turbine_x[0] - desal_equipment_side, turbine_y[0] + tower_base_radius),
            desal_equipment_side,
            desal_equipment_side,
            color=desal_color,
            zorder=21,
            fill=None,
            label="Desalinator",
            hatch=desalinator_hatch,
        )
        ax[ax_index_turbine_detail].add_patch(desal_patch11)
        component_areas["desalination_area_m2"] = desal_equipment_area
        i = 0
        for x, y in zip(turbine_x, turbine_y):
            if i == 0:
                elabel = "H$_2$ Electrolyzer"
                dlabel = "Desalinator"
            else:
                elabel = None
                dlabel = None
            electrolyzer_patch01 = patches.Rectangle(
                (x, y + tower_base_radius),
                electrolyzer_side,
                electrolyzer_side,
                color=electrolyzer_color,
                fill=None,
                zorder=20,
                label=elabel,
                hatch=electrolyzer_hatch,
            )
            desal_patch01 = patches.Rectangle(
                (x - desal_equipment_side, y + tower_base_radius),
                desal_equipment_side,
                desal_equipment_side,
                color=desal_color,
                zorder=21,
                fill=None,
                label=dlabel,
                hatch=desalinator_hatch,
            )
            ax[ax_index_wind_plant].add_patch(electrolyzer_patch01)
            ax[ax_index_wind_plant].add_patch(desal_patch01)
            i += 1

    h2_storage_hatch = "\\\\\\"
    if design_scenario["h2_storage_location"] == "onshore" and (
        greenheart_config["h2_storage"]["type"] != "none"
    ):
        h2_storage_patch = patches.Rectangle(
            (onshorex - h2_storage_side, onshorey - h2_storage_side - 2),
            h2_storage_side,
            h2_storage_side,
            color=h2_storage_color,
            fill=None,
            label="H$_2$ storage",
            hatch=h2_storage_hatch,
        )
        ax[ax_index_plant].add_patch(h2_storage_patch)
        component_areas["h2_storage_area_m2"] = h2_storage_area

        if design_scenario["wind_location"] == "onshore":
            h2_storage_patch = patches.Rectangle(
                (onshorex - h2_storage_side, onshorey - h2_storage_side - 2),
                h2_storage_side,
                h2_storage_side,
                color=h2_storage_color,
                fill=None,
                label="H$_2$ storage",
                hatch=h2_storage_hatch,
            )
            ax[ax_index_detail].add_patch(h2_storage_patch)
            component_areas["h2_storage_area_m2"] = h2_storage_area
    elif design_scenario["h2_storage_location"] == "platform" and (
        greenheart_config["h2_storage"]["type"] != "none"
    ):
        s_side_y = equipment_platform_side_length
        s_side_x = h2_storage_area / s_side_y
        sx = equipment_platform_x - equipment_platform_side_length / 2
        sy = equipment_platform_y - equipment_platform_side_length / 2
        if design_scenario["electrolyzer_location"] == "platform":
            sx += equipment_platform_side_length - s_side_x

        h2_storage_patch = patches.Rectangle(
            (sx, sy),
            s_side_x,
            s_side_y,
            color=h2_storage_color,
            fill=None,
            label="H$_2$ storage",
            hatch=h2_storage_hatch,
        )
        ax[ax_index_detail].add_patch(h2_storage_patch)
        component_areas["h2_storage_area_m2"] = h2_storage_area

    elif design_scenario["h2_storage_location"] == "turbine":
        if greenheart_config["h2_storage"]["type"] == "turbine":
            h2_storage_patch = patches.Circle(
                (turbine_x[0], turbine_y[0]),
                radius=tower_base_diameter / 2,
                color=h2_storage_color,
                fill=None,
                label="H$_2$ storage",
                hatch=h2_storage_hatch,
            )
            ax[ax_index_turbine_detail].add_patch(h2_storage_patch)
            component_areas["h2_storage_area_m2"] = h2_storage_area
            i = 0
            for x, y in zip(turbine_x, turbine_y):
                if i == 0:
                    slabel = "H$_2$ storage"
                else:
                    slabel = None
                h2_storage_patch = patches.Circle(
                    (x, y),
                    radius=tower_base_diameter / 2,
                    color=h2_storage_color,
                    fill=None,
                    label=None,
                    hatch=h2_storage_hatch,
                )
                ax[ax_index_wind_plant].add_patch(h2_storage_patch)
        elif greenheart_config["h2_storage"]["type"] == "pressure_vessel":
            h2_storage_side = np.sqrt(h2_storage_area / greenheart_config["plant"]["num_turbines"])
            h2_storage_patch = patches.Rectangle(
                (
                    turbine_x[0] - h2_storage_side - desal_equipment_side,
                    turbine_y[0] + tower_base_radius,
                ),
                width=h2_storage_side,
                height=h2_storage_side,
                color=h2_storage_color,
                fill=None,
                label="H$_2$ storage",
                hatch=h2_storage_hatch,
            )
            ax[ax_index_turbine_detail].add_patch(h2_storage_patch)
            component_areas["h2_storage_area_m2"] = h2_storage_area
            for i in range(zip(turbine_x, turbine_y)):
                if i == 0:
                    slabel = "H$_2$ storage"
                else:
                    slabel = None
                h2_storage_patch = patches.Rectangle(
                    (
                        turbine_x[i] - h2_storage_side - desal_equipment_side,
                        turbine_y[i] + tower_base_radius,
                    ),
                    width=h2_storage_side,
                    height=h2_storage_side,
                    color=h2_storage_color,
                    fill=None,
                    label=slabel,
                    hatch=h2_storage_hatch,
                )
                ax[ax_index_wind_plant].add_patch(h2_storage_patch)

    ## add battery
    if "battery" in hopp_config["technologies"].keys():
        component_areas["battery_area_m2"] = hopp_results["hybrid_plant"].battery.footprint_area
        if design_scenario["battery_location"] == "onshore":
            battery_side_y = np.sqrt(hopp_results["hybrid_plant"].battery.footprint_area)
            battery_side_x = battery_side_y

            batteryx = electrolyzer_x

            batteryy = electrolyzer_y + electrolyzer_side + 10

            battery_patch = patches.Rectangle(
                (batteryx, batteryy),
                battery_side_x,
                battery_side_y,
                color=battery_color,
                fill=None,
                label="Battery array",
                hatch=battery_hatch,
            )
            ax[ax_index_plant].add_patch(battery_patch)

            if design_scenario["wind_location"] == "onshore":
                battery_patch = patches.Rectangle(
                    (batteryx, batteryy),
                    battery_side_x,
                    battery_side_y,
                    color=battery_color,
                    fill=None,
                    label="Battery array",
                    hatch=battery_hatch,
                )
                ax[ax_index_detail].add_patch(battery_patch)

        elif design_scenario["battery_location"] == "platform":
            battery_side_y = equipment_platform_side_length
            battery_side_x = hopp_results["hybrid_plant"].battery.footprint_area / battery_side_y

            batteryx = equipment_platform_x - equipment_platform_side_length / 2
            batteryy = equipment_platform_y - equipment_platform_side_length / 2

            battery_patch = patches.Rectangle(
                (batteryx, batteryy),
                battery_side_x,
                battery_side_y,
                color=battery_color,
                fill=None,
                label="Battery array",
                hatch=battery_hatch,
            )
            ax[ax_index_detail].add_patch(battery_patch)

    else:
        battery_side_y = 0.0
        battery_side_x = 0.0

    ## add solar
    if hopp_config["site"]["solar"]:
        component_areas["pv_area_m2"] = hopp_results["hybrid_plant"].pv.footprint_area
        if design_scenario["pv_location"] == "offshore":
            solar_side_y = equipment_platform_side_length
            solar_side_x = hopp_results["hybrid_plant"].pv.footprint_area / solar_side_y

            solarx = equipment_platform_x - equipment_platform_side_length / 2
            solary = equipment_platform_y - equipment_platform_side_length / 2

            solar_patch = patches.Rectangle(
                (solarx, solary),
                solar_side_x,
                solar_side_y,
                color=solar_color,
                fill=None,
                label="Solar array",
                hatch=solar_hatch,
            )
            ax[ax_index_detail].add_patch(solar_patch)
        else:
            solar_side_y = np.sqrt(hopp_results["hybrid_plant"].pv.footprint_area)
            solar_side_x = hopp_results["hybrid_plant"].pv.footprint_area / solar_side_y

            solarx = electrolyzer_x

            solary = electrolyzer_y + electrolyzer_side + 10

            if "battery" in hopp_config["technologies"].keys():
                solary += battery_side_y + 10

            solar_patch = patches.Rectangle(
                (solarx, solary),
                solar_side_x,
                solar_side_y,
                color=solar_color,
                fill=None,
                label="Solar array",
                hatch=solar_hatch,
            )

            ax[ax_index_plant].add_patch(solar_patch)

            if design_scenario["wind_location"] != "offshore":
                solar_patch = patches.Rectangle(
                    (solarx, solary),
                    solar_side_x,
                    solar_side_y,
                    color=solar_color,
                    fill=None,
                    label="Solar array",
                    hatch=solar_hatch,
                )

                ax[ax_index_detail].add_patch(solar_patch)

    else:
        solar_side_x = 0.0
        solar_side_y = 0.0

    ## add wave
    if hopp_config["site"]["wave"]:
        # get wave generation area geometry
        num_devices = hopp_config["technologies"]["wave"]["num_devices"]
        distance_to_shore = (
            hopp_config["technologies"]["wave"]["cost_inputs"]["distance_to_shore"] * 1e3
        )
        number_rows = hopp_config["technologies"]["wave"]["cost_inputs"]["number_rows"]
        device_spacing = hopp_config["technologies"]["wave"]["cost_inputs"]["device_spacing"]
        row_spacing = hopp_config["technologies"]["wave"]["cost_inputs"]["row_spacing"]

        # calculate wave generation area dimenstions
        wave_side_y = device_spacing * np.ceil(num_devices / number_rows)
        wave_side_x = row_spacing * (number_rows)
        wave_area = wave_side_x * wave_side_y
        component_areas["wave_area_m2"] = wave_area

        # generate wave generation patch
        wavex = substation_x - wave_side_x
        wavey = substation_y + distance_to_shore
        wave_patch = patches.Rectangle(
            (wavex, wavey),
            wave_side_x,
            wave_side_y,
            color=wave_color,
            fill=None,
            label="Wave array",
            hatch=wave_hatch,
            zorder=1,
        )
        ax[ax_index_wind_plant].add_patch(wave_patch)

        # add electrical transmission for wave
        wave_export_cable_coords_x = [substation_x, substation_x]
        wave_export_cable_coords_y = [substation_y, substation_y + distance_to_shore]

        ax[ax_index_wind_plant].plot(
            wave_export_cable_coords_x,
            wave_export_cable_coords_y,
            cable_color,
            zorder=0,
        )
        ax[ax_index_detail].plot(
            wave_export_cable_coords_x,
            wave_export_cable_coords_y,
            cable_color,
            zorder=0,
        )

    if design_scenario["wind_location"] == "offshore":
        allpoints = cable_array_points.flatten()
    else:
        allpoints = turbine_x

    allpoints = allpoints[~np.isnan(allpoints)]

    if design_scenario["wind_location"] == "offshore":
        roundto = -2
        ax[ax_index_plant].set(
            xlim=[
                round(np.min(onshorex - 100), ndigits=roundto),
                round(
                    np.max(
                        [
                            onshorex,
                            onshore_substation_x_side_length,
                            electrolyzer_side,
                            solar_side_x,
                        ]
                    )
                    * 1.8,
                    ndigits=roundto,
                ),
            ],
            ylim=[
                round(np.min(onshorey - 100), ndigits=roundto),
                round(
                    np.max(onshorey + battery_side_y + electrolyzer_side + solar_side_y + 100)
                    * 1.9,
                    ndigits=roundto,
                ),
            ],
        )
        ax[ax_index_plant].set(aspect="equal")

        roundto = -3
        point_range_x = np.max(allpoints) - np.min(allpoints)
        point_range_y = np.max(turbine_y) - np.min(turbine_y)
        ax[ax_index_wind_plant].set(
            xlim=[
                round(np.min(allpoints) - 0.5 * point_range_x, ndigits=roundto),
                round(np.max(allpoints) + 0.5 * point_range_x, ndigits=roundto),
            ],
            ylim=[
                round(np.min(turbine_y) - 0.3 * point_range_y, ndigits=roundto),
                round(np.max(turbine_y) + 0.3 * point_range_y, ndigits=roundto),
            ],
        )
        # ax[ax_index_wind_plant].autoscale()
        ax[ax_index_wind_plant].set(aspect="equal")
        # ax[ax_index_wind_plant].xaxis.set_major_locator(ticker.\
        #   MultipleLocator(np.round(point_range_x*0.5, decimals=-3)))
        # ax[ax_index_wind_plant].yaxis.set_major_locator(ticker.\
        #   MultipleLocator(np.round(point_range_y*0.5, device_spacing=-3)))

    else:
        roundto = -3
        point_range_x = np.max(allpoints) - np.min(allpoints)
        point_range_y = np.max(turbine_y) - onshorey
        ax[ax_index_plant].set(
            xlim=[
                round(np.min(allpoints) - 0.7 * point_range_x, ndigits=roundto),
                round(np.max(allpoints + 0.7 * point_range_x), ndigits=roundto),
            ],
            ylim=[
                round(np.min(onshorey) - 0.2 * point_range_y, ndigits=roundto),
                round(np.max(turbine_y) + 1.0 * point_range_y, ndigits=roundto),
            ],
        )
        # ax[ax_index_plant].autoscale()
        ax[ax_index_plant].set(aspect="equal")
        # ax[ax_index_plant].xaxis.set_major_locator(ticker.MultipleLocator(2000))
        # ax[ax_index_plant].yaxis.set_major_locator(ticker.MultipleLocator(1000))

    if design_scenario["wind_location"] == "offshore":
        roundto = -2
        ax[ax_index_detail].set(
            xlim=[
                round(origin_x - 400, ndigits=roundto),
                round(origin_x + 100, ndigits=roundto),
            ],
            ylim=[
                round(origin_y - 200, ndigits=roundto),
                round(origin_y + 200, ndigits=roundto),
            ],
        )
        ax[ax_index_detail].set(aspect="equal")
    else:
        roundto = -2

        if "pv" in hopp_config["technologies"].keys():
            xmax = round(
                np.max([onshorex, electrolyzer_side, battery_side_x, solar_side_x]) * 1.1,
                ndigits=roundto,
            )
            ymax = round(
                onshorey + (solar_side_y + electrolyzer_side + battery_side_y) * 1.15,
                ndigits=roundto,
            )
        else:
            xmax = round(np.max([onshorex]) * 1.1, ndigits=roundto)
            ymax = round(
                onshorey + (electrolyzer_side + battery_side_y + solar_side_y) * 1.1,
                ndigits=roundto,
            )
        ax[ax_index_detail].set(
            xlim=[
                round(onshorex - 10, ndigits=roundto),
                xmax,
            ],
            ylim=[
                round(onshorey - 200, ndigits=roundto),
                ymax,
            ],
        )
        ax[ax_index_detail].set(aspect="equal")

    if design_scenario["wind_location"] == "offshore":
        tower_buffer0 = 10
        tower_buffer1 = 10
        roundto = -1
        ax[ax_index_turbine_detail].set(
            xlim=[
                round(
                    turbine_x[0] - tower_base_radius - tower_buffer0 - 50,
                    ndigits=roundto,
                ),
                round(
                    turbine_x[0] + tower_base_radius + 3 * tower_buffer1,
                    ndigits=roundto,
                ),
            ],
            ylim=[
                round(
                    turbine_y[0] - tower_base_radius - 2 * tower_buffer0,
                    ndigits=roundto,
                ),
                round(
                    turbine_y[0] + tower_base_radius + 4 * tower_buffer1,
                    ndigits=roundto,
                ),
            ],
        )
        ax[ax_index_turbine_detail].set(aspect="equal")
        ax[ax_index_turbine_detail].xaxis.set_major_locator(ticker.MultipleLocator(10))
        ax[ax_index_turbine_detail].yaxis.set_major_locator(ticker.MultipleLocator(10))
        # ax[0,1].legend(frameon=False)
        # ax[0,1].axis('off')

    if design_scenario["wind_location"] == "offshore":
        labels = [
            "(a) Onshore plant",
            "(b) Offshore plant",
            "(c) Equipment platform and substation",
            "(d) NW-most wind turbine",
        ]
    else:
        labels = ["(a) Full plant", "(b) Non-wind plant detail"]
    for axi, label in zip(ax.flatten(), labels):
        axi.legend(frameon=False, ncol=2)  # , ncol=2, loc="best")
        axi.set(xlabel="Easting (m)", ylabel="Northing (m)")
        axi.set_title(label, loc="left")
        # axi.spines[['right', 'top']].set_visible(False)

    ## save the plot
    plt.tight_layout()
    savepaths = [
        output_dir / "figures/layout",
        output_dir / "data",
    ]
    if save_plots:
        for savepath in savepaths:
            if not savepath.exists():
                savepath.mkdir(parents=True)
        plt.savefig(savepaths[0] / f"plant_layout_{plant_design_number}.png", transparent=True)

        df = pd.DataFrame([component_areas])
        df.to_csv(
            savepaths[1] / "fcomponent_areas_layout_{plant_design_number}.csv",
            index=False,
        )

    if show_plots:
        plt.show()
    else:
        plt.close()


def save_energy_flows(
    hybrid_plant: HoppInterface.system,
    electrolyzer_physics_results,
    solver_results,
    hours,
    h2_storage_results,
    simulation_length=8760,
    output_dir="./output/",
):
    if isinstance(output_dir, str):
        output_dir = Path(output_dir).resolve()

    output = {}
    if hybrid_plant.pv:
        solar_plant_power = np.array(hybrid_plant.pv.generation_profile[0:simulation_length])
        output.update({"pv generation [kW]": solar_plant_power})
    if hybrid_plant.wind:
        wind_plant_power = np.array(hybrid_plant.wind.generation_profile[0:simulation_length])
        output.update({"wind generation [kW]": wind_plant_power})
    if hybrid_plant.wave:
        wave_plant_power = np.array(hybrid_plant.wave.generation_profile[0:simulation_length])
        output.update({"wave generation [kW]": wave_plant_power})
    if hybrid_plant.battery:
        battery_power_out_mw = hybrid_plant.battery.outputs.P
        output.update(
            {"battery discharge [kW]": [(int(p > 0)) * p * 1e3 for p in battery_power_out_mw]}
        )  # convert from MW to kW and extract only discharging
        output.update(
            {"battery charge [kW]": [-(int(p < 0)) * p * 1e3 for p in battery_power_out_mw]}
        )  # convert from MW to kW and extract only charging
        output.update({"battery state of charge [%]": hybrid_plant.battery.outputs.dispatch_SOC})
    total_generation_hourly = hybrid_plant.grid._system_model.Outputs.system_pre_interconnect_kwac[
        0:simulation_length
    ]
    output.update({"total generation hourly [kW]": total_generation_hourly})
    output.update(
        {
            "total generation curtailed hourly [kW]": hybrid_plant.grid.generation_curtailed[
                0:simulation_length
            ]
        }
    )
    output.update({"total accessory power required [kW]": solver_results[0]})
    output.update({"grid energy usage hourly [kW]": solver_results[1]})
    output.update({"desal energy hourly [kW]": [solver_results[2]] * simulation_length})
    output.update(
        {
            "electrolyzer energy hourly [kW]": electrolyzer_physics_results[
                "power_to_electrolyzer_kw"
            ]
        }
    )
    output.update({"electrolyzer bop energy hourly [kW]": solver_results[5]})
    output.update(
        {"transport compressor energy hourly [kW]": [solver_results[3]] * simulation_length}
    )
    output.update({"storage energy hourly [kW]": [solver_results[4]] * simulation_length})
    output.update(
        {
            "h2 production hourly [kg]": electrolyzer_physics_results["H2_Results"][
                "Hydrogen Hourly Production [kg/hr]"
            ]
        }
    )
    if "hydrogen_storage_soc" in h2_storage_results:
        output.update({"hydrogen storage SOC [kg]": h2_storage_results["hydrogen_storage_soc"]})

    df = pd.DataFrame.from_dict(output)

    filepath = output_dir / "data/production"

    if not filepath.exists():
        filepath.mkdir(parents=True)

    df.to_csv(filepath / "energy_flows.csv")

    return output


def calculate_lca(
    hopp_results,
    electrolyzer_physics_results,
    hopp_config,
    greenheart_config,
    total_accessory_power_renewable_kw,
    total_accessory_power_grid_kw,
    plant_design_scenario_number,
    incentive_option_number,
):
    """
    Function to perform Life Cycle Assessment (LCA) of the simulated system.
    Calculates Scope 1, 2, and 3 average emissions over the lifetime of the plant in kg CO2e per
    unit mass of product produced.
    CO2e or carbon dioxide equivalent is a metric for the global warming potential of different
    greenhouse gases (GHGs) by converting their emissions to the equivalent amount of CO2.
    Leverages ANL's GREET model to determine emission intensity (EI), efficiency, feedstock
    consumption, and energy consumption values of various processes
    Leverages NREL's Cambium API to determine future grid generation mixes and emissions intensities
    of grid electricity consumption

    Args:
        hopp_results (dict): results from the hopp simulation
        electrolyzer_physics_results (dict): results of the electrolysis simulation
        hopp_config (dict): HOPP configuration inputs based on input files
        greenheart_config (GreenHeartSimulationConfig): all inputs to the greenheart simulation
        total_accessory_power_renewable_kw (numpy.ndarray): Total electricity to electrolysis
            peripherals from renewable power (kWh) with shape = (8760,)
        total_accessory_power_grid_kw (numpy.ndarray): Total electricity to electrolysis
            peripherals from grid power (kWh) with shape = (8760,)
        plant_design_scenario_number (int): plant design scenario number
        incentive_option_number (int): incentive option number

    Returns:
        lca_df (pandas.DataFrame): Pandas DataFrame containing average emissions intensities over
            lifetime of plant and other relevant data
    """

    # Load relevant config and results data from HOPP and GreenHEART:
    site_latitude = hopp_config["site"]["data"]["lat"]
    site_longitude = hopp_config["site"]["data"]["lon"]
    project_lifetime = greenheart_config["project_parameters"][
        "project_lifetime"
    ]  # system lifetime (years)
    plant_design_scenario = greenheart_config["plant_design"][
        f"scenario{plant_design_scenario_number}"
    ]  # plant design scenario number
    tax_incentive_option = greenheart_config["policy_parameters"][
        f"option{incentive_option_number}"
    ]  # tax incentive option number
    wind_annual_energy_kwh = hopp_results["annual_energies"][
        "wind"
    ]  # annual energy from wind (kWh)
    solar_pv_annual_energy_kwh = hopp_results["annual_energies"][
        "pv"
    ]  # annual energy from solar (kWh)
    # battery_annual_energy_kwh = hopp_results["annual_energies"][
    #     "battery"
    # ]  # annual energy from battery (kWh)
    # battery_system_capacity_kwh = hopp_results["hybrid_plant"].battery.system_capacity_kwh
    # # battery rated capacity (kWh)
    wind_turbine_rating_MW = (
        hopp_config["technologies"]["wind"]["turbine_rating_kw"] / 1000
    )  # wind turbine rating (MW)
    wind_model = hopp_config["technologies"]["wind"]["model_name"]  # wind model used in analysis

    # Determine renewable technologies in system and define renewables_case string for output file
    renewable_technologies_modeled = [
        tech for tech in hopp_config["technologies"] if tech != "grid"
    ]
    if len(renewable_technologies_modeled) > 1:
        renewables_case = "+".join(renewable_technologies_modeled)
    elif len(renewable_technologies_modeled) == 1:
        renewables_case = str(renewable_technologies_modeled[0])
    else:
        renewables_case = "No-ren"

    # Determine grid case and define grid_case string for output file
    # NOTE: original LCA project code calculations were created with functionality for a
    # hybrid-grid case, however this functionality was removed during prior HOPP refactors
    # NOTE: In future, update logic below to include 'hybrid-grid' case. Possibly look at
    # input config yamls and technologies present for this logic?(pending modular framework):
    # if only grid present -> grid-only?
    # if any renewables + grid present -> hybrid-grid?
    # if only renewables present -> off-grid?
    if greenheart_config["project_parameters"]["grid_connection"]:
        if greenheart_config["electrolyzer"]["sizing"]["hydrogen_dmd"] is not None:
            grid_case = "grid-only"
        else:
            grid_case = "off-grid"
    else:
        grid_case = "off-grid"

    # Capture electrolyzer configuration variables / strings for output files
    if greenheart_config["electrolyzer"]["include_degradation_penalty"]:
        electrolyzer_degradation = "True"
    else:
        electrolyzer_degradation = "False"
    if plant_design_scenario["transportation"] == "colocated":
        electrolyzer_centralization = "Centralized"
    else:
        electrolyzer_centralization = "Distributed"
    electrolyzer_optimized = greenheart_config["electrolyzer"]["pem_control_type"]
    electrolyzer_type = greenheart_config["lca_config"]["electrolyzer_type"]
    number_of_electrolyzer_clusters = int(
        ceildiv(
            greenheart_config["electrolyzer"]["rating"],
            greenheart_config["electrolyzer"]["cluster_rating_MW"],
        )
    )

    # Calculate average annual and lifetime h2 production
    h2_annual_prod_kg = np.array(
        electrolyzer_physics_results["H2_Results"]["Life: Annual H2 production [kg/year]"]
    )  # Lifetime Average Annual H2 production accounting for electrolyzer degradation (kg H2/year)
    h2_lifetime_prod_kg = (
        h2_annual_prod_kg * project_lifetime
    )  # Lifetime H2 production accounting for electrolyzer degradation (kg H2)

    # Calculate energy to electrolyzer and peripherals when hybrid-grid case
    if grid_case == "hybrid-grid":
        energy_shortfall_hopp = hopp_results[
            "energy_shortfall_hopp"
        ]  # Total electricity to electrolyzer and peripherals from grid power (kWh)
        energy_shortfall_hopp.shape = (
            project_lifetime,
            8760,
        )  # Reshaped to be annual power (project_lifetime, 8760)
        annual_energy_to_electrolysis_from_grid = np.mean(
            energy_shortfall_hopp, axis=0
        )  # Lifetime Average Annual electricity to electrolyzer and peripherals from grid power
        # shape = (8760,)

    # Calculate energy to electrolyzer and peripherals when grid-only case
    if grid_case == "grid-only":
        energy_to_electrolyzer = electrolyzer_physics_results[
            "power_to_electrolyzer_kw"
        ]  # Total electricity to electrolyzer from grid power (kWh
        energy_to_peripherals = (
            total_accessory_power_renewable_kw + total_accessory_power_grid_kw
        )  # Total electricity to peripherals from grid power (kWh)
        annual_energy_to_electrolysis_from_grid = (
            energy_to_electrolyzer + energy_to_peripherals
        )  # Average Annual electricity to electrolyzer and peripherals from grid power
        # shape = (8760,)

    # Create dataframe for electrolyzer + peripherals grid power profiles if grid connected
    if grid_case in ("grid-only", "hybrid-grid"):
        electrolyzer_grid_profile_data_dict = {
            "Energy to electrolysis from grid (kWh)": annual_energy_to_electrolysis_from_grid
        }
        electrolyzer_grid_profile_df = pd.DataFrame(data=electrolyzer_grid_profile_data_dict)
        electrolyzer_grid_profile_df = electrolyzer_grid_profile_df.reset_index().rename(
            columns={"index": "Interval"}
        )
        electrolyzer_grid_profile_df["Interval"] = electrolyzer_grid_profile_df["Interval"] + 1
        electrolyzer_grid_profile_df = electrolyzer_grid_profile_df.set_index("Interval")

    # Instantiate lists that define technologies / processes and LCA scopes
    # used to dynamically define key value pairs in dictionaries to store data
    processes = [
        "electrolysis",
        "smr",
        "smr_ccs",
        "atr",
        "atr_ccs",
        "NH3_electrolysis",
        "NH3_smr",
        "NH3_smr_ccs",
        "NH3_atr",
        "NH3_atr_ccs",
        "steel_electrolysis",
        "steel_smr",
        "steel_smr_ccs",
        "steel_atr",
        "steel_atr_ccs",
    ]

    scopes = ["Scope3", "Scope2", "Scope1", "Total"]

    # Instantiate dictionary of numpy objects (np.nan -> converts to np.float when assigned value)
    # to hold EI values per cambium year
    EI_values = {
        f"{process}_{scope}_EI": globals().get(f"{process}_{scope}_EI", np.nan)
        for process in processes
        for scope in scopes
    }

    # Instantiate dictionary of lists to hold EI time series (ts) data for all cambium years
    # EI_values for each cambium year are appended to corresponding lists
    ts_EI_data = {f"{process}_{scope}_EI": [] for process in processes for scope in scopes}

    ## GREET Data
    # Define conversions
    g_to_kg = 0.001  # 1 g = 0.001 kg
    MT_to_kg = 1000  # 1 metric ton = 1000 kg
    kWh_to_MWh = 0.001  # 1 kWh = 0.001 MWh
    MWh_to_kWh = 1000  # 1 MWh = 1000 kWh
    gal_H2O_to_MT = 0.00378541  # 1 US gallon of H2O = 0.00378541 metric tons

    # Instantiate GreetData class object, parse greet if not already parsed
    # return class object and load data dictionary
    greet_data = GREETData(greet_year=2023)
    greet_data_dict = greet_data.data

    # ------------------------------------------------------------------------------
    # Natural Gas
    # ------------------------------------------------------------------------------
    NG_combust_EI = greet_data_dict[
        "NG_combust_EI"
    ]  # GHG Emissions Intensity of Natural Gas combustion in a utility / industrial large boiler
    # (g CO2e/MJ Natural Gas combusted)
    NG_supply_EI = greet_data_dict[
        "NG_supply_EI"
    ]  # GHG Emissions Intensity of supplying Natural Gas to processes as a feedstock / process fuel
    # (g CO2e/MJ Natural Gas consumed)

    # ------------------------------------------------------------------------------
    # Water
    # ------------------------------------------------------------------------------
    if greenheart_config["lca_config"]["feedstock_water_type"] == "desal":
        H2O_supply_EI = greet_data_dict[
            "desal_H2O_supply_EI"
        ]  # GHG Emissions Intensity of RO desalination and supply of that water to processes
    # (kg CO2e/gal H2O).
    elif greenheart_config["lca_config"]["feedstock_water_type"] == "ground":
        H2O_supply_EI = greet_data_dict[
            "ground_H2O_supply_EI"
        ]  # GHG Emissions Intensity of ground water and supply of that water to processes
    # (kg CO2e/gal H2O).
    elif greenheart_config["lca_config"]["feedstock_water_type"] == "surface":
        H2O_supply_EI = greet_data_dict[
            "surface_H2O_supply_EI"
        ]  # GHG Emissions Intensity of surface water and supply of that water to processes
    # (kg CO2e/gal H2O).
    # ------------------------------------------------------------------------------
    # Lime
    # ------------------------------------------------------------------------------
    lime_supply_EI = greet_data_dict[
        "lime_supply_EI"
    ]  # GHG Emissions Intensity of supplying Lime to processes accounting for limestone mining,
    # lime production, lime processing, and lime transportation assuming 20 miles via Diesel engines
    # (kg CO2e/kg lime)
    # ------------------------------------------------------------------------------
    # Renewable infrastructure embedded emission intensities
    # ------------------------------------------------------------------------------
    # NOTE: HOPP/GreenHEART version at time of dev can only model PEM electrolysis
    if electrolyzer_type == "pem":
        # ely_stack_capex_EI = greet_data_dict[
        #     "pem_ely_stack_capex_EI"
        # ]  # PEM electrolyzer CAPEX emissions (kg CO2e/kg H2)
        ely_stack_and_BoP_capex_EI = greet_data_dict[
            "pem_ely_stack_and_BoP_capex_EI"
        ]  # PEM electrolyzer stack CAPEX + Balance of Plant emissions (kg CO2e/kg H2)
    elif electrolyzer_type == "alkaline":
        # ely_stack_capex_EI = greet_data_dict[
        #     "alk_ely_stack_capex_EI"
        # ]  # Alkaline electrolyzer CAPEX emissions (kg CO2e/kg H2)
        ely_stack_and_BoP_capex_EI = greet_data_dict[
            "alk_ely_stack_and_BoP_capex_EI"
        ]  # Alkaline electrolyzer stack CAPEX + Balance of Plant emissions (kg CO2e/kg H2)
    elif electrolyzer_type == "soec":
        # ely_stack_capex_EI = greet_data_dict[
        #     "soec_ely_stack_capex_EI"
        # ]  # SOEC electrolyzer CAPEX emissions (kg CO2e/kg H2)
        ely_stack_and_BoP_capex_EI = greet_data_dict[
            "soec_ely_stack_and_BoP_capex_EI"
        ]  # SOEC electrolyzer stack CAPEX + Balance of Plant emissions (kg CO2e/kg H2)
    wind_capex_EI = greet_data_dict["wind_capex_EI"]  # Wind CAPEX emissions (g CO2e/kWh)
    solar_pv_capex_EI = greet_data_dict[
        "solar_pv_capex_EI"
    ]  # Solar PV CAPEX emissions (g CO2e/kWh)
    battery_EI = greet_data_dict["battery_LFP_EI"]  # LFP Battery embodied emissions (g CO2e/kWh)
    nuclear_BWR_capex_EI = greet_data_dict[
        "nuclear_BWR_capex_EI"
    ]  # Nuclear Boiling Water Reactor (BWR) CAPEX emissions (g CO2e/kWh)
    nuclear_PWR_capex_EI = greet_data_dict[
        "nuclear_PWR_capex_EI"
    ]  # Nuclear Pressurized Water Reactor (PWR) CAPEX emissions (g CO2e/kWh)
    coal_capex_EI = greet_data_dict["coal_capex_EI"]  # Coal CAPEX emissions (g CO2e/kWh)
    gas_capex_EI = greet_data_dict[
        "gas_capex_EI"
    ]  # Natural Gas Combined Cycle (NGCC) CAPEX emissions (g CO2e/kWh)
    hydro_capex_EI = greet_data_dict["hydro_capex_EI"]  # Hydro CAPEX emissions (g CO2e/kWh)
    bio_capex_EI = greet_data_dict["bio_capex_EI"]  # Biomass CAPEX emissions (g CO2e/kWh)
    # geothermal_egs_capex_EI = greet_data_dict[
    #     "geothermal_egs_capex_EI"
    # ]  # Geothermal EGS CAPEX emissions (g CO2e/kWh)
    geothermal_binary_capex_EI = greet_data_dict[
        "geothermal_binary_capex_EI"
    ]  # Geothermal Binary CAPEX emissions (g CO2e/kWh)
    geothermal_flash_capex_EI = greet_data_dict[
        "geothermal_flash_capex_EI"
    ]  # Geothermal Flash CAPEX emissions (g CO2e/kWh)

    # ------------------------------------------------------------------------------
    # Steam methane reforming (SMR) and Autothermal Reforming (ATR)
    # Incumbent H2 production processes
    # ------------------------------------------------------------------------------
    smr_HEX_eff = greet_data_dict["smr_HEX_eff"]  # SMR Heat exchange efficiency (%)
    # SMR without CCS
    smr_steam_prod = greet_data_dict[
        "smr_steam_prod"
    ]  # Steam exported for SMR w/out CCS (MJ/kg H2)
    smr_NG_consume = greet_data_dict[
        "smr_NG_consume"
    ]  # Natural gas consumption for SMR w/out CCS accounting for efficiency, NG as feed and
    # process fuel for SMR and steam production (MJ-LHV/kg H2)
    smr_electricity_consume = greet_data_dict[
        "smr_electricity_consume"
    ]  # Electricity consumption for SMR w/out CCS accounting for efficiency, electricity
    # as a process fuel (kWh/kg H2)
    # SMR with CCS
    smr_ccs_steam_prod = greet_data_dict[
        "smr_ccs_steam_prod"
    ]  # Steam exported for SMR with CCS (MJ/kg H2)
    smr_ccs_perc_capture = greet_data_dict["smr_ccs_perc_capture"]  # CCS rate for SMR (%)
    smr_ccs_NG_consume = greet_data_dict[
        "smr_ccs_NG_consume"
    ]  # Natural gas consumption for SMR with CCS accounting for efficiency, NG as feed and process
    # fuel for SMR and steam production (MJ-LHV/kg H2)
    smr_ccs_electricity_consume = greet_data_dict[
        "smr_ccs_electricity_consume"
    ]  # SMR via NG w/ CCS WTG Total Energy consumption (kWh/kg H2)
    # ATR without CCS
    atr_NG_consume = greet_data_dict[
        "atr_NG_consume"
    ]  # Natural gas consumption for ATR w/out CCS accounting for efficiency, NG as feed and
    # process fuel for SMR and steam production (MJ-LHV/kg H2)
    atr_electricity_consume = greet_data_dict[
        "atr_electricity_consume"
    ]  # Electricity consumption for ATR w/out CCS accounting for efficiency, electricity as a
    # process fuel (kWh/kg H2)
    # ATR with CCS
    atr_ccs_perc_capture = greet_data_dict["atr_ccs_perc_capture"]  # CCS rate for ATR (%)
    atr_ccs_NG_consume = greet_data_dict[
        "atr_ccs_NG_consume"
    ]  # Natural gas consumption for ATR with CCS accounting for efficiency, NG as feed and
    # process fuel for SMR and steam production (MJ-LHV/kg H2)
    atr_ccs_electricity_consume = greet_data_dict[
        "atr_ccs_electricity_consume"
    ]  # Electricity consumption for ATR with CCS accounting for efficiency, electricity as a
    # process fuel (kWh/kg H2)

    # ------------------------------------------------------------------------------
    # Hydrogen production via water electrolysis
    # ------------------------------------------------------------------------------
    if electrolyzer_type == "pem":
        ely_H2O_consume = greet_data_dict[
            "pem_ely_H2O_consume"
        ]  # H2O consumption for H2 production in PEM electrolyzer (gal H20/kg H2)
    elif electrolyzer_type == "alkaline":
        ely_H2O_consume = greet_data_dict[
            "alk_ely_H2O_consume"
        ]  # H2O consumption for H2 production in Alkaline electrolyzer (gal H20/kg H2)
    elif electrolyzer_type == "soec":
        ely_H2O_consume = greet_data_dict[
            "soec_ely_H2O_consume"
        ]  # H2O consumption for H2 production in High Temp SOEC electrolyzer (gal H20/kg H2)
    # ------------------------------------------------------------------------------
    # Ammonia (NH3)
    # ------------------------------------------------------------------------------
    NH3_NG_consume = greet_data_dict[
        "NH3_NG_consume"
    ]  # Natural gas consumption for combustion in the Haber-Bosch process / Boiler for Ammonia
    # production (MJ/metric ton NH3)
    NH3_H2_consume = greet_data_dict[
        "NH3_H2_consume"
    ]  # Gaseous Hydrogen consumption for Ammonia production, based on chemical balance and is
    # applicable for all NH3 production pathways (kg H2/kg NH3)
    NH3_electricity_consume = greet_data_dict[
        "NH3_electricity_consume"
    ]  # Total Electrical Energy consumption for Ammonia production (kWh/kg NH3)

    # ------------------------------------------------------------------------------
    # Steel
    # ------------------------------------------------------------------------------
    # Values agnostic of DRI-EAF config
    # NOTE: in future if accounting for different iron ore mining, pelletizing processes,
    # and production processes, then add if statement to check greenheart_config for
    # iron production type (DRI, electrowinning, etc)
    # iron_ore_mining_EI_per_MT_steel = greet_data_dict[
    #     "DRI_iron_ore_mining_EI_per_MT_steel"
    # ]  # GHG Emissions Intensity of Iron ore mining for use in DRI-EAF Steel production
    # # (kg CO2e/metric ton steel produced)
    iron_ore_mining_EI_per_MT_ore = greet_data_dict[
        "DRI_iron_ore_mining_EI_per_MT_ore"
    ]  # GHG Emissions Intensity of Iron ore mining for use in DRI-EAF Steel production
    # (kg CO2e/metric ton iron ore)
    # iron_ore_pelletizing_EI_per_MT_steel = greet_data_dict[
    #     "DRI_iron_ore_pelletizing_EI_per_MT_steel"
    # ]  # GHG Emissions Intensity of Iron ore pelletizing for use in DRI-EAF Steel production
    # # (kg CO2e/metric ton steel produced)
    iron_ore_pelletizing_EI_per_MT_ore = greet_data_dict[
        "DRI_iron_ore_pelletizing_EI_per_MT_ore"
    ]  # GHG Emissions Intensity of Iron ore pelletizing for use in DRI-EAF Steel production
    # (kg CO2e/metric ton iron ore)

    # NOTE: in future if accounting for different steel productin processes (DRI-EAF vs XYZ),
    # then add if statement to check greenheart_config for steel production process and
    # update HOPP > greet_data.py with specific variables for each process
    steel_H2O_consume = greet_data_dict[
        "steel_H2O_consume"
    ]  # Total H2O consumption for DRI-EAF Steel production w/ 83% H2 and 0% scrap, accounts for
    # water used in iron ore mining, pelletizing, DRI, and EAF
    # (metric ton H2O/metric ton steel production)
    steel_H2_consume = greet_data_dict[
        "steel_H2_consume"
    ]  # Hydrogen consumption for DRI-EAF Steel production w/ 83% H2 regardless of scrap
    # (metric tons H2/metric ton steel production)
    steel_NG_consume = greet_data_dict[
        "steel_NG_consume"
    ]  # Natural gas consumption for DRI-EAF Steel production accounting for DRI with 83% H2,
    # and EAF + LRF (GJ/metric ton steel)
    steel_electricity_consume = greet_data_dict[
        "steel_electricity_consume"
    ]  # Total Electrical Energy consumption for DRI-EAF Steel production accounting for
    # DRI with 83% H2 and EAF + LRF (MWh/metric ton steel production)
    steel_iron_ore_consume = greet_data_dict[
        "steel_iron_ore_consume"
    ]  # Iron ore consumption for DRI-EAF Steel production
    # (metric ton iron ore/metric ton steel production)
    steel_lime_consume = greet_data_dict[
        "steel_lime_consume"
    ]  # Lime consumption for DRI-EAF Steel production
    # (metric ton lime/metric ton steel production)

    ## Cambium
    # Define cambium_year
    # NOTE: at time of dev hopp logic for LCOH = atb_year + 2yr + install_period(3yrs) = 5 years
    cambium_year = greenheart_config["project_parameters"]["atb_year"] + 5
    # Pull / download cambium data files
    cambium_data = CambiumData(
        lat=site_latitude,
        lon=site_longitude,
        year=cambium_year,
        project_uuid=greenheart_config["lca_config"]["cambium"]["project_uuid"],
        scenario=greenheart_config["lca_config"]["cambium"]["scenario"],
        location_type=greenheart_config["lca_config"]["cambium"]["location_type"],
        time_type=greenheart_config["lca_config"]["cambium"]["time_type"],
    )

    # Read in Cambium data file for each year available
    # NOTE: Additional LRMER values for CO2, CH4, and NO2 are available through the cambium call
    # that are not used in this analysis
    for resource_file in cambium_data.resource_files:
        # Read in csv file to a dataframe, update column names and indexes
        cambium_data_df = pd.read_csv(
            resource_file,
            index_col=None,
            header=0,
            usecols=[
                "lrmer_co2e_c",
                "lrmer_co2e_p",
                "lrmer_co2e",
                "generation",
                "battery_MWh",
                "biomass_MWh",
                "beccs_MWh",
                "canada_MWh",
                "coal_MWh",
                "coal-ccs_MWh",
                "csp_MWh",
                "distpv_MWh",
                "gas-cc_MWh",
                "gas-cc-ccs_MWh",
                "gas-ct_MWh",
                "geothermal_MWh",
                "hydro_MWh",
                "nuclear_MWh",
                "o-g-s_MWh",
                "phs_MWh",
                "upv_MWh",
                "wind-ons_MWh",
                "wind-ofs_MWh",
            ],
        )
        cambium_data_df = cambium_data_df.reset_index().rename(
            columns={
                "index": "Interval",
                "lrmer_co2e_c": "LRMER CO2 equiv. combustion (kg-CO2e/MWh)",
                "lrmer_co2e_p": "LRMER CO2 equiv. precombustion (kg-CO2e/MWh)",
                "lrmer_co2e": "LRMER CO2 equiv. total (kg-CO2e/MWh)",
            }
        )
        cambium_data_df["Interval"] = cambium_data_df["Interval"] + 1
        cambium_data_df = cambium_data_df.set_index("Interval")

        if grid_case in ("grid-only", "hybrid-grid"):
            # Calculate consumption and emissions factor for electrolysis powered by the grid
            combined_data_df = pd.concat([electrolyzer_grid_profile_df, cambium_data_df], axis=1)
            electrolysis_grid_electricity_consume = combined_data_df[
                "Energy to electrolysis from grid (kWh)"
            ].sum()  # Total energy to the electrolyzer from the grid (kWh)
            electrolysis_scope3_grid_emissions = (
                (combined_data_df["Energy to electrolysis from grid (kWh)"] / 1000)
                * combined_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"]
            ).sum()  # Scope 3 Electrolysis Emissions from grid electricity consumption (kg CO2e)
            electrolysis_scope2_grid_emissions = (
                (combined_data_df["Energy to electrolysis from grid (kWh)"] / 1000)
                * combined_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"]
            ).sum()  # Scope 2 Electrolysis Emissions from grid electricity consumption (kg CO2e)

        # Calculate annual percentages of nuclear, geothermal, hydropower, wind, solar, battery,
        # and fossil fuel power in cambium grid mix (%)
        generation_annual_total_MWh = cambium_data_df["generation"].sum()
        generation_annual_nuclear_fraction = (
            cambium_data_df["nuclear_MWh"].sum() / generation_annual_total_MWh
        )
        generation_annual_coal_oil_fraction = (
            cambium_data_df["coal_MWh"].sum()
            + cambium_data_df["coal-ccs_MWh"].sum()
            + cambium_data_df["o-g-s_MWh"].sum()
        ) / generation_annual_total_MWh
        generation_annual_gas_fraction = (
            cambium_data_df["gas-cc_MWh"].sum()
            + cambium_data_df["gas-cc-ccs_MWh"].sum()
            + cambium_data_df["gas-ct_MWh"].sum()
        ) / generation_annual_total_MWh
        generation_annual_bio_fraction = (
            cambium_data_df["biomass_MWh"].sum() + cambium_data_df["beccs_MWh"].sum()
        ) / generation_annual_total_MWh
        generation_annual_geothermal_fraction = (
            cambium_data_df["geothermal_MWh"].sum() / generation_annual_total_MWh
        )
        generation_annual_hydro_fraction = (
            cambium_data_df["hydro_MWh"].sum() + cambium_data_df["phs_MWh"].sum()
        ) / generation_annual_total_MWh
        generation_annual_wind_fraction = (
            cambium_data_df["wind-ons_MWh"].sum() + cambium_data_df["wind-ofs_MWh"].sum()
        ) / generation_annual_total_MWh
        generation_annual_solar_fraction = (
            cambium_data_df["upv_MWh"].sum()
            + cambium_data_df["distpv_MWh"].sum()
            + cambium_data_df["csp_MWh"].sum()
        ) / generation_annual_total_MWh
        generation_annual_battery_fraction = (
            cambium_data_df["battery_MWh"].sum()
        ) / generation_annual_total_MWh
        nuclear_PWR_fraction = 0.655  # % of grid nuclear power from PWR, calculated from USNRC data
        # based on type and rated capacity
        nuclear_BWR_fraction = 0.345  # % of grid nuclear power from BWR, calculated from USNRC data
        # based on type and rated capacity
        # https://www.nrc.gov/reactors/operating/list-power-reactor-units.html
        geothermal_binary_fraction = 0.28  # % of grid geothermal power from binary,
        # average from EIA data and NREL Geothermal prospector
        geothermal_flash_fraction = 0.72  # % of grid geothermal power from flash,
        # average from EIA data and NREL Geothermal prospector
        # https://www.eia.gov/todayinenergy/detail.php?id=44576#

        # Calculate Grid Imbedded Emissions Intensity for cambium grid mix of power sources
        # (kg CO2e/kwh)
        grid_capex_EI = (
            (generation_annual_nuclear_fraction * nuclear_PWR_fraction * nuclear_PWR_capex_EI)
            + (generation_annual_nuclear_fraction * nuclear_BWR_fraction * nuclear_BWR_capex_EI)
            + (generation_annual_coal_oil_fraction * coal_capex_EI)
            + (generation_annual_gas_fraction * gas_capex_EI)
            + (generation_annual_bio_fraction * bio_capex_EI)
            + (
                generation_annual_geothermal_fraction
                * geothermal_binary_fraction
                * geothermal_binary_capex_EI
            )
            + (
                generation_annual_geothermal_fraction
                * geothermal_flash_fraction
                * geothermal_flash_capex_EI
            )
            + (generation_annual_hydro_fraction * hydro_capex_EI)
            + (generation_annual_wind_fraction * wind_capex_EI)
            + (generation_annual_solar_fraction * solar_pv_capex_EI)
            + (generation_annual_battery_fraction * battery_EI) * g_to_kg
        )

        # NOTE: current config assumes SMR, ATR, NH3, and Steel processes are always grid powered
        # electricity needed for these processes does not come from renewables
        # NOTE: this is reflective of the current state of modeling these systems in the code
        # at time of dev and should be updated to allow renewables in the future
        if "hybrid-grid" in grid_case:
            ## H2 production via electrolysis
            # Calculate grid-connected electrolysis emissions (kg CO2e/kg H2)
            # future cases should reflect targeted electrolyzer electricity usage
            EI_values["electrolysis_Scope3_EI"] = (
                ely_stack_and_BoP_capex_EI
                + (ely_H2O_consume * H2O_supply_EI)
                + (
                    (
                        electrolysis_scope3_grid_emissions
                        + (wind_capex_EI * g_to_kg * wind_annual_energy_kwh)
                        + (solar_pv_capex_EI * g_to_kg * solar_pv_annual_energy_kwh)
                        + (grid_capex_EI * electrolysis_grid_electricity_consume)
                    )
                    / h2_annual_prod_kg
                )
            )
            EI_values["electrolysis_Scope2_EI"] = (
                electrolysis_scope2_grid_emissions / h2_annual_prod_kg
            )
            EI_values["electrolysis_Scope1_EI"] = 0
            EI_values["electrolysis_Total_EI"] = (
                EI_values["electrolysis_Scope1_EI"]
                + EI_values["electrolysis_Scope2_EI"]
                + EI_values["electrolysis_Scope3_EI"]
            )

            # Calculate ammonia emissions via hybrid grid electrolysis (kg CO2e/kg NH3)
            EI_values["NH3_electrolysis_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["electrolysis_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_electrolysis_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_electrolysis_Scope1_EI"] = (
                NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            )
            EI_values["NH3_electrolysis_Total_EI"] = (
                EI_values["NH3_electrolysis_Scope1_EI"]
                + EI_values["NH3_electrolysis_Scope2_EI"]
                + EI_values["NH3_electrolysis_Scope3_EI"]
            )

            # Calculate steel emissions via hybrid grid electrolysis (kg CO2e/metric ton steel)
            EI_values["steel_electrolysis_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["electrolysis_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_electrolysis_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_electrolysis_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_electrolysis_Total_EI"] = (
                EI_values["steel_electrolysis_Scope1_EI"]
                + EI_values["steel_electrolysis_Scope2_EI"]
                + EI_values["steel_electrolysis_Scope3_EI"]
            )

        if "grid-only" in grid_case:
            ## H2 production via electrolysis
            # Calculate grid-connected electrolysis emissions (kg CO2e/kg H2)
            EI_values["electrolysis_Scope3_EI"] = (
                ely_stack_and_BoP_capex_EI
                + (ely_H2O_consume * H2O_supply_EI)
                + (
                    (
                        electrolysis_scope3_grid_emissions
                        + (grid_capex_EI * electrolysis_grid_electricity_consume)
                    )
                    / h2_annual_prod_kg
                )
            )
            EI_values["electrolysis_Scope2_EI"] = (
                electrolysis_scope2_grid_emissions / h2_annual_prod_kg
            )
            EI_values["electrolysis_Scope1_EI"] = 0
            EI_values["electrolysis_Total_EI"] = (
                EI_values["electrolysis_Scope1_EI"]
                + EI_values["electrolysis_Scope2_EI"]
                + EI_values["electrolysis_Scope3_EI"]
            )

            # Calculate ammonia emissions via grid only electrolysis (kg CO2e/kg NH3)
            EI_values["NH3_electrolysis_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["electrolysis_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_electrolysis_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_electrolysis_Scope1_EI"] = (
                NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            )
            EI_values["NH3_electrolysis_Total_EI"] = (
                EI_values["NH3_electrolysis_Scope1_EI"]
                + EI_values["NH3_electrolysis_Scope2_EI"]
                + EI_values["NH3_electrolysis_Scope3_EI"]
            )

            # Calculate steel emissions via grid only electrolysis (kg CO2e/metric ton steel)
            EI_values["steel_electrolysis_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["electrolysis_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_electrolysis_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_electrolysis_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_electrolysis_Total_EI"] = (
                EI_values["steel_electrolysis_Scope1_EI"]
                + EI_values["steel_electrolysis_Scope2_EI"]
                + EI_values["steel_electrolysis_Scope3_EI"]
            )

            ## H2 production via SMR
            # Calculate SMR emissions. SMR and SMR + CCS are always grid-connected (kg CO2e/kg H2)
            EI_values["smr_Scope3_EI"] = (
                (NG_supply_EI * g_to_kg * (smr_NG_consume - smr_steam_prod / smr_HEX_eff))
                + (
                    smr_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (smr_electricity_consume * grid_capex_EI)
            )
            EI_values["smr_Scope2_EI"] = (
                smr_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["smr_Scope1_EI"] = (
                NG_combust_EI * g_to_kg * (smr_NG_consume - smr_steam_prod / smr_HEX_eff)
            )
            EI_values["smr_Total_EI"] = (
                EI_values["smr_Scope1_EI"] + EI_values["smr_Scope2_EI"] + EI_values["smr_Scope3_EI"]
            )

            # Calculate ammonia emissions via SMR process (kg CO2e/kg NH3)
            EI_values["NH3_smr_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["smr_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_smr_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_smr_Scope1_EI"] = NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            EI_values["NH3_smr_Total_EI"] = (
                EI_values["NH3_smr_Scope1_EI"]
                + EI_values["NH3_smr_Scope2_EI"]
                + EI_values["NH3_smr_Scope3_EI"]
            )

            # Calculate steel emissions via SMR process (kg CO2e/metric ton steel)
            EI_values["steel_smr_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["smr_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_smr_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_smr_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_smr_Total_EI"] = (
                EI_values["steel_smr_Scope1_EI"]
                + EI_values["steel_smr_Scope2_EI"]
                + EI_values["steel_smr_Scope3_EI"]
            )

            # Calculate SMR + CCS emissions (kg CO2e/kg H2)
            EI_values["smr_ccs_Scope3_EI"] = (
                (NG_supply_EI * g_to_kg * (smr_ccs_NG_consume - smr_ccs_steam_prod / smr_HEX_eff))
                + (
                    smr_ccs_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (smr_ccs_electricity_consume * grid_capex_EI)
            )
            EI_values["smr_ccs_Scope2_EI"] = (
                smr_ccs_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["smr_ccs_Scope1_EI"] = (
                (1 - smr_ccs_perc_capture)
                * NG_combust_EI
                * g_to_kg
                * (smr_ccs_NG_consume - smr_ccs_steam_prod / smr_HEX_eff)
            )
            EI_values["smr_ccs_Total_EI"] = (
                EI_values["smr_ccs_Scope1_EI"]
                + EI_values["smr_ccs_Scope2_EI"]
                + EI_values["smr_ccs_Scope3_EI"]
            )

            # Calculate ammonia emissions via SMR with CCS process (kg CO2e/kg NH3)
            EI_values["NH3_smr_ccs_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["smr_ccs_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_smr_ccs_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_smr_ccs_Scope1_EI"] = NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            EI_values["NH3_smr_ccs_Total_EI"] = (
                EI_values["NH3_smr_ccs_Scope1_EI"]
                + EI_values["NH3_smr_ccs_Scope2_EI"]
                + EI_values["NH3_smr_ccs_Scope3_EI"]
            )

            # Calculate steel emissions via SMR with CCS process (kg CO2e/metric ton steel)
            EI_values["steel_smr_ccs_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["smr_ccs_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_smr_ccs_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_smr_ccs_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_smr_ccs_Total_EI"] = (
                EI_values["steel_smr_ccs_Scope1_EI"]
                + EI_values["steel_smr_ccs_Scope2_EI"]
                + EI_values["steel_smr_ccs_Scope3_EI"]
            )

            ## H2 production via ATR
            # Calculate ATR emissions. ATR and ATR + CCS are always grid-connected (kg CO2e/kg H2)
            EI_values["atr_Scope3_EI"] = (
                (NG_supply_EI * g_to_kg * atr_NG_consume)
                + (
                    atr_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (atr_electricity_consume * grid_capex_EI)
            )
            EI_values["atr_Scope2_EI"] = (
                atr_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["atr_Scope1_EI"] = NG_combust_EI * g_to_kg * atr_NG_consume
            EI_values["atr_Total_EI"] = (
                EI_values["atr_Scope1_EI"] + EI_values["atr_Scope2_EI"] + EI_values["atr_Scope3_EI"]
            )

            # Calculate ammonia emissions via ATR process (kg CO2e/kg NH3)
            EI_values["NH3_atr_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["atr_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_atr_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_atr_Scope1_EI"] = NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            EI_values["NH3_atr_Total_EI"] = (
                EI_values["NH3_atr_Scope1_EI"]
                + EI_values["NH3_atr_Scope2_EI"]
                + EI_values["NH3_atr_Scope3_EI"]
            )

            # Calculate steel emissions via ATR process (kg CO2e/metric ton steel)
            EI_values["steel_atr_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["atr_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_atr_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_atr_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_atr_Total_EI"] = (
                EI_values["steel_atr_Scope1_EI"]
                + EI_values["steel_atr_Scope2_EI"]
                + EI_values["steel_atr_Scope3_EI"]
            )

            # Calculate ATR + CCS emissions (kg CO2e/kg H2)
            EI_values["atr_ccs_Scope3_EI"] = (
                (NG_supply_EI * g_to_kg * atr_ccs_NG_consume)
                + (
                    atr_ccs_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (atr_ccs_electricity_consume * grid_capex_EI)
            )
            EI_values["atr_ccs_Scope2_EI"] = (
                atr_ccs_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["atr_ccs_Scope1_EI"] = (
                (1 - atr_ccs_perc_capture) * NG_combust_EI * g_to_kg * atr_ccs_NG_consume
            )
            EI_values["atr_ccs_Total_EI"] = (
                EI_values["atr_ccs_Scope1_EI"]
                + EI_values["atr_ccs_Scope2_EI"]
                + EI_values["atr_ccs_Scope3_EI"]
            )

            # Calculate ammonia emissions via ATR with CCS process (kg CO2e/kg NH3)
            EI_values["NH3_atr_ccs_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["atr_ccs_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_atr_ccs_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_atr_ccs_Scope1_EI"] = NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            EI_values["NH3_atr_ccs_Total_EI"] = (
                EI_values["NH3_atr_ccs_Scope1_EI"]
                + EI_values["NH3_atr_ccs_Scope2_EI"]
                + EI_values["NH3_atr_ccs_Scope3_EI"]
            )

            # Calculate steel emissions via ATR with CCS process (kg CO2e/metric ton steel)
            EI_values["steel_atr_ccs_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["atr_ccs_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_atr_ccs_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_atr_ccs_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_atr_ccs_Total_EI"] = (
                EI_values["steel_atr_ccs_Scope1_EI"]
                + EI_values["steel_atr_ccs_Scope2_EI"]
                + EI_values["steel_atr_ccs_Scope3_EI"]
            )

        if "off-grid" in grid_case:
            ## H2 production via electrolysis
            # Calculate renewable only electrolysis emissions (kg CO2e/kg H2)
            EI_values["electrolysis_Scope3_EI"] = (
                ely_stack_and_BoP_capex_EI
                + (ely_H2O_consume * H2O_supply_EI)
                + (
                    (
                        (wind_capex_EI * g_to_kg * wind_annual_energy_kwh)
                        + (solar_pv_capex_EI * g_to_kg * solar_pv_annual_energy_kwh)
                    )
                    / h2_annual_prod_kg
                )
            )
            EI_values["electrolysis_Scope2_EI"] = 0
            EI_values["electrolysis_Scope1_EI"] = 0
            EI_values["electrolysis_Total_EI"] = (
                EI_values["electrolysis_Scope1_EI"]
                + EI_values["electrolysis_Scope2_EI"]
                + EI_values["electrolysis_Scope3_EI"]
            )

            # Calculate ammonia emissions via renewable electrolysis (kg CO2e/kg NH3)
            EI_values["NH3_electrolysis_Scope3_EI"] = (
                (NH3_H2_consume * EI_values["electrolysis_Total_EI"])
                + (NH3_NG_consume * NG_supply_EI * g_to_kg / MT_to_kg)
                + (
                    NH3_electricity_consume
                    * kWh_to_MWh
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (NH3_electricity_consume * grid_capex_EI)
            )
            EI_values["NH3_electrolysis_Scope2_EI"] = (
                NH3_electricity_consume
                * kWh_to_MWh
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["NH3_electrolysis_Scope1_EI"] = (
                NH3_NG_consume * NG_combust_EI * g_to_kg / MT_to_kg
            )
            EI_values["NH3_electrolysis_Total_EI"] = (
                EI_values["NH3_electrolysis_Scope1_EI"]
                + EI_values["NH3_electrolysis_Scope2_EI"]
                + EI_values["NH3_electrolysis_Scope3_EI"]
            )

            # Calculate steel emissions via renewable electrolysis (kg CO2e/metric ton steel)
            EI_values["steel_electrolysis_Scope3_EI"] = (
                (steel_H2_consume * MT_to_kg * EI_values["electrolysis_Total_EI"])
                + (steel_lime_consume * lime_supply_EI * MT_to_kg)
                + (steel_iron_ore_consume * iron_ore_mining_EI_per_MT_ore)
                + (steel_iron_ore_consume * iron_ore_pelletizing_EI_per_MT_ore)
                + (steel_NG_consume * NG_supply_EI)
                + (steel_H2O_consume * (H2O_supply_EI / gal_H2O_to_MT))
                + (
                    steel_electricity_consume
                    * cambium_data_df["LRMER CO2 equiv. precombustion (kg-CO2e/MWh)"].mean()
                )
                + (steel_electricity_consume * MWh_to_kWh * grid_capex_EI)
            )
            EI_values["steel_electrolysis_Scope2_EI"] = (
                steel_electricity_consume
                * cambium_data_df["LRMER CO2 equiv. combustion (kg-CO2e/MWh)"].mean()
            )
            EI_values["steel_electrolysis_Scope1_EI"] = steel_NG_consume * NG_combust_EI
            EI_values["steel_electrolysis_Total_EI"] = (
                EI_values["steel_electrolysis_Scope1_EI"]
                + EI_values["steel_electrolysis_Scope2_EI"]
                + EI_values["steel_electrolysis_Scope3_EI"]
            )

        # Append emission intensity values for each year to lists in the ts_EI_data dictionary
        for key in ts_EI_data:
            ts_EI_data[key].append(EI_values[key])

    ## Interpolation of emission intensities for years not captured by cambium
    # (cambium 2023 offers 2025-2050 in 5 year increments)
    # Define end of life based on cambium_year and project lifetime
    endoflife_year = cambium_year + project_lifetime

    # Instantiate dictionary of lists to hold full EI time series (ts) data
    # including interpolated data for years when cambium data is not available
    ts_EI_data_interpolated = {
        f"{process}_{scope}_EI": [] for process in processes for scope in scopes
    }

    # Loop through years between cambium_year and endoflife_year, interpolate values
    # Check if the defined cambium_year is less than the earliest data year available
    # from the cambium API, flag and warn users
    if cambium_year < min(cambium_data.cambium_years):
        cambium_year_warning_message = """Warning, the earliest year available for cambium data is
        {min_cambium_year}! For all years less than {min_cambium_year}, LCA calculations will use
        Cambium data from {min_cambium_year}. Thus, calculated emission intensity values for these
        years may be understated.""".format(min_cambium_year=min(cambium_data.cambium_years))
        print("****************** WARNING ******************")
        warnings.warn(cambium_year_warning_message)
        cambium_warning_flag = True
    else:
        cambium_warning_flag = False
    for year in range(cambium_year, endoflife_year):
        # if year < the minimum cambium_year (currently 2025 in Cambium 2023)
        # use data from the minimum year
        if year < min(cambium_data.cambium_years):
            for key in ts_EI_data_interpolated:
                ts_EI_data_interpolated[key].append(ts_EI_data[key][0])

        # else if year <= the maximum cambium_year (currently 2050 in Cambium 2023)
        # interpolate the values (copies existing values if year is already present)
        elif year <= max(cambium_data.cambium_years):
            for key in ts_EI_data_interpolated:
                ts_EI_data_interpolated[key].append(
                    np.interp(year, cambium_data.cambium_years, ts_EI_data[key])
                )

        # else if year > maximum cambium_year, copy data from maximum year (ie: copy data from 2050)
        else:
            for key in ts_EI_data_interpolated:
                ts_EI_data_interpolated[key].append(ts_EI_data[key][-1])

    # Put all cumulative metrics and relevant data into a dictionary, then dataframe
    # return the dataframe, save results to csv in post_processing()
    lca_dict = {
        "Cambium Warning": [cambium_year_warning_message if cambium_warning_flag else "None"],
        "Total Life Cycle H2 Production (kg-H2)": [h2_lifetime_prod_kg],
        "Electrolysis Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["electrolysis_Scope3_EI"])) / project_lifetime
        ],
        "Electrolysis Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["electrolysis_Scope2_EI"])) / project_lifetime
        ],
        "Electrolysis Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["electrolysis_Scope1_EI"])) / project_lifetime
        ],
        "Electrolysis Total Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["electrolysis_Total_EI"])) / project_lifetime
        ],
        "Ammonia Electrolysis Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_electrolysis_Scope3_EI"]))
            / project_lifetime
        ],
        "Ammonia Electrolysis Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_electrolysis_Scope2_EI"]))
            / project_lifetime
        ],
        "Ammonia Electrolysis Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_electrolysis_Scope1_EI"]))
            / project_lifetime
        ],
        "Ammonia Electrolysis Total Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_electrolysis_Total_EI"])) / project_lifetime
        ],
        "Steel Electrolysis Scope 3 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_electrolysis_Scope3_EI"]))
            / project_lifetime
        ],
        "Steel Electrolysis Scope 2 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_electrolysis_Scope2_EI"]))
            / project_lifetime
        ],
        "Steel Electrolysis Scope 1 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_electrolysis_Scope1_EI"]))
            / project_lifetime
        ],
        "Steel Electrolysis Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_electrolysis_Total_EI"]))
            / project_lifetime
        ],
        "SMR Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_Scope3_EI"])) / project_lifetime
        ],
        "SMR Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_Scope2_EI"])) / project_lifetime
        ],
        "SMR Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_Scope1_EI"])) / project_lifetime
        ],
        "SMR Total Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_Total_EI"])) / project_lifetime
        ],
        "Ammonia SMR Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_Scope3_EI"])) / project_lifetime
        ],
        "Ammonia SMR Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_Scope2_EI"])) / project_lifetime
        ],
        "Ammonia SMR Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_Scope1_EI"])) / project_lifetime
        ],
        "Ammonia SMR Total Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_Total_EI"])) / project_lifetime
        ],
        "Steel SMR Scope 3 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_Scope3_EI"])) / project_lifetime
        ],
        "Steel SMR Scope 2 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_Scope2_EI"])) / project_lifetime
        ],
        "Steel SMR Scope 1 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_Scope1_EI"])) / project_lifetime
        ],
        "Steel SMR Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_Total_EI"])) / project_lifetime
        ],
        "SMR with CCS Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_ccs_Scope3_EI"])) / project_lifetime
        ],
        "SMR with CCS Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_ccs_Scope2_EI"])) / project_lifetime
        ],
        "SMR with CCS Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_ccs_Scope1_EI"])) / project_lifetime
        ],
        "SMR with CCS Total Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["smr_ccs_Total_EI"])) / project_lifetime
        ],
        "Ammonia SMR with CCS Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_ccs_Scope3_EI"])) / project_lifetime
        ],
        "Ammonia SMR with CCS Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_ccs_Scope2_EI"])) / project_lifetime
        ],
        "Ammonia SMR with CCS Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_ccs_Scope1_EI"])) / project_lifetime
        ],
        "Ammonia SMR with CCS Total Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_smr_ccs_Total_EI"])) / project_lifetime
        ],
        "Steel SMR with CCS Scope 3 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_ccs_Scope3_EI"])) / project_lifetime
        ],
        "Steel SMR with CCS Scope 2 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_ccs_Scope2_EI"])) / project_lifetime
        ],
        "Steel SMR with CCS Scope 1 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_ccs_Scope1_EI"])) / project_lifetime
        ],
        "Steel SMR with CCS Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_smr_ccs_Total_EI"])) / project_lifetime
        ],
        "ATR Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_Scope3_EI"])) / project_lifetime
        ],
        "ATR Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_Scope2_EI"])) / project_lifetime
        ],
        "ATR Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_Scope1_EI"])) / project_lifetime
        ],
        "ATR Total Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_Total_EI"])) / project_lifetime
        ],
        "Ammonia ATR Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_Scope3_EI"])) / project_lifetime
        ],
        "Ammonia ATR Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_Scope2_EI"])) / project_lifetime
        ],
        "Ammonia ATR Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_Scope1_EI"])) / project_lifetime
        ],
        "Ammonia ATR Total Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_Total_EI"])) / project_lifetime
        ],
        "Steel ATR Scope 3 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_Scope3_EI"])) / project_lifetime
        ],
        "Steel ATR Scope 2 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_Scope2_EI"])) / project_lifetime
        ],
        "Steel ATR Scope 1 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_Scope1_EI"])) / project_lifetime
        ],
        "Steel ATR Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_Total_EI"])) / project_lifetime
        ],
        "ATR with CCS Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_ccs_Scope3_EI"])) / project_lifetime
        ],
        "ATR with CCS Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_ccs_Scope2_EI"])) / project_lifetime
        ],
        "ATR with CCS Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_ccs_Scope1_EI"])) / project_lifetime
        ],
        "ATR with CCS Total Lifetime Average GHG Emissions (kg-CO2e/kg-H2)": [
            sum(np.asarray(ts_EI_data_interpolated["atr_ccs_Total_EI"])) / project_lifetime
        ],
        "Ammonia ATR with CCS Scope 3 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_ccs_Scope3_EI"])) / project_lifetime
        ],
        "Ammonia ATR with CCS Scope 2 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_ccs_Scope2_EI"])) / project_lifetime
        ],
        "Ammonia ATR with CCS Scope 1 Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_ccs_Scope1_EI"])) / project_lifetime
        ],
        "Ammonia ATR with CCS Total Lifetime Average GHG Emissions (kg-CO2e/kg-NH3)": [
            sum(np.asarray(ts_EI_data_interpolated["NH3_atr_ccs_Total_EI"])) / project_lifetime
        ],
        "Steel ATR with CCS Scope 3 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_ccs_Scope3_EI"])) / project_lifetime
        ],
        "Steel ATR with CCS Scope 2 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_ccs_Scope2_EI"])) / project_lifetime
        ],
        "Steel ATR with CCS Scope 1 Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_ccs_Scope1_EI"])) / project_lifetime
        ],
        "Steel ATR with CCS Total Lifetime Average GHG Emissions (kg-CO2e/MT steel)": [
            sum(np.asarray(ts_EI_data_interpolated["steel_atr_ccs_Total_EI"])) / project_lifetime
        ],
        "Site Latitude": [site_latitude],
        "Site Longitude": [site_longitude],
        "Cambium Year": [cambium_year],
        "Electrolysis Case": [electrolyzer_centralization],
        "Grid Case": [grid_case],
        "Renewables Case": [renewables_case],
        "Wind Turbine Rating (MW)": [wind_turbine_rating_MW],
        "Wind Model": [wind_model],
        "Electrolyzer Degradation Modeled": [electrolyzer_degradation],
        "Electrolyzer Stack Optimization": [electrolyzer_optimized],
        f"Number of {electrolyzer_type} Electrolyzer Clusters": [number_of_electrolyzer_clusters],
        "Electricity ITC (%/100 CapEx)": [tax_incentive_option["electricity_itc"]],
        "Electricity PTC ($/kWh 1992 dollars)": [tax_incentive_option["electricity_ptc"]],
        "H2 Storage ITC (%/100 CapEx)": [tax_incentive_option["h2_storage_itc"]],
        "H2 PTC ($/kWh 2022 dollars)": [tax_incentive_option["h2_ptc"]],
    }

    lca_df = pd.DataFrame(data=lca_dict)

    return lca_df


# set up function to post-process HOPP results
def post_process_simulation(
    lcoe,
    lcoh,
    pf_lcoh,
    pf_lcoe,
    hopp_results,
    electrolyzer_physics_results,
    hopp_config,
    greenheart_config,
    orbit_config,
    turbine_config,
    h2_storage_results,
    total_accessory_power_renewable_kw,
    total_accessory_power_grid_kw,
    capex_breakdown,
    opex_breakdown,
    wind_cost_results,
    platform_results,
    desal_results,
    design_scenario,
    plant_design_number,
    incentive_option,
    solver_results=[],
    show_plots=False,
    save_plots=False,
    verbose=False,
    output_dir="./output/",
):  # , lcoe, lcoh, lcoh_with_grid, lcoh_grid_only):
    if isinstance(output_dir, str):
        output_dir = Path(output_dir).resolve()
    # colors (official NREL color palette https://brand.nrel.gov/content/index/guid/color_palette?parent=61)
    colors = [
        "#0079C2",
        "#00A4E4",
        "#F7A11A",
        "#FFC423",
        "#5D9732",
        "#8CC63F",
        "#5E6A71",
        "#D1D5D8",
        "#933C06",
        "#D9531E",
    ]

    # post process results
    if verbose:
        print("LCOE: ", round(lcoe * 1e3, 2), "$/MWh")
        print("LCOH: ", round(lcoh, 2), "$/kg")
        print(
            "hybrid electricity plant capacity factor: ",
            round(
                np.sum(hopp_results["combined_hybrid_power_production_hopp"])
                / (hopp_results["hybrid_plant"].system_capacity_kw.hybrid * 365 * 24),
                2,
            ),
        )
        print(
            "electrolyzer capacity factor: ",
            round(
                np.sum(electrolyzer_physics_results["power_to_electrolyzer_kw"])
                * 1e-3
                / (greenheart_config["electrolyzer"]["rating"] * 365 * 24),
                2,
            ),
        )
        print(
            "Electrolyzer CAPEX installed $/kW: ",
            round(
                capex_breakdown["electrolyzer"]
                / (greenheart_config["electrolyzer"]["rating"] * 1e3),
                2,
            ),
        )

    # Run LCA analysis if config yaml flag = True
    if greenheart_config["lca_config"]["run_lca"]:
        lca_df = calculate_lca(
            hopp_results=hopp_results,
            electrolyzer_physics_results=electrolyzer_physics_results,
            hopp_config=hopp_config,
            greenheart_config=greenheart_config,
            total_accessory_power_renewable_kw=total_accessory_power_renewable_kw,
            total_accessory_power_grid_kw=total_accessory_power_grid_kw,
            plant_design_scenario_number=plant_design_number,
            incentive_option_number=incentive_option,
        )

    if show_plots or save_plots:
        visualize_plant(
            hopp_config,
            greenheart_config,
            turbine_config,
            wind_cost_results,
            hopp_results,
            platform_results,
            desal_results,
            h2_storage_results,
            electrolyzer_physics_results,
            design_scenario,
            colors,
            plant_design_number,
            show_plots=show_plots,
            save_plots=save_plots,
            output_dir=output_dir,
        )
    savepaths = [
        output_dir / "data/",
        output_dir / "data/lcoe/",
        output_dir / "data/lcoh/",
        output_dir / "data/lca/",
    ]
    for sp in savepaths:
        if not sp.exists():
            sp.mkdir(parents=True)

    pf_lcoh.get_cost_breakdown().to_csv(
        savepaths[2]
        / f'cost_breakdown_lcoh_design{plant_design_number}_incentive{incentive_option}_{greenheart_config["h2_storage"]["type"]}storage.csv'  # noqa: E501
    )
    pf_lcoe.get_cost_breakdown().to_csv(
        savepaths[1]
        / f'cost_breakdown_lcoe_design{plant_design_number}_incentive{incentive_option}_{greenheart_config["h2_storage"]["type"]}storage.csv'  # noqa: E501
    )

    # Save LCA results if analysis was run
    if greenheart_config["lca_config"]["run_lca"]:
        lca_savepath = (
            savepaths[3]
            / f'LCA_results_design{plant_design_number}_incentive{incentive_option}_{greenheart_config["h2_storage"]["type"]}storage.csv'  # noqa: E501
        )
        lca_df.to_csv(lca_savepath)
        print("LCA Analysis was run as a postprocessing step. Results were saved to:")
        print(lca_savepath)

    # create dataframe for saving all the stuff
    greenheart_config["design_scenario"] = design_scenario
    greenheart_config["plant_design_number"] = plant_design_number
    greenheart_config["incentive_options"] = incentive_option

    # save power usage data
    if len(solver_results) > 0:
        hours = len(hopp_results["combined_hybrid_power_production_hopp"])
        annual_energy_breakdown = {
            "electricity_generation_kwh": sum(
                hopp_results["combined_hybrid_power_production_hopp"]
            ),
            "electrolyzer_kwh": sum(electrolyzer_physics_results["power_to_electrolyzer_kw"]),
            "renewable_kwh": sum(solver_results[0]),
            "grid_power_kwh": sum(solver_results[1]),
            "desal_kwh": solver_results[2] * hours,
            "h2_transport_compressor_power_kwh": solver_results[3] * hours,
            "h2_storage_power_kwh": solver_results[4] * hours,
            "electrolyzer_bop_energy_kwh": sum(solver_results[5]),
        }

    ######################### save detailed ORBIT cost information
    if wind_cost_results.orbit_project:
        _, orbit_capex_breakdown, wind_capex_multiplier = adjust_orbit_costs(
            orbit_project=wind_cost_results.orbit_project,
            greenheart_config=greenheart_config,
        )

        # orbit_capex_breakdown["Onshore Substation"] = orbit_project.phases["ElectricalDesign"].onshore_cost  # noqa: E501
        # discount ORBIT cost information
        for key in orbit_capex_breakdown:
            orbit_capex_breakdown[key] = -npf.fv(
                greenheart_config["finance_parameters"]["costing_general_inflation"],
                greenheart_config["project_parameters"]["cost_year"]
                - greenheart_config["finance_parameters"]["discount_years"]["wind"],
                0.0,
                orbit_capex_breakdown[key],
            )

        # save ORBIT cost information
        ob_df = pd.DataFrame(orbit_capex_breakdown, index=[0]).transpose()
        savedir = output_dir / "data/orbit_costs/"
        if not savedir.exists():
            savedir.mkdir(parents=True)
        ob_df.to_csv(
            savedir
            / f'orbit_cost_breakdown_lcoh_design{plant_design_number}_incentive{incentive_option}_{greenheart_config["h2_storage"]["type"]}storage.csv'  # noqa: E501
        )
        ###############################

        ###################### Save export system breakdown from ORBIT ###################

        _, orbit_capex_breakdown, wind_capex_multiplier = adjust_orbit_costs(
            orbit_project=wind_cost_results.orbit_project,
            greenheart_config=greenheart_config,
        )

        onshore_substation_costs = (
            wind_cost_results.orbit_project.phases["ElectricalDesign"].onshore_cost
            * wind_capex_multiplier
        )

        orbit_capex_breakdown["Export System Installation"] -= onshore_substation_costs

        orbit_capex_breakdown["Onshore Substation and Installation"] = onshore_substation_costs

        # discount ORBIT cost information
        for key in orbit_capex_breakdown:
            orbit_capex_breakdown[key] = -npf.fv(
                greenheart_config["finance_parameters"]["costing_general_inflation"],
                greenheart_config["project_parameters"]["cost_year"]
                - greenheart_config["finance_parameters"]["discount_years"]["wind"],
                0.0,
                orbit_capex_breakdown[key],
            )

        # save ORBIT cost information using directory defined above
        ob_df = pd.DataFrame(orbit_capex_breakdown, index=[0]).transpose()
        ob_df.to_csv(
            savedir
            / f'orbit_cost_breakdown_with_onshore_substation_lcoh_design{plant_design_number}_incentive{incentive_option}_{greenheart_config["h2_storage"]["type"]}storage.csv'  # noqa: E501
        )

    ##################################################################################
    if save_plots:
        if (
            hasattr(hopp_results["hybrid_plant"], "dispatch_builder")
            and hopp_results["hybrid_plant"].battery
        ):
            savedir = output_dir / "figures/production/"
            if not savedir.exists():
                savedir.mkdir(parents=True)
            plot_tools.plot_generation_profile(
                hopp_results["hybrid_plant"],
                start_day=0,
                n_days=10,
                plot_filename=(savedir / "generation_profile.pdf"),
                font_size=14,
                power_scale=1 / 1000,
                solar_color="r",
                wind_color="b",
                # wave_color="g",
                discharge_color="b",
                charge_color="r",
                gen_color="g",
                price_color="r",
                # show_price=False,
            )
        else:
            print(
                "generation profile not plotted because HoppInterface does not have a "
                "'dispatch_builder'"
            )

    # save production information
    hourly_energy_breakdown = save_energy_flows(
        hopp_results["hybrid_plant"],
        electrolyzer_physics_results,
        solver_results,
        hours,
        h2_storage_results,
        output_dir=output_dir,
    )

    # save hydrogen information
    key = "Hydrogen Hourly Production [kg/hr]"
    np.savetxt(
        output_dir / "h2_usage",
        electrolyzer_physics_results["H2_Results"][key],
        header="# " + key,
    )

    return annual_energy_breakdown, hourly_energy_breakdown
