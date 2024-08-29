from .core import MyTrameSlicerApp


def main(server=None, **kwargs):
    app = MyTrameSlicerApp(server)
    app.server.start(**kwargs)


if __name__ == "__main__":
    main()
