"""
FLV material library.

Each material is one Principled BSDF named MAT_<Thing>, shared by every object
that uses it. Change MAT_Wall_Cream once (Material Properties tab in Blender)
and every wall updates. Colours are linear RGB, 0-1.
"""
import bpy

MATERIALS = {
    # Room
    "MAT_Wall_Cream":        {"color": (0.56, 0.46, 0.36), "roughness": 0.9},
    "MAT_Wall_Panel":        {"color": (0.13, 0.21, 0.20), "roughness": 0.7},
    "MAT_Floor_Wood":        {"color": (0.26, 0.13, 0.06), "roughness": 0.45, "coat": 0.15},
    "MAT_Floor_Wood_Alt":    {"color": (0.20, 0.10, 0.045), "roughness": 0.5, "coat": 0.15},
    "MAT_Trim_White":        {"color": (0.72, 0.68, 0.62), "roughness": 0.5},
    "MAT_Base_Dark":         {"color": (0.03, 0.026, 0.03), "roughness": 0.85},

    # Furniture
    "MAT_Bed_Wood":          {"color": (0.15, 0.075, 0.04), "roughness": 0.45, "coat": 0.2},
    "MAT_Furniture_Wood":    {"color": (0.36, 0.21, 0.11), "roughness": 0.5},
    "MAT_Furniture_Paint":   {"color": (0.60, 0.56, 0.49), "roughness": 0.55},
    "MAT_Headboard_Fabric":  {"color": (0.26, 0.13, 0.17), "roughness": 0.85, "sheen": 0.6},
    "MAT_Metal":             {"color": (0.05, 0.05, 0.055), "roughness": 0.35, "metallic": 1.0},
    "MAT_Brass":             {"color": (0.78, 0.55, 0.25), "roughness": 0.3, "metallic": 1.0},
    "MAT_Aluminium":         {"color": (0.60, 0.60, 0.62), "roughness": 0.35, "metallic": 1.0},
    "MAT_Mirror":            {"color": (0.90, 0.90, 0.92), "roughness": 0.03, "metallic": 1.0},

    # Bed and fabrics
    "MAT_Mattress":          {"color": (0.78, 0.75, 0.68), "roughness": 0.8},
    "MAT_Bedsheet":          {"color": (0.72, 0.71, 0.70), "roughness": 0.85, "sheen": 0.4},
    "MAT_Blanket":           {"color": (0.10, 0.15, 0.30), "roughness": 0.9, "sheen": 0.7},
    "MAT_Pillow":            {"color": (0.82, 0.79, 0.73), "roughness": 0.85, "sheen": 0.5},
    "MAT_Curtain":           {"color": (0.08, 0.12, 0.16), "roughness": 0.9, "sheen": 0.6},
    "MAT_Rug":               {"color": (0.30, 0.19, 0.16), "roughness": 1.0, "sheen": 0.8},
    "MAT_Rug_Border":        {"color": (0.55, 0.46, 0.37), "roughness": 1.0, "sheen": 0.8},
    "MAT_Fabric_Mustard":    {"color": (0.55, 0.33, 0.07), "roughness": 0.9, "sheen": 0.6},
    "MAT_Fabric_Rose":       {"color": (0.45, 0.20, 0.20), "roughness": 0.9, "sheen": 0.6},
    "MAT_Fabric_Sage":       {"color": (0.20, 0.27, 0.18), "roughness": 0.9, "sheen": 0.6},
    "MAT_Fabric_Navy":       {"color": (0.03, 0.05, 0.12), "roughness": 0.9, "sheen": 0.6},
    "MAT_Fabric_Cream":      {"color": (0.70, 0.64, 0.54), "roughness": 0.9, "sheen": 0.6},
    "MAT_Fabric_Charcoal":   {"color": (0.08, 0.08, 0.09), "roughness": 0.9, "sheen": 0.6},

    # Window and the night outside
    "MAT_Window_Glass":      {"color": (0.60, 0.75, 0.90), "roughness": 0.05, "alpha": 0.12},
    "MAT_Night_Sky":         {"color": (0.010, 0.022, 0.06), "emission": 1.0},
    "MAT_Moon":              {"color": (0.85, 0.90, 1.0), "emission": 6.0},
    "MAT_Tree_Silhouette":   {"color": (0.004, 0.006, 0.012), "roughness": 1.0},

    # Lamps and props
    "MAT_Lamp_Shade":        {"color": (1.0, 0.78, 0.50), "roughness": 0.9, "emission": 2.5},
    "MAT_Bulb":              {"color": (1.0, 0.75, 0.45), "emission": 20.0},
    "MAT_Ceramic":           {"color": (0.70, 0.66, 0.60), "roughness": 0.25},
    "MAT_Glass_Clear":       {"color": (0.85, 0.90, 0.95), "roughness": 0.02, "alpha": 0.2},
    "MAT_Water":             {"color": (0.60, 0.75, 0.85), "roughness": 0.02, "alpha": 0.35},
    "MAT_Plastic_Black":     {"color": (0.02, 0.02, 0.022), "roughness": 0.3},
    "MAT_Screen_Off":        {"color": (0.005, 0.005, 0.007), "roughness": 0.05},
    "MAT_Screen_Glow":       {"color": (0.35, 0.55, 0.90), "emission": 1.5},
    "MAT_Paper":             {"color": (0.80, 0.77, 0.68), "roughness": 0.9},
    "MAT_Book_Red":          {"color": (0.35, 0.05, 0.04), "roughness": 0.6},
    "MAT_Book_Green":        {"color": (0.06, 0.16, 0.10), "roughness": 0.6},
    "MAT_Book_Blue":         {"color": (0.05, 0.08, 0.20), "roughness": 0.6},
    "MAT_Book_Tan":          {"color": (0.45, 0.32, 0.18), "roughness": 0.6},
    "MAT_Clock_Body":        {"color": (0.30, 0.04, 0.03), "roughness": 0.35, "metallic": 0.6},
    "MAT_Clock_Face":        {"color": (0.85, 0.82, 0.70), "roughness": 0.4, "emission": 0.4},
    "MAT_Photo":             {"color": (0.45, 0.38, 0.32), "roughness": 0.3},
    "MAT_Art_Canvas":        {"color": (0.025, 0.04, 0.09), "roughness": 0.8},
    "MAT_Art_Moon":          {"color": (0.85, 0.82, 0.70), "roughness": 0.8},
    "MAT_Art_Hills":         {"color": (0.01, 0.012, 0.02), "roughness": 0.8},
    "MAT_Plant_Leaf":        {"color": (0.04, 0.12, 0.05), "roughness": 0.6},
    "MAT_Terracotta":        {"color": (0.42, 0.17, 0.09), "roughness": 0.8},
    "MAT_Soil":              {"color": (0.04, 0.025, 0.015), "roughness": 1.0},
    "MAT_Leather":           {"color": (0.12, 0.06, 0.035), "roughness": 0.5},
    "MAT_Basket":            {"color": (0.45, 0.33, 0.18), "roughness": 0.9},
    "MAT_Wax":               {"color": (0.85, 0.80, 0.68), "roughness": 0.4, "sheen": 0.3},
    "MAT_Flame":             {"color": (1.0, 0.55, 0.15), "emission": 12.0},
    "MAT_Cork":              {"color": (0.45, 0.30, 0.16), "roughness": 1.0},
    "MAT_Red_String":        {"color": (0.55, 0.02, 0.02), "roughness": 0.6},
    "MAT_Paper_Yellow":      {"color": (0.80, 0.65, 0.15), "roughness": 0.9},
    "MAT_Cardboard":         {"color": (0.42, 0.27, 0.13), "roughness": 0.9},
    "MAT_Tape":              {"color": (0.60, 0.50, 0.30), "roughness": 0.3},
    "MAT_Glass_Green":       {"color": (0.10, 0.30, 0.12), "roughness": 0.05, "alpha": 0.55},
    "MAT_Steel":             {"color": (0.70, 0.70, 0.72), "roughness": 0.2, "metallic": 1.0},
    "MAT_Coffee":            {"color": (0.03, 0.015, 0.008), "roughness": 0.1},

    # Characters
    "MAT_Skin":              {"color": (0.57, 0.31, 0.19), "roughness": 0.55, "sheen": 0.2},
    "MAT_Hair":              {"color": (0.025, 0.015, 0.01), "roughness": 0.5, "sheen": 0.4},
    "MAT_Shirt":             {"color": (0.38, 0.09, 0.06), "roughness": 0.85, "sheen": 0.4},
    "MAT_Pants":             {"color": (0.03, 0.04, 0.07), "roughness": 0.85, "sheen": 0.3},
    "MAT_Shoes":             {"color": (0.025, 0.022, 0.02), "roughness": 0.45},
    "MAT_Pajama":            {"color": (0.28, 0.33, 0.45), "roughness": 0.9, "sheen": 0.5},
    "MAT_Pencil":            {"color": (0.85, 0.55, 0.04), "roughness": 0.4},
    "MAT_Ink":               {"color": (0.02, 0.03, 0.08), "roughness": 0.6},
    "MAT_Ruled_Line":        {"color": (0.30, 0.45, 0.70), "roughness": 0.8},
    "MAT_Eye_White":         {"color": (0.80, 0.78, 0.74), "roughness": 0.2},
    "MAT_Mouth":             {"color": (0.08, 0.015, 0.015), "roughness": 0.6},
    "MAT_Vulture_Eye":       {"color": (0.55, 0.68, 0.80), "roughness": 0.08, "coat": 1.0, "emission": 0.25},
    "MAT_Skin_Pale":         {"color": (0.62, 0.45, 0.36), "roughness": 0.6, "sheen": 0.2},
    "MAT_Hair_White":        {"color": (0.75, 0.74, 0.72), "roughness": 0.6, "sheen": 0.5},
    "MAT_Nightshirt":        {"color": (0.70, 0.67, 0.60), "roughness": 0.9, "sheen": 0.4},
    "MAT_Waistcoat":         {"color": (0.06, 0.05, 0.05), "roughness": 0.7, "sheen": 0.3},
    "MAT_Shirt_White":       {"color": (0.72, 0.70, 0.66), "roughness": 0.85},
    "MAT_Cravat":            {"color": (0.25, 0.03, 0.03), "roughness": 0.5, "sheen": 0.4},
    "MAT_Police_Coat":       {"color": (0.02, 0.03, 0.06), "roughness": 0.8, "sheen": 0.3},
    "MAT_Trousers_Grey":     {"color": (0.08, 0.08, 0.08), "roughness": 0.85},
    "MAT_Plaster_Old":       {"color": (0.38, 0.34, 0.27), "roughness": 0.95},
    "MAT_Wallpaper_Dark":    {"color": (0.12, 0.14, 0.11), "roughness": 0.9},
    "MAT_Floor_Old":         {"color": (0.17, 0.10, 0.055), "roughness": 0.6, "coat": 0.1},
    "MAT_Floor_Old_Alt":     {"color": (0.14, 0.08, 0.045), "roughness": 0.65, "coat": 0.1},
    "MAT_Tin":               {"color": (0.35, 0.33, 0.30), "roughness": 0.35, "metallic": 1.0},
    "MAT_Gold":              {"color": (0.85, 0.62, 0.22), "roughness": 0.25, "metallic": 1.0},
    "MAT_Brick":             {"color": (0.22, 0.09, 0.06), "roughness": 0.9},
    "MAT_Cobble":            {"color": (0.08, 0.08, 0.09), "roughness": 0.7},
    "MAT_Title_Text":        {"color": (0.78, 0.74, 0.66), "roughness": 0.5, "emission": 1.2},
    "MAT_Black":             {"color": (0.0, 0.0, 0.0), "roughness": 1.0},
    "MAT_Soot":              {"color": (0.01, 0.01, 0.01), "roughness": 1.0},
    "MAT_Beetle":            {"color": (0.06, 0.035, 0.02), "roughness": 0.3, "coat": 0.8},
    "MAT_Eye_Film":          {"color": (0.82, 0.86, 0.9), "roughness": 0.25, "alpha": 0.4},
    "MAT_Notebook_Cover":    {"color": (0.08, 0.10, 0.20), "roughness": 0.7},
}


def material(name):
    """Return material `name`, creating it from MATERIALS the first time it is used."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    spec = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:              # Blender < 5 creates materials without nodes
        mat.use_nodes = True
    color = (*spec["color"], 1.0)
    bsdf = mat.node_tree.nodes["Principled BSDF"].inputs
    bsdf["Base Color"].default_value = color
    bsdf["Roughness"].default_value = spec.get("roughness", 0.6)
    bsdf["Metallic"].default_value = spec.get("metallic", 0.0)
    bsdf["Sheen Weight"].default_value = spec.get("sheen", 0.0)
    bsdf["Coat Weight"].default_value = spec.get("coat", 0.0)
    if "emission" in spec:
        bsdf["Emission Color"].default_value = color
        bsdf["Emission Strength"].default_value = spec["emission"]
    if "alpha" in spec:
        bsdf["Alpha"].default_value = spec["alpha"]
    mat.diffuse_color = color              # colour shown in Solid viewport mode
    return mat


def haze_material(name="MAT_Atmosphere_Haze", density=0.03, color=(0.75, 0.82, 1.0)):
    """Thin fog that makes light beams visible (a Principled Volume, not a surface)."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.remove(nodes["Principled BSDF"])
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Density"].default_value = density
    volume.inputs["Color"].default_value = (*color, 1.0)
    mat.node_tree.links.new(volume.outputs["Volume"], nodes["Material Output"].inputs["Volume"])
    return mat
