for file in ChatroomsChooser Info MainWindow JumpbridgeChooser SystemChat ChatEntry SoundSetup; do
  pyside6-uic $file'.ui' -o 'generated/ui_'$file'.py'
done;
pyside6-rcc -binary ./resource.qrc -o ../../resource_rc.py