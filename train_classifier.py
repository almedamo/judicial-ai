import argparse
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import csv

p = argparse.ArgumentParser()
p.add_argument('--input', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()
rows = list(csv.DictReader(open(a.input, encoding='utf-8')))
X, y = [r['text'] for r in rows], [r['label'] for r in rows]
if len(set(y)) < 2 or len(rows) < 8:
    raise SystemExit('Need at least 8 examples and at least 2 document classes')
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
model = Pipeline([('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=1)), ('clf', LogisticRegression(max_iter=2000, class_weight='balanced'))])
model.fit(Xtr, ytr)
print(classification_report(yte, model.predict(Xte), zero_division=0))
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, a.output)
print(f'Saved: {a.output}')
