import PyInstaller
import PyInstaller.__main__
import os


def instFiles():
    """
        generate the Windows installer
    Returns:
        None
    """
    workdir = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
    devdir = workdir
    distdir = os.path.join(devdir, 'dist')
    builddir = os.path.join(devdir, 'build')
    pathex = os.path.join(workdir, 'src')
    PyInstaller.__main__.run([
        '--clean',
        '-p', pathex,
        '--distpath', distdir,
        '--workpath', builddir,
        '--onefile',
        '--windowed',
        '--name', 'spyglass-1.7.3',
        '../spyglass.py',
        '--icon=../icon.ico',
        '--add-data=../vi/universe/*.json;./vi/universe',
        '--add-data=../vi/ui/*.ui;./vi/ui',
        '--add-data=../vi/ui/res/*.*;./vi/ui/res',
        '--add-data=../vi/ui/res/mapdata/*.*;./vi/ui/res/mapdata',
        '--add-data=../docs/*.*;./docs/',
        '--add-data=../vi/ui/res/styles/*;./vi/ui/res/styles',
        '--hidden-import=espeak-ng'
        '--hidden-import=pyttsx3.drivers',
        '--hidden-import=pyttsx3.drivers.dummy',
        '--hidden-import=pyttsx3.drivers.espeak',
        '--hidden-import=pyttsx3.drivers.nsss',
        '--hidden-import=pyttsx3.drivers.sapi5',
        '--hidden-import=packaging'
    ])


if __name__ == "__main__":
    instFiles()
