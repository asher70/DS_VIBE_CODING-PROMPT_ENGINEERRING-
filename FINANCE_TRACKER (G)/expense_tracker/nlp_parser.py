import re
from datetime import datetime

# Category keyword mappings
CATEGORY_KEYWORDS = {
    "Food & Dining": ["food", "dining", "dinner", "lunch", "breakfast", "groceries", "grocery", "restaurant", "cafe", "coffee", "starbucks", "pizza", "burger", "eat", "eating", "supermarket", "subway"],
    "Rent & Housing": ["rent", "housing", "apartment", "flat", "room", "landlord", "maintenance", "mortgage"],
    "Salary & Income": ["salary", "paycheck", "wage", "wages", "corporate", "dividend", "interest", "bonus"],
    "Utilities & Bills": ["utility", "utilities", "electricity", "gas", "water", "internet", "wifi", "bill", "bills", "power", "subscription", "netflix", "spotify", "hulu", "amazon prime"],
    "Entertainment & Leisure": ["entertainment", "movie", "movies", "cinema", "concert", "game", "gaming", "play", "party", "clubbing", "leisure", "netflix", "pub", "bar", "drinks"],
    "Transportation": ["transport", "transportation", "bus", "metro", "train", "cab", "taxi", "uber", "lyft", "car", "petrol", "diesel", "gasoline", "fuel", "commute", "flight"],
    "Healthcare & Medical": ["health", "healthcare", "medical", "doctor", "dentist", "medicine", "medicines", "pharmacy", "gym", "fitness", "dentistry", "prescription"],
    "Shopping": ["shopping", "clothes", "shoes", "keyboard", "mouse", "gadget", "gadgets", "amazon", "ebay", "target", "walmart", "shirt", "pants"],
    "Investments": ["investment", "investments", "stock", "stocks", "crypto", "bitcoin", "sip", "mutual", "fund", "etf"],
    "Freelance": ["freelance", "gig", "contract", "project", "client", "upwork", "fiverr"]
}

# Transaction type keywords
INCOME_KEYWORDS = ["earned", "received", "salary", "freelance", "bonus", "income", "dividend", "interest", "won", "gift", "credit", "credited"]
EXPENSE_KEYWORDS = ["spent", "paid", "bought", "purchased", "cost", "expense", "bill", "subscription", "fee", "debit", "debited"]

def parse_nlp_input(text):
    """
    Parses a natural language input string and returns a dictionary of transaction properties.
    Example inputs:
      "Spent 500 on Food for dinner"
      "Earned 1200 from client coding project"
      "1500 for rent"
    """
    if not text:
        return None
        
    text_lower = text.lower().strip()
    
    # 1. Parse Amount
    # Matches strings like "500", "500.50", "₹500", "$500", "500rs", "500 rupees"
    # Looking for a number with optional decimals.
    amount = 0.0
    amount_match = re.search(r'(?:[\$₹€£]|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)\s*(?:rs|rupees|dollars|inr|usd)?', text_lower)
    if amount_match:
        amount = float(amount_match.group(1))
        # Remove the matched amount from the text to make parsing title/category cleaner
        matched_str = amount_match.group(0)
        # Avoid removing standalone numbers inside words, so do a safe replace
        text_clean = text_lower.replace(matched_str, "", 1)
    else:
        # Fallback to any standalone number
        fallback_match = re.search(r'\b\d+(?:\.\d{1,2})?\b', text_lower)
        if fallback_match:
            amount = float(fallback_match.group(0))
            text_clean = text_lower.replace(fallback_match.group(0), "", 1)
        else:
            text_clean = text_lower

    # 2. Determine Transaction Type (Income vs Expense)
    tx_type = "Expense"  # Default to expense
    
    # Check if any income keywords are present
    has_income_kw = any(kw in text_clean for kw in INCOME_KEYWORDS)
    has_expense_kw = any(kw in text_clean for kw in EXPENSE_KEYWORDS)
    
    if has_income_kw and not has_expense_kw:
        tx_type = "Income"
    elif "salary" in text_clean or "freelance" in text_clean or "earned" in text_clean or "received" in text_clean:
        tx_type = "Income"

    # 3. Match Category
    category = "Other"
    category_scores = {}
    
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            # Match word boundary to avoid partial matching (e.g. "bus" in "business")
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text_clean):
                score += 1
        if score > 0:
            category_scores[cat] = score
            
    if category_scores:
        # Pick category with highest matched keyword count
        category = max(category_scores, key=category_scores.get)
    else:
        # Try to infer category based on type
        if tx_type == "Income":
            category = "Salary & Income"

    # 4. Extract Title / Description
    # We clean up common action words, prepositions, and stop words to find a clean description
    words_to_remove = [
        "spent", "paid", "bought", "purchased", "cost", "expense", "bill", "subscription",
        "earned", "received", "salary", "freelance", "bonus", "income", "credit", "debited", "credited",
        "for", "on", "from", "at", "to", "in", "with", "rs", "inr", "rupees", "dollars", "usd",
        "a", "an", "the", "of", "and"
    ]
    
    # Clean the sentence
    cleaned_title = text.strip()
    
    # Replace amount from original text case-insensitively
    if amount_match:
        # Locate exact position in original text (ignore case)
        orig_match = re.search(re.escape(amount_match.group(0)), cleaned_title, re.IGNORECASE)
        if orig_match:
            cleaned_title = cleaned_title.replace(orig_match.group(0), "", 1)
        else:
            # Regex match
            cleaned_title = re.sub(r'(?:[\$₹€£]|rs\.?|inr)?\s*' + re.escape(amount_match.group(1)) + r'\s*(?:rs|rupees|dollars|inr|usd)?', '', cleaned_title, flags=re.IGNORECASE)
            
    # Clean up words
    words = cleaned_title.split()
    filtered_words = []
    for w in words:
        clean_w = re.sub(r'[^\w\s]', '', w).lower()
        if clean_w not in words_to_remove:
            filtered_words.append(w)
            
    title = " ".join(filtered_words).strip()
    
    # If title is empty, default it to Category
    if not title:
        title = f"{category} Transaction" if category != "Other" else "Quick Transaction"
    else:
        # Title casing for professional appearance
        title = title[0].upper() + title[1:]
        
    return {
        "title": title,
        "amount": amount,
        "category": category,
        "transaction_type": tx_type,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "notes": f"Parsed from natural language input: '{text}'"
    }

# Quick validation test if run directly
if __name__ == "__main__":
    test_cases = [
        "Spent ₹500 on Food for dinner",
        "Earned 1200 from client coding project",
        "1500 for rent",
        "Paid electricity bill of 120 dollars",
        "Received a bonus of 2000 from work",
        "weekly grocery shopping 180"
    ]
    for case in test_cases:
        print(f"Input: '{case}'")
        print(f"Parsed: {parse_nlp_input(case)}")
        print("-" * 40)
