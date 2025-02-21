# Blake Xu

from AntiqueScore import AntiqueScore
from Top100Players import Top100Players
# from PlayerStats import getPlayersStatistics, getOnePlayerDetails
import argparse
import re
from AntiqueDriver import AntiqueDriver


def generate_antique_score(antique_driver):
    print("Data fetch begin")
    antique_score_obj = AntiqueScore(antique_driver)
    print("Data fetch success")
    week_num = antique_score_obj.get_week_number()
    print(antique_score_obj.get_week_date_range())
    print("Data processing for week " + str(week_num))
    file_name = antique_score_obj.dump_csv(update_skills=False)
    if not file_name:
        print("Something Wrong Happened")


# def generate_items_recommend(antique_driver):
#     items_recommends = Top100Players(antique_driver)
#     items_recommends.get_all_players_item_statics()
#     items_recommends.dump_csv_cn()


def dump_yesterday_top100_players(antique_driver):
    top_100_players = Top100Players(antique_driver)
    top_100_players.get_yesterday_all_players_statics()


def dump_top100_players_past_x_days_summary(days, antique_driver, new_mode):
    top_100_players = Top100Players(antique_driver)
    top_100_players.get_past_x_days_summary(days, 0, new_mode=new_mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     "-r", "--ranking-index", help="Get ranking index", action="store_true"
    # )
    parser.add_argument(
        "-t",
        "--top-100-stats",
        help="Get top 100 players uses count",
        action="store_true",
    )
    parser.add_argument(
        "-d", "--days", help="Get data for past {DAYS} days", type=int, default=0
    )
    parser.add_argument(
        "-g", "--games", help="Get past X games", type=int, default=50
    )
    # parser.add_argument(
    #     "-c", "--compact", help="Output tables in compact style", action="store_true"
    # )
    parser.add_argument(
        "-n", "--new_mode", help="Using new mode if exist", action="store_true", default=False
    )
    parser.add_argument(
        "-y",
        "--yesterday-data-dump",
        help="Dump yesterday top 100 players' status",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--using_driver",
        help="Using chrome driver to unblock rate limit",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    driver = None
    if args.using_driver:
        driver = AntiqueDriver()
    # if args.ranking_index:
    #     generate_antique_score(driver)
    if args.top_100_stats:
        if args.days >= 1:
            dump_top100_players_past_x_days_summary(args.days, driver, args.new_mode)
        else:
            dump_top100_players_past_x_days_summary(7, driver, args.new_mode)
    elif args.yesterday_data_dump:
        dump_yesterday_top100_players(driver)
    else:
        parser.print_help()
    # Driver.quit()
