"""
Summary of procedure classification model performance
"""
import os
import re

def print_model_summary():
    """Print a summary of model performance"""
    models = ['decision_tree', 'random_forest', 'logistic_regression']
    results = {}
    
    print("\n===== PROCEDURE CLASSIFIER RESULTS =====\n")
    
    for model in models:
        report_path = f'./results/{model}_report.txt'
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                content = f.read()
                match = re.search(r'Accuracy:\s+([\d\.]+)', content)
                if match:
                    accuracy = float(match.group(1))
                    results[model] = accuracy
                    print(f"{model.replace('_', ' ').title()}: Accuracy = {accuracy:.4f}")
    
    print("\nBest model: " + max(results, key=results.get).replace('_', ' ').title())
    print("\nComplete reports and confusion matrices available in the 'results' folder.")

if __name__ == "__main__":
    print_model_summary()
