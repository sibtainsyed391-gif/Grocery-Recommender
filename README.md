# GroceryMate: Grocery Recommendation System

Market basket analysis (Apriori and FP-Growth) with a Flask web app that suggests
related grocery items, e.g. chawal -> cooking oil, doodh -> chai patti.

## Setup
1. Download "Groceries dataset" (Heeral Dedhia) from Kaggle and place
   `Groceries_dataset.csv` in `data/raw/`.
2. `python -m venv venv` then activate it
3. `pip install -r requirements.txt`

## Run (from the project root)
    python mining/add_local.py     # adds synthetic local baskets
    python mining/mine_rules.py    # mines rules, writes benchmark.csv
    python mining/evaluate.py      # evaluation (original Groceries data)
    python app/db.py               # builds the SQLite database
    python run.py                  # open http://127.0.0.1:5000

## Notes
- Local baskets (chai, chawal, daal...) are synthetic, for demonstration only.
- Evaluation uses the original Groceries data only.