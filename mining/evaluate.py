import random
import pandas as pd
from collections import Counter
from sklearn.model_selection import train_test_split
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
from preprocess import load_baskets

MIN_SUPPORT, MIN_CONF = 0.001, 0.03
KS = [3, 5, 10]
random.seed(42)

baskets = load_baskets()
train, test = train_test_split(baskets, test_size=0.2, random_state=42)

# Mine rules on TRAIN baskets only
te = TransactionEncoder()
df = pd.DataFrame(te.fit(train).transform(train), columns=te.columns_)
freq = fpgrowth(df, min_support=MIN_SUPPORT, use_colnames=True, max_len=3)
rules = association_rules(freq, metric="confidence", min_threshold=MIN_CONF)
rules = rules[rules["lift"] >= 1.0]
rule_list = [(set(a), set(c), cf, lf) for a, c, cf, lf in
             zip(rules.antecedents, rules.consequents, rules.confidence, rules.lift)]
popular = [i for i, _ in Counter(x for b in train for x in b).most_common()]
print("Train baskets:", len(train), "| Test baskets:", len(test), "| Rules:", len(rule_list))

def recommend_rules(cart, n, key):
    scores = {}
    for ante, cons, cf, lf in rule_list:
        if ante <= cart:
            s = {"confidence": cf, "lift": lf, "conf_x_lift": cf * lf}[key]
            for item in cons - cart:
                scores[item] = max(scores.get(item, 0), s)
    recs = [i for i, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]
    for p in popular:                      # fallback fills remaining slots
        if len(recs) >= n:
            break
        if p not in cart and p not in recs:
            recs.append(p)
    return recs[:n]

def recommend_popular(cart, n):
    return [p for p in popular if p not in cart][:n]

base_p = {i: c / len(train) for i, c in Counter(x for b in train for x in b).items()}

def recommend_blended(cart, n):
    score = {i: p for i, p in base_p.items() if i not in cart}
    for ante, cons, cf, lf in rule_list:
        if ante <= cart:
            for item in cons - cart:
                score[item] = max(score[item], cf)
    return [i for i, _ in sorted(score.items(), key=lambda x: x[1], reverse=True)][:n]

strategies = {
    "rules_by_confidence": lambda c, n: recommend_rules(c, n, "confidence"),
    "rules_by_lift":       lambda c, n: recommend_rules(c, n, "lift"),
    "rules_by_conf_x_lift": lambda c, n: recommend_rules(c, n, "conf_x_lift"),
    "popularity_baseline": recommend_popular,
        "blended_probability": recommend_blended,
}

hits = {name: {k: 0 for k in KS} for name in strategies}
total = 0
for b in test:
    hidden = random.choice(b)
    cart = set(b) - {hidden}
    total += 1
    for name, fn in strategies.items():
        recs = fn(cart, max(KS))
        for k in KS:
            hits[name][k] += hidden in recs[:k]

res = pd.DataFrame([{"strategy": name, **{f"hit@{k}": round(hits[name][k] / total, 4) for k in KS}}
                    for name in strategies])
res.to_csv("data/processed/eval_results.csv", index=False)
print(res.to_string(index=False))