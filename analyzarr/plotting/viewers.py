# -*- coding: utf-8 -*-

from single_plot import SinglePlot
from double_plot import DoubleImagePlot

class StackViewer(SinglePlot):
    def __init__(self, controller, *args, **kw):
        super(StackViewer, self).__init__(controller, *args,**kw)



