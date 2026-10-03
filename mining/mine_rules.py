import time
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules
from preprocess import load_baskets

MIN_SUPPORT = 0.0007
MIN_CONFIDENCE = 0.03
MIN_LIFT = 1.0

baskets = load_baskets("data/processed/all_transactions.csv")
te = TransactionEncoder()
df = pd.DataFrame(te.fit(baskets).transform(baskets), columns=te.columns_)
print("Baskets:", len(df), "| Products:", df.shape[1])

# Run both algorithms and time them
t = time.time()
freq_ap = apriori(df, min_support=MIN_SUPPORT, use_colnames=True, max_len=3)
t_ap = time.time() - t

t = time.time()
freq_fp = fpgrowth(df, min_support=MIN_SUPPORT, use_colnames=True, max_len=3)
t_fp = time.time() - t

print(f"Apriori:   {len(freq_ap)} itemsets in {t_ap:.3f}s")
print(f"FP-Growth: {len(freq_fp)} itemsets in {t_fp:.3f}s")

# Generate and filter rules
rules = association_rules(freq_fp, metric="confidence", min_threshold=MIN_CONFIDENCE)
rules = rules[rules["lift"] >= MIN_LIFT].sort_values("lift", ascending=False)

# Make itemsets readable and CSV-friendly
rules["antecedents"] = rules["antecedents"].apply(lambda s: ", ".join(sorted(s)))
rules["consequents"] = rules["consequents"].apply(lambda s: ", ".join(sorted(s)))
rules = rules[["antecedents", "consequents", "support", "confidence", "lift"]]

rules.to_csv("data/processed/rules.csv", index=False)
print("Rules saved:", len(rules))
print(rules.head(10))

rows = []
for s in [0.01, 0.005, 0.003, 0.002, 0.001]:
    t = time.time(); a = apriori(df, min_support=s, use_colnames=True, max_len=3); ta = time.time() - t
    t = time.time(); f = fpgrowth(df, min_support=s, use_colnames=True, max_len=3); tf = time.time() - t
    rows.append({"min_support": s, "itemsets": len(f), "apriori_s": round(ta, 3), "fpgrowth_s": round(tf, 3)})
pd.DataFrame(rows).to_csv("data/processed/benchmark.csv", index=False)
print(pd.DataFrame(rows))