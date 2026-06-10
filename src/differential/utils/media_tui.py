from typing import Optional

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Input, Static

from differential.utils.media_name import ParsedMediaName
from differential.utils.media_search import (
    DEFAULT_MEDIA_SEARCH_FIELDS,
    MediaSearchClient,
    MediaSearchError,
    MediaSearchResult,
    PTGEN_SEARCH_FIELDS,
    format_media_result,
    result_to_ptgen_reference,
    score_media_result,
    source_url,
)


PTGEN_SOURCES = ("", "douban", "imdb", "bangumi", "steam", "epic", "indienova")
PTGEN_FIELD_SCOPES = PTGEN_SEARCH_FIELDS


class MediaSearchApp(App[Optional[MediaSearchResult]]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #top {
        height: 9;
        border: solid $accent;
        padding: 0 1;
    }

    #body {
        height: 1fr;
    }

    #results {
        width: 62%;
        height: 100%;
        border: solid $primary;
    }

    #details {
        width: 38%;
        height: 100%;
        border: solid $secondary;
        padding: 0 1;
    }

    #search {
        height: 3;
        border: solid $accent;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("enter", "select", "select"),
        ("up", "cursor_up", "up"),
        ("down", "cursor_down", "down"),
        ("r", "rerun_search", "rerun"),
        ("/", "focus_search", "search"),
        ("s", "cycle_source", "source"),
        ("f", "cycle_fields", "fields"),
        ("escape", "cancel", "cancel"),
        ("q", "cancel", "quit"),
    ]

    def __init__(
        self,
        parsed: ParsedMediaName,
        client: MediaSearchClient,
        limit: int = 10,
        ptgen_source: Optional[str] = None,
        ptgen_fields: str = DEFAULT_MEDIA_SEARCH_FIELDS,
        search_hint: str = "",
    ):
        super().__init__()
        self.parsed = parsed
        self.client = client
        self.limit = limit
        self.ptgen_source = ptgen_source or ""
        self.ptgen_fields = ptgen_fields
        self.search_query = _initial_search_query(parsed, search_hint)
        self.results: list[MediaSearchResult] = []
        self.error: str = ""
        self._search_timer: Optional[Timer] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(id="top")
        with Horizontal(id="body"):
            yield DataTable(id="results")
            yield Static(id="details")
        yield Input(value=self.search_query, placeholder="PTGen search query", id="search")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Score", "Title", "Year", "Kind", "IDs", "People")
        self._run_search()
        table.focus()

    def on_data_table_row_highlighted(self, message: DataTable.RowHighlighted) -> None:
        self._update_details(message.cursor_row)

    def on_data_table_row_selected(self, message: DataTable.RowSelected) -> None:
        self._select_row(message.cursor_row)

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.input.id == "search":
            self.search_query = message.value.strip()
            self._schedule_search()

    def on_input_submitted(self, message: Input.Submitted) -> None:
        if message.input.id == "search":
            self.search_query = message.value.strip()
            self._cancel_scheduled_search()
            self._run_search()
            self.query_one("#results", DataTable).focus()

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_rerun_search(self) -> None:
        self.search_query = self.query_one("#search", Input).value.strip()
        self._cancel_scheduled_search()
        self._run_search()
        self.query_one("#results", DataTable).focus()

    def action_cycle_source(self) -> None:
        index = PTGEN_SOURCES.index(self.ptgen_source) if self.ptgen_source in PTGEN_SOURCES else 0
        self.ptgen_source = PTGEN_SOURCES[(index + 1) % len(PTGEN_SOURCES)]
        self._run_search()
        self.query_one("#results", DataTable).focus()

    def action_cycle_fields(self) -> None:
        index = PTGEN_FIELD_SCOPES.index(self.ptgen_fields) if self.ptgen_fields in PTGEN_FIELD_SCOPES else 0
        self.ptgen_fields = PTGEN_FIELD_SCOPES[(index + 1) % len(PTGEN_FIELD_SCOPES)]
        self._run_search()
        self.query_one("#results", DataTable).focus()

    def action_cursor_up(self) -> None:
        self._move_table_cursor(-1)

    def action_cursor_down(self) -> None:
        self._move_table_cursor(1)

    def action_select(self) -> None:
        table = self.query_one("#results", DataTable)
        self._select_row(table.cursor_row)

    def action_cancel(self) -> None:
        self._cancel_scheduled_search()
        self.exit(None)

    def _schedule_search(self) -> None:
        if self._search_timer is None:
            self._search_timer = self.set_timer(0.25, self._run_scheduled_search)
        else:
            self._search_timer.reset()

    def _run_scheduled_search(self) -> None:
        self._search_timer = None
        self._run_search()

    def _cancel_scheduled_search(self) -> None:
        if self._search_timer is not None:
            self._search_timer.stop()
            self._search_timer = None

    def _run_search(self) -> None:
        table = self.query_one("#results", DataTable)
        self._set_status("Searching...")
        table.clear()
        self.results = []
        self.error = ""

        try:
            self.results = self.client.search_parsed(
                self.parsed,
                limit=self.limit,
                ptgen_source=self.ptgen_source or None,
                ptgen_fields=self.ptgen_fields,
                search_query=self.search_query,
            )
        except MediaSearchError as exc:
            self.error = str(exc)

        for index, result in enumerate(self.results):
            table.add_row(
                str(score_media_result(result, self.parsed)),
                result.display_title,
                str(result.year or ""),
                result.kind or "",
                ", ".join(f"{source}:{sid}" for source, sid in result.source_ids.items()),
                ", ".join((result.directors + result.cast + result.people)[:3]),
                key=str(index),
            )

        self._render_top()
        self._update_details(0)

    def _move_table_cursor(self, direction: int) -> None:
        table = self.query_one("#results", DataTable)
        if not self.results:
            return
        row = max(0, min(table.cursor_row + direction, len(self.results) - 1))
        table.move_cursor(row=row)
        table.focus()
        self._update_details(row)

    def _select_row(self, row_index: int) -> None:
        if 0 <= row_index < len(self.results):
            self.exit(self.results[row_index])

    def _update_details(self, row_index: int) -> None:
        details = self.query_one("#details", Static)
        if self.error:
            details.update(f"[bold red]Search failed[/bold red]\n\n{escape(self.error)}")
            return
        if not self.results:
            details.update("[bold yellow]No results[/bold yellow]\n\nTry another hint or source filter.")
            return

        row_index = max(0, min(row_index, len(self.results) - 1))
        result = self.results[row_index]
        try:
            reference = result_to_ptgen_reference(result)
            reference_text = f"{reference.site}/{reference.sid}\n{source_url(reference.site, reference.sid)}"
        except Exception as exc:
            reference_text = f"unavailable: {exc}"

        aliases = [title for title in result.matchable_titles if title != result.display_title]
        people = result.directors + result.cast + result.people
        description = result.description[:500] + ("..." if len(result.description) > 500 else "")
        details.update(
            "\n".join(
                [
                    f"[bold]{escape(result.display_title)}[/bold]",
                    f"{escape(str(result.year or '-'))}  {escape(result.kind or '-')}",
                    "",
                    f"[bold]Reference[/bold]\n{escape(reference_text)}",
                    "",
                    f"[bold]Aliases[/bold]\n{escape(' / '.join(aliases[:5]) or '-')}",
                    "",
                    f"[bold]People[/bold]\n{escape(', '.join(people[:8]) or '-')}",
                    "",
                    f"[bold]Description[/bold]\n{escape(description or '-')}",
                ]
            )
        )

    def _render_top(self) -> None:
        warnings = ", ".join(self.parsed.warnings) if self.parsed.warnings else "-"
        source = self.ptgen_source or "all"
        fields = self.ptgen_fields or "all"
        query = self.search_query or "-"
        self.query_one("#top", Static).update(
            "\n".join(
                [
                    "[bold]Differential media search[/bold]",
                    f"title: {escape(self.parsed.title or '-')}",
                    f"candidates: {escape(', '.join(self.parsed.title_candidates) or '-')}",
                    f"year: {self.parsed.year or '-'}    kind: {escape(self.parsed.kind_hint or '-')}    source: {escape(source)}    fields: {escape(fields)}",
                    f"search: {escape(query)}",
                    f"warnings: {escape(warnings)}",
                ]
            )
        )

    def _set_status(self, message: str) -> None:
        self.query_one("#details", Static).update(escape(message))


def run_media_search_tui(
    parsed: ParsedMediaName,
    client: MediaSearchClient,
    limit: int = 10,
    ptgen_source: Optional[str] = None,
    ptgen_fields: str = DEFAULT_MEDIA_SEARCH_FIELDS,
    search_hint: str = "",
) -> Optional[MediaSearchResult]:
    app = MediaSearchApp(
        parsed=parsed,
        client=client,
        limit=limit,
        ptgen_source=ptgen_source,
        ptgen_fields=ptgen_fields,
        search_hint=search_hint,
    )
    return app.run()


def _initial_search_query(parsed: ParsedMediaName, search_hint: str) -> str:
    title = parsed.primary_search_title
    hint = str(search_hint or "").strip()
    return f"{title} {hint}".strip() if hint else title
