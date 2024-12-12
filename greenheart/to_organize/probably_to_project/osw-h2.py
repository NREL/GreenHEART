import sys
import warnings

from greenheart.to_organize.H2_Analysis.hopp_for_h2 import run_h2a as run_h2a  # no h2a function


sys.path.append("")
warnings.filterwarnings("ignore")


"""
Perform a LCOH analysis for an offshore wind + Hydrogen PEM system

1. Offshore wind site locations and cost details (4 sites, $1300/kw capex + BOS cost which will
   come from Orbit Runs)~
2. Cost Scaling Based on Year (Have Weiser et. al report with cost scaling for fixed and floating
   tech, will implement)
3. Cost Scaling Based on Plant Size (Shields et. Al report)
4. Future Model Development Required:
- Floating Electrolyzer Platform (per turbine vs. centralized)
"""
