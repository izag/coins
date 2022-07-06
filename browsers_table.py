import asyncio
import json
import os.path
import random
import re
import signal
import time
from threading import Thread
from tkinter import *
from tkinter.ttk import *
from typing import Any

import pythoncom
import pywintypes
import tornado.escape
import tornado.locks
import tornado.web
import win32con
import win32gui
import win32process
import wmi
from pywinauto import Application
from tornado import httputil
from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

lower_bound = 20000

model = []
processes = {}
root = Tk()
cache = {}
sort_idx = 0
is_reversed = False


# TODO:
# 1. Coloring
# 2. Use SQL DB
# 3. Sort rows
# 4. Input IP
# 5. https://numbergenerator.org/randomnumbergenerator/
class App(Frame):
    def __init__(self, parent):
        super().__init__(parent)

        parent.title("Локальные браузеры")

        s = Style()
        s.configure('Treeview.Heading', rowheight=30)
        s.configure('Treeview', rowheight=30)

        tree_frame = Frame(self)
        tree_scroll = Scrollbar(tree_frame)
        tree_scroll.pack(side=RIGHT, fill=Y)

        r = 0
        self.treeview = Treeview(tree_frame, yscrollcommand=tree_scroll.set, selectmode=BROWSE)
        self.treeview['columns'] = ('process_id', 'ip', 'process_name', 'parent_id', 'position')
        self.treeview.heading("#0", text='Serial', anchor='w', command=lambda: self.treeview_sort_column(0, False))
        self.treeview.column("#0", anchor="w")
        self.treeview.heading('process_id', text='PID')
        self.treeview.column('process_id', anchor='center', width=100)
        self.treeview.heading('ip', text='IP')
        self.treeview.column('ip', anchor='center', width=100)
        self.treeview.heading('process_name', text='Process Name')
        self.treeview.column('process_name', anchor='center', width=100)
        self.treeview.heading('parent_id', text='Parent PID')
        self.treeview.column('parent_id', anchor='center', width=100)
        self.treeview.heading('position', text='Position')
        self.treeview.column('position', anchor='center', width=100)

        idx = 0
        for col in self.treeview['columns']:
            idx += 1
            self.treeview.heading(col, command=lambda i=idx: self.treeview_sort_column(i, False))

        self.treeview.tag_configure('upper', background="white")
        self.treeview.tag_configure('lower', background="lightblue")

        self.treeview.bind('<ButtonRelease-1>', self.on_select)

        tree_scroll.config(command=self.treeview.yview)

        self.treeview.pack(expand=True, fill=BOTH)
        tree_frame.grid(row=r, column=0, columnspan=2, sticky=NSEW)

        r += 1
        Label(self, text='Значение очереди', anchor=E).grid(row=r, column=0, sticky=EW)

        self.sv_threshold = StringVar()
        self.entry_threshold = Entry(self, textvariable=self.sv_threshold, width=40)
        self.entry_threshold.grid(row=r, column=1, sticky=EW)
        self.sv_threshold.trace('w', self.on_threshold_change)

        r += 1
        # self.btn_activate = Button(self, text="Activate",
        #                            command=self.activate_browser)
        # self.btn_activate.grid(row=r, column=0, sticky=EW)

        self.btn_close = Button(self, text="Close", command=self.close_browser)
        self.btn_close.grid(row=r, column=1, sticky=EW)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        self.grid(sticky=NSEW)
        self.update()

    def update(self):
        selected = self.treeview.selection()

        for i in self.treeview.get_children():
            self.treeview.delete(i)
        for row in list(model):
            serial = row[0]
            position = row[5]
            tags = ('lower',)
            if position < lower_bound:
                tags = ('upper',)
            self.treeview.insert('', 'end', iid=serial, text=str(serial), values=row[1:], tags=tags)

        self.treeview.selection_set([iid for iid in selected if self.treeview.exists(iid)])

        root.update_idletasks()
        root.after(1000, self.update)

    def on_threshold_change(self, *args):
        global lower_bound
        s = self.sv_threshold.get()
        lower_bound = int(s) if s.isdigit() else 0

    def close_browser(self):
        selected = self.treeview.selection()
        for iid in selected:
            values = self.treeview.item(iid, 'values')
            pid = int(values[0])
            os.kill(pid, signal.SIGTERM)

    def activate_browser(self):
        selected = self.treeview.selection()
        if len(selected) == 0:
            return

        iid = selected[0]
        values = self.treeview.item(iid, 'values')
        pid = int(values[0])
        app = Application().connect(process=pid)
        app.top_window().set_focus()

    def on_select(self, event):
        iid = self.treeview.identify('item', event.x, event.y)
        values = self.treeview.item(iid, 'values')
        if len(values) == 0:
            return

        pid = int(values[0])
        hwnd = find_window_for_pid(pid)
        if hwnd is None:
            return

        win32gui.SetForegroundWindow(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)

    def treeview_sort_column(self, idx, reverse):
        global sort_idx
        global is_reversed

        sort_idx = idx
        is_reversed = reverse

        if idx == 0:
            col = "#0"
            # l = [(self.treeview.item(k)["text"], k) for k in self.treeview.get_children('')]
        else:
            col = self.treeview['columns'][idx - 1]
            # l = [(self.treeview.set(k, col), k) for k in self.treeview.get_children('')]
        # l.sort(reverse=reverse)
        #
        # # rearrange items in sorted positions
        # for index, (val, k) in enumerate(l):
        #     self.treeview.move(k, '', index)

        # reverse sort next time
        self.treeview.heading(col, command=lambda: self.treeview_sort_column(idx, not reverse))


def find_window_for_pid(pid):
    result = None

    def callback(hwnd, _):
        nonlocal result
        ctid, cpid = win32process.GetWindowThreadProcessId(hwnd)
        if cpid == pid:
            result = hwnd
            return False
        return True

    try:
        win32gui.EnumWindows(callback, None)
    except pywintypes.error:
        pass
    return result


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
            tmp = []
            for pid, process in list(processes.items()):
                if process.ParentProcessId in processes:
                    continue

                if process.CommandLine is None:
                    continue

                m = re.search("acc_id=(\d+)", process.CommandLine)
                browser_id = int(m.group(1))

                m = re.search("ip=([\d\.]+)", process.CommandLine)
                ip = m.group(1)

                tmp.append((browser_id, process.ProcessId, ip, process.Name, process.ParentProcessId, cache.get(ip, 0)))
                # tmp.append((browser_id, process.ProcessId, ip, process.Name, process.ParentProcessId,
                #             random.randrange(1, 50000)))

            tmp.sort(key=lambda t: t[sort_idx], reverse=is_reversed)
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

        position = self.json_args["position"]
        cache[self.json_args["ip"]] = int(position) if position.isdigit() else 0
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
