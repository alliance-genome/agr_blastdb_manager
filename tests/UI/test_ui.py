import json
import time

import click
from rich.console import Console
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

console = Console()


def run_test(mod, db_type, items, sequence, release):
    for item in items:
        browser = webdriver.Chrome()

        # Update URL construction to handle different MODs, DB types, and releases
        if mod == "SGD" and db_type in ["main", "fungal"]:
            url = f"https://blast.alliancegenome.org/blast/{mod}/{db_type}"
        else:
            url = f"https://blast.alliancegenome.org/blast/{mod}/{release}"

        browser.get(url)
        console.log(f"Testing {item} for {mod} - {db_type} (Release: {release})")

        # Rest of the function remains the same
        checkbox = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, item))
        )
        checkbox.click()
        console.log(f"Clicked {item}")

        input_box = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.NAME, "sequence"))
        )
        input_box.send_keys(sequence)
        console.log(f"Sent sequence")

        element = browser.find_element(By.ID, "method")
        element.click()
        console.log("Clicked button")

        for _ in tqdm(range(5)):
            time.sleep(1)

        try:
            next_page_element = WebDriverWait(browser, 600).until(
                EC.presence_of_element_located((By.ID, "view"))
            )
            browser.save_screenshot(f"{mod}_{db_type}_{release}_{item}.png")
            for _ in tqdm(range(15)):
                time.sleep(1)
        except Exception as e:
            console.log(e)

        browser.quit()


@click.command()
@click.option("-m", "--mod", help="The MOD to test")
@click.option("-t", "--type",
              help="The DB type to test, i.e. main or fungal for SGD, or the release version for other MODs")
@click.option("-s", "--single_item", help="How many items to test", default=1)
@click.option(
    "-M",
    "--molecule",
    help="The molecule to test, nucl or prot only, default nucl",
    default="nucl",
)
@click.option(
    "-n",
    "--number_of_items",
    help="number of items to test, random, default all, cannot be used with single item",
)
def prepare_test(mod, type, single_item, number_of_items, molecule):
    data = json.loads(open("config.json").read())

    if mod == "SGD":
        db_types = ["main", "fungal"] if type == "all" else [type]
        for db_type in db_types:
            run_test(mod, db_type, data[mod][db_type]["items"], data[mod][db_type][molecule], "")
    else:
        release = data[mod]["current_release"]
        run_test(mod, "main", data[mod]["items"], data[mod][molecule], release)


if __name__ == "__main__":
    prepare_test()