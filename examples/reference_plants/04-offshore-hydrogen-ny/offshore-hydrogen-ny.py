# general imports
from pathlib import Path

# ORBIT imports
from ORBIT.core.library import initialize_library

# GreenHEART imports
from greenheart.simulation.greenheart_simulation import GreenHeartSimulationConfig
from greenheart.tools.optimization.gc_run_greenheart import run_greenheart


DATA_PATH = Path(__file__).parent / "input"
initialize_library(DATA_PATH)

# run the stuff
if __name__ == "__main__":
    # load inputs as needed
    turbine_model = "osw_15MW"
    filename_turbine_config = DATA_PATH / f"turbines/{turbine_model}.yaml"
    filename_floris_config = DATA_PATH / "floris/floris_input_osw_15MW.yaml"
    filename_hopp_config = DATA_PATH / "plant/hopp_config_ny.yaml"
    filename_orbit_config = DATA_PATH / f"plant/orbit-config-{turbine_model}-ny.yaml"
    filename_greenheart_config = DATA_PATH / "plant/greenheart_config_offshore_ny.yaml"

    config = GreenHeartSimulationConfig(
        filename_hopp_config=filename_hopp_config,
        filename_greenheart_config=filename_greenheart_config,
        filename_turbine_config=filename_turbine_config,
        filename_orbit_config=filename_orbit_config,
        filename_floris_config=filename_floris_config,
        verbose=True,
        show_plots=False,
        save_plots=True,
        use_profast=True,
        post_processing=True,
        incentive_option=1,
        plant_design_scenario=1,
        output_level=5,
    )

    # for analysis
    prob, config = run_greenheart(config, run_only=True)

    # for optimization
    # prob, config = run_greenheart(config, run_only=False)

    lcoe = prob.get_val("lcoe", units="USD/(MW*h)")
    lcoh = prob.get_val("lcoh", units="USD/kg")

    print("LCOE: ", lcoe, "[$/MWh]")
    print("LCOH: ", lcoh, "[$/kg]")
