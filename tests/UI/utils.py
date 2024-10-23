import sys

from bs4 import BeautifulSoup
import requests


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
        return

    filename = sys.argv[1]

    with open(filename, "r") as f:
        data = f.read()

    soup = BeautifulSoup(data, features="html.parser")
    # print(soup)

    items = []
    for tag in soup.find_all("a", class_="jstree-anchor"):
        # print(tag.text)
        # print(tag.get("id"))
        items.append(tag.get("id"))

    print(sorted(list(set(items))))


def main2(url):
    response = requests.get(url)
    data = response.text
    print(data)

    soup = BeautifulSoup(data, features="html.parser")
    # print(soup)

    items = []
    for tag in soup.find_all("a", class_="jstree-anchor"):
        # print(tag.text)
        # print(tag.get("id"))
        items.append(tag.get("id"))

    return items


if __name__ == "__main__":
    # url = sys.argv[1]
    # result = main(url)
    # print(result)
    main()
