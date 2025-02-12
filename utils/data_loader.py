import json
import asyncio
import os

async def load_parsed_blast_hits(json_file, progress_callback=None):
    """Load parsed BLAST hits from a JSON file with optional progress callback."""

    def load_json_sync(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)

    loop = asyncio.get_running_loop()
    file_size = os.path.getsize(json_file)  # Accurate file size

    data = await loop.run_in_executor(None, load_json_sync, json_file)

    if 'results' not in data:
        raise ValueError("The JSON file does not contain the 'results' key.")

    results = data.get("results", [])

    if progress_callback:
        num_results = len(results)
        for i, result in enumerate(results):
            # Process each result here if needed (e.g., data transformation)
            # ... your processing logic for 'result' ...

            progress = (i + 1) / num_results * 100
            progress_callback(progress)
            await asyncio.sleep(0)  # Yield to the event loop

    return results