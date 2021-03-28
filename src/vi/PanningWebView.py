###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import QApplication, qApp, QWidget
from PyQt5.QtGui import *
from PyQt5 import QtCore

from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtCore import QEvent, Qt
import webbrowser
import time
import os
class WebEnginePage(QWebEnginePage):
    linkClicked = QtCore.pyqtSignal(QtCore.QUrl)
    def acceptNavigationRequest(self, url:QtCore.QUrl, nav_type, isMainFrame):
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            self.linkClicked.emit(url)
            return False
        elif nav_type == QWebEnginePage.NavigationTypeTyped:
            return True
        elif nav_type == QWebEnginePage.NavigationTypeReload:
            return False
        elif nav_type == QWebEnginePage.NavigationTypeRedirect:
            return False
        else:
            return False

    def javaScriptConsoleMessage(self, QWebEnginePage_JavaScriptConsoleMessageLevel, p_str, p_int, p_str_1):
        print(p_str)
        #print( "{0} {1} {2}".format(p_str,p_int,p_str_1))
        #return

class PanningWebView(QWidget):
    webViewResized = QtCore.pyqtSignal()
    DUMP_CURRENT_VIEW= False
    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.zoom = 1.0
        self.pressed = False
        self.scrolling = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.webview = QWebEngineView(None)
        profile = QWebEngineProfile(self.webview)
        self.setPage(WebEnginePage(profile, self.webview))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.page().settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
        self.scrollPos = QPointF(0.0,0.0)
        self.lastImage = None
        self.imgSize = QtCore.QSize()
        self.webview.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.webview.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)
        self.webview.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.webview.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.webview.setStyleSheet("background:transparent");
        self.webview.page().setBackgroundColor(QtCore.Qt.transparent)

        self.webview.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)
        self.webview.show()
        self.destroyed.connect(self.destroyView)
        self.setMouseTracking(True)

    def destroyView(self):
        print("PanningWebView destroyed")
        del self.webview

    def setContent(self, cnt, type):
        if self.DUMP_CURRENT_VIEW:
            path = os.path.join(os.path.expanduser("~"),"projects","spyglass","src","vi","ui","res","mapdata","curr_map_1.svg")
            with open(path,"wb") as file:
                file.write(cnt)
                file.close()
        self.webview.stop()
        self.webview.setContent(cnt, type)
        self.webview.resize(self.imgSize * 2)
        self.webview.setZoomFactor(self.zoom)
        #todo:usig signal loadFinished leads to fragmented svgs needs a propper way to start rendering
        QtCore.QTimer(self).singleShot(1000, self.renderToImage)

    def setImgSize(self,newsize:QtCore.QSize):
        self.imgSize = newsize
        rcNew = self.imgSize*self.zoom
        rcNew.setWidth(self.imgSize.width()*self.zoom+64)
        rcNew.setHeight(self.imgSize.height() * self.zoom + 64)
        self.webview.resize(rcNew)

    def setUrl(self, url):
        self.webview.setUrl(url)

    def page(self):
        return self.webview.page()

    def setPage(self, aPage):
        self.webview.setPage(aPage)

    def resizeEvent(self, event:QResizeEvent):
        self.webViewResized.emit()
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self.lastImage:
            painter = QPainter(self)
            painter.drawImage(-self.scrollPosition(), self.lastImage)

    def renderToImage(self):
        qApp.processEvents()
        size = self.webview.contentsRect()
        if size.isValid():
            img = QImage(size.width(), size.height(), QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            painter = QPainter(img)
            self.webview.render(painter)
            self.lastImage = img
            if self.DUMP_CURRENT_VIEW:
                path = os.path.join(os.path.expanduser("~"),"projects","spyglass","src","vi","ui","res","mapdata","curr_map.png")
                self.lastImage.save(path)
            self.update()

    def setZoomFactor(self, zoom):
        if zoom > 2:
            zoom = 2;
        if zoom < 0.5:
            zoom = 0.5;
        self.zoom = zoom
        if ( self.imgSize.isValid()):
            self.webview.resize(self.imgSize * 2)
            self.webview.setZoomFactor(zoom)
            self.renderToImage()
            self.webViewResized.emit()
            self.update()

    def zoomFactor(self):
        return self.zoom

    def scrollPosition(self) -> QPointF:
        return self.scrollPos

    def setScrollPosition(self, pos: QPoint):
        self.scrollPos = pos

        if self.scrollPos.x() > self.imgSize.width()*self.zoom-self.size().width():
            self.scrollPos.setX(self.imgSize.width()*self.zoom-self.size().width())
        if self.scrollPos.x() < 0:
            self.scrollPos.setX(0)

        if self.scrollPos.y() > self.imgSize.height()*self.zoom-self.size().height():
            self.scrollPos.setY(self.imgSize.height()*self.zoom-self.size().height())
        if self.scrollPos.y() < 0:
            self.scrollPos.setY(0)

        self.webViewResized.emit()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        if Qt.ControlModifier & event.modifiers():
            if event.angleDelta().y() > 0:
                self.setZoomFactor(self.zoomFactor() * 1.1)
            elif event.angleDelta().y() < 0:
                self.setZoomFactor(self.zoomFactor() * 0.9)

    def mousePressEvent(self, mouseEvent:QMouseEvent):
        if not self.pressed and not self.scrolling and mouseEvent.modifiers() == QtCore.Qt.NoModifier:
            if mouseEvent.buttons() == QtCore.Qt.LeftButton:
                self.pressed = True
                self.scrolling = False
                self.handIsClosed = False
                qApp.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                self.scrollMousePress = self.scrollPosition()
                self.positionMousePress = mouseEvent.pos()

    def mouseReleaseEvent(self, mouseEvent:QMouseEvent):
        if self.scrolling:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            self.positionMousePress = None
            qApp.restoreOverrideCursor()
            return

        if self.pressed:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            qApp.restoreOverrideCursor()
            return

    def hoveCheck(self,pos:QPoint)->bool:
        return False

    def doubleClicked(self,pos:QPoint)->bool:
        return False

    def mouseDoubleClickEvent(self,mouseEvent:QMouseEvent):
        self.doubleClicked(self.mapPosFromEvent(mouseEvent))

    def mapPosFromEvent(self,mouseEvent:QMouseEvent)->QPointF:
        return (mouseEvent.pos() + self.scrollPos) / self.zoom

    def mouseMoveEvent(self, mouseEvent:QMouseEvent):
        if self.scrolling:
            if not self.handIsClosed:
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                self.handIsClosed = True
            if (self.scrollMousePress != None):
                delta = mouseEvent.pos() - self.positionMousePress
                self.setScrollPosition(self.scrollMousePress - delta)
            return
        if self.pressed:
            self.pressed = False
            self.scrolling = True
            return
        if self.hoveCheck(self.mapPosFromEvent(mouseEvent)):
            qApp.setOverrideCursor(QtCore.Qt.PointingHandCursor)
        else:
            qApp.setOverrideCursor(QtCore.Qt.ArrowCursor)
        return

