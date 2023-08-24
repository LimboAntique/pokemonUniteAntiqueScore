import base64
import hashlib
import certifi
import json
from pymongo import MongoClient
import os.path
import time
import urllib
import re

import requests
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.number import bytes_to_long
from bs4 import BeautifulSoup
# from halo import Halo

mongo_client = MongoClient("mongodb+srv://BlakeXu:nljd1SBaKAIVfDH9@antique.uq5zmrd.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())
mongo_db = mongo_client.get_database("underwear_bot")
mongo_col = mongo_db.get_collection("unite_data")
unite_data = {}
for load in mongo_col.find({"unite_api_id": {'$exists': 1}}):
    unite_data[load["unite_api_id"]] = load
    unite_data[load["english"]] = load

player_dump_data_path = "../player_dump_data/"

url_base = "https://uniteapi.dev/"
header = {"User-Agent":
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
          "cookie":'''_pbjs_userid_consent_data=3524755945110770; cnx_userId=bb59f21ed2074949ba224fd66c89c34c; _pubcid=96403697-15f1-4eff-895f-839506911698; _cc_id=5b63e4753ea2ac5d2b228e89d284b1ad; CookieConsent={stamp:'FzinIX/o72k1/r3jCPddUZijVyMJHusM7sQPef39uS1yvfWxZAZWNQ==',necessary:true,preferences:true,statistics:true,marketing:true,ver:1,utc:1668311484789,region:'us-06'}; __gads=ID=9ed613288bf8047a-22de14ea4fb4001b:T=1668208927:S=ALNI_Mb-k_EhOfOua2iOykVUJDYYG0HDZA; _lr_env_src_ats=false; FCNEC=[["AKsRol9KE3JpvhnVQU39Sv6czwWc9PldLgido92i6WOa-mrqAQvefRq_n1bX7VB9SxX6o8d72RdHnnRrM2AF3Bz9SAQT8GBhfQsf9qNh_A-miw6eetwnU9yS0Nc36pNj7r7PF-JpLKhTe44asF1vXw3u0F_NreBTcA=="],null,[]]; _au_1d=AU1D-0100-001677271293-D0W93QRG-NFRN; pbjs-unifiedid={"TDID":"57796944-0e13-4ed3-860d-0e201355dd0e","TDID_LOOKUP":"TRUE","TDID_CREATED_AT":"2023-01-27T21:25:18"}; ntv_as_us_privacy=1YNY; panoramaIdType=panoIndiv; panoramaId_expiry=1679422325681; panoramaId=2ff6a3a5960af3d18c864e2176ac16d53938a9954d0558f049ba3fdb00563a57; ezosuibasgeneris-1=48841980-4026-4fd6-7f0d-3d4cf2dd6585; ezoref_373621=uniteapi.dev; ezoab_373621=mod1-c; _au_last_seen_pixels=eyJhcG4iOjE2NzkxODMxNTUsInR0ZCI6MTY3OTE4MzE1NSwicHViIjoxNjc5MTgzMTU1LCJydWIiOjE2NzkxODMxNTUsInRhcGFkIjoxNjc5MTgzMTU1LCJhZHgiOjE2NzkxODMxNTUsImdvbyI6MTY3OTE4MzE1NSwibWVkaWFtYXRoIjoxNjc5MDI2MTYxLCJwcG50IjoxNjc5MDI2MTYxLCJpbXByIjoxNjc5MTgzMTU1LCJhZG8iOjE2NzkxODMxNTUsIm9wZW54IjoxNjc5MDI2MTYxLCJzb24iOjE2NzkxODMxNTUsInRhYm9vbGEiOjE2NzkwMjYxNjEsInVucnVseSI6MTY3OTAyNjE2MSwiYmVlcyI6MTY3OTAyNTY1Miwic21hcnQiOjE2NzkwMjYxNjF9; _gid=GA1.2.1419690244.1679183156; __gpi=UID=000008a54d75306f:T=1668208927:RT=1679183155:S=ALNI_MbpIZakKL6RBmZPqQUExKtDCAp88A; _ga=GA1.1.1146358985.1668208928; ezepvv=0; _ga_YJKKTSBB0Y=GS1.1.1679183155.145.1.1679184746.0.0.0; cf_clearance=sKHRTD3CqV7fy4W5VMkjyTsGI7zNx.8FGest12goIgA-1679185306-0-160; __Host-next-auth.csrf-token=21ce132a9b1b3c45600faed83a86110a462471a23abf19d2001e491bbf8f51e2|a0e7ff1d0e74632b628c409745b50f655862c2d4b0e904fa9d9b6e081bdad140; __Secure-next-auth.callback-url=https://uniteapi.dev; ezoadgid_373621=-1; ezovid_373621=1263194475; lp_373621=https://uniteapi.dev/; ezovuuid_373621=13c10cbe-a437-4cb4-60eb-e7379a685a8d; ezux_ifep_373621=true; ezovuuidtime_373621=1679186792; active_template::373621=pub_site.1679186792; ezopvc_373621=4; ezux_lpl_373621=1679186792300|82caa147-8f27-4ca1-6d81-d175f45049f0|true; cto_bundle=qZEze18yZHcwY2NlV0IlMkJhTm9UTHMlMkZOMU41SEx0Y0pHbnBDd29MM290JTJGaUMxM0VERlRSNnd4c1hVaUEySzdNZ0F1V1ptWTU4SjQ5UmJwTkJGMyUyQnUyM0dsT2hCZG5xVzJEQmgxTHpXMFR5UnRpZkRUbjklMkZDWEh3ckxFT0hJOXpoWEFPYm9qVnc5bWxGMTBPaGFEV1VWJTJGN2ZxWlE5M0ZwM0FyQ29GcXZTTWR6S1BpenVzb2FWUmZZR2JoTjloQkFaSktCY0FuSHdsNGxoMXhWbzZNTEI4YTZiU1RBJTNEJTNE; cto_bidid=qZEze18yZHcwY2NlV0IlMkJhTm9UTHMlMkZOMU41SEx0Y0pHbnBDd29MM290JTJGaUMxM0VERlRSNnd4c1hVaUEySzdNZ0F1V1ptWTU4SjQ5UmJwTkJGMyUyQnUyM0dsT2hCZG5xVzJEQmgxTHpXMFR5UnRpZkRUbjklMkZDWEh3ckxFT0hJOXpoWEFPYm9qVnc5bWxGMTBPaGFEV1VWJTJGN2ZxWlE5M0ZwM0FyQ29GcXZTTWR6S1BpenVzb2FWUmZZR2JoTjloQkFaSktCY0FuSHdsNGxoMXhWbzZNTEI4YTZiU1RBJTNEJTNE; ezux_et_373621=257; ezux_tos_373621=1942''',
          "Content-Type":"application/x-www-form-urlencoded",
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
        # with open('temp.txt', "w") as filea:
        #     filea.write(str(encoded_data))
        return aes256_decode(encoded_data)
    return {}


def get_one_player_data(
        driver, name:str, force_fetch=False, cache_days=6, retry=1, should_print=True
):
    create_player_dump_data_path_if_needed()
    name_special_match = re.match(r'^<\w+?>.*</\w+?>$', name, re.I)
    clean_name = name
    if name_special_match:
        clean_name = clean_name[3:-4]
    file_path_name = player_dump_data_path + str(clean_name) + ".json"
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
                # with Halo(text="dumping data for " + clean_name, spinner="dots"):
                url = url_base + "p/" + urllib.parse.quote(name, safe='<>')
                player_data = dump_crypto_url(driver, url)
                player_data["dump_time"] = get_past_x_day_start_epoch(0)
                my_print("using new data for " + clean_name, should_print)
            else:
                my_print("using old data for " + clean_name, should_print)
            if "player" not in player_data:
                if times >= retry:
                    my_print("fail dump data for " + clean_name, should_print)
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
        file_path_name = player_dump_data_path + str(clean_name) + ".json"
        try:
            with open(file_path_name, "w") as outfile:
                json.dump(player_data, outfile)
        except:
            print("unable to dump {0}".format(str(clean_name)))
        return player_data


def get_past_x_day_start_epoch(x=0):
    return int(time.time()) - int(time.time()) % 86400 - x * 86400


def aes256_decode(encoded_data):
    ken_len = 21
    # print("111", encoded_data[-ken_len:], encoded_data[-ken_len:].encode("utf-8"))
    key = hashlib.sha256(encoded_data[-ken_len:].encode("utf-8")).digest()
    # print("key", key)
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
    skill1_load = unite_data.get(skill1_id, None)
    skill2_load = unite_data.get(skill2_id, None)
    if not skill1_load or not skill2_load:
        print("Error: unable to get name for " + skill1_id + " or " + skill2_id)
        return None
    return [
        skill1_load["chinese"],
        skill2_load["chinese"],
        unite_data[target_data["usedBattleItem"]]["chinese"]
    ]


def get_pokemon_items_string(items):
    if len(items) < 3:
        return ""
    res = []
    for item in items:
        item_name = unite_data[item["Image"]]["chinese"]
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
