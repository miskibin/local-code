def test_setup_logging_replaces_stdlib_handlers():
    import logging

    from app.observability import setup_logging

    setup_logging("INFO")
    root = logging.getLogger()
    handler_classes = {type(h).__name__ for h in root.handlers}
    assert "InterceptHandler" in handler_classes
