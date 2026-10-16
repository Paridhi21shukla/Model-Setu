import json
from pathlib import Path

import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
METADATA_PATH = BASE_DIR / "model_meta.json"


def train_and_save():
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target,
        test_size=0.2, random_state=42, stratify=iris.target
    )

    evaluator = RandomForestClassifier(n_estimators=100, random_state=42)
    evaluator.fit(X_train, y_train)
    accuracy = accuracy_score(y_test, evaluator.predict(X_test))

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(iris.data, iris.target)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_name": "iris-random-forest",
        "model_version": "1.0.0",
        "algorithm": "RandomForestClassifier",
        "dataset": "Iris",
        "features": iris.feature_names,
        "classes": iris.target_names.tolist(),
        "test_accuracy": round(float(accuracy), 4),
        "training_samples": len(iris.data)
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))
    print("Model saved:", MODEL_PATH)


if __name__ == "__main__":
    train_and_save()
