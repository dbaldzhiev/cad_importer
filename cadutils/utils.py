# VERSION 3.00
debug = False
import copy
import os
import re


if debug:
    try:
        import matplotlib.pyplot as plt
        from tqdm import tqdm
    except Exception as e:
        print(e)
        print("Missing debug modules...")
from .mik import *
from .tableTrans import *

class ReadCadastralFile:

    def __init__(self, pathtofile):
        data = opener(pathtofile)
        self.Filename = os.path.basename(pathtofile).replace(".cad", "")
        self.Header = HeaderLayer(data)
        self.ControlLayers = ControlLayers(data)
        self.CadasterLayer = CadasterLayer(data, self.Header, self.ControlLayers.ControlCheckLayers[
            [c.id for c in self.ControlLayers.ControlCheckLayers].index("CADASTER")].nested)
        self.Buildings = Buildings(data, self.Header)
        self.Tables = Semantic(data)

        try:
            ccl_indx = [m.id for m in self.ControlLayers.ControlCheckLayers].index("CADASTER")
            cc = self.ControlLayers.ControlCheckLayers[ccl_indx]
            self.CADASTERCHECK = controlCheck(self.CadasterLayer, cc, self.Tables)
        except Exception:
            self.CADASTERCHECK = "Fail"

    def __getitem__(self, item):
        return getattr(self, item)


class HeaderLayer:

    def __init__(self, data):
        rx_header = re.compile(
            r"HEADER\s*VERSION\s+(\S+)\s*EKATTE\s+(.*)\s*NAME\s+(.*)\s*PROGRAM\s+(\S+)\s+V?(\S+)\s*DATE\s+(.*)\s*FIRM\s+(.*)\s*REFERENCE\s+(\S+)\s+(\S+)\s*WINDOW\s+(.*)\s*COORDTYPE\s+(\d+),(.*)\s*CONTENTS\s+(.*)\s*COMMENT\s+(.*)\s*END_HEADER",
            re.MULTILINE)
        extract = rx_header.search(data).groups()

        self.cadversion = extract[0].replace("\r", "")
        self.ekatte = extract[1].replace("\r", "")
        self.loc = extract[2].replace("\r", "")
        self.sw = extract[3].replace("\r", "")
        self.swv = extract[4].replace("\r", "")
        self.date = extract[5].replace("\r", "")
        self.firm = extract[6].replace("\r", "")

        self.refX = float(extract[8].replace("\r", ""))
        self.refY = float(extract[7].replace("\r", ""))
        self.window = extract[9].replace("\r", "")
        self.coordid = extract[10].replace("\r", "")
        self.coordidh = extract[11].replace("\r", "")
        self.content = extract[12].replace("\r", "")
        self.comments = extract[13].replace("\r", "")

    def __getitem__(self, item):
        return getattr(self, item)


class CadasterLayer:
    def ContourDictBuilder(self,conts):
        conD = {}
        for c in conts:
            c = c.groups()
            rx_contid = re.compile(r"(\d+)")
            conD[c[1]] = list(map(int, rx_contid.findall(c[6])))
        return conD
    def LineDictBuilder(self,lins):
        lld = {}
        for i in range(len(lins)):
            lld[lins[i].lid] = i
        return lld
    def __init__(self, data, hdr, nests):

        rx_cadLayer = re.compile(r"LAYER CADASTER([\s\S]*?)END_LAYER")
        extract = rx_cadLayer.search(data)
        if extract:
            parse = objectSearch(extract.group())

            if parse[0]:
                self.lineObj = [LineC(line.groups(), hdr) for line in parse[0]]
            if parse[1]:
                contparse = list(parse[1])
                LDic = self.LineDictBuilder(self.lineObj)
                CDic = self.ContourDictBuilder(contparse)
                if debug:
                    contparse = tqdm(contparse)
                self.contourObj = [ContC(contour.groups(), hdr, self.lineObj, LDic, nests, CDic) for contour in contparse]
            if parse[2]:
                self.gepointObj = [GeoPointC(geopt.groups(), hdr) for geopt in parse[2]]
            if parse[3]:
                self.textObj = [TextC(text.groups(), hdr) for text in parse[3]]
            if parse[4]:
                self.symbolObj = [SymbolC(symb.groups(), hdr) for symb in parse[4]]

    def __getitem__(self, item):
        return getattr(self, item)


class ControlLayers:
    def __init__(self, data):
        rx_controlCadaster = re.compile(r"^CONTROL\s+(\S+)\s+([\S\s]*?)END_CONTROL", re.MULTILINE)

        self.ControlCheckLayers = [ControlLayer(cl.groups()) for cl in rx_controlCadaster.finditer(data)]

    def __getitem__(self, item):
        return getattr(self, item)


class ControlLayer:
    def __init__(self, data):
        self.id = data[0]

        self.points = int(re.search(r"(?:NUMBER_POINTS\s+(\d+)\s+)", data[1]).group(1))
        self.lines = int(re.search(r"(?:NUMBER_LINES\s+(\d+)\s+)", data[1]).group(1))
        self.symb = int(re.search(r"(?:NUMBER_SYMBOLS\s+(\d+)\s+)", data[1]).group(1))
        self.txt = int(re.search(r"(?:NUMBER_TEXTS\s+(\d+)\s+)", data[1]).group(1))
        self.contours = int(re.search(r"(?:NUMBER_CONTURS\s+(\d+)\s+)", data[1]).group(1))
        self.nested = {}
        nests = [[n[0], re.findall(r"(\S+)", n[1])] for n in
                 re.findall(r"(?:^CONTUR_NESTED\s+(\S+)(?:\s+(.+)))", data[1], re.MULTILINE)]
        for nest in nests:
            self.nested[nest[0]] = nest[1]

    def __getitem__(self, item):
        return getattr(self, item)


class Buildings:
    def __init__(self, data, hdr):

        rx_LevelSchemasLayer = re.compile(r"LAYER SHEMI([\s\S]*?)END_LAYER")
        rx_Levels = re.compile(r"ET\s+(\S+)\s+(\S+)\s+([\s\S]*?)END_ET")
        extract = rx_LevelSchemasLayer.search(data)
        if extract:
            extract = rx_Levels.finditer(extract.group(0))
            if extract:
                extract = tuple(extract)
                self.list = []
                if extract:
                    for et in extract:
                        if not (et.group(1) in [bid.id for bid in self.list]):
                            b = Building(et.group(1))
                            b.addLevel(et.groups(), hdr)
                            self.list.append(b)
                        else:
                            self.list[[bid.id for bid in self.list].index(et.group(1))].addLevel(et.groups(),
                                                                                                 hdr)

    def __getitem__(self, item):
        return getattr(self, item)


class Building:
    def __init__(self, uid):
        self.id = uid
        self.levels = []

    def addLevel(self, lvldata, hdr):
        self.levels.append(LevelObj(lvldata, hdr))

    def __getitem__(self, item):
        return getattr(self, item)


class LevelObj:
    def LineDictBuilder(self,lins):
        lld = {}
        for i in range(len(lins)):
            lld[lins[i].lid] = i
        return lld
    def __init__(self, data, hdr):
        self.lvl = data[1]
        parse = objectSearch(data[2])

        if parse[0]:
            self.lineObj = [LineC(line.groups(), hdr) for line in parse[0]]
        if parse[1]:
            LDic = self.LineDictBuilder(self.lineObj)
            self.contourObj = [ContC(contour.groups(), hdr, self.lineObj, LDic, nests="", cdicmap="") for contour in parse[1]]

    def __getitem__(self, item):
        return getattr(self, item)


class LineC:
    def __init__(self, array, hdr):
        self.type = str(array[0])
        self.lid = int(array[1])
        self.bordertype = str(array[2])
        self.datecreated = str(array[3])
        self.datedestroyed = str(array[4])
        rx_ptlist = re.compile(r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+);")
        self.ptlist = [LinecPt(p.groups(), hdr) for p in rx_ptlist.finditer(array[5])]
        self.get_point_sequence = [pt.get_XY for pt in self.ptlist]
        self.get_referenced_point_sequence = [pt.get_XYR for pt in self.ptlist]

    def __getitem__(self, item):
        return getattr(self, item)


class LinecPt:
    def __init__(self, array, hdr):
        self.ptN = int(array[0])
        self.ptY = float(array[1])
        self.ptX = float(array[2])
        self.ptacc = array[3]
        self.permasig = array[4]
        self.deter = array[5]
        self.get_XY = self.ptX, self.ptY
        self.get_XYR = self.ptX + hdr.refX, self.ptY + hdr.refY
        self.ptXR = self.ptX + hdr.refX
        self.ptYR = self.ptY + hdr.refY

    def __getitem__(self, item):
        return getattr(self, item)


class ContC:

    def polygonize(self, data, deep=True):
        badcontour = False
        pgon = []

        if deep:
            line_strings = copy.deepcopy(data)
        else:
            line_strings = data
        whilesstopper = 0
        while len(line_strings) > 0 and whilesstopper < 2:
            ingest = len(line_strings)

            if len(pgon) == 0:
                pgon.extend(line_strings[0])
                del line_strings[0]

            for cl in line_strings:
                if pgon[-1] == cl[0] or pgon[-1] == cl[-1] or pgon[0] == cl[0] or pgon[0] == cl[-1]:

                    if pgon[0] == cl[0] or pgon[0] == cl[-1]:
                        pgon = pgon[::-1]  ## reverse pgon
                    if pgon[-1] == cl[0] and pgon[0] == cl[-1]:
                        del cl[0]
                        pgon.extend(cl)  ## End Straing
                        del line_strings[line_strings.index(cl)]
                        break

                    if pgon[-1] == cl[-1] and pgon[0] == cl[0]:
                        del cl[-1]
                        pgon.extend(cl[::-1])  ## End Rev
                        del line_strings[line_strings.index(cl)]
                        break

                    else:

                        lastItemInContour = pgon[-1]
                        if pgon[-1] == cl[0]:
                            del cl[0]
                            pgon.extend(cl)  ## Standard Straight
                            del line_strings[line_strings.index(cl)]
                            break

                        if lastItemInContour == cl[-1]:
                            del cl[-1]
                            pgon.extend(cl[::-1])  ## Standard Rev
                            del line_strings[line_strings.index(cl)]
                            break
                else:

                    if pgon[0] == pgon[-1] and len(line_strings) > 0:
                        chain,badness = self.polygonize(line_strings, False)

                        intersection = list(set(pgon).intersection(set(chain)))

                        if not (len(chain) == len(intersection)):
                            if chain[0] == chain[-1]:
                                if len(intersection) == 1:
                                    starpoint_pgon_idx = pgon.index(intersection[0])
                                    starpoint_chain_idx = chain.index(intersection[0])
                                    chain_pA = chain[:starpoint_chain_idx]
                                    chain_pB = chain[starpoint_chain_idx:]
                                    new_chain = chain_pB + chain_pA
                                    pgon = pgon[:starpoint_pgon_idx + 1] + new_chain[::-1] + pgon[
                                                                                             1 + starpoint_pgon_idx:]
                                    break
                                else:
                                    badcontour = True
                                    print("INVALID PGON too many star points")
                                    break
                            else:
                                badcontour = True
                                print("STRAY CONTOUR")

                        else:
                            print("DUPLICATE CHAIN")
            if ingest == len(line_strings):
                whilesstopper += 1
                badcontour = True

        if badcontour and deep and debug:
            fig, ax = plt.subplots(2)
            fig.suptitle(self.cid, fontsize=16)
            for l in data:
                ax[0].plot([x[0] for x in l], [y[1] for y in l])
            ax[1].plot([x[0] for x in pgon], [y[1] for y in pgon])
            plt.show()

        if not pgon[0] == pgon[-1] and deep:
            print("P NOT C")
            pgon = pgon.extend(pgon[0])

        return (pgon, badcontour)

    def __init__(self, cArray, hdr, lines, linesdic, nests, cdicmap):
        self.type = int(cArray[0])
        self.cid = cArray[1]
        self.posY = float(cArray[2])
        self.posX = float(cArray[3])
        self.datecreated = cArray[4]
        self.datedestroyed = cArray[5]
        rx_contid = re.compile(r"(\d+)")
        self.pgon_ids = list(map(int, rx_contid.findall(cArray[6])))

        self.pgon_pt, self.pgon_bad_flag = self.polygonize([lines[linesdic[i]].get_referenced_point_sequence.copy() for i in self.pgon_ids])
        self.holes_exist = False
        if self.cid in nests:
            self.holes_exist = True
            self.holes_id = [cdicmap.get(ncon) for ncon in nests.get(self.cid)]
            hole_generator = [[lines[linesdic.get(hls)].get_referenced_point_sequence for hls in h] for h in self.holes_id]
            self.holes_pt = []
            self.holes_bad_flag = []
            for individual_hole in hole_generator:
                loop_pt,loop_flag = self.polygonize(individual_hole)
                self.holes_bad_flag.append(loop_flag)
                self.holes_pt.append(loop_pt)

        self.posXR = self.posX + hdr.refX
        self.posYR = self.posY + hdr.refY

    def __getitem__(self, item):
        return getattr(self, item)


class TextC:
    def __init__(self, array, hdr):
        self.type = int(array[0])
        self.id = int(array[1])
        self.posY = float(array[2])
        self.posX = float(array[3])
        self.posXR = self.posX + hdr.refX
        self.posYR = self.posY + hdr.refY
        self.posH = float(array[4])
        self.datecreated = array[5]
        self.datedestroyed = array[6]
        self.rotgon = float(array[7])
        self.rotdeg = (100 - float(array[7])) * 180.0 / 200.0
        self.halign = str(array[8])
        self.valign = str(array[9])
        self.prefixtext = str(array[10])
        self.objtype = str(array[11])
        self.graphicid = str(array[12])
        self.grapicparam = str(array[13])
        self.suffixtext = str(array[14])

    def __getitem__(self, item):
        return getattr(self, item)


class GeoPointC:
    def __init__(self, array, hdr):
        self.type = array[0]
        self.id = array[1]
        self.posY = float(array[2])
        self.posX = float(array[3])
        self.posH = float(array[4])
        self.posclass = array[5]
        self.accy = array[6]
        self.accx = array[7]
        self.hclass = array[8]
        self.acch = array[9]
        self.stab = array[10]
        self.stabalt = array[11]
        self.nsig = array[12]
        self.underg = array[13]
        self.oldN = array[14]
        self.datecreated = array[15]
        self.datedestroyed = array[16]
        self.posXR = self.posX + hdr.refX
        self.posYR = self.posY + hdr.refY

    def __getitem__(self, item):
        return getattr(self, item)


class SymbolC:
    def __init__(self, array, hdr):
        self.type = array[0]
        self.id = array[1]
        self.posY = float(array[2])
        self.posX = float(array[3])
        self.rot = array[4]
        self.scale = array[5]
        self.datecreated = array[6]
        self.datedestroyed = array[7]
        self.posXR = self.posX + hdr.refX
        self.posYR = self.posY + hdr.refY

    def __getitem__(self, item):
        return getattr(self, item)


class Semantic:
    def __init__(self, data):
        rx_table = re.compile(r"^TABLE\s+(\S+)\s+([\s\S]*?)END_TABLE", re.MULTILINE)
        self.Tables = []

        for tablematch in rx_table.finditer(data):
            self.Tables.append(Table(tablematch.groups()))

    def __getitem__(self, item):
        return getattr(self, item)

def closest_strings(dictionary, value):
    closest_codes = sorted(dictionary.keys(), key=lambda x: abs(x - value))[:2]
    closest_strings = [dictionary[code] for code in closest_codes]
    return closest_strings
class Table:

    def __init__(self, match):
        self.name = match[0]
        tableBody = match[1]
        rx_fields = re.compile(r"^F\s+(\S+)\s+([CNSLDBT])\s+(\d{1,2})\s+(\d)(?:\s+([123]))?(?:\s+(\S+))*?$",
                               re.MULTILINE)
        self.fields = [Field(found_field.groups()) for found_field in rx_fields.finditer(tableBody)]
        field_types = {
            "C": "\s*\\\"(.*?)\\\"\s*",
            "S": "(.*?)",
            "N": "(.*?)",
            "L": "(.*?)",
            "B": "([TF]?)",
            "D": "(\d{1,2}\.\d{1,2}\.\d{2,4})?",
            "T": "(\d{1,2}\.\d{1,2}\.\d{2,4})?",
        }
        if self.fields:
            regex_entrys = "^D\s*"
            rx_check = re.compile(regex_entrys + field_types.__getitem__(self.fields[0].type), re.MULTILINE)
            for f in self.fields:
                ent = field_types.__getitem__(f.type)
                if regex_entrys != "^D\s*":
                    ent = "," + ent
                regex_entrys = regex_entrys + ent

            rx_entrys = re.compile(regex_entrys, re.MULTILINE)
            self.entrys = [list(en.groups()) for en in rx_entrys.finditer(match[1])]

            if self.name == "POZEMLIMOTI":
                for f in self.fields:
                    if fields_pozemlimoti.get(f.name) is not None:
                        f.name = fields_pozemlimoti.get(f.name)
            if self.name == "PRAVA":
                for f in self.fields:
                    if fields_prava.get(f.name) is not None:
                        f.name = fields_prava.get(f.name)
            if self.name == "PERSONS":
                for f in self.fields:
                    if fields_persons.get(f.name) is not None:
                        f.name = fields_persons.get(f.name)

            if self.name == "SGRADI":
                for f in self.fields:
                    if fields_sgradi.get(f.name) is not None:
                        f.name = fields_sgradi.get(f.name)

                for value in self.entrys:
                    if vid_sobstvenost.get(int(value[1])) is not None:
                        value[1] = vid_sobstvenost.get(int(value[1]))
                    else:
                        CS = closest_strings(vid_sobstvenost, int(value[1]))
                        value[1] = "{0} / {1}".format(CS[0],CS[1])

                    if sg_pred.get(int(value[3])) is not None:
                        value[3] = sg_pred.get(int(value[3]))
                    else:
                        CS = closest_strings(sg_pred, int(value[3]))
                        value[3] = "{0} / {1}".format(CS[0],CS[1])

            if self.name == "APARTS":
                for f in self.fields:
                    if fields_aparts.get(f.name) is not None:
                        f.name = fields_aparts.get(f.name)
            if self.name == "ULICI":
                for f in self.fields:
                    if fields_ulici.get(f.name) is not None:
                        f.name = fields_ulici.get(f.name)
            if self.name == "ADDRESS":
                for f in self.fields:
                    if fields_address.get(f.name) is not None:
                        f.name = fields_address.get(f.name)
            if self.name == "MESTNOSTI":
                for f in self.fields:
                    if fields_mestnosti.get(f.name) is not None:
                        f.name = fields_mestnosti.get(f.name)
            if self.name == "ZAPOVEDI":
                for f in self.fields:
                    if fields_zapovedi.get(f.name) is not None:
                        f.name = fields_zapovedi.get(f.name)
            if self.name == "IZDATELI":
                for f in self.fields:
                    if fields_izdateli.get(f.name) is not None:
                        f.name = fields_izdateli.get(f.name)
            if self.name == "HISTORY":
                for f in self.fields:
                    if fields_history.get(f.name) is not None:
                        f.name = fields_history.get(f.name)
            if self.name == "SERVITUTI":
                for f in self.fields:
                    if fields_servituti.get(f.name) is not None:
                        f.name = fields_servituti.get(f.name)
            if self.name == "OGRPIMO":
                for f in self.fields:
                    if fields_address.get(f.name) is not None:
                        f.name = fields_address.get(f.name)
            if self.name == "DOCS":
                for f in self.fields:
                    if fields_docs.get(f.name) is not None:
                        f.name = fields_docs.get(f.name)
            if self.name == "GORIMOTI":
                for f in self.fields:
                    if fields_gorimoti.get(f.name) is not None:
                        f.name = fields_gorimoti.get(f.name)




            checker = [chk.groups() for chk in rx_check.finditer(match[1])]
            if len(self.entrys) == len(checker):
                self.check = True
            else:
                self.check = False
        else:
            self.check = "TABLE WITHOUT FIELDS"

    def __getitem__(self, item):
        return getattr(self, item)

class Field:
    def __init__(self, data):
        self.name = data[0]
        self.type = data[1]
        self.length = data[2]
        self.dec = data[3]
        self.flag = data[4]
        self.tableref = data[5]

    def __getitem__(self, item):
        return getattr(self, item)


def objectSearch(data):
    rx_textobj = re.compile(
        r"^T\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s(\S+)\s+(\S+)\s+(\S+)\s+([LCR])([TCD])\s+(?:(?:\"(.*)\"\s)?([CPLVSA])\s+(\S+)\s(AN|SI|NU|LE|XC|YC|HI|AR|LP|AD|ST|IO)\s)?\"(.*)\"",
        re.MULTILINE)
    rx_lineobj = re.compile(
        r"(?:^L\s+(\d+)\s+(\d+)\s+(\d+)\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))\s+)((?:(?:\S+)\s+(?:\S+)\s+(?:\S+)\s+(?:\S+)\s+(?:\S+)\s+(?:\S+);(?:\s+)?)*)",
        re.MULTILINE)
    rx_conobj = re.compile(
        r"C\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))\s+((?:(?:\d+)\s+)*)",
        re.MULTILINE)
    rx_symbobj = re.compile(
        r"S\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))",
        re.MULTILINE)
    rx_geopointobj = re.compile(
        r"P\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(?:(\d+(?:.\d+)*)|(?:0))\s+(?:(\d+(?:.\d+)*)|(?:0))\s+(\d+)\s+(?:(\d+(?:.\d+)*)|(?:0))\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\"(.*)\"\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))\s+((?:\d{1,2}\.\d{1,2}\.\d{2,4})|(?:0))",
        re.MULTILINE)
    lineObjectsStrings = rx_lineobj.finditer(data)
    contObjectsStrings = rx_conobj.finditer(data)
    geoPtObjectsStrings = rx_geopointobj.finditer(data)
    textObjectsStrings = rx_textobj.finditer(data)
    symbObjectsStrings = rx_symbobj.finditer(data)
    return lineObjectsStrings, contObjectsStrings, geoPtObjectsStrings, textObjectsStrings, symbObjectsStrings


def opener(filename):
    if os.path.exists(filename[:-4] + "_cached.tcad"):
        filename = filename[:-4] + "_cached.tcad"
    f = open(filename, "rb")
    filetext = f.read()
    f.close()
    try:
        cadText = filetext.decode("utf-8")
    except Exception:
        cadText = translate(filetext).replace("\r", "")
        ff = open(filename[:-4] + "_cached.tcad", "x", encoding="utf-8")
        ff.write(cadText)
        ff.close()
    return cadText.replace("\r\n", "\n")


def translate(input):
    newChars = map(
        lambda x: bytes([x]) if (x < 128) else bytes(mikdict.get(x), "utf-8") if (x <= 191) and (x >= 128) else b"",
        input)
    res = b''.join(newChars).decode("utf-8")
    return res

def controlCheck(cl, cc, tb):
    if (len(cl.lineObj) == cc.lines) and (len(cl.contourObj) == cc.contours) and (
            len(cl.symbolObj) == cc.symb) and (len(cl.gepointObj) == cc.points) and (len(cl.textObj) == cc.txt):
        chk_cad = True
    else:
        chk_cad = False

    if len(tb.Tables) > 0:
        if all(tb.check for tb in tb.Tables):
            chk_tb = True
        else:
            chk_tb = False
    else:
        chk_tb = "N/A"
    return chk_cad, chk_tb