# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ChatroomsChooser.ui'
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
    QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_ChatroomsChooser(object):
    def setupUi(self, ChatroomsChooser):
        if not ChatroomsChooser.objectName():
            ChatroomsChooser.setObjectName(u"ChatroomsChooser")
        ChatroomsChooser.resize(556, 197)
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
        self.defaultButton = QPushButton(ChatroomsChooser)
        self.defaultButton.setObjectName(u"defaultButton")

        self.horizontalLayout_2.addWidget(self.defaultButton)

        self.cancelButton = QPushButton(ChatroomsChooser)
        self.cancelButton.setObjectName(u"cancelButton")

        self.horizontalLayout_2.addWidget(self.cancelButton)

        self.saveButton = QPushButton(ChatroomsChooser)
        self.saveButton.setObjectName(u"saveButton")

        self.horizontalLayout_2.addWidget(self.saveButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)


        self.retranslateUi(ChatroomsChooser)

        QMetaObject.connectSlotsByName(ChatroomsChooser)
    # setupUi

    def retranslateUi(self, ChatroomsChooser):
        ChatroomsChooser.setWindowTitle(QCoreApplication.translate("ChatroomsChooser", u"Chatrooms", None))
        self.label.setText(QCoreApplication.translate("ChatroomsChooser", u"Enter the chatrooms to watch into the following field. Separate them by comma.", None))
        self.defaultButton.setText(QCoreApplication.translate("ChatroomsChooser", u"Restore Defaults", None))
        self.cancelButton.setText(QCoreApplication.translate("ChatroomsChooser", u"Cancel", None))
        self.saveButton.setText(QCoreApplication.translate("ChatroomsChooser", u"Save", None))
    # retranslateUi

