import json
import math
import os

import FreeCAD
import Mesh
import Part

RESULT_PREFIX = os.environ.get("FC_MCP_RESULT_PREFIX", "MCP_RESULT_JSON:")
JOB = os.environ.get("FC_MCP_JOB", "")
PAYLOAD = json.loads(os.environ.get("FC_MCP_PAYLOAD", "{}"))


def ensure_parent(path_str: str) -> None:
    parent = os.path.dirname(path_str)
    if parent:
        os.makedirs(parent, exist_ok=True)


def result(obj: dict) -> None:
    print(RESULT_PREFIX + json.dumps(obj, ensure_ascii=True))


def make_yz_gusset(x0: float, span_x: float, leg_y: float, leg_z: float) -> Part.Shape:
    profile = Part.makePolygon(
        [
            FreeCAD.Vector(x0, 0.0, 0.0),
            FreeCAD.Vector(x0, leg_y, 0.0),
            FreeCAD.Vector(x0, 0.0, leg_z),
            FreeCAD.Vector(x0, 0.0, 0.0),
        ]
    )
    return Part.Face(profile).extrude(FreeCAD.Vector(span_x, 0.0, 0.0))


if JOB == "health":
    result({"ok": True, "freecad_version": FreeCAD.Version()})

elif JOB == "box_stl":
    out_stl = PAYLOAD["output_stl"]
    out_fcstd = PAYLOAD.get("output_fcstd")
    l = float(PAYLOAD["length_mm"])
    w = float(PAYLOAD["width_mm"])
    h = float(PAYLOAD["height_mm"])

    ensure_parent(out_stl)
    if out_fcstd:
        ensure_parent(out_fcstd)

    doc = FreeCAD.newDocument("BoxDoc")
    obj = doc.addObject("Part::Feature", "Box")
    obj.Shape = Part.makeBox(l, w, h)
    doc.recompute()
    Mesh.export([obj], out_stl)
    if out_fcstd:
        doc.saveAs(out_fcstd)

    result({"ok": True, "output_stl": out_stl, "output_fcstd": out_fcstd})

elif JOB == "plate_stl":
    out_stl = PAYLOAD["output_stl"]
    out_fcstd = PAYLOAD.get("output_fcstd")

    plate_l = float(PAYLOAD["plate_length_mm"])
    plate_w = float(PAYLOAD["plate_width_mm"])
    plate_t = float(PAYLOAD["plate_thickness_mm"])
    hole_d = float(PAYLOAD["hole_diameter_mm"])
    holes = PAYLOAD["hole_centers_mm"]

    ensure_parent(out_stl)
    if out_fcstd:
        ensure_parent(out_fcstd)

    base = Part.makeBox(plate_l, plate_w, plate_t)
    radius = hole_d / 2.0

    for c in holes:
        x = float(c[0])
        y = float(c[1])
        cyl = Part.makeCylinder(radius, plate_t * 2.0, FreeCAD.Vector(x, y, -plate_t * 0.5))
        base = base.cut(cyl)

    doc = FreeCAD.newDocument("PlateDoc")
    obj = doc.addObject("Part::Feature", "MountPlate")
    obj.Shape = base
    doc.recompute()

    Mesh.export([obj], out_stl)
    if out_fcstd:
        doc.saveAs(out_fcstd)

    result(
        {
            "ok": True,
            "output_stl": out_stl,
            "output_fcstd": out_fcstd,
            "plate_length_mm": plate_l,
            "plate_width_mm": plate_w,
            "plate_thickness_mm": plate_t,
            "hole_diameter_mm": hole_d,
            "hole_count": len(holes),
        }
    )

elif JOB == "l_holder_stl":
    out_stl = PAYLOAD["output_stl"]
    out_fcstd = PAYLOAD.get("output_fcstd")

    plane_l = float(PAYLOAD["plane_length_mm"])
    plane_w = float(PAYLOAD["plane_width_mm"])      # horizontal plate Y depth
    plane_y0 = float(PAYLOAD.get("horiz_plate_y_min_mm", -15.0))
    vert_h  = float(PAYLOAD.get("vert_plane_height_mm", 60.0))  # vertical plate Z height
    plate_t = float(PAYLOAD["plate_thickness_mm"])

    baseline = float(PAYLOAD["baseline_mm"])
    camera_center_z = float(PAYLOAD["camera_center_z_mm"])
    camera_hole_d = float(PAYLOAD["camera_hole_diameter_mm"])
    camera_hole_offsets = PAYLOAD["camera_hole_offsets_mm"]
    camera_hole_specs = PAYLOAD.get("camera_hole_specs_mm")

    board_center_x = float(PAYLOAD["board_center_x_mm"])
    board_center_y = float(PAYLOAD["board_center_y_mm"])
    board_hole_d = float(PAYLOAD["board_hole_diameter_mm"])
    board_hole_offsets = PAYLOAD["board_hole_offsets_mm"]

    gusset_enabled = bool(PAYLOAD.get("gusset_enabled", True))
    gusset_span_x = float(PAYLOAD.get("gusset_span_x_mm", 14.0))
    gusset_leg_y = float(PAYLOAD.get("gusset_leg_y_mm", 18.0))
    gusset_leg_z = float(PAYLOAD.get("gusset_leg_z_mm", 18.0))
    gusset_edge_margin_x = float(PAYLOAD.get("gusset_edge_margin_x_mm", 8.0))

    ensure_parent(out_stl)
    if out_fcstd:
        ensure_parent(out_fcstd)

    # Horizontal plate span: y ∈ [plane_y0, plane_y0 + plane_w]
    horiz = Part.makeBox(plane_l, plane_w, plate_t, FreeCAD.Vector(0.0, plane_y0, 0.0))
    # Vertical plane at y ∈ [0, plate_t]
    vert  = Part.makeBox(plane_l, plate_t, vert_h,  FreeCAD.Vector(0.0, 0.0, 0.0))
    base = horiz.fuse(vert)

    if gusset_enabled:
        left_x0 = gusset_edge_margin_x
        right_x0 = plane_l - gusset_edge_margin_x - gusset_span_x
        if right_x0 < left_x0:
            raise ValueError("Gusset placement exceeds available plate length")
        base = base.fuse(make_yz_gusset(left_x0, gusset_span_x, gusset_leg_y, gusset_leg_z))
        base = base.fuse(make_yz_gusset(right_x0, gusset_span_x, gusset_leg_y, gusset_leg_z))

    x_mid = plane_l / 2.0
    left_x = x_mid - baseline / 2.0
    right_x = x_mid + baseline / 2.0

    if camera_hole_specs:
        hole_specs = camera_hole_specs
    else:
        hole_specs = [[float(off[0]), float(off[1]), camera_hole_d] for off in camera_hole_offsets]

    for cam_x in [left_x, right_x]:
        for spec in hole_specs:
            dx = float(spec[0])
            dz = float(spec[1])
            hole_d = float(spec[2])
            cyl = Part.makeCylinder(
                hole_d / 2.0,
                plate_t * 3.0,
                FreeCAD.Vector(cam_x + dx, -plate_t, camera_center_z + dz),
                FreeCAD.Vector(0.0, 1.0, 0.0),
            )
            base = base.cut(cyl)

    board_hole_radius = board_hole_d / 2.0
    for off in board_hole_offsets:
        dx = float(off[0])
        dy = float(off[1])
        cyl = Part.makeCylinder(
            board_hole_radius,
            plate_t * 3.0,
            FreeCAD.Vector(board_center_x + dx, board_center_y + dy, -plate_t),
            FreeCAD.Vector(0.0, 0.0, 1.0),
        )
        base = base.cut(cyl)

    # Tripod boss: blind hex-nut pocket on underside, no through-hole into plate.
    tripod_enabled = bool(PAYLOAD.get("tripod_boss_enabled", True))
    tripod_x = float(PAYLOAD.get("tripod_boss_x_mm", plane_l / 2.0))
    tripod_y = float(PAYLOAD.get("tripod_boss_y_mm", 0.0))  # at front junction, y=0
    tripod_boss_r = float(PAYLOAD.get("tripod_boss_outer_radius_mm", 10.0))
    tripod_boss_h = float(PAYLOAD.get("tripod_boss_height_mm", 8.0))
    tripod_nut_af = float(PAYLOAD.get("tripod_nut_af_mm", 11.3))  # 1/4-20 hex nut AF + 0.2 mm tolerance
    tripod_nut_depth = float(PAYLOAD.get("tripod_nut_depth_mm", 6.1))  # nut thickness 5.6 mm + 0.5 mm

    feet_enabled = bool(PAYLOAD.get("feet_enabled", True))
    feet_radius = float(PAYLOAD.get("feet_radius_mm", 7.0))
    feet_height = float(PAYLOAD.get("feet_height_mm", tripod_boss_h))  # match boss height for flat contact
    feet_positions = PAYLOAD.get("feet_positions_mm", [[20.0, 55.0], [130.0, 55.0]])

    if tripod_enabled:
        boss = Part.makeCylinder(
            tripod_boss_r,
            tripod_boss_h,
            FreeCAD.Vector(tripod_x, tripod_y, -tripod_boss_h),
        )
        base = base.fuse(boss)

        # Hexagonal blind pocket opens at the bottom face of the boss.
        nut_circumscribed_r = (tripod_nut_af / 2.0) / math.cos(math.pi / 6.0)
        hex_pts = [
            FreeCAD.Vector(
                tripod_x + nut_circumscribed_r * math.cos(math.pi / 6.0 + i * math.pi / 3.0),
                tripod_y + nut_circumscribed_r * math.sin(math.pi / 6.0 + i * math.pi / 3.0),
                -tripod_boss_h,
            )
            for i in range(6)
        ]
        hex_pts.append(hex_pts[0])
        hex_face = Part.Face(Part.makePolygon(hex_pts))
        hex_pocket = hex_face.extrude(FreeCAD.Vector(0.0, 0.0, tripod_nut_depth))
        base = base.cut(hex_pocket)

    if feet_enabled:
        for fp in feet_positions:
            foot = Part.makeCylinder(
                feet_radius,
                feet_height,
                FreeCAD.Vector(float(fp[0]), float(fp[1]), -feet_height),
            )
            base = base.fuse(foot)

    doc = FreeCAD.newDocument("LHolderDoc")
    obj = doc.addObject("Part::Feature", "LHolder")
    obj.Shape = base
    doc.recompute()

    Mesh.export([obj], out_stl)
    if out_fcstd:
        doc.saveAs(out_fcstd)

    result(
        {
            "ok": True,
            "output_stl": out_stl,
            "output_fcstd": out_fcstd,
            "plane_length_mm": plane_l,
            "plane_width_mm": plane_w,
            "horiz_plate_y_min_mm": plane_y0,
            "vert_plane_height_mm": vert_h,
            "plate_thickness_mm": plate_t,
            "baseline_mm": baseline,
            "camera_centers_x_mm": [left_x, right_x],
            "camera_center_z_mm": camera_center_z,
            "camera_hole_count_total": len(hole_specs) * 2,
            "board_hole_count": len(board_hole_offsets),
            "gusset_enabled": gusset_enabled,
            "tripod_boss_enabled": tripod_enabled,
            "feet_enabled": feet_enabled,
        }
    )

else:
    result({"ok": False, "error": f"Unknown job: {JOB}"})
