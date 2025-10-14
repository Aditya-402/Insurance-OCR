import os
import re
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google.genai import types
from config import get_gemini_client


def generate(prompt_text):
    """Generates content using the Gemini API with the new google-genai SDK."""
    try:
        client = get_gemini_client()
    except ValueError as e:
        print(f"Error: {e}")
        return ""
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ],
    )

    try:
        response = client.models.generate_content_stream(
            model="gemini-2.5-pro",
            contents=contents,
            config=generate_content_config,
        )
        return "".join(chunk.text for chunk in response).strip()
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return ""


def parse_and_split_file(input_path, part1_path=None, part2_path=None):
    """
    Parse a text file with entries in the format 'item :: value :: category ||', supporting multi-line values,
    and split them into two output files based on category regex patterns. Page breaks are preserved as their own lines.
    Args:
        input_path (str): Path to the input file.
        part1_path (str, optional): Output file for part 1 categories. If None, derived from input_path.
        part2_path (str, optional): Output file for part 2 categories. If None, derived from input_path.
    Returns:
        tuple: (part1_path, part2_path)
    """
    base = os.path.splitext(os.path.basename(input_path))[0]
    if part1_path is None:
        part1_path = f"{base}_part1.txt"
    if part2_path is None:
        part2_path = f"{base}_part2.txt"

    part1_patterns = [
        r'(?i)claim form page',
        r'(?i)assessment record',
        r'(?i)radiology report',
        r'(?i)discharge summary',
        r'(?i)medical report'
    ]
    part2_patterns = [
        r'(?i)insurance card',
        r'(?i)aadhaar card',
        r'(?i)pan card',
        r'(?i)employee id',
        r'(?i)insurance document'
    ]
    part1_lines = []
    part2_lines = []
    entry_re = re.compile(r'^(.*?)\s*::\s*(.*?)\s*::\s*(.*)$')
    def process_entry(entry):
        entry = entry.split('||', 1)[0].strip()
        m = entry_re.match(entry)
        if not m:
            return
        item, value, category = m.groups()
        category_clean = re.split(r"\|{2,}", category)[0].strip()
        formatted_entry = f"{item} :: {value} :: {category_clean} ||"
        if any(re.search(pat, category_clean) for pat in part1_patterns):
            part1_lines.append(formatted_entry)
        elif any(re.search(pat, category_clean) for pat in part2_patterns):
            part2_lines.append(formatted_entry)


    with open(input_path, 'r', encoding='utf-8') as f:
        buffer = []
        for raw in f:
            line = raw.rstrip('\n')
            # If this is a page break, flush buffer and write page break as its own line
            if line.strip().startswith('--- Page') and line.strip().endswith('---'):
                if buffer:
                    entry = ' '.join(buffer)
                    buffer = []
                    if '||' in entry:
                        process_entry(entry)
                part1_lines.append(line)
                part2_lines.append(line)
                continue
            buffer.append(line)
            if '||' in line:
                entry = ' '.join(buffer)
                buffer = []
                process_entry(entry)

    with open(part1_path, 'w', encoding='utf-8') as f1:
        f1.write('\n'.join(part1_lines) + '\n')
    with open(part2_path, 'w', encoding='utf-8') as f2:
        f2.write('\n'.join(part2_lines) + '\n')
    return part1_path, part2_path


def extract_patient_and_nonpatient_data(data_path, patient_name, prompt_template_path=None):
    """
    Extracts patient and non-patient data using the LLM, given a data file and patient name.
    Args:
        data_path (str): Path to the data file (e.g. 1_part2.txt)
        patient_name (str): The patient name to extract for
        prompt_template_path (str, optional): Path to the prompt template. Defaults to prompts/text_consolidation_gemini.txt
    Returns:
        str: LLM output
    """
    if prompt_template_path is None:
        prompt_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "text_consolidation_gemini.txt")
    # Read data
    with open(data_path, 'r', encoding='utf-8') as f:
        data_content = f.read().strip()
    # Read prompt template
    with open(prompt_template_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    # Fill prompt
    prompt = prompt_template.replace('<PATIENT_NAME>', patient_name).replace('<DATA>', data_content)
    # Call LLM
    return generate(prompt)

def extract_patient_name_from_part1(part1_path):
    """
    Extract patient name from the claim form page 1 (first occurrence of a patient name field).
    Args:
        part1_path (str): Path to the part1 file
    Returns:
        str: patient name (or None if not found)
    """
    # Match 'Patient Name :: ... :: Claim form page' (optionally with a number)
    name_pattern = re.compile(r"patient name\s*::\s*([^:]+?)\s*::\s*claim form page( \d+)?", re.IGNORECASE)
    candidates = []
    with open(part1_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = name_pattern.search(line)
            if m:
                candidates.append(m.group(1).strip())
    # If multiple, prefer the longest (most complete) name
    if candidates:
        return max(candidates, key=len)
    return None

def consolidate_and_output(base_filename):
    part1_path = f"{base_filename}_part1.txt"
    part2_path = f"{base_filename}_part2.txt"
    output_path = f"{base_filename}_output.txt"

    print(f"Attempting to consolidate data for: {base_filename}")
    print(f"Part 1 file: {part1_path}")
    print(f"Part 2 file: {part2_path}")
    print(f"Output file: {output_path}")

    def write_error_and_exit(message, include_part1_data=False):
        print(message)
        with open(output_path, 'w', encoding='utf-8') as f_err:
            f_err.write(f"Error: {message}\n")
            if include_part1_data:
                f_err.write("\n--Claim Form Page 1 Data (Patient Name Not Found)--\n")
                with open(part1_path, 'r', encoding='utf-8') as f1_err:
                    f_err.write(f1_err.read())
        print(f"Output file with error message written to {output_path}")

    try:
        if not os.path.exists(part1_path):
            write_error_and_exit(f"Part 1 file not found: {part1_path}")
            return

        patient_name = extract_patient_name_from_part1(part1_path)
        if not patient_name:
            write_error_and_exit(f"Patient name not found in {part1_path}. Cannot proceed with consolidation.", include_part1_data=True)
            return

        print(f"Patient name extracted: {patient_name}")

        if not os.path.exists(part2_path):
            print(f"Error: Part 2 file not found: {part2_path}")
            with open(output_path, 'w', encoding='utf-8') as fout_err:
                fout_err.write(f"Error: Could not generate full output. Part 2 file missing: {part2_path}\n")
                fout_err.write(f"Patient Name: {patient_name}\n")
                fout_err.write("\n--Claim Form Page 1 Data--\n")
                with open(part1_path, 'r', encoding='utf-8') as f1_err:
                    for line in f1_err:
                        fout_err.write(line)
            print(f"Partial output file with error message written to {output_path}")
            return

        llm_response = extract_patient_and_nonpatient_data(part2_path, patient_name)
        print(f"LLM response received (first 100 chars): {llm_response[:100] if llm_response else 'None or Empty'}")

        with open(part1_path, 'r', encoding='utf-8') as f1, open(output_path, 'w', encoding='utf-8') as fout:
            fout.write(f"--Claim Form Page 1 Data--\n")
            fout.write(f"(Patient Name Used for Extraction: {patient_name})\n\n")
            for line in f1:
                fout.write(line.replace('\xa0', ' '))
            
            fout.write("\n--Extracted Insurance/Identity Data--\n")
            if not llm_response or llm_response.isspace():
                fout.write("LLM did not return any data for this section, or an error occurred during LLM call.\n")
                print("Warning: LLM response was empty or whitespace.")
            else:
                for llm_line in llm_response.strip().split('\n'):
                    if llm_line.startswith("--") and llm_line.endswith("--"):
                        fout.write(llm_line.replace('\xa0', ' ') + "\n")
                    elif "::" in llm_line:
                        fout.write(llm_line.strip().replace('\xa0', ' ') + " ||\n")
                    else:
                        fout.write(llm_line.replace('\xa0', ' ') + "\n")
        print(f"Consolidated output successfully written to {output_path}")

    except Exception as e:
        print(f"An unexpected error occurred in consolidate_and_output: {e}")
        try:
            with open(output_path, 'w', encoding='utf-8') as fout_err:
                fout_err.write(f"Critical Error during consolidation process: {e}\n")
                fout_err.write(f"Base filename: {base_filename}\n")
            print(f"Error details written to {output_path}")
        except Exception as e_write:
            print(f"Failed to write error to output file {output_path}: {e_write}")

# CLI support
if __name__ == '__main__':
    if len(sys.argv) == 2:
        # Step 1: Split the input file
        input_file = sys.argv[1]
        part1_path, part2_path = parse_and_split_file(input_file)
        # Step 2 & 3: Run LLM extraction and consolidate
        base_filename = os.path.splitext(os.path.basename(input_file))[0]
        consolidate_and_output(base_filename)
    elif len(sys.argv) == 3 and sys.argv[1] == '--consolidate':
        base_filename = sys.argv[2]
        consolidate_and_output(base_filename)
    else:
        print(f"Usage: python {os.path.basename(sys.argv[0])} <input_file>\n   or: python {os.path.basename(sys.argv[0])} --consolidate <base_filename>")
        sys.exit(1)
