# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'RegionChooser.ui'
##
## Created by: Qt User Interface Compiler version 6.3.1
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
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_RegionChooser(object):
    def setupUi(self, RegionChooser):
        if not RegionChooser.objectName():
            RegionChooser.setObjectName(u"RegionChooser")
        RegionChooser.resize(419, 107)
        self.gridLayout = QGridLayout(RegionChooser)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(RegionChooser)
        self.label.setObjectName(u"label")
        self.label.setTextFormat(Qt.PlainText)
        self.label.setWordWrap(True)

        self.verticalLayout.addWidget(self.label)

        self.regionNameField = QLineEdit(RegionChooser)
        self.regionNameField.setObjectName(u"regionNameField")

        self.verticalLayout.addWidget(self.regionNameField)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.cancelButton = QPushButton(RegionChooser)
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout_2.addWidget(self.cancelButton)

        self.saveButton = QPushButton(RegionChooser)
        self.saveButton.setObjectName(u"saveButton")

        self.horizontalLayout_2.addWidget(self.saveButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        QWidget.setTabOrder(self.regionNameField, self.cancelButton)
        QWidget.setTabOrder(self.cancelButton, self.saveButton)

        self.retranslateUi(RegionChooser)

        self.saveButton.setDefault(True)


        QMetaObject.connectSlotsByName(RegionChooser)
    # setupUi

    def retranslateUi(self, RegionChooser):
        RegionChooser.setWindowTitle(QCoreApplication.translate("RegionChooser", u"Region", None))
        self.label.setText(QCoreApplication.translate("RegionChooser", u"Enter the region to watch into the following field.", None))
        self.cancelButton.setText(QCoreApplication.translate("RegionChooser", u"Close", None))
        self.saveButton.setText(QCoreApplication.translate("RegionChooser", u"Change", None))
    # retranslateUi

