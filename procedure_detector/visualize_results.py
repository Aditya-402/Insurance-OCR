"""
Visualize the results from the procedure classifier models
"""
import os
import matplotlib.pyplot as plt
import re
import pandas as pd
import seaborn as sns

RESULTS_PATH = './results'

def extract_accuracy_from_reports():
    """Extract accuracy scores from model reports"""
    models = ['decision_tree', 'random_forest', 'logistic_regression']
    accuracies = {}
    
    for model in models:
        report_path = f'{RESULTS_PATH}/{model}_report.txt'
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                content = f.read()
                match = re.search(r'Accuracy:\s+([\d\.]+)', content)
                if match:
                    accuracies[model] = float(match.group(1))
    
    return accuracies

def plot_model_comparison():
    """Plot comparison of model accuracies"""
    accuracies = extract_accuracy_from_reports()
    
    if not accuracies:
        print("No model results found to visualize")
        return
    
    plt.figure(figsize=(10, 6))
    models = list(accuracies.keys())
    acc_values = list(accuracies.values())
    
    # Create bar plot
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    bars = plt.bar(
        [m.replace('_', ' ').title() for m in models], 
        acc_values, 
        color=colors
    )
    
    # Add labels
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width()/2., 
            height + 0.01,
            f'{height:.4f}',
            ha='center', 
            va='bottom'
        )
    
    plt.ylim(0, 1.1)
    plt.ylabel('Accuracy Score')
    plt.title('Model Accuracy Comparison')
    plt.tight_layout()
    
    # Save plot
    plt.savefig(f'{RESULTS_PATH}/model_comparison.png')
    print(f"Saved model comparison chart to {RESULTS_PATH}/model_comparison.png")

if __name__ == "__main__":
    if not os.path.exists(RESULTS_PATH):
        os.makedirs(RESULTS_PATH)
        print(f"Created directory: {RESULTS_PATH}")
    
    plot_model_comparison()
