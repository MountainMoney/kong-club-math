from .rgs_verification import load_game_config


def get_mode_names_from_config(game_config: object):
    """Use BetMode class/config to get all bet mode names."""
    modes = []
    for bet_mode in game_config.bet_modes:
        modes.append(bet_mode.get_name())
    return modes


class ForceTool:
    """
    Pass in target search keys and return book-ids satisfying union of given keys.
    The force_record file could be uploaded if small enough, and polled by the front-end to search for game-keys
    Alternatively, this tool can be used to narrow down ids by finding the union of multiple keys.
    """

    def __init__(self, game_id: str, target_modes=None):
        # Load game-config from id
        self.config = load_game_config(game_id)
        if target_modes is not None:
            self.target_modes = target_modes
        else:
            self.target_modes = get_mode_names_from_config(self.config)

    def set_search_keys(self, search_keys):
        """Set search criteria."""
        self.search_keys = search_keys

    def find_partial_key_match(self, search_keys=None):
        """
        Returns all ids with partial match in the 'search' field. i.e. search_keys = [{'kind':'3'}] returns all recorded 3-kind entries 
        """
        pass

    def find_union_key_match(self, search_key=None):
        """
        Returns all ids 
        """
        pass
