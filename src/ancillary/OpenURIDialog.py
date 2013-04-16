"""Modal dialog to prompt for a URI to open."""

from Tkinter import *
import tktools



class OpenURIDialog:
    __lasturi = ''

    def __init__(self, master, title=None, new=1):
        # create widgets
        self.__frame = tktools.make_toplevel(
            master, title=title or "Open Location Dialog")
        #
        fr, top, btnframe = tktools.make_double_frame(
            self.__frame, relief=FLAT)
        #
        self.__entry, frame, label = tktools.make_labeled_form_entry(
            top, 'URI:', 40)
        self.__entry.insert(0, self.__lasturi)
        #
        okbtn = Button(btnframe, text='Open', command=self.okaycmd)
        newbtn = Button(btnframe, text='New', command=self.newcmd)
        clearbtn = Button(btnframe, text='Clear', command=self.clearcmd)
        cancelbtn = Button(btnframe, text='Cancel', command=self.cancelcmd)
        tktools.unify_button_widths(okbtn, newbtn, clearbtn, cancelbtn)
        #
        okbtn.pack(side=LEFT)
        if new:
            newbtn.pack(side=LEFT, padx='1m')
        cancelbtn.pack(side=RIGHT)
        clearbtn.pack(side=RIGHT, padx='1m')
        #
        tktools.set_transient(self.__frame, master)
        #
        self.__entry.bind('<Return>', self.okaycmd)
        self.__entry.bind('<Control-C>', self.cancelcmd)
        self.__entry.bind('<Control-c>', self.cancelcmd)
        if new:
            self.__frame.bind('<Alt-n>', self.newcmd)
            self.__frame.bind('<Alt-N>', self.newcmd)
        self.__frame.bind("<Alt-w>", self.cancelcmd)
        self.__frame.bind("<Alt-W>", self.cancelcmd)
        #
        self.__frame.protocol('WM_DELETE_WINDOW', self.cancelcmd)

    def go(self):
        focuswin = self.__entry.focus_get()
        self.__frame.grab_set()
        self.__entry.focus_set()
        self.__frame.mainloop()
        self.__frame.grab_release()
        focuswin.focus_set()
        self.__frame.destroy()
        if self.__uri:
            self.__uri = ''.join(self.__uri.split())
            self.__class__.__lasturi = self.__uri
        return self.__uri, self.__new

    def okaycmd(self, event=None):
        self.__uri = self.__entry.get()
        self.__new = 0
        self.__frame.quit()

    def newcmd(self, event=None):
        self.__uri = self.__entry.get()
        self.__new = 1
        self.__frame.quit()

    def clearcmd(self, event=None):
        self.__entry.delete(0, END)

    def cancelcmd(self, event=None):
        self.__uri = None
        self.__new = 0
        self.__frame.quit()
