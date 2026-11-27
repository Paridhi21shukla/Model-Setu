import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
METADATA_PATH = BASE_DIR / "model_meta.json"

FEATURE_NAMES = [
    "tenure_months",
    "monthly_charges",
    "support_tickets_3m",
    "contract_months",
]
CLASS_NAMES = ["stay", "churn"]


def generate_customer_data(n_samples=6000):
    """Generate deterministic synthetic customer data for the demo."""
    rng = np.random.RandomState(42)

    tenure = rng.randint(1, 73, n_samples)
    monthly_charges = rng.uniform(20, 120, n_samples)
    support_tickets = rng.randint(0, 11, n_samples)
    contract_months = rng.choice([1, 12, 24], n_samples)

    score = (
        1.0
        - 0.035 * tenure
        + 0.025 * (monthly_charges - 70)
        + 0.28 * support_tickets
        - 0.045 * (contract_months - 1)
    )

    probability = 1 / (1 + np.exp(-score))
    churn = rng.binomial(1, probability)

    X = np.column_stack([
        tenure,
        monthly_charges,
        support_tickets,
        contract_months
    ])

    return X, churn


def train_and_save():
    X, y = generate_customer_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    evaluator = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        class_weight="balanced"
    )

    evaluator.fit(X_train, y_train)
    predictions = evaluator.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_name": "customer-churn-random-forest",
        "model_version": "2.0.0",
        "algorithm": "RandomForestClassifier",
        "dataset": "Synthetic Telco Customer Churn Demo",
        "features": FEATURE_NAMES,
        "classes": CLASS_NAMES,
        "test_accuracy": round(float(accuracy), 4),
        "training_samples": int(len(X))
    }

    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print("Customer Churn Model Training Completed")
    print(json.dumps(metadata, indent=2))
    print("\nEvaluation:")
    print(classification_report(
        y_test,
        predictions,
        target_names=CLASS_NAMES
    ))
    print("Model saved:", MODEL_PATH)


if __name__ == "__main__":
    train_and_save()
