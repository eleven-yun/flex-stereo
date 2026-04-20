# FreeCAD MCP Server (STL-first)

This server exposes a minimal FreeCAD automation surface over MCP using
headless `freecad.cmd` subprocess calls.

## Why this design

Your local Python environment is not the same interpreter as the FreeCAD snap runtime.
Using subprocess calls avoids Python ABI/version coupling and remains stable.

## Tools provided

- `health_check`: verify FreeCAD headless API works
- `export_box_stl`: generate a box and export STL/optional FCStd
- `export_mount_plate_stl`: generate a flat plate with through-holes and export STL/optional FCStd
- `export_l_holder_stl`: generate an L-shaped holder with camera holes on the vertical plane and sync-board holes on the horizontal plane

## Environment

Recommended environment:

- Conda env: `freecad-mcp`
- Python: `3.12`
- Packages: `mcp`, `pydantic`

Create the environment from the repo root:

`conda env create -f environment.yml`

If it already exists:

`conda env update -f environment.yml --prune`

This environment provides the Python-side MCP server only. FreeCAD itself is expected
to be available as `freecad.cmd` on the host system, or provided explicitly via
`FREECAD_CMD`.

## Run self-test

From repo root:

conda run -n freecad-mcp python tools/freecad_mcp_server/server.py --self-test

Expected outputs:

- `bringup_logs/freecad_mcp_selftest/mount_plate_test.stl`
- `bringup_logs/freecad_mcp_selftest/mount_plate_test.FCStd`
- `bringup_logs/freecad_mcp_selftest/box_test.stl`
- `bringup_logs/freecad_mcp_selftest/box_test.FCStd`
- `bringup_logs/freecad_mcp_selftest/l_holder_test.stl`
- `bringup_logs/freecad_mcp_selftest/l_holder_test.FCStd`

## Run MCP server

conda run -n freecad-mcp python tools/freecad_mcp_server/server.py

Optional: override FreeCAD command if needed.

FREECAD_CMD=/snap/bin/freecad.cmd conda run -n freecad-mcp python tools/freecad_mcp_server/server.py

## Example plate call

Use your MCP client to invoke `export_mount_plate_stl` with parameters like:

- output_stl: `/home/yixiao/workspace/code/flex-stereo/bringup_logs/plate_v1.stl`
- output_fcstd: `/home/yixiao/workspace/code/flex-stereo/bringup_logs/plate_v1.FCStd`
- plate_length_mm: `140`
- plate_width_mm: `60`
- plate_thickness_mm: `4`
- hole_diameter_mm: `2.2`
- hole_centers_mm: `[[20,20],[20,40],[120,20],[120,40]]`

## Current L-holder defaults

The current printed holder target uses these default parameters in
`export_l_holder_stl`:

- plane length: `150 mm`
- horizontal plate width: `75 mm`
- horizontal plate span: `y in [-15, 60] mm`
- vertical plate height: `60 mm`
- camera baseline: `64 mm`
- camera center height: `30 mm`
- sync-board center: `(75, 30) mm`
- tripod boss enabled: `true`
- rear feet enabled: `true`

## Generate the current L-holder draft

This command runs directly in Python without an MCP client and writes STL/FCStd under `bringup_logs/l_holder_current`:

conda run -n freecad-mcp python -c "from tools.freecad_mcp_server.server import export_l_holder_stl; print(export_l_holder_stl(output_stl='bringup_logs/l_holder_current/l_holder.stl', output_fcstd='bringup_logs/l_holder_current/l_holder.FCStd'))"
