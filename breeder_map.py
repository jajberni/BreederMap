# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BreederMap
                                 A QGIS plugin
 Creates a field layout for a typical row-column breeder's trial
                              -------------------
        begin                : 2018-02-20
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Jose A. Jimenez Berni
        email                : jose.jimenez.berni@csic.es
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtCore import QObject, SIGNAL, QVariant
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from breeder_map_dialog import BreederMapDialog
import os.path

import math
from qgis.gui import *
from qgis.core import QgsFeature, QgsGeometry, QgsFeatureRequest, QgsVectorDataProvider, QgsPoint, QgsVectorLayer, QgsField, QgsMapLayerRegistry


class BreederMap:
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
            'BreederMap_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Breeder Map')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'BreederMap')
        self.toolbar.setObjectName(u'BreederMap')

        # Plugin functionality
        self.canvas = self.iface.mapCanvas() #CHANGE
        # this QGIS tool emits as QgsPoint after each click on the map canvas
        self.clickTool = QgsMapToolEmitPoint(self.canvas)

        # create a list to hold our selected feature ids
        self.select_list = []
        # current layer ref (set in handleLayerChange)
        self.clayer = None
        # current layer dataProvider ref (set in handleLayerChange)
        self.provider = None


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
        return QCoreApplication.translate('BreederMap', message)


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

        # Create the dialog (after translation) and keep reference
        self.dlg = BreederMapDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/BreederMap/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Breeder Map'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # connect our select function to the canvasClicked signal
        result = QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"),
                                 self.select_feature)

        result = QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.handle_layer_change)

        self.dlg.pb_new_layer.clicked.connect(self.createLayer)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Breeder Map'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""

        # set the current layer immediately if it exists, otherwise it will be set on user selection
        self.clayer = self.iface.mapCanvas().currentLayer()
        if self.clayer:
            self.provider = self.clayer.dataProvider()
        # make our clickTool the tool that we'll use for now
        self.canvas.setMapTool(self.clickTool)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            if self.select_list:
                heading = self.dlg.dsb_heading.value()
                columns = self.dlg.sb_columns.value()
                rows = self.dlg.sb_rows.value()
                col_distance = self.dlg.dsb_col_dist.value()
                row_distance = self.dlg.dsb_row_dist.value()
                for row_ix in range(rows):
                    for col_ix in range(columns):
                        s_feat = QgsFeature()
                        if self.provider.getFeatures(QgsFeatureRequest().setFilterFid(self.select_list[0])).nextFeature(s_feat):
                            if not ((row_ix==0) & (col_ix==0)):
                                # Don't clone first one
                                self.clone_plot(s_feat, col_distance, row_distance, -heading, col_ix, row_ix)

        self.iface.mapCanvas().refresh()

    def select_feature(self, point, button):
        #QMessageBox.information(self.iface.mainWindow(), "Info", "in selectFeature function")
        # setup the provider select to filter results based on a rectangle
        pnt_geom = QgsGeometry.fromPoint(point)
        # scale-dependent buffer of 2 pixels-worth of map units
        pnt_buff = pnt_geom.buffer((self.canvas.mapUnitsPerPixel() * 2), 0)
        rect = pnt_buff.boundingBox()
        # get currentLayer and dataProvider
        self.clayer = self.canvas.currentLayer()
        self.select_list = []
        if self.clayer:
            self.provider = self.clayer.dataProvider()
            feat = QgsFeature()
            # create the select statement
            for feat in self.provider.getFeatures():
                # if the feat geom returned from the selection intersects our point then put it in a list
                if feat.geometry().intersects(pnt_geom):
                    self.select_list.append(feat.id())

            # make the actual selection
            if self.select_list:
                self.clayer.setSelectedFeatures(self.select_list)
        else:
            QMessageBox.information(self.iface.mainWindow(), "Info", "No layer currently selected in TOC")


    def handle_layer_change(self, layer):
        self.clayer = self.canvas.currentLayer()
        if self.clayer:
            self.provider = self.clayer.dataProvider()


    def clone_plot(self, feature, dx, dy, heading, ix, iy):
        #Calculate the translation
        tx = ix*dx*math.cos(math.radians(heading)) - iy*dy*math.sin(math.radians(heading))
        ty = ix*dx*math.sin(math.radians(heading)) + iy*dy*math.cos(math.radians(heading))

        caps = self.provider.capabilities()
        if caps & QgsVectorDataProvider.AddFeatures:
            feat = QgsFeature(feature)
            #feat.addAttribute(0,"hello")
            orig_geom = feat.geometry()
            new_geom = []
            poly = orig_geom.asPolygon()
            #import pdb
            #pdb.set_trace()
            for vertex in poly[0]:
                x_new = vertex[0] + tx
                y_new = vertex[1] + ty
                new_geom.append(QgsPoint(x_new, y_new))

            feat.setGeometry(QgsGeometry.fromPolygon([new_geom]))
            field_names = [field.name() for field in self.provider.fields()]
            if 'Row' in field_names:
                feat['Row'] = feat['Row'] + iy
            if 'Column' in field_names:
                feat['Column'] = feat['Column'] + ix
            if 'PlotID' in field_names:
                feat['PlotID'] = feat['Column']*1000 + feat['Row']
            (res, outFeats) = self.provider.addFeatures( [ feat ] )

    def createLayer(self):
        # create layer
        vl = QgsVectorLayer("Polygon", "temporary_plots", "memory")
        pr = vl.dataProvider()

        # add fields
        pr.addAttributes([QgsField("Experiment", QVariant.String),
                            QgsField("Row",  QVariant.Int),
                            QgsField("Column",  QVariant.Int),
                            QgsField("PlotID",  QVariant.Int)])
        vl.updateFields() # tell the vector layer to fetch changes from the provider

        # Add it to the map
        QgsMapLayerRegistry.instance().addMapLayer(vl)
