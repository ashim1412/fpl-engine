import dagster as dg


@dg.asset
def hello() -> str:
    """Trivial placeholder asset so the webserver has something to load."""
    return "hello, fpl-engine"


defs = dg.Definitions(assets=[hello])
