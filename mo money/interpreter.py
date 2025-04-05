import re

def interpret_investment_prompt(prompt):
    # Extracting the information using regular expressions
    avoid_investment = re.search(r"avoids (.+?)\.", prompt).group(1)
    start_date = re.search(r"investment start date was (.+?)\.", prompt).group(1)
    end_date = re.search(r"investment end date was (.+?)\.", prompt).group(1)
    budget = re.search(r"investment budget is \$(\d+)\.", prompt).group(1)
    
    return {
        "Avoids Investment In": avoid_investment,
        "Investment Start Date": start_date,
        "Investment End Date": end_date,
        "Investment Budget": budget
    }

# Example prompt
prompt = "What does this person not want to invest in, what is the start and end date of there investments in yyyy-mm-dd format, what is there? (Andrew Vega is 77 years old and his investment start date was February 9th, 2016. His investment end date was July 14th, 2016. He enjoys knitting and avoids Real Estate and Construction. Their total investment budget is $49434.)"

# Interpreting the prompt
investment_info = interpret_investment_prompt(prompt)
print(investment_info)