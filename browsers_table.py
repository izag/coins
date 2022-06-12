import asyncio
import json
import os.path
import re
import time
from threading import Thread
from tkinter import *
from tkinter.ttk import *
from typing import Any

import pythoncom
import tornado.escape
import tornado.locks
import tornado.web
import wmi
from tornado import httputil
from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

model = []
processes = {}
root = Tk()
cache = {}


class App(Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.treeview = Treeview(self)
        self.treeview['columns'] = ('process_id', 'ip', 'process_name', 'parent_id', 'time')
        self.treeview.heading("#0", text='Serial', anchor='w')
        self.treeview.column("#0", anchor="w")
        self.treeview.heading('process_id', text='PID')
        self.treeview.column('process_id', anchor='center', width=100)
        self.treeview.heading('ip', text='IP')
        self.treeview.column('ip', anchor='center', width=100)
        self.treeview.heading('process_name', text='Process Name')
        self.treeview.column('process_name', anchor='center', width=100)
        self.treeview.heading('parent_id', text='Parent PID')
        self.treeview.column('parent_id', anchor='center', width=100)
        self.treeview.heading('time', text='Time')
        self.treeview.column('time', anchor='center', width=100)
        self.treeview.grid(sticky=(N, S, W, E))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid(sticky=(N, S, W, E))
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        self.update()

    def update(self):
        selected = self.treeview.selection()

        for i in self.treeview.get_children():
            self.treeview.delete(i)
        for row in list(model):
            serial = row[0]
            self.treeview.insert('', 'end', iid=serial, text=str(serial), values=row[1:])

        self.treeview.selection_set([iid for iid in selected if self.treeview.exists(iid)])

        root.update_idletasks()
        root.after(1000, self.update)


class Filler(Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        global processes
        pythoncom.CoInitialize()
        while True:
            f = wmi.WMI()
            tmp = {}
            for process in f.Win32_Process(Name="SunBrowser.exe"):
                tmp[process.ProcessId] = process
            processes = tmp
            time.sleep(5)


class Printer(Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        global model
        while True:
            # print("Browsers >")
            tmp = []
            for pid, process in list(processes.items()):
                if process.ParentProcessId in processes:
                    continue

                m = re.search("acc_id=(\d+)", process.CommandLine)
                browser_id = int(m.group(1))

                m = re.search("ip=([\d\.]+)", process.CommandLine)
                ip = m.group(1)

                # print(f"{process.Name} {process.ParentProcessId} {process.ProcessId} {browser_id} {ip}")
                tmp.append((browser_id, process.ProcessId, ip, process.Name, process.ParentProcessId, cache.get(ip, "")))

            # print()
            tmp.sort()
            model = tmp
            time.sleep(1)


class JSONHandler(tornado.web.RequestHandler):
    def __init__(
            self,
            application: "Application",
            request: httputil.HTTPServerRequest,
            **kwargs: Any
    ):
        super().__init__(application, request, **kwargs)
        self.json_args = None

    def prepare(self):
        if self.request.headers.get("Content-Type", "").startswith("text/plain"):
            self.json_args = json.loads(self.request.body)

    def post(self):
        if self.json_args is None:
            self.write(dict(result="error"))
            return

        cache[self.json_args["ip"]] = self.json_args["time"]
        self.write(dict(result="ok"))


async def main():
    parse_command_line()
    app = tornado.web.Application(
        [
            (r"/browsers", JSONHandler)
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        debug=options.debug,
    )
    app.listen(options.port)
    await asyncio.Event().wait()


class Server(Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())


if __name__ == "__main__":
    Server().start()
    Filler().start()
    Printer().start()
    App(root)
    root.mainloop()
