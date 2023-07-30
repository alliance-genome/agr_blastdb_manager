# Paulo Nuin July 2023

import json
import click


@click.command()
@click.option('-j', '--input_json', help='JSON file input coordinates')
def create_dbs(input_json):

    db_coordinates = json.load(open(input_json, "r"))

    print(db_coordinates)






if __name__ == '__main__':

    create_dbs()