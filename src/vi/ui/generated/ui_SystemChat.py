# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SystemChat.ui'
##
## Created by: Qt User Interface Compiler version 6.4.0
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog,
    QGridLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_SystemChat(object):
    def setupUi(self, SystemChat):
        if not SystemChat.objectName():
            SystemChat.setObjectName(u"SystemChat")
        SystemChat.setWindowModality(Qt.NonModal)
        SystemChat.resize(390, 327)
        SystemChat.setMinimumSize(QSize(0, 0))
        SystemChat.setModal(False)
        self.gridLayout = QGridLayout(SystemChat)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.chat = QListWidget(SystemChat)
        self.chat.setObjectName(u"chat")
        self.chat.setSelectionMode(QAbstractItemView.NoSelection)

        self.verticalLayout.addWidget(self.chat)

        self.widget = QWidget(SystemChat)
        self.widget.setObjectName(u"widget")
        self.widget.setMinimumSize(QSize(0, 31))
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setSpacing(5)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(5, 5, 5, 5)
        self.closeButton = QPushButton(self.widget)
        self.closeButton.setObjectName(u"closeButton")

        self.verticalLayout_3.addWidget(self.closeButton)


        self.gridLayout_2.addLayout(self.verticalLayout_3, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(5, 7, 5, 0)
        self.location_vlayout = QVBoxLayout()
        self.location_vlayout.setSpacing(2)
        self.location_vlayout.setObjectName(u"location_vlayout")
        self.playerNamesBox = QComboBox(self.widget)
        self.playerNamesBox.setObjectName(u"playerNamesBox")

        self.location_vlayout.addWidget(self.playerNamesBox)

        self.locationButton = QPushButton(self.widget)
        self.locationButton.setObjectName(u"locationButton")

        self.location_vlayout.addWidget(self.locationButton)

        self.openzKillboard = QPushButton(self.widget)
        self.openzKillboard.setObjectName(u"openzKillboard")
        self.openzKillboard.setIconSize(QSize(17, 16))

        self.location_vlayout.addWidget(self.openzKillboard)


        self.horizontalLayout.addLayout(self.location_vlayout)

        self.status_vlayout = QVBoxLayout()
        self.status_vlayout.setSpacing(2)
        self.status_vlayout.setObjectName(u"status_vlayout")
        self.alarmButton = QPushButton(self.widget)
        self.alarmButton.setObjectName(u"alarmButton")

        self.status_vlayout.addWidget(self.alarmButton)

        self.clearButton = QPushButton(self.widget)
        self.clearButton.setObjectName(u"clearButton")

        self.status_vlayout.addWidget(self.clearButton)

        self.dotlanButton = QPushButton(self.widget)
        self.dotlanButton.setObjectName(u"dotlanButton")

        self.status_vlayout.addWidget(self.dotlanButton)


        self.horizontalLayout.addLayout(self.status_vlayout)


        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.widget)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(SystemChat)

        QMetaObject.connectSlotsByName(SystemChat)
    # setupUi

    def retranslateUi(self, SystemChat):
        SystemChat.setWindowTitle(QCoreApplication.translate("SystemChat", u"Dialog", None))
        self.closeButton.setText(QCoreApplication.translate("SystemChat", u"Close", None))
        self.locationButton.setText(QCoreApplication.translate("SystemChat", u"Set Char Location", None))
        self.openzKillboard.setText(QCoreApplication.translate("SystemChat", u"Open zKillboard", None))
        self.alarmButton.setText(QCoreApplication.translate("SystemChat", u"Set alarm", None))
        self.clearButton.setText(QCoreApplication.translate("SystemChat", u"Set clear", None))
        self.dotlanButton.setText(QCoreApplication.translate("SystemChat", u"Open Dotlan", None))
    # retranslateUi

