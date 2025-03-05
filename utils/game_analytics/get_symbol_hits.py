import json
import os


class HitRateCalculations:
    """Get"""

    def __init__(self, gameID, mode, mode_cost):
        self.gameID = gameID
        self.mode = mode
        self.cost = mode_cost
        self.initialiseFiles()

    def initialiseFiles(self):
        forceFile = str.join(
            "/", ["Games", self.gameID, "Library", "Forces", "force_for_rob_" + self.mode + ".json"]
        )
        lutFile = str.join(
            "/", ["Games", self.gameID, "Library", "LookUpTables", "lookUpTable_" + self.mode + "_0.csv"]
        )
        with open(forceFile) as f:
            fileDict = json.load(f)
            allKeys = [d.keys() for d in fileDict]
        f.close()

        lutIds = []
        weights = []
        payouts = []
        with open(lutFile) as f:
            for line in f:
                lutIds.append(int(line.strip().split(",")[0]))
                weights.append(int(line.strip().split(",")[1]))
                payouts.append(float(line.strip().split(",")[2]))
        f.close()

        self.weights = weights
        self.totalWeight = sum(self.weights)
        self.payouts = payouts
        self.forceDict = fileDict
        self.allKeys = allKeys

    def getHitRates(self, specificIds: list):
        cumulativeWeight = 0
        for id in specificIds:
            cumulativeWeight += self.weights[id - 1]

        prob = cumulativeWeight / self.totalWeight
        try:
            return 1 / prob
        except:
            return 0

    def getAverageWin(self, specificIds: list):
        searchKeysTotalWeight = 0
        # find out the total payout and weights from the force keys subset of the lookup table
        for id in specificIds:
            searchKeysTotalWeight += self.weights[id - 1]
        averageWin = 0
        # multiply each win in the subset of lookup table by the ratio of its weight to normalize the avg payout
        for id in specificIds:
            normalizedPayout = self.payouts[id - 1] * (self.weights[id - 1] / searchKeysTotalWeight)
            averageWin += normalizedPayout
        try:
            return averageWin
        except:
            return 0

    def getSimCount(self, searchKey: dict):
        search_key_count = 0
        for key in self.forceDict:
            if all(key["search"].get(x) == y for x, y in searchKey.items()):
                search_key_count += key["timesTriggered"]
        return search_key_count

    def searchCondition(gameType: str, hasWild: bool, kind: int, symbol: str, wildMult: int):
        dict = {"gameType": gameType, "hasWild": hasWild, "kind": kind, "symbol": symbol, "wildMult": wildMult}
        return dict

    def returnValidIds(self, searchKey):
        allValidIds = []
        for item in self.forceDict:
            if all(item["search"].get(k) == v for k, v in searchKey.items()):
                validIDs = item["bookIds"]
                allValidIds.extend(validIDs)

        return allValidIds


def construct_symbol_keys(config):
    searchKeys = []
    for symTuple in list(config.payTable.keys()):
        searchKeys.append({"kind": symTuple[0], "symbol": symTuple[1]})

    return searchKeys


def analyse_serach_keys(config, modes_to_analyse: list, search_keys: list[dict]):
    hr_summary, av_win_summary, sim_count_summary = {}, {}, {}
    for mode in modes_to_analyse:
        GameObject = HitRateCalculations(config.gameId, mode, mode_cost=config.costMapping[mode])
        hr_summary[mode], av_win_summary[mode], sim_count_summary[mode] = {}, {}, {}
        for search_key in search_keys:
            valid_key_ids = GameObject.returnValidIds(search_key)
            hr = GameObject.getHitRates(valid_key_ids)
            avg_win = GameObject.getAverageWin(valid_key_ids)
            key_instances = GameObject.getSimCount(search_key)
            hr_summary[mode][str(search_key)] = hr
            av_win_summary[mode][str(search_key)] = avg_win
            sim_count_summary[mode][str(search_key)] = key_instances

    return hr_summary, av_win_summary, sim_count_summary


def construct_symbol_probabilities(config, modes_to_analyse: list):
    print("TO DO: Put RTP allocation metrics in.")
    # Check force files exist
    checkFile = []
    for mode in modes_to_analyse:
        force_file = str.join(
            "/", ["Games", config.gameId, "Library", "Forces", "force_for_rob_" + mode + ".json"]
        )
        checkFile.append(os.path.isfile(force_file))
    if not all(checkFile):
        raise RuntimeError("Force File Does Not Exist.")

    symbol_search_keys = construct_symbol_keys(config)
    hr_summary, av_win_summary, sim_count_summary = analyse_serach_keys(
        config, modes_to_analyse, symbol_search_keys
    )
    return hr_summary, av_win_summary, sim_count_summary


def construct_custom_key_probabilities(config, modes_to_analyse, cumstom_serach_keys):
    # Check force files exist
    checkFile = []
    for mode in modes_to_analyse:
        force_file = str.join(
            "/", ["Games", config.gameId, "Library", "Forces", "force_for_rob_" + mode + ".json"]
        )
        checkFile.append(os.path.isfile(force_file))
    if not all(checkFile):
        raise RuntimeError("Force File Does Not Exist.")

    hr_summary, av_win_summary, sim_count_summary = analyse_serach_keys(
        config, modes_to_analyse, cumstom_serach_keys
    )
    return hr_summary, av_win_summary, sim_count_summary
