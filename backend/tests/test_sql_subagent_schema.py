import pytest

CHINOOK_TABLES = (
    "Album",
    "Artist",
    "Customer",
    "Employee",
    "Genre",
    "Invoice",
    "InvoiceLine",
    "MediaType",
    "Playlist",
    "PlaylistTrack",
    "Track",
)


@pytest.fixture(autouse=True)
def _clear_schema_cache():
    from app.tools.sql_subagent_query import schema_blob

    schema_blob.cache_clear()
    yield
    schema_blob.cache_clear()


def test_schema_blob_returns_chinook_create_tables(chinook_path):
    from app.tools.sql_subagent_query import schema_blob

    blob = schema_blob()
    assert "CREATE TABLE" in blob
    for table in CHINOOK_TABLES:
        assert table in blob, f"expected {table!r} in baked schema"
