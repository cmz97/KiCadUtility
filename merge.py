import sexpdata
import uuid
import os
import math
import re

# Directory containing .kicad_sch files to merge
input_directory = '/Users/chengmingzhang/CodingProjects/KiCadUtility/ListOfSch'
# Path to the empty template .kicad_sch file
template_file = '/Users/chengmingzhang/CodingProjects/KiCadUtility/EmptyTemplate.kicad_sch'
output_file = '/Users/chengmingzhang/CodingProjects/KiCadUtility/merged_output.kicad_sch'

def new_uuid():
    return str(uuid.uuid4())

def load_schematic(filepath):
    with open(filepath, 'r') as f:
        return sexpdata.loads(f.read())

def save_schematic(filepath, data):
    with open(filepath, 'w') as f:
        f.write(sexpdata.dumps(data))

def get_schematic_bounds(schematic):
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for element in schematic:
        if isinstance(element, list) and len(element) > 1:
            if element[0] == sexpdata.Symbol('at'):
                x, y = element[1], element[2]
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
            elif element[0] in [sexpdata.Symbol('wire'), sexpdata.Symbol('polyline')]:
                for point in element:
                    if isinstance(point, list) and point[0] == sexpdata.Symbol('pts'):
                        for pt in point[1:]:
                            if isinstance(pt, list) and pt[0] == sexpdata.Symbol('xy'):
                                x, y = pt[1], pt[2]
                                min_x = min(min_x, x)
                                min_y = min(min_y, y)
                                max_x = max(max_x, x)
                                max_y = max(max_y, y)
    
    if min_x == float('inf'):
        return (0, 0, 100, 100)
    return (min_x, min_y, max_x, max_y)

def move_element(element, dx, dy):
    if isinstance(element, list):
        if element[0] == sexpdata.Symbol('at'):
            element[1] += dx
            element[2] += dy
        elif element[0] == sexpdata.Symbol('wire'):
            for point in element:
                if isinstance(point, list) and point[0] == sexpdata.Symbol('pts'):
                    for pt in point[1:]:
                        if isinstance(pt, list) and pt[0] == sexpdata.Symbol('xy'):
                            pt[1] += dx
                            pt[2] += dy
        else:
            for i, item in enumerate(element):
                element[i] = move_element(item, dx, dy)
    return element

def update_references(element, ref_counts):
    if isinstance(element, list):
        if element[0] == sexpdata.Symbol('property') and element[1] == 'Reference':
            ref = element[2]
            match = re.match(r'([A-Z]+)(\d+)', ref)
            if match:
                prefix, number = match.groups()
                new_number = ref_counts.get(prefix, 0) + 1
                ref_counts[prefix] = new_number
                new_ref = f"{prefix}{new_number}"
                element[2] = new_ref
        else:
            for i, item in enumerate(element):
                element[i] = update_references(item, ref_counts)
    return element

def update_uuids(element):
    if isinstance(element, list):
        if element[0] == sexpdata.Symbol('uuid'):
            element[1] = new_uuid()
        else:
            for i, item in enumerate(element):
                element[i] = update_uuids(item)
    return element

def merge_schematics(schematics, grid_size, spacing):
    merged = [sexpdata.Symbol('kicad_sch'),
              [sexpdata.Symbol('version'), 20230121],
              [sexpdata.Symbol('generator'), sexpdata.Symbol('eeschema')],
              [sexpdata.Symbol('uuid'), new_uuid()],
              [sexpdata.Symbol('paper'), 'A4']]
    
    lib_symbols = [sexpdata.Symbol('lib_symbols')]
    for schematic in schematics:
        for element in schematic:
            if isinstance(element, list) and element[0] == sexpdata.Symbol('lib_symbols'):
                lib_symbols.extend(element[1:])
    merged.append(lib_symbols)
    
    ref_counts = {}
    
    max_width = 0
    max_height = 0
    for schematic in schematics:
        bounds = get_schematic_bounds(schematic)
        width = (bounds[2] - bounds[0])
        height = (bounds[3] - bounds[1])
        max_width = max(max_width, width)
        max_height = max(max_height, height)

    columns = math.ceil(math.sqrt(len(schematics)))
    rows = math.ceil(len(schematics) / columns)
    
    for i, schematic in enumerate(schematics):
        bounds = get_schematic_bounds(schematic)
        width = (bounds[2] - bounds[0])
        height = (bounds[3] - bounds[1])
        
        row = i // columns
        col = i % columns
        
        offset_x = col * (max_width + spacing) - bounds[0]
        offset_y = row * (max_height + spacing) - bounds[1]
        
        for element in schematic:
            if isinstance(element, list) and element[0] not in [sexpdata.Symbol('kicad_sch'), sexpdata.Symbol('version'), sexpdata.Symbol('generator'), sexpdata.Symbol('uuid'), sexpdata.Symbol('paper'), sexpdata.Symbol('lib_symbols')]:
                moved_element = move_element(element, offset_x, offset_y)
                updated_element = update_references(moved_element, ref_counts)
                updated_element = update_uuids(updated_element)
                merged.append(updated_element)
    
    merged.append([sexpdata.Symbol('sheet_instances'),
                   [sexpdata.Symbol('path'), '/', [sexpdata.Symbol('page'), '1']]])
    
    return merged

# Main script
sch_files = [f for f in os.listdir(input_directory) if f.endswith('.kicad_sch')]
print(f"Found {len(sch_files)} .kicad_sch files to merge")

schematics = [load_schematic(os.path.join(input_directory, f)) for f in sch_files]

grid_size = 1.27
spacing = 15 * grid_size  # 15 grid units

merged_schematic = merge_schematics(schematics, grid_size, spacing)

save_schematic(output_file, merged_schematic)

print(f"\nSaved merged schematic to {output_file}")
print("Merge completed successfully")