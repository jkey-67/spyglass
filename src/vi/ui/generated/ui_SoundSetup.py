# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SoundSetup.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
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
    QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QSlider, QSpacerItem, QToolButton, QVBoxLayout,
    QWidget)
import resource_rc

class Ui_SoundSetup(object):
    def setupUi(self, SoundSetup):
        if not SoundSetup.objectName():
            SoundSetup.setObjectName(u"SoundSetup")
        SoundSetup.setWindowModality(Qt.ApplicationModal)
        SoundSetup.resize(512, 305)
        SoundSetup.setWindowOpacity(1.000000000000000)
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

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.testSoundButton = QToolButton(self.frame)
        self.testSoundButton.setObjectName(u"testSoundButton")
        icon = QIcon()
        icon.addFile(u":/Icons/res/play.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.testSoundButton.setIcon(icon)
        self.testSoundButton.setIconSize(QSize(24, 24))

        self.horizontalLayout_2.addWidget(self.testSoundButton)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.soundAlarm_2 = QLineEdit(self.frame)
        self.soundAlarm_2.setObjectName(u"soundAlarm_2")
        self.soundAlarm_2.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_2, 1, 1, 1, 1)

        self.selectAlarm_1 = QToolButton(self.frame)
        self.selectAlarm_1.setObjectName(u"selectAlarm_1")
        icon1 = QIcon()
        icon1.addFile(u":/Icons/res/load.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.selectAlarm_1.setIcon(icon1)
        self.selectAlarm_1.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.selectAlarm_1, 0, 2, 1, 1)

        self.soundAlarm_3 = QLineEdit(self.frame)
        self.soundAlarm_3.setObjectName(u"soundAlarm_3")
        self.soundAlarm_3.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_3, 2, 1, 1, 1)

        self.soundAlarm_5 = QLineEdit(self.frame)
        self.soundAlarm_5.setObjectName(u"soundAlarm_5")
        self.soundAlarm_5.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_5, 4, 1, 1, 1)

        self.selectAlarm_3 = QToolButton(self.frame)
        self.selectAlarm_3.setObjectName(u"selectAlarm_3")
        self.selectAlarm_3.setIcon(icon1)
        self.selectAlarm_3.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.selectAlarm_3, 2, 2, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_2.addWidget(self.label_5, 2, 0, 1, 1)

        self.palyAlarm_2 = QToolButton(self.frame)
        self.palyAlarm_2.setObjectName(u"palyAlarm_2")
        self.palyAlarm_2.setIcon(icon)
        self.palyAlarm_2.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.palyAlarm_2, 1, 3, 1, 1)

        self.label_7 = QLabel(self.frame)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_2.addWidget(self.label_7, 4, 0, 1, 1)

        self.selectAlarm_4 = QToolButton(self.frame)
        self.selectAlarm_4.setObjectName(u"selectAlarm_4")
        self.selectAlarm_4.setIcon(icon1)
        self.selectAlarm_4.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.selectAlarm_4, 3, 2, 1, 1)

        self.selectAlarm_2 = QToolButton(self.frame)
        self.selectAlarm_2.setObjectName(u"selectAlarm_2")
        self.selectAlarm_2.setIcon(icon1)
        self.selectAlarm_2.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.selectAlarm_2, 1, 2, 1, 1)

        self.selectAlarm_5 = QToolButton(self.frame)
        self.selectAlarm_5.setObjectName(u"selectAlarm_5")
        self.selectAlarm_5.setIcon(icon1)
        self.selectAlarm_5.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.selectAlarm_5, 4, 2, 1, 1)

        self.palyAlarm_4 = QToolButton(self.frame)
        self.palyAlarm_4.setObjectName(u"palyAlarm_4")
        self.palyAlarm_4.setIcon(icon)
        self.palyAlarm_4.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.palyAlarm_4, 3, 3, 1, 1)

        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout_2.addWidget(self.label_4, 1, 0, 1, 1)

        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 0, 0, 1, 1)

        self.palyAlarm_5 = QToolButton(self.frame)
        self.palyAlarm_5.setObjectName(u"palyAlarm_5")
        self.palyAlarm_5.setIcon(icon)
        self.palyAlarm_5.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.palyAlarm_5, 4, 3, 1, 1)

        self.soundAlarm_4 = QLineEdit(self.frame)
        self.soundAlarm_4.setObjectName(u"soundAlarm_4")
        self.soundAlarm_4.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_4, 3, 1, 1, 1)

        self.palyAlarm_3 = QToolButton(self.frame)
        self.palyAlarm_3.setObjectName(u"palyAlarm_3")
        self.palyAlarm_3.setIcon(icon)
        self.palyAlarm_3.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.palyAlarm_3, 2, 3, 1, 1)

        self.palyAlarm_1 = QToolButton(self.frame)
        self.palyAlarm_1.setObjectName(u"palyAlarm_1")
        self.palyAlarm_1.setIcon(icon)
        self.palyAlarm_1.setIconSize(QSize(24, 24))

        self.gridLayout_2.addWidget(self.palyAlarm_1, 0, 3, 1, 1)

        self.label_6 = QLabel(self.frame)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_2.addWidget(self.label_6, 3, 0, 1, 1)

        self.soundAlarm_1 = QLineEdit(self.frame)
        self.soundAlarm_1.setObjectName(u"soundAlarm_1")
        self.soundAlarm_1.setReadOnly(True)

        self.gridLayout_2.addWidget(self.soundAlarm_1, 0, 1, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.applySoundSetting = QToolButton(self.frame)
        self.applySoundSetting.setObjectName(u"applySoundSetting")
        icon2 = QIcon()
        icon2.addFile(u":/Icons/res/apply.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.applySoundSetting.setIcon(icon2)
        self.applySoundSetting.setIconSize(QSize(24, 24))

        self.horizontalLayout.addWidget(self.applySoundSetting)

        self.useSpokenNotifications = QToolButton(self.frame)
        self.useSpokenNotifications.setObjectName(u"useSpokenNotifications")
        self.useSpokenNotifications.setMinimumSize(QSize(0, 0))
        icon3 = QIcon()
        icon3.addFile(u":/Icons/res/volume_off.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon3.addFile(u":/Icons/res/volume.svg", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.useSpokenNotifications.setIcon(icon3)
        self.useSpokenNotifications.setIconSize(QSize(24, 24))
        self.useSpokenNotifications.setCheckable(True)

        self.horizontalLayout.addWidget(self.useSpokenNotifications)

        self.useSoundSystem = QToolButton(self.frame)
        self.useSoundSystem.setObjectName(u"useSoundSystem")
        self.useSoundSystem.setMinimumSize(QSize(0, 0))
        icon4 = QIcon()
        icon4.addFile(u":/Icons/res/speach_off.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        icon4.addFile(u":/Icons/res/speach.svg", QSize(), QIcon.Mode.Normal, QIcon.State.On)
        self.useSoundSystem.setIcon(icon4)
        self.useSoundSystem.setIconSize(QSize(24, 24))
        self.useSoundSystem.setCheckable(True)

        self.horizontalLayout.addWidget(self.useSoundSystem)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.defaultSounds = QToolButton(self.frame)
        self.defaultSounds.setObjectName(u"defaultSounds")
        icon5 = QIcon()
        icon5.addFile(u":/Icons/res/default.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.defaultSounds.setIcon(icon5)
        self.defaultSounds.setIconSize(QSize(24, 24))

        self.horizontalLayout.addWidget(self.defaultSounds)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.horizontalLayout_4.addLayout(self.verticalLayout)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setMaximumSize(QSize(32, 32))
        self.label.setPixmap(QPixmap(u":/Icons/res/volume.svg"))
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignCenter)

        self.verticalLayout_3.addWidget(self.label)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.volumeSlider = QSlider(self.frame)
        self.volumeSlider.setObjectName(u"volumeSlider")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
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
#if QT_CONFIG(tooltip)
        self.testSoundButton.setToolTip(QCoreApplication.translate("SoundSetup", u"Play the soundfile", None))
#endif // QT_CONFIG(tooltip)
        self.testSoundButton.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
#if QT_CONFIG(shortcut)
        self.testSoundButton.setShortcut(QCoreApplication.translate("SoundSetup", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.selectAlarm_1.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.selectAlarm_3.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.label_5.setText(QCoreApplication.translate("SoundSetup", u"Dist 3", None))
#if QT_CONFIG(tooltip)
        self.palyAlarm_2.setToolTip(QCoreApplication.translate("SoundSetup", u"Play the soundfile", None))
#endif // QT_CONFIG(tooltip)
        self.palyAlarm_2.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
#if QT_CONFIG(shortcut)
        self.palyAlarm_2.setShortcut(QCoreApplication.translate("SoundSetup", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.label_7.setText(QCoreApplication.translate("SoundSetup", u"Dist 5", None))
        self.selectAlarm_4.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.selectAlarm_2.setText(QCoreApplication.translate("SoundSetup", u"...", None))
        self.selectAlarm_5.setText(QCoreApplication.translate("SoundSetup", u"...", None))
#if QT_CONFIG(tooltip)
        self.palyAlarm_4.setToolTip(QCoreApplication.translate("SoundSetup", u"Play the soundfile", None))
#endif // QT_CONFIG(tooltip)
        self.palyAlarm_4.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
#if QT_CONFIG(shortcut)
        self.palyAlarm_4.setShortcut(QCoreApplication.translate("SoundSetup", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.label_4.setText(QCoreApplication.translate("SoundSetup", u"Dist. 2 ", None))
        self.label_3.setText(QCoreApplication.translate("SoundSetup", u"Dist. 1", None))
#if QT_CONFIG(tooltip)
        self.palyAlarm_5.setToolTip(QCoreApplication.translate("SoundSetup", u"Play the soundfile", None))
#endif // QT_CONFIG(tooltip)
        self.palyAlarm_5.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
#if QT_CONFIG(shortcut)
        self.palyAlarm_5.setShortcut(QCoreApplication.translate("SoundSetup", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.palyAlarm_3.setToolTip(QCoreApplication.translate("SoundSetup", u"Play the soundfile", None))
#endif // QT_CONFIG(tooltip)
        self.palyAlarm_3.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
#if QT_CONFIG(shortcut)
        self.palyAlarm_3.setShortcut(QCoreApplication.translate("SoundSetup", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.palyAlarm_1.setToolTip(QCoreApplication.translate("SoundSetup", u"Play the soundfile", None))
#endif // QT_CONFIG(tooltip)
        self.palyAlarm_1.setText(QCoreApplication.translate("SoundSetup", u"Play", None))
#if QT_CONFIG(shortcut)
        self.palyAlarm_1.setShortcut(QCoreApplication.translate("SoundSetup", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.label_6.setText(QCoreApplication.translate("SoundSetup", u"Dist 4", None))
#if QT_CONFIG(tooltip)
        self.applySoundSetting.setToolTip(QCoreApplication.translate("SoundSetup", u"Apply setting and close", None))
#endif // QT_CONFIG(tooltip)
        self.applySoundSetting.setText(QCoreApplication.translate("SoundSetup", u"...", None))
#if QT_CONFIG(tooltip)
        self.useSpokenNotifications.setToolTip(QCoreApplication.translate("SoundSetup", u"Enable notification sounds.", None))
#endif // QT_CONFIG(tooltip)
        self.useSpokenNotifications.setText(QCoreApplication.translate("SoundSetup", u"Use Spoken Notifications", None))
#if QT_CONFIG(tooltip)
        self.useSoundSystem.setToolTip(QCoreApplication.translate("SoundSetup", u"Enable text to speach output.", None))
#endif // QT_CONFIG(tooltip)
        self.useSoundSystem.setText(QCoreApplication.translate("SoundSetup", u"Use Spoken Notifications", None))
#if QT_CONFIG(tooltip)
        self.defaultSounds.setToolTip(QCoreApplication.translate("SoundSetup", u"Reset all values to default.", None))
#endif // QT_CONFIG(tooltip)
        self.defaultSounds.setText(QCoreApplication.translate("SoundSetup", u"Default", None))
        self.label.setText("")
#if QT_CONFIG(tooltip)
        self.volumeSlider.setToolTip(QCoreApplication.translate("SoundSetup", u"Adust Sound Volume", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

