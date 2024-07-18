import spacy
import re

nlp = spacy.load('en_core_web_sm')

STOP_WORDS = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", 
              "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", 
              "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
              "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", 
                "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through",
                "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", 
                "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", 
                "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", 
                "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]
UNWANTED_WORDS = [
    "Advertisement", "advertisement", "ads", "Ad", "ad", "Buy our product", "Buy now", "Shop now", 
    "Click here", "Subscribe", "Sign up", "Join now", "Limited offer", "Sale", "Discount", "Promo", 
    "Deal", "Coupon", "Exclusive offer", "Special offer", "Free trial", "Get your free", "Order now", 
    "Hurry up", "Offer ends soon", "Best price", "Save money", "Use code", "Powered by", "Sponsored by",
    "We use cookies", "cookie policy", "cookies to improve", "cookies for better experience", 
    "cookie settings", "cookie consent", "accept cookies", "This site uses cookies", "privacy policy", 
    "terms of service", "terms and conditions", "Read more", "Learn more", "More info", 
    "advertising purposes", "Third-party cookies", "ad choices"
]
FORMAT_WORDS = [
    "bar graph", "bar chart", "horizontal bar chart", "vertical bar chart", "stacked bar chart", 
    "grouped bar chart", "clustered bar chart",
    "column graph", "column chart", "vertical column chart", "stacked column chart", 
    "grouped column chart", "clustered column chart",
    "line graph", "line chart", "line plot", "trend line", "time series chart",
    "pie chart", "donut chart", "doughnut chart", "circular chart", "ring chart",
    "area chart", "stacked area chart", "stacked area graph", "filled line chart",
    "scatter plot", "scatter diagram", "dot plot", "xy plot",
    "histogram", "frequency distribution chart",
    "box plot", "box-and-whisker plot", "box and whisker plot",
    "bubble chart", "bubble plot",
    "heatmap", "heat map", "density plot",
    "radar chart", "spider chart", "web chart", "star plot",
    "tree map", "treemap",
    "waterfall chart", "bridge chart",
    "gantt chart", "gantt diagram",
    "donut chart", "doughnut chart", "ring chart",
    "sparkline", "sparkline chart",
    "table", "data table", "tabular data",
    "dashboard", "data dashboard",
    "map", "geographical map", "location map", "geo map",
    "timeline", "time line",
    "network diagram", "network graph", "node-link diagram",
    "funnel chart", "sales funnel chart", "conversion funnel chart",
    "violin plot", "violin chart",
    "word cloud", "tag cloud"
]

STOP_WORDS_SET = set(STOP_WORDS)
UNWANTED_WORDS_SET = set(UNWANTED_WORDS)
FORMAT_WORDS_SET = set(FORMAT_WORDS)

def simplify_sentence(text):
    doc = nlp(text)
    normalized_tokens = []
    
    for token in doc:
        if token.text not in STOP_WORDS:
            if token.pos_ == 'VERB':
                normalized_tokens.append(token.lemma_)
            elif token.pos_ == 'NOUN':
                normalized_tokens.append(token.lemma_) 
            else:
                normalized_tokens.append(token.text) 
    
    return ' '.join(normalized_tokens)

def clean_data(text):
    text = re.sub("\W", " ", text)
    pattern = re.compile("|".join(map(re.escape, UNWANTED_WORDS)), re.IGNORECASE)
    text = pattern.sub("", text)
    text = simplify_sentence(text)
    return text

def clean_query(query):
    normalized_tokens = []
    for word in query.split():
        word = word.lower()
        if word not in STOP_WORDS and word not in FORMAT_WORDS:
            normalized_tokens.append(word)
    return " ".join(normalized_tokens)
    
    