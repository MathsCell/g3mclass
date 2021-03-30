#!/usr/bin/env python3
"""g3mclass.py is Gaussian Mixture Models for Marker Classification

usage: g3mclass.py [-h|--help] [--DEBUG] [-w] [data[.tsv]]
"""
#Todo:
# - data parsing
# - test and query classification
# - plots
# - write results
# - GUI
# - doc
# - packaging

# 2021-03-19 sokol
# Copyright 2021, INRAE/INSA/CNRS, Marina GUVAKOVA

# This file content:
# -imports
# -custom classess
# -config constants
# -global vars
# -call-backs defs
# -working functions
# -line arguments parse
# -GUI layout (from *_lay.kvh)

## imports
import sys;
import os;
import getopt;
import re;

import wx;
import wx.adv;
import wx.html;
import wx.grid as wxg;
from wx.lib.wordwrap import wordwrap;
import wx.lib.floatcanvas.FloatCanvas as wxfc;

import pandas as pa;

import webbrowser;

import g3mclass
dirx=os.path.dirname(os.path.abspath(sys.argv[0])); # execution dir
diri=os.path.dirname(os.path.abspath(g3mclass.__file__)); # install dir
import tools_ssg as tls;

## custom classes
class data2tab(wxg.GridTableBase):
    def __init__(self, data):
        wxg.GridTableBase.__init__(self);
        self.data=data;
    def GetNumberRows(self):
        return(self.data.shape[0]);
    def GetNumberCols(self):
        return(self.data.shape[1]);
    def IsEmptyCell(self, row, col):
        v=self.data.iloc[row, col];
        return v != v;
    def GetValue(self, row, col):
        v=self.data.iloc[row, col];
        return(v if v == v else "");
        #return(self.data[row, col]);
    def SetValue(self, row, col, value):
        pass;
    def GetColLabelValue(self, col):
        return self.data.columns[col] if len(self.data) else None;

## config constants
with open(os.path.join(diri, "g3mclass", "version.txt"), "r") as fp:
    version=fp.read()
# program name
#me=os.path.basename(sys.argv[0]);
me="G3Mclass";
# message in welcome tab
welc_text="""
<html>
<h1>Welcome to <tt>%(me)s</tt>!</h1>

<p>
<b><tt>%(me)s</tt></b> is a software for Gaussian Mixture Model for Marker Classification.
</p>

<h3>Usage:</h3>
<ol>
<li>Open a data file: <i>File > Open > ...</i>(choose some file, let call it <tt>data.tsv</tt>)

<tt>data.tsv</tt> must contain duplicate or triplicate columns relative to some biomedical markers. If we have a marker 'geneA'
then we should have following columns: <tt>geneA (ref)</tt>, <tt>geneA (test)</tt> and optionally <tt>geneB (query)</tt>.
The first column <tt>geneA (ref)</tt> contains blablabla ... </li>

<li>Data from columns <tt>(test)</tt> are used to learn Gaussian mixtures, one mixture per marker.</li>

<li>Data from columns <tt>(test)</tt> and <tt>(query)</tt> (if present) are automatically classified with detection of multiple cut-offs.
The classification results can be examined in tabs <i>Plots</i> and <i>Results</i></li>

<li>If results are satisfactory, they can be saved in a TSV file (<i>File > Save results</i>)</li>
</ol>

<p>
For legal information see <i>Help > About</i>
</p>
</html>
""" % {"me": me};
welc_text=re.sub("\n\n", "<br>\n", welc_text);
with open(os.path.join(diri, "g3mclass", "licence_en.txt"), "r") as fp:
    licenseText=fp.read();

## global vars
gui=wx.Object();
dogui=False;
fdata=""; # name of data file
data=None;
settings={
    "param1": 10,
    "param2": 10,
};
canvas=None; # plotting canvas
sett_inp=None; # dictionary of input widgets for settings
wd=""; # working dir
## call back functions
def OnExit(evt):
    """
    This is executed when the user clicks the 'Exit' option
    under the 'File' menu or close the window.  We ask the user if he *really*
    want to exit, then close everything down if he does.
    """
    global fdata;
    if not fdata:
        gui.mainframe.Destroy();
        return
    dlg = wx.MessageDialog(None, 'Exit %(me)s?'%{"me": me}, 'Choose Yes or No!',
                          wx.YES_NO | wx.ICON_QUESTION);
    if dlg.ShowModal() == wx.ID_YES:
        dlg.Destroy();
        gui.mainframe.Destroy();
    else:
        dlg.Destroy();
def OnOpen(evt):
    """
    This is executed when the user clicks the 'Open' option
    under the 'File' menu.  We ask the user to choose a TSV file.
    """
    global fdata
    dlg = wx.FileDialog(None, defaultDir=wd, wildcard="Data files (*.tsv)|*.tsv|Data files (*.csv)|*.csv",
        style=wx.FD_OPEN);
    if dlg.ShowModal() == wx.ID_OK:
        #print "selected file="+dlg.GetPath();
        # proceed the data file
        fdata=dlg.GetPath()
        file2data(fdata);
        gui.nb.SetSelection(lab2ip(gui.nb, "Data")[0]);
        gui.mainframe.SetStatusText("'%s' is read"%os.path.basename(fdata))
    # do smth
    dlg.Destroy();

def OnSave(evt):
    """
    This is executed when the user clicks the 'Save results' option
    under the 'File' menu. Results are stored in data_res.tsv.
    """
    global fdata;
    win=evt.GetEventObject();
    win=win.GetWindow();
    with wx.FileDialog(win, "Save TSV file", wildcard="TSV files (*.tsv)|*.tsv", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return # the user changed their mind

        # save the current contents in the file
        fpath = fileDialog.GetPath()
        try:
            res2file(data, fpath);
            gui.mainframe.SetStatusText("Written '"+os.path.basename(fpath)+"'");
        except IOError:
            wx.LogError("Cannot save results in file '%s'." % fpath)
    if False:
        if not fdata:
            # data is not yet choosed
            dlg=wx.MessageDialog(None, "No data yet chosen.\nChoose a data file first.", 'Error', wx.OK | 
                wx.ICON_ERROR);
            dlg.ShowModal();
            dlg.Destroy();
            return;
        # file name
        fn=re.sub("\.tsv$", "", fdata)+"_res.tsv";
        fpath=os.path.join(wd, fn);

def OnAbout(evt):
    "show about dialog"
    win=evt.GetEventObject();
    win=win.GetWindow();
    info = wx.adv.AboutDialogInfo();
    info.SetName(me);
    info.SetVersion(version);
    info.SetCopyright("(C) 2021 INRAE/INSA/CNRS, Marina Guvakova");
    info.SetDescription(wordwrap(
        "g3mclass is Gaussian Mixture Model for Marker Classification"
        " It reads data and writes classification results form and to TSV files",
        350, wx.ClientDC(win)));
    info.SetWebSite("https://pypi.org/project/g3mclass");
    info.AddDeveloper("Serguei SOKOL");
    info.AddDeveloper("Marina GUVAKOVA");

    info.SetLicense(wordwrap(licenseText, 500, wx.ClientDC(win)));

    # Then we call wx.AboutBox giving it that info object
    wx.adv.AboutBox(info);

def OnLinkClicked(evt):
    webbrowser.open_new_tab(evt.GetLinkInfo().Href);

def OnSize(evt):
    "main window is resized"
    win=evt.GetEventObject();
    sz=evt.GetSize();
    win.SetSize(sz);
    evt.Skip();
    return;

def ToDo(evt):
    """
    A general purpose "we'll do it later" dialog box
    """
    win=evt.GetEventObject().GetTopLevelParent();
    dlg = wx.MessageDialog(win, "Not Yet Implimented! evt="+str(dir(evt)), "ToDo",
                         wx.OK | wx.ICON_INFORMATION);
    dlg.ShowModal();
    dlg.Destroy();

## working functions
def file2data(fn):
    "Read file name 'fn' intto data.frame"
    global data;
    try:
        data=pa.read_csv(fn, sep="\t")
    except:
        if dogui:
            dlg=wx.MessageDialog(None, "File "+fn+" could not be read\nChoose another TSV file", "Error", wx.OK | wx.ICON_ERROR);
            if dlg.ShowModal() == wx.ID_OK:
                dlg.Destroy();
        else:
            pass;
    data.columns=[v if not v[:9] == "Unnamed: " else "" for v in data.columns];
    ## create and fill the data table
    if dogui:
        if "grid" in dir(gui.sw_data):
            # destroy the previous grid
            gui.sw_data.grid.Destroy();
        # create new one
        grid=wxg.Grid(gui.sw_data, wx.ID_ANY);
        gui.sw_data.grid=grid;
        grid.table=data2tab(data);
        grid.SetTable(grid.table, True);
        grid.Fit();
        gui.sw_data.SetVirtualSize(grid.GetSize());
def res2file(res, fpath=None):
    if fpath == None:
        if fdata:
            fpath=os.path.join(wd, re.sub("\.tsv", "", fdata)+"_res.tsv");
        else:
            raise Exception("fpath is not set for writing");
    tls.obj2kvh(res, "res", fpath);

def s2ftime(s=0.):
    """s2ftime(s=0) -> String
    Format second number as hh:mm:ss.cc
    """
    si=int(s);
    cc=round(100*(s-si), 0);
    s=si;
    ss=s%60;
    s//=60;
    mm=s%60;
    s//=60;
    hh=s;
    return("%02d:%02d:%02d.%02d"%(hh,mm,ss,cc));

def lab2ip(nb, lab):
    """lab2i(nb, nm) -> (i,Page) or (None,None)
    get page of a notebook nb by its label lab
    """
    for i in range(nb.GetPageCount()):
        if lab == nb.GetPageText(i):
            return((i,gui.nb.GetPage(i)));
    return((None,None));

def sett2wx(win):
    "create input wx widgets for settings in the window win"
    global sett_inp;
    gs=wx.FlexGridSizer(0, 2, 2, 2)  # rows=len(settings), cols, vgap, hgap;
    panel=wx.Panel(win, wx.ID_ANY);
    # create widgets and add them to the sizer
    gs.AddSpacer(10);
    gs.AddSpacer(10);
    sett_inp={};
    for (k,v) in list(settings.items()):
        #print("set k=", k);
        gs.Add(wx.StaticText(panel, wx.ID_ANY, k), 0, wx.EXPAND, 5);
        inp=wx.TextCtrl(panel, wx.ID_ANY, str(v), size=(125, -1));
        inp.Bind(wx.EVT_TEXT, OnSettings);
        inp.set_field=k;
        gs.Add(inp, 0, wx.EXPAND, 5);
        sett_inp[k]=inp;
    gs.AddSpacer(10);
    gs.AddSpacer(10);
    panel.SetSizer(gs);
    panel.Fit();
    win.SetVirtualSize(panel.GetSize());
    #panel.Center(wx.HORIZONTAL);

def usage():
    print(__doc__);

def make_gui():
    "create GUI"
    global gui;
    gui=wx.Object();
    gui.app=wx.App();
    code=tls.wxlay2py(tls.kvh2tlist(os.path.join(diri, "g3mclass", "g3mclass_lay.kvh")), pref="gui.");
    exec(code);

## take arguments
def main():
    global fdata, wd, gui, dogui;
    try:
        opts,args=getopt.getopt(sys.argv[1:], "hw", ["help", "DEBUG"]);
    except getopt.GetoptError as err:
        print((str(err)));
        usage();
        sys.exit(1);
    DEBUG=False;
    dogui=True;
    write_res=False;
    for o,a in opts:
        if o in ("-h", "--help"):
            usage();
            sys.exit(0);
        elif o=="--DEBUG":
            DEBUG=True;
        elif o=="-w":
            dogui=False;
            write_res=True;
        else:
            assert False, "unhandled option";
    if dogui:
        make_gui();
    fdata=args[0] if len(args) else "";
    if fdata and fdata[-4:] != ".tsv":
        fdata+=".tsv";
    if fdata and not os.path.exists(fdata):
        raise Exception(me+": file '"+fdata+"' does not exist.\n");
    if fdata:
        file2data(fdata);
        wd=os.path.dirname(os.path.abspath(fdata));
        os.chdir(wd);
        fdata=os.path.basename(fdata);
        if dogui:
            gui.nb.SetSelection(lab2ip(gui.nb, "Data")[0]);
            gui.mainframe.SetStatusText("'%s' is read"%fdata)
    else:
        wd=os.path.abspath(os.getcwd());
    if fdata and write_res:
        res2file(data);
    if dogui:
        gui.app.MainLoop();

if __name__ == "__main__":
    main();
