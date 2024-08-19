import sexpdata
import uuid
import os
import math
import re

# Directory containing .kicad_sch files to merge
input_directory = '/Users/chengmingzhang/CodingProjects/KiCadUtility/ListOfSch'
output_file = '/Users/chengmingzhang/CodingProjects/KiCadUtility/merged_output.kicad_sch'

# Aspect ratio (width:height)
ASPECT_RATIO = (3, 2)

# Add a border offset
BORDER_OFFSET = 50  # You can adjust this value as needed

def new_uuid():
    return str(uuid.uuid4())

def load_schematic(filepath):
    with open(filepath, 'r') as f:
        return sexpdata.loads(f.read())

def save_schematic(filepath, data):
    with open(filepath, 'w') as f:
        f.write(sexpdata.dumps(data))

def snap_to_grid(value, grid_size):
    return round(value / grid_size) * grid_size

def get_schematic_bounds(schematic):
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for element in schematic:
        if isinstance(element, list) and len(element) > 1:
            if element[0] == sexpdata.Symbol('at'):
                x, y = element[1], element[2]
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
            elif element[0] in [sexpdata.Symbol('wire'), sexpdata.Symbol('polyline')]:
                for point in element:
                    if isinstance(point, list) and point[0] == sexpdata.Symbol('pts'):
                        for pt in point[1:]:
                            if isinstance(pt, list) and pt[0] == sexpdata.Symbol('xy'):
                                x, y = pt[1], pt[2]
                                min_x, max_x = min(min_x, x), max(max_x, x)
                                min_y, max_y = min(min_y, y), max(max_y, y)
            elif element[0] == sexpdata.Symbol('rectangle'):
                start = element[1]
                end = element[2]
                min_x, max_x = min(min_x, start[1], end[1]), max(max_x, start[1], end[1])
                min_y, max_y = min(min_y, start[2], end[2]), max(max_y, start[2], end[2])
    
    return (min_x, min_y, max_x, max_y)

def move_element(element, dx, dy, grid_size):
    if isinstance(element, list):
        if element[0] == sexpdata.Symbol('at'):
            element[1] = snap_to_grid(element[1] + dx, grid_size)
            element[2] = snap_to_grid(element[2] + dy, grid_size)
        elif element[0] in [sexpdata.Symbol('wire'), sexpdata.Symbol('polyline')]:
            for point in element:
                if isinstance(point, list) and point[0] == sexpdata.Symbol('pts'):
                    for pt in point[1:]:
                        if isinstance(pt, list) and pt[0] == sexpdata.Symbol('xy'):
                            pt[1] = snap_to_grid(pt[1] + dx, grid_size)
                            pt[2] = snap_to_grid(pt[2] + dy, grid_size)
        elif element[0] == sexpdata.Symbol('rectangle'):
            element[1][1] = snap_to_grid(element[1][1] + dx, grid_size)
            element[1][2] = snap_to_grid(element[1][2] + dy, grid_size)
            element[2][1] = snap_to_grid(element[2][1] + dx, grid_size)
            element[2][2] = snap_to_grid(element[2][2] + dy, grid_size)
        elif element[0] == sexpdata.Symbol('text'):
            element[2][1] = snap_to_grid(element[2][1] + dx, grid_size)
            element[2][2] = snap_to_grid(element[2][2] + dy, grid_size)
        else:
            for i, item in enumerate(element):
                element[i] = move_element(item, dx, dy, grid_size)
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
    # Calculate the bounds and size of each schematic
    schematic_info = []
    for sch in schematics:
        bounds = get_schematic_bounds(sch)
        width = snap_to_grid(bounds[2] - bounds[0], grid_size)
        height = snap_to_grid(bounds[3] - bounds[1], grid_size)
        schematic_info.append((sch, bounds, width, height))

    # Sort schematics by area (descending order)
    schematic_info.sort(key=lambda x: x[2] * x[3], reverse=True)

    # Function to place schematics
    def place_schematics(sheet_width, sheet_height):
        layout = []
        current_x, current_y = BORDER_OFFSET, BORDER_OFFSET
        row_max_height = 0
        max_x, max_y = 0, 0

        for sch, bounds, width, height in schematic_info:
            if current_x + width + spacing > sheet_width - BORDER_OFFSET:
                # Start a new row
                current_x = BORDER_OFFSET
                current_y += row_max_height + spacing
                row_max_height = 0

            if current_y + height + spacing > sheet_height - BORDER_OFFSET:
                return None  # Sheet is too small

            layout.append((sch, bounds, current_x, current_y))
            current_x += width + spacing
            row_max_height = max(row_max_height, height)
            max_x = max(max_x, current_x)
            max_y = max(max_y, current_y + height)

        return layout, max_x, max_y

    # Calculate initial sheet size based on total area
    total_area = sum(width * height for _, _, width, height in schematic_info)
    sheet_width = math.sqrt(total_area * ASPECT_RATIO[0] / ASPECT_RATIO[1])
    sheet_height = sheet_width * ASPECT_RATIO[1] / ASPECT_RATIO[0]

    # Find the smallest sheet size that fits all schematics
    layout = None
    max_iterations = 100  # Limit the number of iterations
    for _ in range(max_iterations):
        result = place_schematics(sheet_width, sheet_height)
        if result:
            layout, max_x, max_y = result
            new_width = max(max_x + BORDER_OFFSET, sheet_width * 0.95)  # Prevent shrinking too fast
            new_height = max(max_y + BORDER_OFFSET, sheet_height * 0.95)
            
            # Adjust to maintain aspect ratio
            if new_width / new_height > ASPECT_RATIO[0] / ASPECT_RATIO[1]:
                new_height = new_width * ASPECT_RATIO[1] / ASPECT_RATIO[0]
            else:
                new_width = new_height * ASPECT_RATIO[0] / ASPECT_RATIO[1]
            
            if abs(new_width - sheet_width) < grid_size and abs(new_height - sheet_height) < grid_size:
                break  # Stop if the change is smaller than the grid size
            
            sheet_width, sheet_height = new_width, new_height
        else:
            sheet_width *= 1.1
            sheet_height = sheet_width * ASPECT_RATIO[1] / ASPECT_RATIO[0]

    if not layout:
        raise ValueError("Failed to find a suitable layout after maximum iterations")

    # Snap sheet size to grid
    sheet_width = snap_to_grid(sheet_width, grid_size)
    sheet_height = snap_to_grid(sheet_height, grid_size)

    # Create merged schematic
    merged = [sexpdata.Symbol('kicad_sch'),
              [sexpdata.Symbol('version'), 20230121],
              [sexpdata.Symbol('generator'), sexpdata.Symbol('eeschema')],
              [sexpdata.Symbol('uuid'), new_uuid()],
              [sexpdata.Symbol('paper'), "User", sheet_width, sheet_height]]

    lib_symbols = [sexpdata.Symbol('lib_symbols')]
    for schematic, _, _, _ in schematic_info:
        for element in schematic:
            if isinstance(element, list) and element[0] == sexpdata.Symbol('lib_symbols'):
                lib_symbols.extend(element[1:])
    merged.append(lib_symbols)

    ref_counts = {}

    for schematic, bounds, offset_x, offset_y in layout:
        dx = offset_x - bounds[0]
        dy = offset_y - bounds[1]

        for element in schematic:
            if isinstance(element, list) and element[0] not in [sexpdata.Symbol('kicad_sch'), sexpdata.Symbol('version'), sexpdata.Symbol('generator'), sexpdata.Symbol('uuid'), sexpdata.Symbol('paper'), sexpdata.Symbol('lib_symbols')]:
                moved_element = move_element(element, dx, dy, grid_size)
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
spacing = snap_to_grid(5 * grid_size, grid_size)  # 5 grid units spacing

merged_schematic = merge_schematics(schematics, grid_size, spacing)

save_schematic(output_file, merged_schematic)

print(f"\nSaved merged schematic to {output_file}")
print("Merge completed successfully")