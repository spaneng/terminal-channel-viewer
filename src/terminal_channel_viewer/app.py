import json

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, ListView, ListItem, Label

from pydoover.docker import DeviceAgentInterface
from pydoover.models import AggregateUpdateEvent, EventSubscription
from pydoover.models.generated.device_agent import device_agent_pb2

from .styles import CSS


class ChannelViewerApp(App):
    TITLE = "DDA Channel Viewer"
    CSS = CSS
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "toggle_star", "Star/Unstar"),
    ]

    def __init__(self, uri: str, key_filter: str | None = None):
        super().__init__()
        self.uri = uri
        self.key_filter = key_filter
        self.active_channel = "tag_values"
        self.device_agent = DeviceAgentInterface(
            app_key="tag_reader",
            dda_uri=f"{uri}:50051",
            dda_timeout=10,
        )
        self.starred: dict[tuple[str, str], str] = {}
        self._channel_data: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Channels", classes="sidebar-title")
                yield ListView()
            with Vertical(id="content"):
                yield DataTable(id="channel-table")
                with Vertical(id="starred-section"):
                    yield Label("Starred", classes="section-title")
                    yield DataTable(id="starred-table")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{self.uri} — {self.active_channel}"

        table = self.query_one("#channel-table", DataTable)
        table.add_column("Key", key="key")
        table.add_column("Value", key="value")
        table.cursor_type = "row"
        table.zebra_stripes = True

        starred = self.query_one("#starred-table", DataTable)
        starred.add_column("Channel", key="channel")
        starred.add_column("Key", key="key")
        starred.add_column("Value", key="value")
        starred.cursor_type = "row"
        starred.zebra_stripes = True

        self._load_channels()
        self._watch_channel(self.active_channel)

    # -- Channel list -----------------------------------------------------------

    @work(exit_on_error=False)
    async def _load_channels(self) -> None:
        await self.device_agent.wait_until_healthy(timeout=10)
        resp = await self.device_agent.make_request(
            "GetDebugInfo",
            device_agent_pb2.DebugInfoRequest(),
        )
        channel_names = sorted(ch.channel_name for ch in resp.channels)
        list_view = self.query_one(ListView)
        for name in channel_names:
            list_view.append(ListItem(Label(name), name=name))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        channel = event.item.name
        if channel and channel != self.active_channel:
            self.active_channel = channel
            self.sub_title = f"{self.uri} — {self.active_channel}"
            table = self.query_one("#channel-table", DataTable)
            table.clear(columns=False)
            self._watch_channel(channel)

    # -- Channel streaming ------------------------------------------------------

    @work(exclusive=True, group="channel_stream", exit_on_error=False)
    async def _watch_channel(self, channel_name: str) -> None:
        async def on_update(event):
            if isinstance(event, AggregateUpdateEvent):
                self._channel_data[channel_name] = event.aggregate.data
                if channel_name == self.active_channel:
                    self._update_channel_table(event.aggregate.data)
                self._update_starred_from_channel(channel_name, event.aggregate.data)

        self.device_agent.add_event_callback(
            channel_name,
            on_update,
            events=EventSubscription.aggregate_update,
        )

        await self.device_agent.wait_for_channels_sync([channel_name], timeout=10)
        aggregate = await self.device_agent.fetch_channel_aggregate(channel_name)
        self._channel_data[channel_name] = aggregate.data
        self._update_channel_table(aggregate.data)
        self._update_starred_from_channel(channel_name, aggregate.data)

    @work(exit_on_error=False)
    async def _ensure_channel_subscription(self, channel_name: str) -> None:
        if channel_name in self._channel_data:
            return

        async def on_update(event):
            if isinstance(event, AggregateUpdateEvent):
                self._channel_data[channel_name] = event.aggregate.data
                self._update_starred_from_channel(channel_name, event.aggregate.data)

        self.device_agent.add_event_callback(
            channel_name,
            on_update,
            events=EventSubscription.aggregate_update,
        )

        await self.device_agent.wait_for_channels_sync([channel_name], timeout=10)
        aggregate = await self.device_agent.fetch_channel_aggregate(channel_name)
        self._channel_data[channel_name] = aggregate.data
        self._update_starred_from_channel(channel_name, aggregate.data)

    # -- Data helpers -----------------------------------------------------------

    def _flatten_data(self, data: dict) -> dict[str, object]:
        items = {}
        if self.key_filter:
            val = data.get(self.key_filter)
            if val is None:
                items[self.key_filter] = "not found"
            elif isinstance(val, dict):
                for k in sorted(val.keys()):
                    items[f"{self.key_filter}.{k}"] = val[k]
            else:
                items[self.key_filter] = val
        else:
            for k in sorted(data.keys()):
                v = data[k]
                if isinstance(v, dict):
                    for nk in sorted(v.keys()):
                        items[f"{k}.{nk}"] = v[nk]
                else:
                    items[k] = v
        return items

    @staticmethod
    def _format_val(val) -> str:
        return json.dumps(val, default=str) if not isinstance(val, str) else val

    # -- Table updates ----------------------------------------------------------

    def _update_channel_table(self, data: dict) -> None:
        table = self.query_one("#channel-table", DataTable)
        items = self._flatten_data(data)

        existing_keys = set(items.keys())
        for row_key in list(table.rows.keys()):
            if row_key.value not in existing_keys:
                table.remove_row(row_key)

        for row_key, val in items.items():
            display_val = self._format_val(val)
            try:
                table.update_cell(row_key, "value", display_val)
            except Exception:
                table.add_row(row_key, display_val, key=row_key)

    def _update_starred_from_channel(self, channel_name: str, data: dict) -> None:
        starred_table = self.query_one("#starred-table", DataTable)
        items = self._flatten_data(data)

        for (ch, key), _ in list(self.starred.items()):
            if ch != channel_name:
                continue
            val = items.get(key)
            if val is not None:
                display_val = self._format_val(val)
                self.starred[(ch, key)] = display_val
                row_id = f"{ch}::{key}"
                try:
                    starred_table.update_cell(row_id, "value", display_val)
                except Exception:
                    pass

    # -- Star/unstar ------------------------------------------------------------

    def action_toggle_star(self) -> None:
        table = self.query_one("#channel-table", DataTable)
        if not table.rows:
            return

        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return

        key = row_key.value
        channel = self.active_channel
        star_id = (channel, key)
        starred_table = self.query_one("#starred-table", DataTable)

        if star_id in self.starred:
            del self.starred[star_id]
            try:
                starred_table.remove_row(f"{channel}::{key}")
            except Exception:
                pass
        else:
            items = self._flatten_data(self._channel_data.get(channel, {}))
            display_val = self._format_val(items.get(key, ""))
            self.starred[star_id] = display_val
            starred_table.add_row(
                channel, key, display_val, key=f"{channel}::{key}"
            )

            if channel != self.active_channel:
                self._ensure_channel_subscription(channel)

    # -- Quit -------------------------------------------------------------------

    async def action_quit(self) -> None:
        await self.device_agent.close()
        self.exit()
