import os
import excel as ex
import numpy as np

from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import misc as mc


def plot_Structure(Structure, Added_Masses, waterdepth=None, height_ref="", waterlevel=0, show_section_numbers=True):


    fig, ax = plt.subplots(1, 3, figsize=[22, 6])

    # Check if Structure is empty
    structure_empty = Structure.empty

    if not structure_empty:
        top_structure = Structure["Top [m]"].max()
        bottom_structure = Structure["Bottom [m]"].min()
        left = -max(Structure["D, top [m]"].max(), Structure["D, bottom [m]"].max()) / 2
        right = -left
    else:
        top_structure = -np.inf
        bottom_structure = np.inf
        left, right = -1.0, 1.0  # Default limits

    # Use Added_Masses if present to help set limits
    if not Added_Masses.empty:
        top_masses = Added_Masses["Top [m]"].max()
        bottom_masses = Added_Masses["Bottom [m]"].min()
        top_all = max(top_structure, top_masses)
        bottom_all = min(bottom_structure, bottom_masses)
    else:
        top_all = top_structure if top_structure != -np.inf else 10
        bottom_all = bottom_structure if bottom_structure != np.inf else 0

    for ax_curr in ax:
        ax_curr.set_ylim(bottom_all - 0.05 * (top_all - bottom_all), top_all + 0.05 * (top_all - bottom_all))
        ax_curr.grid(True, linestyle='--')

    # Plot 1: Structure overview
    axis = ax[0]
    if not structure_empty:
        plot_cans(Structure, axis, show_section_numbers=show_section_numbers, set_lims=False, color="k")

    if waterlevel is not None:
        axis.axhline(waterlevel, color="blue", linestyle="--")
    axis.axvline(0, color="grey", linestyle="--", linewidth=1)
    if waterdepth is not None:
        axis.axhline(waterdepth, color="brown", linestyle="-", linewidth=2)

    ticks = axis.get_xticks()
    axis.set_xticks(ticks[ticks >= 0])
    axis.set_xticklabels([f"{2 * t:.0f}" for t in ticks if t >= 0])
    axis.set_xlim(left - 0.4 * abs(right), right + 0.4 * abs(right))
    axis.set_xlabel("Diameter in [m]")
    axis.set_ylabel(f"z in m{height_ref}")
    axis.set_title("Overview and Diameter")

    # Plot 2: Added masses
    axis = ax[1]
    if not structure_empty:
        weight = mc.calc_weight(
            7850,
            Structure["t [mm]"],
            Structure["Top [m]"],
            Structure["Bottom [m]"],
            Structure["D, top [m]"],
            Structure["D, bottom [m]"]
        )
        grey = [0.8, 0.8, 0.8]
        plot_cans(Structure, axis, show_section_numbers=False, color=grey, set_lims=False)

    label_entries = []
    placed_z = defaultdict(int)
    tol = 0.050 * (top_all - bottom_all)
    x_step = 0.04 * (right - left)

    for _, mass in Added_Masses.iterrows():
        name = mass['Name']
        top = mass['Top [m]']
        bottom = mass['Bottom [m]']
        mass_val = mass['Mass [kg]']

        is_point = top == bottom
        z = top if is_point else (top + bottom) / 2

        z_key = round(z / tol) * tol
        index = placed_z[z_key]
        x_offset = index * x_step
        placed_z[z_key] += 1

        color = 'red' if is_point else 'blue'
        x_pos = x_offset

        if is_point:
            axis.plot(x_pos, z, 'o', color=color, markersize=8)
        else:
            axis.plot([x_pos, x_pos], [bottom, top], color=color, linewidth=6, alpha=0.6)

        label_entries.append({
            'y': z,
            'label': f"{name} ({mass_val:.0f} kg)",
            'color': color,
            'x_start': x_pos
        })

    # Labeling logic
    MAX_LABELS = 25
    if len(label_entries) <= MAX_LABELS:
        label_entries.sort(key=lambda x: -x['y'])
        occupied_y = []
        min_dy = 0.03 * (top_all - bottom_all)
        x_text = 0.6 * abs(right)

        for entry in label_entries:
            target_y = entry['y']
            while any(abs(target_y - oy) < min_dy for oy in occupied_y):
                target_y -= min_dy
            occupied_y.append(target_y)

            axis.plot([entry['x_start'], x_text - 0.05], [entry['y'], target_y], '-', color=entry['color'])
            axis.text(x_text, target_y, entry['label'], ha='left', va='center', fontsize=9, color=entry['color'])
    else:
        axis.text(0.8 * abs(right), 0.5 * (top_all + bottom_all), "Too many masses to label", ha='center', va='center', fontsize=13, color='red')

    axis.axvline(0, color="grey", linestyle="--", linewidth=1)
    axis.set_xlim(-0.1 * abs(right), 2 * abs(right))
    axis.set_title("Masses\n(horizontal displacement only for distinction, all lie on center line)")
    axis.set_xticks([])
    axis.set_xticklabels([])

    # Plot 3: Slope, Wall Thickness, D/t Ratio
    axis = ax[2]
    axis2 = axis.twiny()
    if not structure_empty:
        z_nodes = list(Structure["Top [m]"]) + [Structure["Bottom [m]"].values[-1]]
        t = list(Structure["t [mm]"] / 1000)
        slope = -(Structure["D, top [m]"] - Structure["D, bottom [m]"]) / (Structure["Top [m]"] - Structure["Bottom [m]"])
        D_nodes = list(Structure["D, top [m]"]) + [Structure["D, bottom [m]"].values[-1]]

        # D/t
        z_d_by_t = []
        d_by_t = []
        for _, row in Structure.iterrows():
            t_curr = row["t [mm]"]
            z_d_by_t += [row["Top [m]"], row["Bottom [m]"]]
            d_by_t += [row["D, top [m]"] / t_curr, row["D, bottom [m]"] / t_curr]

        slope_steps = [np.nan if s == 0 else s for s in slope]

        axis2.plot(d_by_t, z_d_by_t, label="D/t", color="C0")
        axis2.set_xlabel("D/t [-]")
        axis2.xaxis.set_label_position('top')
        axis2.xaxis.tick_top()

        line1 = axis.stairs(slope_steps, z_nodes, orientation="horizontal", label="slope (where not 0)", color="C1", baseline=None)
        line2 = axis.stairs(t, z_nodes, label="t [mm]", orientation="horizontal", color="C2", baseline=None)

        lines = [line1, line2]
        labels = [line.get_label() for line in lines]
        axis.legend(lines, labels, loc="lower left")

    axis.set_title("Slope, Wall Thickness, D/t Ratio")
    return fig

def plot_cans(Structure, axis, show_section_numbers=False, set_lims=True, **plot_kwargs):
    """
    Plots a structural representation of cylindrical segments ("cans") on a given Matplotlib axis.

    Parameters
    ----------
    Structure : pandas.DataFrame
        DataFrame describing the structure, with one row per cylindrical segment.
        Required columns:
        - "Top [m]": top elevation of each segment.
        - "Bottom [m]": bottom elevation of each segment.
        - "D, top [m]": diameter at the top of the segment.
        - "D, bottom [m]": diameter at the bottom of the segment.
        - "Section": (optional) section number used for labeling (required if `show_section_numbers=True`).

    axis : matplotlib.axes.Axes
        Matplotlib axis on which the cans will be drawn.

    show_section_numbers : bool, optional
        If True, displays section numbers at the center of each can.
        Requires the 'Section' column in `Structure`.

    set_lims : bool, optional
        If True, automatically sets the axis limits based on the geometry of the structure.

    **plot_kwargs : dict, optional
        Additional keyword arguments passed to `axis.plot()` for customizing line style, color, etc.

    Returns
    -------
    None
        The function modifies the provided `axis` in place.
    """
    if set_lims:
        top_all = Structure["Top [m]"].max()
        bottom_all = Structure["Bottom [m]"].min()
        left = -max(Structure["D, top [m]"].max(), Structure["D, bottom [m]"].max()) / 2
        right = -left
        axis.set_ylim(bottom_all - 0.05 * (top_all - bottom_all), top_all + 0.05 * (top_all - bottom_all))
        axis.set_xlim(left - 0.05 * (right - left), right + 0.05 * (right - left))

    for _, can in Structure.iterrows():
        up_left = (-can["D, top [m]"] / 2, can["Top [m]"])
        up_right = (can["D, top [m]"] / 2, can["Top [m]"])
        down_left = (-can["D, bottom [m]"] / 2, can["Bottom [m]"])
        down_right = (can["D, bottom [m]"] / 2, can["Bottom [m]"])

        axis.plot([down_left[0], up_left[0]], [down_left[1], up_left[1]], **plot_kwargs)
        axis.plot([down_right[0], up_right[0]], [down_right[1], up_right[1]], **plot_kwargs)
        axis.plot([down_left[0], down_right[0]], [down_left[1], down_right[1]], **plot_kwargs)
        axis.plot([up_left[0], up_right[0]], [up_left[1], up_right[1]], **plot_kwargs)

        if show_section_numbers:
            axis.text(0, (down_left[1] + up_left[1]) / 2, int(can["Section"]),
                      fontsize=8, ha='center', va='center', fontweight='bold')


def plot_Assambly(WHOLE_STRUCTURE, SKIRT=None, seabed=None, waterlevel=0, height_ref=""):
    """
    Plots the assembled offshore structure, showing its subcomponents (MP, TP, TOWER) and optionally a skirt.

    Parameters
    ----------
    WHOLE_STRUCTURE : pandas.DataFrame
        Combined structure data with one row per segment. Must include:
        - "Top [m]": top elevation of the segment.
        - "Bottom [m]": bottom elevation of the segment.
        - "D, top [m]": diameter at the top of the segment.
        - "D, bottom [m]": diameter at the bottom of the segment.
        - "Affiliation": string column specifying the component ("MP", "TP", or "TOWER").

    SKIRT : pandas.DataFrame, optional
        Additional structure to plot (e.g., skirt piles). Same structure as `WHOLE_STRUCTURE`.

    seabed : float, optional
        Elevation of the seabed in meters. If provided, a horizontal brown line will be plotted.

    waterlevel : float, default=0
        Elevation of the water level in meters. Shown as a dashed blue line.

    height_ref : str, optional
        Optional height reference string (e.g., " MSL") appended to the y-axis label.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The generated Matplotlib figure showing the assembled structure with appropriate annotations.

    Notes
    -----
    - MP (monopile), TP (transition piece), and TOWER segments are colored black, blue, and grey respectively.
    - The skirt (if provided) is colored red with partial transparency.
    - Diameters are doubled in the x-axis tick labels to represent total width.
    """
    fig, axis = plt.subplots(1, 1, figsize=[8, 27])

    MP_assambled = WHOLE_STRUCTURE.loc[WHOLE_STRUCTURE["Affiliation"] == "MP", :]
    TP_assambled = WHOLE_STRUCTURE.loc[WHOLE_STRUCTURE["Affiliation"] == "TP", :]
    TOWER_assambled = WHOLE_STRUCTURE.loc[WHOLE_STRUCTURE["Affiliation"] == "TOWER", :]

    if len(MP_assambled) != 0:
        plot_cans(MP_assambled, axis, show_section_numbers=False, color="k", set_lims=False)
    if len(TP_assambled) != 0:
        plot_cans(TP_assambled, axis, show_section_numbers=False, color="blue", set_lims=False)
    if len(TOWER_assambled) != 0:
        plot_cans(TOWER_assambled, axis, show_section_numbers=False, color="grey", set_lims=False)
    if SKIRT is not None:
        plot_cans(SKIRT, axis, show_section_numbers=False, color="red", set_lims=False, alpha=0.8)

    ticks = axis.get_xticks()
    axis.set_xticks(ticks[ticks >= 0])
    axis.set_xticklabels([f"{2 * t:.0f}" for t in ticks if t >= 0])
    axis.set_xlabel("Diameter in [m]")
    axis.set_ylabel(f"z in m{height_ref}")

    axis.axhline(waterlevel, color="blue", linestyle="--")
    axis.axvline(0, color="grey", linestyle="--", linewidth=1)
    if seabed is not None:
        axis.axhline(seabed, color="brown", linestyle="-", linewidth=2)

    return fig


def plot_Assambly_Build(excel_caller):
    """
    Reads structural component data from an Excel workbook, assembles the offshore structure,
    generates an assembly plot, and inserts it back into the Excel file.

    Parameters
    ----------
    excel_caller : str
        Full path to the Excel file from which to read structure data. The filename is extracted
        and used to read various component tables from the "BuildYourStructure" sheet.

    Reads From Excel
    ----------------
    Sheet: "BuildYourStructure"
        - "MP_DATA": Main pile geometry (required).
        - "TP_DATA": Transition piece geometry (required).
        - "TOWER_DATA": Tower geometry (required).
        - "MP_META": Metadata including:
            - "Water Depth [m]": Used to determine seabed elevation.
            - "Height Reference": Optional reference appended to the vertical axis label.

    Excel Output
    ------------
    Sheet: "BuildYourStructure"
        - Plot inserted into cell anchor labeled "Assambly_plot".

    Returns
    -------
    None
        This function performs operations with side effects:
        - Generates a structural assembly plot using `plot_Assambly`.
        - Inserts the figure into the provided Excel workbook.

    Notes
    -----
    - The function calls `mc.assemble_structure` to combine MP, TP, and TOWER into a unified DataFrame.
    - If the "Water Depth [m]" value in metadata is not numeric, seabed is ignored.
    - The assembled structure is visualized using the `plot_Assambly` function with color-coded segments.
    """
    excel_filename = os.path.basename(excel_caller)
    MP = ex.read_excel_table(excel_filename, "BuildYourStructure", f"MP_DATA", dtype=float, dropnan=True)
    TP = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TP_DATA", dtype=float, dropnan=True)
    TOWER = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TOWER_DATA", dtype=float, dropnan=True)
    META_MP = ex.read_excel_table(excel_filename, "BuildYourStructure", f"MP_META", dropnan=True)

    if len(META_MP) != 0:
        value = META_MP.loc[0, "Water Depth [m]"]
        seabed = -value if np.isreal(value) else None

        value = META_MP.loc[0, "Height Reference"]
        height_ref = value if value else None

    else:
        seabed = None
        height_ref = None

    if len(MP) > 0 and len(TP) > 0:
        WHOLE_STRUCTURE, _, SKIRT, _ = mc.assemble_structure(MP, TP, TOWER, interactive=False, ignore_hovering=True, overlapp_mode="Skirt")

    else:
        WHOLE_STRUCTURE = pd.DataFrame(columns=["Affiliation"])
        SKIRT = None
        ex.show_message_box(excel_filename, "Please fill MP and/or TP section to plot whole structure" )

    Fig = plot_Assambly(WHOLE_STRUCTURE, SKIRT=SKIRT, seabed=seabed, waterlevel=0, height_ref=height_ref)
    ex.insert_plot(Fig, excel_filename, "BuildYourStructure", f"Assambly_plot")


def plot_Assambly_Overview(excel_caller):
    excel_filename = os.path.basename(excel_caller)
    WHOLE_STRUCTURE = ex.read_excel_table(excel_filename, "StructureOverview", f"WHOLE_STRUCTURE", dropnan=True)
    ALL_ADDED_MASSES = ex.read_excel_table(excel_filename, "StructureOverview", f"ALL_ADDED_MASSES", dropnan=True)
    SKIRT_POINTMASS = ex.read_excel_table(excel_filename, "StructureOverview", f"SKIRT_POINTMASS", dropnan=True)
    SKIRT = ex.read_excel_table(excel_filename, "StructureOverview", f"SKIRT", dropnan=True)
    MARINE_GROWTH = ex.read_excel_table(excel_filename, "StructureOverview", f"MARINE_GROWTH", dropnan=True)
    HYDRO_COEFFICIENTS = ex.read_excel_table(excel_filename, "StructureOverview", f"HYDRO_COEFFICIENTS", dropnan=True)
    STRUCTURE_META = ex.read_excel_table(excel_filename, "StructureOverview", f"STRUCTURE_META", dropnan=True)

    water_level = STRUCTURE_META.loc[STRUCTURE_META["Parameter"] == "Water level", "Value"]
    if water_level.empty:
        water_level = None
    else:
        water_level = -water_level.values[0]

    seabed_level = STRUCTURE_META.loc[STRUCTURE_META["Parameter"] == "Seabed level", "Value"]
    if seabed_level.empty:
        seabed_level = None
    else:
        seabed_level = -seabed_level.values[0]

    height_ref = STRUCTURE_META.loc[STRUCTURE_META["Parameter"] == "Height Reference", "Value"]
    if height_ref.empty:
        height_ref = None
    else:
        height_ref = height_ref.values[0]


    Fig = plot_Assambly(WHOLE_STRUCTURE, SKIRT=SKIRT, waterlevel=water_level, seabed=-seabed_level, height_ref=height_ref)

    ex.insert_plot(Fig, excel_filename, "StructureOverview", f"Assambly_plot_Overview2")


def plot_MP(excel_caller):
    excel_filename = os.path.basename(excel_caller)
    Structure = ex.read_excel_table(excel_filename, "BuildYourStructure", f"MP_DATA", dtype=float)
    Added_Masses = ex.read_excel_table(excel_filename, "BuildYourStructure", f"MP_MASSES")
    Added_Masses = Added_Masses.dropna(how="all")
    Structure = Structure.dropna(how="all")

    META = ex.read_excel_table(excel_filename, "BuildYourStructure", f"MP_META")
    if len(META) != 0:
        value = META.loc[0, "Water Depth [m]"]
        waterdepth = -value if np.isreal(value) else None

        value = META.loc[0, "Height Reference"]
        height_ref = value if value else None

    else:
        waterdepth = None
        height_ref = None

    FIG = plot_Structure(Structure, Added_Masses, waterdepth=waterdepth, height_ref=height_ref)

    ex.insert_plot(FIG, excel_filename, "BuildYourStructure", f"MP_plot")

    return


def plot_TP(excel_caller):
    excel_filename = os.path.basename(excel_caller)
    Structure = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TP_DATA", dtype=float)
    Added_Masses = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TP_MASSES")
    Added_Masses = Added_Masses.dropna(how="all")
    Structure = Structure.dropna(how="all")

    META = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TP_META")
    if len(META) != 0:
        value = META.loc[0, "Height Reference"]
        height_ref = value if value else None
    else:
        height_ref = None

    FIG = plot_Structure(Structure, Added_Masses, waterdepth=None, height_ref=height_ref)

    ex.insert_plot(FIG, excel_filename, "BuildYourStructure", f"TP_plot")

    return


def plot_TOWER(excel_caller):
    excel_filename = os.path.basename(excel_caller)
    Structure = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TOWER_DATA", dtype=float)
    Added_Masses = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TOWER_MASSES")
    Added_Masses = Added_Masses.dropna(how="all")
    Structure = Structure.dropna(how="all")

    META = ex.read_excel_table(excel_filename, "BuildYourStructure", f"TOWER_META")
    if len(META) != 0:
        value = META.loc[0, "Height Reference"]
        height_ref = value if value else None
    else:
        height_ref = None

    FIG = plot_Structure(Structure, Added_Masses, waterdepth=None, height_ref=height_ref, waterlevel=None, show_section_numbers=False)

    ex.insert_plot(FIG, excel_filename, "BuildYourStructure", f"TOWER_plot")

    return

# plot_Assambly_Build("C:/Users/aaron.lange/Desktop/Projekte/Geometrie_Converter/GeometrieConverter/GeometrieConverter.xlsm")
#plot_Assambly_Overview("C:/Users/aaron.lange/Desktop/Projekte/Geometrie_Converter/GeometrieConverter/GeometrieConverter.xlsm")
