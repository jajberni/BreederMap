# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BreederMapDockWidget
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

import os

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QTranslator,
    pyqtSignal,
    Qt,
    QVariant,
    QSettings,
    QUrl
)
from qgis.PyQt.QtGui import QColor, QDesktopServices
from qgis._core import QgsLineString
from qgis.core import (
    Qgis,
    QgsWkbTypes,
    QgsGeometry,
    QgsPointXY,
    QgsPoint,
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

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'breeder_map_dockwidget_base.ui'))


class BreederMapDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()
    plugin = None

    def __init__(self, _plugin, parent=None):
        """Constructor."""
        super(BreederMapDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.plugin = _plugin
        self.canvas = self.plugin.iface.mapCanvas()
        self.started = False
        self.btnStart.setCheckable(True)
        self.mt = MapTool(self)

        self.plugin_dir = os.path.dirname(__file__)

        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, "i18n", "{}.qm".format(locale))
        self.info(localePath)

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)
            QCoreApplication.installTranslator(self.translator)

        for widget in [
            self.btnStart,
            self.btnSave,
            self.lbColGap,
            self.lbRowGap,
            self.lbColumns,
            self.lbRows,
            self.btnHelp,
            self.btnAbout,
            self.cbReverseColumns,
            self.cbReverseRows,
            self.cbIndividualNode
        ]:
            widget.setText(self.tr(widget.text()))

        self.widget2Enable = [
            self.rowCount,
            self.columnCount,
            self.columnGap,
            self.rowGap,
            self.cbReverseColumns,
            self.cbReverseRows,
            self.cbIndividualNode
        ]

        self.alert.setText("")

    def tr(self, message):
        return QCoreApplication.translate("QPhenoGrid", message)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def info(self, message, d=1):
        self.plugin.iface.messageBar().pushMessage(
            "Breeder Map", self.tr(message), level=Qgis.Info, duration=d
        )

    def start(self):
        """Start the process : activates tools, builds rubber bands..."""
        self.info("Start")

        for w in self.widget2Enable:
            w.setEnabled(True)

        self.canvas.setMapTool(self.mt)

        self.mt.newRubber()

        return True

    def cancel(self):
        self.mt.hide()
        self.canvas.unsetMapTool(self.mt)

        for w in self.widget2Enable:
            w.setEnabled(False)

    def on_btnStart_toggled(self, checked):
        self.started = checked
        if checked:
            if self.start():
                self.btnStart.setText("Cancel")
            else:
                self.btnStart.toggle()
        else:
            self.btnStart.setText("Start")
            self.cancel()

    def on_rowCount_valueChanged(self, v):
        self.mt.updateRubberGeom()

    def on_columnCount_valueChanged(self, v):
        self.mt.updateRubberGeom()

    def on_cbReverseColumns_toggled(self, v):
        self.mt.updateRubberGeom()

    def on_cbReverseRows_toggled(self, v):
        self.mt.updateRubberGeom()

    def clip_polygons(self, polygonsLayer, rowBuffer, columnBuffer, iRowLayer, iColLayer):
        outgoingFeatureList = []
        finalFeatureList = []
        row_number = -1

        fields = polygonsLayer.fields()
        for f in polygonsLayer.getFeatures():

            localFeature = f.geometry()
            for compFeature in rowBuffer.asGeometryCollection():
                if localFeature.intersects(compFeature):
                    localFeature = localFeature.difference(compFeature)

            if localFeature.isMultipart():
                #self.info("Polys 1: {}".format(localFeature.asWkt()))
                polys = localFeature.asGeometryCollection()
                for part in polys:
                    outgoingFeature = QgsFeature()
                    outgoingFeature.setFields(fields)
                    outgoingFeature.setGeometry(part)
                    outgoingFeatureList.append(outgoingFeature)
            else:
                outgoingFeature = QgsFeature()
                outgoingFeature.setFields(fields)
                outgoingFeature.setGeometry(localFeature)
                outgoingFeatureList.append(outgoingFeature)
        for f in outgoingFeatureList:
            localFeature = f.geometry()
            for row_line in iRowLayer.getFeatures():
                if localFeature.intersects(row_line.geometry()):
                    row_number = row_line['row']
                    break
            for compFeature in columnBuffer.asGeometryCollection():
                if localFeature.intersects(compFeature):
                    localFeature = localFeature.difference(compFeature)
            if localFeature.isMultipart():
                polys = localFeature.asGeometryCollection()
                for part in polys:
                    outgoingFeature = QgsFeature()
                    outgoingFeature.setFields(fields)
                    outgoingFeature['row'] = row_number
                    outgoingFeature.setGeometry(part)
                    finalFeatureList.append(outgoingFeature)
            else:
                outgoingFeature = QgsFeature()
                outgoingFeature.setFields(fields)
                outgoingFeature['row'] = row_number
                outgoingFeature.setGeometry(localFeature)
                finalFeatureList.append(outgoingFeature)
        for f in finalFeatureList:
            localFeature = f.geometry()
            for col_line in iColLayer.getFeatures():
                if localFeature.intersects(col_line.geometry()):
                    col_number = col_line['column']
                    f['column'] = col_number
                    f['num'] = col_number*1000 + f['row']
                    break
        return finalFeatureList

    def on_btnSave_released(self):
        layer = QgsVectorLayer(
            "MultiLineString?crs={}".format(QgsProject.instance().crs().authid()),
            "Lines",
            "memory",
        )

        #QgsProject.instance().addMapLayer(layer)
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("num", QVariant.Int)])
        layer.dataProvider().addAttributes([QgsField("row", QVariant.Int)])
        layer.dataProvider().addAttributes([QgsField("column", QVariant.Int)])
        layer.updateFields()
        feats = []

        columnGap = self.columnGap.value()
        rowGap = self.rowGap.value()
        fid = 0
        lin = QgsGeometry.fromMultiPolylineXY(self.mt.rowLines)
        feature = QgsFeature(fid)
        feature.setAttributes([str(fid)])
        feature.setGeometry(lin)
        feats.append(feature)
        g = feature.geometry()
        rowBuffer = g.buffer(rowGap / 2, 5)

        fid = 1
        lin = QgsGeometry.fromMultiPolylineXY(self.mt.columnLines)
        feature = QgsFeature(fid)
        feature.setAttributes([str(fid)])
        feature.setGeometry(lin)
        feats.append(feature)
        columnBuffer = lin.buffer(columnGap / 2, 5)

        layer.dataProvider().addFeatures(feats)

        # layer.loadNamedStyle(self.plugin_dir + "/lines.qml")
        layer.commitChanges()

        # Generate index lines

        if self.cbReverseRows.isChecked():
            leftEdge = (
                QgsGeometry.fromPolylineXY([self.mt.pA, self.mt.pD])
                    .densifyByCount(self.rowCount.value() * 2 - 1)
                    .asPolyline()
            )
            rightEdge = (
                QgsGeometry.fromPolylineXY([self.mt.pB, self.mt.pC])
                    .densifyByCount(self.rowCount.value() * 2 - 1)
                    .asPolyline()
            )
        else:
            leftEdge = (
                QgsGeometry.fromPolylineXY([self.mt.pD, self.mt.pA])
                    .densifyByCount(self.rowCount.value() * 2 - 1)
                    .asPolyline()
            )
            rightEdge = (
                QgsGeometry.fromPolylineXY([self.mt.pC, self.mt.pB])
                    .densifyByCount(self.rowCount.value() * 2 - 1)
                    .asPolyline()
            )

        # Plot edges lines
        polyline_rows = list(zip(leftEdge[1::2], rightEdge[1::2]))
        if self.cbReverseColumns.isChecked():
            backSide = (
                QgsGeometry.fromPolylineXY([self.mt.pB, self.mt.pA])
                    .densifyByCount(self.columnCount.value() * 2 - 1)
                    .asPolyline()
            )
            frontSide = (
                QgsGeometry.fromPolylineXY([self.mt.pC, self.mt.pD])
                    .densifyByCount(self.columnCount.value() * 2 - 1)
                    .asPolyline()
            )
        else:
            backSide = (
                QgsGeometry.fromPolylineXY([self.mt.pA, self.mt.pB])
                    .densifyByCount(self.columnCount.value() * 2 - 1)
                    .asPolyline()
            )
            frontSide = (
                QgsGeometry.fromPolylineXY([self.mt.pD, self.mt.pC])
                    .densifyByCount(self.columnCount.value() * 2 - 1)
                    .asPolyline()
            )
        polyline_columns = list(zip(backSide[1::2], frontSide[1::2]))

        # Generate Row lines
        iRowLayer = QgsVectorLayer(
            "MultiLineString?crs={}".format(QgsProject.instance().crs().authid()),
            "Index Rows",
            "memory",
        )

        #QgsProject.instance().addMapLayer(iRowLayer)
        iRowLayer.startEditing()
        iRowLayer.dataProvider().addAttributes([QgsField("row", QVariant.Int)])
        iRowLayer.updateFields()
        feats = []

        row = 1
        lines_rows = QgsGeometry.fromMultiPolylineXY(polyline_rows)
        for p in lines_rows.asGeometryCollection():
            feature = QgsFeature(fid)
            feature.setAttributes([row])
            feature.setGeometry(p)
            feats.append(feature)
            row += 1

        iRowLayer.dataProvider().addFeatures(feats)
        iRowLayer.commitChanges()

        # Generate Column lines
        iColLayer = QgsVectorLayer(
            "MultiLineString?crs={}".format(QgsProject.instance().crs().authid()),
            "Index Columns",
            "memory",
        )

        #QgsProject.instance().addMapLayer(iColLayer)
        iColLayer.startEditing()
        iColLayer.dataProvider().addAttributes([QgsField("column", QVariant.Int)])
        iColLayer.updateFields()
        feats = []

        column = 1
        lines_columns = QgsGeometry.fromMultiPolylineXY(polyline_columns)
        for p in lines_columns.asGeometryCollection():
            feature = QgsFeature(fid)
            feature.setAttributes([column])
            feature.setGeometry(p)
            feats.append(feature)
            column += 1
        iColLayer.dataProvider().addFeatures(feats)
        iColLayer.commitChanges()


        pLayer = QgsVectorLayer(
            "Polygon?crs={}".format(QgsProject.instance().crs().authid()),
            "Polygons",
            "memory",
        )
        #QgsProject.instance().addMapLayer(pLayer)
        pLayer.dataProvider().addAttributes([QgsField("num", QVariant.Int)])
        pLayer.dataProvider().addAttributes([QgsField("row", QVariant.Int)])
        pLayer.dataProvider().addAttributes([QgsField("column", QVariant.Int)])
        pLayer.startEditing()
        pLayer.updateFields()
        feats = []
        feature = QgsFeature(0)
        feature.setAttributes([str(fid), 0, 0])

        line_list = [f.geometry() for f in layer.getFeatures()]
        lines = QgsGeometry.unaryUnion(line_list)
        polygons = QgsGeometry.polygonize([lines])
        fid = 0
        for p in polygons.asGeometryCollection():
            feature = QgsFeature(fid)
            feature.setAttributes([str(fid), 0, 0])
            feature.setGeometry(p)
            feats.append(feature)
            fid += 1

        pLayer.dataProvider().addFeatures(feats)
        pLayer.commitChanges()

        pcLayer = QgsVectorLayer(
            "Polygon?crs={}".format(QgsProject.instance().crs().authid()),
            "Plots",
            "memory",
        )
        QgsProject.instance().addMapLayer(pcLayer)
        pcLayer.dataProvider().addAttributes(pLayer.fields())
        pcLayer.startEditing()
        pcLayer.updateFields()
        pcLayer.dataProvider().addFeatures(self.clip_polygons(pLayer, rowBuffer, columnBuffer, iRowLayer, iColLayer))
        pcLayer.commitChanges()

        ptLayer = QgsVectorLayer(
            "Point?crs={}".format(QgsProject.instance().crs().authid()),
            "Points",
            "memory"
        )
        QgsProject.instance().addMapLayer(ptLayer)
        ptLayer.startEditing()
        ptLayer.dataProvider().addAttributes([QgsField("num", QVariant.Int)])
        ptLayer.updateFields()
        feats = []
        fid = 0
        lin = QgsGeometry.fromMultiPolylineXY(self.mt.rowLines)

        for line in lin.asGeometryCollection():
            poly = line.densifyByCount(self.rowCount.value() * 2).asPolyline()
            for part in poly:
                feature = QgsFeature(fid)
                feature.setAttributes([str(fid)])
                feature.setGeometry(QgsPoint(part))
                feats.append(feature)
                fid += 1
        # ptLayer.dataProvider().addFeatures(sorted(feats, key=lambda f: f['num']))
        ptLayer.dataProvider().addFeatures(feats)
        ptLayer.commitChanges()

    def on_btnAbout_released(self):
        from .about_dialog import AboutDialog
        AboutDialog(self.plugin.iface.mainWindow()).exec_()

    def on_btnHelp_released(self):
        """Display application help to the user."""
        help_file = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'help', 'index.html')
        self.info("Show help: " + help_file)
        QDesktopServices.openUrl(QUrl.fromLocalFile(help_file))


class MapTool(QgsMapTool):
    MODE_NONE = 0
    MODE_PAN = 1
    MODE_ROTATE = 2
    MODE_SCALE = 3
    MODE_SCALE_X = 4
    MODE_SCALE_Y = 5
    MODE_PAN_RESULT = 6
    MODE_NODE = 7
    NODE_NAMES = ['A', 'B', 'C', 'D']

    def __init__(self, widget):
        QgsMapTool.__init__(self, widget.canvas)
        self.widget = widget
        self.canvas = widget.canvas
        self.mode = self.MODE_NONE
        self.selected_node = None

        # clicked point
        self.p0 = None

        # centre rectangle
        self.pX = None

        # rectangle vertices (handles)
        self.pA = None  # hg
        self.pB = None  # hd
        self.pC = None  # bd
        self.pD = None  # bg
        self.zoneWidth = None
        self.zoneDepth = None

        # eye (rotation)
        self.pY = None

        # rectangle
        self.rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setStrokeColor(Qt.blue)
        self.rb.setWidth(3)

        self.rbFoc = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rbFoc.setStrokeColor(Qt.blue)
        self.rbFoc.setWidth(1)

        # SCALE nodes
        self.rbPA = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPA.setColor(Qt.red)
        self.rbPA.setWidth(8)
        self.rbPB = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPB.setColor(Qt.red)
        self.rbPB.setWidth(8)
        self.rbPC = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPC.setColor(Qt.red)
        self.rbPC.setWidth(8)
        self.rbPD = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPD.setColor(QColor(255, 50, 150, 255))
        self.rbPD.setWidth(8)
        # scale Y node
        self.rbPH = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPH.setColor(Qt.red)
        self.rbPH.setWidth(8)
        # scale X node
        self.rbPL = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPL.setColor(Qt.red)
        self.rbPL.setWidth(8)

        # final pan
        self.rbPan = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPan.setColor(QColor(0, 200, 50, 255))
        self.rbPan.setWidth(8)

        # ROTATE node
        self.rbPY = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rbPY.setColor(Qt.blue)
        self.rbPY.setWidth(6)
        self.rotation = 0.0

        # cutting lines
        self.rbLines = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rbLines.setColor(QColor(40, 180, 30, 255))
        self.rbLines.setWidth(1.5)

        # plots
        self.rbPlots = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rbPlots.setStrokeColor(QColor(200, 120, 70, 150))
        self.rbPlots.setWidth(0.8)

        self.rubbers = [
            self.rb,
            self.rbPA,
            self.rbPB,
            self.rbPC,
            self.rbPD,
            self.rbPY,
            self.rbPH,
            self.rbPL,
            self.rbPan,
            self.rbLines,
            self.rbPlots,
            self.rbFoc,
        ]

        self.rowLines = None
        self.columnLines = None
        self.allLines = None

    def hide(self):
        for rb in self.rubbers:
            rb.reset()

    def updateRubberGeom(self):
        if self.pA is None:
            return

        self.zoneWidth = self.pA.distance(self.pB)
        self.zoneDepth = self.pA.distance(self.pD)
        self.pM = QgsPointXY(
            (self.pC.x() + self.pD.x()) / 2, (self.pC.y() + self.pD.y()) / 2
        )
        self.d0 = self.pM.distance(self.pY)
        # self.widget.updateZ(self.pY)

        self.rb.setToGeometry(
            QgsGeometry.fromPolygonXY([[self.pD, self.pA, self.pB, self.pC, self.pD]])
        )
        self.rbFoc.setToGeometry(
            QgsGeometry.fromPolylineXY([self.pD, self.pY, self.pC])
        )

        for p, rb in [
            [self.pA, self.rbPA],
            [self.pB, self.rbPB],
            [self.pC, self.rbPC],
            [self.pD, self.rbPD],
            [self.pY, self.rbPY],
            [self.pH, self.rbPH],
            [self.pL, self.rbPL],
        ]:
            rb.setToGeometry(QgsGeometry.fromPointXY(p))

        leftEdge = (
            QgsGeometry.fromPolylineXY([self.pA, self.pD])
                .densifyByCount(self.widget.rowCount.value() - 1)
                .asPolyline()
        )
        rightEdge = (
            QgsGeometry.fromPolylineXY([self.pB, self.pC])
                .densifyByCount(self.widget.rowCount.value() - 1)
                .asPolyline()
        )

        # Plot edges lines
        polyline = list(zip(leftEdge, rightEdge))

        backSide = (
            QgsGeometry.fromPolylineXY([self.pA, self.pB])
                .densifyByCount(self.widget.columnCount.value() - 1)
                .asPolyline()
        )
        frontSide = (
            QgsGeometry.fromPolylineXY([self.pD, self.pC])
                .densifyByCount(self.widget.columnCount.value() - 1)
                .asPolyline()
        )
        polylineX = list(zip(frontSide[:], backSide[:]))

        self.finalWidth = self.zoneWidth

        self.rowLines = polyline
        self.columnLines = polylineX
        self.allLines = polyline + polylineX
        self.rbLines.setToGeometry(
            QgsGeometry.fromMultiPolylineXY(
                polylineX
                + polyline
                + polyline[:: max(1, 1 + len(polyline))]
            )
        )
        if self.widget.cbReverseRows.isChecked():
            if self.widget.cbReverseColumns.isChecked():
                self.rbPC.setColor(Qt.red)
                self.rbPD.setColor(Qt.red)
                self.rbPA.setColor(Qt.red)
                self.rbPB.setColor(QColor(0, 200, 150, 255))
            else:
                self.rbPC.setColor(Qt.red)
                self.rbPD.setColor(Qt.red)
                self.rbPB.setColor(Qt.red)
                self.rbPA.setColor(QColor(0, 200, 150, 255))
        else:
            if self.widget.cbReverseColumns.isChecked():
                self.rbPA.setColor(Qt.red)
                self.rbPB.setColor(Qt.red)
                self.rbPD.setColor(Qt.red)
                self.rbPC.setColor(QColor(0, 200, 150, 255))
            else:
                self.rbPA.setColor(Qt.red)
                self.rbPB.setColor(Qt.red)
                self.rbPC.setColor(Qt.red)
                self.rbPD.setColor(QColor(0, 200, 150, 255))

        self.widget.alert.setText("Total plots: {}".format(self.widget.columnCount.value()*self.widget.rowCount.value()))

    def getLines(self):
        return QgsGeometry.fromMultiPolylineXY(self.rowLines)

    def getSampleLines(self):
        return (
                [self.rowLines[0], self.rowLines[1]]
                + self.rowLines[2:-1][
                  :: max(1, 1 + int((len(self.rowLines) - 3) / 9))
                  ]
                + [self.rowLines[-1]]
        )

    def newRubber(self):
        if self.pX is not None:
            self.updateRubberGeom()
            return

        # default parameters
        h = 2 * self.widget.canvas.extent().height() / 3 / 20

        # first bbox, according to current view
        h = self.canvas.extent().height() / 6
        c = self.canvas.extent().center()
        rubberExtent = QgsRectangle(
            QgsPointXY(c.x() - h, c.y() - h), QgsPointXY(c.x() + h, c.y() + h)
        )
        self.rotation = 0.0
        width = rubberExtent.xMaximum() - rubberExtent.xMinimum()
        height = rubberExtent.yMaximum() - rubberExtent.yMinimum()

        # centre rectangle
        self.pX = QgsPointXY(
            rubberExtent.xMinimum() + width / 2, rubberExtent.yMinimum() + height / 2
        )

        self.pA = QgsPointXY(rubberExtent.xMinimum(), rubberExtent.yMaximum())
        self.pB = QgsPointXY(rubberExtent.xMaximum(), rubberExtent.yMaximum())
        self.pC = QgsPointXY(rubberExtent.xMaximum(), rubberExtent.yMinimum())
        self.pD = QgsPointXY(rubberExtent.xMinimum(), rubberExtent.yMinimum())

        # handles H / L
        self.pH = QgsPointXY(
            (self.pA.x() + self.pB.x()) / 2, (self.pA.y() + self.pB.y()) / 2
        )
        self.pL = QgsPointXY(
            (self.pB.x() + self.pC.x()) / 2, (self.pB.y() + self.pC.y()) / 2
        )

        # eye (rotation)
        self.pY = QgsPointXY(self.pX.x(), self.pX.y() - 2 * height / 3)

        self.pM = QgsPointXY(
            (self.pC.x() + self.pD.x()) / 2, (self.pC.y() + self.pD.y()) / 2
        )

        self.rotation_init = self.rotation
        self.pA_init = QgsPointXY(self.pA)
        self.pB_init = QgsPointXY(self.pB)
        self.pC_init = QgsPointXY(self.pC)
        self.pD_init = QgsPointXY(self.pD)
        self.pX_init = QgsPointXY(self.pX)
        self.pY_init = QgsPointXY(self.pY)
        self.pH_init = QgsPointXY(self.pH)
        self.pL_init = QgsPointXY(self.pL)

        self.updateRubberGeom()

    def canvasPressEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        self.p0 = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

        distPA = self.p0.distance(self.pA) / self.canvas.mapUnitsPerPixel()
        distPB = self.p0.distance(self.pB) / self.canvas.mapUnitsPerPixel()
        distPC = self.p0.distance(self.pC) / self.canvas.mapUnitsPerPixel()
        distPD = self.p0.distance(self.pD) / self.canvas.mapUnitsPerPixel()
        distPY = self.p0.distance(self.pY) / self.canvas.mapUnitsPerPixel()
        distPH = self.p0.distance(self.pH) / self.canvas.mapUnitsPerPixel()
        distPL = self.p0.distance(self.pL) / self.canvas.mapUnitsPerPixel()

        edit_individual_node = self.widget.cbIndividualNode.isChecked()

        if distPA < 6 or distPB < 6 or distPC < 6 or distPD < 6:
            if edit_individual_node:
                self.mode = self.MODE_NODE
                val, idx = min((val, idx) for (idx, val) in enumerate([distPA, distPB, distPC, distPD]))
                self.selected_node = self.NODE_NAMES[idx]
            else:
                self.mode = self.MODE_SCALE
            return

        if distPH < 6:
            self.mode = self.MODE_SCALE_Y
            return

        if distPL < 6:
            self.mode = self.MODE_SCALE_X
            return

        if distPY < 6:
            self.mode = self.MODE_ROTATE
            return

        if self.rb.asGeometry().contains(self.p0):
            self.mode = self.MODE_PAN
            return

    def canvasMoveEvent(self, event):
        if self.mode == self.MODE_NONE:
            return

        x = event.pos().x()
        y = event.pos().y()
        pt = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
        dx = pt.x() - self.p0.x()
        dy = pt.y() - self.p0.y()

        # node name
        if self.mode == self.MODE_NODE:
            if self.selected_node == 'A':
                self.pA.setX(self.pA_init.x() + dx)
                self.pA.setY(self.pA_init.y() + dy)
            elif self.selected_node == 'B':
                self.pB.setX(self.pB_init.x() + dx)
                self.pB.setY(self.pB_init.y() + dy)
            elif self.selected_node == 'C':
                self.pC.setX(self.pC_init.x() + dx)
                self.pC.setY(self.pC_init.y() + dy)
            elif self.selected_node == 'D':
                self.pD.setX(self.pD_init.x() + dx)
                self.pD.setY(self.pD_init.y() + dy)

        # pan mode
        if self.mode == self.MODE_PAN:
            for p, p_ini in [
                [self.pA, self.pA_init],
                [self.pB, self.pB_init],
                [self.pC, self.pC_init],
                [self.pD, self.pD_init],
                [self.pX, self.pX_init],
                [self.pY, self.pY_init],
                [self.pH, self.pH_init],
                [self.pL, self.pL_init],
            ]:
                p.setX(p_ini.x() + dx)
                p.setY(p_ini.y() + dy)

        # horizontal + vertical sizing
        if self.mode == self.MODE_SCALE:
            d_old = self.pA_init.distance(self.pX_init)
            d_new = pt.distance(self.pX_init)
            dd = d_new / d_old

            for p, p_ini in [
                [self.pA, self.pA_init],
                [self.pB, self.pB_init],
                [self.pC, self.pC_init],
                [self.pD, self.pD_init],
                [self.pY, self.pY_init],
                [self.pH, self.pH_init],
                [self.pL, self.pL_init],
            ]:
                dx = dd * (p_ini.x() - self.pX.x())
                dy = dd * (p_ini.y() - self.pX.y())
                p.setX(self.pX.x() + dx)
                p.setY(self.pX.y() + dy)

        # horizontal sizing
        if self.mode == self.MODE_SCALE_X:
            d_old = self.pL_init.distance(self.pX_init)
            d_new = pt.distance(self.pX_init)
            dd = d_new / d_old
            if dd < 0.001:
                dd = 0.001

            dx = dd * (self.pL_init.x() - self.pX.x())
            dy = dd * (self.pL_init.y() - self.pX.y())
            self.pL.setX(self.pX.x() + dx)
            self.pL.setY(self.pX.y() + dy)

            centre = self.pH
            for p, p_ini in [[self.pA, self.pA_init], [self.pB, self.pB_init]]:
                dx = dd * (p_ini.x() - centre.x())
                dy = dd * (p_ini.y() - centre.y())
                p.setX(centre.x() + dx)
                p.setY(centre.y() + dy)

            centre = self.pM
            for p, p_ini in [[self.pC, self.pC_init], [self.pD, self.pD_init]]:
                dx = dd * (p_ini.x() - centre.x())
                dy = dd * (p_ini.y() - centre.y())
                p.setX(centre.x() + dx)
                p.setY(centre.y() + dy)

        # vertical sizing
        if self.mode == self.MODE_SCALE_Y:
            d_old = self.pH_init.distance(self.pX_init)
            d_new = pt.distance(self.pX_init)
            dd = d_new / d_old
            if dd < 0.001:
                dd = 0.001

            dx = dd * (self.pH_init.x() - self.pX.x())
            dy = dd * (self.pH_init.y() - self.pX.y())
            self.pH.setX(self.pX.x() + dx)
            self.pH.setY(self.pX.y() + dy)

            centre = self.pL
            for p, p_ini in [[self.pB, self.pB_init], [self.pC, self.pC_init]]:
                dx = dd * (p_ini.x() - centre.x())
                dy = dd * (p_ini.y() - centre.y())
                p.setX(centre.x() + dx)
                p.setY(centre.y() + dy)

            centre = QgsPointXY(
                (self.pA.x() + self.pD.x()) / 2, (self.pA.y() + self.pD.y()) / 2
            )
            for p, p_ini in [[self.pA, self.pA_init], [self.pD, self.pD_init]]:
                dx = dd * (p_ini.x() - centre.x())
                dy = dd * (p_ini.y() - centre.y())
                p.setX(centre.x() + dx)
                p.setY(centre.y() + dy)

        if self.mode == self.MODE_ROTATE:
            self.pY.setX(self.pY_init.x() + dx)
            self.pY.setY(self.pY_init.y() + dy)

            azimuth = self.pX.azimuth(pt)
            theta = azimuth - self.rotation_init + 180
            self.rotation = self.rotation_init + theta

            for a, i in [
                [self.pA, self.pA_init],
                [self.pB, self.pB_init],
                [self.pC, self.pC_init],
                [self.pD, self.pD_init],
                [self.pH, self.pH_init],
                [self.pL, self.pL_init],
            ]:
                A = QgsGeometry.fromPointXY(i)
                A.rotate(theta, self.pX)
                a.setX(A.asPoint().x())
                a.setY(A.asPoint().y())

        self.updateRubberGeom()

    def canvasReleaseEvent(self, event):
        self.pA_init = QgsPointXY(self.pA)
        self.pB_init = QgsPointXY(self.pB)
        self.pC_init = QgsPointXY(self.pC)
        self.pD_init = QgsPointXY(self.pD)
        self.pX_init = QgsPointXY(self.pX)
        self.pY_init = QgsPointXY(self.pY)
        self.pH_init = QgsPointXY(self.pH)
        self.pL_init = QgsPointXY(self.pL)
        self.rotation_init = self.rotation

        self.mode = self.MODE_NONE

    def activate(self):
        pass

    def deactivate(self):
        self.hide()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True