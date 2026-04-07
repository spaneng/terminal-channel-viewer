CSS = """
#sidebar {
    width: 30;
    dock: left;
    border-right: solid $accent;
}

#sidebar ListView {
    height: 1fr;
}

#sidebar .sidebar-title {
    text-style: bold;
    padding: 0 1;
    color: $text;
    background: $surface;
}

#content {
    width: 1fr;
}

#channel-table {
    height: 1fr;
}

#starred-section {
    height: auto;
    max-height: 40%;
    border-top: solid $accent;
}

#starred-section .section-title {
    text-style: bold;
    padding: 0 1;
    color: $text;
    background: $surface;
}

#starred-table {
    height: auto;
    max-height: 100%;
}
"""
