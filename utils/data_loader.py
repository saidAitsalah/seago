import json


def load_parsed_blast_hits(json_file):
    """Load parsed BLAST hits from a JSON file."""
    with open(json_file, 'r') as file:
        data = json.load(file)
    if 'results' in data:
        return data['results']
    else:
        raise ValueError("The JSON file does not contain the 'results' key.")
