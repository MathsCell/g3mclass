import sys;
from pathlib import Path;
import pandas as pa;
import csv;
import numpy as np;
np.seterr(all="ignore");
import numpy.ma as nma;
from io import StringIO;
import wx;
import matplotlib as mpl;
from math import erf, fabs, nan;
from distutils.util import strtobool;

DEBUG=False;
nan=np.nan;
Inf=np.inf;

# translate gmm class to 0-ref class numbers
#cl0br=np.array([-Inf,-2,-1,0,1,Inf]) # breaks for 0-ref classes
#cl0lab=np.array(["down-deeper", "down", "ref", "up", "up-higher"]) # labels for these breaks
# (stringent) cutoff class names to numbers -> cl2i
#cl2i=pa.DataFrame({"ref": 0, "ref-down": 0, "ref-up": 0, "down-deeper": -2, "down": -1, "up": 1, "up-higher": 2, "N/A": nan}, index=[0])

def aff(name, obj, ident=0, f=sys.stdout):
    saveout=sys.stdout
    sys.stdout=f;
    to=type(obj);
    if to == type({}):
        # dictionary case
        print('|'*ident+'+'+str(name)+' #'+str(len(obj)));
        for k in obj:
            aff('{'+str(k)+'}', obj[k], ident+1, f);
    elif to == type(()):
        # tuple case
        print('|'*ident+'+'+str(name)+' #'+str(len(obj)));
        for (i,k) in enumerate(obj):
            aff('('+str(i)+')', obj[i], ident+1, f);
    elif to == type([]):
        # list case
        print('|'*ident+'+'+str(name)+' #'+str(len(obj)));
        for (i,k) in enumerate(obj):
            aff('['+str(i)+']', obj[i], ident+1, f);
    else:
        print('%s%s: %s' % ('|'*ident+'+', name, obj));
    sys.stdout=saveout;
def join(c,l,p='',s='',a=''):
    """join the items of the list (or iterator) l separated by c.
    Each item is prefixed with p and suffixed with s.
    If the join result is empty for any reason, an alternative a is returned.
    p, s and a are optional"""
    i=0;
    return c.join(p+str(i)+s for i in l) or a;
def list2count(l, incr=1):
    """count values in list l incrementing the counter by optional incr
    and return dictionary {item:count}"""
    dico={};
    for item in l:
        dico[item]=dico.get(item,0)+incr;
    return dico;
def isstr(s):
    """returns True if the argument is a string""";
    return isinstance(s,type(""));
def trd(l, d, p="", s="", a=""):
    """translate items in an iterable l by a dictionary d, prefixing
    translated items by optional p and suffixing them by optional s.
    If an item is not found in the dictionnary alternative string a is used.
    If a==None, the item is left unchanged.
    No prefix or suffix are applied in both case.
    Returns an iterator"""
    return (p+str(d[i])+s if i in d else i if a==None else a for i in l);
def s2bif(s):
    "try to convert s to bool, int, float. If failed, leave it as is"
    res=s;
    for t in (strtobool, int, float):
        try:
            res=t(s);
            break;
        except:
            continue;
    return(res);
def kvhd2type(d, conv=s2bif):
    "Recursively convert values in d to conv(d)"
    return(dict((k,conv(v)) if isstr(v) else (k, kvhd2type(v)) for k,v in d.items()));
def kvh2tlist(fp, lev=[0], indent=[0]):
    """kvh2tlist(fp, lev=[0], indent=[0])
    Read a kvh file from fp stream descriptor
    and organize its content in list of tuples [(k1,v1), (k2,[(k2.1, v2.1)])]
    If fp is a string, it is used in open() operator
    """
    # check the stream
    open_here=False;
    if isstr(fp) or type(fp) == type(Path()):
        fp=open(fp, "r");
        fp.seek(0);
        open_here=True;
    # error control
    if lev[0] < 0 or indent[0] < 0:
        raise NameError("lev=%d, indent=%d both must be positive"%(lev[0], indent[0]));
    if lev[0] < indent[0]:
        raise NameError("lev=%d, indent=%d, lev must be greater or equal to indent"%(lev[0], indent[0]));
    if lev[0] > fp.tell():
        raise NameError("lev=%d, file position=%d, lev must be less or equal to file position"%(lev[0], fp.tell()));
    if indent[0] > fp.tell():
        raise NameError("indent=%d, file position=%d, indent must be less or equal to file position"%(indent[0], fp.tell()));
    # algorithm:
    # advance to requested indent (=level)
    # if not sucsessful return an empty list
    # read a key 
    # if sep==\t read value
    # elif sep=\n
    #     recursive call
    #     if no result at the level+1 put empty value
    # else put empty value
    tlist=[];
    key="";
    val="";
    if DEBUG:
        import pdb; pdb.set_trace();##
    while True:
        # current position is supposed to point to the begining of a key
        # so go through an appropriate tab number for the current level
        while indent[0] < lev[0]:
            char=fp.read(1);
            if char != "\t":
                if char != "":
                    fp.seek(fp.tell()-1,0);
                break;
            indent[0]+=1;
        if indent[0] < lev[0]:
            # we could not read till the requested level
            # so the current level is finished;
            if open_here:
                fp.close();
            return tlist;
        (key,sep)=kvh_read_key(fp);
        if sep=="\t":
            tlist.append((key, kvh_read_val(fp)));
            indent[0]=0;
        elif sep=="\n":
            lev[0]+=1;
            indent[0]=0;
            nextlist=kvh2tlist(fp, lev, indent);
            lev[0]-=1;
            if len(nextlist)==0:
                # no value and no deeper level
                tlist.append((key, ""));
            else:
                tlist.append((key, nextlist));
        else:
            # we are at the end of file
            if indent[0] or key:
                tlist.append((key, ""));
            indent[0]=0;
            lev[0]=0;
            if open_here:
                fp.close();
            return tlist;
def kvh_read_key(fp):
    """kvh_read_key(fp)
    Read a string from the current position till the first unescaped
    \t, \n or the end of stream fp.
    Return tuple (key, sep). sep=None at the end of the stream"""
    #pdb.set_trace();##
    key="";
    while True:
        char=fp.read(1);
        if char=="\\":
            # try to read next char if any
            nextchar=fp.read(1);
            if nextchar=="":
                # end of file
                return (key, None);
            else:
                # just add escaped char
                key+=nextchar;
        elif char=="\t" or char=="\n":
            return (key, char);
        elif char=="":
            return (key, None);
        else:
            # just add a plain char
            key+=char;
def kvh_read_val(fp):
    """kvh_read_val(fp)
    Read a string from current position till the first unescaped
    \n or the end of file.
    Return the read string."""
    val="";
    while True:
        char=fp.read(1);
        if char=="\\":
            # try to read next char if any
            nextchar=fp.read(1);
            if nextchar=="":
                # end of file
                return val;
            else:
                # just add escaped char
                val+=nextchar;
        elif char=="\n" or char=="":
            return val;
        else:
            # just add a plain char
            val+=char;
def kvh_tlist2dict(tlist):
    """kvh_tlist2dict(tlist)
    Translate a tlist structure read from a kvh file to
    a hierarchical dictionnary. Repeated keys at the same level
    of a dictionnary are silently overwritten"""
    return dict((k,(v if isstr(v) else kvh_tlist2dict(v))) for (k,v) in tlist);
def kvh2dict(fp):
    """kvh2dict(fp)
    Read a kvh file from fp pointer then translate its tlist
    structure to a returned hierarchical dictionnary.
    Repeated keys at the same level of a dictionnary are
    silently overwritten"""
    return kvh_tlist2dict(kvh2tlist(fp));
def dict2kvh(d, fp=sys.stdout, indent=0, dig=None):
    """dict2kvh(d, fp=sys.stdout, indent=0)
    Write a nested dictionary on the stream fp (stdout by default). 'dig' is digit number for rounding.
    """
    open_here=False;
    if isstr(fp) or type(fp) == type(Path()):
        open_here=True;
        fp=open(fp, "w");
    for (k,v) in d.items():
        if issubclass(type(v), dict):
            # recursive call with incremented indentation
            fp.write("%s%s\n"%("\t"*indent, escape(str(k), "\t\\\n")));
            dict2kvh(v, fp, indent+1, dig=dig);
        elif issubclass(type(v), pa.DataFrame):
            obj2kvh(v, k, fp, indent, dig=dig);
        else:
            obj2kvh(v, k, fp, indent, dig=dig);
            #fp.write("%s%s\t%s\n" % ("\t"*indent, escape(str(k), "\t\\\n"), escape(str(v), "\\\n")));
    if open_here:
        fp.close();
def obj2kvh(o, oname=None, fp=sys.stdout, indent=0, dig=None):
    "write data.frame or dict to kvh file. 'dig' is digit number for rounding"
    open_here=False;
    if isstr(fp) or type(fp) == type(Path()):
        open_here=True;
        fp=open(fp, "w");
    have_name=oname != None;
    if have_name:
        fp.write("%s%s" % ("\t"*indent, escape(str(oname), "\t\\\n")));
    to=type(o);
    if issubclass(to, list) or issubclass(to, tuple):
        if have_name:
            fp.write("\n");
        for i,v in enumerate(o):
            obj2kvh(v, str(i), fp, indent+1, dig=dig);
    elif issubclass(to, dict):
        if have_name:
            fp.write("\n");
        dict2kvh(o, fp, indent+have_name);
    elif issubclass(to, pa.DataFrame):
        if have_name:
            fp.write("\n");
        fp.write("\t"*(indent+have_name)+"row_col\t"+"\t".join(escape(v, "\\\n") for v in o.columns)+"\n");
        s=o.to_csv(header=False, sep="\t", quoting=csv.QUOTE_NONE, na_rep="", float_format=None if dig is None else "%."+str(int(dig))+"g");
        li=s.split("\n");
        if len(li) == o.shape[0]+1:
            fp.write("\t"*(indent+have_name)+("\n"+"\t"*(indent+have_name)).join(li[:-1])+"\n");
        else:
            raise Exception("Not yet implemented newline in data.frame")
    elif issubclass(to, float):
        if dig is None:
            fp.write("\t%s\n" % str(o));
        else:
            fp.write("\t%s\n" % str(round(o, dig)));
    else:
        fp.write("\t%s\n" % (escape(str(o), "\\\n")));
    if open_here:
        fp.close();
def escape(s, spch="|&;<>()$`\\\"' \t\n*?[#~=%", ech="\\"):
    """escape(s, spch="|&;<>()$`\\\"' \t\n*?[#~=%", ech="\\")
escape special characters in s. The especial characters are listed in spch.
Escaping is done by putting an ech string before them.
Default spch and ech corresponds to quoting Shell arguments
in accordance with
http://www.opengroup.org/onlinepubs/009695399/utilities/xcu_chap02.html
Example: os.system("ls %s" % escape(file_name_with_all_meta_chars_but_newline));
NB.
1. Escaped <newline> is removed by a shell if not put
in a single-quotted string (' ')
2. A single-quote character even escaped cannot appear in a
single-quotted string
"""
    return "".join((ech+c if c in spch else c) for c in str(s));
def kvh_getv_by_k(kvt, kl):
    """kvh_getv_by_k(kvt, kl)->None|String|kvh tlist
    get value from kvt (kvh tlist) according to the key hierarchy
    defined in the list of keys kl. Return None if no key is found
    """
    for (k,v) in kvt:
        if k==kl[0]:
            # found
            if len(kl) == 1:
                return(v);
            elif len(kl) > 1:
                # recursive call
                return(kvh_getv_by_k(v, kl[1:]));
def dict2df(d, dig=None):
    "Return a dict 'd' converted to DataFrame in kvh way. 'dig' is a digit number for rounding"
    fp=StringIO();
    dict2kvh(d, fp, dig=dig);
    s=fp.getvalue();
    fp.close();
    if s[-1] == "\n":
        s=s[:-1]; # strip the last newline
    li=s.split("\n");
    nrow=len(li);
    dl=locals();
    table=[(dl.update({"cols": v.split("\t")}), dl["cols"])[1] for v in li];
    ncol=max(len(v) for v in table);
    table=[row+[""]*(ncol-len(row)) for row in table];
    return(pa.DataFrame(table, columns=[""]*ncol, index=np.arange(nrow)+1));
def tcol2df(tcol):
    "Transform a list of tuples (one tuple per column) into regular data frame"
    ncol=len(tcol);
    nrow=max(len(v) for k,v in tcol);
    table=[[str(v) if v==v else "" for v in col]+[""]*(nrow-len(col)) for nm, col in tcol];
    res=pa.DataFrame(table).transpose();
    res.index=np.arange(1, nrow+1);
    res.columns=[k for k,v in tcol];
    return res;
def ddf2xlsx(ddf, fnm):
    "write dictionary of DataFrames 'ddf' to tabs of xlsx file 'fnm', one dict entry per tab"
    tr="".maketrans("[]:*?/\\", "().....")
    with pa.ExcelWriter(fnm, engine='xlsxwriter', options={'strings_to_numbers': True}) as writer:
        wb=writer.book;
        pfmt0=wb.add_format({'num_format': '0"%"'});
        pfmt=wb.add_format({'num_format': '0.00"%"'});
        hfmt=wb.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'border': 0,
        });
        for nm, df in ddf.items():
            if nm == "model":
                df.to_excel(writer, sheet_name=nm.translate(tr), header=False, index=False);
            else:
                nms=nm.translate(tr)
                df.to_excel(writer, sheet_name=nms)
                ws=writer.sheets[nms]
                # header format
                ws.set_row(0, 32);
                ws.write(0, 0, "", hfmt);
                for ir in range(df.shape[0]):
                    ws.write(ir+1, 0, df.index[ir], hfmt);
                for ic in range(df.shape[1]):
                    ws.write(0, ic+1, df.columns[ic], hfmt);
                # percentage format
                for ir, ic in zip(*np.where(np.char.endswith(df.to_numpy().astype(str), "%"))):
                    val=df.iloc[ir, ic][:-1]
                    if ir == 1:
                        ws.write(ir+1, ic+1, val, pfmt)
                    else:
                        ws.write(ir+1, ic+1, val, pfmt0)

    
def wxlay2py(kvt, parent=[None], pref=""):
    """wxlay2py(kvt)
    return a string with python code generating wxWindow
    widget layout described in kvh tlist sturcture
    """
    res="";
    # get the kvh tuples
    for (k,v) in kvt:
        if k[:3] == "wx." or k[:3] == "wx_" and type(v) == list:
            ## produce the code for this widget
            # call class init
            vname=kvh_getv_by_k(v, ["varname"]);
            #if vname=="cpick_neghigh":
            #    import pdb; pdb.set_trace();
            # call methods if any and varname is set
            cl=kvh_getv_by_k(v, ["callmeth"]);
            if vname is None:
                if not cl is None:
                    raise Exception("there are callmeth but varname is not given");
            else:
                varname=pref+vname;
                res += varname+"=";
            param=kvh_getv_by_k(v, ["param"]);
            if param:
                param=param.replace(".parent", str(parent[-1]));
                if len(parent) > 1:
                    param=param.replace(".top", str(parent[1]));
            res+=k+"("+(param or "")+");\n"
            # recursivly create children
            res+=wxlay2py(v, parent+[varname], pref);
            if varname and cl:
                for (kc,vc) in cl:
                    if vc:
                        #import pdb; pdb.set_trace()
                        # if key and value store the result in key
                        vc=vc.replace(".parent", str(parent[-1]));
                        vc=vc.replace(".self", varname);
                        kc=pref+kc.replace(".self", varname);
                        if len(parent) > 1:
                            vc=vc.replace(".top", str(parent[1]));
                        res+=kc+"="+(varname+"."
                            if vc[:2] != "wx" else "")+vc+";\n";
                    elif kc:
                        # just call the key content
                        if kc[:1] != "#":
                            kc=kc.replace(".parent", str(parent[-1]));
                            kc=kc.replace(".self", varname);
                            if len(parent) > 1:
                                kc=kc.replace(".top", str(parent[1]));
                            res+=(varname+"." if vc[:2] != "wx"
                                else "")+kc+";\n";
        elif k.strip() == "" and type(v) == str and v[0]=="\t":
            raise Exception("A space is found where a tab is expected v='"+v+"'");
        else:
            # we don't know what it is, just silently ignore
            pass;
    return(res);
def subset(l, i):
    "return an iterator over l[i] where i is an iterable of indexes"
    for ii in i:
        yield l[ii];
def colSums(x):
    return(x.sum(0));
def rowSums(x):
    return(x.sum(1).reshape((x.shape[0], 1)));
def which(x):
    "return array of indexes where 'x' is True. 'x' is supposed 1D."
    return(np.where(np.asarray(x).flatten())[0]);
def c(*args):
    "concatenates flattened vectors in arguments"
    if len(args):
        return(np.hstack([v.flatten() if "flatten" in dir(v) else v for v in args]));
    else:
        return(None);
def zcross(f, xleft, xright, *args, fromleft=True, nitvl=10, **kwargs):
    "find interval [x1, x2] where f(x) changes its sign (zero crossing)"
    #print("args=", args);
    n1=nitvl+1;
    xp=np.linspace(xleft, xright, n1);
    y=np.vectorize(lambda x: f(x, *args, **kwargs))(xp);
    yprod=y[:-1]*y[1:];
    izcross=which(yprod <= 0.) if fromleft else nitvl-1-which(yprod[::-1] <= 0.);
    if not len(izcross):
        raise Exception(f"zero-cross point is not found in [{xleft}; {xright}]");
    izcross=izcross[0];
    return([xp[izcross], xp[izcross+1]]);
def zeroin(f, ax, bx, *args, tol=sys.float_info.epsilon**0.25, **kwargs):
    """
 adapted from www.netlib.org/c/brent.shar zeroin.c
 ************************************************************************
 *	    		    C math library
 * function ZEROIN - obtain a function zero within the given range
 *
 * Input
 *	double zeroin(ax,bx,f,tol)
 *	double ax; 			Root will be seeked for within
 *	double bx;  			a range [ax,bx]
 *	double (*f)(double x);		Name of the function whose zero
 *					will be seeked for
 *	double tol;			Acceptable tolerance for the root
 *					value.
 *					May be specified as 0.0 to cause
 *					the program to find the root as
 *					accurate as possible
 *
 * Output
 *	Zeroin returns an estimate for the root with accuracy
 *	4*EPSILON*abs(x) + tol
 *
 * Algorithm
 *	G.Forsythe, M.Malcolm, C.Moler, Computer methods for mathematical
 *	computations. M., Mir, 1980, p.180 of the Russian edition
 *
 *	The function makes use of the bissection procedure combined with
 *	the linear or quadric inverse interpolation.
 *	At every step program operates on three abscissae - a, b, and c.
 *	b - the last and the best approximation to the root
 *	a - the last but one approximation
 *	c - the last but one or even earlier approximation than a that
 *		1) |f(b)| <= |f(c)|
 *		2) f(b) and f(c) have opposite signs, i.e. b and c confine
 *		   the root
 *	At every step Zeroin selects one of the two new approximations, the
 *	former being obtained by the bissection procedure and the latter
 *	resulting in the interpolation (if a,b, and c are all different
 *	the quadric interpolation is utilized, otherwise the linear one).
 *	If the latter (i.e. obtained by the interpolation) point is 
 *	reasonable (i.e. lies within the current interval [b,c] not being
 *	too close to the boundaries) it is accepted. The bissection result
 *	is used in the other case. Therefore, the range of uncertainty is
 *	ensured to be reduced at least by the factor 1.6
 *
 ************************************************************************
 */
"""
    # double a,b,c;				# Abscissae, descr. see above	
    # double fa;				# f(a)				
    # double fb;				# f(b)				
    # double fc;				# f(c)				
    
    a = float(ax);  b = float(bx);  fa = float(f(np.asarray(a), *args, **kwargs));  fb = float(f(np.asarray(b), *args, **kwargs));
    c = a;   fc = fa;
    EPSILON=sys.float_info.epsilon;
    if fa*fb > tol:
        raise Exception("function 'f' must be of opposite sign on interval limits");
    
    while True:         # Main iteration loop	
        prev_step = b-a;        # Distance from the last but one
                                # to the last approximation	
        # double tol_act;       # Actual tolerance		
        # double p;             # Interpolation step is calcu- 
        # double q;             # lated in the form p/q; divi- 
                                # sion operations is delayed   
                                # until the last moment	
        # double new_step;      		# Step at this iteration       
       
        if fabs(fc) < fabs(fb):
            # Swap data for b to be the 	
            a = b;  b = c;  c = a;          # best approximation		
            fa=fb;  fb=fc;  fc=fa;
        tol_act = 2*EPSILON*fabs(b) + tol*0.5;
        new_step = (c-b)*0.5;

        if fabs(new_step) <= tol_act or fb == 0.:
          return(b);    # Acceptable approx. is found	

        # Decide if the interpolation can be tried	
        if fabs(prev_step) >= tol_act and fabs(fa) > fabs(fb):
            # If prev_step was large enough and was in true direction,	
            # Interpolatiom may be tried	
            # register double t1,cb,t2;
            cb = c-b;
            if a==c:    # If we have only two distinct	
                        # points linear interpolation 	
                t1 = fb/fa;			# can only be applied		
                p = cb*t1;
                q = 1.0 - t1;
            else:   # Quadric inverse interpolation
                q = fa/fc;  t1 = fb/fc;  t2 = fb/fa;
                p = t2 * ( cb*q*(q-t1) - (b-a)*(t1-1.0) );
                q = (q-1.0) * (t1-1.0) * (t2-1.0);
            if p > 0.:  # p was calculated with the op-
              q = -q;   # posite sign; make p positive	
            else:       # and assign possible minus to	
              p = -p;   # q				

            if p < (0.75*cb*q-fabs(tol_act*q)*0.5) and p < fabs(prev_step*q*0.5):
                # If b+p/q falls in [b,c] and isn't too large	
                new_step = p/q;			# it is accepted	
                            # If p/q is too large then the	
                            # bissection procedure can 	
                            # reduce [b,c] range to more	
                            # extent			

        if fabs(new_step) < tol_act:
            # Adjust the step to be not less than tolerance
            if new_step > 0.:
                new_step = tol_act;
            else:
                new_step = -tol_act;

        a = b;  fa = fb;			# Save the previous approx.	
        b += new_step;  fb = float(f(np.asarray(b), *args, **kwargs));	# Do step to a new approxim.	
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            # Adjust c for it to have a sign opposite to that of b	
            c = a;  fc = fa;
def is_na_end(x): return((np.cumsum(1-is_na(x)[::-1]) == 0)[::-1]);
def is_empty_end(x): return((np.cumsum(1-(x.astype(str)=="")[::-1]) == 0)[::-1]);
def sd1(x):
    return(np.std(x, ddof=1));
def ipeaks(x, decreasing=True):
    r"""return a vector of indexes corresponding to peaks in a vector x
    By default, the peaks are sorted in decreasing order.
    The peaks are searched only in the form /\ (mountain) and in /-\ (plateau).
    In case of plateau, floor((i1+i2)/2) is returned as peak position (i1 and i2 are limits of plateau)."""
    d=np.sign(np.diff(x));
    # make the same length as x (linear extrapolation)
    d=np.hstack((1., d, -1.)); # doubt benefice on the ends
    d2=np.diff(d);
    ip=which(d2==-2);
    ipl=which((d2 == -1)&(d[:-1] == 1.)); # left indexes of plateau candidate in ipl
    ipr=which((d2 == -1)&(d[:-1] == 0.)); # right indexes of plateau candidate in ipl
    if len(ipl) and len(ipr):
        dl=locals();
        it=np.apply_along_axis(lambda v: (dl.update({"w": which(v)}), dl["w"][-1] if len(dl["w"]) else nan)[-1], 0, ipl[:,None]<ipr[None,:]).astype(float); # indexes of last true ipl<ipr
        irep=which(it[:-1]==it[1:])+1;
        it[irep]=nan;
        ipr=ipr[~is_na(it)];
        it=np.int_(it[~is_na(it)]);
        ipl=ipl[it];
        ipc=np.array([(l+r)//2 for l,r in zip(ipl, ipr) if not np.any((l < ip)*(ip < r))], int); # "center" index
        ip=np.append(ip, ipc);
    o=np.argsort(x[ip]);
    if decreasing:
        o=o[::-1];
    return(ip[o]);
def smooth725(v, repet=1):
   """smooth by convolution with 0.25;0.5;0.25
   NB: the returned vector has the same length as original one.
   Extreme points have weights 0.75, 0.25 on left and 0.25;0.75 on right"""
   v=v.flatten();
   n=len(v);
   if n<2 or repet < 1:
      # the vector is too short or no smoothing is asked
      # send it back as is
      return(v);
   # extend v beyond interval and NA gaps
   # indexes of valid value having NA on its left
   nal=np.hstack((0, which((v[:-1] != v[:-1])*(v[1:] == v[1:]))+1));
   # indexes of valid value having NA on its right
   nar=np.hstack((which((v[1:] != v[1:])*(v[:-1] == v[:-1])), n-1));
   ve=np.hstack((nan, v, nan));
   ve[nal]=v[nal];
   ve[nar+2]=v[nar];
   ve=ve[:-1]+ve[1:];
   ve=0.25*(ve[:-1]+ve[1:]);
   if repet <= 1:
      return(ve);
   else:
      return(smooth725(ve, repet-1));
def outer(x, y, f=lambda x,y: x*y):
    "Apply f() on every couple xi, yj form x and y respectivly. Return f(xi,yj) in higher dimensional array"
    fv=np.vectorize(f);
    res=fv(x.flatten()[:, None], y.flatten());
    res.reshape((*x.shape, *y.shape));
    return(res);
def nrow(x):
    return(np.shape(x)[0] if len(np.shape(x)) > 0 else 0);
def ncol(x):
    return(np.shape(x)[1] if len(np.shape(x)) > 1 else 0);
def cut(x, bins, labels=None):
    "return indexes of bins in which x are falling: i is s.t. x ∈ (bins[i-1], bins[i]]. If labels are given then they are returned instead of indexes."
    xs=x.shape;
    x=np.asarray(x).flatten();
    bins=np.asarray(bins).flatten();
    i=(x[:, None] <= bins[None, :]).argmax(1)-1;
    nlab=len(labels) if not labels is None else 0;
    #import pdb; pdb.set_trace();
    if nlab > 0:
        if nlab != len(bins)-1:
            #import pdb; pdb.set_trace();
            raise Exception("len(labels) must be equal to len(bins)-1");
        i=np.asarray(labels)[i];
    i=nma.asarray(i);
    i.mask=is_na(x);
    return(i.reshape(xs));
def is_na(x):
    "return boolean array with True where x is nan or is masked"
    if nma.isMA(x):
        return(x.mask if type(x.mask) == np.ndarray else np.zeros(x.shape, bool));
    else:
        xx=np.asarray(x);
        return xx != xx;
def na_omit(x):
    "omit NA from x"
    xx=np.asarray(x);
    return(xx[~is_na(xx)]);
def starfun(t):
    return(t[0](*(t[1:])));
def oset(x):
    "returns a dict with keys in x and None in values"
    return dict((v, None) for v in x);
# EM part
erfv=np.vectorize(erf);
def dnorm(x, mean=np.array(0.), sd=np.array(1.)):
    "Normal law density function"
    #x=np.asarray(x);
    #if type(x) != np.ndarray:
    #    x=np.array(x);
    #xs=x.shape;
    x=np.reshape(x, (-1, 1)); # column
    mean=np.reshape(mean, (1, -1)); # row
    sd=np.reshape(sd, (1, -1)); # row
    res=np.exp( - 0.5*((x - mean)/sd)**2)/(sd * np.sqrt(2. * np.pi));
    nc=ncol(mean);
    res=res.reshape((len(x), nc));
    return(res);
def dnorm_d1(x, mean=0, sd=1):
    "first derivative by x of the normal law density function"
    #x=np.asarray(x);
    #if type(x) != np.ndarray:
    #    x=np.array(x);
    x=x.reshape(-1, 1); # column
    mean=mean.reshape(1, -1); # row
    sd=sd.reshape(1, -1); # row
    res=dnorm(x, mean, sd)*(mean-x)/(sd*sd);
    res=res.reshape(len(x), ncol(mean));
    return(res);
def dnorm_d2(x, mean=0, sd=1):
    "second derivative by x of the normal law density function"
    #x=np.asarray(x);
    #if type(x) != np.ndarray:
    #    x=np.array(x);
    x=x.reshape(-1, 1); # column
    mean=mean.reshape(1, -1); # row
    sd=sd.reshape(1, -1); # row
    res=dnorm(x, mean, sd)*(((mean-x)/sd)**2-1.)/(sd*sd);
    res=res.reshape(len(x), ncol(mean));
    return(res);
def pnorm(x, mean=0., sd=1.):
    "Normal law cumulative distribution function"
    return(0.5*(1+erfv((x-mean)/(sd*np.sqrt(2.)))));
def dgmmn(x, par, f=dnorm):
    """return a matrix of Gaussian mixture model calculated in points x
    and for components who's parameters are in 3-row matrix 'par', one
    component per column with items named: "a", "mean", "sd".
    The sum of positive 'a's is supposed to be 1 (not checked here).
    In the result matrix res, we have nrow(res)=length(x) and ncol(res)=ncol(par)
    """
    #x=np.asarray(x);
    res=np.array(par.loc["a", :]).reshape(1,-1)*f(x, np.array(par.loc["mean",:]), np.array(par.loc["sd",:]));
    return(res);
def dgmm(x, par, f=dnorm):
    if isinstance(x, (int, float)):
        return(dgmmn(x, par, f).sum(1)[0]);
    else:
        return(dgmmn(x, par, f).sum(1).reshape(x.shape));
def e_step1(x, mean=None, sd=None, a=None, par=None):
    """E-step of EM algorithm for 1D gaussian mixture: estimate membership weights

    @param x, numeric vector, N random samples from the mixture (without NA)
    @param mu, numeric vector, K means
    @param sd, numeric vector, K sd values
    @param par, numeric 3xG matrix as an alternative to mu, sd, a
    @value NxK numeric matrix of membership weights
    """
    if mean is None and par is None:
        raise Exception("'mean' and 'par' cannot be both None");
    if not mean is None and not par is None:
        raise Exception("One of 'mean' or 'par' must be None");
    if not mean is None and ("shape" in dir(mean) and len(mean.shape) != 1):
        raise Exception("'mean' is supposed to be a vector. Confounded with 'par'?");
    if par is None:
        if sd is None:
            raise Exception("'par' and 'sd' cannot be None simultaneously");
        par=pa.DataFrame(np.array([a, mean, sd]), index=["a", "mean", "sd"]);
    par.loc["a",:]=par.loc["a",:]/sum(par.loc["a",:]);
    w=dgmmn(x, par);
    w[w==np.inf]=sys.float_info.max;
    rs=w.sum(1)[:,None];
    iz=np.where(rs == 0.)[0]; # detect samples too far from any center
    if len(iz):
        im=[np.argmin(np.abs(x[i]-par.loc["mean",:])/par.loc["sd",:]) for i in iz];
        w[iz, im]=1.; # assign them to the closest from centered/reduced point of view
        rs[iz]=1.;
    return(w/rs);
def m_step1(x, w, imposed=pa.DataFrame(index=["a", "mean", "sd"]), inaa=None, inam=None, inas=None, tol=sys.float_info.epsilon*2**7):
    """M-step of EM algorithm for 1D gaussian mixture: estimate a, mean and sd

    @param x, numeric vector, N random samples from the mixture (without NA)
    @param w, NxK numeric matrix of membership weights
    @param gimp, integer scalar
    @value par, 3xK numeric matrix of a, mean, sd estimated parameters
    """
    gimp=imposed.shape[1];
    if gimp > 0:
        if inaa is None:
            inaa=np.isnan(imposed.loc["a", :]);
        if inam is None:
            inam=np.isnan(imposed.loc["mean", :]);
        if inas is None:
            inas=np.isnan(imposed.loc["sd", :]);
    else:
        if inaa is None:
            inaa=np.full(0, True);
        if inam is None:
            inam=np.full(0, True);
        if inas is None:
            inas=np.full(0, True);
    ninaa=~inaa;
    ninam=~inam;
    ninas=~inas;
    x=np.asarray(x);
    n=len(x);
    nk=w.sum(0);
    a=nk/n;
    # renormalize a
    if gimp > 0 and not all(inaa):
        an=a.copy(); # 'a' new
        an[:gimp][ninaa]=imposed.loc["a", ninaa] ;
        simp=sum(imposed.loc["a", ninaa]);
        irest=np.full(w.shape[1], True);
        irest[:gimp][ninaa]=False;
        srest=sum(an[irest]);
        fa=(1.-simp)/srest;
        an[irest]=fa*an[irest];
        nk=an*n;
        fa=an/a;
        fa[np.isinf(fa)]=1.
        w=w*fa;
        a=an;
    mean=np.dot(w.T, x)/nk;
    if gimp > 0 and not all(inam):
        mean[:gimp][ninam]=imposed.loc["mean", ninam];
    #sd=(np.dot(w.T, x**2)-nk*mean**2)/(nk-1.);
    sd=(w*(x.reshape((-1, 1))-mean.reshape((1, -1)))**2).sum(0)/(nk-1.);
    sd[sd<=0.]=sys.float_info.min;
    sd=np.sqrt(sd);
    if gimp > 0 and not all(inas):
        sd[:gimp][ninas]=imposed.loc["sd", ninas];
    res=pa.DataFrame([a, mean, sd]);
    res.index=["a", "mean", "sd"];
    return(res);
def em1(x, par=None, imposed=pa.DataFrame(index=["a", "mean", "sd"]), G=range(1,10), maxit=10, tol=1.e-7, restart=5, classify=False):
    "EM algorithm for Gaussian Mixture Model fitting on a 1D sample x. G is supposed to be increasing sequence of class numbers."
    iva=np.isfinite(x);
    xv=x[iva];
    nv=len(xv);
    gimp=imposed.shape[1];
    inaa=np.isnan(imposed.loc["a",:]);
    inam=np.isnan(imposed.loc["mean",:]);
    inas=np.isnan(imposed.loc["sd",:]);
    ninaa=~inaa;
    ninam=~inam;
    ninas=~inas;

    res=dict();
    if type(G) in (int, float):
        G=[round(G)];
    for g in G:
        #if g != G[0] and degen:
        #    break; # there were too low classes with even lower class number
        res_rest=dict();
        for istart in range(restart):
            if istart > 0 and (g == 1 or maxit == 0):
                break;
            # iterate e and m steps until convergence or maxit is reached
            # init par
            if DEBUG:
                print("istart=", istart);
            if istart > 0 or par is None or g != G[0]:
                par=pa.DataFrame(np.full((3, g+gimp), 0.), index=["a", "mean", "sd"]);
                # init means
                par.loc["mean",:]=sorted(np.random.choice(xv, g+gimp, False));
                # init a, sd
                par.loc["a",:]=1./(g+gimp);
                par.loc["sd",:]=np.std(xv, ddof=1)/(g+gimp)/4.;
            elif g==G[0] and par.shape[1] != g+gimp:
                raise Exception("at starting point, par.shape[1] must be equal to G[0]+imposed.shape[1]")
            else:
                par.loc["a", np.isnan(par.loc["a",:])]=1./(g+gimp);
                m_na=np.isnan(par.loc["mean",:]);
                par.loc["mean", m_na]=np.random.choice(xv, sum(m_na), False);
                par.loc["sd", np.isnan(par.loc["sd",:])]=np.std(xv, ddof=1)/(g+gimp)/4.;
                ifree=gimp+np.arange(par.shape[1]-gimp);
                par.iloc[:, ifree]=par.iloc[:, gimp+np.argsort(par.loc["mean",ifree])];
            if gimp > 0:
                # inject imposed
                i=np.arange(gimp);
                par.loc["a",i[ninaa]]=imposed.loc["a", ninaa];
                par.loc["mean",i[ninam]]=imposed.loc["mean", ninam];
                par.loc["sd",i[ninas]]=imposed.loc["sd", ninas];
            par.loc["a",:]=par.loc["a",:]/sum(par.loc["a",:]);
            converged=(g==0);
            it=1;
            #degen=(g != 0) and it < maxit;
            #np.seterr(divide='raise')
            pr=dgmm(xv, par);
            lp=-746*np.ones(pr.shape);
            lp=np.log(pr, out=lp, where=pr>0.);
            #np.seterr(divide='warn')
            #lp[lp == -np.inf]=-746;
            loglike=sum(lp);
            BIC=BIC_prec=-2*loglike+np.log(nv)*(3*par.shape[1]-sum(ninaa)-sum(ninam)-sum(ninas))
            while not converged and it <= maxit:
                w=e_step1(xv, par=par);
                #degen=any(w.sum(0) <= 2.);
                #if DEBUG:
                #    print("degen=", degen);
                #if False and degen:
                #    import pdb; pdb.set_trace();
                #if degen and it > 1:
                #    if DEBUG:
                #        print("par=", par, "\tnk=", w.sum(0), "\nw=", w);
                #    break;
                if np.isnan(w).any():
                    raise Exception("nan appeared in weights");
                parnew=m_step1(xv, w, imposed, inaa, inam, inas);
                #print("it=", it, "\tparnew=\n", parnew);
                i0=which(parnew.loc["a",:] <= tol);
                # remove empty non imposed classes
                i0=i0[i0 > gimp-1];
                parnew.drop(columns=i0, inplace=True);
                parnew.columns=np.arange(ncol(parnew));
                #print("it=", it, "\tparnew drop=\n", parnew);
                lp=np.log(dgmm(xv, parnew));
                lp[lp == -np.inf]=-746
                loglike=sum(lp);
                BIC=-2*loglike+np.log(nv)*(3*parnew.shape[1]-sum(ninaa)-sum(ninam)-sum(ninas));
                #print("it=", it, "\tBIC=", BIC)
                #if BIC < 0:
                #    print("it=", it, "\tBIC=", BIC, ";\t-2*loglike=", -2*loglike, ";\tpar=", np.log(nv)*(3*parnew.shape[1]-sum(ninaa)-sum(ninam)-sum(ninas)));
                if BIC > BIC_prec:
                    BIC=BIC_prec;
                    if DEBUG:
                        print("BIC increased");
                    break;
                converged=((BIC_prec-BIC < tol) or (BIC_prec-BIC)/fabs(BIC_prec) < tol);
                #print("(BIC_prec-BIC)/fabs(BIC_prec)=", (BIC_prec-BIC)/fabs(BIC_prec), "\ttol=", tol)
                if DEBUG:
                    print("g=", g, "\tit=", it, "\tBIC=", BIC, "\tconv=", converged);
                par=parnew;
                BIC_prec=BIC;
                it=it+1;
            #if degen: # there are groups with less then or equal to 2 members => don't record this try
            #    continue;
            res_rest[istart]={"par": par, "BIC": BIC, "loglike": loglike, "it": it-1, "maxit_reached": it==maxit+1}
        ibic=min(res_rest.keys(), key=lambda k: res_rest[k]["BIC"]);
        res["g"+str(g)]=res_rest[ibic];
        if ncol(par) < g:
            break; # don't try other g as there are already disappeared group(s)
    if not res:
        return({});
    kbic=min(res.keys(), key=lambda k: res[k]["BIC"]);
    res={"win": res[kbic], "all": res};
    if classify:
        cl=gmmcl(x, res["win"]["par"]);
        res["classification"]=pa.DataFrame({"x": x, "proba_max": cl["wmax"], "cl": cl["cl"]});
    return(res)
def par2gaus(par):
   # transform par (3xG matrix) to function calculating sum of gaussians
   return(lambda x: dgmm(x, par));
def gmmcl(x, par):
    """classify x according to GMM in par
    return a dict with class number 'cl', matrix of class weights 'w' and a vector
    of maximal weights 'wmax'"""
    w=e_step1(x, par=par);
    cl=nma.asarray(w.argmax(1));
    #cl=as_integer(ifelse(sapply(cl, length)==0, NA, cl))
    wmax=w[range(len(x)), cl];
    cl[:]=par.columns[cl];
    cl.mask=wmax != wmax;
    return({"cl": cl, "w": w, "wmax": wmax});
def roothalf(i1, i2, par, fromleft=True):
    "find intersection and half-height interval of 2 gaussians defined by columns i1 and i2 in par"
    if type(par) != pa.DataFrame:
        raise Exception("par must be a DataFrame");
    if par.shape[1] < 2:
        raise Exception("par must have at least two columns");
    try:
        mid=zeroin(lambda x: np.diff(dgmmn(x, par.loc[:, [i1,i2]]), axis=1), par.loc["mean", i1]-0.25*par.loc["sd", i1], par.loc["mean", i2]+0.25*par.loc["sd", i2]);
    except Exception as e:
        print("par=", par, "\ni1=", i1, "; i2=", i2)
        import pdb; pdb.set_trace()
        raise e;
    # find "grey-zone" limits as peak half-height
    # first find peack's tip
    #fw_d2=grad(fw_d1);
    try:
        xlr=zcross(fw_d2, par.loc["mean", i1]-0.75*par.loc["sd", i1], par.loc["mean", i2]+0.75*par.loc["sd", i2], par, 0, fromleft=fromleft);
        xtip=zeroin(fw_d2, xlr[0], xlr[1], par, 0);
        ftip=float(fw_d1(xtip, par, 0));
        # now find tip/2 positions
        fhalf=lambda x: float(fw_d1(x, par, 0))-ftip*0.5;
        xlr=zcross(fhalf, par.loc["mean", i1]-3*par.loc["sd", i1], xtip, fromleft=False);
        left=zeroin(fhalf, xlr[0], xlr[1]);
        xlr=zcross(fhalf, xtip, par.loc["mean", i2]+3*par.loc["sd", i2], fromleft=True);
        right=zeroin(fhalf, xlr[0], xlr[1]);
    except:
        left=right=nan;
    return({"mid": mid, "left": left, "right": right});
def gcl2i(cl, par):
    o=np.argsort(par.loc["mean",:]).to_numpy();
    io=o.copy();
    io[o]=np.arange(len(o));
    iv=cl == cl;
    res=np.asarray(cl);
    res[iv]=io[cl[iv]]-io[0];
    return(res);
def fw(x, par, i):
    "weights of Gaussian class i"
    pdf=dgmmn(x, par);
    return(pdf[:,i]/rowSums(pdf)[:,0]);
def fw_d1(x, par, i):
    "first derivative by x of weights of Gaussian class i"
    x=np.asarray(x);
    pdf=dgmmn(x, par);
    pdf_d1=dgmmn(x, par, dnorm_d1);
    w=rowSums(pdf)[:,0];
    w_d1=rowSums(pdf_d1)[:,0];
    return((pdf_d1[:,i]-pdf[:,i]*w_d1/w)/w);
def fw_d2(x, par, i):
    "second derivative by x of weights of Gaussian class i"
    x=np.asarray(x);
    pdf=dgmmn(x, par);
    pdf_d1=dgmmn(x, par, dnorm_d1);
    pdf_d2=dgmmn(x, par, dnorm_d2);
    w=rowSums(pdf)[:,0];
    w_d1=rowSums(pdf_d1)[:,0];
    w_d2=rowSums(pdf_d2)[:,0];
    return((pdf_d2[:, i] - ((2 * pdf_d1[:, i] - pdf[:, i] * w_d1/w) * 
        w_d1 + pdf[:, i] * (w_d2 - 
        w_d1**2/w))/w)/w);
def rt2model(ref, test, par_mod):
    "ref and test samples to GMM model. par_mod['thr_w'] is weight threshold for vanishing classes"
    # get only valid entries
    rv=ref[ref == ref];
    tv=test[test == test];
    athr=par_mod["thr_w"]/len(tv);
    # imposed group
    imp=pa.DataFrame([nan, np.mean(rv), sd1(rv)], index=["a", "mean", "sd"]);
    # histogram for first approximation of class nb and positions
    tmin=np.min(tv);
    tmax=np.max(tv);
    h=np.histogram(tv, bins=np.linspace(tmin, tmax, par_mod["k"]+1));
    # smooth counts
    #plt.figure("h");
    #plt.plot(h[0]);
    #hcnt=smooth725(h[0], 3);
    hcnt=h[0];
    #plt.plot(hcnt);
    #plt.show(block=False);
    ip=ipeaks(hcnt);
    iv=ipeaks(-hcnt); # valles
    # estimate cardinal of each peak and eliminate too low populated ones
    ip.sort();
    iv.sort();
    if len(ip):
        if iv[0] > ip[0]:
            iv=np.insert(iv, 0, ip[0]);
        if iv[-1] < ip[-1]:
            iv=np.append(iv, ip[-1]);
        pcnt=np.array([hcnt[iv[i]:(iv[i+1]+1)].sum() for i in range(len(iv)-1)])
        if len(pcnt) != len(ip):
            #import pdb; pdb.set_trace();
            ipeaks(-hcnt);
            raise Exception("cardinal of peaks has not the same length as peak list");
    ip=ip[pcnt>=3]; # too rare groups are eliminated
    #print("ip=", ip);
    par=pa.DataFrame(np.array([[nan]*len(ip), np.sort(h[1][ip]), [(tmax-tmin)/30/4]*len(ip)]), index=["a", "mean", "sd"]);
    # learn gmm without imposed class
    pari=em1(tv, par=par, G=par.shape[1], restart=1, maxit=200, tol=1.e-5)["win"]["par"];
    #print("pari=", pari);
    # is there any class very close to imp?
    di=(np.abs(pari.loc["mean",:]-imp.loc["mean",0])/(pari.loc["sd",:]+imp.loc["sd",0])*2.).to_frame();
    di=di.T;
    di.index=["dist_to_ref"];
    par_hist=pari.copy();
    par_hist=par_hist.append(di);
    i_imp= di <= par_mod["thr_di"]; #0.5;
    if np.any(i_imp):
        i_imp=which(i_imp);
        pari.loc["a",:]=1./(ncol(pari)-len(i_imp)+1);
        pari.iloc[:, i_imp[0]]=imp;
        if len(i_imp) > 1:
            pari.drop(columns=i_imp[1:], inplace=True);
    else:
        pari=pa.concat((imp, pari), axis=1);
        pari.loc["a",:]=1./pari.shape[1];
    pari.columns=np.arange(ncol(pari));
    cpar=em1(tv, par=pari, imposed=imp, G=(pari.shape[1]-1), restart=1, maxit=200, tol=1.e-5, classify=True)["win"];
    # re-detect classes too close to each other, eliminate one of them and re-estimate GMM
    ng=ncol(cpar["par"]);
    neglige=(ng > 1) and any(cpar["par"].loc["a",1:] <= athr)
    while neglige:
        # strip too rare classes
        iz=np.argmin(cpar["par"].loc["a",1:])
        pari=cpar["par"].drop(columns=iz+1);
        pari.columns=np.arange(ncol(pari));
        cpar=em1(tv, par=pari, imposed=imp, G=ncol(pari)-ncol(imp), restart=1, maxit=200, tol=1.e-5, classify=True)["win"];
        ng=ncol(cpar["par"]);
        neglige=(ng > 1) and any(cpar["par"].loc["a",1:] <= athr);
    fuse=ng > 1;
    while fuse:
        ing=np.arange(ng);
        di=outer(ing, ing, lambda i1,i2: (np.abs(cpar["par"].loc["mean",i1]-cpar["par"].loc["mean",i2])/(cpar["par"].loc["sd",i1]+cpar["par"].loc["sd",i2])*2) <= 0.5);
        i12=np.where(outer(ing, ing, lambda i,j: i > j) * di); # candidates to fuse with class=0 will be first
        if len(i12[0]) > 0:
            irm=i12[0][0];
            pari=cpar["par"].drop(columns=irm);
            pari.loc["sd", 1:]=pari.loc["sd", 1:]/4.;
            pari.columns=np.arange(ncol(pari));
            cpar=em1(tv, par=pari, imposed=imp, G=ncol(pari)-1, restart=1, maxit=200, tol=1.e-5, classify=True)["win"];
            ng=ncol(cpar["par"]);
        else:
            break
    ng=ncol(cpar["par"]);
    #cpar.update({"par_hist": par_hist});
    # find cutoffs
    iom=np.argsort(cpar["par"].loc["mean",:]); # indexes of ordered means
    iref=which(iom == 0)[0];
    cutoff=dict()
    p1=cpar["par"].copy();
    p1.loc["a",:]=1.;
    for i,im in enumerate(iom):
        if i == 0:
            continue;
        # precedent class
        im1=iom[i-1];
        if i <= iref:
            # down classes
            if i == iref:
                # first down shifted class
                roots=roothalf(im1, 0, p1, True);
                cutoff["down-1"]=roots["mid"];
                cutoff["down_left"]=roots["left"];
                cutoff["down_right"]=roots["right"];
            else:
                # other down class
                cutoff["down-"+str(iref-i+1)]=zeroin(lambda x: dgmmn(x, p1)[:, im1] - dgmmn(x, p1)[:, im], p1.loc["mean", im1]-0.5*p1.loc["sd", im1], p1.loc["mean", im]+0.5*p1.loc["sd", im]);
        else:
            # up classes
            if i == iref+1:
                # first up shifted class
                roots=roothalf(0, im, p1, False);
                cutoff["up-1"]=roots["mid"];
                cutoff["up_left"]=roots["left"];
                cutoff["up_right"]=roots["right"];
            else:
                # other up class
                cutoff["up-"+str(i-iref)]=zeroin(lambda x: dgmmn(x, p1)[:, im1] - dgmmn(x, p1)[:, im], p1.loc["mean", im1]-0.5*p1.loc["sd", im1], p1.loc["mean", im]+0.5*p1.loc["sd", im]);
    # renumber classes and add class labels
    o=np.argsort(cpar["par"].loc["mean",:]).to_numpy();
    io=o.copy();
    io[o]=np.arange(len(o));
    cpar["par"].columns=io-io[0];
    #print("classes=", cpar["par"].columns);
    #if -2 in cpar["par"].columns:
    #    import pdb; pdb.set_trace();
    #import pdb; pdb.set_trace();
    br=[-Inf];
    cllab=[];
    cbr=[-Inf];
    ccllab=[];
    kdown=sorted([k for k in cutoff if k.startswith("down-")], key=lambda k: int(k[5:]), reverse=True);
    for k in kdown:
        br.append(cutoff[k]);
        cllab.append(k);
        cbr.append(cutoff[k]);
        ccllab.append(k);
    cllab.append("ref");
    ccllab.append("ref");
    kup=sorted([k for k in cutoff if k.startswith("up-")], key=lambda k: int(k[3:]));
    for k in kup:
        br.append(cutoff[k]);
        cllab.append(k);
        cbr.append(cutoff[k]);
        ccllab.append(k);
    br.append(Inf);
    cbr.append(Inf);
    
    if "down-1" in cutoff:
        i=ccllab.index("down-1");
        cbr[i+1]=cutoff["down_left"];
    if "up-1" in cutoff:
        i=ccllab.index("up-1");
        cbr[i]=cutoff["up_right"];
    
    cutoff["breaks"]=br;
    cutoff["labels"]=cllab;
    cutoff["sbreaks"]=cbr;
    cutoff["slabels"]=ccllab;
    cpar["cutoff"]=cutoff;
    cpar["par_mod"]=par_mod.copy();
    #import pdb; pdb.set_trace();
    return(cpar);
def xmod2class(x, cpar):
    "cpar is a model dict from rt2model(). It is used to classify a vector x. Return a 'classification' DataFrame"
    cla=gmmcl(x, cpar["par"]);
    classification=pa.DataFrame({"x": x, "cl": cla["cl"], "wmax": cla["wmax"]});
    #import pdb; pdb.set_trace();
    #classification["class_descr"]=pa.DataFrame(cut(classification["cl"], cl0br, cl0lab));
    cl=classification["cl"].copy().astype(object);
    ine=cl < 0;
    ipo=cl > 0;
    i0=cl==0;
    cl[ine]="down"+cl[ine].astype(int).astype(str);
    cl[i0]="ref";
    cl[ipo]="up-"+cl[ipo].astype(int).astype(str);
    classification["class_descr"]=cl;
    # add classification by cutoff and scutoff (stringent cutoff)
    cutoff=cpar["cutoff"];
    
    clcut=cut(x, cutoff["breaks"], cutoff["labels"]);
    cclcut=cut(x, cutoff["sbreaks"], cutoff["slabels"]);
    cutnum=cut(x, cutoff["breaks"], sorted(cpar["par"].columns)).astype(object).filled(nan);
    ccutnum=cut(x, cutoff["sbreaks"], sorted(cpar["par"].columns)).astype(object).filled(nan);
    classification["cutoff"]=clcut;
    classification["cutnum"]=cutnum;
    classification["stringentcutoff"]=cclcut;
    classification["stringentcutnum"]=ccutnum;
    return(classification);
