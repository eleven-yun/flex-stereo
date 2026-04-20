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

## Run self-test

From repo root:

conda run -n freecad-mcp python tools/freecad_mcp_server/server.py --self-test

Expected outputs:

- `bringup_logs/freecad_mcp_selftest/mount_plate_test.stl`
- `bringup_logs/freecad_mcp_selftest/mount_plate_test.FCStd`
- `bringup_logs/freecad_mcp_selftest/box_test.stl`
- `bringup_logs/freecad_mcp_selftest/box_test.FCStd`

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

## Generate the current L-holder draft

This command runs directly in Python without an MCP client and writes STL/FCStd under `bringup_logs/l_holder_v04`:

conda run -n freecad-mcp python -c "from tools.freecad_mcp_server.server import export_l_holder_stl; print(export_l_holder_stl(output_stl='bringup_logs/l_holder_v04/l_holder_v04.stl', output_fcstd='bringup_logs/l_holder_v04/l_holder_v04.FCStd'))"
