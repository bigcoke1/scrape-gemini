from main import *

if __name__ == "__main__":
    with open("questions.txt", "r") as f:
        questions = f.readlines()
    for q in questions:
        try:
            day_tolerence = get_day_tolerence(q)
            links = search_google(q)
            links = [link for link in links if link is not None]
            links = links[:5]
            result = iter_result(links, day_tolerence)
            print(f"'{q}' is completed")
        except:
            continue