#! /usr/bin/env python3
import tools_g3m as tls;
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
nmrt=("femalegluc (ref)", "femalegluc (test)");
par_loc=par_mod.copy();
par_loc["k"]=35;
data=pa.read_csv(fnm, sep="\t");
ref=np.array(data[nmrt[0]]);
ref=ref[~tls.is_na_end(ref)];
test=np.array(data[nmrt[1]]);
test=test[~tls.is_na_end(test)];
#warnings.simplefilter("error");
#if let == "B":
cpar=tls.rt2model(ref, test, par_loc);
classif=dict();
classif["ref"]=tls.xmod2class(ref, cpar);
classif["test"]=tls.xmod2class(test, cpar);
tls.obj2kvh({"model": cpar, "classification": classif}, None, fp=fnm[:-4]+".kvh");

plt.figure(nmrt[1]);
import pdb; pdb.set_trace();
tls.histgmm(test, cpar["par"], plt, cpar["par_mod"], par_plot) # hist of test

plt.show();
