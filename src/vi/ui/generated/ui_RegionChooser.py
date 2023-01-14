# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'RegionChooser.ui'
##
## Created by: Qt User Interface Compiler version 6.5.0
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QSizePolicy, QToolButton, QVBoxLayout,
    QWidget)
import resource_rc

class Ui_RegionChooser(object):
    def setupUi(self, RegionChooser):
        if not RegionChooser.objectName():
            RegionChooser.setObjectName(u"RegionChooser")
        RegionChooser.resize(385, 101)
        self.verticalLayout = QVBoxLayout(RegionChooser)
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(3, 3, 3, 3)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(3, 3, 3, 3)
        self.label = QLabel(RegionChooser)
        self.label.setObjectName(u"label")
        self.label.setTextFormat(Qt.PlainText)
        self.label.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.label)


        self.verticalLayout.addLayout(self.verticalLayout_2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(3, 3, 3, 3)
        self.regionNameField = QLineEdit(RegionChooser)
        self.regionNameField.setObjectName(u"regionNameField")

        self.horizontalLayout_2.addWidget(self.regionNameField)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.saveButton = QToolButton(RegionChooser)
        self.saveButton.setObjectName(u"saveButton")
        icon = QIcon()
        icon.addFile(u":/Icons/res/apply.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.saveButton.setIcon(icon)
        self.saveButton.setIconSize(QSize(24, 24))

        self.verticalLayout.addWidget(self.saveButton)


        self.retranslateUi(RegionChooser)

        QMetaObject.connectSlotsByName(RegionChooser)
    # setupUi

    def retranslateUi(self, RegionChooser):
        RegionChooser.setWindowTitle(QCoreApplication.translate("RegionChooser", u"Region", None))
        self.label.setText(QCoreApplication.translate("RegionChooser", u"Enter the region to watch into the following field.", None))
#if QT_CONFIG(tooltip)
        self.saveButton.setToolTip(QCoreApplication.translate("RegionChooser", u"Apply setting and close", None))
#endif // QT_CONFIG(tooltip)
        self.saveButton.setText(QCoreApplication.translate("RegionChooser", u"Change", None))
    # retranslateUi

