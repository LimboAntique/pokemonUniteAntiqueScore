# Blake Xu

import csv
import logging
import time
import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
import AntiqueScoreUtil
from AntiqueDriver import AntiqueDriver

# 配置日志
logger = logging.getLogger(__name__)

# 常量配置
DATA_DIR = Path("./dump_data")
DAILY_DIR = DATA_DIR / "top100daily"
VOICE_TEXT_PATH = Path("../voice_text.txt")

# 阈值常量
MIN_USE_RATE_THRESHOLD = 0.1  # 最小使用率阈值（10%）
HISTORICAL_WEIGHT = 0.2  # 历史数据权重
TOP_PLAYERS_DISPLAY_COUNT = 3  # 显示前N名玩家
MAX_PLAYERS_COUNT = 100  # Top 100 玩家数量


class Top100Players:
    """Top 100 玩家数据统计和分析类"""
    
    def __init__(self, driver: Optional[AntiqueDriver]) -> None:
        """
        初始化 Top100Players
        
        Args:
            driver: AntiqueDriver 实例，用于绕过 Cloudflare 限制
        """
        self.driver = driver
        self.match_ids: Dict[str, str] = {}
        self.daily_data: Dict[str, Any] = {"pokemons": {}}
        self.top100_players: List[str] = []

    def get_current_top_100_players(self) -> None:
        """获取当前 Top 100 玩家列表"""
        logger.info("正在获取当前 Top 100 玩家列表...")
        url = AntiqueScoreUtil.url_base + "rankings/"
        
        try:
            response = AntiqueScoreUtil.dump_crypto_url(self.driver, url)
            if not response:
                logger.error("获取排行榜失败：响应为空")
                return
            
            logger.debug(f"响应数据: {response}")
            user_data = response.get('top100', [])
            
            if not user_data:
                logger.warning("Top 100 列表为空")
                return
            
            for count, player in enumerate(user_data, start=1):
                self.top100_players.append(player['Uid'])
                logger.debug(f"#{count}: {player['RoleName']}")
                
                if count >= MAX_PLAYERS_COUNT:
                    break
            
            logger.info(f"成功获取 {len(self.top100_players)} 名玩家")
            
        except KeyError as e:
            logger.error(f"解析玩家数据失败，缺少键: {e}")
        except Exception as e:
            logger.error(f"获取 Top 100 玩家列表时发生错误: {e}")

    def get_yesterday_one_player_static(self, name: str, new_mode: bool = False) -> Dict:
        """
        获取单个玩家昨日的统计数据
        
        Args:
            name: 玩家 UID
            new_mode: 是否使用新模式（默认 False）
            
        Returns:
            玩家统计数据字典
        """
        data = AntiqueScoreUtil.get_one_player_data(self.driver, name, cache_days=1)
        if not data or "player" not in data:
            logger.warning(f"无法获取玩家 {name} 的数据")
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

    def get_yesterday_all_players_statics(self, new_mode: bool = False) -> None:
        """
        获取所有 Top 100 玩家昨日的统计数据
        
        Args:
            new_mode: 是否使用新模式（默认 False）
        """
        # 构建文件路径
        if not new_mode:
            json_file_name = f"{AntiqueScoreUtil.get_past_x_day_start_epoch(2)}.json"
        else:
            json_file_name = f"{AntiqueScoreUtil.get_past_x_day_start_epoch(0)}_new_mode.json"
        
        json_file_path = DAILY_DIR / json_file_name
        
        # 检查文件是否已存在
        if json_file_path.exists():
            logger.info(f"{json_file_path} 已存在，跳过生成")
            return
        
        # 获取 Top 100 玩家列表
        self.get_current_top_100_players()
        if len(self.top100_players) < MAX_PLAYERS_COUNT:
            logger.error(f"获取玩家列表失败，只获取到 {len(self.top100_players)} 名玩家")
            return
        
        # 遍历所有玩家
        logger.info(f"开始处理 {len(self.top100_players)} 名玩家的数据...")
        for index, name in enumerate(self.top100_players, start=1):
            logger.info(f"处理玩家 {index}/{len(self.top100_players)}: {name}")
            self.get_yesterday_one_player_static(name, new_mode)
        
        # 保存数据
        self.daily_data["match_count"] = len(self.match_ids)
        
        try:
            # 确保目录存在
            DAILY_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(json_file_path, "w", encoding="utf-8") as outfile:
                json.dump(self.daily_data, outfile, ensure_ascii=False, indent=2)
            logger.info(f"成功保存数据到 {json_file_path}")
        except IOError as e:
            logger.error(f"保存文件失败: {e}")
            raise

    @staticmethod
    def _get_sort_key_by_win(data: Dict[str, Any]) -> List[str]:
        """
        按胜场数和胜率排序
        
        Args:
            data: 包含 win 和 lost 字段的数据字典
            
        Returns:
            排序后的键列表
        """
        keys = [k for k in data.keys() if isinstance(data[k], dict)]
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
    def _get_player_name(driver: Optional[AntiqueDriver], short_name: str) -> str:
        """
        获取玩家全名
        
        Args:
            driver: AntiqueDriver 实例
            short_name: 玩家短名称
            
        Returns:
            玩家全名，如果获取失败则返回短名称
        """
        player_data = AntiqueScoreUtil.get_one_player_data(driver, short_name)
        if not player_data or "player" not in player_data:
            return short_name
        return player_data["player"]["profile"]["playerName"]

    def get_past_x_days_summary(
        self, 
        start: int = 7, 
        end: int = 0, 
        force_fetch: bool = False, 
        new_mode: bool = False
    ) -> None:
        """
        获取过去 X 天的汇总统计数据
        
        Args:
            start: 开始天数（默认 7）
            end: 结束天数（默认 0）
            force_fetch: 是否强制重新获取（默认 False）
            new_mode: 是否使用新模式（默认 False）
        """
        if start - end < 1:
            logger.error(f"参数错误：start ({start}) 应该大于 end ({end})")
            return
        
        logger.info(f"开始生成过去 {start-end} 天的统计数据...")

        # 构建文件名
        file_name = self._build_file_name(start, end, new_mode)
        json_file_path = DAILY_DIR / f"{file_name}.json"
        
        # 加载或初始化数据
        if not force_fetch and json_file_path.exists():
            logger.info(f"从缓存加载数据: {json_file_path}")
            try:
                with open(json_file_path, "r", encoding="utf-8") as readfile:
                    data = json.load(readfile)
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"读取缓存文件失败: {e}")
                data = {}
        else:
            data = {}

        if not data:
            players_items = {}
            range_start = 1 if new_mode else 1 + end
            range_end = 2 if new_mode else 1 + start
            
            logger.info(f"加载第 {range_start} 到 {range_end-1} 天的数据...")
            
            for d in range(range_start, range_end):
                day_start = AntiqueScoreUtil.get_past_x_day_start_epoch(d)
                
                if not new_mode:
                    day_file_name = f"{day_start}.json"
                else:
                    day_file_name = f"{AntiqueScoreUtil.get_past_x_day_start_epoch(0)}_new_mode.json"
                
                day_file_path = DAILY_DIR / day_file_name
                
                if not day_file_path.exists():
                    if d == 0:
                        logger.info(f"数据文件不存在，开始获取: {day_file_path}")
                        self.get_yesterday_all_players_statics(new_mode)
                    else:
                        logger.warning(f"跳过不存在的文件: {day_file_path}")
                        continue
                
                try:
                    with open(day_file_path, "r", encoding="utf-8") as readfile:
                        day_data = json.load(readfile)
                        data = AntiqueScoreUtil.merge_2_dicts(data, day_data)
                    logger.info(f"成功加载: {day_file_path}")
                except (IOError, json.JSONDecodeError) as e:
                    logger.error(f"读取文件失败 {day_file_path}: {e}")
                    continue
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
                        lambda k: data["pokemons"][k]["use_rate"] > MIN_USE_RATE_THRESHOLD,
                        AntiqueScoreUtil.get_sorted_dict_keys_list_by_value(
                            data["pokemons"], "win_rate", True
                        ),
                    )
                )
            
            # 保存 JSON 数据
            try:
                DAILY_DIR.mkdir(parents=True, exist_ok=True)
                with open(json_file_path, "w", encoding="utf-8") as outfile:
                    json.dump(data, outfile, ensure_ascii=False, indent=2)
                logger.info(f"成功保存 JSON 文件: {json_file_path}")
            except IOError as e:
                logger.error(f"保存 JSON 文件失败: {e}")
                raise

        # 生成完整 CSV 文件
        csv_file_path = DATA_DIR / f"top100_players_{file_name}.csv"
        logger.info(f"开始生成完整 CSV 文件: {csv_file_path}")
        
        _index = 0
        index = 0
        use_rate = 0
        
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(csv_file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
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
                        if count >= TOP_PLAYERS_DISPLAY_COUNT:
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
                logger.info(f"成功生成完整 CSV 文件: {csv_file_path}")
        except IOError as e:
            logger.error(f"生成 CSV 文件失败: {e}")
            raise

        # 加载上周数据用于对比
        last_week_file_name = self._build_file_name(start + 7, end + 7, new_mode)
        last_week_json_path = DAILY_DIR / f"{last_week_file_name}.json"
        
        if not force_fetch and last_week_json_path.exists():
            try:
                with open(last_week_json_path, "r", encoding="utf-8") as readfile:
                    last_week_data = json.load(readfile)
                logger.info(f"加载上周数据: {last_week_json_path}")
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"读取上周数据失败: {e}")
                last_week_data = {"pokemons": {}}
        else:
            logger.info("上周数据不存在，跳过对比")
            last_week_data = {"pokemons": {}}
        # 生成简化 CSV 文件（仅限 7 天数据）
        if start - end == 7:
            simple_csv_path = DATA_DIR / f"top100_players_simple_{file_name}.csv"
            logger.info(f"开始生成简化 CSV 文件: {simple_csv_path}")
            
            use_rate = 0
            _index = 0
            
            try:
                with open(simple_csv_path, "w", newline="", encoding="utf-8-sig") as csvfile:
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
                    logger.info(f"成功生成简化 CSV 文件: {simple_csv_path}")
            except IOError as e:
                logger.error(f"生成简化 CSV 文件失败: {e}")
                raise
            
            # 生成 AI 语音文本文件
            logger.info(f"开始生成语音文本文件: {VOICE_TEXT_PATH}")
            use_rate = 0
            _index = 0
            
            try:
                VOICE_TEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(VOICE_TEXT_PATH, "w", encoding="utf-8") as voice_file:
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
                    
                    logger.info(f"成功生成语音文本文件: {VOICE_TEXT_PATH}")
            except IOError as e:
                logger.error(f"生成语音文本文件失败: {e}")
                raise

    @staticmethod
    def _build_file_name(start: int, end: int, new_mode: bool = False) -> str:
        """
        构建数据文件名
        
        Args:
            start: 开始天数
            end: 结束天数
            new_mode: 是否使用新模式
            
        Returns:
            文件名字符串（不含扩展名）
        """
        if not new_mode:
            return (
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
            return (
                time.strftime(
                    "%Y-%b-%d",
                    time.gmtime(AntiqueScoreUtil.get_past_x_day_start_epoch(1 + end)),
                )
                + "_new_mode"
            )

    @staticmethod
    def add_win_rate(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归添加胜率到数据字典
        
        Args:
            data: 包含 win 和 lost 的数据字典
            
        Returns:
            添加了 win_rate 字段的数据字典
        """
        for key in data:
            if isinstance(data[key], dict):
                data[key] = Top100Players.add_win_rate(data[key])
        if "win" in data and "lost" in data:
            total = data["win"] + data["lost"]
            data["win_rate"] = data["win"] / total if total > 0 else 0
        return data

    @staticmethod
    def get_one_player_item_static(
        driver: Optional[AntiqueDriver],
        name: str,
        force_fetch: bool = False,
        cache_days: int = 6,
        total_battle_threshold: int = 60,
        season_battle_threshold: int = 25,
        season_battle_threshold_soft: int = 10,
        has_season_win: bool = True,
        retry: int = 2,
        should_print: bool = True,
    ) -> Dict[str, Any]:
        """
        获取单个玩家的持有物统计数据
        
        Args:
            driver: AntiqueDriver 实例
            name: 玩家名称
            force_fetch: 是否强制重新获取
            cache_days: 缓存天数
            total_battle_threshold: 总战斗场次阈值
            season_battle_threshold: 赛季战斗场次阈值
            season_battle_threshold_soft: 赛季战斗场次软阈值
            has_season_win: 是否要求有赛季胜场
            retry: 重试次数
            should_print: 是否打印日志
            
        Returns:
            玩家持有物数据字典
        """
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
                    and int(pokemon["statistics"]["SeasonBattles"]) >= season_battle_threshold_soft
                )
                or int(pokemon["statistics"]["SeasonBattles"]) >= season_battle_threshold
            ):
                if "Image" not in pokemon:
                    continue
                
                pokemon_name = AntiqueScoreUtil.unite_data[pokemon["Image"]]["chinese"]
                items_string = AntiqueScoreUtil.get_pokemon_items_string(pokemon["Items"])
                
                player_data[pokemon_name] = {
                    "items_string": items_string,
                    "win": pokemon["statistics"]["SeasonWins"]
                           + int(
                        HISTORICAL_WEIGHT
                        * (pokemon["statistics"]["NoOfWins"] - pokemon["statistics"]["SeasonWins"])
                    ),
                    "total": pokemon["statistics"]["SeasonBattles"]
                             + int(
                        HISTORICAL_WEIGHT
                        * (pokemon["statistics"]["TotalBattles"] - pokemon["statistics"]["SeasonBattles"])
                    ),
                }
        return player_data
