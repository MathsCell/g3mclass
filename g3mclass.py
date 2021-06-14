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
import wx.lib.mixins.inspection as wit
import matplotlib as mpl
from matplotlib.backends.backend_wxagg import (
    FigureCanvasWxAgg as FigureCanvas,
    NavigationToolbar2WxAgg as NavigationToolbar)

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
        self.ShowScrollbars(True, True);
        if bg_grey is None:
            bg_grey=self.GetLabelBackgroundColour();
        #self.SetDefaultCellBackgroundColour(bg_grey);
        parent.grid=self;
        for j in range(ncol):
            self.SetColLabelValue(j, str(nmc[j]));
            vcol=df.iloc[:,j].to_numpy();
            empty=np.all(tls.is_na(vcol)) or np.all(vcol.astype(str)=="");
            empty_end=tls.is_empty_end(vcol) | tls.is_na_end(vcol);
            for k in range(nrow):
                if empty or empty_end[k]:
                    break;
                    self.SetCellValue(k, j, "");
                    #self.SetCellBackgroundColour(k, j, bg_grey);
                else:
                    #self.SetCellBackgroundColour(k, j, bg_white);
                    val=vcol[k];
                    val=str(val) if val == val else "";
                    self.SetCellValue(k, j, val);
        self.AutoSize();
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
#me=os.path.basename(sys.argv[0]);
me="G3Mclass";
# message in welcome tab
with open(os.path.join(diri, "g3mclass", "welcome.html"), "r") as fp:
    welc_text=fp.read() % {"me": me};
welc_text=re.sub("\n\n", "<br>\n", welc_text);
with open(os.path.join(diri, "g3mclass", "licence_en.txt"), "r") as fp:
    licenseText=fp.read();

## global vars
lock=threading.Lock();
gui=wx.Object();
dogui=False;
fdata=""; # name of data file
data=None;
dcols={};
resdf=None; # dict for formatted output in .tsv
par_mod={
    "k": 25,
    "k_var": False,
    "thr_di": 0.5,
    "thr_w": 1.,
};
canvas=None; # plotting canvas
sett_inp=None; # dictionary of input widgets for settings
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
    under the 'File' menu. Results are stored in <fdata>_test_geneA.tsv, <fdata>_ref_geneA.tsv and so on.
    """
    global fdata, resdf;
    if not fdata:
        # data is not yet choosed
        err_mes("no data yet chosen.\nRead a data file first.");
        return;
    if dogui:
        win=evt.GetEventObject();
        win=win.GetWindow();
        with wx.FileDialog(win, "Save model, test, ref and query results in TSV files (silently overwritten). Choose base-name file (e.g. input data). It will be appended with suffixes like '_test_geneA.tsv'", wildcard="TSV files (*.tsv)|*.tsv", style=wx.FD_SAVE ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return # the user changed their mind

            # save the current contents in the file
            fpath=fileDialog.GetPath();
    else:
        fpath=fdata;
    fbase=fpath if fpath.lower()[-4:] != ".tsv" else fpath[:-4];
    try:
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
    except IOError:
        #import pdb; pdb.set_trace();
        err_mes("Cannot save results in file '%s'." % fpath)
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
    global resdf;
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
                if dtype == "qry":
                    for nmq,dq in d[dtype].items():
                        vnm=nm+" ("+nmq+")";
                        resdf[dtype][vnm]=tls.tcol2df(class2tcol(dq));
                else:
                    resdf[dtype][nm]=tls.tcol2df(class2tcol(d[dtype]));
    timeme("resdf");
    if dogui:
        for tab in ("sw_data", "sw_model", "sw_test", "sw_ref", "sw_qry", "sw_plot"):
            gtab=getattr(gui, tab);
            if False and "grid" in dir(gtab):
                # destroy the previous grid
                gtab.grid.Destroy();
                gtab.SetVirtualSize((0, 0));
                delattr(gtab, "grid");
            if tab == "sw_data":
                grid=df2grid(gtab, data);
            elif False and tab == "sw_model":
                grid=df2grid(gtab, tls.dict2df(model));
            elif tab in ("sw_model", "sw_test", "sw_ref", "sw_qry", "sw_plot"):
                dtype=tab[3:];
                if False and "grid" in dir(gtab):
                    gtab.grid.Destroy();
                    delattr(gtab, "grid");
                # remove previous sub-pages and create one page per variable (e.g. gene)
                nb=getattr(gui, "nb_"+dtype);
                #print("tab=", tab, "; nb=", nb);
                for i in range(nb.GetPageCount()-1, -1, -1):
                    nb.DeletePage(i);
                nb.SetSize(400, 300); # fixes warning "gtk_box_gadget_distribute: assertion 'size >= 0' failed"
                if tab == "sw_plot":
                    for nm,dm in model.items():
                        m2plot(nm, dm, nb);
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
    timeme("dogui");
def OnSlider(evt):
    "Slider was moved"
    global par_mod;
    #print("evt=", evt);
    if not data is None :
        gui.btn_remod.Enable();
    par_mod["k"]=round(gui.sl_hbin.GetValue());
    #print("sl_hbin.GetValue()=", gui.sl_hbin.GetValue());
    #print("k=", par_mod["k"]);
    par_mod["thr_di"]=gui.sl_thr_di.GetValue();
    par_mod["thr_w"]=gui.sl_thr_w.GetValue();
    gui.chk_hbin.SetLabel("  "+", ".join(vhbin(par_mod["k"]).astype(str)));
    evt.GetEventObject()._OnSlider(evt);
def OnCheck(evt):
    "a checkbow was checked/unchecked"
    win=evt.GetEventObject();
    par_mod["k_var"]=win.IsChecked();
    if not data is None :
        gui.btn_remod.Enable();
def OnTabChange(evt):
    #import pdb; pdb.set_trace();
    win=evt.GetEventObject();
    i=win.GetSelection();
    for nb in (gui.nb_model, gui.nb_test, gui.nb_ref, gui.nb_plot):
        if win is nb:
            continue;
        nb.SetSelection(i);
def ToDo(evt):
    """
    A general purpose "we'll do it later" dialog box
    """
    win=evt.GetEventObject().GetTopLevelParent();
    dlg = wx.MessageDialog(win, "Not Yet Implimented! evt="+str(dir(evt)), "ToDo",
                         wx.OK | wx.ICON_INFORMATION);
    dlg.ShowModal();
    dlg.Destroy();
def d2grid(nm, df, nb, lock=None):
    #print("nm=", nm, "; nb=", nb, "lock=", lock);
    if not lock is None:
        #print(nm+" waiting for lock1");
        lock.acquire();
        #print(nm+" lock1 is aquired");
    gtab2=wx.Panel(nb);
    nb.AddPage(gtab2, nm);
    #import pdb; pdb.set_trace();
    if not lock is None:
        time.sleep(0.1);
        lock.release();
        #print(nm+" lock1 is released");
    #gtab2.SetSizer(wx.BoxSizer(wx.VERTICAL));
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
    t=dcols[nm];
    tls.histgmm(data.iloc[:,t[1]], dm["par"], ax, dm["par_mod"], alpha=0.3) # hist of test
    ax.set_title(nm);
    sizer=wx.BoxSizer(wx.VERTICAL);
    sizer.Add(canvas, 1, wx.EXPAND);
    sizer.Add(toolbar, 0, wx.LEFT | wx.EXPAND);
    gtab.SetSizer(sizer);
    

# working horses
def err_mes(mes):
    "Show error dialog in GUI mode or raise exception"
    if dogui:
        dlg=wx.MessageDialog(None, mes, "Error", wx.OK | wx.ICON_ERROR);
        dlg.ShowModal()
        dlg.Destroy();
    else:
        raise Exception(me+": "+mes);
def vhbin(x):
    "produce a vector of hbin values"
    return(tls.c(np.linspace(max(10, par_mod["k"]-15), par_mod["k"], min(4, int(np.ceil((par_mod["k"]-10)/5))+1)), par_mod["k"]+np.linspace(5, 15, 3)).astype(int));
## working functions
def file2data(fn):
    "Read file name 'fn' into data.frame"
    global data, dcols;
    try:
        data=pa.read_csv(fn, header=None, sep="\t");
    except:
        err_mes("file '"+fn+"' could not be read");
        return;
    cols=[str(v).strip() if v==v else "" for v in data.iloc[0, :]];
    # search for (ref) and (test)
    suff=" (ref)";
    dcols=dict((i, re.sub(tls.escape(suff, "()")+"$", "", v).strip()) for i,v in enumerate(cols) if v.endswith(suff))
    if not dcols:
        err_mes("not found '"+suff+"' in column names");
        return;
    # check that varnames are unique and non empty
    cnt=tls.list2count(dcols.values());
    if len(cnt) != len(dcols):
        vbad=[v for v,i in cnt.items() if i > 1];
        err_mes("following column name is not unique in ' (ref)' set: '"+vbad[0]+"'");
        return;
    
    # build dcols: varname => (icolref, icoltest, icolid, qry_dict). icolid can be None, qry_dict can be empty
    dcols=dict((v,k) for k,v in dcols.items());
    for nm in dcols.keys():
        # check that every ref has its test pair
        itest=[i for i,v in enumerate(cols) if v.startswith(nm) and v.endswith(" (test)") and re.match("^ *$", v[len(nm):-7])];
        if not itest:
            err_mes("column '"+nm+" (ref)' has not its counter part '"+nm+" (test)'");
            return;
        elif len(itest) > 1:
            err_mes("following column name is not unique in '(test)' set: '"+nm+"'");
            return;
        else:
            dcols[nm]=(dcols[nm],itest[0]);
        iid=[i for i,v in enumerate(cols) if v.startswith(nm) and v.lower().endswith(" (id)") and re.match("^ *$", v[len(nm):-5])];
        if len(iid) > 1:
            err_mes("following column name is not unique in '(id)' set: '"+nm+"'");
            return;
        else:
            dcols[nm]=(*dcols[nm], iid[0] if len(iid) else None);
        # get query (if any)
        dqry=dict((i,v[len(nm)+1:].strip("( )")) for i,v in enumerate(cols) if v.startswith(nm+" ") and not v.endswith(" (test)") and not v.endswith(" (ref)") and not v.endswith(" (id)"));
        # check that qry names are unique
        cnt=tls.list2count(dqry.values());
        if len(cnt) < len(dqry):
            err_mes("following column name is not unique in ' (query)' set: '"+nm+" "+[v for v,i in cnt.items() if i > 1][0]+"'");
            return;
        dcols[nm]=(*dcols[nm], dqry);
    
    #tls.aff("dcols", dcols);
    data.columns=cols
    data=data.iloc[1:,:]
    # convert to float
    for nm,t in dcols.items():
        data.iloc[:,t[0]]=np.asarray(data.iloc[:,t[0]], float);
        data.iloc[:,t[1]]=np.asarray(data.iloc[:,t[1]], float);
        for iq,qnm in t[3].items():
            # qry is present
            data.iloc[:,iq]=np.asarray(data.iloc[:,iq], float);
    OnRemodel(None);
#def onScrollGrid(obj, event):
#    import pdb; pdb.set_trace();
    
def data2model(data, dcols):
    "Learn models for each var in 'data' described in 'dcols'. Return a dict with models pointed by varname"
    if len(dcols) > 1 and not par_mod["k_var"]:
        with mp.Pool(min(len(dcols), mp.cpu_count())) as pool:
        #with thpool(min(len(dcols), os.cpu_count())) as pool:
            res=pool.map(tls.starfun, ((tls.rt2model, data.iloc[:,t[0]].to_numpy(), data.iloc[:,t[1]].to_numpy(), par_mod) for t in dcols.values()));
        res=dict(zip(dcols.keys(), res));
    else:
        res=dict();
        for nm,t in dcols.items():
            ref=np.asarray(data.iloc[:,t[0]]);
            test=np.asarray(data.iloc[:,t[1]]);
            if par_mod["k_var"]:
                # run hbin numbers through vbin and get the best BIC
                vbin=vhbin(par_mod["k"]);
                #import pdb; pdb.set_trace();
                dl=dict();
                par_loc=[(dl.update({"tmp": par_mod.copy()}), dl["tmp"].update({"k": nbin}), dl["tmp"])[-1] for nbin in vbin]; # create n copies of par_mod with diff hbin
                with mp.Pool(min(len(dcols), mp.cpu_count())) as pool:
                #with thpool(min(len(dcols), os.cpu_count())) as pool:
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
    for nm,t in dcols.items():
        ref=np.asarray(data.iloc[:,t[0]]);
        ref=ref[~tls.is_na_end(ref)];
        test=np.asarray(data.iloc[:,t[1]]);
        test=test[~tls.is_na_end(test)];
        res[nm]={
            "ref": tls.xmod2class(ref, model[nm]),
            "test": tls.xmod2class(test, model[nm]),
            "qry": dict((v, tls.xmod2class(np.asarray(data.iloc[:,k]), model[nm])) for k,v in t[3].items())
        };
    return(res);
def class2tcol(d):
    "Format classification in d in tuple-column collection"
    # prepare text table
    x=d["x"];
    tcol=[("x", x)];
    # add class & repartition
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
        ucl=np.sort(tls.na_omit(list(set(vcl)))).astype(int);
        dstat={"x": x.describe().astype(object)};
        for icl in ucl:
            xcl=x[tls.which(vcl==icl)];
            tcol.append((str(icl), xcl));
            dstat[str(icl)]=xcl.describe().astype(object);
        dstat=pa.DataFrame(dstat);
        dstat.loc["count"]=dstat.loc["count"].astype(int);
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
    global gui, bg_grey;
    gui=wx.Object();
    gui.app=wx.App();
    code=tls.wxlay2py(tls.kvh2tlist(os.path.join(diri, "g3mclass", "g3mclass_lay.kvh")), pref="gui.");
    exec(code);
## take arguments
def main():
    global fdata, wd, gui, dogui, TIMEME;
    try:
        opts,args=getopt.getopt(sys.argv[1:], "hwvt", ["help", "DEBUG"]);
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
        else:
            assert False, "unhandled option";
    if dogui:
        make_gui();
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
