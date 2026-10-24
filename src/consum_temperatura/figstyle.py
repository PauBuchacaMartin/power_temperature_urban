"""One style for every figure of article 1 (matplotlib, static PNG for print).

Colours come from a validated data-viz palette: an ordinal blue ramp for years
(light = early, dark = late) and fixed categorical slots for sectors or conditions.
Text never takes the series colour; grids and axes are recessive.
"""
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]           # blau, taronja, aigua, groc (ordre fix)
YEARS_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]   # rampa ordinal de blaus


def year_colors(years):
    """Ordinal colour for each year (light = first, dark = last)."""
    years = list(years)
    n = len(years)
    idx = [round(i * (len(YEARS_RAMP) - 1) / max(n - 1, 1)) for i in range(n)]
    return {a: YEARS_RAMP[i] for a, i in zip(years, idx)}


def apply_style():
    """Matplotlib defaults for the article figures."""
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": INK_2, "axes.labelcolor": INK, "xtick.color": INK_2, "ytick.color": INK_2,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2.0,
        "lines.markersize": 5, "errorbar.capsize": 2.5, "legend.frameon": False,
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "savefig.dpi": 300,
        "axes.prop_cycle": mpl.cycler(color=CAT),
    })
