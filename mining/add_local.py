import random
import pandas as pd

random.seed(42)

# (core items, optional items)
TEMPLATES = {
    "chai":      (["doodh", "chai patti", "cheeni"], ["rusk", "biscuits"]),
    "pulao":     (["chawal", "cooking oil", "namak"], ["masala", "pyaaz", "ghee"]),
    "roti_daal": (["atta", "daal", "cooking oil"], ["pyaaz", "tamatar", "namak"]),
    "breakfast": (["anda", "double roti", "doodh"], ["dahi", "paratha"]),
    "biryani":   (["chawal", "masala", "dahi", "pyaaz"], ["tamatar", "ghee"]),
    "salan":     (["aloo", "pyaaz", "tamatar", "masala"], ["cooking oil"]),
}
ALL_LOCAL = sorted({i for c, o in TEMPLATES.values() for i in c + o})

rows, member = [], 90001
for core, opt in TEMPLATES.values():
    for _ in range(50):
        items = list(core) + [o for o in opt if random.random() < 0.5]
        if random.random() < 0.10:                     # noise: forgot a core item
            items.remove(random.choice(core))
        if random.random() < 0.15:                     # noise: random extra item
            items.append(random.choice(ALL_LOCAL))
        date = f"{random.randint(1, 28):02d}-{random.randint(1, 12):02d}-2015"
        for it in set(items):
            rows.append({"Member_number": member, "Date": date, "itemDescription": it})
        member += 1

local = pd.DataFrame(rows)
groceries = pd.read_csv("data/raw/Groceries_dataset.csv")
combined = pd.concat([groceries, local], ignore_index=True)
combined.to_csv("data/processed/all_transactions.csv", index=False)
print("Local baskets:", member - 90001, "| Total rows:", len(combined))