import argparse

from .app import ChannelViewerApp


def main():
    parser = argparse.ArgumentParser(description="Terminal UI for viewing DDA channel data")
    parser.add_argument("uri", help="DDA host address (e.g. 10.144.226.144)")
    parser.add_argument("--key", help="Only show a single tag key")
    args = parser.parse_args()

    app = ChannelViewerApp(uri=args.uri, key_filter=args.key)
    app.run()


if __name__ == "__main__":
    main()
