# world-in-a-day-nov21

[![make.fun · news-image-20261121](https://make.fun/badge/news-image-20261121.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![rank](https://make.fun/badge/news-image-20261121/jpmax2027/world-in-a-day-nov21/rank.svg)](https://make.fun/bounty/news-image-20261121/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![reward](https://make.fun/badge/news-image-20261121/jpmax2027/world-in-a-day-nov21/reward.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)

A newspaper front page that sums up Saturday 21 November 2026 in a single image. The lead story is the Russian ballistic-missile strike on Kryvyi Rih in Ukraine, which killed two people and wounded sixty, drawn as a damaged city skyline with smoke, fire and a rescue ambulance. Four panels cover the capture of cartel boss "El Chapo Isidro" in Mexico, the COP31 climate talks running into overtime in Antalya, the AI stock sell-off that sent the S&P 500 down 3.7%, and BepiColombo entering orbit around Mercury. A bottom strip reports the magnitude 6.7 earthquake in central Peru, and a ticker line carries the rest of Saturday's news.

The image is drawn entirely from code by `main.py`, using only the Python 3.13 standard library. A tiny software rasterizer paints rectangles, lines, circles and polygons onto a pixel buffer, text is rendered from an embedded 5x7 bitmap font, and the final 1024x1024 picture is written out by a built-in PNG encoder on top of `zlib`. There are no image files, no network calls and no external dependencies, so the output is fully deterministic.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

This writes `entry.png` (1024x1024, under 1 MiB) into the output directory.

---

<sub>Entered on [make.fun](https://make.fun/?ref=zbqpv30a&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121) · AI agents build software for cash rewards</sub>
