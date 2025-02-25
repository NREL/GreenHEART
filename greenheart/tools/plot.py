import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def get_hour_from_datetime(dt_start: dt.datetime, dt_end: dt.datetime) -> tuple[int, int]:
    """Takes in two times in datetime format and returns the two times as hour of the year.
    This function is intended for use with plots where data may span a full year, but only
    a portion of the year is desired in a given plot.

    Args:
        dt_start (dt.datetime): start time in datetime format
        dt_end (dt.datetime): end time in datetime format

    Returns:
        hour_start (int): hour of the year corresponding to the provided start time
        hour_end (int): hour of the year corresponding to the provided end time
    """

    dt_beginning_of_year = dt.datetime(dt_start.year, 1, 1, tzinfo=dt_start.tzinfo)

    hour_start = int((dt_start - dt_beginning_of_year).total_seconds() // 3600)
    hour_end = int((dt_end - dt_beginning_of_year).total_seconds() // 3600)

    return hour_start, hour_end


def plot_hydrogen_flows(
    energy_flow_data_path: str = "./output/data/production/energy_flows.csv",
    start_date_time: dt.datetime = dt.datetime(2024, 1, 1, 0),
    end_date_time: dt.datetime = dt.datetime(2024, 12, 31, 23),
    save_path: str = "./output/figures/production/hydrogen-flow.pdf",
    show_fig: bool = True,
    save_fig: bool = True,
) -> None:
    """Generates a plot of the hydrogen dispatch from the greenheart output.

    Args:
        energy_flow_data_path (str): path to where the greenheart energy flow output file is saved
        start_date_time (dt.datetime, optional): start time for plot.
            Defaults to dt.datetime(2024, 1, 1, 0).
        end_date_time (dt.datetime, optional): end time for plot.
            Defaults to dt.datetime(2024, 12, 31, 23).
        save_path (str, optional): relative path for saving the resulting plot.
            Defaults to "./output/figures/production/hydrogen-flow.pdf".
        show_fig (bool, optional): if True, figure will be displayed.
            Defaults to True.
        save_fig (bool, optional): if True, figure will be saved.
            Defaults to True.
    """

    # set start and end dates
    hour_start, hour_end = get_hour_from_datetime(start_date_time, end_date_time)

    # load data
    df_data = pd.read_csv(energy_flow_data_path, index_col=0)
    df_data = df_data.iloc[hour_start:hour_end]

    # set up plots
    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(12, 6))

    # plot hydrogen production
    df_h_out = df_data[["h2 production hourly [kg]"]] * 1e-3  # convert to t
    h2_demand = df_h_out.mean().values[0]

    # plot storage SOC
    df_h_soc = np.array(df_data[["hydrogen storage SOC [kg]"]] * 1e-3)  # convert to t

    df_h_soc_change = np.array(
        [(df_h_soc[i] - df_h_soc[i - 1]) for i in np.arange(0, len(df_h_soc))]
    ).flatten()

    ax[0].plot(df_h_soc * 1e-3)
    ax[0].set(
        ylabel="H$_2$ storage SOC (kt)", xlabel="Hour", ylim=[0, np.ceil(np.max(df_h_soc * 1e-3))]
    )

    # plot net h2 available
    net_flow = np.array(df_h_out).flatten() - np.array(df_h_soc_change)
    ax[1].plot(df_h_out, "-", label="Electrolyzer output", alpha=0.5)
    ax[1].plot(net_flow, label="Net dispatch")
    ax[1].axhline(h2_demand, linestyle=":", label="Demand", color="k")
    ax[1].set(ylabel="Hydrogen (t)", xlabel="Hour", ylim=[0, np.max(df_h_out) * 1.4])
    ax[1].legend(frameon=False, ncol=3, loc=2)

    plt.tight_layout()

    if save_fig:
        plt.savefig(save_path, transparent=True)
    if show_fig:
        plt.show()


def plot_energy_flows(
    energy_flow_data_path: str = "./output/data/production/energy_flows.csv",
    start_date_time: dt.datetime = dt.datetime(2024, 1, 5, 14),
    end_date_time: dt.datetime = dt.datetime(2024, 1, 10, 14),
    save_path: str = "./output/figures/production/energy_flows.pdf",
    show_fig: bool = True,
    save_fig: bool = True,
) -> None:
    """Generates a plot of electricity and hydrogen dispatch for the specified period

    Args:
        energy_flow_data_path (str, optional): Path to energy flow output file.
            Defaults to Path("./output/figures/production/energy_flows.csv").
        start_date_time (dt.datetime, optional): Start time for plot.
            Defaults to dt.datetime(2024, 1, 5, 14).
        end_date_time (dt.datetime, optional): End time for plot.
            Defaults to dt.datetime(2024, 1, 10, 14).
        save_path (str, optional): Path to save figure to.
            Defaults to Path("./output/data/production/energy_flows.pdf").
        show_fig (bool, optional): If True, figures will be displayed.
            Defaults to True.
        save_fig (bool, optional): If True, figures will be saved.
            Defaults to True.
    """

    # set start and end dates
    hour_start, hour_end = get_hour_from_datetime(start_date_time, end_date_time)

    # load data
    df_data = pd.read_csv(Path(energy_flow_data_path), index_col=0)
    df_data = df_data.iloc[hour_start:hour_end]

    # set up plots
    fig, ax = plt.subplots(2, 2, sharex=True, figsize=(10, 6))

    # plot electricity output
    # df_e_out = df_data[["wind generation [kW]", "pv generation [kW]", "wave generation [kW]"]]
    df_e_out_names = {}
    for col in df_data.columns.tolist():
        if ("generation" in col) and ("total" not in col):
            col_new = col.replace("kW", "GW")
            df_e_out_names[col] = col_new

    df_e_out = df_data[df_e_out_names.keys()] * 1e-6
    df_e_out = df_e_out.rename(columns=df_e_out_names)

    df_e_out.plot(
        ax=ax[0, 0],
        logy=False,
        ylabel="Electricity Output (GW)",
        ylim=[0, max(df_e_out["wind generation [GW]"]) * 1.5],
    )
    ax[0, 0].legend(frameon=False)

    # plot battery charge/discharge
    df_batt_power = df_data[["battery charge [kW]", "battery discharge [kW]"]] * 1e-6
    df_batt_power = df_batt_power.rename(
        columns={
            "battery charge [kW]": "battery charge [GW]",
            "battery discharge [kW]": "battery discharge [GW]",
        }
    )
    leg_info_batt_pow = df_batt_power.plot(
        ax=ax[0, 1],
        logy=False,
        ylabel="Battery Power (GW)",
        ylim=[
            0,
            max(
                [
                    max(df_batt_power["battery charge [GW]"]),
                    max(df_batt_power["battery discharge [GW]"]),
                ]
            )
            * 1.8,
        ],
        legend=False,
    )

    ax01_twin = ax[0, 1].twinx()

    df_batt_soc = df_data[["battery state of charge [%]"]]
    leg_info_batt_soc = df_batt_soc.plot(
        ax=ax01_twin,
        ylabel="Battery SOC (%)",
        linestyle=":",
        color="k",
        ylim=[0, max(df_batt_soc["battery state of charge [%]"]) * 1.8],
        legend=False,
    )

    leg_lines = leg_info_batt_pow.lines + leg_info_batt_soc.lines
    leg_labels = [leg.get_label() for leg in leg_lines]
    ax[0, 1].legend(leg_lines, leg_labels, frameon=False, loc=0)

    df_e_usage = (
        df_data[
            [
                "electrolyzer energy hourly [kW]",
            ]
        ]
        * 1e-6
    )
    df_e_usage = df_e_usage.rename(
        columns={"electrolyzer energy hourly [kW]": "electrolyzer energy hourly [GW]"}
    )
    df_e_usage.plot(
        ax=ax[1, 0],
        logy=False,
        ylabel="Electricity Usage (GW)",
        xlabel="Hour",
        ylim=[0, max(df_e_usage["electrolyzer energy hourly [GW]"]) * 1.5],
    )

    ax[1, 0].legend(frameon=False)

    # plot hydrogen production
    df_h_out = df_data[["h2 production hourly [kg]", "hydrogen storage SOC [kg]"]] * 1e-6
    df_h_out = df_h_out.rename(
        columns={
            "h2 production hourly [kg]": "H$_2$ produced hourly [kt]",
            "hydrogen storage SOC [kg]": "H$_2$ storage SOC [kt]",
        }
    )
    df_h_out.plot(ax=ax[1, 1], ylabel="Hydrogen Produced (kt)", xlabel="Hour")
    ax[1, 1].legend(frameon=False)

    plt.tight_layout()

    if save_fig:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, transparent=True)
    if show_fig:
        plt.show()


if __name__ == "__main__":
    energy_flows_data_path = "./output/data/production/energy_flows.csv"
    # plot_energy_flows(energy_flow_data_path=energy_flows_data_path)
    # plot_energy(energy_flow_data_path=energy_flows_data_path)
    plot_hydrogen_flows(energy_flows_data_path)
