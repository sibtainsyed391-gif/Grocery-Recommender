# GroceryMate: How Everything Works

A complete walkthrough of the grocery recommendation system, from raw CSV to the live web store

**Contents**

1. [The big picture](#big)
2. [Files and folders](#files)
3. [Step 1: The data](#data)
4. [Step 2: Preprocessing](#pre)
5. [Step 3: Core concepts](#concepts)
6. [Step 4: Apriori and FP-Growth](#algos)
7. [Step 5: Mining the rules](#mine)
8. [Step 6: Evaluation](#eval)
9. [Step 7: The recommender](#rec)
10. [Step 8: The database](#db)
11. [Step 9: Flask backend](#flask)
12. [Step 10: The frontend](#ui)
13. [One click, end to end](#life)
14. [Running and rebuilding](#run)
15. [Viva questions and answers](#viva)

## 1. The big picture

GroceryMate answers one question: **"This shopper has these items in the cart. What else are they likely to buy?"** It does not use hand-written suggestions. It learns them from about 15,000 real shopping baskets using **association rule mining**.

The system has two halves that never mix:

Raw CSV*→*Clean into baskets*→*Mine rules (FP-Growth / Apriori)*→*rules.csv + database

Browser*→*Flask API*→*Recommender (reads rules)*→*Suggestions back to browser

**Key design rule:** mining is slow, so it runs **offline, once**. The web app only reads the finished rules, so every click returns instantly. We never run Apriori or FP-Growth while a user is shopping.

## 2. Files and folders

| Path | What it does |
| --- | --- |
| `data/raw/Groceries_dataset.csv` | Original Kaggle download. Never edited. |
| `data/processed/all_transactions.csv` | Groceries plus 300 synthetic local baskets (made by `add_local.py`). |
| `data/processed/rules.csv` | The mined association rules. The heart of the project. |
| `data/processed/benchmark.csv` | Apriori vs FP-Growth runtimes (feeds the analytics chart). |
| `data/processed/eval_results.csv` | Hit-rate results for each strategy (feeds the evaluation chart). |
| `mining/preprocess.py` | Turns rows into baskets. Used by the other mining scripts. |
| `mining/add_local.py` | Generates synthetic baskets of local items (chai, chawal...). |
| `mining/mine_rules.py` | Runs both algorithms, creates rules, writes rules.csv and benchmark.csv. |
| `mining/evaluate.py` | Tests how well each recommendation strategy predicts purchases. |
| `app/recommender.py` | The brain: cart in, two suggestion lists out. |
| `app/catalog.py` | Gives each product a category, emoji, demo price and image name. |
| `app/db.py`, `database/schema.sql` | SQLite connection helper, table definitions, and the script that fills the database. |
| `app/__init__.py`, `app/routes.py` | Flask app setup and all pages and API endpoints. |
| `app/templates/*.html` | Pages: shop (index), analytics, about, and the shared base layout. |
| `app/static/img/` | Optional product photos named by slug, such as `whole-milk.jpg`. |
| `run.py` | Starts the Flask server. |

## 3. Step 1: The data

The Groceries dataset has three columns: `Member_number`, `Date`, `itemDescription`. Each row is **one item bought by one member on one date**. It has about 38,000 rows and 167 products.

### Synthetic local baskets

The Groceries data has no chai, chawal or daal, so `add_local.py` creates 300 extra baskets from six templates (chai, pulao, roti-daal, breakfast, biryani, salan), 50 baskets each. Each template has *core* items (always present) and *optional* items (each added with 50% chance). To avoid unrealistically perfect rules, two kinds of noise are added: 10% of baskets forget one core item, and 15% get a random extra item. Member numbers start at 90001 so they never clash with real members.

**Be honest about this in the viva:** these baskets are synthetic. They make the demo relevant to Pakistan, but they are not real shopper data. The evaluation uses **only the original Groceries data**, so the reported accuracy is not inflated by made-up baskets.

## 4. Step 2: Preprocessing (`preprocess.py`)

```
df["itemDescription"] = df["itemDescription"].str.strip().str.lower()
df = df.dropna().drop_duplicates()
baskets = df.groupby(["Member_number","Date"])["itemDescription"] \
            .apply(lambda x: sorted(set(x))).tolist()
baskets = [b for b in baskets if len(b) > 1]
```

1. **Standardise names:** "Whole Milk " and "whole milk" must be one product.
2. **Remove missing values and duplicates.**
3. **Define a basket:** all items one member bought on one date. `groupby` collects them; `set` removes repeats inside a basket.
4. **Drop single-item baskets:** a basket with one item contains no "bought together" information.

Result: **14,758 baskets** from the original data, about 15,058 after the local baskets. Each basket is a list such as `['sausage', 'semi-finished bread', 'whole milk', 'yogurt']`.

### One-hot encoding

The algorithms need a table, not lists. `TransactionEncoder` builds a True/False matrix: one row per basket, one column per product. A cell is True if that product is in that basket. This matrix is what Apriori and FP-Growth read.

## 5. Step 3: Core concepts

An **association rule** looks like `{A} → {B}`: "baskets containing A often contain B". A is the *antecedent* and B the *consequent*. Three numbers describe how good a rule is.

| Metric | Formula | Meaning |
| --- | --- | --- |
| Support | baskets with A and B / all baskets | How common the pair is. Low support means too rare to trust. |
| Confidence | support(A and B) / support(A) | Of the baskets with A, the share that also have B. |
| Lift | confidence / support(B) | How much more likely B is with A than by chance. 1 = no link, above 1 = positive link. |

### Worked example from your data: {brandy} → {whole milk}

- Support = 0.088%: about 13 of 14,758 baskets have both.
- Confidence = 34.2%: about a third of brandy baskets also contain whole milk.
- Whole milk alone appears in about 15.7% of all baskets, so **lift = 0.342 / 0.157 = 2.17**. Brandy buyers are 2.17 times more likely to buy milk than a random shopper.

**Why lift matters:** whole milk is in so many baskets that it would "follow" almost anything. Confidence alone would suggest milk for everything. Lift tells you when the link is real and not just popularity.

## 6. Step 4: Apriori and FP-Growth

Both do the same job: find all **frequent itemsets**, meaning item groups whose support is at least `min_support`. They give identical results but work differently.

### Apriori (level by level)

1. Count single items; keep those above min support.
2. Combine survivors into pairs; count; keep the frequent pairs.
3. Combine into triples, and so on.

The Apriori principle: **if an itemset is rare, every bigger set containing it is rare too**, so those candidates are skipped. Still, it generates many candidates and rescans the data at every level. It slows down badly as min support drops.

### FP-Growth (tree based)

It scans the data twice, compresses all baskets into a compact **FP-tree** (shared prefixes are stored once), then mines patterns straight from the tree. **No candidate generation.** That is why it stays fast at low support.

| min_support | Itemsets | Apriori (s) | FP-Growth (s) |
| --- | --- | --- | --- |
| 0.01 | 69 | 0.153 | 0.177 |
| 0.005 | 130 | 0.257 | 0.238 |
| 0.003 | 216 | 0.454 | 0.149 |
| 0.002 | 330 | 0.571 | 0.203 |
| 0.001 | 750 | 0.861 | 0.160 |

At high support they are about equal. The gap opens as support drops. In the main run, FP-Growth took 0.37 s against Apriori's 2.10 s on the same 1,030 itemsets (about 5.7x faster).

## 7. Step 5: Mining the rules (`mine_rules.py`)

```
freq = fpgrowth(df, min_support=0.001, use_colnames=True, max_len=3)
rules = association_rules(freq, metric="confidence", min_threshold=0.03)
rules = rules[rules["lift"] >= 1.0].sort_values("lift", ascending=False)
```

| Parameter | Our choice | Why |
| --- | --- | --- |
| min_support | 0.001 | Baskets are small and products many, so pairs are rare. A higher value gave only 25 rules. |
| min_confidence | 0.03 | Low on purpose; the recommender ranks by confidence later. |
| min lift | 1.0 | Keep only positive relationships. |
| max_len | 3 | Itemsets of up to three products; keeps rules simple and mining fast. |

The script saves `rules.csv` with columns `antecedents, consequents, support, confidence, lift`. Multi-item sides are stored as comma-separated text, such as `whole milk, yogurt`. Tuning moved the count from **25 rules to 271**. It also times both algorithms and writes `benchmark.csv`.

## 8. Step 6: Evaluation (`evaluate.py`)

Having rules does not prove they work. We test them on baskets the rules have never seen.

1. Split the baskets 80/20: 11,806 train, 2,952 test (fixed random seed 42).
2. Mine rules on the **training baskets only** (198 rules).
3. For each test basket, **hide one random item**. The rest is the "cart".
4. Ask each strategy for its top 3, 5 and 10 suggestions. If the hidden item is among them, that is a **hit**.
5. Hit rate = hits / test baskets.

| Strategy | Hit@3 | Hit@5 | Hit@10 |
| --- | --- | --- | --- |
| Rules by confidence | 11.25% | 19.21% | 34.08% |
| Rules by lift | 10.57% | 18.43% | 34.01% |
| Rules by confidence x lift | 11.11% | 19.04% | 34.08% |
| Popularity baseline | 17.31% | 24.36% | 36.04% |
| **Blended (our Top Picks)** | **17.34%** | **24.59%** | 35.87% |

### Why popularity beats pure rules, and how we fixed it

Most rules in this dataset have low confidence (5 to 10%). Whole milk, vegetables and rolls each appear in 10 to 15% of all baskets, so simply guessing them often wins. The fix is the **blended score**: for each item compare (a) its overall popularity with (b) the best rule confidence given the cart, and take the higher. A rule only overrides a popular item when it is genuinely stronger, such as brandy → whole milk at 34%. The blended method ties the baseline on this data, which is the honest result.

Hit rate rewards guessing popular items, but the project goal is *related* items (milk → sugar and tea). That is why the app shows **two lists**: "Frequently bought together" (rules only) and "Top picks" (blended).

## 9. Step 7: The recommender (`app/recommender.py`)

### What it loads at start-up

- **Rules** from `rules.csv`, each turned into `(set of antecedent items, set of consequent items, confidence, lift)`.
- **Base popularity** `base_p`: for every product, the share of baskets that contain it. Built from `all_transactions.csv` using the same basket logic as preprocessing.

### What `recommend(cart, n)` does

1. **Related list:** go through every rule. If the rule's antecedent is a subset of the cart (`ante <= cart`), then each consequent not already in the cart becomes a candidate. If an item appears in several rules, keep its highest confidence. Sort by confidence and return the top n.
2. **Top picks:** start with every product not in the cart, scored by `base_p`. For items in the related list, replace the score with the rule confidence if it is higher. Sort and return the top n, marked "rule" or "popular".

**Example, cart = \[brandy\]:** the only matching rule is brandy → whole milk. "Frequently bought together" shows whole milk at 34% (lift 2.17). In "Top picks", whole milk scores 0.342, beating its base 0.157, so it ranks first and is tagged "rule"; the other slots fill with popular items (other vegetables, rolls/buns...).

**Example, cart = \[whole milk, yogurt\]:** the rule `{whole milk, yogurt} → sausage` only fires because *both* items are in the cart. That is why multi-item rules need the subset test.

If a cart matches no rule, the related list is empty and Top picks falls back to best sellers. This is the **cold-start fallback**.

## 10. Step 8: The database (SQLite)

| Table | Columns | Used for |
| --- | --- | --- |
| products | product_id, name, popularity | Shop listing and search |
| rules | rule_id, antecedents, consequents, support, confidence, lift | Analytics rule chart |
| transactions | transaction_id, created_at | One row per checkout |
| transaction_items | id, transaction_id, product_id | The items in each checkout |

`python app/db.py` runs `schema.sql`, then fills `products` from the recommender's popularity table and `rules` from `rules.csv`. The database file is `database/grocery.db`.

**Know this for the viva:** the recommender reads `rules.csv` directly, not the database. The database serves the product list, the analytics rules and saved checkouts. Saved checkouts are stored so that rules *could* be re-mined later; the app does not re-mine automatically yet.

## 11. Step 9: The Flask backend

`run.py` calls `create_app()` in `app/__init__.py`. That builds one Recommender when the server starts (loading rules once into memory) and registers the routes from `routes.py`.

| Route | What it does |
| --- | --- |
| `GET /` | Shop page. |
| `GET /analytics`, `GET /about` | Analytics dashboard and method explanation pages. |
| `GET /api/products?q=` | Products from SQLite, filtered by search text, most popular first. Each is enriched by `catalog.describe()` with category, emoji, price, unit and image slug. |
| `POST /api/recommend` | Body `{"cart":["brandy"],"n":5}`. Returns `{related:[...], top_picks:[...]}` from the Recommender. |
| `POST /api/checkout` | Saves the cart as a transaction and its items. Returns the order number. |
| `GET /api/rules?sort=&limit=` | Top rules from SQLite. The sort column is checked against an allowed list to prevent SQL injection. |
| `GET /api/stats` | Reads `benchmark.csv` and `eval_results.csv` for the charts. |

### catalog.py

Your dataset has no prices or categories. `describe(name)` matches the product name against keyword lists (milk, bread, chicken...) to pick a category, chooses an emoji, and creates a **deterministic demo price** by hashing the name, so a product always gets the same price. The slug (`"rolls/buns"` becomes `rolls-buns`) links a product to its photo file. All of this is demo data, not real pricing.

## 12. Step 10: The frontend

The shop page is plain HTML with Tailwind CSS (loaded from a CDN) and vanilla JavaScript. There is no framework. The whole page is driven by a few pieces of state:

```
let products = [], byName = {}, cart = {}, cat = 'All', q = '', rec = {related:[], top_picks:[]};
```

- `cart` is an object such as `{"whole milk": 2, "brandy": 1}` (name → quantity).
- `update()` is the single refresh function. It calls `renderCart()` (cart panel, drawer, totals, free-delivery bar), `renderGrid()` (product cards, filtered by category and search) and `refreshRec()` (asks the server for new suggestions).
- One click listener on the whole document handles Add, plus, minus and category pills through `data-` attributes.
- Each product tile shows an emoji. A photo `<img>` is laid on top; if the file `/static/img/<slug>.jpg` does not exist, `onerror` removes the image and the emoji shows through.
- Free delivery applies at Rs 3,000; otherwise a Rs 150 fee. These are demo values in the JavaScript.
- `analytics.html` fetches `/api/rules` and `/api/stats` and draws three Chart.js charts: top rules by lift, Apriori vs FP-Growth runtime, and hit rate by strategy.

## 13. One click, end to end

You click **+ Add** on Brandy:

1. The click listener increments `cart["brandy"]` and calls `update()`.
2. `renderCart()` updates the badge, mini-cart, drawer and delivery bar immediately.
3. `refreshRec()` sends `POST /api/recommend` with `{"cart":["brandy"],"n":5}`.
4. Flask passes the cart to `Recommender.recommend()`, which scans the 271 rules in memory (a fraction of a millisecond).
5. The JSON reply `{related, top_picks}` returns to the browser.
6. `renderRec()` draws both lists with confidence, lift and the Add buttons. `renderGrid()` redraws so matching product cards show a "Pairs with your basket" badge.

At no point is any mining algorithm run. The intelligence was baked into `rules.csv` earlier.

## 14. Running and rebuilding

From the project root, with the virtual environment active:

```
python mining/add_local.py      # builds all_transactions.csv (only if you want local items)
python mining/mine_rules.py     # rules.csv and benchmark.csv
python mining/evaluate.py       # eval_results.csv (original Groceries data only)
python app/db.py                # rebuilds database/grocery.db
python run.py                   # open http://127.0.0.1:5000
```

**Rule of thumb:** if the data or thresholds change, rerun mining, then `db.py`, then restart the server. If only HTML changes, just refresh the browser (Ctrl+F5).

## 15. Viva questions and answers

| Question | Short answer |
| --- | --- |
| What problem does the project solve? | Suggests items that are bought together, learned from past baskets instead of hand-coded. |
| Explain support, confidence and lift. | Support is how common the pair is; confidence is the chance B is bought given A; lift compares that to B's normal popularity (above 1 is a real link). Use the brandy example. |
| Why FP-Growth over Apriori? | Same itemsets, but no candidate generation and only two data scans. It was 5.7x faster at low support. |
| Why did you lower min support? | The data is sparse, so at higher values only 25 rules survived. Lowering it gave 271. |
| Why are lift values modest? | Small baskets and a few dominant products (milk, vegetables, rolls). It is a data limitation, not a bug. |
| Why does popularity beat pure rules? | Most rules have low confidence, while popular items have high base rates. Hit rate rewards guessing them. |
| What did you do about it? | Blended score: take the higher of popularity and rule confidence. It ties the baseline while keeping strong rules. |
| How did you avoid cheating in evaluation? | Rules were mined on the 80% training split only, and the test item was hidden from the cart. |
| Why is mining not done in Flask? | It is slow. Precomputing makes each request a fast lookup. |
| What is the cold-start problem? | A cart with no matching rule. The system falls back to best sellers. |
| Which data is synthetic? | The 300 local baskets, plus demo prices, categories and emojis. Evaluation uses only real Groceries data. |
| What would you improve? | Re-mine from saved checkouts, add collaborative filtering and time-aware rules, and test on a larger dataset like Instacart. |