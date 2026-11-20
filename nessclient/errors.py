class PanelNotRespondingError(TimeoutError):
    """The connection is open but the panel did not answer a status request in time."""


class ClientClosedError(ConnectionError):
    """The client has been closed and will not connect again."""
