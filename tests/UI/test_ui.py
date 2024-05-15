import click

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from tqdm import tqdm
import json
from rich import Console


console = Console()

def run_test(mod, items, db_type, sequence):

    # Set up the browser (replace "chrome" with "firefox" for Firefox)
    browser = webdriver.Chrome()

    # Navigate to your webpage
    browser.get(f"https://blast.alliancegenome.org/blast/{mod}/{type}")

    # Locate and click the checkbox
    for item in items:
        checkbox = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "Akanthomyces_anchor"))
        )
        checkbox.click()

        # Locate and fill out the input box
        input_box = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.NAME, "sequence"))
        )
        input_box.send_keys(sequence)


        element = browser.find_element(By.ID, "method")
        element.click()

        print("clicked")
        for _ in tqdm(range(10)):  # Pauses the script for 10 seconds
            time.sleep(1)

        try:
            next_page_element = WebDriverWait(browser, 600).until(
                EC.presence_of_element_located((By.ID, "view"))
            )
            browser.save_screenshot(f'{item}.png')
            for _ in tqdm(range(10)):  # Pauses the script for 10 seconds
                time.sleep(1)
        except Exception as e:
            console.log(e)
            browser.quit()

@click.command()
@click.option("-m", "--mod", help="The MOD to test")
@click.option("-t", "--type", help="The DB type to test, i.e. fungal for SGD")
@click.option("-s", "--single_item", help="How many items to test", default=1)
@click.option("-n", "--number_of_items", help="number of items to test, random, default all, cannot be used with single item")
def prepare_test(mod, type, single_item, number_of_items):

    data = json.loads(open("config.json").read())
    run_test(mod, data[mod][type]["items"], db_type, data[mod][type][sequence])

if __name__ == "__main__":
    prepare_test()