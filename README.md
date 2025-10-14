# Insurance OCR & Claims Validation System

A comprehensive insurance document processing and claims validation system powered by Google Gemini 2.5 Pro. The system extracts structured data from insurance documents using OCR and validates claims against complex business rules.

## 🌟 Key Features

### 📄 Document Processing (Extract & Map)
- **PDF to Image Conversion**: Automated conversion of multi-page insurance PDFs to images
- **OCR with Gemini Vision**: Extract text from images using Google Gemini 2.5 Pro's vision capabilities
- **Text Consolidation**: Intelligent consolidation and structuring of extracted data
- **Batch Processing**: Process multiple PDFs automatically with progress tracking

### ✅ Claims Validation (Check Rules)
- **L1 Rules**: Basic document submission checks (e.g., "Is Prescription submitted?")
- **L2 Rules**: Complex business logic validation with AI-powered evaluation
- **Rule Database**: SQLite-based rule management system
- **Interactive Agent**: Chat with AI about claim rules and validation status
- **HTML Reports**: Generate comprehensive validation reports

### 🖥️ Web Interface
- **Streamlit UI**: Modern, intuitive web interface
- **Two Main Modules**:
  - **Extract & Map**: Upload PDFs and extract structured data
  - **Check Rules**: Validate claims against business rules
- **Real-time Processing**: Visual feedback for each processing step
- **Export Options**: Download results as CSV or HTML reports

## 🚀 Recent Updates (October 2025)

- **Migrated to google-genai SDK**: Now using the latest Google Gemini SDK with 2.5 Pro model
- **Centralized Configuration**: Single source of truth for all settings in `config.py`
- **Code Quality Improvements**: 
  - Fixed all security vulnerabilities
  - Removed code duplication
  - All files under 330 lines
  - Proper import structure
- **Enhanced Rule System**: Support for both L1 (document checks) and L2 (complex logic) rules
- **Better Documentation**: Comprehensive docs and architecture diagrams

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Aditya-402/Insurance-OCR.git
    cd Insurance-OCR
    ```

2.  **Create a Conda environment (recommended):**
    ```bash
    conda create -n insurance_ocr_env python=3.10
    conda activate insurance_ocr_env
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    - Create a `.env` file in the project root directory
    - Add your Google API key:
        ```env
        GOOGLE_API_KEY=your_google_api_key_here
        GEMINI_MODEL_NAME=gemini-2.5-pro
        ```
    - Get your API key from: https://aistudio.google.com/app/apikey

5.  **Initialize databases (optional):**
    ```bash
    # Create rules database (if not already present)
    python Rules/create_rules_db.py
    
    # Import rules from CSV
    python Rules/import_excel_to_db.py
    ```

## 🎯 Usage

### Web Application (Recommended)

1.  **Start the Streamlit app:**
    ```bash
    conda activate insurance_ocr_env
    streamlit run main.py
    ```

2.  **Open your browser** to `http://localhost:8501`

3.  **Choose a module:**
    - **Extract & Map**: Upload insurance PDFs to extract structured data
    - **Check Rules**: Validate claims against business rules

### Command Line Tools

#### Batch Process PDFs
```bash
python batch_process_pdfs.py
```
Processes all PDFs in a specified folder with progress tracking.

#### Interactive Rule Checker
```bash
python check_rules/rules_agent.py
```
Chat with AI to validate claim rules interactively.

#### Database Management
```bash
# View database schema
python Rules/inspect_schema.py

# Edit rules database
python Rules/sqlite_gui_editor.py
```

## 📁 Project Structure

```
Insurance_ocr/
├── check_rules/              # Claims validation module
│   ├── check_rule_evaluator.py   # Evaluate L1 document rules
│   ├── l1_rule_manager.py         # L1 rule management
│   ├── l2_rule_evaluator.py       # L2 complex rule evaluation
│   ├── rules_agent.py             # Interactive AI agent
│   ├── sql_tooling.py             # Database query utilities
│   └── config.py                  # Module configuration
├── extract_map/              # OCR & text extraction module
│   ├── extract_from_image.py      # Gemini Vision OCR
│   └── text_consolidation.py      # Text processing & structuring
├── streamlit_ui/             # Web interface
│   ├── app.py                     # Main Streamlit app
│   ├── ui_extract_map.py          # Extract & Map UI
│   ├── ui_check_rules.py          # Check Rules UI
│   └── html_report_generator.py   # Report generation
├── Rules/                    # Database management scripts
│   ├── create_rules_db.py         # Create rules database
│   ├── import_excel_to_db.py      # Import rules from CSV
│   └── sqlite_gui_editor.py       # GUI database editor
├── prompts/                  # AI prompts
│   ├── extract_from_image_gemini.txt
│   ├── text_consolidation_gemini.txt
│   └── rules.txt
├── documentation/            # Project documentation
├── tests/                    # Unit tests
├── config.py                 # Global configuration
├── main.py                   # Application entry point
├── pdf_to_images.py          # PDF conversion utility
├── batch_process_pdfs.py     # Batch processing script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔒 Security Notes

- **Never commit `.env` file**: Contains your API keys - already in `.gitignore`
- **Databases excluded**: All `.db` files are gitignored
- **Use environment variables**: All sensitive data should be in `.env`
- **Token security**: Never share your GitHub personal access tokens publicly

## 🧪 Testing

Run tests with:
```bash
python run_tests.py
```

## 📚 Documentation

Additional documentation available in the `/documentation` folder:
- Architecture diagrams
- Functional requirements
- Flow diagrams

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is for educational/internal use.

## 🙏 Acknowledgments

- Powered by Google Gemini 2.5 Pro
- Built with Streamlit
- OCR processing using google-genai SDK
