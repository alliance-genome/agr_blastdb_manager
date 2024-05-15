import sys

from bs4 import BeautifulSoup


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

    print(items)


if __name__ == "__main__":
    main()
