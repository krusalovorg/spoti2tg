import logging

from spoti2tg import NowPlayingPoster


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    poster = NowPlayingPoster()
    poster.run()


if __name__ == "__main__":
    main()
