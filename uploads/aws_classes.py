"""Store and check file upload details"""

import os
import sys
import json
import hashlib
import warnings
import threading
from botocore.exceptions import NoCredentialsError


class CheckFiles:
    """Compare file hash values."""

    def __init__(self, game: str):
        self.game = game

    def get_lut_length(self, lut_base_path, file):
        """Verify LUT item count matches book count."""
        full_file = lut_base_path + file
        csv = open(full_file, "r")
        book_count = len(csv.readlines)

        return book_count

    def get_lut_sha(self, lut_base_path, target_file):
        """Compare hash of lookup tables."""
        file_to_hash = lut_base_path + target_file
        with open(file_to_hash, "rb") as f:
            sha256_file = hashlib.sha256()
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256_file.update(data)

        sha256_hexRep = sha256_file.hexdigest()

        return sha256_hexRep

    def file_checker(self):
        """Return valid game modes from config."""
        config_path = "games/" + self.game + "/library/configs/config.json"
        if not os.path.isfile(config_path):
            print("config.json does not exist!")
            return 0
        else:
            game_modes = []
            read_json = json.load(open(config_path))
            for mode in read_json["bookShelfConfig"]:
                game_modes.append(mode["name"])

        return read_json, game_modes

    def get_file_characteristics(self, read_json, game_modes):
        """Verify config file details."""
        all_check_items = []
        bookshelf = read_json["bookShelfConfig"]
        lut_base_path = "Games/" + self.game + "/Library/"
        mode_params = {}
        try:
            mode_params["EXPECTED_FORCE_SHA"] = read_json["standardForceFile"]["sha256"]
            mode_params["ACTUAL_FORCE_SHA"] = self.get_lut_sha(
                lut_base_path + "Forces/", read_json["standardForceFile"]["file"]
            )

            for mode, _ in enumerate(game_modes):

                mode_params["MODE"] = game_modes[mode]
                mode_params["LUT"] = bookshelf[mode]["tables"][0]["file"]
                print("SHOULD BE A LUT PATH (if yes, delete this print):", bookshelf[mode]["tables"][0]["file"])

                mode_params["EXPECTED_LUT_LENGTH"] = int(bookshelf[mode]["bookLength"])
                mode_params["ACTUAL_LUT_LENGTH"] = int(
                    self.get_lut_length(lut_base_path + "LookUpTables/", bookshelf[mode]["tables"][0]["file"])
                )

                mode_params["EXPECTED_SHA"] = bookshelf[mode]["tables"][0]["sha256"]
                mode_params["ACTUAL_SHA"] = self.get_lut_sha(
                    lut_base_path + "LookUpTables/", bookshelf[mode]["tables"][0]["file"]
                )

                all_check_items.append(mode_params)
        except:
            raise FileNotFoundError("Cant obtain required file paramaters")

        return all_check_items

    def compare_file_values(self, file_dict):
        """Verify file hash and length of lookup table items."""
        errors = 0
        for mode in file_dict:
            if mode["EXPECTED_LUT_LENGTH"] != mode["ACTUAL_LUT_LENGTH"]:
                errors += 1
                raise FileNotFoundError(
                    f"Actual and Expected lookuptable length do not match! - Source: {mode['MODE']}"
                )
            elif mode["EXPECTED_SHA"] != mode["ACTUAL_SHA"]:
                errors += 1
                raise FileNotFoundError(
                    f"Actual and Expected SHA256 values do not match! - Source: {mode['MODE']}"
                )

        if errors > 0:
            raise RuntimeError("File comparison failed! Check Hash values and book lenghts with config file.")
        elif errors == 0:
            return True


class FileDetails:
    """Obtain details of files being uploaded."""

    def __init__(self, game_to_upload, game_modes):
        self.game_to_upload = game_to_upload + "/"
        self.game_modes = game_modes

    def get_win_weights(self, fname):
        """Return sorted win distribution."""
        file = open(fname, "r")
        winDict = {}
        total_weight = 0
        for line in file:
            _, weight, win = line.split(",")
            try:
                winDict[float(win)] += float(weight)
            except:
                winDict[float(win)] = float(weight)
            total_weight += float(weight)

        sorted_wins = list(winDict.keys())
        sorted_wins.sort()
        sortedWeights = [winDict[win] for win in sorted_wins]

        return sorted_wins, sortedWeights

    def get_file_paths(
        self, books=True, configFiles=True, lookupTables=True, forceFiles=True, eventList=False, winDist=False
    ):

        game_to_upload = self.game_to_upload
        game_modes = self.game_modes

        gamePath = "/".join(["Games", game_to_upload[:-1], "Library"])
        all_file_paths = {}
        if configFiles:
            try:
                all_file_paths["config_frontend"] = "/".join(
                    [gamePath, "Configs", "config_fe_" + game_to_upload[:-1] + ".json"]
                )
                all_file_paths["config_backend"] = "/".join([gamePath, "Configs", "config.json"])
                all_file_paths["standardForce"] = "/".join([gamePath, "Forces", "force.json"])
            except FileNotFoundError:
                print("Config File or force.json Upload Error!")

        # Lookup tables, books, force results
        for mode in game_modes:
            books_name = mode + "_books"
            lut_name = mode + "_LUT"
            force_name = mode + "_forceFile"
            if books:
                try:
                    all_file_paths[books_name] = "/".join(
                        [gamePath, "book_compressed", "books_" + mode + ".json.zst"]
                    )
                except FileNotFoundError:
                    print("Book Upload Error!")
            if lookupTables:
                try:
                    all_file_paths[lut_name] = "/".join(
                        [gamePath, "lookup_tables", "lookUpTable_" + mode + "_0.csv"]
                    )
                except FileNotFoundError:
                    print("LookupTable Upload Error!")
            if forceFiles:
                try:
                    all_file_paths[force_name] = "/".join([gamePath, "Forces", "force_record_" + mode + ".json"])
                except FileNotFoundError:
                    print("Force File Upload Error!")

            if eventList:
                all_file_paths["eventFile"] = "/".join([gamePath, "configs", "event_config_" + mode + ".json"])
        # Event list
        if eventList:
            all_file_paths["eventFile"] = "/".join([gamePath, "configs", "uniqueEventList.json"])

        all_file_uploads = all_file_paths.values()
        print("\n***File Paths Found***\n")
        [print(i) for i in all_file_uploads]

        return all_file_uploads

    def check_file_size(self, local_path):
        """Return size of file being uploaded."""

        sys.path.append(local_path.split("/")[0:-2])
        sizeMB = os.path.getsize(local_path) / 1e6
        fname = local_path.split("/")[-1]
        if sizeMB > 100:
            warnings.warn(f"Attempting to Upload Large File: ({sizeMB}) MB -- {fname}")
        return True

    def check_config_details(self):
        """Ensure config file has required fields for ACP upload."""

        config_filepath = "/".join(["games", self.game_to_upload, "library", "configs", "config.json"])
        required_keywords = ["minDenomination", "providerNumber", "gameID", "rtp", "rtpNumber"]
        bookshelf_keywords = ["cost", "rtp", "bookLength"]
        with open(config_filepath, "r") as file:
            jsonObject = json.load(file)

        for keyword in required_keywords:
            if keyword not in jsonObject:
                raise ValueError(f"{keyword} not found in supplied config file!")

        for keyword2 in bookshelf_keywords:
            for mode in jsonObject["bookShelfConfig"]:
                if keyword2 not in mode:
                    raise ValueError(f"{keyword2} not found in supplied config (bookShelfConfig) file!")

        return True

    def check_rtp(self, game_modes):
        """Verify RTP from lookup tables matches configuration file value."""

        config_filepath = "/".join(["Games", self.game_to_upload, "library", "configs", "config.json"])
        config_details = json.load(open(config_filepath, "r"))
        failed = False
        for bookshelf in config_details["bookShelfConfig"]:
            lut_file = "/".join(
                [
                    "games",
                    self.game_to_upload,
                    "library",
                    "lookup_tables",
                    "lookUpTable_" + bookshelf["name"] + "_0.csv",
                ]
            )
            if lut_file.split("/")[-1].split("_")[1] in game_modes:
                wins, weights = self.get_win_weights(lut_file)
                dotProd = 0.0
                total_weight = 0.0
                expected_rtp = config_details["rtpNumber"]

                for win, weight in zip(wins, weights):
                    dotProd += float(win) * float(weight)
                    total_weight += weight
                rtp = (dotProd / total_weight) / bookshelf["cost"]

                if expected_rtp < 1 and round(rtp, 4) != round(expected_rtp, 4):
                    failed = True
                elif expected_rtp > 1 and round(rtp, 2) != round(expected_rtp, 2):
                    failed = True
                if failed:
                    warnings.warn(
                        f"RTP DOES NOT MATCH FOR {lut_file}!\n \nEXPECTED {round(expected_rtp,4)}\nCALCULATED {round(rtp*100,4)}"
                    )

        return failed


class AWSCommands:
    """Upload through S3 API."""

    def __init__(self, s3_client, bucket_name, bucket_folder):
        self.bucket_name = bucket_name
        self.bucket_folder = bucket_folder
        self.s3_client = s3_client
        self.s3_bucket = s3_client.Bucket(bucket_name)

    def upload_to_aws(self, localFile):
        """Verify file exists locally."""
        bucket_object = self.s3_bucket
        bucket_folder = self.bucket_folder

        # Attempt file upload
        try:
            s3_name = bucket_folder + (localFile.split("/")[-1])
            bucket_object.upload_file(
                Filename=localFile,
                Key=s3_name,
                ExtraArgs={"ACL": "public-read"},
                Callback=ProgressPercentage(localFile),
            )

            print(f"{localFile.split('/')[-1]} Uploaded Successfully")
            return True
        except FileNotFoundError:
            print("The file was not found")
            return False
        except NoCredentialsError:
            print("Credentials not available")
            return False


class ProgressPercentage(object):
    """Return upload progress as percentage."""

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        print("\n")

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (self._filename, self._seen_so_far, self._size, percentage)
            )
            sys.stdout.flush()
