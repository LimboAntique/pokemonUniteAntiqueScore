import base64
import hashlib
import certifi
import json
from pymongo import MongoClient
import os.path
import time
import urllib

import requests
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.number import bytes_to_long
from bs4 import BeautifulSoup
from halo import Halo

mongo_client = MongoClient("mongodb+srv://BlakeXu:nljd1SBaKAIVfDH9@antique.uq5zmrd.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())
mongo_db = mongo_client.get_database["underwear_bot"]
mongo_col = mongo_db.get_collection("unite_data")

player_dump_data_path = "../player_dump_data/"

item_name_dict = {
    "Eos2": "救援屏障",
    "FocusBand": "气势头带",
    "MuscleBand": "力量头带",
    "AssaultVest": "突击背心",
    "ChoiceSpecs": "讲究眼镜",
    "Eos1": "能量增幅器",
    "WiseGlasses": "博识眼镜",
    "Eos3": "得分护盾",
    "Eos5": "猛攻哑铃",
    "RazorClaw": "锐利之爪",
    "ScopeLens": "焦点镜",
    "WeaknessPolicy": "弱点保险",
    "ExpShare": "学习装置",
    "Eos6": "进击眼镜",
    "ShellBell": "贝壳之铃",
    "FloatStone": "轻石" + "\t",
    "Eos4": "亿奥斯饼干",
    "RockyHelmet": "凸凸头盔",
    "Leftovers": "吃剩的东西",
    "ComboScarf": "连打围巾",
    "CureCrown": "治愈王冠",
}

url_base = "https://uniteapi.dev/"
header = {"User-Agent":
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
          }


# def load_header():
#     res = copy.deepcopy(header)
#     with open('cookie.txt', 'r') as f:
#         res['cookie'] = f.readlines()[0]
#     return res


def my_print(string, allow=True):
    if allow:
        print(string)


def create_player_dump_data_path_if_needed():
    if not os.path.exists(player_dump_data_path):
        os.mkdir(player_dump_data_path)


def dump_url(driver, url):
    if driver is not None:
        response = driver.get(url)
    else:
        response = requests.get(url)
    if response:
        return BeautifulSoup(response.text, "html.parser")
    return None


def dump_crypto_url(driver, url) -> dict:
    response_soup = dump_url(driver, url)
    if response_soup:
        encoded_data = json.loads(response_soup.body.find("script", {"id": "__NEXT_DATA__"}).string)["props"][
            "pageProps"
        ]["a"]
        with open('temp.txt', "w") as filea:
            filea.write(str(encoded_data))
        return aes256_decode(encoded_data)
    return {}


def get_one_player_data(
        driver, name, force_fetch=False, cache_days=6, retry=1, should_print=True
):
    create_player_dump_data_path_if_needed()
    file_path_name = player_dump_data_path + str(name) + ".json"
    player_data = {}
    current_time = time.time()
    for times in range(retry + 1):
        try:
            if (not force_fetch) and os.path.exists(file_path_name):
                with open(file_path_name, "r") as readfile:
                    player_data = json.load(readfile)
            if (
                    force_fetch
                    or int((current_time - player_data.get("dump_time", 0)) / 86400)
                    >= cache_days
            ):
                # re-dump data if old data older than 7 days
                with Halo(text="dumping data for " + name, spinner="dots"):
                    url = url_base + "p/" + urllib.parse.quote(name)
                    player_data = dump_crypto_url(driver, url)
                    player_data["dump_time"] = get_past_x_day_start_epoch(0)
            else:
                my_print("using old data for " + name, should_print)
            if "player" not in player_data:
                if times >= retry:
                    my_print("fail dump data for " + name, should_print)
                    return {}
                else:
                    player_data["dump_time"] = 0
                    time.sleep(10)
                    continue
            file_path_name = player_dump_data_path + player_data["player"]["profile"]["userShort"] + ".json"
        except:
            player_data["dump_time"] = 0
            force_fetch = True
            time.sleep(5)
            continue

        with open(file_path_name, "w") as outfile:
            json.dump(player_data, outfile)
        return player_data


def get_past_x_day_start_epoch(x=0):
    return int(time.time()) - int(time.time()) % 86400 - x * 86400


def aes256_decode(encoded_data):
    ken_len = 21
    key = hashlib.sha256(encoded_data[-ken_len:].encode("utf-8")).digest()
    b64decoded_data = base64.b64decode(encoded_data[:-ken_len])
    cipher = AES.new(
        key,
        AES.MODE_CTR,
        counter=Counter.new(128, initial_value=bytes_to_long(b64decoded_data[0:16])),
    )
    decoded_data = cipher.decrypt(b64decoded_data[16:]).decode("utf-8")
    return json.loads(decoded_data)


# match is match data
def check_is_match_win(match, player_uid):
    winners = match["Winners"]["data"]
    for winner in winners:
        if winner["PlayerUid"] == player_uid:
            return True
    return False


# return a list of [skill1_name, skill2_name, battle_item_name]
def get_match_battle_set(match, player_uid):
    target_data = {}
    for player in match["Winners"]["data"]:
        if target_data:
            break
        if player["PlayerUid"] == player_uid:
            target_data = player
    for player in match["Losers"]["data"]:
        if target_data:
            break
        if player["PlayerUid"] == player_uid:
            target_data = player

    skill1_id = "_".join(target_data["Skill1"].split("_")[0:4])
    skill2_id = "_".join(target_data["Skill2"].split("_")[0:4])
    skill1_load = mongo_col.find_one({"unite_api_id": skill1_id})
    skill2_load = mongo_col.find_one({"unite_api_id": skill2_id})
    if not skill1_load or not skill2_load:
        print("Error: unable to get name for " + skill1_id + " or " + skill2_id)
        return None
    return [
        skill1_load["english"],
        skill2_load["english"],
        target_data["usedBattleItem"].split("_")[-1],
    ]


def get_pokemon_items_string(items):
    if len(items) < 3:
        return ""
    res = []
    for item in items:
        item_name = item["Image"].split("_")[-1]
        res.append(item_name)
    return "_".join(sorted(res))


def merge_2_dicts(dict1, dict2):
    for key1 in dict1:
        if key1 in dict2:
            if type(dict1[key1]) is dict:
                dict1[key1] = merge_2_dicts(dict1[key1], dict2[key1])
            else:
                dict1[key1] += dict2[key1]
    for key2 in dict2:
        if key2 not in dict1:
            dict1[key2] = dict2[key2]
    return dict1


def get_sorted_dict_keys_list_by_value(
        data: dict, value_key: str, reverse: bool = False
) -> list:
    return sorted(
        list(filter(lambda k: type(data[k]) is dict, data.keys())),
        key=lambda k: data[k][value_key],
        reverse=reverse,
    )
