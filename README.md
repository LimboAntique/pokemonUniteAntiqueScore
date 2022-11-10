# pokemonUniteAntiqueScore

## Install
```
pip install -r requirements.txt
```

## Usage
```
usage: main.py [-h] [-r] [-i] [-p] [-n NAMES] [-t] [-d DAYS] [-c] [-y]

optional arguments:
  -h, --help            show this help message and exit
  -r, --ranking-index   Get ranking index
  -i, --items           Get items recommendation
  -p, --player-stats    Get player's statistics, specify names with --names
  -n NAMES, --names NAMES
                        Players' name list {NAMES}, split by space or comma
  -t, --top-100-stats   Get top 100 players uses count
  -d DAYS, --days DAYS  Get data for past {DAYS} days
  -c, --compact         Output tables in compact style
  -y, --yesterday-data-dump
                        Dump yesterday top 100 players' status
```
