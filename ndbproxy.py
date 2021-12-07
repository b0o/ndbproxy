"""Proxy chrome debugger connection with a stable URL"""
# pylint: disable=missing-function-docstring

import asyncio
import atexit
import json
import multiprocessing
import time

import requests

import websockets
import websockets.client

from mitmproxy import ctx
from mitmproxy import http

# TODO: Make configurable from command-line
UPSTREAM_HOST = "localhost"
UPSTREAM_PORT = 9229


def task(func):
    """(decorator) Runs an async function on the main event loop"""
    return lambda *args, **kwargs: asyncio.get_running_loop().create_task(func(*args, **kwargs))


class RetryError(Exception):
    """retry error"""


def retry(max_tries=10, delay=0.1, backoff=1, exception=Exception, is_async=True):
    """(decorator) make a function call retry until it succeeds"""
    if not isinstance(exception, list):
        exception = [exception]

    async def _retry(func, *args, **kwargs):
        err = Exception()
        i = -1
        while max_tries == -1 or i < max_tries:
            i += 1
            if i > 0:
                print(f"retry: attempt {i}")
                if delay > 0:
                    await asyncio.sleep((i * backoff * delay) + delay)
            try:
                if is_async:
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            except Exception as _err:  # pylint: disable=broad-except
                match = False
                for ex in exception:
                    err = _err
                    if isinstance(err, ex):
                        match = True
                        break
                if not match:
                    raise err  # pylint: disable=raise-missing-from

        raise RetryError(f"too many retries (max={max_tries})") from err

    return lambda func: lambda *args, **kwargs: _retry(func, *args, **kwargs)


def upstream_uri(path=None, proto="http"):
    """get uri for `path` for the upstream, optionally with protocol `proto`"""
    if path is None:
        path = []
    elif isinstance(path, str):
        path = [path]
    return "{}://{}:{}/{}".format(proto, UPSTREAM_HOST, UPSTREAM_PORT, "/".join(path))


@retry(exception=requests.exceptions.ConnectionError, is_async=False, max_tries=-1)
def upstream_id() -> str:
    """get the current ID from the upstream server"""
    res = requests.get(upstream_uri("json/list")).json()
    return res[0]['id']


def chrome_console_message(kind, *args):
    msg = {
        "method": "Runtime.consoleAPICalled",
        "params": {
            "type": kind,
            "args": [],
            "executionContextId": 1,
            "timestamp": time.time_ns() / 1000000,
        }
    }

    if kind == "clear":
        msg["params"]["args"].append({
            "type": "string",
            "value": "console.clear",
        })

    elif kind == "log":
        for arg in args:
            msg["params"]["args"].append({
                "type": "string",
                "value": arg,
            })

    return json.dumps(msg)


class NdbBridge(multiprocessing.Process):  # pylint: disable=too-many-instance-attributes
    """bridge between the upstream debug server and the NdbProxy mitmproxy addon"""
    def __init__(self, listen_host, listen_port):
        super().__init__()

        self.listen_host = listen_host
        self.listen_port = listen_port

        self.bridge_server = None

        self.server_conn = None
        self.server_queue = None
        self.server_sub = None
        self.server_handler = None

        self.client_message_prelude_complete = False
        self.client_message_prelude = []
        self.client_conn = None
        self.client_queue = None
        self.client_sub = None

    @task
    async def queue_subscribe(self, queue: asyncio.Queue, handler):
        print("subscribe: init")
        while True:
            message = await queue.get()
            print("subscribe: got message")
            await handler(message)
            print("subscribe: handled message")

    @retry(exception=OSError, max_tries=-1)
    async def bridge_serve(self):
        """start the bridge websocket server"""
        self.server_queue = asyncio.Queue()
        self.client_queue = asyncio.Queue()
        serve_ws = websockets.serve  # pylint: disable=no-member
        if not self.client_sub:
            self.client_sub = self.queue_subscribe(self.client_queue, self.client_message_handler)
        self.bridge_server = serve_ws(self.client_websocket_handler, self.listen_host, self.listen_port)
        async with self.bridge_server:
            print(f"bridge: listening at {self.listen_host}:{self.listen_port}")
            await asyncio.Future()

    async def client_message_handler(self, message):
        print("client_message_handler: message")
        if not self.client_message_prelude_complete:
            self.client_message_prelude.append(message)
            message_dict = json.loads(message)
            if message_dict.get("method") == "Runtime.runIfWaitingForDebugger":
                self.client_message_prelude_complete = True
        try:
            await self.server_conn.send(message)
        except websockets.exceptions.ConnectionClosed:
            print("client_message_handler: server connection closed")
            await self.server_reconnect()
            return
        print("client_message_handler: sent")
        return

    async def server_reconnect(self):
        await self.server_connect()
        await self.client_replay_prelude()
        await self.client_conn.send(
            chrome_console_message("log", "%cDebug server restarted", "color: red; font-weight: bold"))

    async def client_replay_prelude(self):
        print("client_replay_prelude")
        while not self.client_queue.empty():
            self.client_queue.get_nowait()
        for message in self.client_message_prelude:
            await self.client_queue.put(message)

    async def client_websocket_handler(self, websocket):
        """handle incoming websocket messages from the client"""
        self.client_conn = websocket
        await self.server_connect()
        while True:
            try:
                message = await websocket.recv()
            except websockets.exceptions.ConnectionClosedError:
                return
            print("bridge: receive: " + message)
            await self.client_queue.put(message)
            print(f"bridge: client_queue put {self.client_queue.qsize()}")

    @retry(exception=[TimeoutError, websockets.exceptions.InvalidHandshake], max_tries=-1)
    async def server_connect(self):
        """connect to the upstream server"""
        upstream = upstream_uri(await upstream_id(), "ws")
        print(f"bridge: server_connect: {upstream}")
        self.server_conn = await websockets.client.connect(upstream, ping_interval=None)
        if not self.server_sub:
            self.server_sub = self.queue_subscribe(self.server_queue, self.server_message_handler)
        print(f"bridge: connected to server: {self.server_conn}")
        if self.server_handler:
            self.server_handler.cancel()
        self.server_handler = self.server_websocket_handler()

    async def server_message_handler(self, message):
        print("server_message_handler: message")
        message_dict = json.loads(message)
        if message_dict.get("method") == "Runtime.executionContextDestroyed":
            print("Runtime.executionContextDestroyed: closing connection to server")
            await self.server_conn.close()
            return
        await self.client_conn.send(message)
        print("server_message_handler: sent")
        return

    @task
    async def server_websocket_handler(self):
        print("server_websocket_handler: connection")
        while True:
            try:
                message = await self.server_conn.recv()
            except websockets.exceptions.ConnectionClosedError:
                await self.server_reconnect()
                return

            print("server_websocket_handler: recv")
            await self.server_queue.put(message)
            print("server_websocket_handler: queue.put")

    def run(self):
        """multiprocessing entrypoint"""
        print('bridge: start')
        asyncio.run(self.bridge_serve())

    def stop(self):
        """multiprocessing termination handler"""
        print('bridge: stop')
        if self.client_conn:
            self.client_conn.close()
        if self.server_conn:
            self.server_conn.close()
        if self.bridge_server:
            self.bridge_server.close()
        print('bridge: stopped')


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

if __name__ == "__main__":
    bridge = NdbBridge("localhost", 9228)
    bridge.run()
else:
    addons.append(NdbProxy())
