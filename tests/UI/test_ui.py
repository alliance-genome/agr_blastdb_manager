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


def run_test(mod, items, type, sequence):

    # Locate and click the checkbox
    for item in items:
        # Set up the browser (replace "chrome" with "firefox" for Firefox)
        browser = webdriver.Chrome()

        # Navigate to your webpage
        browser.get(f"https://blast.alliancegenome.org/blast/{mod}/{type}")
        console.log(f"Testing {item}")
        checkbox = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, item))
        )
        checkbox.click()
        console.log(f"Clicked {item}")

        # Locate and fill out the input box
        input_box = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.NAME, "sequence"))
        )
        input_box.send_keys(sequence)
        console.log(f"Sent sequence")

        element = browser.find_element(By.ID, "method")
        element.click()
        element.click()
        console.log("Clicked button")

        for _ in tqdm(range(20)):  # Pauses the script for 10 seconds
            time.sleep(1)

        try:
            next_page_element = WebDriverWait(browser, 600).until(
                EC.presence_of_element_located((By.ID, "view"))
            )
            browser.save_screenshot(f"SGD/{item}.png")
            for _ in tqdm(range(20)):  # Pauses the script for 10 seconds
                time.sleep(1)
        except Exception as e:
            console.log(e)

        browser.quit()


@click.command()
@click.option("-m", "--mod", help="The MOD to test")
@click.option("-t", "--type", help="The DB type to test, i.e. fungal for SGD")
@click.option("-s", "--single_item", help="How many items to test", default=1)
@click.option("-M", "--molecule", help="The molecule to test, nucl or prot only, default nucl", default="nucl")
@click.option(
    "-n",
    "--number_of_items",
    help="number of items to test, random, default all, cannot be used with single item",
)
def prepare_test(mod, type, single_item, number_of_items, molecule):
    """ """

    # print(mod, type, single_item, number_of_items, molecule)

    data = json.loads(open("config.json").read())
    run_test(mod, data[mod][type]["items"], type, data[mod][type][molecule])


if __name__ == "__main__":
    prepare_test()
