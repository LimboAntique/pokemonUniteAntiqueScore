# Blake Xu

from Top100Players import Top100Players
import argparse
from AntiqueDriver import AntiqueDriver


def dump_yesterday_top100_players(antique_driver):
    top_100_players = Top100Players(antique_driver)
    top_100_players.get_yesterday_all_players_statics()


def dump_top100_players_past_x_days_summary(days, antique_driver):
    top_100_players = Top100Players(antique_driver)
    top_100_players.get_past_x_days_summary(days, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
    if args.top_100_stats:
        if args.days >= 1:
            dump_top100_players_past_x_days_summary(args.days, driver)
        else:
            dump_top100_players_past_x_days_summary(7, driver)
    elif args.yesterday_data_dump:
        dump_yesterday_top100_players(driver)
    else:
        parser.print_help()
