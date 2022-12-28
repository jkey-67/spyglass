# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'JumpbridgeChooser.ui'
##
## Created by: Qt User Interface Compiler version 6.4.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QProgressBar, QSizePolicy,
    QSpacerItem, QTextBrowser, QToolButton, QVBoxLayout,
    QWidget)
import resource_rc

class Ui_JumpbridgeChooser(object):
    def setupUi(self, JumpbridgeChooser):
        if not JumpbridgeChooser.objectName():
            JumpbridgeChooser.setObjectName(u"JumpbridgeChooser")
        JumpbridgeChooser.resize(595, 638)
        self.gridLayout = QGridLayout(JumpbridgeChooser)
        self.gridLayout.setSpacing(3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(2, 3, 3, 3)
        self.widget3 = QWidget(JumpbridgeChooser)
        self.widget3.setObjectName(u"widget3")
        self.horizontalLayout_4 = QHBoxLayout(self.widget3)
        self.horizontalLayout_4.setSpacing(3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(3, 3, 3, 3)
        self.cancelButton = QToolButton(self.widget3)
        self.cancelButton.setObjectName(u"cancelButton")
        icon = QIcon()
        icon.addFile(u":/Icons/res/apply.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.cancelButton.setIcon(icon)
        self.cancelButton.setIconSize(QSize(24, 24))

        self.horizontalLayout_4.addWidget(self.cancelButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.generateJumpBridgeButton = QToolButton(self.widget3)
        self.generateJumpBridgeButton.setObjectName(u"generateJumpBridgeButton")
        icon1 = QIcon()
        icon1.addFile(u":/Icons/res/arrows-rotate.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.generateJumpBridgeButton.setIcon(icon1)
        self.generateJumpBridgeButton.setIconSize(QSize(24, 24))

        self.horizontalLayout_4.addWidget(self.generateJumpBridgeButton)


        self.gridLayout.addWidget(self.widget3, 2, 0, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(3, 3, 3, 3)
        self.widget2 = QWidget(JumpbridgeChooser)
        self.widget2.setObjectName(u"widget2")
        self.gridLayout_4 = QGridLayout(self.widget2)
        self.gridLayout_4.setSpacing(3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(3, 3, 3, 3)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(3, 3, 3, 3)
        self.urlField = QLineEdit(self.widget2)
        self.urlField.setObjectName(u"urlField")

        self.horizontalLayout.addWidget(self.urlField)

        self.fileChooser = QToolButton(self.widget2)
        self.fileChooser.setObjectName(u"fileChooser")
        icon2 = QIcon()
        icon2.addFile(u":/Icons/res/load.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.fileChooser.setIcon(icon2)
        self.fileChooser.setIconSize(QSize(24, 24))

        self.horizontalLayout.addWidget(self.fileChooser)

        self.saveButton = QToolButton(self.widget2)
        self.saveButton.setObjectName(u"saveButton")
        icon3 = QIcon()
        icon3.addFile(u":/Icons/res/save.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.saveButton.setIcon(icon3)
        self.saveButton.setIconSize(QSize(24, 24))

        self.horizontalLayout.addWidget(self.saveButton)

        self.horizontalLayout.setStretch(0, 5)

        self.gridLayout_4.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.formatInfoField = QTextBrowser(self.widget2)
        self.formatInfoField.setObjectName(u"formatInfoField")
        self.formatInfoField.setOverwriteMode(False)

        self.gridLayout_4.addWidget(self.formatInfoField, 2, 0, 1, 1)

        self.generateJumpBridgeProgress = QProgressBar(self.widget2)
        self.generateJumpBridgeProgress.setObjectName(u"generateJumpBridgeProgress")
        self.generateJumpBridgeProgress.setValue(24)

        self.gridLayout_4.addWidget(self.generateJumpBridgeProgress, 3, 0, 1, 1)

        self.label = QLabel(self.widget2)
        self.label.setObjectName(u"label")

        self.gridLayout_4.addWidget(self.label, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.widget2)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        QWidget.setTabOrder(self.urlField, self.fileChooser)
        QWidget.setTabOrder(self.fileChooser, self.cancelButton)
        QWidget.setTabOrder(self.cancelButton, self.generateJumpBridgeButton)

        self.retranslateUi(JumpbridgeChooser)

        QMetaObject.connectSlotsByName(JumpbridgeChooser)
    # setupUi

    def retranslateUi(self, JumpbridgeChooser):
        JumpbridgeChooser.setWindowTitle(QCoreApplication.translate("JumpbridgeChooser", u"Jumpbridge Data", None))
#if QT_CONFIG(tooltip)
        self.cancelButton.setToolTip(QCoreApplication.translate("JumpbridgeChooser", u"Apply changes", None))
#endif // QT_CONFIG(tooltip)
        self.cancelButton.setText(QCoreApplication.translate("JumpbridgeChooser", u"Apply", None))
#if QT_CONFIG(tooltip)
        self.generateJumpBridgeButton.setToolTip(QCoreApplication.translate("JumpbridgeChooser", u"Generate the list uf jumpbridges online", None))
#endif // QT_CONFIG(tooltip)
        self.generateJumpBridgeButton.setText(QCoreApplication.translate("JumpbridgeChooser", u"Generate ", None))
#if QT_CONFIG(tooltip)
        self.fileChooser.setToolTip(QCoreApplication.translate("JumpbridgeChooser", u"Set the import file name or define the import URL", None))
#endif // QT_CONFIG(tooltip)
        self.fileChooser.setText(QCoreApplication.translate("JumpbridgeChooser", u"Import File Name / URL", None))
#if QT_CONFIG(tooltip)
        self.saveButton.setToolTip(QCoreApplication.translate("JumpbridgeChooser", u"Export the current Jump Bridge set to a text file", None))
#endif // QT_CONFIG(tooltip)
        self.saveButton.setText(QCoreApplication.translate("JumpbridgeChooser", u"Export", None))
        self.formatInfoField.setHtml(QCoreApplication.translate("JumpbridgeChooser", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'Cantarell'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">Format of the jumpbridge data file:</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The jumpbridge file can be accessed either from the internet by specifying a URL for download, or by pointing to a local file.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; ma"
                        "rgin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">How to format the data for the jumpbridges:</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Put all the jumpbridges in one single textfile, where a line in the file represents a jumpbridge.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The line contains the first system, the connection between the systems and the second system. Between the three parts there has to be a space.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; font-style:italic;\">Examples:<"
                        "/span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">	System1 &lt;-&gt; System2</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">	System1 \u00bb System1</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">If selected, all jumpbridges will be drawn on map as bezier lines in different shades fo green.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Write the system names exactly as they are written in the maps.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">D"
                        "on't forget the space in between the system names and the jumpbridge!</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:600;\">Generate jump bridge:</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Generating the jumpbridges may take a while, received data will be cached internally and can be interrupted and continued. For some reasons, the received jumpbridges data may be not accurate.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Especially esi data sets for systems with heavy fights inside can provide several jumpbridges for only one target system.</p></body></ht"
                        "ml>", None))
        self.label.setText(QCoreApplication.translate("JumpbridgeChooser", u"Select the jump bridge data file or URL for automated updates on startup", None))
    # retranslateUi

