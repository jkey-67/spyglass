import PyInstaller
import PyInstaller.__main__
import os

def instFiles():
    
    workdir = os.path.abspath(os.path.join(os.getcwd(),"..",".."))
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
        '--name', 'spyglass-1.6.2',
        '../spyglass.py',
        '--icon=../icon.ico',
        "--add-data=../vi/ui/*.ui;./vi/ui",
        "--add-data=../vi/ui/res/*;./vi/ui/res",
        "--add-data=../vi/ui/res/mapdata*;./vi/ui/res/mapdata",
        "--add-data=../docs/*.*;./docs/",
        "--add-data=../vi/ui/res/styles/*;./vi/ui/res/styles",
        #"--add-binary=../lib/*.dll;./lib",
        '--hidden-import=pyttsx3.drivers',
        '--hidden-import=pyttsx3.drivers.dummy',
        '--hidden-import=import=pyttsx3.drivers.espeak',
        '--hidden-import=pyttsx3.drivers.nsss',
        '--hidden-import=pyttsx3.drivers.sapi5',
        '--hidden-import=packaging'
    ])

if __name__ == "__main__":
    instFiles()
