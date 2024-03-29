# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BreederMap
                                 A QGIS plugin
 Creates a field layout for a typical row-column breeder's trial
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-05-14
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Jose A. _Jimenez-Berni
        email                : berni@ias.csic.es
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
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
# Initialize Qt resources from file resources.py
from .resources import *

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QTranslator,
    pyqtSignal,
    Qt,
    QVariant,
    QSettings,
)
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    Qgis,
    QgsWkbTypes,
    QgsGeometry,
    QgsPointXY,
    QgsMessageLog,
    QgsProject,
    QgsMapLayer,
    QgsVectorLayer,
    QgsField,
)
from qgis.core import (
    QgsFeature,
    QgsRaster,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsRectangle,
)
from qgis.gui import QgsRubberBand, QgsMapTool
import math
import sys
import traceback

MESSAGE_CATEGORY = "Messages"


def enable_remote_debugging():
    try:
        import ptvsd

        if ptvsd.is_attached():
            QgsMessageLog.logMessage(
                "Remote Debug for Visual Studio is already active",
                MESSAGE_CATEGORY,
                Qgis.Info,
            )
            return
        ptvsd.enable_attach(address=("localhost", 5678))
        QgsMessageLog.logMessage(
            "BreederMap attached remote Debug for Visual Studio on port 5678",
            MESSAGE_CATEGORY,
            Qgis.Info,
        )
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        format_exception = traceback.format_exception(
            exc_type, exc_value, exc_traceback
        )
        QgsMessageLog.logMessage(
            repr(format_exception[0]), MESSAGE_CATEGORY, Qgis.Critical
        )
        QgsMessageLog.logMessage(
            repr(format_exception[1]), MESSAGE_CATEGORY, Qgis.Critical
        )
        QgsMessageLog.logMessage(
            repr(format_exception[2]), MESSAGE_CATEGORY, Qgis.Critical
        )


# Import the code for the DockWidget
from .breeder_map_dockwidget import BreederMapDockWidget
from .breeder_map_about_dialog import AboutDialog
import os.path


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
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Breeder Map')

        #print "** INITIALIZING BreederMap"

        self.pluginIsActive = False
        self.dockwidget = None

        self.widget2Enable = [

        ]

        self.started = False

        self.about_action = None



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

        icon_path = ':/plugins/breeder_map/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create experiment grid'),
            callback=self.run,
            parent=self.iface.mainWindow())

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING BreederMap"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD BreederMap"

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Breeder Map'),
                action)
            self.iface.removeToolBarIcon(action)

    # --------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING BreederMap"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = BreederMapDockWidget(self)

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

    def about(self):
        AboutDialog(self.iface.mainWindow()).exec_()


