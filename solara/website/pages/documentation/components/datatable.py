import pandas as pd
import solara


@solara.component
def Page():
    df = pd.DataFrame(
        {
            "name": ["Ada", "Grace", "Linus", "Guido", "Margaret"],
            "role": ["analyst", "scientist", "engineer", "engineer", "researcher"],
            "score": [98, 95, 92, 88, 91],
        }
    )

    solara.Markdown(
        """
# DataTable

A lightweight read-only dataframe viewer with paging, search, column selection, sorting, and CSV export.

```python
solara.DataTable(
    df,
    searchable=True,
    columns=["name", "score"],
    sort_by="score",
    descending=True,
    export_filename="scores.csv",
)
```
"""
    )

    solara.DataTable(
        df,
        items_per_page=3,
        searchable=True,
        search="engineer",
        columns=["name", "role", "score"],
        sort_by="score",
        descending=True,
        export_filename="scores.csv",
    )
