# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SoundSetup.ui'
##
## Created by: Qt User Interface Compiler version 6.3.2
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSlider, QSpacerItem, QToolButton,
    QVBoxLayout, QWidget)

class Ui_SoundSetup(object):
    def setupUi(self, SoundSetup):
        if not SoundSetup.objectName():
            SoundSetup.setObjectName(u"SoundSetup")
        SoundSetup.setWindowModality(Qt.ApplicationModal)
        SoundSetup.resize(588, 311)
        self.verticalLayout_2 = QVBoxLayout(SoundSetup)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame = QFrame(SoundSetup)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.testSoundButton = QToolButton(self.frame)
        self.testSoundButton.setObjectName(u"testSoundButton")

        self.horizontalLayout_2.addWidget(self.testSoundButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_2.addWidget(self.label_5, 2, 0, 1, 1)

        self.palyAlarm_3 = QToolButton(self.frame)
        self.palyAlarm_3.setObjectName(u"palyAlarm_3")

        self.gridLayout_2.addWidget(self.palyAlarm_3, 2, 3, 1, 1)

        self.label_7 = QLabel(self.frame)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_2.addWidget(self.label_7, 4, 0, 1, 1)

        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_2.addWidget(self.label_4, 1, 0, 1, 1)

        self.soundAlarm_4 = QLineEdit(self.frame)
        self.soundAlarm_4.setObjectName(u"soundAlarm_4")
        self.soundAlarm_4.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_4, 3, 1, 1, 1)

        self.selectAlarm_1 = QToolButton(self.frame)
        self.selectAlarm_1.setObjectName(u"selectAlarm_1")

        self.gridLayout_2.addWidget(self.selectAlarm_1, 0, 2, 1, 1)

        self.soundAlarm_5 = QLineEdit(self.frame)
        self.soundAlarm_5.setObjectName(u"soundAlarm_5")
        self.soundAlarm_5.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_5, 4, 1, 1, 1)

        self.selectAlarm_2 = QToolButton(self.frame)
        self.selectAlarm_2.setObjectName(u"selectAlarm_2")

        self.gridLayout_2.addWidget(self.selectAlarm_2, 1, 2, 1, 1)

        self.palyAlarm_4 = QToolButton(self.frame)
        self.palyAlarm_4.setObjectName(u"palyAlarm_4")

        self.gridLayout_2.addWidget(self.palyAlarm_4, 3, 3, 1, 1)

        self.soundAlarm_3 = QLineEdit(self.frame)
        self.soundAlarm_3.setObjectName(u"soundAlarm_3")
        self.soundAlarm_3.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_3, 2, 1, 1, 1)

        self.label_6 = QLabel(self.frame)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_2.addWidget(self.label_6, 3, 0, 1, 1)

        self.selectAlarm_3 = QToolButton(self.frame)
        self.selectAlarm_3.setObjectName(u"selectAlarm_3")

        self.gridLayout_2.addWidget(self.selectAlarm_3, 2, 2, 1, 1)

        self.palyAlarm_5 = QToolButton(self.frame)
        self.palyAlarm_5.setObjectName(u"palyAlarm_5")

        self.gridLayout_2.addWidget(self.palyAlarm_5, 4, 3, 1, 1)

        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 0, 0, 1, 1)

        self.palyAlarm_1 = QToolButton(self.frame)
        self.palyAlarm_1.setObjectName(u"palyAlarm_1")

        self.gridLayout_2.addWidget(self.palyAlarm_1, 0, 3, 1, 1)

        self.soundAlarm_2 = QLineEdit(self.frame)
        self.soundAlarm_2.setObjectName(u"soundAlarm_2")
        self.soundAlarm_2.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_2, 1, 1, 1, 1)

        self.palyAlarm_2 = QToolButton(self.frame)
        self.palyAlarm_2.setObjectName(u"palyAlarm_2")

        self.gridLayout_2.addWidget(self.palyAlarm_2, 1, 3, 1, 1)

        self.selectAlarm_5 = QToolButton(self.frame)
        self.selectAlarm_5.setObjectName(u"selectAlarm_5")

        self.gridLayout_2.addWidget(self.selectAlarm_5, 4, 2, 1, 1)

        self.soundAlarm_1 = QLineEdit(self.frame)
        self.soundAlarm_1.setObjectName(u"soundAlarm_1")
        self.soundAlarm_1.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_1, 0, 1, 1, 1)

        self.selectAlarm_4 = QToolButton(self.frame)
        self.selectAlarm_4.setObjectName(u"selectAlarm_4")

        self.gridLayout_2.addWidget(self.selectAlarm_4, 3, 2, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.closeButton = QPushButton(self.frame)
        self.closeButton.setObjectName(u"closeButton")

        self.horizontalLayout.addWidget(self.closeButton)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.defaultSounds = QPushButton(self.frame)
        self.defaultSounds.setObjectName(u"defaultSounds")

        self.horizontalLayout.addWidget(self.defaultSounds)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.horizontalLayout_4.addLayout(self.verticalLayout)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignCenter)

        self.verticalLayout_3.addWidget(self.label)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.volumeSlider = QSlider(self.frame)
        self.volumeSlider.setObjectName(u"volumeSlider")
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.volumeSlider.sizePolicy().hasHeightForWidth())
        self.volumeSlider.setSizePolicy(sizePolicy)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setTracking(False)
        self.volumeSlider.setOrientation(Qt.Vertical)
        self.volumeSlider.setTickPosition(QSlider.TicksBelow)

        self.horizontalLayout_3.addWidget(self.volumeSlider)


        self.verticalLayout_3.addLayout(self.horizontalLayout_3)


        self.horizontalLayout_4.addLayout(self.verticalLayout_3)


        self.verticalLayout_2.addWidget(self.frame)


        self.retranslateUi(SoundSetup)

        QMetaObject.connectSlotsByName(SoundSetup)
    # setupUi

    def retranslateUi(self, SoundSetup):
        SoundSetup.setWindowTitle(QCoreApplication.translate("SoundSetup", u"Sound Setup", None))
        self.label_2.setText(QCoreApplication.translate("SoundSetup", u"Default", None))
        self.testSoundButton.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
        self.label_5.setText(QCoreApplication.translate("SoundSetup", u"Dist 3", None))
        self.palyAlarm_3.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
        self.label_7.setText(QCoreApplication.translate("SoundSetup", u"Dist 5", None))
        self.label_4.setText(QCoreApplication.translate("SoundSetup", u"Dist. 2 ", None))
        self.selectAlarm_1.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.selectAlarm_2.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.palyAlarm_4.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
        self.label_6.setText(QCoreApplication.translate("SoundSetup", u"Dist 4", None))
        self.selectAlarm_3.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.palyAlarm_5.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
        self.label_3.setText(QCoreApplication.translate("SoundSetup", u"Dist. 1", None))
        self.palyAlarm_1.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
        self.palyAlarm_2.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
        self.selectAlarm_5.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.selectAlarm_4.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.closeButton.setText(QCoreApplication.translate("SoundSetup", u"Close", None))
        self.defaultSounds.setText(QCoreApplication.translate("SoundSetup", u"Default", None))
        self.label.setText(QCoreApplication.translate("SoundSetup", u"Volume", None))
    # retranslateUi
