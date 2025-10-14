# Procedure Classification Models

This folder contains machine learning models to classify surgical procedures based on alternative procedure names.

## Models

- Decision Tree
- Random Forest  
- Logistic Regression

## Usage

1. Run the classifier:
   ```bash
   conda activate insurance_ocr_env
   python procedure_classifier.py
   ```

2. View model comparison:
   ```bash
   python visualize_results.py
   ```

## Outputs

- `models/`: Saved model files
- `results/`: Confusion matrices and classification reports
