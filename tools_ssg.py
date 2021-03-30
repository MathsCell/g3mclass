import sys;
import operator;
import string;
import pandas as pa;
import csv;
DEBUG=False;

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

def asort(d):
    """sorts a dictionnary by value preserving key=value association
    the result is a list of tuples (key,value)"""
    return sorted(list(a.items()), key=operator.itemgetter(1));

def iterbit(i, size=0):
    """iterator on bits in integer starting from 0-position. The
    iterator stops at highest non-zero bit"""
    i=int(i);
    moveb=1;
    b_no=0;
    while (moveb <= i and size==0) or (b_no < size):
        yield (1 if (moveb&i) else 0);
        moveb<<=1;
        b_no+=1;

def iternumbit(i, size=0):
    """iterator on bits and its number in integer starting from 0-position.
    The iterator yields tuples (n,bit).
    If optional size is zero then it stops at highest non-zero bit.
    If not, it will stop at bit number size-1."""
    i=int(i);
    moveb=1;
    b_no=0;
    while (moveb <= i and size==0) or (b_no < size):
        yield (b_no, 1 if (moveb&i) else 0);
        moveb<<=1;
        b_no+=1;

def sumbit(i):
    """return sum of bits in an integer"""
    return sum(iterbit(i));

def strbit32(i):
    """return a string of 0-1s (in chunk of 4) in an 32 bit integer"""
    i=int(i);
    moveb=1<<31;
    res='';
    for b in range(32):
        res+=str(int((moveb&i) > 0));
        res+=' ' if not (b+1)%4 and b < 31 else '';
        moveb>>=1;
    return res;
def strbit(i,size=0):
    """return the lowest part of integer as string binary represantation"""
    return ''.join(('1' if b else '0') for b in iterbit(i,size) )[::-1];
def rstrbit(i,size=0):
    """return the integer as reversed string binary represantation
    The lowest bit is on the left side"""
    return ''.join(('1' if b else '0') for b in iterbit(i,size) );

def setbit32(i, nb):
    """set a bit number nb (0 based) in an integer i"""
    if (nb < 0 or nb > 31):
       return i; # do nothing to i
    i|=(1<<nb);

def valval(o):
    """iterator returning values of values, i.e.
    collapsing values of fisrt two levels"""
    for i1 in o:
        for i2 in i1: yield i2;

def join(c,l,p='',s='',a=''):
    """join the items of the list (or iterator) l separated by c.
    Each item is prefixed with p and suffixed with s.
    If the join result is empty for any reason, an alternative a is returned.
    p, s and a are optional"""
    i=0;
    return c.join(p+str(i)+s for i in l) or a;
def joint(c,l,p='',s='',a=''):
    """join "true" items of the list (or iterator) l separated by c.
    Each item is prefixed with p and suffixed with s.
    If the join result is empty for any reason, an alternative a is returned.
    p, s and a are optional"""
    i=0;
    return c.join(p+str(i)+s for i in l if i) or a;

def list2count(l, incr=1):
    """count values in list l incrementing the counter by optional incr
    and return dictionary {item:count}"""
    dico={};
    for item in l:
        dico[item]=dico.get(item,0)+incr;
    return dico;

def strbit2int(s):
    """translate a string of 0's and 1's interpreted as bits to an integer
    all characters different from 0,1 are silently ignored"""
    res=0;
    movb=1;
    for c in s[::-1]:
        if c=='1':
            res+=movb;
        elif c!='0':
            continue;
        movb<<=1;
    return res;

def setcharbit(s,ch,i):
    """set character ch in a string s everywhere a corresponding bit of i is set"""
    res=''.join((ch if b else s[-b_no-1]) for (b_no,b) in iternumbit(i));
    #print 'in:', s, ch, strbit(i);
    #print 'r', res;
    res=s[:len(s)-len(res)]+res[::-1];
    #print 'final', res;
    return res;

def expandbit(i,pos):
    """copy bits set to 1 in i to the result position given in the list pos.
    length of pos must be greater or equal to bitlength of i"""
    #print i, pos;##
    return sum(b<<pos[b_no] for (b_no,b) in iternumbit(i));

def isstr(s):
    """returns True if the argument is a string""";
    return isinstance(s,type("")) or isinstance(s,type(""));

def trd(l, d, p="", s="", a=""):
    """translate items in an iterable l by a dictionary d, prefixing
    translated items by optional p and suffixing them by optional s.
    If an item is not found in the dictionnary alternative string a is used.
    If a==None, the item is left unchanged.
    No prefix or suffix are applied in both case.
    Returns an iterator"""
    return (p+str(d[i])+s if i in d else i if a==None else a for i in l);
def icumo2iiso(icumo, size):
    """iterator on isotopomers composing a given icumo. size is carbon number"""
    nzero=size-sumbit(icumo);
    zpos=[n for (n,b) in iternumbit(icumo, size) if not b];
    return (expandbit(iz,zpos)+icumo for iz in range(1<<nzero));
def reverse(it):
    """reverse order of an iterable"""
    for i in range(len(it),0,-1):
        yield it[i-1];
def ssign(i, sp="+", sm="-"):
    """return a string of i sign: sp (i>=0) or sm (i<0). """
    return sp if float(i) >= 0 else sm;
def arr2pbm(A, fp):
    """arr2pbm(A, fp)
    Write an image map of non-zero entries of matrix A to file pointer fp.
    Matrix A is an array"""
    fp.write("P1\n%d %d\n" % A.shape[::-1]);
    for row in A:
        p=0;
        for c in row:
            fp.write("1 " if c else "0 ");
            p+=2;
            if p >= 69:
                fp.write("\n");
                p=0;
        fp.write("\n");
        p=0;
def kvh2tlist(fp, lev=[0], indent=[0]):
    """kvh2tlist(fp, lev=[0], indent=[0])
    Read a kvh file from fp stream descriptor
    and organize its content in list of tuples [(k1,v1), (k2,[(k2.1, v2.1)])]
    If fp is a string, it is used in open() operator
    """
    # check the stream
    open_here=False;
    if isstr(fp):
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
        pdb.set_trace();##
    while True:
        # current position is supposed to point to the begining of a key
        # so go through an appropriate tab number for the current level
        while indent[0] < lev[0]:
            char=fp.read(1);
            if char!="\t":
                if char!="":
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
def dict2kvh(d, fp=sys.stdout, indent=0):
    """dict2kvh(d, fp=sys.stdout, indent=0)
    Write a nested dictionary on the stream fp (stdout by default).
    """
    open_here=False;
    if isstr(fp):
        open_here=True;
        fp=open(fp, "w");
    for (k,v) in d.items():
        if issubclass(type(v), dict):
            # recursive call with incremented indentation
            fp.write("\n");
            dict2kvh(v, fp, indent+1);
        elif issubclass(type(v), pa.DataFrame):
            obj2kvh(v, k, fp, indent+1);
        else:
            fp.write("%s%s\t%s\n" % ("\t"*indent, escape(str(k), "\t\\\n"), escape(str(v), "\\\n")));
    if open_here:
        fp.close();
def obj2kvh(o, oname=None, fp=sys.stdout, indent=0):
    "write data.frame of dict to kvh file"
    open_here=False;
    if isstr(fp):
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
            obj2kvh(v, str(i), fp, indent+1);
    elif issubclass(to, dict):
        fp.write("\n");
        dict2kvh(o, fp, indent+1);
    elif issubclass(to, pa.DataFrame):
        if have_name:
            fp.write("\n");
        fp.write("\t"*(indent+have_name)+"row_col\t"+"\t".join(escape(v, "\\\n") for v in o.columns)+"\n");
        s=o.to_csv(header=False, sep="\t", quoting=csv.QUOTE_NONE, na_rep="");
        li=s.split("\n");
        if (len(li) == o.shape[0]+1):
            fp.write("\t"*(indent+have_name)+("\n"+"\t"*(indent+have_name)).join(li[:-1])+"\n");
        else:
            raise Exception("Not yet implemented newline in data.frame")
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
    return "".join((ech+c if c in spch else c) for c in s);
def cumsum(l, tot=0):
   """cumsum(l, tot=0)
   Return an iterable of the length len(l)+1 with cumulated sum
   of items in l. First element in cumsum is equal to initial
   value of tot. Result depends
   on the meaning of "+" operator for l items and of tot type.
   >>> list(cumsum("abc",tot=""))
   ['', 'a', 'ab', 'abc']
   >>> list(cumsum(xrange(1,5)))
   [0, 1, 3, 6, 10]
   """
   for i in l:
       yield tot;
       tot+=i;
   yield tot;
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
def wxlay2py(kvt, parent=[None], pref=""):
    """wxlay2py(kvt)
    return a string with python code generating wxWindow
    widget layout described in kvh tlist sturcture
    """
    res="";
    # get the kvh tuples
    for (k,v) in kvt:
        if k[:3]=="wx." or k[:3]=="wx_"and type(v)==type([]):
            ## produce the code for this widget
            # call class init
            varname=pref+kvh_getv_by_k(v, ["varname"]);
            res+=(varname+"=") if kvh_getv_by_k(v, ["varname"]) else "";
            param=kvh_getv_by_k(v, ["param"]);
            if param:
                param=param.replace(".parent", str(parent[-1]));
                if len(parent) > 1:
                    param=param.replace(".top", str(parent[1]));
            res+=k+"("+(param or "")+");\n"
            # recursivly create children
            res+=wxlay2py(v, parent+[varname], pref);
            # call methods if any and varname is set
            cl=kvh_getv_by_k(v, ["callmeth"]);
            if varname and cl:
                for (kc,vc) in cl:
                    if vc:
                        # if key and value store the result in key
                        vc=vc.replace(".parent", str(parent[-1]));
                        vc=vc.replace(".self", varname);
                        kc=kc.replace(".self", varname);
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
        else:
            # we don't know what it is, just silently ignore
            pass;
    return(res);

def ulong(i):
    """ulong(i) -> workarounded ulong"""
    return(-((i^0xffffffff)+1));
