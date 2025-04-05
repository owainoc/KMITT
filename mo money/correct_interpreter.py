from transformers import pipeline

# Load the model and tokenizer
model_name = "deepset/roberta-base-squad2"
nlp = pipeline("question-answering", model=model_name, tokenizer=model_name)

# Predefined list of sectors to avoid
avoid_sectors = [
    "Technology", "Financial Services", "Consumer Defensive", "Industrials",
    "Healthcare", "Energy", "Consumer Cyclical", "Communication Services"
]

def extract_investment_info(message):
    questions = [
        "What is the start date?",
        "What is the end date?",
        "What is the budget?",
        "What companies should be avoided?"
    ]
    answers = {}
    for question in questions:
        result = nlp(question=question, context=message)
        answers[question] = result['answer']
    
    # Filter "avoid companies" to only include sectors in the predefined list
    avoid_companies = answers.get("What companies should be avoided?", "")
    filtered_avoid_companies = [
        sector for sector in avoid_sectors if sector.lower() in avoid_companies.lower()
    ]
    answers["What companies should be avoided?"] = filtered_avoid_companies

    return answers

message = (
    "Tristan White is 61 years old, has a hobby of rock climbing, and has an "
    "investment start date of July 17th, 2010 and an investment end date of "
    "November 30th, 2012. He has a budget of $67903 total. Avoid investing in Technology and Energy."
)
info = extract_investment_info(message)
print(info)