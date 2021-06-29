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
import getopt;
import re;
import itertools as itr;
import multiprocessing as mp;
from concurrent.futures import ThreadPoolExecutor as thpool;
import threading;
import time;

import wx;
import wx.grid;
import wx.adv;
import wx.html;
from wx.lib.wordwrap import wordwrap;
import wx.lib.mixins.inspection as wit;
import wx.lib.colourdb;
#from wx.lib.agw.flatnotebook import FlatNotebook as wx_nb;
wx_nb=wx.Notebook;

import matplotlib as mpl;
from matplotlib.backends.backend_wxagg import (
    FigureCanvasWxAgg as FigureCanvas,
    NavigationToolbar2WxAgg as NavigationToolbar);
from matplotlib.backends.backend_pdf import PdfPages as mpdf;
import matplotlib.pyplot as plt;

import numpy as np;
import pandas as pa;
import webbrowser;

import g3mclass
dirx=os.path.dirname(os.path.abspath(sys.argv[0])); # execution dir
diri=os.path.dirname(os.path.abspath(g3mclass.__file__)); # install dir
import tools_g3m as tls;

# timeit
from time import strftime, localtime, process_time as tproc
globals()["_T0"]=tproc()
def timeme(s="", dig=2):
    "if a global variable TIMEME is True and another global variable _T0 is set, print current CPU time relative to _T0. This printing is preceded by a message from 's'"
    if TIMEME:
        if "_T0" in globals():
            print(s, ":\tCPU=", round(tproc()-_T0, dig), "s", sep="");
        else:
            globals()["_T0"]=tproc();

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
        self.panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND));
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
        if bg_grey is None:
            bg_grey=self.GetLabelBackgroundColour();
        self.SetDefaultCellBackgroundColour(bg_white);
        parent.grid=self;
        bg=wx.grid.GridCellAttr();
        bg.SetBackgroundColour(bg_grey);
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
            for k in range(nrow):
                if empty or empty_end[k]:
                    pass;
                    #self.SetCellBackgroundColour(k, j, bg_grey);
                    #break;
                    #self.SetCellValue(k, j, "");
                else:
                    #self.SetCellBackgroundColour(k, j, bg_white);
                    val=vcol[k];
                    val=str(val) if val == val else "";
                    self.SetCellValue(k, j, val);
        self.AutoSizeColumns();
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
        self.txt.SetLabel(self.frmt%self._value);
        #print("ival=", ival);
        #print("_val=", self._value);
    def GetSizer(self):
        return self.hbox;
    def GetValue(self):
        return self._value;

## config constants
with open(os.path.join(diri, "g3mclass", "version.txt"), "r") as fp:
    version=fp.read()
# program name
me="G3Mclass";
# message in welcome tab
with open(os.path.join(diri, "g3mclass", "welcome.html"), "r") as fp:
    welc_text=fp.read() % {"me": me};
welc_text=re.sub("\n\n", "<br>\n", welc_text);
with open(os.path.join(diri, "g3mclass", "licence_en.txt"), "r") as fp:
    licenseText=fp.read();

## global vars
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
dcols={};
resdf=None; # dict for formatted output in .tsv
par_mod={
    "k": 25,
    "k_var": False,
    "thr_di": 0.5,
    "thr_w": 1.,
};
par_plot={
    "col_hist": "black",
    "col_panel": "white",
    "col_tot": "grey",
    "col_ref": "seagreen",
    "col_neglow": "lightskyblue",
    "col_neghigh": "dodgerblue",
    "col_poslow": "lightcoral",
    "col_poshigh": "maroon",
    "alpha": 0.5,
    "lw": 2,
};
wd=""; # working dir
bg_grey=None;
bg_white=wx.WHITE;
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
    global fdata, prev_res_saved;
    win=evt.GetEventObject();
    win=win.GetWindow();
    if not prev_res_saved:
        if wx.MessageBox("Current results have not been saved! Proceed?", "Please confirm",
                         wx.ICON_QUESTION | wx.YES_NO, win) == wx.NO:
            return;
    with wx.FileDialog(None, defaultDir=wd, wildcard="Data files (*.tsv)|*.tsv|Data files (*.csv)|*.csv",
        style=wx.FD_OPEN) as dlg:
        wait=wx.BusyCursor();
        if dlg.ShowModal() == wx.ID_OK:
            #print "selected file="+dlg.GetPath();
            # proceed the data file
            fdata=dlg.GetPath()
            file2data(fdata);
            gui.nb.SetSelection(lab2ip(gui.nb, "Data")[0]);
            gui.mainframe.SetStatusText("'%s' is read"%os.path.basename(fdata));
            pre_res_saved=False;
        del(wait);
def OnSave(evt):
    """
    This is executed when the user clicks the 'Save results' option
    under the 'File' menu. Results are stored in <fdata>_test_geneA.tsv, <fdata>_ref_geneA.tsv and so on.
    """
    global fdata, resdf, prev_res_saved;
    if not fdata:
        # data are not yet chosen
        err_mes("no data yet chosen.\nRead a data file first.");
        return;
    if dogui:
        win=evt.GetEventObject();
        win=win.GetWindow();
        with wx.FileDialog(win, "Save model, test, ref and query results in TSV files (silently overwritten). Choose base-name file (e.g. input data). It will be appended with suffixes like '_test_geneA.tsv'", defaultFile=fdata, wildcard="TSV files (*.tsv)|*.tsv", style=wx.FD_SAVE ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return # the user changed their mind

            # save the current contents in the file
            fpath=fileDialog.GetPath();
    else:
        fpath=fdata;
    fbase=fpath if fpath.lower()[-4:] != ".tsv" else fpath[:-4];
    try:
        # save *.tsv
        for dtype in ("model", "test", "ref", "qry"):
            if dtype == "model":
                fnm=fbase+"_model.tsv";
                df=resdf["model"];
                res2file(df, fnm);
                if dogui:
                    gui.mainframe.SetStatusText("Written '"+os.path.basename(fnm)+"'");
            else:
                for nm,d in resdf[dtype].items():
                    fnm=fbase+"_"+dtype+"_"+nm+".tsv";
                    res2file(d, fnm);
                    if dogui:
                        gui.mainframe.SetStatusText("Written '"+os.path.basename(fnm)+"'");
        # save .pdf
        fnm=fbase+".pdf";
        with mpdf(fnm) as pdf:
            for nm, dm in model.items():
                figure=mpl.figure.Figure(dpi=None, figsize=(8, 6));
                ax=figure.gca();
                dc=dcols[nm];
                histgmm(data.iloc[:,dc["itest"]].values, dm["par"], ax, dm["par_mod"], par_plot) # hist of test
                ax.set_title(nm);
                pdf.savefig(figure);
                #ax.close();
        if dogui:
            gui.mainframe.SetStatusText("Written '"+os.path.basename(fnm)+"'");
    except IOError:
        #import pdb; pdb.set_trace();
        err_mes("Cannot save results in file '%s'." % fpath);
    prev_res_saved=True;
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
                resdf[dtype][nm]=tls.dict2df(dm);
        else:
            resdf[dtype]={};
            for nm,d in classif.items():
                ucl=sorted(model[nm]["par"].columns);
                if dtype == "qry":
                    for nmq,dq in d[dtype].items():
                        vnm=nm+" ("+nmq+")";
                        resdf[dtype][vnm]=tls.tcol2df(class2tcol(dq, ucl));
                else:
                    resdf[dtype][nm]=tls.tcol2df(class2tcol(d[dtype], ucl));
    timeme("resdf");
    if dogui:
        for tab in ("sw_data", "sw_model", "sw_test", "sw_ref", "sw_qry", "sw_plot"):
            gtab=getattr(gui, tab);
            if tab == "sw_data":
                grid=df2grid(gtab, data);
            else:
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
        del(wait);
        prev_res_saved=False;
    timeme("dogui");
def OnReplot(evt):
    "replot in tab Plots"
    if model is None:
        return;
    # Model plots
    nb=gui.nb_plot;
    for i in range(nb.GetPageCount()-1, -1, -1):
        nb.DeletePage(i);
    for nm,dm in model.items():
        m2plot(nm, dm, nb);
    if evt is not None:
        w,h=gui.mainframe.GetSize();
        gui.mainframe.SetSize(w+1,h);
        wx.CallAfter(gui.mainframe.SetSize, w,h);
        gui.nb.SetSelection(lab2ip(gui.nb, "Plots")[0]);
    # Heatmaps
    for htype in ("ref", "test", "qry"):
        tab=getattr(gui, "sw_heat_"+htype);
        cl2heat(htype, tab, classif);
def OnSlider(evt):
    "Slider for modeling parameters was moved"
    global par_mod;
    #print("evt=", evt);
    if data is not None :
        gui.btn_remod.Enable();
    par_mod["k"]=round(gui.sl_hbin.GetValue());
    #print("sl_hbin.GetValue()=", gui.sl_hbin.GetValue());
    #print("k=", par_mod["k"]);
    par_mod["thr_di"]=gui.sl_thr_di.GetValue();
    par_mod["thr_w"]=gui.sl_thr_w.GetValue();
    gui.chk_hbin.SetLabel("  "+", ".join(vhbin(par_mod["k"]).astype(str)));
    evt.GetEventObject()._OnSlider(evt);
def OnSliderPlot(evt):
    "Slider for plot parameters was moved"
    global par_plot;
    win=evt.GetEventObject();
    par_plot[win.GetName()]=win.GetValue();
    win._OnSlider(evt);
def OnCheck(evt):
    "a checkbow was checked/unchecked"
    win=evt.GetEventObject();
    par_mod["k_var"]=win.IsChecked();
    if data is not None :
        gui.btn_remod.Enable();
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
    global par_plot;
    #import pdb; pdb.set_trace();
    win=evt.GetEventObject();
    par_plot[win.GetName()]=evt.GetColour();
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
    gtab2=wx.Panel(nb);
    nb.AddPage(gtab2, nm);
    #import pdb; pdb.set_trace();
    gtab2.SetBackgroundColour("WHITE");
    gtab2.Bind(wx.EVT_SIZE, OnSize);
    grid2=df2grid(gtab2, df);
    timeme("sub="+nm);
def m2plot(nm, dm, nb):
    gtab=wx.Panel(nb);
    nb.AddPage(gtab, nm);
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
def cl2heat(htype, pg, classif):
    if len(ids[htype]) == 0:
        return;
    # clear previous plots
    for ch in pg.GetChildren():
        ch.Destroy();
    figure=mpl.figure.Figure(dpi=None, figsize=(len(ids[htype])*0.3+1, 12));
    canvas=FigureCanvas(pg, -1, figure);
    toolbar=NavigationToolbar(canvas);
    toolbar.Realize();
    ax=[];
    if htype != "qry":
        ipl=0;
        for ctype, item in (("proba", "cl"), ("cutoff", "cutnum"), ("cutoff with confidence", "confcutnum")):
            ipl += 1;
            # extract classes of given type
            pcl=pa.DataFrame();
            cls=[]; # all classes in this htype
            for nm,d in classif.items():
                co=model[nm]["par"].columns;
                vmin=min(co);
                vmax=max(co);
                cls += co.to_list();
                pcl[nm]=d[htype][item];
            nr=pcl.shape[0];
            nid=len(ids[htype]);
            if nr > nid:
                pcl=pcl.iloc[:nid,:];
                nr=nid;
            pcl.index=ids[htype][:nr];
            # valid, i.e. non all empty rows
            dn=pcl.to_numpy();
            irv=(dn == dn).any(1)*(~tls.is_na(ids[htype][:nr]));
            pcl=pcl.iloc[irv,:];
            
            # prepare cmap
            cls=np.sort(list(set(cls)));
            clist, cmap=cl2cmap(cls, par_plot);
            # normalizer
            norm_bins=cls+0.5;
            norm_bins=np.insert(norm_bins, 0, np.min(norm_bins)-1.0);
            ## Make normalizer
            norm=mpl.colors.BoundaryNorm(norm_bins, len(cls), clip=True);
            ax.append(figure.add_subplot(310+ipl));
            im=heatmap(pcl, ax[-1], collab=(ipl == 1), cmap=cmap, norm=norm);
            ax[-1].set_title(ctype);
        figure.colorbar(im, ax=ax, ticks=cls);
    sizer=wx.BoxSizer(wx.VERTICAL);
    sizer.Add(canvas, 0);
    sizer.Add(toolbar, 0);
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
def vhbin(x):
    "produce a vector of hbin values"
    return(tls.c(np.linspace(max(10, par_mod["k"]-15), par_mod["k"], min(4, int(np.ceil((par_mod["k"]-10)/5))+1)), par_mod["k"]+np.linspace(5, 15, 3)).astype(int));
## working functions
def file2data(fn):
    "Read file name 'fn' into data.frame"
    global data, dcols, ids;
    try:
        data=pa.read_csv(fn, header=None, sep="\t");
    except:
        err_mes("file '"+fn+"' could not be read");
        return;
    cols=[str(v).strip() if v==v else "" for v in data.iloc[0, :]];
    data.columns=cols;
    data=data.iloc[1:,:];
    iparse=[]; # collect parsed columns
    # search for (ref) and (test)
    suff="(ref)";
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
        for nmq in dqry.keys():
            iq=dqry[nmq]["i"];
            iparse.append(iq);
            iid=iq-1 if iq > 0 and cols[iq-1].lower() == "id" else None;
            dqry[nmq]["id"]=iid;
            if iid is not None:
                iparse.append(iid);
        dcols[nm]["qry"]=dqry;
    #tls.aff("dcols", dcols);
    # gather ids. id (ref) and id (test) are unique. id_qry (name) may be multiple
    ids=dict();
    for suff in ("ref", "test"):
        ids[suff]=dict((i, None) for i,v in enumerate(cols) if re.match("id *\("+suff+"\)$", str(v)));
        if len(ids[suff]) > 1:
            err_mes("Column 'id ("+suff+") is not unique, cf. columns: "+", ".join(str(i+1) for i in ids[suff].keys()));
        if ids[suff]:
            icol=list(ids[suff].keys())[0];
            idh=data.iloc[:,icol]; # id here
            iu,ic=np.unique(idh[idh == idh], return_counts=True);
            if np.max(ic) > 1:
                err_mes("ID column '"+cols[icol]+"' ("+str(icol+1)+") in '"+os.path.basename(fn)+"' has non unique entries. Each ID must be unique.");
                return;
            ids[suff]=idh[~tls.is_na_end(idh)];
            iparse.append(icol);
    # each id_qry (name) is relative to next qrys till next id_qry is found
    ids["qry"]=dict((v[6:].strip("( )"), i) for i,v in enumerate(cols) if v.startswith("id_qry"));
    # collect qry icols for each block
    ib=list(ids["qry"].values());
    nb=len(ids["qry"]);
    for i,nmb in enumerate(ids["qry"].keys()):
        icol=ids["qry"][nmb];
        iparse.append(icol);
        idh=data.iloc[:,icol]; # id here
        iu,ic=np.unique(idh[idh == idh], return_counts=True);
        if np.max(ic) > 1:
            err_mes("ID column '"+cols[icol]+"' ("+str(icol+1)+") in '"+os.path.basename(fn)+"' has non unique entries. Each ID must be unique.");
            return;
        iend=ib[i]+1 if i < nb-1 else len(cols);
        nmqs=[(nmm, nmq) for nmm,d in dcols.items() for nmq,dq in d["qry"].items() if dq["i"] > icol and dq["i"] <= iend]; # collection of tuples (marker_name; qry_name)
        ids["qry"][nmb]=nmqs;
    #print("ids=", ids);
    # check that all columns are used
    iparse=set(iparse);
    for i,nm in enumerate(cols):
        if nm and i not in iparse:
            warn_mes("Column '"+nm+"' is not categorized in any of: ref, test, query or id of one of these");
    if dogui:
        gui.mainframe.SetCursor(wx.Cursor(wx.CURSOR_WAIT));
    # convert to float
    for nm,dc in dcols.items():
        for i in [dc["iref"], dc["itest"], *[dq["i"] for nmq,dq in dc["qry"].items()]]:
            data.iloc[:,i]=data.iloc[:,i].to_numpy(float);
    OnRemodel(None);
    if dogui:
        gui.mainframe.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
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
                vbin=vhbin(par_mod["k"]);
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
def class2tcol(d, ucl):
    "Format classification in d in tuple-column collection"
    # prepare text table
    x=d["x"];
    tcol=[("x", x)];
    # add class & repartition
    #ucl=sorted(set(tls.na_omit(d["cl"])));
    for cl,clname in (("cl", "proba"), ("cutnum", "cutoff"), ("confcutnum", "with confidence")):
        #import pdb; pdb.set_trace();
        tcol.append((clname, []));
        if clname == "proba":
            tcol.append(("max", d["wmax"]));
        vcl=d[cl].astype(object);
        i=tls.which(~tls.is_na(vcl));
        vcl[i]=vcl[i].astype(int);
        tcol.append(("class", vcl));
        #import pdb; pdb.set_trace();
        
        dstat={"x": x.describe().astype(object)};
        for icl in ucl:
            xcl=x[tls.which(vcl==icl)];
            tcol.append((str(icl), xcl));
            dstat[str(icl)]=xcl.describe().astype(object);
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
        if fdata:
            fpath=os.path.join(wd, re.sub("\.tsv", "", fdata)+"_res.tsv");
        else:
            raise Exception("fpath is not set for writing");
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
    return("%02d:%02d:%02d.%02d"%(hh,mm,ss,cc));
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
    cneg=[colorFader(par_plot["col_neghigh"], par_plot["col_neglow"], i/nneg) for i in range(nneg)];
    npos=sum(cls>0);
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
    global gui, bg_grey;
    gui=wx.Object();
    gui.app=wx.App();
    wx.lib.colourdb.updateColourDB();
    code=tls.wxlay2py(tls.kvh2tlist(os.path.join(diri, "g3mclass", "g3mclass_lay.kvh")), pref="gui.");
    exec(code);
## take arguments
def main():
    global fdata, wd, gui, dogui, TIMEME, nproc;
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
    fdata=args[0] if len(args) else "";
    if fdata and fdata.lower()[-4:] != ".tsv":
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
        #print("todo: write all results");
        OnRemodel(None);
        OnSave(None);
    if dogui:
        gui.app.MainLoop();
if __name__ == "__main__":
    main();
