import os
from graphviz import Source

# Define file paths
DOT_FILE_PATH = os.path.join('documentation', 'pdf_to_images_flow.dot')
OUTPUT_PATH = os.path.join('documentation', 'pdf_to_images_flow')

def generate_png_from_dot(dot_path, output_path):
    """Renders a .dot file to a PNG image."""
    try:
        if not os.path.exists(dot_path):
            print(f"Error: Input file not found at '{dot_path}'")
            return

        # Load the DOT source file
        s = Source.from_file(dot_path)

        # Render the graph to PNG, don't open it automatically or delete the source
        rendered_path = s.render(output_path, format='png', view=False, cleanup=False)
        print(f"Successfully generated diagram: {rendered_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the Graphviz software is installed and its 'bin' directory is in your system's PATH.")

if __name__ == "__main__":
    # Generate the structural diagram
    print("Generating structural diagram...")
    generate_png_from_dot(
        os.path.join('documentation', 'pdf_to_images_flow.dot'),
        os.path.join('documentation', 'pdf_to_images_flow')
    )

    # Generate the logic flowchart
    print("\nGenerating logic flowchart...")
    generate_png_from_dot(
        os.path.join('documentation', 'pdf_to_images_logic_flow.dot'),
        os.path.join('documentation', 'pdf_to_images_logic_flow')
    )
