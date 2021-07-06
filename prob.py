#! /usr/bin/env python3
import tools_g3m as tls;
import g3mclass as g3m;

import warnings;
import wx;
import pandas as pa;
#import autograd.numpy as np;
#from autograd import elementwise_grad as egrad;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;
from matplotlib.backends.backend_pdf import PdfPages as mpdf;
#import warnings;

nan=np.nan;
Inf=np.inf;

par_mod={
    "k": 25,
    "k_var": False,
    "k_var_hlen": 5,
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
}

n=100;
mean=[-1, 1];
sd=[0.5, 0.5];
a=[1, 1];
par=pa.DataFrame(np.array([a, mean, sd]), index=["a", "mean", "sd"]);
x=np.array(list(np.random.normal(mean[i], sd[i], int(n/len(mean))) for i in range(len(mean)))).flatten();
#print("x=", x);
w=tls.e_step1(x, par=par);
#print("w=", w);
m1=tls.m_step1(x, w);
#print("m1=", m1);

imposed=pa.DataFrame(np.array([nan, -1, 0.5], float).reshape((3, 1)), index=["a", "mean", "sd"]);
m1i=tls.m_step1(x, w, imposed);
#print("m1i=", m1i);

#x[0]=nan;
tls.DEBUG=False;
res=tls.em1(x, maxit=100);
#print("res=", res["win"]);
rese=tls.em1(x, par=par, G=2, maxit=0);
#print("rese=", rese["win"]);
#m2=tls.m_step1(x, w, imposed, classify=True);
#print("m2=", m2);
cl=tls.gmmcl(x, res["win"]["par"]);
cl0=tls.gcl2i(cl["cl"], res["win"]["par"]);
#print("cl=", cl["cl"], "cl0=", cl0);
xn=x.copy();
xn[0]=nan;
cln=tls.gmmcl(xn, res["win"]["par"]);
#print("cln=", cln);

#plt.figure(100);
#tls.histgmm(x, res["win"]["par"], plt);
#plt.show(block=False);

# plot 0G weight
if False:
    xp=np.linspace(-5, 5, 301);
    plt.figure(200);
    plt.plot(xp, tls.fw(xp, par, 0));
    plt.plot(xp, tls.fw_d1(xp, par, 0));
    fw_d2=egrad(tls.fw_d1);
    plt.plot(xp, fw_d2(xp, par, 0));
    plt.show(block=False);
if False:
    xp=np.linspace(-2, 2, 301);
    plt.figure(300);
    plt.plot(xp, tls.fw(xp, res["win"]["par"]));
    plt.plot(xp, tls.fw_d1(xp, res["win"]["par"]));
    fw_d2=egrad(tls.fw_d1);
    plt.plot(xp, fw_d2(xp, res["win"]["par"]));
    plt.show(block=False);
# test roothalf()
#print("rh=", tls.roothalf(0, 1, par));

# Gaussian derivatives
if False:
    xp=np.linspace(-5, 5, 301)
    plt.plot(xp, tls.dnorm(xp));
    plt.plot(xp, tls.dnorm_d1(xp));
    plt.plot(xp, tls.dnorm_d2(xp));
    plt.show(block=False);

# ref-test try
#test=x.copy();
#ref=np.random.normal(par.loc["mean", 0], par.loc["sd", 0], 20);
fnm="male_female_gluc_bmi.tsv";
nmref=("malegluc (ref)", "malebmi (ref)", "femalegluc (ref)", "femalebmi (ref)");
nmtest=("malegluc (test)", "malebmi (test)", "femalegluc (test)", "femalebmi (test)");

nmrt=(nmref[0], nmtest[0]);
par_loc=par_mod.copy();
par_loc["k"]=35;
data=pa.read_csv(fnm, sep="\t");
classif=dict();
model=dict();
for nmrt in zip(nmref, nmtest):
	nmm=nmrt[0][:-6];
	ref=np.array(data[nmrt[0]]);
	ref=ref[~tls.is_na_end(ref)];
	test=np.array(data[nmrt[1]]);
	test=test[~tls.is_na_end(test)];
	#warnings.simplefilter("error");
	#if let == "B":
	model[nmm]=tls.rt2model(ref, test, par_loc);
	cpar=model[nmm];
	classif[nmm]=dict();
	classif[nmm]["ref"]=tls.xmod2class(ref, cpar);
	classif[nmm]["test"]=tls.xmod2class(test, cpar);
	#tls.obj2kvh({"model": cpar, "classification": classif}, None, fp=fnm[:-4]+".kvh");

#plt.figure(nmrt[1]);
#import pdb; pdb.set_trace();
#tls.histgmm(test, cpar["par"], plt, cpar["par_mod"], par_plot) # hist of test

# heatmap of test classif
htype="test";
idh=np.arange(len(test));
nid=len(idh);
cls=[];
for nm,d in classif.items():
	cls += model[nm]["par"].columns.to_list();
cls=np.sort(list(set(cls)));
figsize=(len(idh)*0.1+12, len(nmtest)*0.1+12);
#print("htype=", htype, "figsize=", figsize);
#figure=mpl.figure.Figure(dpi=100, figsize=figsize);
figure=plt.figure(dpi=100, figsize=figsize);
figure.suptitle(htype, fontsize=16);
ctype, item=("proba", "cl");
# extract classes of given type
pcl=pa.DataFrame();
for nm,d in classif.items():
	pcl[nm]=d[htype][item];
nr=pcl.shape[0];
if nr > nid:
	pcl=pcl.iloc[:nid,:];
	nr=nid;
pcl.index=idh[:nr];
# valid, i.e. non all empty rows
dn=pcl.to_numpy();
irv=(dn == dn).any(1)*(~tls.is_na(idh[:nr]));
pcl=pcl.iloc[irv,:];

# prepare cmap
g3m.main();
clist, cmap=g3m.cl2cmap(cls, par_plot);
# normalizer
norm_bins=cls+0.5;
norm_bins=np.insert(norm_bins, 0, np.min(norm_bins)-1.0);
## Make normalizer
norm=mpl.colors.BoundaryNorm(norm_bins, len(cls), clip=True);
ax=figure.add_subplot(111);
figure.subplots_adjust(hspace = 0.5);
im=g3m.heatmap(pcl, ax, collab=True, cmap=cmap, norm=norm);
ax.set_title(ctype);
position=figure.add_axes([0.93, 0.3, 0.02, 0.35])  ## the parameters are the specified position you set 
figure.colorbar(im, ticks=cls, cax=position);
warnings.filterwarnings("ignore");
figure.tight_layout(rect=[0, 0, 0.9, 1.0]);
import pdb; pdb.set_trace();
warnings.filterwarnings("default");

plt.show();
pass;
