from pathlib import Path

import pandas as pd
import pytest
import solara

try:
    import vaex
except ImportError:
    vaex = None
import polars as pl

from solara.components.datatable import DataTable, DataTableWidget
from solara.util import IPYVUETIFY_V3

HERE = Path(__file__).parent

titanic_url = HERE.parent / "titanic.csv"
df_pandas = pd.read_csv(titanic_url)
for col in df_pandas.columns:
    if hasattr(pd, "Int64Dtype") and isinstance(df_pandas[col].dtype, pd.Int64Dtype):
        df_pandas[col] = df_pandas[col].fillna(0).astype("int64")
    elif hasattr(pd, "Float64Dtype") and isinstance(df_pandas[col].dtype, pd.Float64Dtype):
        df_pandas[col] = df_pandas[col].fillna(0.0).astype("float64")
    elif df_pandas[col].dtype == "object":
        df_pandas[col] = df_pandas[col].astype(str).fillna("nan")

dfs = [pytest.param(df_pandas, id="pandas")]
if vaex is not None:
    dfs.insert(0, pytest.param(vaex.from_pandas(df_pandas), id="vaex"))
try:
    dfs.append(pytest.param(pl.from_pandas(df_pandas), id="polars"))
except ImportError as e:
    dfs.append(pytest.param(None, id="polars", marks=pytest.mark.skip(reason=f"polars conversion failed: {e}")))


@pytest.mark.parametrize("df", dfs)
def test_render(df):
    @solara.component
    def Test():
        return DataTable(df)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert isinstance(widget, DataTableWidget)
    assert len(widget.items) == 20
    expected_keys = {"title", "key", "sortable"} if IPYVUETIFY_V3 else {"text", "value", "sortable"}
    assert set(widget.headers[0]) == expected_keys
    assert ("v-data-table-server" in widget.template.template) is IPYVUETIFY_V3


def test_search_filter_and_columns():
    @solara.component
    def Test():
        return DataTable(df_pandas, searchable=True, search="female", columns=["sex", "age"], items_per_page=5)

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert [item["sex"] for item in widget.items]
    assert all("age" in item for item in widget.items)
    assert all("name" not in item for item in widget.items)
    assert widget.total_length > 0


def test_export_widget():
    @solara.component
    def Test():
        return DataTable(df_pandas.head(3), export_filename="titanic.csv")

    widget, rc = solara.render_fixed(Test(), handle_error=False)
    assert widget.children
    assert any(getattr(child, "filename", None) == "titanic.csv" for child in widget.children)
