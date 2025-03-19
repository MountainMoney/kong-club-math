from collections import defaultdict
import os


class OutputFiles:
    """Construct all output filename and directories."""

    def __init__(self, game_config: object):
        self.game_config = game_config
        self.setup_output_directories()
        self.assign_config_details()
        self.assign_book_details()
        self.assign_force_details()
        self.assign_lookup_details()

    def check_folder_exists(self, folder_path: str) -> None:
        """Check if target folder exists, and create if it does not."""
        if not (os.path.exists(folder_path)):
            os.makedirs(folder_path)

    # Check existence of output folders and create them if they do not exist.
    def setup_output_directories(self):
        """Entrypoint for saving all output files."""
        self.library_path = str.join("/", ["games", self.game_config.game_id, "library"])
        self.temp_path = str.join("/", [self.library_path, "temp_multi_threaded_files"])
        self.config_path = str.join("/", [self.library_path, "configs"])
        self.force_path = str.join("/", [self.library_path, "forces"])
        self.book_path = str.join("/", [self.library_path, "books"])
        self.compressed_path = str.join("/", [self.library_path, "books_compressed"])
        self.lookup_path = str.join("/", [self.library_path, "lookup_tables"])
        self.optimization_path = str.join("/", [self.library_path, "optimization_files"])
        self.optimization_result_path = str.join("/", [self.library_path, "optimization_files", "trial_results"])

        all_paths = [
            "library_path",
            "book_path",
            "compressed_path",
            "lookup_path",
            "config_path",
            "force_path",
            "temp_path",
            "optimization_path",
            "optimization_result_path",
        ]
        for p in all_paths:
            self.check_folder_exists(getattr(self, p))

    # Assign filenames and output file locations
    def assign_config_details(self):
        """All config filenames and paths."""
        self.configs = {
            "folder_dir": str.join("/", [self.library_path, "configs"]),
            "names": {
                "manifest": "manifest.json",
                "be_config": "config.json",
                "fe_config": "fe_config.json",
                "math_config": "math_config.json",
            },
            "paths": {
                "manifest": self.config_path + "/manifest.json",
                "be_config": self.config_path + "/config.json",
                "fe_config": self.config_path + "/config_fe_" + str(self.game_config.game_id) + ".json",
                "math_config": self.config_path + "/math_config.json",
            },
        }

    def assign_book_details(self):
        """Compressed and uncompressed simulation books."""
        self.books = defaultdict(dict)
        for mode in self.game_config.bet_modes:
            self.books[mode.get_name()] = {
                "folder_dir": self.book_path,
                "names": {
                    "books_uncompressed": f"books_{mode.get_name()}.json",
                    "books_compressed": f"books_{mode.get_name()}.json.zst",
                },
                "paths": {
                    "books_uncompressed": self.book_path + f"/books_{mode.get_name()}.json",
                    "books_compressed": self.compressed_path + f"/books_{mode.get_name()}.json.zst",
                },
            }

    def assign_force_details(self):
        """Recorded game event files."""
        self.force = defaultdict(dict)
        for mode in self.game_config.bet_modes:
            self.force[mode.get_name()] = {
                "folder_dir": self.force_path,
                "names": {"force_record": f"force_record_{mode.get_name()}.json"},
                "paths": {"force_record": self.force_path + f"/force_record_{mode.get_name()}.json"},
            }

    def assign_lookup_details(self):
        """Lookup tables and gametype win information."""
        self.lookups = defaultdict(dict)
        for mode in self.game_config.bet_modes:
            self.lookups[mode.get_name()] = {
                "folder_dir": self.lookup_path,
                "names": {
                    "base_lookup": f"lookUpTable_{mode.get_name()}.csv",
                    "optimized_lookup": f"lookUpTable_{mode.get_name()}_0.csv",
                    "criteria_id": f"lookUpTableIdToCriteria_{mode.get_name()}.csv",
                    "segmented_id": f"lookUpTableSegmented_{mode.get_name()}.csv",
                },
                "paths": {
                    "base_lookup": self.lookup_path + f"/lookUpTable_{mode.get_name()}.csv",
                    "optimized_lookup": self.lookup_path + f"/lookUpTable_{mode.get_name()}_0.csv",
                    "criteria_id": self.lookup_path + f"/lookUpTableIdToCriteria_{mode.get_name()}.csv",
                    "segmented_id": self.lookup_path + f"/lookUpTableSegmented_{mode.get_name()}.csv",
                },
            }

    # Temporary file construction
    def get_temp_multi_thread_name(self, betmode: str, thread_index: int, repeat_count: int, compress: bool):
        """Naming convention for temp book files."""
        if not compress:
            return str.join(
                "/",
                [
                    self.temp_path,
                    f"books_{str(betmode)}" + "_" + f"{str(thread_index)}" + "_" + f"{repeat_count}.json",
                ],
            )
        elif compress:
            return str.join(
                "/",
                [
                    self.temp_path,
                    f"books_{str(betmode)}" + "_" + f"{str(thread_index)}" + "_" + f"{repeat_count}.json.zst",
                ],
            )

    def get_temp_lookup_name(self, betmode: str, thread_index: int, repeat_count: int):
        """Naming convention for temp lookup files."""
        return str.join(
            "/", [self.temp_path, str.join("_", ["lookUpTable", betmode, str(thread_index), str(repeat_count)])]
        )

    def get_temp_criteria_name(self, betmode: str, thread_index: int, repeat_count: int):
        """Naming convention for temp lookup files."""
        return str.join(
            "/",
            [
                self.temp_path,
                str.join("_", ["lookUpTableIdToCriteria", betmode, str(thread_index), str(repeat_count)]),
            ],
        )

    def get_temp_segmented_name(self, betmode: str, thread_index: int, repeat_count: int):
        """Naming convention for temp lookup files."""
        return str.join(
            "/",
            [
                self.temp_path,
                str.join("_", ["lookUpTableSegmented", betmode, str(thread_index), str(repeat_count)]),
            ],
        )

    def get_temp_force_name(self, betmode: str, thread_index: int, repeat_count: int):
        """Naming convention for temp lookup files."""
        return str.join(
            "/",
            [
                self.temp_path,
                str.join("_", ["force", betmode, str(thread_index), str(repeat_count) + ".json"]),
            ],
        )

    def get_final_book_name(self, betmode: str, compress: bool):
        """Returns final simulation books output name."""
        if compress:
            return str.join(
                "/",
                [
                    self.compressed_path,
                    "books_" + betmode + ".json.zst",
                ],
            )
        else:
            return str.join(
                "/",
                [
                    self.book_path,
                    "books_" + betmode + ".json",
                ],
            )

    # Final output filenames, created by joining temporary force, lookup and book files.
    def get_final_lookup_name(self, betmode: str):
        """Final csv lookup table name."""
        return str.join("/", [self.lookup_path, "lookUpTable_" + betmode + ".csv"])

    def get_final_segmented_name(self, betmode: str):
        """Final csv segmented wins lookup table name."""
        return str.join("/", [self.lookup_path, "lookUpTableSegmented_" + betmode + ".csv"])

    def get_final_criteria_name(self, betmode: str):
        """Final csv showing simulation number to criteria mapping."""
        return str.join("/", [self.lookup_path, "lookUpTableIdToCriteria_" + betmode + ".csv"])
