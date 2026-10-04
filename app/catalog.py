import re, hashlib

# (category, emoji, price range in Rs, unit, keywords) - first match wins
RULES = [
 ("Beverages", "🥤", (60, 450), "1 bottle", ["juice","soda","beer","wine","water","coffee","tea","liquor","brandy","rum","whisky","champagne","prosecco","vodka","cocoa","drinks","beverages"]),
 ("Dairy & Eggs", "🥛", (80, 700), "1 pack", ["milk","yogurt","curd","butter","cream","cheese","egg","doodh","dahi","anda","margarine","whipped","uht"]),
 ("Bakery", "🥖", (40, 400), "per pack", ["bread","roll","bun","pastry","cake","biscuit","rusk","paratha","waffle","brioche","cookie","roti","bakery"]),
 ("Meat & Deli", "🥩", (250, 1400), "500 g", ["beef","pork","chicken","sausage","frankfurter","ham","meat","fish","turkey","salmon","liver"]),
 ("Fresh Produce", "🥦", (60, 500), "per kg", ["fruit","vegetable","apple","banana","onion","potato","tomato","lemon","berries","herbs","salad","pip","citrus","tropical","root","pyaaz","aloo","tamatar","mushroom","grapes"]),
]
DEFAULT = ("Pantry & Home", "🛒", (60, 900), "1 pack")

EMOJI = {
 "whole milk":"🥛","uht-milk":"🥛","doodh":"🥛","yogurt":"🥣","dahi":"🥣","curd":"🥣","butter":"🧈","ghee":"🧈",
 "domestic eggs":"🥚","anda":"🥚","chawal":"🍚","rice":"🍚","atta":"🌾","daal":"🫘","cooking oil":"🫒","namak":"🧂",
 "cheeni":"🍬","chai patti":"🍵","masala":"🌶️","brown bread":"🍞","double roti":"🍞","rolls/buns":"🥖","pastry":"🥐",
 "sausage":"🌭","frankfurter":"🌭","chicken":"🍗","beef":"🥩","pork":"🥩","soda":"🥤","bottled water":"💧",
 "canned beer":"🍺","bottled beer":"🍺","coffee":"☕","fruit/vegetable juice":"🧃","tropical fruit":"🍍",
 "citrus fruit":"🍊","other vegetables":"🥦","root vegetables":"🥕","pyaaz":"🧅","aloo":"🥔","tamatar":"🍅",
 "shopping bags":"🛍️","newspapers":"📰","cat food":"🐱","dog food":"🐶","pet care":"🐾","napkins":"🧻","softener":"🧴",
}

def describe(name):
    n = name.strip().lower()
    tokens = re.findall(r"[a-z]+", n)
    cat = None
    for c, em, pr, unit, kws in RULES:
        if any(t == k or (len(k) > 3 and t.startswith(k)) for t in tokens for k in kws):
            cat = (c, em, pr, unit)
            break
    cat = cat or DEFAULT
    lo, hi = cat[2]
    h = int(hashlib.md5(n.encode()).hexdigest()[:8], 16)
    price = lo + (h % ((hi - lo) // 5)) * 5          # deterministic demo price
    return {"category": cat[0], "emoji": EMOJI.get(n, cat[1]), "price": price,
            "unit": cat[3], "slug": re.sub(r"[^a-z0-9]+", "-", n).strip("-")}