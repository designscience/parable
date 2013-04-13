#!/usr/bin/python

"""
__version__ = "$Revision: 1.10 $"
__date__ = "$Date: 2004/04/24 22:13:31 $"
"""

from PythonCard import model

class parablew(model.Background):
    def __init__(self, aParent, aBgRsrc):
        model.Background.__init__(self, aParent, aBgRsrc)
        self.appstr = "howdy"

    def hello(self, hellostr):
        self.hell0s = hellstr

    def on_btnHello_mouseClick(self, event):
        print self.appstr


if __name__ == '__main__':
    app = model.Application(parablew)
    app.MainLoop()
