"""Test file decompression and validate data structure is valid JSON."""

import json
import zstandard as zstd


def decompress(input_path: str):
    """Decompress zst files assuming newline char to indicate different sims."""

    def json_validate(json_blob):
        """Validate each uncompressed result to ensure valid json format."""
        try:
            _ = json.load(json_blob)
        except json.decoder.JSONDecodeError:
            print("Invalid JSON!")

    decompressor = zstd.ZstdDecompressor()
    with open(input_path, "rb") as f:
        decompressed_data = decompressor.decompress(f.read()).decode("UTF-8")

    all_sims = decompressed_data.split("\n")
    for sim in all_sims:
        json_validate(sim)


if __name__ == "__main__":

    test_file = "games/0_0_lines/library/books_compressed/books_base.json.zst"
    decompress(test_file)
