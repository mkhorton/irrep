            # ###   ###   #####  ###
            # #  #  #  #  #      #  #
            # ###   ###   ###    ###
            # #  #  #  #  #      #
            # #   # #   # #####  #


##################################################################
## This file is distributed as part of                           #
## "IrRep" code and under terms of GNU General Public license v3 #
## see LICENSE file in the                                       #
##                                                               #
##  Written by Stepan Tsirkin, University of Zurich.             #
##  e-mail: stepan.tsirkin@physik.uzh.ch                         #
##################################################################

from ._version import __version__

import copy
import os
import sys
import logging

import numpy as np

from irrep.__aux import str2bool, str2list_space, str_

# using a logger to print useful information during debugging,
# set to logging.INFO to disable debug messages
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SymopTable:
    '''
    Parses a `str` that  describes a symmetry operation of the space-group and 
    stores info about it in attributes.

    Parameters
    ----------
    line : str
        Line to be parsed, which describes a symmetry operation.
    from_user : bool, default=False
        `True` if `line` was read from files of irreps already included in 
        `IrRep` (MI: from_user=True deprecated?)

    Attributes
    ----------
    R : array, shape=(3,3)
        Rotational part, describing the transformation of basis vectors (not 
        cartesian coordinates!).
    t : array, shape=(3,)
        Direct coordinates of the translation vector.
    S : array, shape=(2,2)
        SU(2) matrix describing the transformation of spinor components.
    '''

    def __init__(self, line, from_user=False):

        if from_user:
            self.__init__from_user(line)
            return
        numbers = line.split()
        self.R = np.array(numbers[:9], dtype=int).reshape(3, 3)
        self.t = np.array(numbers[9:12], dtype=float)
        self.S = (
            np.array(numbers[12::2], dtype=float)
            * np.exp(1j * np.pi * np.array(numbers[13::2], dtype=float))
        ).reshape(2, 2)

    def __init__from_user(self, line):
        '''
        Initialize class attributes by parsing line read from files included in 
        `IrRep`. 

        Parameters
        ----------  
        line : str
            Line to be parsed, which describes the symmetry operation.
            
        '''
        numbers = line.split()
        self.R = np.array(numbers[:9], dtype=int).reshape(3, 3)
        self.t = np.array(numbers[9:12], dtype=float)
        if len(numbers) > 12:
            self.S = (
                np.array(numbers[12:16], dtype=float)
                * np.exp(1j * np.pi * np.array(numbers[16:20], dtype=float))
            ).reshape(2, 2)
        else:
            self.S = np.eye(2)

    def str(self, spinor=True):
        """
        Create a `str` describing the symmetry operation as implemented in the 
        files included in `IrRep`.

        Parameters
        ----------
        spinor : bool
            `True` if the matrix describing the transformation of spinor 
            components should be written.

        Returns
        -------
        str

        """
        return (
            "   ".join(" ".join(str(x) for x in r) for r in self.R)
            + "     "
            + " ".join(str_(x) for x in self.t)
            + (
                (
                    "      "
                    + "    ".join(
                        "  ".join(str_(x) for x in X)
                        for X in (
                            np.abs(self.S.reshape(-1)),
                            np.angle(self.S.reshape(-1)) / np.pi,
                        )
                    )
                )
                if spinor
                else ""
            )
        )


class CharFunction:
    """
    deprecated?
    """

    def __init__(self, abcde):
        """

        :param abcde:
        """
        self.abcde = copy.deepcopy(abcde)

    def __call__(self, u=0, v=0, w=0):
        """

        :param u:
        :param v:
        :param w:
        :return:
        """
        return sum(
            aaa[0]
            * np.exp(1j * np.pi * (sum(a * u for a, u in zip(aaa[1:], (1, u, v, w)))))
            for aaa in self.abcde
        )


class KPoint:
    """
    Orginizes the info about a maximal k-point and contains routines to print 
    it. This info is obtained by parsing the parameter `line` or passed 
    directly as `name`, `k` and `isym`.
    
    Parameters
    ----------
    name : str
        Label of the k-point.
    k : array, shape=(3,)
        Direct coordinates of the k-point.
    isym : array
        Indices of symmetry operations in the little co-group. Indices make 
        reference to the symmetry operations stored in the header of the file 
        and stored in `IrrepTable.symmetries`. 
    line : str
        Line to be parsed. 
    
    Attributes
    ----------
    name : str
        Label of the k-point. 
    k : array, shape=(3,) 
        Direct coordinates of the k-point.
    isym : array
        Indices of symmetry operations in the little co-group. Indices make 
        reference to the symmetry operations stored in the header of the file 
        and stored in `IrrepTable.symmetries`. 
    """

    def __init__(self, name=None, k=None, isym=None, line=None):

        if line is not None:
            line_ = line.split(":")
            if line_[0].split()[0] != "kpoint":
                raise ValueError
            self.name = line_[0].split()[1]
            self.k = np.array(line_[1].split(), dtype=float)
            self.isym = str2list_space(
                line_[2]
            )  # [ int(x) for x in line_[2].split() ]  #
        else:
            self.name = name
            self.k = k
            self.isym = isym

    def __eq__(self, other):
        """
        Compares the attributes of this class with those of class instance 
        `other`.

        Parameters
        ----------
        other : class
            Instance of class `KPoint`.

        Returns
        -------
        bool
            `True` if all attributes have identical value, `False` otherwise.

        """
        if self.name != other.name:
            return False
        if np.linalg.norm(self.k - other.k) > 1e-8:
            return False
        if self.isym != other.isym:
            return False
        return True

    def show(self):
        """
        Create a `str` containing the values of all attributes.

        Returns
        -------
        str
            Line showing the values of all attributes.

        """
        return "{0} : {1}  symmetries : {2}".format(self.name, self.k, self.isym)

    def str(self):
        '''
        Create a `str` containing the values of all attributes.

        Returns
        -------
        str
            Line that, when parsed, would lead to an instance of class `KPoint` 
            with identical values of attributes.

        '''
        return "{0} : {1}  : {2}".format(
            self.name,
            " ".join(str(x) for x in self.k),
            " ".join(str(x) for x in sorted(self.isym)),
        )


class Irrep:
    """
    Parses the line containing the description of the irrep, stores the info in 
    its attributes. The methods print descriptions of the irrep. 

    Parameters
    ----------
    f : file object, default=None 
        It corresponds to the file containing the info about the space-group 
        and its irreps.
    nsym_group : int, default=None
        Number of symmetry operations in the "point-group" of the space-group.
    line : str, default=None
        Line with the description of an irrep, read from the file containing 
        info about the space-group and irreps.
    k_point : class instance, default=None
        Instance of class `KPoint`. It is `None` when file is old (deprecated?)

    Attributes
    ----------
    k : array, shape=(3,) 
        Attribute `k` of class `KPoint`. It is an array of direct coordinates 
        of a k-point.
    kpname : str
        Attribute `name` of class `KPoint`. It is the label of a k-point.
    has_rkmk : deprecated?
    name : str
        Label of the irrep.
    dim : int
        Dimension of the irrep.
    nsym : int
        Number of symmetry operations in the little co-group of the k-point.
    reality : bool
        `True` if characters of all symmetry operations are real, `False` 
        otherwise.
    characters : dict
        Each key is the index of a symmetry operation in the little co-group 
        and the corresponding value is the trace of that symmetry in the irrep.
    hasuvw : deprecated?
    """

    def __init__(self, f=None, nsym_group=None, line=None, k_point=None):

        if k_point is not None:
            self.__init__user(line, k_point)
            return
        s = f.readline().split()
        logger.debug(s)
        self.k = np.array(s[:3], dtype=float)
        self.has_rkmk = True if s[3] == "1" else "0" if s[3] == 0 else None
        self.name = s[4]
        self.kpname = s[7]
        self.dim = int(s[5])
        self.nsym = int(int(s[6]) / 2)
        self.reality = int(s[8])
        self.characters = {}
        self.hasuvw = False
        for isym in range(1, nsym_group + 1):
            ism, issym = [int(x) for x in f.readline().split()]
            assert ism == isym
            logger.debug("ism,issym", ism, issym)
            if issym == 0:
                continue
            elif issym != 1:
                raise RuntimeError("issym should be 0 or 1, <{0}> found".format(issym))
            abcde = []
            hasuvw = []
            for i in range(self.dim):
                for j in range(self.dim):
                    l1, l2 = [f.readline() for k in range(2)]
                    if i != j:
                        continue  # we need only diagonal elements
                    l1 = l1.strip()
                    if l1 == "1":
                        hasuvw.append(False)
                    elif l1 == "2":
                        hasuvw.append(True)
                    else:
                        raise RuntimeError(
                            "hasuvw should be 1 or 2. <{0}> found".format(l1)
                        )
                    abcde.append(np.array(l2.split(), dtype=float))
            if any(hasuvw):
                self.hasuvw = True
            if isym <= nsym_group / 2:
                self.characters[isym] = CharFunction(abcde)
        if not self.hasuvw:
            self.characters = {
                isym: self.characters[isym]() for isym in self.characters
            }
        logger.debug("characters are:", self.characters)
        assert len(self.characters) == self.nsym

    def __init__user(self, line, k_point):
        """
        Parse line containing info about an irrep and store this info in 
        attributes.
 
        Parameters
        ----------
        line : str, default=None
            Line with the description of an irrep, read from the file containing 
            info about the space-group and irreps.
        k_point : class instance, default=None
            Instance of class `KPoint`. It is `None` when file is old (deprecated?)

        """
        logger.debug("reading irrep line <{0}> for KP=<{1}> ".format(line, k_point.str()))
        self.k = k_point.k
        self.kpname = k_point.name
        line = line.split()
        self.name = line[0]
        self.dim = int(line[1])
        self.nsym = len(k_point.isym)
        self.reality = len(line[2:]) == self.nsym
        ch = np.array(line[2 : 2 + self.nsym], dtype=float)
        if not self.reality:
            ch = ch * np.exp(
                1.0j
                * np.pi
                * np.array(line[2 + self.nsym : 2 + 2 * self.nsym], dtype=float)
            )
        self.characters = {k_point.isym[i]: ch[i] for i in range(self.nsym)}

        logger.debug("the irrep {0}  ch= {1}".format(self.name, self.characters))

    def show(self):
        """
        Print label of the k-point and info about the irrep.
        """
        print(self.kpname, self.name, self.dim, self.reality)

    def str(self):
        """
        Generate a line describing the irrep and its character.

        Returns
        -------
        str
            Line describing the irrep, which as it is written in the table of 
            space-groups included in `IrRep`. This line contains the label, 
            dimension and character of the irrep.

        """
        logger.debug(self.characters)
        ch = np.array([self.characters[isym] for isym in sorted(self.characters)])
        if np.abs(np.imag(ch)).max() > 1e-6:
            str_ch = "   " + "  ".join(str_(x) for x in np.abs(ch))
            str_ch += "   " + "  ".join(str_(x) for x in np.angle(ch) / np.pi)
        else:
            str_ch = "   " + "  ".join(str_(x) for x in np.real(ch))
        return self.name + " {} ".format(self.dim) + str_ch


class IrrepTable:
    """
    Parse file corresponding to a space-group, storing the info in attributes. 
    Also contains methods to print and write this info in a file.

    Parameters
    ----------
    SGnumber : int
        Number of the space-group.
    spinor : bool
        `True` if the matrix describing the transformation of spinor components 
        should be read.
    fromUser : bool, default=True
        `True` if the file to be is one already included in `IrRep`. `False` if 
        the file to be read is an old (deprecated?) file.
    name : str, default=None
        Name of the file from which info about the space-group and irreps 
        should be read. If `None`, the code will try to open a file already 
        included in it.

    Attributes
    ----------
    number : int
        Number of the space-group.
    name : str
        Symbol of the space-group in Hermann-Mauguin notation. 
    spinor : bool
        `True` if wave-functions are spinors (SOC), `False` if they are scalars.
    nsym : int
       Number of symmetry operations in the "point-group" of the space-group. 
    symmetries : list
        Each component is an instance of class `SymopTable` corresponding to a 
        symmetry operation of the space-group.
    NK : int
        Number of maximal k-points in the Brillouin zone.
    irreps : list
        Each component is an instance of class `IrRep` corresponding to an 
        irrep of the little group of a maximal k-point.

    """

    def __init__(self, SGnumber, spinor, fromUser=True, name=None):
        if fromUser:
            self.__init__user(SGnumber, spinor, name)
            return
        self.number = SGnumber


        with open(
            os.path.dirname(os.path.realpath(__file__))
            + "/TablesIrrepsLittleGroup/TabIrrepLittle_{0}.txt".format(self.number),
            "r",
        ) as f:
            self.nsym, self.name = f.readline().split()
            self.spinor = spinor
            self.nsym = int(self.nsym)
            self.symmetries = [SymopTable(f.readline()) for i in range(self.nsym)]
            assert f.readline().strip() == "#"
            self.NK = int(f.readline())
            self.irreps = []
            try:
                while True:
                    self.irreps.append(Irrep(f=f, nsym_group=self.nsym))
                    logger.debug("irrep appended:")
                    logger.debug(self.irreps[-1].show())
                    f.readline()
            except EOFError:
                pass
            except IndexError as err:
                logger.debug(err)
                pass

        if self.spinor:
            self.irreps = [s for s in self.irreps if s.name.startswith("-")]
        else:
            self.irreps = [s for s in self.irreps if not s.name.startswith("-")]

        self.nsym = int(self.nsym / 2)
        self.symmetries = self.symmetries[0 : self.nsym]

    def show(self):
        '''
        Print info about symmetry operations and irreps.  
        '''
        for i, s in enumerate(self.symmetries):
            print(i + 1, "\n", s.R, "\n", s.t, "\n", s.S, "\n\n")
        for irr in self.irreps:
            irr.show()

    def save4user(self, name=None):
        """
        Creates the a file with info about the space-group and irreps. It is 
        used to create the files included in `IrRep`, with `name`=`None`.

        Parameters
        ----------
        name : str, default=None
            File in which info about the space-group and irreps will be written.

        """
        if name is None:
            name = "tables/irreps-SG={SG}-{spinor}.dat".format(
                SG=self.number, spinor="spin" if self.spinor else "scal"
            )
        fout = open(name, "w")
        fout.write(
            "SG={SG}\n name={name} \n nsym= {nsym}\n spinor={spinor}\n".format(
                SG=self.number, name=self.name, nsym=self.nsym, spinor=self.spinor
            )
        )
        fout.write(
            "symmetries=\n"
            + "\n".join(s.str(self.spinor) for s in self.symmetries)
            + "\n\n"
        )

        kpoints = {}

        for irr in self.irreps:
            if not irr.hasuvw:
                kp = KPoint(irr.kpname, irr.k, set(irr.characters.keys()))
                if (
                    len(
                        set(
                            [0.123, 0.313, 1.123, 0.877, 0.427, 0.246, 0.687]
                        ).intersection(list(kp.k))
                    )
                    == 0
                ):
                    try:
                        assert kpoints[kp.name] == kp
                    except KeyError:
                        kpoints[kp.name] = kp

        for kp in kpoints.values():
            fout.write("\n kpoint  " + kp.str() + "\n")
            for irr in self.irreps:
                if irr.kpname == kp.name:
                    fout.write(irr.str() + "\n")
        fout.close()

    def __init__user(self, SG, spinor, name):
        """
        Parse file containing info about space-group, its symmetry operations 
        and irreps.

        Parameters
        ----------
        SG : int
            Number of the space-group.
        spinor : bool 
            `True` if wave-functions are spinors (SOC), `False` if they are scalars.
        name : str
            File from which irreps will be read.

        """
        self.number = SG
        self.spinor = spinor
        if name is None:
            name = "{root}/tables/irreps-SG={SG}-{spinor}.dat".format(
                SG=self.number,
                spinor="spin" if self.spinor else "scal",
                root=os.path.dirname(__file__),
            )
            logger.debug("reading from a standard irrep table <{0}>".format(name))
        else:
            logger.debug("reading from a user-defined irrep table <{0}>".format(name))

        lines = open(name).readlines()[-1::-1]
        while len(lines) > 0:
            l = lines.pop().strip().split("=")
            # logger.debug(l,l[0].lower())
            if l[0].lower() == "SG":
                assert int(l[1]) == SG
            elif l[0].lower() == "name":
                self.name = l[1]
            elif l[0].lower() == "nsym":
                self.nsym = int(l[1])
            elif l[0].lower() == "spinor":
                assert str2bool(l[1]) == self.spinor
            elif l[0].lower() == "symmetries":
                print("reading symmetries")
                self.symmetries = []
                while len(self.symmetries) < self.nsym:
                    l = lines.pop()
                    # logger.debug(l)
                    try:
                        self.symmetries.append(SymopTable(l, from_user=True))
                    except Exception as err:
                        logger.debug(err)
                        pass
                break

        logger.debug("symmetries are:\n" + "\n".join(s.str() for s in self.symmetries))

        self.irreps = []
        while len(lines) > 0:
            l = lines.pop().strip()
            try:
                kp = KPoint(line=l)
                logger.debug("kpoint successfully read:", kp.str())
            except Exception as err:
                logger.debug("error while reading k-point <{0}>".format(l), err)
                try:
                    self.irreps.append(Irrep(line=l, k_point=kp))
                except Exception as err:
                    logger.debug("error while reading irrep <{0}>".format(l), err)
                    pass
