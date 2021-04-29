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
with open(os.path.join(diri, "g3mclass", "welcome.html"), "r") as fp:
    welc_text=fp.read() % {"me": me};
welc_text=re.sub("\n\n", "<br>\n", welc_text);
with open(os.path.join(diri, "g3mclass", "licence_en.txt"), "r") as fp:
    licenseText=fp.read();

## global vars
gui=wx.Object();
dogui=False;
fdata=""; # name of data file
data=None;
dcols={};
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
    if not fdata:
        # data is not yet choosed
        err_mes("no data yet chosen.\nRead a data file first.");
        return;
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
def err_mes(mes):
    "Show error dialog in GUI mode or raise exception"
    if dogui:
        dlg=wx.MessageDialog(None, mes, "Error", wx.OK | wx.ICON_ERROR);
        dlg.ShowModal()
        dlg.Destroy();
    else:
        raise Exception(me+": "+mes);
## working functions
def file2data(fn):
    "Read file name 'fn' intto data.frame"
    global data, dcols;
    try:
        data=pa.read_csv(fn, header=None, sep="\t");
    except:
        err_mes("file '"+fn+"' could not be read");
        return;
    cols=[str(v).strip() if v==v else "" for v in data.iloc[0, :]];
    # search for (ref) and (test)
    dcols={} # reinit
    suff=" (ref)";
    dcols["inm"]=dict((i, re.sub(tls.escape(suff, "()")+"$", "", v).strip()) for i,v in enumerate(cols) if v.endswith(suff))
    if not dcols["inm"]:
        err_mes("not found '"+suff+"' in column names");
        return;
    # check that varnames are unique and non empty
    cnt=tls.list2count(dcols["inm"].values());
    if len(cnt) != len(dcols["inm"]):
        vbad=[v for v,i in cnt.items() if i > 1];
        err_mes("following column name is not unique in ' (ref)' set: '"+vbad[0]+"'");
        return;
    # check that every ref has its test pair
    for ir in dcols["inm"].keys():
        nm=dcols["inm"][ir];
        itest=[i for i,v in enumerate(cols) if v.startswith(nm) and v.endswith(" (test)") and re.match("^ *$", v[len(nm):-7])]
        if not itest:
            err_mes("column '"+nm+" (ref)' has not its counter part '"+nm+" (test)'");
            return;
        elif len(itest) > 1:
            err_mes("following column name is not unique in '( test)' set: '"+nm+"'");
            return;
        else:
            dcols["inm"][ir]=(nm,itest[0]);
        # get query (if any)
        dqry=dict((i,v[len(nm)+1:].strip()) for i,v in enumerate(cols) if v.startswith(nm+" ") and not v.endswith(" (test)") and not v.endswith(" (ref)"));
        # check that qry names are unique
        cnt=tls.list2count(dqry.values());
        if len(cnt) < len(dqry):
            err_mes("following column name is not unique in ' (query)' set: '"+nm+" "+[v for v,i in cnt.items() if i > 1][0]+"'");
            return;
        dcols["inm"][ir]=(*dcols["inm"][ir], dqry);
        
    
    tls.aff("dcols", dcols);
    data.columns=cols
    data=data.iloc[1:,:]
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
        opts,args=getopt.getopt(sys.argv[1:], "hwv", ["help", "DEBUG"]);
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
            return(0);
        elif o=="--DEBUG":
            DEBUG=True;
        elif o=="-v":
            print(me+": "+version);
            return(0);
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
