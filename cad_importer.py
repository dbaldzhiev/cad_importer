# -*- coding: utf-8 -*-
"""
/***************************************************************************
 cad_import_class
                                 A QGIS plugin
 Import Bulgarian CAD4 files to QGIS.
                              -------------------
        begin                : 2023-01-11
        copyright            : (C) 2023 by Dimitar Baldzhiev
        email                : db@tectonica-b.com
 ***************************************************************************/
 
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
#from qgis.core import QgsVectorLayer, QgsField, QgsProject, QgsFeature
import qgis.core as qc

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .cad_importer_dialog import cad_import_classDialog
import os.path
from .cadutils import utils


from inspect import getsourcefile
from os.path import abspath
import re
class cad_import_class:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'cad_import_class_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CAD4 Importer')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('cad_import_class', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/cad_importer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'CAD4 Importer'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&CAD4 Importer'),
                action)
            self.iface.removeToolBarIcon(action)

    def addLines(self,CF,merge):

        if merge == 2:
            layers = qc.QgsProject.instance().mapLayersByName("Lines_")
            exist = True if layers else False
            if not(exist):
                layerBag = qc.QgsVectorLayer("LineString?crs=epsg:7801", "Lines_", "memory")
            else:
                layerBag = qc.QgsProject.instance().mapLayersByName("Lines_")[0]
        if merge == 0:
            layerBag = qc.QgsVectorLayer("LineString?crs=epsg:7801", "Lines_" + CF.Filename, "memory")

        pr = layerBag.dataProvider()
        pr.addAttributes([
            qc.QgsField("id", QVariant.String),
            qc.QgsField("type", QVariant.String),
        qc.QgsField("bordertype", QVariant.String),
        qc.QgsField("datecreated", QVariant.String),
        qc.QgsField("datedestroyed", QVariant.String)])
        layerBag.updateFields()
        qc.QgsProject.instance().addMapLayer(layerBag)
        layerBag.startEditing()
        layerBag.loadNamedStyle(os.path.dirname(abspath(getsourcefile(lambda: 0)))+"\LLStyle.qml")

        for line in CF.CadasterLayer.lineObj:
            feat = qc.QgsFeature(layerBag.fields())  # Create the feature
            feat.setAttribute("id", line.lid)  # set attributes
            feat.setAttribute("type", line.type)
            feat.setAttribute("bordertype", line.bordertype)
            feat.setAttribute("datecreated", line.datecreated)
            feat.setAttribute("datedestroyed", line.datedestroyed)
            feat.setGeometry(qc.QgsGeometry.fromPolylineXY(
                [qc.QgsPointXY(ptx, pty) for ptx, pty in line.get_referenced_point_sequence]))
            layerBag.addFeature(feat)  # add the feature to the layer

        layerBag.endEditCommand()  # Stop editing
        layerBag.commitChanges()  # Save changes
    def addContours(self,CF,merge):
        if merge == 2:
            layers = qc.QgsProject.instance().mapLayersByName("Contours_")
            exist = True if layers else False
            if not(exist):
                layerBag = qc.QgsVectorLayer("Polygon?crs=epsg:7801", "Contours_", "memory")
            else:
                layerBag = qc.QgsProject.instance().mapLayersByName("Contours_")[0]
        if merge == 0:
            layerBag = qc.QgsVectorLayer("Polygon?crs=epsg:7801", "Contours_" + CF.Filename, "memory")


        pr = layerBag.dataProvider()
        pr.addAttributes([
            qc.QgsField("id", QVariant.String),
            qc.QgsField("type", QVariant.String),
        qc.QgsField("datecreated", QVariant.String),
        qc.QgsField("datedestroyed", QVariant.String)])
        layerBag.updateFields()
        qc.QgsProject.instance().addMapLayer(layerBag)
        layerBag.startEditing()
        layerBag.loadNamedStyle(os.path.dirname(abspath(getsourcefile(lambda: 0)))+"\CLStyle.qml")


        for contour in CF.CadasterLayer.contourObj:
            feat = qc.QgsFeature(layerBag.fields())  # Create the feature
            feat.setAttribute("id", contour.cid)  # set attributes
            feat.setAttribute("type", contour.type)
            feat.setAttribute("datecreated", contour.datecreated)
            feat.setAttribute("datedestroyed", contour.datedestroyed)
            if not(contour.pgon_bad_flag) and contour.pgon_pt is not None:
                a = [qc.QgsPointXY(ptx, pty) for ptx, pty in contour.pgon_pt]
                feat.setGeometry(qc.QgsGeometry.fromPolygonXY([a]))
                layerBag.addFeature(feat)  # add the feature to the layer

        layerBag.endEditCommand()  # Stop editing
        layerBag.commitChanges()  # Save changes
    def addPt(self,CF,merge):

        if merge == 2:
            layers = qc.QgsProject.instance().mapLayersByName("GeoPts_")
            exist = True if layers else False
            if not(exist):
                layerBag = qc.QgsVectorLayer("Point?crs=epsg:7801", "GeoPts_", "memory")
            else:
                layerBag = qc.QgsProject.instance().mapLayersByName("GeoPts_")[0]
        if merge == 0:
            layerBag = qc.QgsVectorLayer("Point?crs=epsg:7801", "GeoPts_" + CF.Filename, "memory")



        pr = layerBag.dataProvider()
        pr.addAttributes([
            qc.QgsField("id", QVariant.String),
            qc.QgsField("type", QVariant.String),
            qc.QgsField("posH", QVariant.String)])
        layerBag.updateFields()
        qc.QgsProject.instance().addMapLayer(layerBag)
        layerBag.startEditing()
        layerBag.loadNamedStyle(os.path.dirname(abspath(getsourcefile(lambda: 0)))+"\GLStyle.qml")


        for gptt in CF.CadasterLayer.gepointObj:
            feat = qc.QgsFeature(layerBag.fields())  # Create the feature
            feat.setAttribute("id", gptt.id)  # set attributes
            feat.setAttribute("type", gptt.type)
            feat.setAttribute("posH", gptt.posH)
                #a = [qc.QgsPointXY(ptx, pty) for ptx, pty in contour.pgon_pt]
            feat.setGeometry(qc.QgsPoint(gptt.posXR, gptt.posYR))
            layerBag.addFeature(feat)  # add the feature to the layer

        layerBag.endEditCommand()  # Stop editing
        layerBag.commitChanges()  # Save changes

    def addCadTxt(self, CF,merge):

        if merge == 2:
            layers = qc.QgsProject.instance().mapLayersByName("Texts_")
            exist = True if layers else False
            if not (exist):
                layerBag = qc.QgsVectorLayer("Point?crs=epsg:7801", "Texts_", "memory")
            else:
                layerBag = qc.QgsProject.instance().mapLayersByName("Texts_")[0]
        if merge == 0:
            layerBag = qc.QgsVectorLayer("Point?crs=epsg:7801", "Texts_" + CF.Filename, "memory")


        pr = layerBag.dataProvider()
        pr.addAttributes([
            qc.QgsField("id", QVariant.String),
            qc.QgsField("type", QVariant.String),
            qc.QgsField("prefixtext", QVariant.String),
            qc.QgsField("suffixtext", QVariant.String),
            qc.QgsField("datecreated", QVariant.String),
            qc.QgsField("datedestroyed", QVariant.String)
        ])
        layerBag.updateFields()
        qc.QgsProject.instance().addMapLayer(layerBag)
        layerBag.startEditing()
        layerBag.loadNamedStyle(os.path.dirname(abspath(getsourcefile(lambda: 0)))+"\TLStyle.qml")

        for txt in CF.CadasterLayer.textObj:
            feat = qc.QgsFeature(layerBag.fields())  # Create the feature
            feat.setAttribute("id", txt.id)  # set attributes
            feat.setAttribute("type", txt.type)
            feat.setAttribute("prefixtext", txt.prefixtext.replace("None",""))  # set attributes
            feat.setAttribute("suffixtext", txt.suffixtext.replace("None",""))
            feat.setAttribute("datecreated", txt.datecreated)  # set attributes
            feat.setAttribute("datedestroyed", txt.datedestroyed)
            # a = [qc.QgsPointXY(ptx, pty) for ptx, pty in contour.pgon_pt]
            feat.setGeometry(qc.QgsPoint(txt.posXR, txt.posYR))
            layerBag.addFeature(feat)  # add the feature to the layer

        layerBag.endEditCommand()  # Stop editing
        layerBag.commitChanges()  # Save changes

    def addTables(self, CF, merge):
        for tbb in CF.Tables.Tables:
            if merge == 2:
                layers = qc.QgsProject.instance().mapLayersByName("Table_" + tbb.name)
                exist = True if layers else False
                if not (exist):
                    layerBag = qc.QgsVectorLayer("NoGeometry?crs=epsg:7801", "Table_" + tbb.name, "memory")
                else:
                    layerBag = qc.QgsProject.instance().mapLayersByName("Table_" + tbb.name)[0]
            if merge == 0:
                layerBag = qc.QgsVectorLayer("NoGeometry?crs=epsg:7801", "Table_{0}_{1}".format(CF.Filename,tbb.name), "memory")
            pr = layerBag.dataProvider()
            FieldNames = []
            for Field in tbb.fields:
                FieldNames.append(Field.name)
            pr.addAttributes([qc.QgsField(f,QVariant.String) for f in FieldNames])
            layerBag.updateFields()
            qc.QgsProject.instance().addMapLayer(layerBag)
            layerBag.startEditing()

            for ent in tbb.entrys:
                feat = qc.QgsFeature(layerBag.fields())
                for value,field in zip(ent,FieldNames):
                    feat.setAttribute(field,value)
                layerBag.addFeature(feat)

            layerBag.endEditCommand()  # Stop editing
            layerBag.commitChanges()  # Save changes
    def run(self):
            """Run method that performs all the real work"""

            # Create the dialog with elements (after translation) and keep reference
            # Only create GUI ONCE in callback, so that it will only load when the plugin is started
            if self.first_start == True:
                self.first_start = False
                self.dlg = cad_import_classDialog()

            # show the dialog
            self.dlg.show()
            # Run the dialog event loop
            result = self.dlg.exec_()
            # See if OK was pressed
            if result:
                # Do something useful here - delete the line containing pass and
                # substitute with your code.
                filenames = self.dlg.cadFilePath.splitFilePaths(self.dlg.cadFilePath.filePath())
                mt = self.dlg.mergeToggle.checkState()
                for filename in filenames:
                    #try:
                    CCF = utils.ReadCadastralFile(filename)
                    self.addContours(CCF,mt)
                    self.addLines(CCF,mt)
                    self.addPt(CCF,mt)
                    self.addCadTxt(CCF,mt)
                    self.addTables(CCF,mt)
                    #print(filename + " Imported!")
                    #except:
                    #    print(filename + " Failed!")
                    #    pass
                print("READING DONE")

