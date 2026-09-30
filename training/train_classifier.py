import argparse
import csv
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
with open(args.input, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
texts = [row["text"] for row in rows]
labels = [row["label"] for row in rows]
if len(rows) < 8 or len(set(labels)) < 2 or min(labels.count(label) for label in set(labels)) < 2:
    raise SystemExit("Need >=8 texts, >=2 classes, and >=2 examples per class")
train_x, test_x, train_y, test_y = train_test_split(texts, labels, test_size=0.25, random_state=42, stratify=labels)
model = Pipeline([("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))),
                  ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])
model.fit(train_x, train_y)
print(classification_report(test_y, model.predict(test_x), zero_division=0))
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, args.output)
print(f"Saved: {args.output}")
