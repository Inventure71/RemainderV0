import rumps


class AlwaysOnApp(rumps.App):
    def __init__(self):
        super().__init__("MyApp", icon=None, menu=["Do something", "Quit"])

    @rumps.clicked("Do something")
    def do_something(self, _):
        rumps.notification("Hello", "This is your app", "It’s always on!")


if __name__ == "__main__":
    AlwaysOnApp().run()
