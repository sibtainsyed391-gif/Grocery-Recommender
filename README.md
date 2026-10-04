# GroceryMate: Smart Grocery Recommendation System

A web-based grocery store that suggests related items as you shop. Add milk and it suggests tea and sugar. Add rice and it suggests cooking oil and salt. The suggestions are not hand-coded: they are **discovered automatically from real shopping baskets** using association rule mining (Apriori and FP-Growth).

Built as a 3rd year Data Mining course project, using only free and open-source tools.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Flask](https://img.shields.io/badge/Flask-backend-black) ![SQLite](https://img.shields.io/badge/SQLite-database-lightgrey) ![License](https://img.shields.io/badge/cost-%240-brightgreen)

## Features

- **Frequently bought together:** rule-based suggestions ranked by confidence, shown with lift
- **Top picks:** a blended score (rule confidence vs item popularity) that performed best in evaluation
- **Live cart:** suggestions update instantly as items are added or removed, with no page reload
- **Shop UI:** product cards, category filters, search, cart drawer, free-delivery progress bar and checkout receipt
- **Analytics dashboard:** top rules by lift, Apriori vs FP-Growth runtime, and hit rate by strategy (Chart.js)
- **About page:** plain-language explanation of the method and metrics
- **Cold-start fallback:** carts with no matching rule fall back to best sellers
- **Local flavour:** extra synthetic baskets of chai, chawal, daal, atta and similar items

## How it works

The system has two halves that never mix:

```
OFFLINE (run once)                                ONLINE (every click)
Raw CSV -> clean baskets -> FP-Growth / Apriori   Browser -> Flask API -> Recommender
        -> association rules -> rules.csv + DB                     (reads rules, instant)
```

Mining is slow, so it runs offline. The web app only reads the finished rules, which makes every recommendation an instant lookup. Mining is never run inside a web request.

### Key concepts

| Metric | Meaning |
|---|---|
| **Support** | How often items appear together across all baskets |
| **Confidence** | Of the baskets with A, the share that also contain B |
| **Lift** | How much more likely B is with A than by chance (above 1 means a real link) |

Example from the data: `{brandy} -> {whole milk}` has confidence 34% and lift 2.17, so brandy buyers are about twice as likely to buy milk as a random shopper.

## Results

**Apriori vs FP-Growth.** Both find identical itemsets. FP-Growth took 0.37 s against Apriori's 2.10 s on the same 1,030 itemsets (about 5.7x faster), and the gap widens as `min_support` drops.

**Evaluation.** Rules are mined on an 80% training split. For each test basket one item is hidden, the rest is the cart, and a hit means the hidden item is in the top-k suggestions. Evaluation uses only the original Groceries data.

| Strategy | Hit@3 | Hit@5 | Hit@10 |
|---|---|---|---|
| Rules by confidence | 11.25% | 19.21% | 34.08% |
| Rules by lift | 10.57% | 18.43% | 34.01% |
| Rules by confidence x lift | 11.11% | 19.04% | 34.08% |
| Popularity baseline | 17.31% | 24.36% | 36.04% |
| **Blended (used for Top picks)** | **17.34%** | **24.59%** | 35.87% |

Pure rules lose to popularity on this sparse dataset, because most rules have low confidence while a few products (whole milk, vegetables, rolls) are bought very often. The blended score keeps a rule only when it beats an item's popularity, which matches the baseline while still surfacing strong relationships.

## Tech stack

| Layer | Tools |
|---|---|
| Language | Python 3.10+ |
| Data and mining | Pandas, NumPy, mlxtend, scikit-learn |
| Backend | Flask |
| Database | SQLite |
| Frontend | HTML, Tailwind CSS (CDN), vanilla JavaScript |
| Charts | Chart.js |
| Experiments | Jupyter Notebook |

## Project structure

```
grocery-recommender/
|-- data/
|   |-- raw/                  # original Kaggle CSV (not in git)
|   `-- processed/            # generated: rules.csv, benchmark.csv, eval_results.csv, all_transactions.csv
|-- notebooks/                # EDA and experiments
|-- mining/
|   |-- preprocess.py         # rows -> baskets
|   |-- add_local.py          # synthetic local-item baskets
|   |-- mine_rules.py         # Apriori + FP-Growth, writes rules and benchmark
|   `-- evaluate.py           # hit rate vs popularity baseline
|-- app/
|   |-- __init__.py           # Flask app factory
|   |-- routes.py             # pages and API endpoints
|   |-- recommender.py        # loads rules, returns suggestions
|   |-- catalog.py            # category, emoji, demo price per product
|   |-- db.py                 # SQLite helpers and database builder
|   |-- templates/            # base, index (shop), analytics, about
|   `-- static/img/           # optional product photos, e.g. whole-milk.jpg
|-- database/schema.sql
|-- requirements.txt
`-- run.py
```

## Getting started

### 1. Clone and install

```bash
git clone https://github.com/sibtainsyed391-gif/Grocery-Recommender.git
cd Grocery-Recommender

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # Mac/Linux

pip install -r requirements.txt
```

### 2. Get the dataset

Download the **Groceries dataset** (by Heeral Dedhia) from Kaggle and place `Groceries_dataset.csv` in `data/raw/`. Also create the output folder if it does not exist:

```bash
mkdir data/processed
```

### 3. Build the model and run the app

Run these from the project root, in order:

```bash
python mining/add_local.py      # adds synthetic local baskets -> all_transactions.csv
python mining/mine_rules.py     # mines rules -> rules.csv, benchmark.csv
python mining/evaluate.py       # evaluation -> eval_results.csv
python app/db.py                # builds database/grocery.db
python run.py                   # starts the server
```

Open <http://127.0.0.1:5000>.

If the data or thresholds change, rerun mining, then `app/db.py`, then restart the server.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Shop page |
| GET | `/analytics` | Analytics dashboard |
| GET | `/about` | Method explanation |
| GET | `/api/products?q=` | List or search products |
| POST | `/api/recommend` | Body `{"cart": ["brandy"], "n": 5}`; returns `related` and `top_picks` |
| POST | `/api/checkout` | Saves the cart as a transaction |
| GET | `/api/rules?sort=&limit=` | Top rules |
| GET | `/api/stats` | Benchmark and evaluation data for the charts |

Example response from `/api/recommend`:

```json
{
  "related":   [{"item": "whole milk", "confidence": 0.342, "lift": 2.17}],
  "top_picks": [{"item": "whole milk", "probability": 0.342, "reason": "rule"}]
}
```

## Adding product photos (optional)

Every product shows an emoji by default. To show a photo instead, save a `.jpg` named after the product's slug in `app/static/img/`, for example `whole-milk.jpg` or `rolls-buns.jpg`. Slugs are listed at `/api/products`. Products without a photo keep their emoji.

## Notes and limitations

- **Synthetic data:** the 300 local-item baskets (chai, chawal, daal...) are generated for demonstration, not real shoppers. Prices, categories and emojis are also demo values.
- **Sparse dataset:** small baskets and many rare products give modest lift values and low confidence. This is a property of the data.
- **Static rules:** checkouts are saved but rules are not re-mined automatically.
- **No personalization:** suggestions depend only on the current cart, not the user.

## Future work

- Re-mine rules from saved checkouts so the system keeps learning
- Collaborative filtering and user profiles
- Time-aware and seasonal rules
- Scale up with a larger dataset such as Instacart

## Acknowledgements

- Groceries dataset by Heeral Dedhia (Kaggle)
- [mlxtend](https://rasbt.github.io/mlxtend/) for Apriori, FP-Growth and association rules
- Free icons and photos from Bootstrap Icons, Unsplash and Pexels

## Author

**[Your Name]** | [Department] | [University] | 3rd year Data Mining course project
