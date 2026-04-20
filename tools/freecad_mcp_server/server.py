#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

MCP = FastMCP("freecad-mcp")
FREECAD_CMD = os.environ.get("FREECAD_CMD", "freecad.cmd")
RESULT_PREFIX = "MCP_RESULT_JSON:"


def _run_freecad_job(job: str, payload: dict[str, Any], timeout_sec: int = 120) -> dict[str, Any]:
    payload_json = json.dumps(payload)
    runner_path = Path(__file__).with_name("freecad_runner.py").resolve()
    code = f"import runpy; runpy.run_path({json.dumps(str(runner_path))}, run_name='__main__')"
    env = os.environ.copy()
    env["FC_MCP_JOB"] = job
    env["FC_MCP_PAYLOAD"] = payload_json
    env["FC_MCP_RESULT_PREFIX"] = RESULT_PREFIX

    proc = subprocess.run(
        [FREECAD_CMD, "-c", code],
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout_sec,
    )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if proc.returncode != 0:
        raise RuntimeError(
            f"FreeCAD command failed (exit={proc.returncode}).\\n"
            f"stdout:\\n{stdout[-4000:]}\\n"
            f"stderr:\\n{stderr[-4000:]}"
        )

    parsed: dict[str, Any] | None = None
    for line in stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            parsed = json.loads(line[len(RESULT_PREFIX) :])

    if parsed is None:
        raise RuntimeError(
            "FreeCAD output did not include a structured result.\\n"
            f"stdout:\\n{stdout[-4000:]}\\n"
            f"stderr:\\n{stderr[-4000:]}"
        )

    if not parsed.get("ok", False):
        raise RuntimeError(f"FreeCAD job returned error payload: {parsed}")

    return parsed


@MCP.tool()
def health_check() -> dict[str, Any]:
    """Check that FreeCAD headless automation is available."""
    return _run_freecad_job("health", {})


@MCP.tool()
def export_box_stl(
    output_stl: str,
    length_mm: float = 80.0,
    width_mm: float = 40.0,
    height_mm: float = 5.0,
    output_fcstd: str | None = None,
) -> dict[str, Any]:
    """Create a simple rectangular box and export it as STL (optionally FCStd)."""
    payload = {
        "output_stl": str(Path(output_stl).expanduser().resolve()),
        "output_fcstd": str(Path(output_fcstd).expanduser().resolve()) if output_fcstd else None,
        "length_mm": length_mm,
        "width_mm": width_mm,
        "height_mm": height_mm,
    }
    return _run_freecad_job("box_stl", payload)


@MCP.tool()
def export_mount_plate_stl(
    output_stl: str,
    plate_length_mm: float = 140.0,
    plate_width_mm: float = 60.0,
    plate_thickness_mm: float = 4.0,
    hole_diameter_mm: float = 2.2,
    hole_centers_mm: list[list[float]] | None = None,
    output_fcstd: str | None = None,
) -> dict[str, Any]:
    """
    Create a flat mounting plate with through-holes and export STL.

    hole_centers_mm uses [[x1, y1], [x2, y2], ...] in mm relative to plate origin.
    """
    default_holes = [[20.0, 20.0], [20.0, 40.0], [120.0, 20.0], [120.0, 40.0]]
    payload = {
        "output_stl": str(Path(output_stl).expanduser().resolve()),
        "output_fcstd": str(Path(output_fcstd).expanduser().resolve()) if output_fcstd else None,
        "plate_length_mm": plate_length_mm,
        "plate_width_mm": plate_width_mm,
        "plate_thickness_mm": plate_thickness_mm,
        "hole_diameter_mm": hole_diameter_mm,
        "hole_centers_mm": hole_centers_mm or default_holes,
    }
    return _run_freecad_job("plate_stl", payload)


@MCP.tool()
def export_l_holder_stl(
    output_stl: str,
    output_fcstd: str | None = None,
    plane_length_mm: float = 150.0,
    plane_width_mm: float = 75.0,
    horiz_plate_y_min_mm: float = -15.0,
    vert_plane_height_mm: float = 60.0,
    plate_thickness_mm: float = 4.0,
    baseline_mm: float = 64.0,
    camera_center_z_mm: float = 30.0,
    camera_hole_diameter_mm: float = 2.5,
    camera_hole_offsets_mm: list[list[float]] | None = None,
    camera_hole_specs_mm: list[list[float]] | None = None,
    board_center_x_mm: float = 75.0,
    board_center_y_mm: float = 30.0,
    board_hole_diameter_mm: float = 2.5,
    board_hole_offsets_mm: list[list[float]] | None = None,
    gusset_enabled: bool = True,
    gusset_span_x_mm: float = 14.0,
    gusset_leg_y_mm: float = 18.0,
    gusset_leg_z_mm: float = 18.0,
    gusset_edge_margin_x_mm: float = 8.0,
    tripod_boss_enabled: bool = True,
    tripod_boss_x_mm: float = 75.0,
    tripod_boss_y_mm: float = 0.0,
    tripod_boss_outer_radius_mm: float = 10.0,
    tripod_boss_height_mm: float = 8.0,
    tripod_nut_af_mm: float = 11.3,
    tripod_nut_depth_mm: float = 6.1,
    feet_enabled: bool = True,
    feet_radius_mm: float = 7.0,
    feet_height_mm: float = 8.0,
    feet_positions_mm: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Create an L-shaped holder with camera holes on the vertical plane and board holes on the horizontal plane."""
    payload = {
        "output_stl": str(Path(output_stl).expanduser().resolve()),
        "output_fcstd": str(Path(output_fcstd).expanduser().resolve()) if output_fcstd else None,
        "plane_length_mm": plane_length_mm,
        "plane_width_mm": plane_width_mm,
        "horiz_plate_y_min_mm": horiz_plate_y_min_mm,
        "vert_plane_height_mm": vert_plane_height_mm,
        "plate_thickness_mm": plate_thickness_mm,
        "baseline_mm": baseline_mm,
        "camera_center_z_mm": camera_center_z_mm,
        "camera_hole_diameter_mm": camera_hole_diameter_mm,
        "camera_hole_offsets_mm": camera_hole_offsets_mm
        or [[0.0, 9.0], [0.0, -9.0], [-5.0, 8.0], [5.0, -8.0]],
        "camera_hole_specs_mm": camera_hole_specs_mm
        or [[0.0, 9.0, 4.6], [0.0, -9.0, 4.6], [-5.0, 8.0, 2.5], [5.0, -8.0, 2.5]],
        "board_center_x_mm": board_center_x_mm,
        "board_center_y_mm": board_center_y_mm,
        "board_hole_diameter_mm": board_hole_diameter_mm,
        "board_hole_offsets_mm": board_hole_offsets_mm
        or [[-18.25, 8.25], [18.25, 8.25], [-18.25, -8.25], [18.25, -8.25]],
        "gusset_enabled": gusset_enabled,
        "gusset_span_x_mm": gusset_span_x_mm,
        "gusset_leg_y_mm": gusset_leg_y_mm,
        "gusset_leg_z_mm": gusset_leg_z_mm,
        "gusset_edge_margin_x_mm": gusset_edge_margin_x_mm,
        "tripod_boss_enabled": tripod_boss_enabled,
        "tripod_boss_x_mm": tripod_boss_x_mm,
        "tripod_boss_y_mm": tripod_boss_y_mm,
        "tripod_boss_outer_radius_mm": tripod_boss_outer_radius_mm,
        "tripod_boss_height_mm": tripod_boss_height_mm,
        "tripod_nut_af_mm": tripod_nut_af_mm,
        "tripod_nut_depth_mm": tripod_nut_depth_mm,
        "feet_enabled": feet_enabled,
        "feet_radius_mm": feet_radius_mm,
        "feet_height_mm": feet_height_mm,
        "feet_positions_mm": feet_positions_mm or [[20.0, 50.0], [130.0, 50.0]],
    }
    return _run_freecad_job("l_holder_stl", payload)


def _run_self_test() -> int:
    out_dir = Path("bringup_logs/freecad_mcp_selftest").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    health = health_check()
    plate = export_mount_plate_stl(
        output_stl=str(out_dir / "mount_plate_test.stl"),
        output_fcstd=str(out_dir / "mount_plate_test.FCStd"),
    )
    box = export_box_stl(
        output_stl=str(out_dir / "box_test.stl"),
        output_fcstd=str(out_dir / "box_test.FCStd"),
    )
    l_holder = export_l_holder_stl(
        output_stl=str(out_dir / "l_holder_test.stl"),
        output_fcstd=str(out_dir / "l_holder_test.FCStd"),
    )

    print(json.dumps({"health": health, "plate": plate, "box": box, "l_holder": l_holder}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="FreeCAD MCP server with STL export helpers")
    parser.add_argument("--self-test", action="store_true", help="Run quick local self-test and exit")
    args = parser.parse_args()

    if args.self_test:
        return _run_self_test()

    MCP.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
