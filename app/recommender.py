import pandas as pd

class Recommender:
    def __init__(self, rules_path="data/processed/rules.csv",
                 raw_path="data/processed/all_transactions.csv"):
        r = pd.read_csv(rules_path)
        self.rules = [
            (set(a.split(", ")), set(c.split(", ")), conf, lift)
            for a, c, conf, lift in zip(r.antecedents, r.consequents, r.confidence, r.lift)
        ]
        raw = pd.read_csv(raw_path).dropna().drop_duplicates()
        raw["itemDescription"] = raw["itemDescription"].str.strip().str.lower()
        baskets = (raw.groupby(["Member_number", "Date"])["itemDescription"]
                   .apply(lambda x: set(x)))
        baskets = [b for b in baskets if len(b) > 1]
        counts = {}
        for b in baskets:
            for i in b:
                counts[i] = counts.get(i, 0) + 1
        self.base_p = {i: c / len(baskets) for i, c in counts.items()}
        self.products = sorted(self.base_p)

    def recommend(self, cart, n=5):
        cart = {i.strip().lower() for i in cart}

        # 1) Related items: rules only, ranked by confidence
        related = {}
        for ante, cons, conf, lift in self.rules:
            if ante <= cart:
                for item in cons - cart:
                    if item not in related or conf > related[item][0]:
                        related[item] = (conf, lift)
        related_list = [
            {"item": i, "confidence": round(v[0], 3), "lift": round(v[1], 2)}
            for i, v in sorted(related.items(), key=lambda x: x[1][0], reverse=True)
        ][:n]

        # 2) Top picks: blended probability (rule confidence vs base popularity)
        score = {i: (p, "popular") for i, p in self.base_p.items() if i not in cart}
        for item, (conf, lift) in related.items():
            if item in score and conf > score[item][0]:
                score[item] = (conf, "rule")
        top = sorted(score.items(), key=lambda x: x[1][0], reverse=True)[:n]
        top_picks = [{"item": i, "probability": round(v[0], 3), "reason": v[1]}
                     for i, v in top]

        return {"related": related_list, "top_picks": top_picks}

if __name__ == "__main__":
    rec = Recommender()
    for cart in (["sausage"], ["whole milk", "yogurt"], ["brandy"]):
        out = rec.recommend(cart, 5)
        print(cart)
        print("  related:  ", out["related"])
        print("  top picks:", out["top_picks"])