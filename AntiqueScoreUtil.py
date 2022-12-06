import base64
import hashlib
import json
import os.path
import time
import urllib

import requests
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.number import bytes_to_long
from bs4 import BeautifulSoup
from halo import Halo

player_dump_data_path = "../player_dump_data/"

pokemon_image_to_name_dict = {"t_Square_Venusaur": "Venusaur", "t_Square_Charizard": "Charizard", "t_Square_Blastoise": "Blastoise", "t_Square_Pikachu": "Pikachu", "t_Square_Clefable": "Clefable", "t_Square_Ninetales": "Alolan Ninetales", "t_Square_Wigglytuff": "Wigglytuff", "t_Square_Machamp": "Machamp", "t_Square_Slowbro": "Slowbro", "t_Square_Dodrio": "Dodrio", "t_Square_Gengar": "Gengar", "t_Square_Blissey": "Blissey", "t_Square_MrMime": "Mr. Mime", "t_Square_Scizor": "Scizor", "t_Square_Snorlax": "Snorlax", "t_Square_Dragonite": "Dragonite", "t_Square_Mew": "Mew", "t_Square_Azumarill": "Azumarill", "t_Square_Espeon": "Espeon", "t_Square_Mamoswine": "Mamoswine", "t_Square_Tyranitar": "Tyranitar", "t_Square_Gardevoir": "Gardevoir", "t_Square_Sableye": "Sableye", "t_Square_Absol": "Absol", "t_Square_Garchomp": "Garchomp", "t_Square_Lucario": "Lucario", "t_Square_Glaceon": "Glaceon", "t_Square_Crustle": "Crustle", "t_Square_Zoroark": "Zoroark", "t_Square_Delphox": "Delphox", "t_Square_Greninja": "Greninja", "t_Square_Talonflame": "Talonflame", "t_Square_Aegislash": "Aegislash", "t_Square_Sylveon": "Sylveon", "t_Square_Trevenant": "Trevenant", "t_Square_Hoopa": "Hoopa", "t_Square_Decidueye": "Decidueye", "t_Square_Tsareena": "Tsareena", "t_Square_Comfey": "Comfey", "t_Square_Buzzwole": "Buzzwole", "t_Square_Zeraora": "Zeraora", "t_Square_Cinderace": "Cinderace", "t_Square_Greedent": "Greedent", "t_Square_Eldegoss": "Eldegoss", "t_Square_Cramorant": "Cramorant", "t_Square_Duraludon": "Duraludon", "t_Square_Dragapult": "Dragapult", "t_Square_Urshifu_Single": "Urshifu", "t_Square_Urshifu_Rapid": "Urshifu"}

pokemon_chinese_name_dict = {"Venusaur": "妙蛙花", "Charizard": "喷火龙", "Blastoise": "水箭龟", "Pikachu": "皮卡丘",
                             "Alolan Ninetales": "阿罗拉九尾", "Wigglytuff": "胖可丁", "Machamp": "怪力", "Slowbro": "呆壳兽",
                             "Gengar": "耿鬼", "Blissey": "幸福蛋", "Mr. Mime": "魔墙人偶", "Snorlax": "卡比兽", "Dragonite": "快龙",
                             "Azumarill": "玛力露丽", "Espeon": "太阳伊布", "Mamoswine": "象牙猪", "Gardevoir": "沙奈朵",
                             "Glaceon": "冰伊布", "Absol": "阿勃梭鲁", "Garchomp": "烈咬陆鲨", "Lucario": "路卡利欧",
                             "Crustle": "岩殿居蟹", "Delphox": "妖火红狐", "Greninja": "甲贺忍蛙", "Talonflame": "烈箭鹰",
                             "Aegislash": "坚盾剑怪", "Sylveon": "仙子伊布", "Trevenant": "朽木妖", "Hoopa": "胡帕",
                             "Decidueye": "狙射树枭", "Tsareena": "甜冷美后", "Zeraora": "捷拉奥拉", "Cinderace": "闪焰王牌",
                             "Greedent": "藏饱栗鼠", "Eldegoss": "白蓬蓬", "Duraludon": "铝钢龙", "Cramorant": "古月鸟",
                             "Buzzwole": "爆肌蚊", "Tyranitar": "班基拉斯", "Mew": "梦幻", "Dodrio": "嘟嘟利", "Scizor": "巨钳螳螂",
                             "Clefable": "皮可西", "Sableye": "勾魂眼", "Zoroark": "索罗亚克", "Urshifu": "武道熊师"}

pokemon_skill_names = {"t_Skill_Bulbasaur_S12": "Giga Drain", "t_Skill_Bulbasaur_U12": "Petal Dance",
                       "t_Skill_Bulbasaur_S11": "Sludge Bomb", "t_Skill_Bulbasaur_U11": "Solar Beam",
                       "t_Skill_Charmander_S11": "Flamethrower", "t_Skill_Charmander_U11": "Fire Blast",
                       "t_Skill_Charmander_U12": "Flare Blitz", "t_Skill_Charmander_S12": "Fire Punch",
                       "t_Skill_Squirtle_S11": "Water Spout", "t_Skill_Squirtle_S22": "Rapid Spin",
                       "t_Skill_Squirtle_S12": "Hydro Pump", "t_Skill_Squirtle_S21": "Surf",
                       "t_Skill_Pikachu_S12": "Electro Ball", "t_Skill_Pikachu_U12": "Volt Tackle",
                       "t_Skill_Pikachu_U11": "Thunder", "t_Skill_Pikachu_S11": "Thunderbolt",
                       "t_Skill_Vulpix_S12": "Dazzling Gleam", "t_Skill_Vulpix_S22": "Aurora Veil",
                       "t_Skill_Vulpix_S11": "Avalanche", "t_Skill_Vulpix_S21": "Blizzard",
                       "t_Skill_Jigglypuff_S12": "Dazzling Gleam", "t_Skill_Jigglypuff_S22": "Sing",
                       "t_Skill_Jigglypuff_S11": "Double Slap", "t_Skill_Jigglypuff_S21": "Rollout",
                       "t_Skill_Machop_S11": "Close Combat", "t_Skill_Machop_S21": "Dynamic Punch",
                       "t_Skill_Machop_S12": "Cross Chop", "t_Skill_Machop_S22": "Submission",
                       "t_Skill_Slowpoke_S11": "Scald", "t_Skill_Slowpoke_S21": "Amnesia",
                       "t_Skill_Slowpoke_S22": "Telekinesis", "t_Skill_Slowpoke_S12": "Surf",
                       "t_Skill_Gastly_S21": "Shadow Ball", "t_Skill_Gastly_S11": "Dream Eater",
                       "t_Skill_Gastly_S12": "Sludge Bomb", "t_Skill_Gastly_S22": "Hex",
                       "t_Skill_Chansey_S11": "Egg Bomb", "t_Skill_Chansey_S21": "Soft-Boiled",
                       "t_Skill_Chansey_S12": "Helping Hand", "t_Skill_Chansey_S22": "Safeguard",
                       "t_Skill_MrMime_S21": "Confusion", "t_Skill_MrMime_S22": "Power Swap",
                       "t_Skill_MrMime_S11": "Barrier", "t_Skill_MrMime_S12": "Psychic",
                       "t_Skill_Snorlax_S12": "Heavy Slam", "t_Skill_Snorlax_S22": "Block",
                       "t_Skill_Snorlax_S11": "Flail",
                       "t_Skill_Dragonite_S11": "Dragon Dance", "t_Skill_Dragonite_S21": "Hyper Beam",
                       "t_Skill_Dragonite_S22": "Outrage", "t_Skill_Dragonite_S12": "Extreme Speed",
                       "t_Skill_Azumarill_S11": "Play Rough", "t_Skill_Azumarill_S21": "Whirlpool",
                       "t_Skill_Azumarill_S12": "Water Pulse", "t_Skill_Azumarill_S22": "Aqua Tail",
                       "t_Skill_Espeon_S11": "Psyshock", "t_Skill_Espeon_S21": "Psybeam",
                       "t_Skill_Espeon_S22": "Future Sight", "t_Skill_Espeon_S12": "Stored Power",
                       "t_Skill_Swinub_S11": "Icicle Crash", "t_Skill_Swinub_S21": "High Horsepower",
                       "t_Skill_Swinub_S12": "Ice Fang", "t_Skill_Swinub_S22": "Earthquake",
                       "t_Skill_Ralts_S12": "Moonblast", "t_Skill_Ralts_S22": "Future Sight",
                       "t_Skill_Ralts_S11": "Psychic", "t_Skill_Ralts_S21": "Psyshock",
                       "t_Skill_Absol_S21": "Night Slash", "t_Skill_Absol_S11": "Psycho Cut",
                       "t_Skill_Absol_S12": "Pursuit", "t_Skill_Absol_S22": "Sucker Punch",
                       "t_Skill_Gible_S12": "Dragon Rush", "t_Skill_Gible_S22": "Dragon Claw",
                       "t_Skill_Gible_S21": "Dig", "t_Skill_Gible_S11": "Earthquake",
                       "t_Skill_Lucario_S12": "Extreme Speed", "t_Skill_Lucario_U12": "Bone Rush",
                       "t_Skill_Lucario_S11": "Power-Up Punch", "t_Skill_Lucario_U11": "Close Combat",
                       "t_Skill_Glaceon_S11": "Icicle Spear", "t_Skill_Glaceon_S21": "Ice Shard",
                       "t_Skill_Glaceon_S22": "Freeze-Dry", "t_Skill_Glaceon_S12": "Icy Wind",
                       "t_Skill_Dwebble_S12": "Shell Smash", "t_Skill_Dwebble_S22": "X-Scissor",
                       "t_Skill_Dwebble_S21": "Stealth Rock", "t_Skill_Dwebble_S11": "Rock Tomb",
                       "t_Skill_Fennekin_S12": "Mystical Fire", "t_Skill_Fennekin_S21": "Fire Spin",
                       "t_Skill_Fennekin_S11": "Fire Blast", "t_Skill_Fennekin_S22": "Flame Charge",
                       "t_Skill_Froakie_S12": "Surf", "t_Skill_Froakie_S22": "Smokescreen",
                       "t_Skill_Froakie_S11": "Water Shuriken", "t_Skill_Froakie_S21": "Double Team",
                       "t_Skill_Fletchling_S12": "Flame Charge", "t_Skill_Fletchling_S21": "Fly",
                       "t_Skill_Fletchling_S11": "Aerial Ace", "t_Skill_Fletchling_S22": "Brave Bird",
                       "t_Skill_Aegislash_S11": "Sacred Sword", "t_Skill_Aegislash_S21": "Wide Guard",
                       "t_Skill_Aegislash_S22": "Iron Head", "t_Skill_Aegislash_S12": "Shadow Claw",
                       "t_Skill_Sylveon_S12": "Hyper Voice", "t_Skill_Sylveon_S22": "Calm Mind",
                       "t_Skill_Sylveon_S11": "Mystical Fire", "t_Skill_Sylveon_S21": "Draining Kiss",
                       "t_Skill_Trevenant_S12": "Curse", "t_Skill_Trevenant_S21": "Horn Leech",
                       "t_Skill_Trevenant_S11": "Wood Hammer", "t_Skill_Trevenant_S22": "Pain Split",
                       "t_Skill_Hoopa_S11": "Phantom Force", "t_Skill_Hoopa_S21": "Hyperspace Hole",
                       "t_Skill_Hoopa_S12": "Shadow Ball",
                       "t_Skill_Hoopa_S22": "Trick", "t_Skill_Decidueye_S12": "Spirit Shackle",
                       "t_Skill_Decidueye_S22": "Shadow Sneak", "t_Skill_Decidueye_S11": "Razor Leaf",
                       "t_Skill_Decidueye_S21": "Leaf Storm", "t_Skill_Tsareena_S12": "Stomp",
                       "t_Skill_Tsareena_S21": "Trop Kick", "t_Skill_Tsareena_S22": "Grassy Glide",
                       "t_Skill_Tsareena_S11": "Triple Axel", "t_Skill_Zeraora_S11": "Volt Switch",
                       "t_Skill_Zeraora_S21": "Discharge", "t_Skill_Zeraora_S12": "Spark",
                       "t_Skill_Zeraora_S22": "Wild Charge", "t_Skill_Scorbunny_S12": "Blaze Kick",
                       "t_Skill_Scorbunny_S21": "Flame Charge", "t_Skill_Scorbunny_S11": "Pyro Ball",
                       "t_Skill_Scorbunny_S22": "Feint", "t_skill_Skwovet_1B": "Belch", "t_skill_Skwovet_2B": "Covet",
                       "t_skill_Skwovet_1A": "Bullet Seed", "t_skill_Skwovet_2A": "Stuff Cheeks",
                       "t_Skill_Gossifleur_S12": "Leaf Tornado", "t_Skill_Gossifleur_S21": "Cotton Guard",
                       "t_Skill_Gossifleur_S22": "Cotton Spore", "t_Skill_Gossifleur_S11": "Pollen Puff",
                       "t_Skill_Cramorant_S12": "Dive", "t_Skill_Cramorant_S22": "Air Slash",
                       "t_Skill_Cramorant_S11": "Surf", "t_Skill_Cramorant_S21": "Hurricane",
                       "t_Skill_Duraludon_S11": "Flash Cannon", "t_Skill_Duraludon_S21": "Dragon Tail",
                       "t_Skill_Duraludon_S12": "Dragon Pulse", "t_Skill_Duraludon_S22": "Stealth Rock",
                       "t_Skill_Buzzwole_S12": "Smack Down", "t_Skill_Buzzwole_S22": "Super Power",
                       "t_Skill_Buzzwole_S21": "Leech Life", "t_Skill_Buzzwole_S11": "Lunge",
                       "t_Skill_Tyranitar_S11": "Dark Pulse", "t_Skill_Tyranitar_S12": "Stone Edge",
                       "t_Skill_Tyranitar_S21": "Ancient Power",
                       "t_Skill_Tyranitar_S22": "Sand Tomb", "t_Skill_Mew_S1B": "Solar Beam",
                       "t_Skill_Mew_S2B": "Light Screen", "t_Skill_Mew_S1C": "Surf", "t_Skill_Mew_S2C": "Agility",
                       "t_Skill_Mew_S1A": "Electro Ball", "t_Skill_Mew_S2A": "Coaching",
                       "t_Skill_Ingame_BT": "In Choice", "t_Skill_Dodrio_S12": "Drill Peck",
                       "t_Skill_Dodrio_S22": "Jump Kick", "t_Skill_Dodrio_S21": "Agility",
                       "t_Skill_Dodrio_S11": "Tri Attack", "t_Skill_Scyther_S11": "Dual Wingbeat",
                       "t_Skill_Scyther_S12": "Bullet Punch", "t_Skill_Scyther_S21": "Double Hit",
                       "t_Skill_Scyther_S22": "Swords Dance", "t_Skill_Scizor_S11": "Dual Wingbeat",
                       "t_Skill_Scizor_S12": "Bullet Punch", "t_Skill_Scizor_S21": "Double Hit",
                       "t_Skill_Scizor_S22": "Swords Dance",
                       "t_Skill_Clefable_S11": "Moonlight", "t_Skill_Clefable_S12": "Draining Kiss",
                       "t_Skill_Clefable_S21": "Gravity", "t_Skill_Clefable_S22": "Follow Me",
                       "t_Skill_Zorua_S11": "Night Slash", "t_Skill_Zorua_S12": "Feint Attack",
                       "t_Skill_Zorua_S21": "Shadow Claw", "t_Skill_Zorua_S22": "Cut",
                       "t_Skill_Sableye_S11": "Knock Off", "t_Skill_Sableye_S12": "Shadow Sneak",
                       "t_Skill_Sableye_S21": "Feint Attack", "t_Skill_Sableye_S22": "Confuse Ray",
                       "t_Skill_Urshifu_S11": "Wicked Blow", "t_Skill_Urshifu_S12": "Throat Chop",
                       "t_Skill_Urshifu_S21": "Surging Strikes", "t_Skill_Urshifu_S22": "Liquidation", }

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

skills_dict = {
    "Aerial Ace": "燕返" + "\t",
    "Agility": "高速移动",
    "Air Slash": "空气斩",
    "Amnesia": "瞬间失忆",
    "Aurora Veil": "极光幕",
    "Aqua Tail": "水流尾",
    "Avalanche": "雪崩" + "\t",
    "Barrier": "屏障" + "\t",
    "Belch": "打嗝" + "\t",
    "Blizzard": "暴风雪",
    "Blaze Kick": "火焰踢",
    "Block": "挡路" + "\t",
    "Bone Rush": "骨棒乱打",
    "Brave Bird": "勇鸟猛攻",
    "Bullet Seed": "种子机关枪",
    "Calm Mind": "冥想" + "\t",
    "Close Combat": "近身战",
    "Coaching": "指导" + "\t",
    "Confusion": "念力" + "\t",
    "Cotton Guard": "棉花防守",
    "Cotton Spore": "棉孢子",
    "Covet": "渴望" + "\t",
    "Cross Chop": "十字劈",
    "Curse": "咒术" + "\t",
    "Dazzling Gleam": "魔法闪耀",
    "Dig": "挖洞" + "\t",
    "Dive": "潜水" + "\t",
    "Discharge": "放电" + "\t",
    "Double Slap": "连环巴掌",
    "Double Team": "影子分身",
    "Dragon Claw": "龙爪" + "\t",
    "Dragon Dance": "龙之舞",
    "Dragon Pulse": "龙之波动",
    "Dragon Rush": "龙之俯冲",
    "Dragon Tail": "龙尾" + "\t",
    "Draining Kiss": "吸取之吻",
    "Dream Eater": "食梦" + "\t",
    "Dynamic Punch": "爆裂拳",
    "Earthquake": "地震" + "\t",
    "Egg Bomb": "炸蛋" + "\t",
    "EjectButton": "逃脱按键",
    "Electro Ball": "电球" + "\t",
    "Extreme Speed": "神速" + "\t",
    "Feint": "佯攻" + "\t",
    "Fire Blast": "大字爆炎",
    "Fire Spin": "火焰旋涡",
    "Fire Punch": "火焰拳",
    "Flail": "抓狂" + "\t",
    "Flame Charge": "蓄能焰袭",
    "Flamethrower": "喷射火焰",
    "Flare Blitz": "闪焰冲锋",
    "Flash Cannon": "加农光炮",
    "Fly": "飞翔" + "\t",
    "Future Sight": "预知未来",
    "Freeze-Dry": "冷冻干燥",
    "Ganrao": "得分加速装置",
    "Gear": "迟缓烟雾",
    "Giga Drain": "终极吸取",
    "Grassy Glide": "青草滑梯",
    "Guard Swap": "防守互换",
    "Heavy Slam": "重磅冲撞",
    "Helping Hand": "帮助" + "\t",
    "Hex": "祸不单行",
    "High Horsepower": "十万马力",
    "Horn Leech": "木角" + "\t",
    "Hydro Pump": "水炮" + "\t",
    "Hyper Beam": "破坏光线",
    "Hyper Voice": "巨声" + "\t",
    "Hyperspace Fury": "异次元猛攻",
    "Hyperspace Hole": "异次元洞",
    "Hurricane": "暴风" + "\t",
    "Ice Fang": "冰冻牙",
    "Icy Wind": "冰冻之风",
    "Ice Shard": "冰砾" + "\t",
    "Icicle Spear": "冰锥" + "\t",
    "Iron Head": "铁头" + "\t",
    "Icicle Crash": "冰柱坠击",
    "Leaf Tornado": "青草搅拌器",
    "Leaf Storm": "飞叶风暴",
    "Light Screen": "光墙" + "\t",
    "Moonblast": "月亮之力",
    "Mystical Fire": "魔法火焰",
    "Night Slash": "暗袭要害",
    "Outrage": "逆鳞" + "\t",
    "Pain Split": "分担痛楚",
    "Petal Dance": "花瓣舞",
    "Phantom Force": "潜灵奇袭",
    "Play Rough": "嬉闹" + "\t",
    "Pollen Puff": "花粉团",
    "Potion": "伤药" + "\t",
    "Power-Up Punch": "增强拳",
    "Psybeam": "幻象光线",
    "Psychic": "精神强念",
    "Psycho Cut": "精神利刃",
    "Psyshock": "精神冲击",
    "Purify": "万灵药",
    "Pursuit": "追打" + "\t",
    "Pyro Ball": "火焰球",
    "Rapid Spin": "高速旋转",
    "Razor Leaf": "飞叶快刀",
    "Rock Tomb": "岩石封锁",
    "Rollout": "滚动" + "\t",
    "Sacred Sword": "圣剑" + "\t",
    "Safeguard": "神秘守护",
    "Scald": "热水" + "\t",
    "Shadow Ball": "暗影球",
    "Shadow Claw": "暗影爪",
    "Shadow Sneak": "影子偷袭",
    "Shell Smash": "破壳" + "\t",
    "Sing": "唱歌" + "\t",
    "Sludge Bomb": "污泥炸弹",
    "Smokescreen": "烟幕" + "\t",
    "Soft-Boiled": "生蛋" + "\t",
    "Solar Beam": "日光束",
    "Spark": "电光" + "\t",
    "Spirit Shackle": "缝影" + "\t",
    "Stealth Rock": "隐形岩",
    "Stomp": "踩踏" + "\t",
    "Stored Power": "辅助力量",
    "Stuff Cheeks": "大快朵颐",
    "Submission": "地狱翻滚",
    "Sucker Punch": "突袭" + "\t",
    "Surf": "冲浪" + "\t",
    "Tail": "向尾喵的尾巴",
    "Telekinesis": "意念移物",
    "Thunder": "打雷" + "\t",
    "Thunderbolt": "十万伏特",
    "Trick": "戏法" + "\t",
    "Triple Axel": "三旋击",
    "Trop Kick": "热带踢",
    "Volt Tackle": "伏特攻击",
    "Volt Switch": "伏特替换",
    "Water Pulse": "水之波动",
    "Water Shuriken": "飞水手里剑",
    "Water Spout": "喷水" + "\t",
    "Whirlpool": "潮旋" + "\t",
    "Wide Guard": "广域防守",
    "Wild Charge": "疯狂伏特",
    "Wood Hammer": "木槌" + "\t",
    "X-Scissor": "十字剪",
    "XAttack": "攻击强化",
    "XSpeed": "速度强化",
    "Yawn": "哈欠" + "\t",
    "Lunge": "猛扑" + "\t",
    "Smack Down": "击落" + "\t",
    "Leech Life": "吸血" + "\t",
    "Super Power": "蛮力" + "\t",
    "Dark Pulse": "恶之波动",
    "Stone Edge": "尖石攻击",
    "Ancient Power": "原始之力",
    "Sand Tomb": "流沙地狱",
    "Power Swap": "力量互换",
    "Coaching": "指导" + "\t",
    "In Choice": "技能未定",
    "Drill Peck": "啄钻" + "\t",
    "Jump Kick": "飞踢" + "\t",
    "Tri Attack": "三重攻击",
    "Agility": "高速移动",
    "Bullet Punch": "子弹拳",
    "Swords Dance": "剑舞" + "\t",
    "Dual Wingbeat": "双翼" + "\t",
    "Double Hit": "二连击",
    "Quick Attack": "电光一闪",
    "Heal Pulse": "治愈波动",
    "Moonlight": "月光" + "\t",
    "Disarming Voice": "魅惑之声",
    "Draining Kiss": "吸取之吻",
    "Gravity": "重力" + "\t",
    "Follow Me": "看我嘛",
    "Night Slash": "暗袭要害",
    "Feint Attack": "出奇一击",
    "Shadow Claw": "暗影爪",
    "Cut": "居合劈",
    "Knock Off": "拍落",
    "Confuse Ray": "奇异之光",
    "Wicked Blow": "暗冥强击",
    "Throat Chop": "深渊突刺",
    "Surging Strikes": "水流连打",
    "Liquidation": "水流裂破",
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
    skill_names = pokemon_skill_names
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

    skill1_name = "_".join(target_data["Skill1"].split("_")[0:4])
    skill2_name = "_".join(target_data["Skill2"].split("_")[0:4])
    if skill1_name == skill2_name == "t_Skill_Hoopa_U":
        skill1_name = "t_Skill_Hoopa_U_S1"
        skill2_name = "t_Skill_Hoopa_U_S2"
    if not skill_names.get(skill1_name, None) or not skill_names.get(skill2_name, None):
        print("Error: unable to get name for " + skill1_name + " or " + skill2_name)
        return None
    return [
        skill_names[skill1_name],
        skill_names[skill2_name],
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
