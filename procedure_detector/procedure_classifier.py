"""
Procedure Classification Model
This script trains Decision Tree, Random Forest, and Logistic Regression models
to classify surgical procedures based on alternative names.
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.pipeline import Pipeline
import pickle

# Set paths
DATA_PATH = '../procedure_mappings.csv'
MODELS_PATH = './models'
RESULTS_PATH = './results'

# Create necessary directories
os.makedirs(MODELS_PATH, exist_ok=True)
os.makedirs(RESULTS_PATH, exist_ok=True)

def prepare_data():
    """Load and prepare data for model training"""
    print("Loading data...")
    df = pd.read_csv(DATA_PATH)
    
    # Create dataset for classification
    X_data = []
    y_data = []
    
    # For each main procedure name, create multiple training examples from alt names
    for _, row in df.iterrows():
        proc_main = row['Proc_Name_main']
        alt_names = row['Proc_name_Alt1']
        
        # Split alternative names by comma and clean
        alt_names_list = [name.strip() for name in alt_names.split(',')]
        
        # Add each alternative name as a training example
        for alt in alt_names_list:
            X_data.append(alt)
            y_data.append(proc_main)
            
        # Also add the main name as a training example
        X_data.append(proc_main)
        y_data.append(proc_main)
    
    # Create dataframe
    training_df = pd.DataFrame({
        'text': X_data,
        'procedure': y_data
    })
    
    print(f"Prepared dataset with {len(training_df)} examples")
    return training_df

def train_evaluate_models(df):
    """Train and evaluate models"""
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        df['text'], df['procedure'], test_size=0.25, random_state=42
    )
    
    # Define models
    models = {
        'decision_tree': Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('classifier', DecisionTreeClassifier(random_state=42))
        ]),
        'random_forest': Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
        ]),
        'logistic_regression': Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('classifier', LogisticRegression(max_iter=1000, random_state=42))
        ])
    }
    
    results = {}
    
    # Train and evaluate each model
    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        
        # Predictions
        y_pred = model.predict(X_test)
        
        # Evaluation
        accuracy = accuracy_score(y_test, y_pred)
        conf_matrix = confusion_matrix(y_test, y_pred)
        class_report = classification_report(y_test, y_pred)
        
        # Save confusion matrix as text
        with open(f'{RESULTS_PATH}/{name}_confusion_matrix.txt', 'w') as f:
            f.write(f"Confusion Matrix - {name.replace('_', ' ').title()}\n")
            f.write("Format: [actual][predicted] = count\n\n")
            
            # Convert labels to list for easier indexing
            labels = list(np.unique(y_test))
            
            # Write header row with predicted labels
            f.write("Predicted ->\nActual |\t")
            f.write("\t".join(labels))
            f.write("\n")
            
            # Write each row of the confusion matrix
            for i, row_label in enumerate(labels):
                f.write(f"{row_label}\t")
                f.write("\t".join([str(conf_matrix[i, j]) for j in range(len(labels))]))
                f.write("\n")
        
        # Save classification report
        with open(f'{RESULTS_PATH}/{name}_report.txt', 'w') as f:
            f.write(f"Model: {name}\n")
            f.write(f"Accuracy: {accuracy:.4f}\n\n")
            f.write(class_report)
        
        # Save model
        with open(f'{MODELS_PATH}/{name}_model.pkl', 'wb') as f:
            pickle.dump(model, f)
        
        results[name] = {
            'accuracy': accuracy
        }
    
    return results

def main():
    """Main function to run the training and evaluation"""
    print("Starting procedure classification model training...")
    
    # Prepare data
    df = prepare_data()
    
    # Train and evaluate models
    results = train_evaluate_models(df)
    
    # Print summary
    print("\nTraining complete. Summary of results:")
    for name, result in results.items():
        print(f"{name.replace('_', ' ').title()}: Accuracy = {result['accuracy']:.4f}")
    
    print(f"\nModels saved to {MODELS_PATH}")
    print(f"Results and confusion matrices saved to {RESULTS_PATH}")

if __name__ == "__main__":
    main()
