# NOTE: this is currently non-functioning

import atexit

from mitmproxy import ctx
from mitmproxy import http


class NdbProxy:
    """Proxy connection between Node<-->Chrome debugger with a stable URL"""

    def __init__(self):
        self.bridge = NdbBridge("localhost", 8273)
        self.bridge.start()
        atexit.register(self.bridge.kill)

    def done(self):
        print("proxy: done")
        self.bridge.kill()

    def load(self, loader):  # pylint: disable=no-self-use
        """ mitmproxy load hook """
        loader.add_option(
            name="out-file",
            typespec=str,
            default="",
            help="File to output WebSocket messages to",
        )

    def request(self, flow: http.HTTPFlow) -> None:
        """mitmproxy request hook"""
        print("proxy: request")
        if flow.request.path != "/debugger":
            return
        req_headers = flow.request.headers
        if not (req_headers["Connection"] == "Upgrade" and req_headers["Upgrade"] == "websocket"):
            return
        flow.request.host = self.bridge.listen_host
        flow.request.port = self.bridge.listen_port
        flow.request.path = "/"

    def websocket_message(self, flow: http.HTTPFlow) -> None:  # pylint: disable=no-self-use
        """mitmproxy websocket_message hook"""
        assert flow.websocket is not None
        msg = flow.websocket.messages[-1]
        kind = "client" if msg.from_client else "server"

        file = getattr(ctx.options, 'out-file')
        if file:
            with open(file, "a") as handle:
                handle.write(json.dumps({kind: json.loads(msg.text)}) + "\n")


addons = []
