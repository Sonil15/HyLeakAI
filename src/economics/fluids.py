"""Fluid properties at reservoir conditions — the evidence for the transfer claim.

WHY THIS MODULE EXISTS

The commercial case names natural gas storage as the next market after hydrogen.
That claim rests on a physical assertion — that CH4 is a near neighbour of H2 and
CO2 is not — and an assertion of that kind, made to a jury of reservoir
engineers, has to be computed rather than asserted. `Data_sources_research.md`
records what happens otherwise: an earlier AI-generated version of that document
inverted the H2/CH4 viscosity and density relationship, and the correction only
came from computing it.

So every number in the transfer table comes out of CoolProp at the dataset's own
pressure, and the module refuses to emit any of them unless it first reproduces a
number we already committed to elsewhere.

THE CALIBRATION CHECK

`config.LeakageConfig.h2_viscosity_pa_s` is 9.5e-06 Pa.s, tagged [ASSUMED]. If
CoolProp is being driven correctly, it must return that value for hydrogen at the
dataset pressure and some plausible reservoir temperature. It does, at ~40 C, to
within 0.2%. That agreement is asserted at import of the report, not eyeballed:
if a CoolProp upgrade or a unit slip breaks it, this module fails loudly and the
transfer table never gets written.

WHAT THE NUMBERS SAY

At 197.2 bar and 40 C, relative to H2:

    CH4    1.9x the viscosity,   10x the density
    CO2    8.3x the viscosity,   61x the density

CH4 sits an interpolation away from H2. CO2 does not — at these conditions it is
a liquid-like supercritical phase. The consequence that matters for a *leakage*
model is buoyancy, because caprock leakage is buoyancy-driven: the density
contrast against brine that pushes gas up against the seal is ~1036 kg/m3 for H2
and ~213 kg/m3 for CO2, a factor of ~5 weaker. A model whose features encode
H2 buoyancy would mis-rank CO2 containment risk systematically, not randomly.

That is the whole argument for naming CH4 as the next market and leaving CO2 out
of the pitch, reduced to numbers a reservoir engineer can check.

Usage:
    python -m src.economics.fluids
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict

from src import config as C
from src.config import LEAKAGE

# [DATASET] Initial reservoir pressure, Mao et al. simulations.
P_RESERVOIR_PA = C.P_INIT_BAR * 1e5

# [DERIVED] The temperature at which CoolProp reproduces the H2 viscosity already
# committed to in LeakageConfig. The source paper never states a reservoir
# temperature, so this is back-solved from our own constant rather than assumed
# independently — see `calibration_temperature()`.
T_CALIBRATED_K = 313.15

# [ASSUMED] The temperature implied instead by the ~1878 m depth inferred in
# docs/PRESENTATION_CONTEXT.md under a normal 30 C/km geothermal gradient and a
# 20 C surface temperature. Carried as a sensitivity case, not as the primary.
T_DEPTH_IMPLIED_K = 349.0

# [ASSUMED] Formation brine density. Only used for the buoyancy contrast, which
# is reported as a ratio between fluids, so the exact value cancels to first
# order. Mid-range for a saline formation brine.
BRINE_DENSITY_KG_M3 = 1050.0

# Tolerance on the calibration check. 1% is far tighter than the [ASSUMED] tag on
# the config constant deserves; it is set this tight because the check is
# detecting driver/unit errors, not physical disagreement.
CALIBRATION_RTOL = 0.01

FLUIDS = {"H2": "Hydrogen", "CH4": "Methane", "CO2": "CO2"}


@dataclass(frozen=True)
class FluidState:
    """Properties of one fluid at one (P, T)."""

    fluid: str
    temperature_k: float
    pressure_pa: float
    viscosity_pa_s: float
    density_kg_m3: float

    @property
    def buoyancy_contrast_kg_m3(self) -> float:
        """Density deficit against brine — the driving force for caprock leakage.

        Negative would mean the phase is denser than brine and would not migrate
        upward at all; none of H2/CH4/CO2 reach that at these conditions, but the
        sign is what makes this the right quantity to compare rather than density.
        """
        return BRINE_DENSITY_KG_M3 - self.density_kg_m3


def properties(fluid_key: str, temperature_k: float,
               pressure_pa: float = P_RESERVOIR_PA) -> FluidState:
    """Viscosity and density from CoolProp. SI throughout — no unit conversions."""
    from CoolProp.CoolProp import PropsSI

    name = FLUIDS[fluid_key]
    return FluidState(
        fluid=fluid_key,
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        viscosity_pa_s=float(PropsSI("V", "P", pressure_pa, "T", temperature_k, name)),
        density_kg_m3=float(PropsSI("D", "P", pressure_pa, "T", temperature_k, name)),
    )


def calibration_temperature(tolerance: float = CALIBRATION_RTOL) -> float:
    """Assert CoolProp reproduces the H2 viscosity we already committed to.

    Raises rather than returning a flag: if this disagrees, every downstream
    number in the transfer table is suspect and none of them should be written.
    """
    state = properties("H2", T_CALIBRATED_K)
    expected = LEAKAGE.h2_viscosity_pa_s
    rel = abs(state.viscosity_pa_s - expected) / expected
    assert rel < tolerance, (
        f"CoolProp gives H2 viscosity {state.viscosity_pa_s:.4e} Pa.s at "
        f"{T_CALIBRATED_K:.2f} K / {P_RESERVOIR_PA / 1e5:.1f} bar, but "
        f"LeakageConfig.h2_viscosity_pa_s is {expected:.4e} Pa.s "
        f"({rel:.2%} apart, tolerance {tolerance:.0%}). Either the CoolProp "
        f"backend changed or a unit is wrong — do not trust the transfer table."
    )
    return T_CALIBRATED_K


def transfer_table(temperature_k: float) -> dict:
    """Every fluid at one temperature, expressed as ratios against H2.

    Ratios rather than absolutes because the transfer claim is comparative: the
    question is not what CH4's viscosity is, it is how far CH4 sits from the
    fluid the U-Net was actually trained on.
    """
    states = {k: properties(k, temperature_k) for k in FLUIDS}
    h2 = states["H2"]
    return {
        "temperature_k": temperature_k,
        "temperature_c": temperature_k - 273.15,
        "pressure_bar": P_RESERVOIR_PA / 1e5,
        "fluids": {
            key: {
                **asdict(s),
                "buoyancy_contrast_kg_m3": s.buoyancy_contrast_kg_m3,
                "viscosity_ratio_to_h2": s.viscosity_pa_s / h2.viscosity_pa_s,
                "density_ratio_to_h2": s.density_kg_m3 / h2.density_kg_m3,
                "buoyancy_ratio_to_h2": (
                    s.buoyancy_contrast_kg_m3 / h2.buoyancy_contrast_kg_m3),
            }
            for key, s in states.items()
        },
    }


def label_viscosity_sensitivity() -> dict:
    """How much the T3 flux label moves if the reservoir is hotter than calibrated.

    T3 is Darcy flux, so it scales as 1/mu exactly. This turns the temperature
    ambiguity into a number rather than leaving it as a caveat: the answer is a
    few percent, against the three orders of magnitude of fault-permeability
    uncertainty the screen already sweeps. It is not the term that matters.
    """
    cold = properties("H2", T_CALIBRATED_K).viscosity_pa_s
    hot = properties("H2", T_DEPTH_IMPLIED_K).viscosity_pa_s
    return {
        "calibrated_t_k": T_CALIBRATED_K,
        "depth_implied_t_k": T_DEPTH_IMPLIED_K,
        "viscosity_calibrated_pa_s": cold,
        "viscosity_depth_implied_pa_s": hot,
        "viscosity_increase": hot / cold - 1.0,
        # T3 flux goes as 1/mu, so a higher viscosity lowers the flux.
        "t3_flux_change": cold / hot - 1.0,
        "fault_permeability_decades_swept": 3.0,
        "note": (
            "The T3 label scales exactly as 1/mu, so the unresolved reservoir "
            "temperature moves every flux by this fraction uniformly. It shifts "
            "the labels together rather than reordering them, and it is small "
            "against the three decades of fault permeability the screen sweeps."
        ),
    }


def build_report() -> dict:
    temperature = calibration_temperature()
    return {
        "calibration": {
            "temperature_k": temperature,
            "config_h2_viscosity_pa_s": LEAKAGE.h2_viscosity_pa_s,
            "coolprop_h2_viscosity_pa_s": properties("H2", temperature).viscosity_pa_s,
            "tolerance": CALIBRATION_RTOL,
            "note": (
                "LeakageConfig's [ASSUMED] H2 viscosity corresponds to hydrogen at "
                "the dataset pressure and ~40 C. The source paper states no "
                "reservoir temperature, so this is back-solved from our own "
                "constant rather than assumed a second time."
            ),
        },
        "primary": transfer_table(temperature),
        "sensitivity_depth_implied": transfer_table(T_DEPTH_IMPLIED_K),
        "label_viscosity_sensitivity": label_viscosity_sensitivity(),
        "brine_density_kg_m3": BRINE_DENSITY_KG_M3,
    }


def main() -> int:
    report = build_report()
    t = report["primary"]

    print(f"Reservoir conditions: {t['pressure_bar']:.1f} bar, "
          f"{t['temperature_k']:.2f} K ({t['temperature_c']:.1f} C)")
    print(f"OK CoolProp reproduces LeakageConfig H2 viscosity "
          f"({report['calibration']['coolprop_h2_viscosity_pa_s']:.4e} vs "
          f"{report['calibration']['config_h2_viscosity_pa_s']:.4e} Pa.s)\n")

    print(f"{'fluid':>5} {'mu (Pa.s)':>11} {'rho':>8} {'d-rho':>8} "
          f"| {'mu/H2':>7} {'rho/H2':>7} {'buoy/H2':>8}")
    print("-" * 66)
    for key, f in t["fluids"].items():
        print(f"{key:>5} {f['viscosity_pa_s']:>11.3e} {f['density_kg_m3']:>8.1f} "
              f"{f['buoyancy_contrast_kg_m3']:>8.1f} "
              f"| {f['viscosity_ratio_to_h2']:>7.2f} "
              f"{f['density_ratio_to_h2']:>7.1f} "
              f"{f['buoyancy_ratio_to_h2']:>8.2f}")

    s = report["label_viscosity_sensitivity"]
    print(f"\nIf the reservoir is at {s['depth_implied_t_k']:.0f} K instead "
          f"(the depth-implied case), H2 viscosity rises {s['viscosity_increase']:+.1%} "
          f"and every T3 flux moves {s['t3_flux_change']:+.1%} — uniformly, against "
          f"{s['fault_permeability_decades_swept']:.0f} decades of fault permeability.")

    print("\nREAD THIS OFF THE TABLE")
    print("  CH4 is an interpolation from H2; CO2 is not. What matters for a")
    print("  leakage model is the buoyancy column: caprock leakage is driven by")
    print("  the density contrast against brine, and CO2's is ~5x weaker than")
    print("  H2's. An H2-trained model would mis-rank CO2 risk systematically.")

    C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = C.OUTPUT_DIR / "fluid_properties.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
