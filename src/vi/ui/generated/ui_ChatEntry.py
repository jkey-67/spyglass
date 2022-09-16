# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ChatEntry.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QSizePolicy, QWidget)

class Ui_ChatEntry(object):
    def setupUi(self, ChatEntry):
        if not ChatEntry.objectName():
            ChatEntry.setObjectName(u"ChatEntry")
        ChatEntry.resize(86, 46)
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ChatEntry.sizePolicy().hasHeightForWidth())
        ChatEntry.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(ChatEntry)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.avatarLabel = QLabel(ChatEntry)
        self.avatarLabel.setObjectName(u"avatarLabel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.avatarLabel.sizePolicy().hasHeightForWidth())
        self.avatarLabel.setSizePolicy(sizePolicy1)
        self.avatarLabel.setMinimumSize(QSize(32, 32))
        self.avatarLabel.setMaximumSize(QSize(32, 32))
        self.avatarLabel.setTextFormat(Qt.RichText)
        self.avatarLabel.setScaledContents(True)
        self.avatarLabel.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout.addWidget(self.avatarLabel)

        self.textLabel = QLabel(ChatEntry)
        self.textLabel.setObjectName(u"textLabel")
        sizePolicy2 = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.textLabel.sizePolicy().hasHeightForWidth())
        self.textLabel.setSizePolicy(sizePolicy2)
        self.textLabel.setTextFormat(Qt.RichText)
        self.textLabel.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.textLabel.setWordWrap(True)

        self.horizontalLayout.addWidget(self.textLabel)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 1, 1, 1)


        self.retranslateUi(ChatEntry)

        QMetaObject.connectSlotsByName(ChatEntry)
    # setupUi

    def retranslateUi(self, ChatEntry):
        ChatEntry.setWindowTitle(QCoreApplication.translate("ChatEntry", u"Form", None))
        self.avatarLabel.setText(QCoreApplication.translate("ChatEntry", u"TextLabel", None))
        self.textLabel.setText(QCoreApplication.translate("ChatEntry", u"?", None))
    # retranslateUi

