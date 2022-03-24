#!/usr/bin/env python3
"""g3mclass.py is Gaussian Mixture Models for Marker Classification

usage: g3mclass.py [-h|--help] [--DEBUG] [-w] [data[.tsv]]
"""
#Todo:
# + data parsing
# + test and query classification
# + plots
# + write results
# + GUI
# - doc
# - packaging

# 2021-03-19 sokol
# Copyright 2021, INRAE/INSA/CNRS, Marina GUVAKOVA

# This file content:
# -imports
# -custom classes
# -config constants
# -global vars
# -call-backs defs
# -working functions
# -line arguments parse
# -GUI layout (from *_lay.kvh)

## imports
import sys;
import os;
from pathlib import Path;
import io;
import getopt;
import re;
import itertools as itr;
import multiprocessing as mp;
import time;
import datetime;
import warnings;
import tempfile;
import zipfile;

try:
    import wx;
    import matplotlib as mpl;
    import numpy as np;
    import pandas as pa;
    import xlsxwriter;
except ModuleNotFoundError:
    import subprocess
    res=subprocess.run([sys.executable, "-m", "pip", "install", "--user", 'wxpython', 'numpy', 'pandas', 'matplotlib', 'xlsxwriter'], capture_output=True)
    print("res=", res)
    import wx;
    import matplotlib as mpl;
    import numpy as np;
    import pandas as pa;

import wx.grid;
import wx.adv;
import wx.html;
from wx.lib.wordwrap import wordwrap;
import wx.lib.mixins.inspection as wit;
import wx.lib.colourdb;
#from wx.lib.agw.flatnotebook import FlatNotebook as wx_nb;
wx_nb=wx.Notebook;

from matplotlib.backends.backend_wxagg import (
    FigureCanvasWxAgg as FigureCanvas,
    NavigationToolbar2WxAgg as NavigationToolbar);
from matplotlib.backends.backend_pdf import PdfPages as mpdf;
import matplotlib.pyplot as plt;

import numpy as np;
import pandas as pa;
import webbrowser;

import g3mclass
dirx=Path(sys.argv[0]).resolve().parent; # execution dir
diri=Path(g3mclass.__file__).resolve().parent; # install dir
import tools_g3m as tls;

# timeit
from time import strftime, localtime, process_time as tproc
globals()["_T0"]=tproc()
globals()["_T0w"]=time.time()
def timeme(s="", dig=2):
    "if a global variable TIMEME is True and another global variable _T0 is set, print current CPU time relative to _T0. This printing is preceded by a message from 's'"
    if TIMEME:
        if "_T0" in globals():
            print(s, ":\tCPU=", s2ftime(tproc()-_T0), "s", "\ttime=%s"%s2ftime(time.time()-_T0w), "s", sep="");
        else:
            globals()["_T0"]=tproc();
            globals()["_T0w"]=time.time();

TIMEME=False;

## custom classes
class wx_nbl(wx.Panel):
    "replace notebook with pages selected in a list"
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs);  # main container for list and pages
        self.lbox=wx.ListBox(self, style=wx.LB_SINGLE);
        self.lbox.Hide();
        self.Bind(wx.EVT_LISTBOX, self.OnLbox, self.lbox);
        self.panel=wx.Panel(self);
        #self.panel.SetPosition((0, self.lbox.GetSize()[1]));
        self.pages=[];
        sizer=wx.BoxSizer(wx.VERTICAL);
        sizer.Add(self.lbox, 0, wx.ALL | wx.ALIGN_CENTER, border=5);
        sizer.Add(self.panel, 1, wx.EXPAND);
        self.SetSizer(sizer);
        self.panel.Bind(wx.EVT_SIZE, self.OnSize);
        self.panel.SetBackgroundColour(bg_sys);
        self.Fit();
        w,h=self.GetSize();
        self.SetSize(w,h+1);
        self.SetSize(w,h);
    def OnLbox(self, evt):
        isel=self.lbox.GetSelection();
        w,h=self.GetSize();
        self.SetSize(w,h+1);
        self.SetSize(w,h);
        #print("lbox: selected", isel);
        #print("pos=", self.panel.GetPosition());
        #print("sz=", self.panel.GetSize());
        # update pos and size then hide
        [(pg.SetPosition(self.panel.GetPosition()), pg.SetSize(self.panel.GetSize()), pg.Hide()) for pg in self.pages];
        # show selected page
        self.pages[isel].Show();
    def AddPage(self, pg, nm):
        self.lbox.InsertItems([nm], self.lbox.Count);
        self.pages.append(pg);
        self.lbox.SetSelection(self.lbox.Count-1);
        self.lbox.Show();
        self.OnLbox(None);
    def OnSize(self, evt):
        evt.Skip();
        sz=self.panel.GetSize();
        [pg.SetSize(sz) for pg in self.pages];
    def GetPageCount(self):
        return self.lbox.Count;
    def DeletePage(self, i):
        if i < self.lbox.Count:
            self.pages[i].Destroy();
            del(self.pages[i]);
            self.lbox.Delete(i);
        if self.lbox.Count == 0:
            self.lbox.Hide();
class df2grid(wx.grid.Grid):
    def __init__(self, parent, df, *args, **kwargs):
        #import pdb; pdb.set_trace();
        global bg_grey;
        parent.df=df;
        self._grid=super(type(self), self);
        self._grid.__init__(parent, *args, **kwargs);
        nrow, ncol=df.shape;
        nmc=df.columns;
        # destroy previous grid
        if "grid" in dir(parent):
            parent.grid.Destroy();
        self.CreateGrid(nrow, ncol);
        self.EnableEditing(False);
        if bg_grey is None:
            bg_grey=self.GetLabelBackgroundColour();
        self.SetDefaultCellBackgroundColour(bg_sys);
        parent.grid=self;
        bg=wx.grid.GridCellAttr();
        bg.SetBackgroundColour(bg_sys);
        #import pdb; pdb.set_trace();
        for j in range(ncol):
            self.SetColLabelValue(j, str(nmc[j]));
            vcol=df.iloc[:,j].to_numpy();
            empty=np.all(tls.is_na(vcol)) or np.all(vcol.astype(str)=="");
            empty_end=tls.is_empty_end(vcol) | tls.is_na_end(vcol);
            if empty:
                self.SetColAttr(j, bg);
                bg.IncRef();
                continue;
            if vcol.dtype == float:
                vcol=np.round(vcol, 3);
            for k in range(nrow):
                if empty or empty_end[k]:
                    pass;
                    #self.SetCellBackgroundColour(k, j, bg_grey);
                    #break;
                    #self.SetCellValue(k, j, "");
                else:
                    #self.SetCellBackgroundColour(k, j, bg_null);
                    val=vcol[k];
                    val=str(val) if val == val else "";
                    self.SetCellValue(k, j, val);
        self.AutoSizeColumns(setAsMin=False);
        if not parent.GetSizer():
            parent.SetSizer(wx.BoxSizer(wx.VERTICAL));
        parent.GetSizer().Add(self, 1, wx.EXPAND);
class wx_FloatSlider(wx.Slider):
    def __init__(self, parent, value=0, minValue=0., maxValue=1., scale=100, frmt="%.2f", **kwargs):
        self._value = value;
        self._min = minValue;
        self._max = maxValue;
        self._scale = scale;
        ival, imin, imax = [round(v*scale) for v in (value, minValue, maxValue)];
        self.frmt=frmt;
        self._islider = super(type(self), self);
        #pnl=wx.Panel(parent, -1);
        pnl=parent;
        self._islider.__init__(pnl, value=ival, minValue=imin, maxValue=imax, **kwargs);
        self.Bind(wx.EVT_SLIDER, self._OnSlider);
        self.txt = wx.StaticText(pnl, label=self.frmt%self._value, style = wx.ALIGN_RIGHT);
        self.hbox = wx.BoxSizer(wx.HORIZONTAL);
        self.hbox.Add(self.txt, 0, wx.ALIGN_CENTRE_VERTICAL | wx.ALL, border=10);
        self.hbox.Add(self, 1, wx.ALIGN_CENTRE_VERTICAL | wx.ALL, border=10);
        #import pdb; pdb.set_trace();
        #pnl.SetSizer(hbox);
    def _OnSlider(self, event):
        #import pdb; pdb.set_trace()
        #print("event=", event);
        ival = self._islider.GetValue();
        imin = self._islider.GetMin();
        imax = self._islider.GetMax();
        if ival == imin:
            self._value = self._min;
        elif ival == imax:
            self._value = self._max;
        else:
            self._value = ival / self._scale;
        if self._scale <= 1:
            self._value=int(self._value);
        self.txt.SetLabel(self.frmt%self._value);
        #print("ival=", ival);
        #print("_val=", self._value);
    def GetSizer(self):
        return self.hbox;
    def GetValue(self):
        return self._value;
    def SetValue(self, val):
        self._islider.SetValue(round(val*self._scale));
        self._value=val;
        if self._scale <= 1:
            self._value=int(self._value);
        self.txt.SetLabel(self.frmt%self._value);
class wx_ColourPickerCtrl(wx.ColourPickerCtrl):
    def __init__(self, *args, label="", label_size=wx.DefaultSize, **kwargs):
        wx.ColourPickerCtrl.__init__(self, *args, **kwargs);
        self.hbox=wx.BoxSizer(wx.HORIZONTAL);
        self.label=wx.StaticText(args[0], label=label, style=wx.ALIGN_LEFT, size=label_size);
        if label_size != wx.DefaultSize:
            self.label.Wrap(label_size[0]);
        self.hbox.Add(self.label, 0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border = 5);
        self.hbox.Add(self, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5);
## config constants
with (diri/"version.txt").open() as fp:
    version=fp.read().strip();
# program name
me="g3mclass";
# message in welcome tab
with (diri/"welcome.html").open() as fp:
    welc_text=fp.read();
welc_text=re.sub("\n\n", "<br>\n", welc_text);
with (diri/"licence_en.txt").open() as fp:
    licenseText=fp.read();

## global vars
LOCAL_TIMEZONE=datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo;
nan=np.nan;
Inf=np.inf;
nproc=os.cpu_count();
gui=wx.Object();
dogui=False;
fdata=""; # name of data file
data=None;
model=None;
classif=None;
ids=None;
prev_res_saved=True;
prev_par_saved=True;
dcols={};
resdf=None; # dict for formatted output in .tsv
par_mod={
    "k": 25,
    "k_hlen": 3,
    "k_var": True,
    "thr_di": 0.5,
    "thr_w": 1.,
};
par_plot={
    "hcl_proba": True,
    "hcl_cutoff": True,
    "hcl_scutoff": True,
    "col_hist": "black",
    "col_panel": "white",
    "col_tot": "grey",
    "col_ref": "seagreen",
    "col_neglow": "lightskyblue",
    "col_neghigh": "#0061ff",
    "col_poslow": "#e7c4d3",
    "col_poshigh": "#b3001a",
    "alpha": 0.5,
    "lw": 2,
};
# default values
#wx.App(False);
par_def={
    "par_mod": par_mod.copy(),
    "par_plot": par_plot.copy()
};
wd=""; # working dir
bg_grey=None;
bg_white=wx.WHITE;
bg_null=wx.NullColour;
hcl2item={
    "hcl_proba": ("proba", "cl"),
    "hcl_cutoff": ("cutoff", "cutnum"),
    "hcl_scutoff": ("stringent cutoff ", "stringentcutnum")
};
ID_OPEN_KVH=None;
ID_SAVE_KVH=None;
## call back functions
def OnExit(evt):
    """
    This is executed when the user clicks the 'Exit' option
    under the 'File' menu or close the window.  We ask the user if he *really*
    want to exit, then close everything down if he does.
    """
    global fdata;
    if fdata == Path() or model is None:
        gui.mainframe.Destroy();
        return
    if not prev_res_saved:
        dlg = wx.MessageDialog(None, 'Results were not saved. Exit %s anyway?'%me, 'Choose Yes or No!', wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT);
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
    global fdata, model, resdf, wd, prev_res_saved, par_mod, par_plot, prev_par_saved;
    #import pdb; pdb.set_trace();
    win=evt.GetEventObject();
    win=win.GetWindow();
    if not prev_res_saved and fdata != Path():
        if wx.MessageBox("Current results have not been saved! Proceed?", "Please confirm",
                         wx.ICON_QUESTION | wx.YES_NO, win) == wx.NO:
            return;
    if evt.GetId() != wx.ID_OPEN:
        fdata=diri/"example"/'gene W ID ref ID test ID query.txt';
    else:
        with wx.FileDialog(None, defaultDir=str(wd), wildcard="Data files (*.tsv;*.txt;*.csv)|*.tsv;*.txt;*.csv",
            style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                # proceed the data file
                fdata=Path(dlg.GetPath());
            else:
                return;
    wait=wx.BusyCursor();
    try:
        file2data(fdata);
        gui.mainframe.SetTitle(me+" "+fdata.name);
        wd=fdata.parent;
        if fdata.with_suffix(".kvh").exists():
            file2par(fdata.with_suffix(".kvh"));
        else:
            par_mod=par_def["par_mod"].copy();
            par_plot=par_def["par_plot"].copy();
            prev_par_saved=True;
        par2gui(par_mod, par_plot);
        gui.nb.SetSelection(lab2ip(gui.nb, "Data")[0]);
        gui.mainframe.SetStatusText("'%s' is read"%fdata.name);
        prev_res_saved=False;
        # clean tabs in Model, Test etc
        model=resdf=None;
        for tab in ("model", "test", "ref", "qry", "plot"):
            nb=getattr(gui, "nb_"+tab)
            #print("tab=", tab, "nb=", nb.GetName())
            nb_rmpg(nb);
            #for ch in pg.GetChildren():
            #    print("rm ", ch)
            #    if tab == "plot":
            #        import pdb; pdb.set_trace()
            #    ch.Destroy();
        for tab in ("ref", "test", "qry"):
            pg=getattr(gui, "sw_heat_"+tab);
            for ch in pg.GetChildren():
                ch.Destroy();
    finally:
        del(wait);
def OnOpenPar(evt):
    """
    This is executed when the user clicks the 'Open parameters' option
    under the 'File' menu.  We ask the user to choose a KVH file.
    """
    global fdata, prev_par_saved, par_mod, par_plot;
    win=evt.GetEventObject().GetWindow();
    if not prev_par_saved:
        if wx.MessageBox("Current parameters have not been saved! Proceed?", "Please confirm",
                         wx.ICON_QUESTION | wx.YES_NO, win) == wx.NO:
            return;
    with wx.FileDialog(None, defaultDir=str(wd), wildcard="Parameter files (*.kvh)|*.kvh",
        style=wx.FD_OPEN) as dlg:
        if dlg.ShowModal() == wx.ID_OK:
            #print "selected file="+dlg.GetPath();
            # proceed the parameter file
            fpar=Path(dlg.GetPath());
            #import pdb; pdb.set_trace();
            file2par(fpar);
            par2gui(par_mod, par_plot);
            gui.nb.SetSelection(lab2ip(gui.nb, "Parameters")[0]);
            gui.mainframe.SetStatusText("'%s' is read"%fpar.name);
            gui.btn_remod.Enable();
            prev_par_saved=True;
def OnSave(evt):
    """
    This is executed when the user clicks the 'Save results' option
    under the 'File' menu. Results are stored in a zip archive.
    """
    global fdata, resdf, prev_res_saved;
    if model is None or len(model) == 0:
        # data are not yet chosen
        err_mes("No learned model.\nRead data file and learn model first.");
        return;
    timeme("OnSave")
    if dogui:
        win=evt.GetEventObject();
        win=win.GetWindow();
        with wx.FileDialog(win, "Save results in a ZIP archive", defaultFile=fdata.with_suffix(".zip").name, defaultDir=str(wd), wildcard="ZIP files (*.zip)|*.zip", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return # the user changed their mind

            # save the current contents in the file
            fzip=Path(fileDialog.GetPath());
            wait=wx.BusyCursor();
            #wx.BeginBusyCursor();
            #print("wait");
    else:
        fzip=fdata.with_suffix(".zip");
    with tempfile.TemporaryDirectory() as tmpd:
        #import pdb; pdb.set_trace();
        fbase=Path(tmpd);
        try:
            # save *.zip one file per gene with tabs: model, ref etc.
            nwork=min(len(model.keys()), nproc)
            if nwork == 1:
                for nm in model.keys():
                    nm2xlsx(nm, fbase, resdf);
            else:
                with mp.Pool(nwork) as pool:
                    pool.map(tls.starfun, ((nm2xlsx, nm, fbase, resdf) for nm in model.keys()));
            # save .pdf
            fnm=fbase/"plots.pdf";
            with mpdf(fnm) as pdf:
                for nm, dm in model.items():
                    figure=mpl.figure.Figure(dpi=None, figsize=(8, 6));
                    ax=figure.gca();
                    dc=dcols[nm];
                    histgmm(data.iloc[:,dc["itest"]].values, dm["par"], ax, dm["par_mod"], par_plot) # hist of test
                    ax.set_title(nm);
                    pdf.savefig(figure);
                d=pdf.infodict();
                d["Creator"]=me+" "+version;
                d["CreationDate"]=datetime.datetime.now(LOCAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z %z');
            # save heatmaps
            if ids is not None and len(ids) > 0:
                #import pdb; pdb.set_trace();
                fnm=fbase/"heatmaps.pdf";
                with mpdf(fnm) as pdf:
                    for htype in ("ref", "test", "qry"):
                        cl2heat(htype, None, classif, pdf);
                    d=pdf.infodict();
                    d["Creator"]=me+" "+version;
                    d["CreationDate"]=datetime.datetime.now(LOCAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z %z');
                if dogui:
                    gui.mainframe.SetStatusText("Written '"+fnm.name+"'");
            # prepare zip
            with zipfile.ZipFile(fzip, "w") as zf:
                zf.write(fdata, fdata.name);
                with zf.open(fdata.with_suffix(".kvh").name, "w") as f:
                    fs=io.StringIO();
                    tls.dict2kvh({"par_mod": par_mod, "par_plot": par_plot}, fs);
                    f.write(fs.getvalue().encode());
                    fs.close();
                for f in fbase.glob("**/*"):
                    zf.write(f, fzip.with_suffix("").name+"/"+f.name);
            prev_res_saved=True;
        except IOError:
            #import pdb; pdb.set_trace();
            if dogui:
                del(wait);
            err_mes("Cannot save results in file '%s'." % fpath);
            return;
    timeme("end save")
    if dogui:
        #wx.EndBusyCursor();
        #print("del wait");
        del(wait);
def OnSavePar(evt):
    """
    This is executed when the user clicks the 'Save parameters' option
    under the 'File' menu. Parameters are stored in <fdata>.kvh.
    """
    global fdata, resdf, prev_res_saved, prev_par_saved;
    if dogui:
        win=evt.GetEventObject().GetWindow();
        with wx.FileDialog(win, "Save parameters in a KVH file", defaultFile=fdata.with_suffix(".kvh").name if fdata != Path() else "parameters.kvh", defaultDir=str(wd), wildcard="KVH files (*.kvh)|*.kvh", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return # the user changed their mind

            # save the current contents in the file
            fpar=Path(fileDialog.GetPath());
    else:
        fpar=fdata.with_suffix(".kvh");
    try:
        # save *.kvh
        with fpar.open("w") as f:
            tls.dict2kvh({"par_mod": par_mod, "par_plot": par_plot}, f);
        prev_par_saved=True;
    except IOError:
        #import pdb; pdb.set_trace();
        err_mes("Cannot save parameters in file '%s'." % fpar);
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
        " It reads data from and writes classification results to TSV files",
        350, wx.ClientDC(win)));
    info.SetWebSite("https://pypi.org/project/g3mclass");
    info.AddDeveloper("Serguei SOKOL");
    info.AddDeveloper("Marina GUVAKOVA");

    info.SetLicense(wordwrap(licenseText, 500, wx.ClientDC(win)));

    # Then we call wx.AboutBox giving it that info object
    wx.adv.AboutBox(info);
def OnLinkClicked(evt):
    url=evt.GetLinkInfo().Href
    if url.startswith("http"):
        webbrowser.open_new_tab(evt.GetLinkInfo().Href);
    else:
        evt.Skip()
def OnSize(evt):
    "main window is resized"
    win=evt.GetEventObject();
    sz=evt.GetSize();
    #print(win);
    #print(sz)
    win.SetSize(sz);
    evt.Skip();
    return;
def OnRemodel(evt):
    "Model parameters changed => relearn and put results in gui"
    global resdf, prev_res_saved, model, classif;
    timeme("OnRemodel");
    if dogui:
        gui.btn_remod.Disable();
        wait=wx.BusyCursor();
        gui.mainframe.SetStatusText("Calculating models ...")
    # learn model
    #import pdb; pdb.set_trace();
    model=data2model(data, dcols);
    timeme("model");
    # classify data
    classif=dclass(data, dcols, model);
    timeme("classify");
    ## create and fill the data table
    if resdf is None:
        resdf={};
    for dtype in ("model", "test", "ref", "qry"):
        if dtype == "model":
            resdf[dtype]={};
            for nm,dm in model.items():
                resdf[dtype][nm]=tls.dict2df(dm, dig=3);
        else:
            resdf[dtype]={};
            for nm,d in classif.items():
                ucl=sorted(model[nm]["par"].columns);
                if dtype == "qry":
                    for nmq,dq in d[dtype].items():
                        vnm=nm+" ("+nmq+")";
                        resdf[dtype][vnm]=tls.tcol2df(class2tcol(dq, ucl, ids["m,q2id"].get(nm+"\t"+nmq) if ids is not None else None));
                else:
                    idh=None if ids is None else ids.get(dtype);
                    if idh is not None and len(idh) == 0:
                        idh=None;
                    resdf[dtype][nm]=tls.tcol2df(class2tcol(d[dtype], ucl, idh));
    timeme("resdf");
    if dogui:
        for tab in ("sw_model", "sw_test", "sw_ref", "sw_qry", "sw_plot"):
            gtab=getattr(gui, tab);
            dtype=tab[3:];
            # remove previous sub-pages and create one page per marker
            nb=getattr(gui, "nb_"+dtype);
            #print("tab=", tab, "; nb=", nb);
            for i in range(nb.GetPageCount()-1, -1, -1):
                nb.DeletePage(i);
            nb.SetSize(400, 300); # fixes warning "gtk_box_gadget_distribute: assertion 'size >= 0' failed"
            if tab == "sw_plot":
                OnReplot(None);
            else:
                #with thpool(min(4, len(resdf[dtype]), os.cpu_count())) as pool:
                #    list(pool.map(tls.starfun, ((wx.CallAfter, d2grid, nm, df, nb, lock) for nm,df in resdf[dtype].items())));

                for nm,df in resdf[dtype].items():
                #    wx.CallLater(10, d2grid, nm, df, nb);
                    d2grid(nm, df, nb);
            timeme("tab="+tab)
        gui.nb.SetSelection(lab2ip(gui.nb, "Model")[0]);
        w,h=gui.mainframe.GetSize();
        gui.mainframe.SetSize(w+1,h);
        wx.CallAfter(gui.mainframe.SetSize, w,h);
        wx.CallAfter(OnReheat, None);
        del(wait);
        prev_res_saved=False;
        gui.mainframe.SetStatusText("Calculating models ... done.")
    timeme("dogui");
def OnReplot(evt):
    "replot in tab Plots"
    if model is None:
        return;
    # Model plots
    nb=gui.nb_plot;
    nb_rmpg(nb);
    for nm,dm in model.items():
        m2plot(nm, dm, nb);
    if evt is not None:
        w,h=gui.mainframe.GetSize();
        gui.mainframe.SetSize(w+1,h);
        wx.CallAfter(gui.mainframe.SetSize, w,h);
        gui.nb.SetSelection(lab2ip(gui.nb, "Model plots")[0]);
        wx.CallAfter(OnReheat, None);
def OnReheat(evt):
    # Heatmaps
    if dogui:
        wait=wx.BusyCursor();
    try:
        for htype in ("ref", "test", "qry"):
            tab=getattr(gui, "sw_heat_"+htype);
            cl2heat(htype, tab, classif);
    except Exception as e:
        err_mes(format(e));
        if dogui:
            del(wait);
            return;
    #import pdb; pdb.set_trace();
    #pass;
    if dogui:
        w,h=gui.mainframe.GetSize();
        gui.mainframe.SetSize(w+1,h);
        wx.CallAfter(gui.mainframe.SetSize, w,h);
        if evt is not None:
            gui.nb.SetSelection(lab2ip(gui.nb, "Heatmaps")[0]);
        del(wait);
def OnSlider(evt):
    "Slider for modeling parameters was moved"
    global par_mod, prev_par_saved;
    prev_par_saved=False;
    if data is not None :
        gui.btn_remod.Enable();
    if evt is not None:
        win=evt.GetEventObject();
        #print("evt=", evt);
        nm=win.GetName();
        val=win.GetValue();
        par_mod[nm]=val;
        win._OnSlider(evt);
        if nm == "k_hlen":
            gui.chk_hbin.SetValue(True);
    s=gui.txt_hbin_hlen.GetLabel().split(":")
    gui.txt_hbin_hlen.SetLabel(s[0]+": "+", ".join(vhbin(par_mod).astype(str)));
    OnCheck(None)
def OnSliderPlot(evt):
    "Slider for plot parameters was moved"
    global par_plot, prev_par_saved;
    prev_par_saved=False;
    win=evt.GetEventObject();
    par_plot[win.GetName()]=win.GetValue();
    win._OnSlider(evt);
def OnCheck(evt):
    "a checkbox was checked/unchecked"
    global prev_par_saved;
    prev_par_saved=False;
    if evt is None:
        val=gui.chk_hbin.GetValue();
    else:
        win=evt.GetEventObject();
        val=win.IsChecked();
    par_mod["k_var"]=val;
    # set text labels
    s2=gui.txt_hbin2.GetLabel().split("(")
    s3=gui.txt_hbin3.GetLabel().split("(")
    if val:
        gui.txt_hbin2.SetLabel(s2[0]+"(no)");
        gui.txt_hbin3.SetLabel(s3[0]+"(yes)");
    else:
        gui.txt_hbin2.SetLabel(s2[0]+"(yes)");
        gui.txt_hbin3.SetLabel(s3[0]+"(no)");
    if data is not None :
        gui.btn_remod.Enable();
def OnCheckHcl(evt):
    "a checkbox of heatmap classif was checked/unchecked"
    global prev_par_saved;
    prev_par_saved=False;
    win=evt.GetEventObject();
    par_plot[win.GetName()]=win.IsChecked();
def OnTabChange(evt):
    #import pdb; pdb.set_trace();
    win=evt.GetEventObject();
    i=win.GetSelection();
    for nb in (gui.nb_model, gui.nb_test, gui.nb_ref, gui.nb_plot):
        if win is nb:
            continue;
        if i < nb.GetPageCount():
            nb.SetSelection(i);
def OnColpick(evt):
    "respond to color picker control"
    global par_plot, prev_par_saved;
    prev_par_saved=False;
    #import pdb; pdb.set_trace();
    win=evt.GetEventObject();
    par_plot[win.GetName()]=evt.GetColour().GetAsString(wx.C2S_HTML_SYNTAX);
def OnDefault(evt):
    "Change parameters to default values"
    global par_plot, par_mod, prev_par_saved;
    prev_par_saved=False;
    win=evt.GetEventObject();
    if win.GetName() == "def_mod":
        for k,v in par_mod.items():
            val=par_def["par_mod"][k]
            par_mod[k]=val.copy() if "copy" in dir(val) else val
    if win.GetName() == "def_plot":
        for k,v in par_plot.items():
            if k.startswith("hcl_"):
                continue;
            val=par_def["par_plot"][k]
            par_plot[k]=val.copy() if "copy" in dir(val) else val
    if win.GetName() == "def_heat":
        for k,v in par_plot.items():
            if not k.startswith("hcl_"):
                continue;
            val=par_def["par_plot"][k]
            par_plot[k]=val.copy() if "copy" in dir(val) else val
    par2gui(par_mod, par_plot)
def OnHelp(evt):
    gui.help.AddBook(str(diri/"help"/"g3mclass.hhp"));
    gui.help.DisplayContents()
    gui.helpwin=gui.help.GetHelpWindow()
    gui.helpwin.Bind(wx.html.EVT_HTML_LINK_CLICKED, OnLinkClicked)

# helpers
def ToDo(evt):
    """
    A general purpose "we'll do it later" dialog box
    """
    win=evt.GetEventObject().GetTopLevelParent();
    dlg = wx.MessageDialog(win, "Not Yet Implimented! evt="+str(dir(evt)), "ToDo",
                         wx.OK | wx.ICON_INFORMATION);
    dlg.ShowModal();
    dlg.Destroy();
def d2grid(nm, df, nb):
    gtab2=wx.Panel(nb, name=nm);
    nb.AddPage(gtab2, nm);
    #import pdb; pdb.set_trace();
    gtab2.SetBackgroundColour(bg_sys);
    gtab2.Bind(wx.EVT_SIZE, OnSize);
    grid2=df2grid(gtab2, df, name=nm);
    timeme("grid="+nm);
def m2plot(nm, dm, nb):
    gtab=wx.Panel(nb, name=nm);
    nb.AddPage(gtab, nm);
    if is_dark:
        plt.style.use('dark_background')
    figure=mpl.figure.Figure(dpi=None, figsize=(2, 2));
    canvas=FigureCanvas(gtab, -1, figure);
    toolbar=NavigationToolbar(canvas);
    toolbar.Realize();
    ax=figure.gca();
    dc=dcols[nm];
    histgmm(data.iloc[:,dc["itest"]].values, dm["par"], ax, dm["par_mod"], par_plot) # hist of test
    ax.set_title(nm);
    sizer=wx.BoxSizer(wx.VERTICAL);
    sizer.Add(canvas, 1, wx.EXPAND);
    sizer.Add(toolbar, 0, wx.LEFT | wx.EXPAND);
    gtab.SetSizer(sizer);
def cl2heat(htype, pg, classif, pdf=None):
    # clear previous plots
    if pdf is None:
        for ch in pg.GetChildren():
            ch.Destroy();
    if ids is None or len(ids.get(htype, {})) == 0 or classif is None:
        return;
    if pdf is None:
        sizer=wx.BoxSizer(wx.VERTICAL);
        pg.figs=[];
    dpi=100;
    #import pdb; pdb.set_trace();
    for fig in [htype] if htype != "qry" else list(ids[htype].keys()):
        idh=ids[htype][fig]["id"] if htype == "qry" else ids[htype];
        nid=len(idh);
        # gather classif data s.t. can be indexed by "cl", "cutnum" etc.
        cdata={};
        cls=[];
        if htype == "qry":
            if all(nmq == fig for _,nmq in ids[htype][fig]["m,q"]):
                # strip nmq if block has the same name
                for nmm,nmq in ids[htype][fig]["m,q"]:
                    cdata[nmm]=classif[nmm]["qry"][nmq];
                    cls += model[nmm]["par"].columns.to_list();
            else:
                for nmm,nmq in ids[htype][fig]["m,q"]:
                    cdata[nmm+" ("+nmq+")"]=classif[nmm]["qry"][nmq];
                    cls += model[nmm]["par"].columns.to_list();
        else:
            for nm,d in classif.items():
                cdata[nm]=d[htype];
                cls += model[nm]["par"].columns.to_list();
        cls=np.sort(list(set(cls)));
        figsize=np.array((0, 0)); # will be set later
        #print("htype=", htype, "figsize=", figsize);
        figure=mpl.figure.Figure(dpi=dpi, figsize=figsize/dpi);
        if pdf is None:
            pg.figs.append(figure);
        if htype == "qry":
            figure.suptitle(fig, fontsize=16);
        elif pdf is not None:
            figure.suptitle(htype, fontsize=16);
        ax=[];
        im=[];
        nhcl=(par_plot["hcl_proba"]+par_plot["hcl_cutoff"]+par_plot["hcl_scutoff"]);
        ihcl=0;
        for hcl in ("hcl_proba", "hcl_cutoff", "hcl_scutoff"):
            if not par_plot[hcl]:
                continue;
            ihcl += 1;
            ctype,item=hcl2item[hcl];
            # extract classes of given type
            pcl=pa.DataFrame();
            for nm,d in cdata.items():
                pcl[nm]=d[item];
            nr,nc=pcl.shape;
            if nr > nid:
                pcl=pcl.iloc[:nid,:];
                nr=nid;
            pcl.index=idh[:nr];
            # valid, i.e. non all empty rows
            dn=pcl.to_numpy();
            irv=(dn == dn).any(1)*(~tls.is_na(idh[:nr]));
            pcl=pcl.iloc[irv,:];
            nr,nc=pcl.shape;
            if ihcl == 1:
                # recalculate figure size
                mh=35; # all horizontal margins/pads
                lh=max(len(str(v)) for v in pcl.columns)*28;  # nb char * 28 pix = horizontal label length
                imh=nr*25; # image width
                mv=175; # all vertical margins/pads
                lv=max(len(str(v)) for v in pcl.index)*18;
                imv=nc*25; # image height
                wcb=20; # width of colorbar
                mtit=(42 if pdf or htype == "qry" else 0); # margin for title
                figsize=np.array([mh+lh+imh+wcb, (mv+lv+imv)*nhcl+mtit]);
                figure.set_size_inches(figsize/dpi);
            
            # prepare cmap
            clist, cmap=cl2cmap(cls, par_plot);
            # normalizer
            #norm_bins=cls+0.5;
            #norm_bins=np.insert(norm_bins, 0, np.min(norm_bins)-1.0);
            ## Make normalizer
            #norm=mpl.colors.BoundaryNorm(norm_bins, len(cls), clip=True);
            norm=mpl.colors.Normalize(cls.min()-0.5, cls.max()+0.5)
            ax.append(figure.add_subplot(nhcl*100+10+ihcl)); # nx1 grid ipl-th plot
            #figure.subplots_adjust(hspace = 0.5);
            im.append(heatmap(pcl, ax[-1], collab=True, cmap=cmap, norm=norm));
            ax[-1].set_title(ctype);
            #ax[-1].apply_aspect();
            #print(htype, ctype, "im bbox=", im[-1].get_window_extent());
        if ihcl == 0:
            return;
        cbm2=(figsize[0]-wcb-45)/figsize[0]; # colbar width in 0-1 figure coords
        cbm=(figsize[0]-wcb)/figsize[0]; # colbar width in 0-1 figure coords
        #print("cbm=", cbm, "cbm2=", cbm2);
        position=figure.add_axes([cbm2, 0.3, (1-cbm2)*0.5, 0.35]); #0.93, 0.02
        figure.colorbar(im[-1], ticks=cls, cax=position);
        #figure.colorbar(im, ax=ax, ticks=cls, shrink=0.5);
        warnings.filterwarnings("ignore");(figsize[0]-wcb)/figsize[0]
        #print(figsize)
        #import pdb; pdb.set_trace()
        #figure.tight_layout(rect=[10/figsize[0], 0, cbm, 1]); #0.9
        figure.tight_layout(rect=[45./figsize[0], 0, cbm2*0.95, 1-mtit/figsize[1]], pad=0.4, w_pad=0.5, h_pad=1.0)
        #print("plot w=", (figsize[0]-wcb)/figsize[0]);
        #import pdb; pdb.set_trace();
        warnings.filterwarnings("default");
        if pdf is None:
            canvas=FigureCanvas(pg, -1, figure);
            toolbar=NavigationToolbar(canvas);
            toolbar.Realize();
            sizer.Add(canvas, 0); #1, wx.EXPAND);
            sizer.Add(toolbar, 0);
        else:
            pdf.savefig(figure);
    if pdf is None:
        pg.SetSizer(sizer);
def heatmap(data, ax, collab=True, **kwargs):
    """
    Create a heatmap from a pandas DataFrame.

    Parameters
    ----------
    data
        A dataframe of shape (nr, nc).
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current axes.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    # Plot the heatmap
    im = ax.imshow(data.to_numpy().transpose().astype(float), **kwargs);
    #print("vmin=", kwargs["vmin"], "vmax=", kwargs["vmax"])
    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[0]));
    ax.set_yticks(np.arange(data.shape[1]));
    # ... and label them with the respective list entries.
    ax.set_yticklabels(data.columns);
    ax.set_xticks(np.arange(data.shape[0]+1)-.5, minor=True);
    ax.set_yticks(np.arange(data.shape[1]+1)-.5, minor=True);
    ax.grid(which="minor", color="w", linestyle='-', linewidth=1);
    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False);
    if collab:
        ax.set_xticklabels(data.index);

        # Rotate the tick labels and set their alignment.
        plt.setp(ax.get_xticklabels(), rotation=-60, ha="right",
                 rotation_mode="anchor")
    else:
        ax.set_xticklabels("");
    return im;
def err_mes(mes):
    "Show error dialog in GUI mode or raise exception"
    if dogui:
        dlg=wx.MessageDialog(None, mes, "Error", wx.OK | wx.ICON_ERROR);
        dlg.ShowModal();
        dlg.Destroy();
    else:
        raise Exception(me+": "+mes);
def warn_mes(mes):
    "Show info dialog in GUI mode or print on stderr"
    if dogui:
        dlg=wx.MessageDialog(None, mes, "Warning", wx.OK | wx.ICON_WARNING);
        dlg.ShowModal();
        dlg.Destroy();
    else:
        print(me+": "+mes, file=sys.stderr);
def vhbin(par_mod):
    "produce a vector of hbin values"
    v=par_mod["k"]+5*np.linspace(-par_mod["k_hlen"], par_mod["k_hlen"], round(2*par_mod["k_hlen"]+1));
    v=v[v >= 10];
    return(v.astype(int));
def par2gui(par_mod, par_plot):
    "Set gui widgets in accordance with 'par' content"
    # modeling parameters
    gui.sl_hbin.SetValue(par_mod["k"]);
    gui.chk_hbin.SetValue(par_mod["k_var"]);
    gui.sl_hbin_hlen.SetValue(par_mod["k_hlen"]);
    gui.sl_thr_di.SetValue(par_mod["thr_di"]);
    gui.sl_thr_w.SetValue(par_mod["thr_w"]);
    # heatmap
    gui.chk_hcl_proba.SetValue(par_plot["hcl_proba"]);
    gui.chk_hcl_cutoff.SetValue(par_plot["hcl_cutoff"]);
    gui.chk_hcl_scutoff.SetValue(par_plot["hcl_scutoff"]);
    # plot
    gui.cpick_hist.SetColour(par_plot["col_hist"]);
    gui.cpick_panel.SetColour(par_plot["col_panel"]);
    gui.cpick_tot.SetColour(par_plot["col_tot"]);
    gui.cpick_ref.SetColour(par_plot["col_ref"]);
    gui.cpick_neglow.SetColour(par_plot["col_neglow"]);
    gui.cpick_neghigh.SetColour(par_plot["col_neghigh"]);
    gui.cpick_poslow.SetColour(par_plot["col_poslow"]);
    gui.cpick_poshigh.SetColour(par_plot["col_poshigh"]);
    gui.sl_alpha.SetValue(par_plot["alpha"]);
    gui.sl_lw.SetValue(par_plot["lw"]);
    # set text labels
    OnSlider(None);
    OnCheck(None);
def nm2xlsx(nm, fbase, resdf):
    "generate xlsx file for marker named by 'nm'"
    fnm=fbase/(nm.replace("/", ".")+".xlsx");
    ddf={};
    for dtype in ("model", "test", "ref", "qry"):
        if dtype == "qry":
            #import pdb; pdb.set_trace()
            for nmq,dq in resdf[dtype].items():
                if nmq.startswith(nm+" ("):
                    nmq=nmq[len(nm):].strip("( )")
                    ddf[nmq]=dq;
        else:
            ddf[dtype]=resdf[dtype][nm];
    tls.ddf2xlsx(ddf, fnm);
def nb_rmpg(nb):
    "Remove pages from wx.notebook 'nb'"
    for i in range(nb.GetPageCount()-1, -1, -1):
        nb.DeletePage(i);
## working functions
def file2par(fpar):
    "Read parameters from fpar file"
    global par_mod, par_plot;
    d=tls.kvhd2type(tls.kvh2dict(fpar));
    #print("read kvh=", d);
    par_mod.update(d.get("par_mod", {}));
    par_plot.update(d.get("par_plot", {}));
    #import pdb; pdb.set_trace();
    for k in [v for v in par_plot.keys() if v.startswith("col_")]:
        par_plot[k]=wx.Colour(par_plot[k]).GetAsString(wx.C2S_HTML_SYNTAX);
def file2data(fn):
    "Read Path 'fn' into data.frame"
    global data, dcols, ids;
    try:
        data=pa.read_csv(fn, header=None, sep="\t");
    except:
        err_mes("file '"+str(fn)+"' could not be read");
        return;
    cols=[str(v).strip() if v==v else "" for v in data.iloc[0, :]];
    data.columns=cols;
    data=data.iloc[1:,:];
    iparse=[]; # collect parsed columns
    # search for (ref) and (test)
    suff=r"(ref)";
    dcols=dict((i, re.sub(tls.escape(suff, "()")+"$", "", v).strip()) for i,v in enumerate(cols) if v.endswith(suff) and not re.match("^id *\(ref\)$", v));
    #import pdb; pdb.set_trace();
    if not dcols:
        err_mes("not found markers '"+suff+"' in column names");
        return;
    # check that varnames are unique and non empty
    cnt=tls.list2count(dcols.values());
    if len(cnt) != len(dcols):
        vbad=[v for v,i in cnt.items() if i > 1];
        err_mes("following column name is not unique in '(ref)' set: '"+vbad[0]+"'");
        return;
    iparse += list(dcols.keys());
    
    # build dcols: varname => dict:iref, itest, qry_dict). qry_dict can be empty
    dcols=dict((v,k) for k,v in dcols.items());
    for nm in dcols.keys():
        # check that every ref has its test pair
        itest=[i for i,v in enumerate(cols) if v.startswith(nm) and v.endswith("(test)") and re.match("^ *$", v[len(nm):-7])];
        if not itest:
            err_mes("column '"+nm+" (ref)' has not its counter part '"+nm+" (test)'");
            return;
        elif len(itest) > 1:
            err_mes("following column name is not unique in '(test)' set: '"+nm+"'");
            return;
        else:
            iref=dcols[nm];
            itest=itest[0];
            dcols[nm]={"iref": iref, "itest": itest};
        iparse.append(itest);
        # get query (if any)
        dqry=dict((i,v[len(nm):].strip("( )")) for i,v in enumerate(cols) if (v.startswith(nm+" ") or v.startswith(nm+"(")) and not (v.endswith("(test)") or v.endswith("(ref)")));
        #print(nm+" dqry=", dqry);
        # check that qry names are unique
        cnt=tls.list2count(dqry.values());
        if len(cnt) < len(dqry):
            err_mes("following column names are not unique in '(query)' set: '"+"', '".join([v for v,i in cnt.items() if i > 1])+"'");
            return;
        dqry=dict((v,{"i": i}) for i,v in dqry.items());
        to_rm=[];
        for nmq in dqry.keys():
            iq=dqry[nmq]["i"];
            iparse.append(iq);
            if all(tls.is_na(data.iloc[:,iq])):
                to_rm.append(nmq);
        for nmq in to_rm:
            del(dqry[nmq]);
        dcols[nm]["qry"]=dqry;
    #tls.aff("dcols", dcols);
    # gather ids. id (ref) and id (test) are unique. id_qry (name) may be multiple
    ids=dict();
    #import pdb; pdb.set_trace();
    for suff in ("ref", "test"):
        ids[suff]=dict((i, None) for i,v in enumerate(cols) if re.match("id *\("+suff+"\)$", str(v)));
        if len(ids[suff]) > 1:
            err_mes("Column 'id ("+suff+") is not unique, cf. columns: "+", ".join(str(i+1) for i in ids[suff].keys()));
        if ids[suff]:
            icol=list(ids[suff].keys())[0];
            iparse.append(icol);
            idh=data.iloc[:,icol]; # id here
            idh=idh[~tls.is_na_end(idh)];
            if len(idh) == 0:
                ids[suff]=None;
                continue;
            #iu,ic=np.unique(idh[idh == idh], return_counts=True);
            #if np.max(ic) > 1:
            #    err_mes("ID column '"+cols[icol]+"' ("+str(icol+1)+") in '"+fn.name+"' has non unique entries. Each ID must be unique.");
            #    return;
            ids[suff]=idh;
            
    # each id (name) is relative to next qrys till next 'id (smth)' is found
    ids["qry"]=dict((v[3:].strip("( )"), i) for i,v in enumerate(cols) if v.startswith("id ") and not (v.endswith("(ref)") or v.endswith("(test)")));
    ids["m,q2id"]=dict();
    # collect qry icols for each block
    ib=list(ids["qry"].values());
    nb=len(ids["qry"]);
    for i,nmb in enumerate(list(ids["qry"].keys())):
        icol=ids["qry"][nmb];
        iparse.append(icol);
        idh=data.iloc[:,icol]; # id here
        idh=idh[~tls.is_na_end(idh)];
        if len(idh) == 0:
            del(ids["qry"][nmb])
            continue;
        #iu,ic=np.unique(idh[idh == idh], return_counts=True);
        #if np.max(ic) > 1:
        #    err_mes("ID column '"+cols[icol]+"' ("+str(icol+1)+") in '"+fn.name+"' has non unique entries. Each ID must be unique.");
        #    return;
        iend=ib[i+1] if i < nb-1 else len(cols);
        nmqs=[(nmm, nmq) for nmm,d in dcols.items() for nmq,dq in d["qry"].items() if dq["i"] > icol and dq["i"] <= iend]; # collection of tuples (marker_name; qry_name)
        #import pdb; pdb.set_trace();
        ids["qry"][nmb]={"id": idh, "m,q": nmqs};
        ids["m,q2id"].update(dict((m+"\t"+q, idh) for m,q in nmqs));
    for k in list(ids.keys()):
        if len(ids[k]) == 0:
            del(ids[k]);
    if len(ids) == 0:
        ids=None;
    #print("ids=", ids);
    # check that all columns are used
    iparse=set(iparse);
    for i,nm in enumerate(cols):
        if nm and i not in iparse:
            err_mes("Column '"+nm+"' is not recognized as one of: ref, test, query or id of one of these");
            return;
    if dogui:
        gui.mainframe.SetCursor(wx.Cursor(wx.CURSOR_WAIT));
    # convert to float
    for nm,dc in dcols.items():
        for i in [dc["iref"], dc["itest"], *[dq["i"] for nmq,dq in dc["qry"].items()]]:
            data.iloc[:,i]=data.iloc[:,i].to_numpy(float);
    if dogui:
        gtab=getattr(gui, "sw_data");
        grid=df2grid(gtab, data);
        gui.btn_remod.Enable();
        w,h=gui.mainframe.GetSize();
        gui.mainframe.SetSize(w+1,h);
        wx.CallAfter(gui.mainframe.SetSize, w,h);
        gui.mainframe.SetCursor(wx.Cursor(wx.CURSOR_ARROW));
    else:
        OnRemodel(None) # automatically do analysis in non gui mod
def data2model(data, dcols):
    "Learn models for each var in 'data' described in 'dcols'. Return a dict with models pointed by varname"
    if len(dcols) > 1 and not par_mod["k_var"]:
        if nproc == 1:
            res=[tls.rt2model(data.iloc[:,dc["iref"]].values, data.iloc[:,dc["itest"]].values, par_mod) for dc in dcols.values()];
        else:
            #with thpool(min(len(dcols), os.cpu_count())) as pool:
            with mp.Pool(min(len(dcols), nproc)) as pool:
                res=pool.map(tls.starfun, ((tls.rt2model, data.iloc[:,dc["iref"]].values, data.iloc[:,dc["itest"]].values, par_mod) for dc in dcols.values()));
        res=dict(zip(dcols.keys(), res));
    else:
        res=dict();
        for nm,dc in dcols.items():
            ref=data.iloc[:,dc["iref"]].values;
            test=data.iloc[:,dc["itest"]].values;
            if par_mod["k_var"]:
                # run hbin numbers through vbin and get the best BIC
                vbin=vhbin(par_mod);
                #import pdb; pdb.set_trace();
                dl=dict();
                par_loc=[(dl.update({"tmp": par_mod.copy()}), dl["tmp"].update({"k": nbin}), dl["tmp"])[-1] for nbin in vbin]; # create n copies of par_mod with diff hbin
                if nproc == 1:
                    res_loc=[];
                    for d in par_loc:
                        try:
                            res_loc.append(tls.rt2model(ref, test, d));
                        except:
                            #import pdb; pdb.set_trace();
                            #tmp=tls.rt2model(ref, test, d);
                            raise;
                else:
                    #with thpool(min(len(dcols), os.cpu_count())) as pool:
                    with mp.Pool(min(nproc, len(dcols))) as pool:
                        res_loc=list(pool.map(tls.starfun, ((tls.rt2model, ref, test, d) for d in par_loc)));
                history=pa.DataFrame(None, columns=["k", "BIC", "classes"]);
                for tmp in res_loc:
                    history=history.append(pa.Series([tmp["par_mod"]["k"], tmp["BIC"], ",".join(tmp["par"].columns.astype(str))], index=history.columns), ignore_index=True);
                    #print("nbin=", nbin, "; bic=", tmp["BIC"], "par_mod=", tmp["par_mod"]);
                ibest=np.argmin([v["BIC"] for v in res_loc]);
                #print("ibest=", ibest, "bic=", res_loc[ibest]["BIC"], "vbic=", [v["BIC"] for v in res_loc]);
                history.index=list(range(1, tls.nrow(history)+1));
                res_loc[ibest]["history"]=history;
                res[nm]=res_loc[ibest];
            else:
                res[nm]=tls.rt2model(ref, test, par_mod);
            timeme("model "+nm);
    for k,v in res.items():
        v["creator"]={"name": me, "version": version, "data": str(fdata), "date": datetime.datetime.now(LOCAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z %z')};
    return(res);
def dclass(data, dcols, model):
    "Classify each var in 'data' described in 'dcols' using corresponding 'model'. Return a dict with classification pointed by varname/{ref,test}"
    res=dict();
    for nm,dc in dcols.items():
        ref=data.iloc[:,dc["iref"]].values;
        ref=ref[~tls.is_na_end(ref)];
        test=data.iloc[:,dc["itest"]].values;
        test=test[~tls.is_na_end(test)];
        res[nm]={
            "ref": tls.xmod2class(ref, model[nm]),
            "test": tls.xmod2class(test, model[nm]),
            "qry": dict((nmq, tls.xmod2class(data.iloc[:,dq["i"]].values, model[nm])) for nmq,dq in dc["qry"].items())
        };
    return(res);
def class2tcol(d, ucl, idh=None):
    "Format classification in d in tuple-column collection"
    # prepare text table
    x=d["x"];
    tcol=[("x", np.round(x, 3))];
    if idh is not None:
        tcol.insert(0, ("id", idh));
    # add class & repartition
    #ucl=sorted(set(tls.na_omit(d["cl"])));
    for cl,clname in (("cl", "proba"), ("cutnum", "cutoff"), ("stringentcutnum", "s.cutoff")):
        #import pdb; pdb.set_trace();
        tcol.append((clname, []));
        if clname == "proba":
            tcol.append(("max", np.round(d["wmax"], 3)));
        vcl=d[cl].astype(object);
        i=tls.which(~tls.is_na(vcl));
        vcl[i]=vcl[i].astype(int);
        tcol.append(("class", vcl));
        #import pdb; pdb.set_trace();
        
        dstat={"x": np.round(x.describe(), 3).astype(object)};
        for icl in ucl:
            ix=tls.which(vcl==icl);
            xcl=x[ix];
            if idh is not None:
                tcol.append(("id", idh.iloc[ix]));
            tcol.append((str(icl), np.round(xcl, 3)));
            dstat[str(icl)]=np.round(xcl.describe(), 3).astype(object);
        dstat=pa.DataFrame(dstat);
        dstat.loc["count"]=dstat.loc["count"].astype(int);
        dstat.loc["percent"]=(np.round((100*dstat.loc["count"]/dstat.loc["count", "x"]).astype(float), 2)).astype(str)+"%";
        dstat.loc["percent"]=dstat.loc["percent"].astype(str);
        i=dstat.index;
        dstat=dstat.reindex(i[0:1].to_list()+i[-1:].to_list()+i[1:-1].to_list())
        tcol.append((" ", []));
        tcol.append(("descriptive stats", dstat.index));
        for icol in range(tls.ncol(dstat)):
            #import pdb; pdb.set_trace();
            tcol.append((dstat.columns[icol], dstat.iloc[:,icol]));
    return(tcol);
def res2file(res, fpath=None, objname=None):
    if fpath == None:
        if fdata != Path():
            fpath=wd/(fdata.stem+"_res.tsv");
        else:
            err_mes("'fpath' variable is not set for writing");
    tls.obj2kvh(res, objname, fpath);
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
    return("%02d:%02d:%02d.%02d"%(hh,mm,ss,cc) if hh else "%02d:%02d.%02d"%(mm,ss,cc) if mm else "%02d.%02d"%(ss,cc));
def lab2ip(nb, lab):
    """lab2i(nb, nm) -> (i,Page) or (None,None)
    get page of a notebook nb by its label lab
    """
    for i in range(nb.GetPageCount()):
        if lab == nb.GetPageText(i):
            return((i,gui.nb.GetPage(i)));
    return((None,None));
def wxc2mplc(c):
    "Convert wx.Colour to matplotlib colour"
    return mpl.colors.to_rgb(np.asarray(wx.Colour(c))/255.);
def colorFader(c1,c2,mix=0): #fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
    c1=np.asarray(wxc2mplc(c1));
    c2=np.asarray(wxc2mplc(c2));
    return mpl.colors.to_hex((1-mix)*c1 + mix*c2);
def cl2cmap(cls, par_plot):
    "create a list of colors corresponding to classes in cls. Return the color list and cmap."
    cls=np.sort(cls);
    # prepare colors
    nneg=sum(cls<0);
    if nneg == 1:
        cneg=[par_plot["col_neglow"]];
    else:
        cneg=[colorFader(par_plot["col_neghigh"], par_plot["col_neglow"], i/nneg) for i in range(nneg)];
    npos=sum(cls>0);
    if npos == 1:
        cpos=[par_plot["col_poslow"]];
    else:
        cpos=[colorFader(par_plot["col_poslow"], par_plot["col_poshigh"], i/npos) for i in range(npos)];
    clist=cneg+[wxc2mplc(par_plot["col_ref"])]+cpos;
    return (clist, mpl.colors.LinearSegmentedColormap.from_list('clist', clist, len(clist)));
def histgmm(x, par, plt, par_mod, par_plot, **kwargs):
    "Plot histogram of sample 'x' and GMM density plot on the same bins"
    #print("pp=", par_plot);
    opar=par[sorted(par.columns)];
    xv=x[~tls.is_na(x)];
    xmi=np.min(xv);
    xma=np.max(xv);
    col_edge=wxc2mplc(par_plot["col_hist"]);
    col_panel=list(wxc2mplc(par_plot["col_panel"]))+[par_plot["alpha"]];
    
    #import pdb; pdb.set_trace();
    count, bins, patches = plt.hist(xv, np.linspace(xmi, xma, par_mod["k"]+1), color=wxc2mplc(par_plot["col_hist"]), density=True, **kwargs);
    [(p.set_facecolor(col_panel), p.set_edgecolor(col_edge)) for p in patches.get_children()];
    dbin=bins[1]-bins[0];
    nbp=401;
    xp=np.linspace(xmi, xma, nbp);
    dxp=(xma-xmi)/(nbp-1.);
    cdf=np.hstack(list(opar.loc["a", i]*tls.pnorm(xp, opar.loc["mean", i], opar.loc["sd", i]).reshape((len(xp), 1), order="F") for i in opar.columns));
    pdf=np.diff(np.hstack((tls.rowSums(cdf), cdf)), axis=0)/dxp;
    xpm=0.5*(xp[:-1]+xp[1:]);
    #import pdb; pdb.set_trace();
    clist,cmap=cl2cmap(par.columns, par_plot);
    colpar=[wxc2mplc(par_plot["col_tot"])]+clist;
    for i in range(pdf.shape[1]):
        line,=plt.plot(xpm, pdf[:,i], color=colpar[i], linewidth=par_plot["lw"], label=str(opar.columns[i-1]) if i > 0 else "Total"); #, **kwargs);
        lcol=line.get_color();
        plt.fill_between(xpm, 0, pdf[:,i], color=lcol, alpha=par_plot["alpha"], **kwargs);
    # x tics
    plt.tick_params(colors='grey', which='minor');
    if "set_xticks" in dir(plt):
        plt.set_xticks(xv, minor=True);
    plt.legend(loc='upper right', shadow=True); #, fontsize='x-large');
def usage():
    print(__doc__);
def make_gui():
    "create GUI"
    global gui, bg_grey, ID_OPEN_KVH, ID_SAVE_KVH, bg_sys, fg_sys, is_dark;
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)
    except:
        pass

    ID_OPEN_KVH=wx.Window.NewControlId();
    ID_SAVE_KVH=wx.Window.NewControlId();
    gui=wx.Object();
    gui.app=wx.App();
    wx.lib.colourdb.updateColourDB();
    bg_sys=wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW).GetAsString(wx.C2S_HTML_SYNTAX);
    fg_sys=wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT).GetAsString(wx.C2S_HTML_SYNTAX);
    is_dark=wx.SystemSettings.GetAppearance().IsDark();
    code=tls.wxlay2py(tls.kvh2tlist(str(diri/"g3mclass_lay.kvh")), pref="gui.");
    #("code=\n", code)
    exec(code);
    gui.help=wx.html.HtmlHelpController();
## take arguments
def main():
    global fdata, wd, gui, dogui, TIMEME, nproc, par_mod, par_plot;
    try:
        opts,args=getopt.getopt(sys.argv[1:], "hwvt", ["help", "DEBUG", "np="]);
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
        elif o=="-t":
            TIMEME=True;
        elif o=="--np":
            tmp=int(a);
            if tmp < 0:
                raise Excpetion("--np must have a positive integer argument")
            elif tmp == 0:
                pass; # keep actual nproc value;
            else:
                nproc=tmp;
        else:
            assert False, "unhandled option";
    if dogui:
        make_gui();
    else:
        gui.app=wx.App(False); # for wx.Colour converters in pdf
    fdata=Path(args[0]).resolve() if len(args) else Path();
    if fdata != Path() and (not fdata.is_file() and fdata.suffix != ".tsv"):
        fdata=fdata.with_suffix(".tsv");
        if not fdata.is_file():
            fdata=fdata.with_suffix(".txt");
            if not fdata.is_file():
                fdata=fdata.with_suffix(".csv");
                if not fdata.is_file():
                    err_mes(me+": file '"+str(fdata.parent/fdata.stem)+".[tsv|txt|csv]' does not exist.\n");
    if fdata != Path() and not fdata.is_file():
        err_mes(me+": file '"+str(fdata)+"' does not exist.\n");
    # convert colors to hexa
    for k in [v for v in par_plot.keys() if v.startswith("col_")]:
        par_plot[k]=wx.Colour(par_plot[k]).GetAsString(wx.C2S_HTML_SYNTAX);
    if fdata != Path():
        file2data(fdata);
        if dogui:
            gui.mainframe.SetTitle(me+" "+fdata.name);
        if fdata.with_suffix(".kvh").exists():
            file2par(fdata.with_suffix(".kvh"));
        else:
            par_mod=par_def["par_mod"].copy();
            par_plot=par_def["par_plot"].copy();
        wd=fdata.parent;
        os.chdir(wd);
        if dogui:
            par2gui(par_mod, par_plot);
            gui.nb.SetSelection(lab2ip(gui.nb, "Data")[0]);
            gui.mainframe.SetStatusText("'%s' is read"%fdata.name);
        if write_res:
            OnRemodel(None);
            OnSave(None);
    else:
        wd=Path(os.getcwd()).resolve();
        
    if dogui:
        #import wx.lib.inspection as wxli
        #wxli.InspectionTool().Show()
        gui.app.MainLoop();
if __name__ == "__main__":
    main();
