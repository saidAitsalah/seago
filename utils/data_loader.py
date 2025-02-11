import json
import asyncio

async def load_parsed_blast_hits(json_file, progress_callback=None):
    """Load parsed BLAST hits from a JSON file with optional progress callback."""

    def load_json_sync(file_path):  # Synchronous function for run_in_executor
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data

    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, load_json_sync, json_file)

    if 'results' in data:
        results = data.get("results", [])

        if progress_callback:  # Example progress (very basic)
            file_size = len(json.dumps(data).encode('utf-8')) # Approximate size
            chunk_size = 1024 * 10 # 10KB chunks (adjust as needed)
            for i in range(0, file_size, chunk_size):
                await asyncio.sleep(0.01) # Simulate some processing time
                progress = (i / file_size) * 100
                progress_callback(progress)  # Call the callback

        return results
    else:
        raise ValueError("The JSON file does not contain the 'results' key.")