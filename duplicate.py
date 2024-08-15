import skip
import uuid

# Load the schematic
input_file = '/Users/chengmingzhang/Desktop/ExploreKidCAD/ExploreKidCAD2.kicad_sch'
output_file = '/Users/chengmingzhang/Desktop/ExploreKidCAD/output.kicad_sch'

print(f"Loading schematic from {input_file}")
sch = skip.Schematic(input_file)
print(f"Schematic loaded successfully")

# Function to generate a new UUID
def new_uuid():
    return str(uuid.uuid4())

# Function to clone and move an element
def clone_and_move(element, dy=50):
    new_element = element.clone()
    if hasattr(new_element, 'at'):
        new_element.translation(0, dy)
    return new_element

# Function to process a collection of elements
def process_collection(collection, collection_name):
    print(f"Processing {collection_name}...")
    new_elements = []
    for i, element in enumerate(list(collection)):  # Create a list to avoid modifying during iteration
        new_element = clone_and_move(element)
        new_element.uuid = new_uuid()
        new_elements.append(new_element)
        if i % 10 == 0:  # Print progress every 10 elements
            print(f"  Processed {i+1} {collection_name}")
    print(f"Finished processing {len(new_elements)} {collection_name}")
    return new_elements

# Process each type of element
new_symbols = process_collection(sch.symbol, "symbols")
new_wires = process_collection(sch.wire, "wires")
new_labels = process_collection(sch.label, "labels")
new_global_labels = process_collection(sch.global_label, "global labels")
new_junctions = process_collection(sch.junction, "junctions")

# Add all new elements to the schematic
print("Adding new elements to the schematic...")
for new_symbol in new_symbols:
    sch.symbol.append(new_symbol)
for new_wire in new_wires:
    sch.wire.append(new_wire)
for new_label in new_labels:
    sch.label.append(new_label)
for new_global_label in new_global_labels:
    sch.global_label.append(new_global_label)
for new_junction in new_junctions:
    sch.junction.append(new_junction)
print("Finished adding new elements")

# Save the modified schematic
print(f"Saving modified schematic to {output_file}")
sch.write(output_file)
print(f"Schematic duplicated and saved successfully")

print("Script execution completed")