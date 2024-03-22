# Blake Xu

import csv
import time
import json
import os
import AntiqueScoreUtil
from AntiqueDriver import AntiqueDriver
from pprint import pprint

script_ver = 0.3
support_languages = ["Chinese", "English"]
path = "./dump_data/top100daily/"


class Top100Players:
    def __init__(self, driver):
        self.items_statics = {}
        self.driver = driver
        self.match_ids = {}
        self.daily_data = {"pokemons": {}}
        self.top100_players = []

    def get_current_top_100_players(self):
        print("fetching current top 100 players list")
        url = AntiqueScoreUtil.url_base + "rankings/"
        response_soup = AntiqueScoreUtil.dump_url(self.driver, url)
        # with open('temp.txt', "w") as filea:
        #     filea.write(str(response_soup.select("#content-container > div > div > div > div > p")))
        # response = Driver.get(Driver.url_base + "rankings")
        # soup = BeautifulSoup(response.text, "html.parser")
        count = 0
        for player in response_soup.select("#__next > div > div > div > div > div > div > p"):
            print(player.get_text())
            self.top100_players.append(player.get_text())
            count += 1
            if count >= 100:
                break

    def get_yesterday_one_player_static(self, name, new_mode):
        data = AntiqueScoreUtil.get_one_player_data(self.driver, name, cache_days=1)
        if not data or "player" not in data:
            return {}
        name = data["player"]["profile"]["userShort"]
        if not new_mode:
            all_matches = list(
                filter(
                    lambda _match: AntiqueScoreUtil.get_past_x_day_start_epoch(1)
                                   <= int(_match["GameStartTime"])
                                   < AntiqueScoreUtil.get_past_x_day_start_epoch(0)
                                   and _match["MapSubMode"] == 2,
                    data["player"]["MatchResults"],
                )
            )
        else:
            all_matches = list(
                filter(
                    lambda _match: AntiqueScoreUtil.get_past_x_day_start_epoch(7)
                                   <= int(_match["GameStartTime"])
                                   < AntiqueScoreUtil.get_past_x_day_start_epoch(0)
                                   and _match["MapSubMode"] == 2,
                    data["player"]["MatchResults"],
                )
            )[:50]
        for match in all_matches:
            self.match_ids["{0}_{1}_{2}".format(match["GameStartTime"], match.get("Camp1Score", 0),
                                                match.get("Camp2Score", 0))] = ""
            battle_sets = AntiqueScoreUtil.get_match_battle_set(match, data["player"]["profile"]["uid"])
            if not battle_sets:
                continue
            battle_set = "_".join(battle_sets)
            pokemon_name = AntiqueScoreUtil.unite_data[match["currentPlayer"]["playedPokemonImg"]]["chinese"]
            if pokemon_name not in self.daily_data["pokemons"]:
                self.daily_data["pokemons"][pokemon_name] = {
                    "win": 0,
                    "lost": 0,
                    "players": {},
                    "battle_sets": {},
                }
            if battle_set not in self.daily_data["pokemons"][pokemon_name]["battle_sets"]:
                self.daily_data["pokemons"][pokemon_name]["battle_sets"][battle_set] = {
                    "win": 0,
                    "lost": 0,
                }
            if name not in self.daily_data["pokemons"][pokemon_name]["players"]:
                self.daily_data["pokemons"][pokemon_name]["players"][name] = {
                    "win": 0,
                    "lost": 0,
                    "battle_sets": {},
                }
            if battle_set not in self.daily_data["pokemons"][pokemon_name]["players"][name]["battle_sets"]:
                self.daily_data["pokemons"][pokemon_name]["players"][name][
                    "battle_sets"
                ][battle_set] = {
                    "win": 0,
                    "lost": 0,
                }
            if AntiqueScoreUtil.check_is_match_win(match, data["player"]["profile"]["uid"]):
                self.daily_data["pokemons"][pokemon_name]["win"] += 1
                self.daily_data["pokemons"][pokemon_name]["battle_sets"][battle_set][
                    "win"
                ] += 1
                self.daily_data["pokemons"][pokemon_name]["players"][name]["win"] += 1
                self.daily_data["pokemons"][pokemon_name]["players"][name][
                    "battle_sets"
                ][battle_set]["win"] += 1
            else:
                self.daily_data["pokemons"][pokemon_name]["lost"] += 1
                self.daily_data["pokemons"][pokemon_name]["battle_sets"][battle_set][
                    "lost"
                ] += 1
                self.daily_data["pokemons"][pokemon_name]["players"][name]["lost"] += 1
                self.daily_data["pokemons"][pokemon_name]["players"][name][
                    "battle_sets"
                ][battle_set]["lost"] += 1
        return

    def get_yesterday_all_players_statics(self, new_mode=False):
        if not new_mode:
            json_file_path_name = (
                    path + str(AntiqueScoreUtil.get_past_x_day_start_epoch(2)) + ".json"
            )
        else:
            json_file_path_name = (
                    path + str(AntiqueScoreUtil.get_past_x_day_start_epoch(0)) + "_new_mode.json"
            )
        if os.path.exists(json_file_path_name):
            print(json_file_path_name + " is generated before")
            return
        self.get_current_top_100_players()
        if len(self.top100_players) < 100:
            # print(len(self.top100_players))
            print("fail to get top 100 players list")
            return
        index = 1
        for name in self.top100_players:
            print(index)
            self.get_yesterday_one_player_static(name, new_mode)
            index += 1
        self.daily_data["match_count"] = len(self.match_ids)
        with open(json_file_path_name, "w") as outfile:
            json.dump(self.daily_data, outfile)
        return

    @staticmethod
    def _get_sort_key_by_win(data):
        keys = list(filter(lambda k: type(data[k]) is dict, data.keys()))
        keys = sorted(
            keys,
            key=lambda k: (
                data[k]["win"],
                data[k]["win"] / (data[k]["win"] + data[k]["lost"]),
            ),
            reverse=True,
        )
        return keys

    @staticmethod
    def _get_player_name(driver, short_name):
        player_data = AntiqueScoreUtil.get_one_player_data(driver, short_name)
        return player_data["player"]["profile"]["playerName"]

    def get_past_x_days_summary(self, start=7, end=0, force_fetch=False, new_mode=False):
        if start - end < 1:
            print("start should smaller than end")
            return

        if not new_mode:
            file_name = (
                    time.strftime(
                        "%Y-%b-%d",
                        time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(start)),
                    )
                    + "_"
                    + time.strftime(
                "%Y-%b-%d",
                time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(1 + end)),
            )
            )
        else:
            file_name = time.strftime(
                "%Y-%b-%d",
                time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(1 + end)),
            ) + "_new_mode"
        json_file_name = path + file_name + ".json"
        if not force_fetch and os.path.exists(json_file_name):
            with open(json_file_name, "r") as readfile:
                data = json.load(readfile)
        else:
            data = {}

        if not data:
            # temp = {}
            players_items = {}
            if not new_mode:
                range_start = 1 + end
                range_end = 1 + start
            else:
                range_start = 1
                range_end = 2
            for d in range(range_start, range_end):
                day_start = AntiqueScoreUtil.get_past_x_day_start_epoch(d)
                if not new_mode:
                    file_path_name = path + str(day_start) + ".json"
                else:
                    file_path_name = path + str(AntiqueScoreUtil.get_past_x_day_start_epoch(0)) + "_new_mode.json"
                if not os.path.exists(file_path_name):
                    # print(file_path_name, d)
                    if d == 0:
                        self.get_yesterday_all_players_statics(new_mode)
                    else:
                        continue
                with open(file_path_name, "r") as readfile:
                    data = AntiqueScoreUtil.merge_2_dicts(data, json.load(readfile))
                data = Top100Players.add_win_rate(data)

                for pokemon in data["pokemons"]:
                    battle_items = {}
                    for player in data["pokemons"][pokemon]["players"]:
                        if player not in players_items:
                            players_items[
                                player
                            ] = Top100Players.get_one_player_item_static(
                                self.driver,
                                player,
                                cache_days=1,
                                has_season_win=False,
                                total_battle_threshold=0,
                                season_battle_threshold=0,
                                season_battle_threshold_soft=0,
                            )
                        if players_items[player]:
                            if pokemon not in players_items[player]:
                                continue
                            data["pokemons"][pokemon]["players"][player][
                                "battle_items"
                            ] = players_items[player][pokemon]["items_string"]
                            if (
                                    data["pokemons"][pokemon]["players"][player][
                                        "battle_items"
                                    ]
                                    not in battle_items
                            ):
                                battle_items[
                                    players_items[player][pokemon]["items_string"]
                                ] = {"players": {}, "win": 0, "lost": 0}
                            battle_items[
                                players_items[player][pokemon]["items_string"]
                            ]["players"][player] = ""
                            battle_items[
                                players_items[player][pokemon]["items_string"]
                            ]["win"] += data["pokemons"][pokemon]["players"][player][
                                "win"
                            ]
                            battle_items[
                                players_items[player][pokemon]["items_string"]
                            ]["lost"] += data["pokemons"][pokemon]["players"][player][
                                "lost"
                            ]
                    _data = data["pokemons"][pokemon]["battle_sets"]
                    keys = list(filter(lambda k: type(_data[k]) is dict, _data.keys()))
                    data["pokemons"][pokemon]["battle_set_win_sort"] = sorted(
                        keys,
                        key=lambda k: (
                            _data[k]["win"],
                            _data[k]["win"] / (_data[k]["win"] + _data[k]["lost"]),
                        ),
                        reverse=True,
                    )
                    data["pokemons"][pokemon][
                        "players_win_sort"
                    ] = Top100Players._get_sort_key_by_win(
                        data["pokemons"][pokemon]["players"]
                    )
                    data["pokemons"][pokemon]["use_rate"] = (
                                                                    data["pokemons"][pokemon]["win"]
                                                                    + data["pokemons"][pokemon]["lost"]
                                                            ) / data["match_count"]
                    data["pokemons"][pokemon]["battle_items"] = battle_items
                    data["pokemons"][pokemon]["battle_items_sort"] = sorted(
                        battle_items.keys(),
                        key=lambda k: (
                            len(battle_items[k]["players"]),
                            battle_items[k]["win"],
                            battle_items[k]["win"]
                            / (battle_items[k]["win"] + battle_items[k]["lost"]),
                        ),
                        reverse=True,
                    )
                    # battle_sets_count
                    for battle_set in data["pokemons"][pokemon]["battle_sets"]:
                        if (
                                type(data["pokemons"][pokemon]["battle_sets"][battle_set])
                                is not dict
                        ):
                            continue
                        names = {}
                        for player in data["pokemons"][pokemon]["players"]:
                            if (
                                    battle_set
                                    in data["pokemons"][pokemon]["players"][player][
                                "battle_sets"
                            ]
                            ):
                                names[player] = ""
                        data["pokemons"][pokemon]["battle_sets"][battle_set][
                            "players"
                        ] = names
                    data["pokemons"][pokemon]["battle_sets"][
                        "battle_sets_win_sort"
                    ] = Top100Players._get_sort_key_by_win(
                        data["pokemons"][pokemon]["battle_sets"]
                    )
                data[
                    "pokemons_use_rate_sort"
                ] = AntiqueScoreUtil.get_sorted_dict_keys_list_by_value(
                    data["pokemons"], "use_rate", True
                )
                data["pokemons_win_rate_sort_over_10_per"] = list(
                    filter(
                        lambda k: data["pokemons"][k]["use_rate"] > 0.1,
                        AntiqueScoreUtil.get_sorted_dict_keys_list_by_value(
                            data["pokemons"], "win_rate", True
                        ),
                    )
                )
            # pprint(temp)
            with open(json_file_name, "w") as outfile:
                json.dump(data, outfile)
            print("dumped json file: " + json_file_name)

        # csv file
        csv_file_name = "./dump_data/" + "top100_players_" + file_name + ".csv"
        _index = 0
        index = 0
        use_rate = 0
        with open(csv_file_name, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["", "一共游戏场数", data["match_count"]])
            for pokemon in data["pokemons_use_rate_sort"]:
                _index += 1
                if data["pokemons"][pokemon]["use_rate"] != use_rate:
                    index = _index
                use_rate = data["pokemons"][pokemon]["use_rate"]
                writer.writerow(
                    [
                        index,
                        pokemon,
                        "\t\t-- 使用人数 --",
                        "- 使用率 -",
                        "- 胜场数 -",
                        "-  胜  率  -",
                    ]
                )
                writer.writerow(
                    [
                        "",
                        "",
                        len(data["pokemons"][pokemon]["players"]),
                        str(round(100 * data["pokemons"][pokemon]["use_rate"], 2))
                        + "%",
                        data["pokemons"][pokemon]["win"],
                        str(round(100 * data["pokemons"][pokemon]["win_rate"], 2))
                        + "%",
                    ]
                )
                writer.writerow(
                    ["", "胜场数最多的三大玩家", "\t\t--- 玩家ID ---", "- 胜场数 -", "-  胜  率  -"]
                )
                count = 0
                for name in data["pokemons"][pokemon]["players_win_sort"]:
                    if count >= 3:
                        break
                    writer.writerow(
                        [
                            "",
                            "",
                            Top100Players._get_player_name(self.driver, name),
                            data["pokemons"][pokemon]["players"][name]["win"],
                            str(
                                round(
                                    100
                                    * data["pokemons"][pokemon]["players"][name][
                                        "win_rate"
                                    ],
                                    2,
                                )
                            )
                            + "%",
                        ]
                    )
                    count += 1
                writer.writerow(
                    [
                        "",
                        "技能对战道具组合",
                        "\t\t--- 组  合 ---",
                        "- 胜场数 -",
                        "- 胜  率 -",
                        "- 使用人数 -",
                    ]
                )
                for battle_set in data["pokemons"][pokemon]["battle_set_win_sort"]:
                    sets = []
                    for skill in battle_set.split("_"):
                        if not skill:
                            continue
                        if len(skill) < 3:
                            skill += "\t"
                        sets.append(skill)
                    writer.writerow(
                        [
                            "",
                            "",
                            "\t".join(sets),
                            # battle_set,
                            data["pokemons"][pokemon]["battle_sets"][battle_set]["win"],
                            str(
                                round(
                                    100
                                    * data["pokemons"][pokemon]["battle_sets"][
                                        battle_set
                                    ]["win_rate"],
                                    2,
                                )
                            )
                            + "%",
                            len(
                                data["pokemons"][pokemon]["battle_sets"][battle_set][
                                    "players"
                                ]
                            ),
                        ]
                    )
                writer.writerow(
                    ["", "持有物组合", "\t\t--- 组  合 ---", "- 胜场数 -", "- 胜  率 -", "- 使用人数 -"]
                )
                for battle_item in data["pokemons"][pokemon]["battle_items_sort"]:
                    if not battle_item:
                        continue
                    items = []
                    for item in battle_item.split("_"):
                        items.append(item)
                    writer.writerow(
                        [
                            "",
                            "",
                            "\t".join(items),
                            data["pokemons"][pokemon]["battle_items"][battle_item][
                                "win"
                            ],
                            str(
                                round(
                                    100
                                    * (
                                            data["pokemons"][pokemon]["battle_items"][
                                                battle_item
                                            ]["win"]
                                            / (
                                                    data["pokemons"][pokemon]["battle_items"][
                                                        battle_item
                                                    ]["win"]
                                                    + data["pokemons"][pokemon]["battle_items"][
                                                        battle_item
                                                    ]["lost"]
                                            )
                                    ),
                                    2,
                                )
                            )
                            + "%",
                            len(
                                data["pokemons"][pokemon]["battle_items"][battle_item][
                                    "players"
                                ]
                            ),
                        ]
                    )
            index = _index + 1
            # for pokemon in AntiqueScoreUtil.pokemon_chinese_name_dict:
            #     if pokemon not in data["pokemons_use_rate_sort"]:
            #         writer.writerow(
            #             [
            #                 index,
            #                 AntiqueScoreUtil.pokemon_chinese_name_dict[pokemon],
            #                 "\t\t-- 使用人数 --",
            #                 "- 使用率 -",
            #                 "- 胜场数 -",
            #                 "-  胜  率  -",
            #             ]
            #         )
            #         writer.writerow(["", "", 0, "0%", "0%", 0])
        print("generated csv file: " + csv_file_name)

        if not new_mode:
            last_week_file_name = (
                    time.strftime(
                        "%Y-%b-%d",
                        time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(7 + 7)),
                    )
                    + "_"
                    + time.strftime(
                "%Y-%b-%d",
                time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(1 + 7)),
            )
            )
        else:
            last_week_file_name = time.strftime(
                "%Y-%b-%d",
                time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(1 + 7)),
            ) + "_new_mode"
        last_week_json_file_name = path + last_week_file_name + ".json"
        if not force_fetch and os.path.exists(last_week_json_file_name):
            with open(last_week_json_file_name, "r") as readfile:
                last_week_data = json.load(readfile)
        else:
            last_week_data = {"pokemons": {}}
        if start - end == 7:
            simple_csv_file_name = (
                    "./dump_data/" + "top100_players_simple_" + file_name + ".csv"
            )
            use_rate = 0
            _index = 0
            with open(simple_csv_file_name, "w", newline="") as csvfile:
                fieldnames = ["排名", "名称", "使用人数", "使用率", "使用率变化", "胜场数", "胜率"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for pokemon in data["pokemons_use_rate_sort"]:
                    _index += 1
                    if data["pokemons"][pokemon]["use_rate"] != use_rate:
                        index = _index
                    use_rate = data["pokemons"][pokemon]["use_rate"]
                    last_week_use_rate = last_week_data["pokemons"].get(pokemon, {"use_rate": use_rate})["use_rate"]
                    writer.writerow(
                        {
                            "排名": index,
                            "名称": pokemon,
                            "使用人数": len(data["pokemons"][pokemon]["players"]),
                            "使用率": str(round(100 * use_rate, 2)) + "%",
                            "使用率变化": str(round(100 * (use_rate - last_week_use_rate), 2)) + "%",
                            "胜场数": data["pokemons"][pokemon]["win"],
                            "胜率": str(
                                round(100 * data["pokemons"][pokemon]["win_rate"], 2)
                            )
                                    + "%",
                        }
                    )
            print("generated csv file: " + simple_csv_file_name)
            ai_voice_txt_file_name = "../" + "voice_text" + ".txt"
            use_rate = 0
            _index = 0
            with open(ai_voice_txt_file_name, "w") as voice_file:
                for pokemon in data["pokemons_use_rate_sort"]:
                    _index += 1
                    if data["pokemons"][pokemon]["use_rate"] != use_rate:
                        index = _index
                    use_rate = data["pokemons"][pokemon]["use_rate"]
                    if index != _index:
                        voice_file.write("并列")
                    voice_file.write(
                        "第{0}名, {1}。\n".format(
                            index, pokemon
                        )
                    )
                    voice_file.write(
                        "使用率{0}%，较前周".format(
                            str(round(100 * use_rate, 2)),
                        )
                    )
                    last_week_use_rate = last_week_data["pokemons"].get(pokemon, {"use_rate": use_rate})["use_rate"]
                    change = round(100 * (use_rate - last_week_use_rate), 2)
                    if change > 0:
                        voice_file.write("上升" + str(change) + "%")
                    elif change < 0:
                        voice_file.write("下降" + str(-change) + "%")
                    else:
                        voice_file.write("并没有变化")
                    voice_file.write("。\n\n")

    @staticmethod
    def add_win_rate(data):
        for key in data:
            if type(data[key]) is dict:
                data[key] = Top100Players.add_win_rate(data[key])
        if "win" in data and "lost" in data:
            data["win_rate"] = data["win"] / (data["win"] + data["lost"])
        return data

    @staticmethod
    def merge_top100_player_2_days_static(data1, data2):
        for pokemon in data1:
            if pokemon == "match_count":
                data1["match_count"] += data2["match_count"]
                continue
            if pokemon in data2:
                data1[pokemon]["win"] += data2[pokemon]["win"]
                data1[pokemon]["lost"] += data2[pokemon]["lost"]

    @staticmethod
    def get_one_player_item_static(
            driver,
            name,
            force_fetch=False,
            cache_days=6,
            total_battle_threshold=60,
            season_battle_threshold=25,
            season_battle_threshold_soft=10,
            has_season_win=True,
            retry=2,
            should_print=True,
    ):
        player_data = {}
        data = AntiqueScoreUtil.get_one_player_data(
            driver, name, force_fetch, cache_days, retry, should_print=should_print
        )
        if not data:
            return {}
        for pokemon in data["player"]["Pokemons"]:
            if (
                    not has_season_win or int(pokemon["statistics"]["SeasonWins"]) > 0
            ) and (
                    (
                            int(pokemon["TotalBattles"]) >= total_battle_threshold
                            and int(pokemon["statistics"]["SeasonBattles"])
                            >= season_battle_threshold_soft
                    )
                    or int(pokemon["statistics"]["SeasonBattles"])
                    >= season_battle_threshold
            ):
                if "Name" not in pokemon:
                    continue
                if pokemon["Name"] == "Mewtwo":
                    pokemon["Name"] = "MewtwoX"
                pokemon_name = AntiqueScoreUtil.unite_data[pokemon["Name"]]["chinese"]
                items_string = AntiqueScoreUtil.get_pokemon_items_string(
                    pokemon["Items"]
                )
                player_data[pokemon_name] = {
                    "items_string": items_string,
                    "win": pokemon["statistics"]["SeasonWins"]
                           + int(
                        0.2
                        * (
                                pokemon["statistics"]["NoOfWins"]
                                - pokemon["statistics"]["SeasonWins"]
                        )
                    ),
                    "total": pokemon["statistics"]["SeasonBattles"]
                             + int(
                        0.2
                        * (
                                pokemon["statistics"]["TotalBattles"]
                                - pokemon["statistics"]["SeasonBattles"]
                        )
                    ),
                }
        return player_data

    def get_all_players_item_statics(
            self, force_fetch=False, cache_days=7, battle_threshold=25
    ):
        self.get_current_top_100_players()
        for name in self.top100_players:
            data = self.get_one_player_item_static(
                self.driver, name, force_fetch, cache_days, battle_threshold
            )
            for pokemon in data.keys():
                if pokemon not in self.items_statics:
                    self.items_statics[pokemon] = {}
                items_string = data[pokemon]["items_string"]
                if data[pokemon]["items_string"] not in self.items_statics[pokemon]:
                    self.items_statics[pokemon][items_string] = {
                        "win": 0,
                        "total": 0,
                        "hide_point": 0,
                    }
                self.items_statics[pokemon][items_string]["win"] += data[pokemon]["win"]
                self.items_statics[pokemon][items_string]["total"] += data[pokemon][
                    "total"
                ]

    def process_data(self):
        new_data = {}
        for pokemon in self.items_statics.keys():
            new_data[pokemon] = {
                "name": pokemon,
                "chinese_name": AntiqueScoreUtil.unite_data[pokemon]["chinese"],
            }
            data = self.items_statics[pokemon]
            # sorted_keys = sorted(data.keys(), key=lambda win: data[win]['win'], reverse=True)
            sorted_keys = AntiqueScoreUtil.get_sorted_dict_keys_list_by_value(
                data, "win", True
            )
            for index in range(min(3, len(sorted_keys))):
                items = []
                for item in sorted_keys[index].split("_"):
                    items.append(AntiqueScoreUtil.item_name_dict[item])
                new_data[pokemon]["item_set_" + str(1 + index)] = {
                    "items": "\t".join(items),
                    "win_count": data[sorted_keys[index]]["win"],
                    "win_rate": str(
                        round(
                            100
                            * data[sorted_keys[index]]["win"]
                            / data[sorted_keys[index]]["total"],
                            2,
                        )
                    )
                                + "%",
                }
        return new_data

    def dump_csv_cn(self):
        try:
            file_name = "./dump_data/items_recommend.csv"
            data = self.process_data()
            with open(file_name, "w", newline="") as csvfile:
                fieldnames = ["名称", "持有物组合", "胜场", "胜率"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for d in data.values():
                    if "item_set_1" in d:
                        writer.writerow(
                            {
                                "名称": d["chinese_name"],
                                "持有物组合": d["item_set_1"]["items"],
                                "胜场": d["item_set_1"]["win_count"],
                                "胜率": d["item_set_1"]["win_rate"],
                            }
                        )
                    if "item_set_2" in d:
                        writer.writerow(
                            {
                                "名称": "",
                                "持有物组合": d["item_set_2"]["items"],
                                "胜场": d["item_set_2"]["win_count"],
                                "胜率": d["item_set_2"]["win_rate"],
                            }
                        )
                    if "item_set_3" in d:
                        writer.writerow(
                            {
                                "名称": "",
                                "持有物组合": d["item_set_3"]["items"],
                                "胜场": d["item_set_3"]["win_count"],
                                "胜率": d["item_set_3"]["win_rate"],
                            }
                        )
            print("items_recommend.csv is generated")
        except Exception as e:
            print("items_recommend.csv failed due to " + e.message)


