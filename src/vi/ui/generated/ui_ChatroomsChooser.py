# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ChatroomsChooser.ui'
##
## Created by: Qt User Interface Compiler version 6.7.1
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
    QLabel, QPlainTextEdit, QSizePolicy, QSpacerItem,
    QToolButton, QVBoxLayout, QWidget)
import resource_rc

class Ui_ChatroomsChooser(object):
    def setupUi(self, ChatroomsChooser):
        if not ChatroomsChooser.objectName():
            ChatroomsChooser.setObjectName(u"ChatroomsChooser")
        ChatroomsChooser.resize(381, 229)
        self.gridLayout = QGridLayout(ChatroomsChooser)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(ChatroomsChooser)
        self.label.setObjectName(u"label")
        self.label.setTextFormat(Qt.PlainText)
        self.label.setWordWrap(True)

        self.verticalLayout.addWidget(self.label)

        self.roomnamesField = QPlainTextEdit(ChatroomsChooser)
        self.roomnamesField.setObjectName(u"roomnamesField")

        self.verticalLayout.addWidget(self.roomnamesField)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.saveButton = QToolButton(ChatroomsChooser)
        self.saveButton.setObjectName(u"saveButton")
        icon = QIcon()
        icon.addFile(u":/Icons/res/apply.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.saveButton.setIcon(icon)
        self.saveButton.setIconSize(QSize(24, 24))

        self.horizontalLayout_2.addWidget(self.saveButton)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.defaultButton = QToolButton(ChatroomsChooser)
        self.defaultButton.setObjectName(u"defaultButton")
        icon1 = QIcon()
        icon1.addFile(u":/Icons/res/default.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.defaultButton.setIcon(icon1)
        self.defaultButton.setIconSize(QSize(24, 24))

        self.horizontalLayout_2.addWidget(self.defaultButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(ChatroomsChooser)

        QMetaObject.connectSlotsByName(ChatroomsChooser)
    # setupUi

    def retranslateUi(self, ChatroomsChooser):
        ChatroomsChooser.setWindowTitle(QCoreApplication.translate("ChatroomsChooser", u"Chatrooms", None))
        self.label.setText(QCoreApplication.translate("ChatroomsChooser", u"Enter the chatrooms to watch into the following field. Separate them by comma.", None))
#if QT_CONFIG(tooltip)
        self.saveButton.setToolTip(QCoreApplication.translate("ChatroomsChooser", u"Apply setting and close", None))
#endif // QT_CONFIG(tooltip)
        self.saveButton.setText(QCoreApplication.translate("ChatroomsChooser", u"Save", None))
        self.defaultButton.setText(QCoreApplication.translate("ChatroomsChooser", u"Restore Defaults", None))
    # retranslateUi

