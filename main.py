import asyncio
import threading
import sys
import signal
from typing import Optional, Any, cast
import tkinter as tk
from tkinter import messagebox
import traceback
from concurrent.futures import Future

# Requires bleak (pip install bleak)
try:
    from bleak import BleakClient, BleakScanner
except Exception:
    BleakClient = None
    BleakScanner = None

# We deliberately avoid monkeypatching BleakClient or client instances here.
# Different bleak versions expose services differently (async get_services vs .services),
# so we do safe local checks where we need them instead of modifying third-party classes.

DEVICE_NAME = "ardubotr4"
# Match Arduino sketch UUIDs
ROBOT_SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
COMMAND_CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
# Commands mapping (you can change the payloads to match your device expectations)
REQUIRE_RESPONSE_ON_WRITE = True
COMMANDS = {
    "forward": "forward",
    "back": "back",
    "left": "left",
    "right": "right",
    "switch": "switch",
}


class BLEController:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        # Use a generic Any type here so static checkers won't complain about backend-specific methods
        self.client: Optional[Any] = None
        self.char_uuid: Optional[str] = None
        self.address: Optional[str] = None
        self.connected = False
        self._lock = asyncio.Lock()

    async def scan_and_connect(self, name: str, timeout: float = 5.0) -> bool:
        if BleakScanner is None:
            raise RuntimeError("bleak is not installed")

        async with self._lock:
            if self.connected:
                return True

            devices = await BleakScanner.discover(timeout=timeout)
            target = None
            for d in devices:
                if d.name and d.name.lower() == name.lower():
                    target = d
                    break

            if not target:
                return False

            self.address = target.address
            # create BleakClient and cast to Any to keep static analyzers from complaining
            client = cast(Any, BleakClient(self.address, loop=self.loop))
            try:
                # debug trace
                print(f"DEBUG: scan_and_connect -> connecting to {self.address}", file=sys.stderr, flush=True)
                try:
                    await client.connect()
                except RecursionError as re:
                    tb = ''.join(traceback.format_exception(type(re), re, re.__traceback__))
                    with open('main_error.log', 'w', encoding='utf-8') as fh:
                        fh.write('RecursionError during client.connect():\n')
                        fh.write(tb)
                    print('RecursionError captured during connect to main_error.log', file=sys.stderr)
                    raise
                print("DEBUG: connected", file=sys.stderr, flush=True)

                # Discover services via client.services (no direct get_services call); retry briefly
                services = getattr(client, "services", None)
                retries = 0
                while not services and retries < 10:
                    await asyncio.sleep(0.1)
                    services = getattr(client, "services", None)
                    retries += 1
                if services:
                    print("DEBUG: services present after connect", file=sys.stderr, flush=True)
                else:
                    print("DEBUG: services not populated, will proceed with known UUID", file=sys.stderr, flush=True)

                chosen_char_uuid = None
                if services:
                    # Prefer exact known characteristic UUID
                    uuid_target = COMMAND_CHAR_UUID.lower()
                    for svc in services:
                        for ch in getattr(svc, 'characteristics', []):
                            if getattr(ch, 'uuid', '').lower() == uuid_target:
                                chosen_char_uuid = ch.uuid
                                break
                        if chosen_char_uuid:
                            break
                    # If not found, fallback to any writable char
                    if not chosen_char_uuid:
                        for svc in services:
                            for ch in getattr(svc, 'characteristics', []):
                                props = getattr(ch, 'properties', []) or []
                                if 'write' in props or 'write-without-response' in props:
                                    chosen_char_uuid = ch.uuid
                                    break
                            if chosen_char_uuid:
                                break

                # Finalize selection
                self.client = client
                self.char_uuid = chosen_char_uuid or COMMAND_CHAR_UUID
                print(f"DEBUG: using char {self.char_uuid}", file=sys.stderr, flush=True)
                self.connected = True
                return True
            except Exception:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                raise

    async def disconnect(self):
        async with self._lock:
            if self.client and self.connected:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
            self.client = None
            self.char_uuid = None
            self.connected = False

    async def send(self, payload: bytes, require_response: bool = False):
        async with self._lock:
            if not (self.client and self.connected and self.char_uuid):
                raise RuntimeError("Not connected")
            await self.client.write_gatt_char(self.char_uuid, payload, response=require_response)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ardubotr4 BLE Controller")

        # Asyncio loop in background thread
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()

        self.ble = BLEController(self.loop)

        self.status_var = tk.StringVar(value="Not connected")

        self._build_ui()

        # try to auto-connect
        self._schedule_coroutine(self._connect_and_update())

        # handle close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        # set a custom exception handler to capture unhandled exceptions in background tasks
        def _loop_exception_handler(loop, context):
            try:
                msg = context.get('message') or ''
                exc = context.get('exception')
                with open('main_error.log', 'a', encoding='utf-8') as fh:
                    fh.write('Loop exception: ' + str(msg) + '\n')
                    if exc is not None:
                        fh.write('\n'.join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
                    else:
                        fh.write(str(context) + '\n')
                print('Logged loop exception to main_error.log', file=sys.stderr)
            except Exception:
                pass

        self.loop.set_exception_handler(_loop_exception_handler)
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    def _schedule_coroutine(self, coro):
        # Schedule coroutine on background loop and return future
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        # attach done callback to log exceptions from the future
        def _on_done(f: Future):
            try:
                exc = f.exception()
            except Exception:
                exc = None
            if exc is not None:
                try:
                    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                    with open('main_error.log', 'a', encoding='utf-8') as fh:
                        fh.write('Task exception:\n')
                        fh.write(tb)
                    print('Task exception logged to main_error.log', file=sys.stderr)
                except Exception:
                    pass
        try:
            fut.add_done_callback(_on_done)
        except Exception:
            pass
        return fut

    async def _connect_and_update(self):
        self._set_status("Scanning for %s..." % DEVICE_NAME)
        try:
            ok = await self.ble.scan_and_connect(DEVICE_NAME, timeout=5.0)
            if ok:
                self._set_status(f"Connected to {DEVICE_NAME}")
            else:
                self._set_status(f"Device '{DEVICE_NAME}' not found or no writable char")
        except Exception as e:
            self._set_status(f"Connection error: {e}")

    def _set_status(self, txt: str):
        def _update():
            self.status_var.set(txt)
        # pass callable directly (no args)
        self.root.after(0, _update)

    def _build_ui(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack()

        status_label = tk.Label(frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        btn_forward = tk.Button(frame, text="Forward", width=12, command=lambda: self.on_button("forward"))
        btn_back = tk.Button(frame, text="Back", width=12, command=lambda: self.on_button("back"))
        btn_left = tk.Button(frame, text="Left", width=12, command=lambda: self.on_button("left"))
        btn_right = tk.Button(frame, text="Right", width=12, command=lambda: self.on_button("right"))
        btn_switch = tk.Button(frame, text="Switch", width=12, command=lambda: self.on_button("switch"))

        # Arrange control pad without mode selector row
        btn_forward.grid(row=1, column=1, pady=5)
        btn_left.grid(row=2, column=0, padx=5, pady=5)
        btn_switch.grid(row=2, column=1, padx=5, pady=5)
        btn_right.grid(row=2, column=2, padx=5, pady=5)
        btn_back.grid(row=3, column=1, pady=5)

        # Extra control buttons
        conn_frame = tk.Frame(self.root)
        conn_frame.pack(pady=(5, 10))
        btn_connect = tk.Button(conn_frame, text="Reconnect", command=lambda: self._schedule_coroutine(self._connect_and_update()))
        btn_disconnect = tk.Button(conn_frame, text="Disconnect", command=lambda: self._schedule_coroutine(self.ble.disconnect()))
        # use literal side string to satisfy type-checkers
        btn_connect.pack(side="left", padx=5)
        btn_disconnect.pack(side="left", padx=5)

    def on_button(self, name: str):
        base = COMMANDS.get(name)
        if not base:
            messagebox.showerror("Error", f"Unknown command: {name}")
            return
        # Build payload: plain text command (no newline)
        payload = base.encode("utf-8")

        future = self._schedule_coroutine(self._send_command(payload))

        def _on_done(fut):
            try:
                res = fut.result()
            except Exception as e:
                self._set_status(f"Send error: {e}")
        future.add_done_callback(_on_done)

    async def _send_command(self, payload: bytes):
        if not self.ble.connected:
            # try to connect first
            ok = False
            try:
                ok = await self.ble.scan_and_connect(DEVICE_NAME, timeout=5.0)
            except Exception as e:
                self._set_status(f"Connection error: {e}")
                raise

            if not ok:
                self._set_status(f"Device '{DEVICE_NAME}' not found")
                raise RuntimeError("Device not connected")

        try:
            await self.ble.send(payload, require_response=REQUIRE_RESPONSE_ON_WRITE)
            shown = payload.decode('utf-8', errors='replace')
            self._set_status(f"Sent: {shown}")
        except Exception as e:
            self._set_status(f"Send failed: {e}")
            raise

    def on_close(self):
        # schedule disconnect and stop loop
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            try:
                fut = self._schedule_coroutine(self.ble.disconnect())
                fut.result(timeout=3)
            except Exception:
                pass
            # stop loop: pass callable directly
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.root.destroy()


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    # allow CTRL+C in console
    if sys.platform.startswith("win"):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        main()
    except RecursionError as e:
        # write full traceback to a file for diagnosis
        tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        with open('main_error.log', 'w', encoding='utf-8') as fh:
            fh.write('RecursionError:')
            fh.write('\n')
            fh.write(tb)
        print('RecursionError captured to main_error.log', file=sys.stderr)
        raise
    except Exception as e:
        tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        with open('main_error.log', 'w', encoding='utf-8') as fh:
            fh.write('Unhandled exception:')
            fh.write('\n')
            fh.write(tb)
        print('Exception captured to main_error.log', file=sys.stderr)
        raise
