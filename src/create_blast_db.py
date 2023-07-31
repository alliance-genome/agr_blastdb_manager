# Paulo Nuin July 2023

import json
import click
from rich import console

console = console.Console()

@click.command()
@click.option('-j', '--input_json', help='JSON file input coordinates')
def create_dbs(input_json):

    db_coordinates = json.load(open(input_json, "r"))

    for entry in db_coordinates:
        console.log(entry)






if __name__ == '__main__':

    create_dbs()