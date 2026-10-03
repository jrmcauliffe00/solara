import dataclasses
import io
import math
import os
from dataclasses import replace
from typing import Any, Callable, List, Optional, Sequence, cast

import ipywidgets
import traitlets
import solara
import solara.hooks.dataframe
import solara.lab
from solara.lab.hooks.dataframe import use_df_column_names, df_row_names
from solara.lab.utils.dataframe import df_len, df_records, df_slice
from solara.util import IPYVUETIFY_V3

from .. import CellAction, ColumnAction


def _ensure_dict(d):
    if dataclasses.is_dataclass(d) and not isinstance(d, type):
        return dataclasses.asdict(d)
    return d


def _drop_keys_from_list_of_mappings(drop):
    def closure(list_of_dicts, widget):
        return [{k: v for k, v in _ensure_dict(d).items() if k not in drop} for d in list_of_dicts]

    return closure


class DataTableWidget(solara.components.component_vue.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "datatable_v3.vue" if IPYVUETIFY_V3 else "datatable.vue"))

    total_length = traitlets.CInt().tag(sync=True)
    checked = traitlets.List(cast(List[Any], [])).tag(sync=True)
    column_actions = traitlets.List(trait=traitlets.Instance(ColumnAction), default_value=[]).tag(sync=True, to_json=_drop_keys_from_list_of_mappings(["on_click"]))
    _column_actions_callbacks = traitlets.List(trait=traitlets.Callable(), default_value=[])
    cell_actions = traitlets.List(trait=traitlets.Instance(CellAction), default_value=[]).tag(sync=True, to_json=_drop_keys_from_list_of_mappings(["on_click"]))
    _cell_actions_callbacks = traitlets.List(trait=traitlets.Callable(), default_value=[])
    items = traitlets.Any().tag(sync=True)
    headers = traitlets.Any().tag(sync=True)
    headers_selections = traitlets.Any().tag(sync=True)
    options = traitlets.Any(default_value={"page": 1, "itemsPerPage": 20, "sortBy": []} if IPYVUETIFY_V3 else None).tag(sync=True)
    items_per_page = traitlets.CInt(11).tag(sync=True)
    selections = traitlets.Any([]).tag(sync=True)
    selection_colors = traitlets.Any([]).tag(sync=True)
    selection_enabled = traitlets.Bool(True).tag(sync=True)
    highlighted = traitlets.Int(None, allow_none=True).tag(sync=True)
    scrollable = traitlets.Bool(False).tag(sync=True)
    height = traitlets.Unicode(None, allow_none=True).tag(sync=True)
    hidden_components = traitlets.List(cast(List[Any], [])).tag(sync=False)
    column_header_hover = traitlets.Unicode(allow_none=True).tag(sync=True)
    column_header_widget = traitlets.Any(allow_none=True).tag(sync=True, **ipywidgets.widget_serialization)

    def vue_on_column_action(self, data):
        header_value, action_index = data
        on_click = self._column_actions_callbacks[action_index]
        if on_click:
            on_click(header_value)

    def vue_on_cell_action(self, data):
        row, header_value, action_index = data
        on_click = self._cell_actions_callbacks[action_index]
        if on_click:
            on_click(header_value, row)


def format_default(df, column, row_index, value):
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return str(value)


def _normalise_columns(columns: Optional[Sequence[str]], available: Sequence[str]) -> list[str]:
    if columns is None:
        return list(available)
    allowed = set(available)
    return [column for column in columns if column in allowed]


@solara.component
def DataTable(
    df,
    page=0,
    items_per_page=20,
    format=None,
    column_actions: List[ColumnAction] = [],
    cell_actions: List[CellAction] = [],
    scrollable=False,
    on_column_header_hover: Optional[Callable[[Optional[str]], None]] = None,
    column_header_info: Optional[solara.Element] = None,
    searchable: bool = False,
    search: str = "",
    on_search: Optional[Callable[[str], None]] = None,
    columns: Optional[Sequence[str]] = None,
    sort_by: Optional[str] = None,
    descending: bool = False,
    export_filename: Optional[str] = None,
):
    total_length = df_len(df)
    options = {"descending": descending, "page": page + 1, "itemsPerPage": items_per_page, "sortBy": [], "totalItems": total_length}
    options, set_options = solara.use_state(options, key="options")
    format = format or format_default
    search_value, set_search = solara.use_state(search, key="search")
    filtered_columns = _normalise_columns(columns, use_df_column_names(df))
    all_columns = use_df_column_names(df)
    records = df_records(df)

    row_indices = list(range(total_length))
    if searchable and search_value:
        search_query = search_value.lower().strip()
        row_indices = [i for i, record in enumerate(records) if any(search_query in str(record.get(column, "")).lower() for column in filtered_columns)]

    if sort_by is not None and sort_by in all_columns:
        row_indices.sort(key=lambda i: records[i].get(sort_by))
        if descending:
            row_indices.reverse()

    total_length = len(row_indices)
    page = options["page"] - 1
    items_per_page = options["itemsPerPage"]
    i1 = page * items_per_page
    i2 = min(total_length, (page + 1) * items_per_page)

    displayed_indices = row_indices[i1:i2]
    items = []
    for row_index in displayed_indices:
        record = records[row_index]
        item = {"__row__": format(df, None, row_index, df_row_names(df)[row_index])}
        for column in filtered_columns:
            item[column] = format(df, column, row_index, record[column])
        items.append(item)

    if IPYVUETIFY_V3:
        headers = [{"title": name, "key": name, "sortable": False} for name in filtered_columns]
    else:
        headers = [{"text": name, "value": name, "sortable": False} for name in filtered_columns]

    column_actions_callbacks = [k.on_click for k in column_actions]
    cell_actions_callbacks = [k.on_click for k in cell_actions]
    column_actions = [replace(k, on_click=None) for k in column_actions]
    cell_actions = [replace(k, on_click=None) for k in cell_actions]

    export_widget = None
    if export_filename:

        def download_csv():
            output = io.StringIO()
            try:
                df_slice(df, 0, df_len(df)).to_csv(output, index=False)
            except Exception:
                import pandas as pd

                pd.DataFrame(records).to_csv(output, index=False)
            return output.getvalue().encode()

        export_widget = solara.FileDownload(data=download_csv, filename=export_filename, label="Export CSV")

    children = []
    if searchable:
        children.append(solara.InputText(label="Search", value=search_value, continuous_update=True, on_value=set_search))
    if export_widget is not None:
        children.append(export_widget)

    return DataTableWidget.element(
        total_length=total_length,
        items=items,
        headers=headers,
        headers_selections=[],
        options=options,
        items_per_page=items_per_page,
        selections=[],
        selection_colors=[],
        selection_enabled=False,
        highlighted=None,
        scrollable=scrollable,
        on_options=set_options,
        column_actions=column_actions,
        cell_actions=cell_actions,
        _column_actions_callbacks=column_actions_callbacks,
        _cell_actions_callbacks=cell_actions_callbacks,
        on_column_header_hover=on_column_header_hover,
        column_header_widget=column_header_info,
        children=children,
    )


@solara.component
def DataFrame(
    df,
    items_per_page=20,
    column_actions: List[ColumnAction] = [],
    cell_actions: List[CellAction] = [],
    scrollable=False,
    on_column_header_hover: Optional[Callable[[Optional[str]], None]] = None,
    column_header_info: Optional[solara.Element] = None,
    searchable: bool = False,
    search: str = "",
    columns: Optional[Sequence[str]] = None,
    sort_by: Optional[str] = None,
    descending: bool = False,
    export_filename: Optional[str] = None,
):
    return DataTable(
        df,
        items_per_page=items_per_page,
        column_actions=column_actions,
        cell_actions=cell_actions,
        scrollable=scrollable,
        on_column_header_hover=on_column_header_hover,
        column_header_info=column_header_info,
        searchable=searchable,
        search=search,
        columns=columns,
        sort_by=sort_by,
        descending=descending,
        export_filename=export_filename,
    )
