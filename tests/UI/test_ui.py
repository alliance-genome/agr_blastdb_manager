import click

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from tqdm import tqdm


def run_test()

    # Set up the browser (replace "chrome" with "firefox" for Firefox)
    browser = webdriver.Chrome()

    # Navigate to your webpage
    browser.get("https://blast.alliancegenome.org/blast/SGD/fungal")

    # Locate and click the checkbox
    checkbox = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.ID, "Akanthomyces_anchor"))
    )
    checkbox.click()

    # Locate and fill out the input box
    input_box = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.NAME, "sequence"))
    )
    input_box.send_keys(
        "ATGGATTCTGGTATGTTCTAGCGCTTGCACCATCCCATTTAACTGTAAGAAGAATTGCACGGTCCCAATTGCTCGAGAGATTTCTCTTTTACCTTTTTTTACTATTTT"
        "TCACTCTCCCATAACCTCCTATATTGACTGATCTGTAATAACCACGATATTATTGGAATAAATAGGGGCTTGAAATTTGGAAAAAAAAAAAAAACTGAAATATTTTCGT"
        "GATAAGTGATAGTGATATTCTTCTTTTATTTGCTACTGTTACTAAGTCTCATGTACTAACATCGATTGCTTCATTCTTTTTGTTGCTATATTATATGTTTAGAGGTTGCT"
        "GCTTTGGTTATTGATAACGGTTCTGGTATGTGTAAAGCCGGTTTTGCCGGTGACGACGCTCCTCGTGCTGTCTTCCCATCTATCGTCGGTAGACCAAGACACCAAGGTAT"
    )

    # new_tab = WebDriverWait(browser, 10).until(
    #     EC.element_to_be_clickable((By.ID, "toggleNewTab"))
    # )
    # new_tab.click()


    element = browser.find_element(By.ID, "method")
    element.click()

    print("clicked")
    for _ in tqdm(range(20)):  # Pauses the script for 10 seconds
        time.sleep(1)

    try:
        next_page_element = WebDriverWait(browser, 600).until(
            EC.presence_of_element_located((By.ID, "view"))
        )
        print("found")
        browser.save_screenshot('screenshot.png')
        for _ in tqdm(range(10)):  # Pauses the script for 10 seconds
            time.sleep(1)
    except Exception as e:
        print(e)
        browser.quit()

    # print("done")
    # browser.quit()

@click.command()
@click.option("-m", "--mod", help="The MOD to test")
@click.option("-s", "--single_item", help="How many items to test", default=1)
def prepare_test(mod, single_item ):

    con


if __name__ == "__main__":
    check_names()