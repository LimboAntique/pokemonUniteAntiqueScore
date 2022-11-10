# Blake Xu

import csv
import datetime
import os.path
import json
import AntiqueScoreUtil
import time
from AntiqueDriver import AntiqueDriver

antique_score_ver = 0.2
script_ver = 0.3  # adding English CSV support
# script_ver = 0.2  # change 上周指数变为指数变化，添加妖火红狐翻译, 添加胜率变化
# script_ver = 0.1  # basic code
path = "./dump_data/"
support_languages = ["Chinese", "English"]


class AntiqueScore:
    def __init__(self, driver):
        url = AntiqueScoreUtil.url_base + "meta/"
        self.driver = driver
        self.data = AntiqueScoreUtil.dump_crypto_url(self.driver, url)
        self.gen_pokemon_list()
        # print(self.data)
        self.antique_score_data = {}

    @staticmethod
    def get_support_languages():
        return support_languages

    def get_fetched_data(self):
        return self.data

    def gen_pokemon_list(self):  # compact new data model with exist code
        pokemons = self.data.get('pokemons')
        pokemons_list = {}
        for pokemon in pokemons:
            pokemons_list[str(pokemon['id'])] = pokemon
        self.data["pokemonsList"] = pokemons_list

    def get_week_number(self):
        date_data = list(self.data["metaData"].values())[0]["pickRateByWeek"]
        return int(date_data[-1]["week"].split()[-1]) - 1

    def get_week_date_range(self):
        date = self.gen_week_date_str()
        return (
                datetime.datetime.strptime(date + "-1", "%Y-W%W-%w").strftime("%Y.%m.%d")
                + "-"
                + datetime.datetime.strptime(date + "-0", "%Y-W%W-%w").strftime("%Y.%m.%d")
        )

    def get_pokemon_name(self, pokemon_id):
        return self.data["pokemonsList"][pokemon_id]["name"]

    def get_bias_win_rate(self, pokemon_id):
        return float(self.data["metaData"][pokemon_id]["winRate"]["MirrorAccWinRate"])

    def get_pick_rate(self, pokemon_id):
        pick_rates = self.data["metaData"][pokemon_id]["pickRateByWeek"]
        return float(pick_rates[-1]["pickRate"])

    def get_antique_score(self, pokemon_id):
        # ver 0.2
        win_rate_data = self.data["metaData"][pokemon_id]["winRate"]
        bias_win_rate = float(win_rate_data["MirrorAccWinRate"])
        if bias_win_rate >= 50:
            mirror_fix = 0.21 * (
                    float(win_rate_data["MirrorBiasWinRate"])
                    - float(win_rate_data["TotalWinRate"])
            )
        else:
            mirror_fix = 2.5 / (
                    float(win_rate_data["MirrorBiasWinRate"])
                    - float(win_rate_data["TotalWinRate"])
            )
        # print(str(pokemon_id) + " " + str(bias_win_rate) + " " + str(mirror_fix))
        return 1.2 * (bias_win_rate + (bias_win_rate - 50) * mirror_fix)

    def gen_antique_score_data(self):
        meta_data = self.data["metaData"]
        for pokemon_id in meta_data.keys():
            if int(pokemon_id) >= 1000:
                continue  # special case for different status of same Pokémon, like hoopa
            if self.get_pick_rate(pokemon_id) <= 0:
                continue  # remove unused Pokémon
            pokemon_data = {
                "name": self.get_pokemon_name(pokemon_id),
                "chinese_name": AntiqueScoreUtil.pokemon_chinese_name_dict[
                    self.get_pokemon_name(pokemon_id)
                ],
                "pick_rate": float(self.get_pick_rate(pokemon_id)),
                "bias_win_rate": float(self.get_bias_win_rate(pokemon_id)),
                "antique_score": self.get_antique_score(pokemon_id),
            }
            self.antique_score_data[self.get_pokemon_name(pokemon_id)] = pokemon_data

    def get_sorted_antique_score_data(self, key_field="antique_score"):
        if len(self.antique_score_data) == 0:
            self.gen_antique_score_data()
        self.dump_data()
        data = sorted(
            self.antique_score_data.values(),
            key=lambda score_data: score_data[key_field],
            reverse=True,
        )
        pick_rates = []
        for d in self.antique_score_data.values():
            pick_rates.append(d["pick_rate"])
        pick_rates.sort(reverse=True)
        for i in range(len(data)):
            data[i]["antique_score"] = data[i]["antique_score"]
            data[i]["pick_rate_rank"] = pick_rates.index(data[i]["pick_rate"]) + 1
        return data

    def gen_week_date_str(self):
        year = datetime.date.today().year
        week_num = self.get_week_number()
        if week_num <= 0:
            week_num += 52
            year -= 1
        return str(year) + "-W" + str(week_num)

    def dump_previous_week_data(self):
        year = datetime.date.today().year
        week_num = self.get_week_number() - 1
        if week_num <= 0:
            week_num += 52
            year -= 1
        date = str(year) + "-W" + str(week_num)
        file_name = date + ".json"
        try:
            with open(path + file_name, "r") as readfile:
                data = json.load(readfile)
                return data["antique_score_data"]
        except Exception as e:
            print("dump_previous_week_data due to " + file_name + " " + e.message)
            return {}

    def dump_data(self):
        file_name = self.gen_week_date_str() + ".json"
        dump_data = {
            "raw_data": self.data,
            "antique_score_data": self.antique_score_data,
            "script_version": script_ver,
            "antique_score_ver": antique_score_ver,
        }
        with open(path + file_name, "w") as outfile:
            json.dump(dump_data, outfile)
        return file_name

    def update_pokemon_skill_names(self):
        skill_name_dict = {}
        meta_data = self.data["metaData"]
        for pokemon_id in meta_data:
            for skill in meta_data[pokemon_id]["skills"]:
                skill1_name = "_".join(skill["skill1"]["img"].split("_")[0:4])
                skill2_name = "_".join(skill["skill2"]["img"].split("_")[0:4])
                skill_name_dict[skill1_name] = skill["skill1"]["name"]
                skill_name_dict[skill2_name] = skill["skill2"]["name"]
        # handle special case for hoopa
        skill_name_dict["t_Skill_Hoopa_U_S1"] = "Hyperspace Fury"
        skill_name_dict["t_Skill_Hoopa_U_S2"] = "Psybeam"
        with open(path + "skill_names.json", "w") as outfile:
            json.dump(skill_name_dict, outfile)

    def dump_csv(self, language_code="0", update_skills=True):
        if update_skills:
            self.update_pokemon_skill_names()
        if "0" == language_code:
            return self.dump_csv_cn()
        elif "1" == language_code:
            return self.dump_csv_en()
        else:
            return self.dump_csv_cn() + " " + self.dump_csv_en()

    def dump_csv_cn(self):
        file_name = self.get_week_date_range() + ".csv"
        if os.path.exists(path + file_name):
            print("CSV file: " + file_name + " is generated before")
            return file_name
        last_week_antique_score_data = self.dump_previous_week_data()
        data = self.get_sorted_antique_score_data()
        top100_file = (
                    time.strftime(
                        "%Y-%b-%d",
                        time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(7)),
                    )
                    + "_"
                    + time.strftime(
                        "%Y-%b-%d",
                        time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(1)),
                    )
            )
        last_week_top100_file = (
                    time.strftime(
                        "%Y-%b-%d",
                        time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(14)),
                    )
                    + "_"
                    + time.strftime(
                        "%Y-%b-%d",
                        time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(8)),
                    )
            )
        top100_data = {
            'pokemons_use_rate_sort': [],
            'pokemons': {},
        }
        last_top100_data = {
            'pokemons_use_rate_sort': [],
            'pokemons': {},
        }
        if os.path.exists("./dump_data/top100daily/" + top100_file + ".json"):
            with open("./dump_data/top100daily/" + top100_file + ".json", "r", newline="") as json_file:
                top100_data = json.load(json_file)
        if os.path.exists("./dump_data/top100daily/" + last_week_top100_file + ".json"):
            with open("./dump_data/top100daily/" + last_week_top100_file + ".json", "r") as readfile:
                last_top100_data = json.load(readfile)
        with open(path + file_name, "w", newline="") as csvfile:
            fieldnames = ["排名", "名称", "排位指数", "指数变化", "单边获胜率", "胜率变化", "热度排名", "选出率", '百大选出率', "百大选出排名", "百大选出率变化"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            line = 1
            for d in data:
                writer.writerow(
                    {
                        "排名": line,
                        "名称": d["chinese_name"],
                        "排位指数": round(d["antique_score"], 2),
                        "指数变化": round(
                            d["antique_score"]
                            - last_week_antique_score_data.get(
                                d["name"], {"antique_score": d["antique_score"]}
                            )["antique_score"],
                            2,
                        ),
                        "单边获胜率": str(d["bias_win_rate"]) + "%",
                        "胜率变化": str(
                            round(
                                d["bias_win_rate"]
                                - last_week_antique_score_data.get(
                                    d["name"], {"bias_win_rate": d["bias_win_rate"]}
                                )["bias_win_rate"],
                                2,
                            )
                        ) + "%",
                        "热度排名": d["pick_rate_rank"],
                        "选出率": str(d["pick_rate"]) + '%',
                        "百大选出率": str(round(
                            100 * top100_data['pokemons'][d["name"]]["use_rate"],
                            2,
                        )) + "%",
                        "百大选出排名": str(top100_data['pokemons_use_rate_sort'].index(d["name"]) + 1),
                        "百大选出率变化": str(
                                round(
                                    100
                                    * (top100_data['pokemons'][d["name"]]["use_rate"] -
                                        last_top100_data['pokemons'][d["name"]]["use_rate"]),
                                    2,
                                )
                            ) + "%",
                    }
                )
                line += 1
        print("new CSV file: " + file_name + " is generated")
        ai_voice_txt_file_name = "../" + "voice_text" + ".txt"
        with open(ai_voice_txt_file_name, "w") as voice_file:
            voice_file.write("大家好，这里是古董的AI语音助手。\n")
            line = 1
            for d in data:
                voice_file.write("第{0}名，{1}。\n".format(line, d["chinese_name"]))
                change = round(
                    d["antique_score"]
                    - last_week_antique_score_data.get(
                        d["name"], {"antique_score": d["antique_score"]}
                    )["antique_score"],
                    2,
                )
                if abs(change) > 4:
                    if change < 0:
                        voice_file.write("排位指数下降{0}分。\n".format(-change))
                    else:
                        voice_file.write("排位指数上升{0}分。\n".format(change))
                line += 1
        return file_name

    def dump_csv_en(self):
        file_name = self.get_week_date_range() + "_en.csv"
        if os.path.exists(path + file_name):
            print("CSV file: " + file_name + " is generated before")
            return file_name
        last_week_antique_score_data = self.dump_previous_week_data()
        data = self.get_sorted_antique_score_data()
        with open(path + file_name, "w", newline="") as csvfile:
            fieldnames = [
                "Rank",
                "Name",
                "Rank Index",
                "Index Change",
                "Bias Win Rate",
                "Win Rate Change",
                "Pick Rate Rank",
                "Pick Rate",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            line = 1
            for d in data:
                writer.writerow(
                    {
                        "Rank": line,
                        "Name": d["name"],
                        "Rank Index": round(d["antique_score"], 2),
                        "Index Change": round(
                            d["antique_score"]
                            - last_week_antique_score_data.get(
                                d["name"], {"antique_score": d["antique_score"]}
                            )["antique_score"],
                            2,
                        ),
                        "Bias Win Rate": str(d["bias_win_rate"]) + "%",
                        "Win Rate Change": str(
                            round(
                                d["bias_win_rate"]
                                - last_week_antique_score_data.get(
                                    d["name"], {"bias_win_rate": d["bias_win_rate"]}
                                )["bias_win_rate"],
                                2,
                            )
                        )
                                           + "%",
                        "Pick Rate Rank": d["pick_rate_rank"],
                        "Pick Rate": str(d["pick_rate"]) + '%',
                    }
                )
                line += 1
        print("new CSV file: " + file_name + " is generated")
        return file_name
