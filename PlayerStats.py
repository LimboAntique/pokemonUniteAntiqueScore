# Blake Xu

import AntiqueScoreUtil
import time
import traceback
from prettytable import PrettyTable, DOUBLE_BORDER
from copy import deepcopy
from pprint import pprint

user_detail_data = {
    'overall': {
        'win': 0,
        'lost': 0,
    },
    1: {
        'win': 0,
        'lost': 0,
    },
    2: {
        'win': 0,
        'lost': 0,
    },
    3: {
        'win': 0,
        'lost': 0,
    },
    5: {
        'win': 0,
        'lost': 0,
    },
}


def getOnePlayerDetailsRow(data):
    if data['win'] + data['lost'] == 0:
        return '--'
    return str(data['win']) + ' - ' + str(data['lost']) + ' (' + str(
        round(100 * data['win'] / (data['win'] + data['lost']), 2)
    ) + '%)'


def getOnePlayerDetails(name, games_count, driver):
    data = AntiqueScoreUtil.get_one_player_data(driver, name, True)
    unit_id_to_pokemon_name = AntiqueScoreUtil.unitID_to_pokemon_name_dict
    matches = sorted(
        data["player"]["MatchResults"],
        key=lambda _match: int(_match["GameStartTime"]),
        reverse=True,
    )
    matches = list(
        filter(
            lambda _match: _match["MapSubMode"] == 2,
            matches,
        )
    )[:games_count]
    results = {
        'all': deepcopy(user_detail_data),
        'pokemons': {},
        'friends': {},
    }
    current_rank = data["player"]["profile"]["currentRank"]
    if current_rank == "Master":
        current_rank += ": " + str(data["player"]["profile"]["masterPoints"])
    for match in matches:
        pokemon_name = unit_id_to_pokemon_name[
            match["CurrentPlayer"]["HeroID"]
        ]
        if pokemon_name not in results['pokemons']:
            results['pokemons'][pokemon_name] = deepcopy(user_detail_data)
        is_win = False
        for winner in match["Winners"]["data"]:
            if winner["PlayerName"] == match["CurrentPlayer"]["PlayerName"]:
                team_flag = int(winner.get("TeamFlag", -1))
                is_win = True
        if not is_win:
            for loser in match["Losers"]["data"]:
                if loser["PlayerName"] == match["CurrentPlayer"]["PlayerName"]:
                    team_flag = int(loser.get("TeamFlag", -1))
        friends = []
        if team_flag > 0:
            if is_win:
                for winner in match["Winners"]["data"]:
                    if winner["PlayerName"] != match["CurrentPlayer"]["PlayerName"] \
                            and team_flag == int(winner.get("TeamFlag", -2)):
                        friends.append(winner["PlayerName"])
            else:
                for loser in match["Losers"]["data"]:
                    if loser["PlayerName"] != match["CurrentPlayer"]["PlayerName"] \
                            and team_flag == int(loser.get("TeamFlag", -2)):
                        friends.append(loser["PlayerName"])
        queue = 1 + len(friends)
        key = 'lost'
        if is_win:
            key = 'win'
        results['all']['overall'][key] += 1
        results['all'][queue][key] += 1
        results['pokemons'][pokemon_name]['overall'][key] += 1
        results['pokemons'][pokemon_name][queue][key] += 1
        for friend in friends:
            if friend not in results['friends']:
                results['friends'][friend] = deepcopy(user_detail_data)
            results['friends'][friend]['overall'][key] += 1
            results['friends'][friend][queue][key] += 1

    print("Check last " + str(len(matches)) + " rank games result for " + data["player"]["profile"]["playerName"] + " (" +
          current_rank + ") ")
    table = PrettyTable()
    table.set_style(DOUBLE_BORDER)
    table.align = "l"
    table.field_names = [
        "",
        "总和",
        "单排",
        "双排",
        "三排",
        "五排",
    ]
    table.add_row([
        '玩家："' + data["player"]["profile"]["playerName"] + '"',
        getOnePlayerDetailsRow(results['all']['overall']),
        getOnePlayerDetailsRow(results['all'][1]),
        getOnePlayerDetailsRow(results['all'][2]),
        getOnePlayerDetailsRow(results['all'][3]),
        getOnePlayerDetailsRow(results['all'][5])
    ])
    for pokemon_name in results['pokemons']:
        table.add_row([
            AntiqueScoreUtil.pokemon_chinese_name_dict[pokemon_name],
            getOnePlayerDetailsRow(results['pokemons'][pokemon_name]['overall']),
            getOnePlayerDetailsRow(results['pokemons'][pokemon_name][1]),
            getOnePlayerDetailsRow(results['pokemons'][pokemon_name][2]),
            getOnePlayerDetailsRow(results['pokemons'][pokemon_name][3]),
            getOnePlayerDetailsRow(results['pokemons'][pokemon_name][5])
        ])
    for friend in results['friends']:
        table.add_row([
            'with "' + friend + '"',
            getOnePlayerDetailsRow(results['friends'][friend]['overall']),
            getOnePlayerDetailsRow(results['friends'][friend][1]),
            getOnePlayerDetailsRow(results['friends'][friend][2]),
            getOnePlayerDetailsRow(results['friends'][friend][3]),
            getOnePlayerDetailsRow(results['friends'][friend][5])
        ])
    print(table.get_string())


class PlayerStats:
    def __init__(
            self,
            player_name,
            win_matches_count,
            lost_matches_count,
            last_played_time,
            last_played_pokemon,
            current_rank,
            season_winrate,
    ):
        self.player_name = player_name
        self.win_matches_count = win_matches_count
        self.lost_matches_count = lost_matches_count
        self.last_played_time = last_played_time
        self.last_played_pokemon = last_played_pokemon
        self.current_rank = current_rank
        self.season_winrate = season_winrate

    def pretty_table_row(self):
        win = self.win_matches_count
        lost = self.lost_matches_count
        return [
            self.player_name,
            win,
            lost,
            (str(round(100 * win / (win + lost), 2)) + "%")
            if win + lost > 0
            else "0.0%",
            time.strftime("%m-%d %H:%M", time.localtime(self.last_played_time))
            if self.last_played_time > 0
            else "No games",
            AntiqueScoreUtil.pokemon_chinese_name_dict[self.last_played_pokemon]
            if len(self.last_played_pokemon) > 0
            else "No games",
            self.current_rank,
            self.season_winrate,
        ]


def getPlayerStatistics(antique_driver, name, track_back_days=0):
    try:
        current_rank = ""
        today_start = AntiqueScoreUtil.get_past_x_day_start_epoch(track_back_days)
        data = AntiqueScoreUtil.get_one_player_data(antique_driver, name, True)
        unit_id_to_pokemon_name = AntiqueScoreUtil.unitID_to_pokemon_name_dict
        matches = sorted(
            data["player"]["MatchResults"],
            key=lambda _match: int(_match["GameStartTime"]),
            reverse=True,
        )
        user_name = data["player"]["profile"]["playerName"]
        today_rank_matches = list(
            filter(
                lambda _match: (
                        today_start <= int(_match["GameStartTime"])
                        and _match["MapSubMode"] == 2
                ),
                matches,
            )
        )
        current_rank = data["player"]["profile"]["currentRank"]
        season_winrate = getCurrentSeasonWinRate(data)
        if current_rank == "Master":
            current_rank += ": " + str(data["player"]["profile"]["masterPoints"])
        if not today_rank_matches:
            return PlayerStats(user_name, 0, 0, 0, "", current_rank, season_winrate)
        last_played_pokemon = unit_id_to_pokemon_name[
            today_rank_matches[0]["CurrentPlayer"]["HeroID"]
        ]
        last_played_time = int(today_rank_matches[0]["GameStartTime"])
        win = 0
        lost = 0
        for match in today_rank_matches:
            if AntiqueScoreUtil.check_is_match_win(match):
                win += 1
            else:
                lost += 1
        return PlayerStats(
            user_name,
            win,
            lost,
            last_played_time,
            last_played_pokemon,
            current_rank,
            season_winrate,
        )
    except Exception as e:
        print(e)
        traceback.print_exc()
        print("Fail to get player status: " + name)
        return PlayerStats(user_name, 0, 0, 0, "", current_rank, "N/A")


def getCurrentSeasonWinRate(player_data):
    pokemons = player_data["player"]["Pokemons"]
    win = 0
    lost = 0
    for pokemon in pokemons:
        win += pokemon["statistics"]["SeasonWins"]
        lost += pokemon["statistics"]["SeasonLoses"]
    if win + lost <= 0:
        return "N/A"
    return str(round(100 * (win / (win + lost)), 2)) + "%"


def getPlayersStatistics(antique_driver, names, track_back_days=0, compact=False, ):
    field_names = [
        "Player Name",
        "Win",
        "Lost",
        "Win Rate",
        "Last Played",
        "Last Pokemon",
        "Rank",
        "Season Win Rate",
    ]
    if compact:
        for name in names:
            table = PrettyTable()
            table.set_style(DOUBLE_BORDER)
            table.align = "l"
            table.field_names = [field_names[0] + ": " + name]
            row_names = field_names[1:]
            player_stat = getPlayerStatistics(antique_driver, name, track_back_days)
            for j in range(len(row_names)):
                row = [row_names[j] + ": " + str(player_stat.pretty_table_row()[j + 1])]
                table.add_row(row)
            print(table.get_string())
            print()
    else:
        all_player_stats = []
        for name in names:
            all_player_stats.append(getPlayerStatistics(antique_driver, name, track_back_days))
        table = PrettyTable()
        table.set_style(DOUBLE_BORDER)
        table.align = "l"
        table.field_names = field_names
        all_player_stats = sorted(
            all_player_stats,
            key=lambda data: sortPlayerDataFormula(data),
            reverse=True)
        for player_stats in all_player_stats:
            table.add_row(player_stats.pretty_table_row())
        print(
            table.get_string()
        )


def sortPlayerDataFormula(data):
    if data.win_matches_count + data.lost_matches_count == 0:
        res = -100000000
    else:
        res = 100000000
    rank_score = data.current_rank.split()[-1]
    if not rank_score or not rank_score.isdigit():
        rank_score = -1
    else:
        rank_score = int(rank_score)
    if "Master" in data.current_rank:
        res += rank_score
    if "Ultra:" in data.current_rank:
        res += rank_score
    if "Veteran:" in data.current_rank:
        res += 20 - rank_score
    res += 1010000 * data.win_matches_count - 1000000 * data.lost_matches_count
    return res
