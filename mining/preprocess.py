import pandas as pd

def load_baskets(path="data/raw/Groceries_dataset.csv"):
    df = pd.read_csv(path)
    df["itemDescription"] = df["itemDescription"].str.strip().str.lower()
    df = df.dropna().drop_duplicates()

    # One basket = one member on one date
    baskets = (
        df.groupby(["Member_number", "Date"])["itemDescription"]
        .apply(lambda x: sorted(set(x)))
        .tolist()
    )

    # Single-item baskets carry no relationship information
    baskets = [b for b in baskets if len(b) > 1]
    return baskets

if __name__ == "__main__":
    b = load_baskets()
    print("Baskets:", len(b))
    print("Example:", b[0])