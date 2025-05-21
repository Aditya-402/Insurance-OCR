import sys
import os
import re
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv

# Load environment variables and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def generate(prompt_text):
    """Generates content using the Gemini API with google.generativeai library."""
    model_instance = genai.GenerativeModel("gemini-1.5-pro")

    generation_config = genai.types.GenerationConfig(
        response_mime_type="text/plain"
    )
    safety_settings = [
        {
            "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
    ]

    response_accumulator = ""
    try:
        response_stream = model_instance.generate_content(
            prompt_text,
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=True
        )
        for chunk in response_stream:
            response_accumulator += chunk.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        # Optionally, re-raise the exception or return a specific error message
        # For now, returning what has been accumulated, or an empty string if error was immediate.
        # Consider more sophisticated error handling if needed.
        return response_accumulator.strip() # Or raise e

    return response_accumulator.strip()


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
        for l in part1_lines:
            f1.write(l + '\n')
    with open(part2_path, 'w', encoding='utf-8') as f2:
        for l in part2_lines:
            f2.write(l + '\n')
    return part1_path, part2_path


def extract_patient_and_nonpatient_data(data_path, patient_name, prompt_template_path=None):
    """
    Extracts patient and non-patient data using the LLM, given a data file and patient name.
    Args:
        data_path (str): Path to the data file (e.g. 1_part2.txt)
        patient_name (str): The patient name to extract for
        prompt_template_path (str, optional): Path to the prompt template. Defaults to prompts/prompts.txt
    Returns:
        str: LLM output
    """
    if prompt_template_path is None:
        prompt_template_path = os.path.join(os.path.dirname(__file__), "prompts", "prompts.txt")
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
    """
    Orchestrate the workflow: extract patient name from part1, run LLM extraction on part2, and consolidate outputs.
    Args:
        base_filename (str): Base filename (without _part1.txt/_part2.txt)
    Output:
        Writes consolidated output to <base_filename>_output.txt
    """
    part1_path = f"{base_filename}_part1.txt"
    part2_path = f"{base_filename}_part2.txt"
    output_path = f"{base_filename}_output.txt"
    # 1. Extract patient name from part1
    patient_name = extract_patient_name_from_part1(part1_path)
    if not patient_name:
        raise ValueError(f"Patient name not found in {part1_path}")
    # 2. Extract patient/non-patient data from part2 using LLM
    llm_response = extract_patient_and_nonpatient_data(part2_path, patient_name)
    # 3. Consolidate data: combine part1.txt content and LLM response
    with open(part1_path, 'r', encoding='utf-8') as f1, open(output_path, 'w', encoding='utf-8') as fout:
        fout.write(f"--Claim Form Page 1 Data--\n")
        for line in f1:
            fout.write(line)
        fout.write("\n--Extracted Insurance/Identity Data--\n")
        for llm_line in llm_response.strip().split('\n'):
            if llm_line.startswith("--") and llm_line.endswith("--"):
                fout.write(llm_line + "\n")  # Write headers as is
            elif "::" in llm_line: # It's a data line
                fout.write(llm_line.strip() + " ||\n") # Add the delimiter
            else: # Empty lines or other non-data lines from LLM
                fout.write(llm_line + "\n")
    print(f"Consolidated output written to {output_path}")

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
