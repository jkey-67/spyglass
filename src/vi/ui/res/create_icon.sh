#!/bin/bash
inkscape -w 24 -h 24 logo.svg -o logo-24.png
inkscape -w 32 -h 32 logo.svg -o logo-32.png
inkscape -w 48 -h 48 logo.svg -o logo-48.png
inkscape -w 64 -h 64 logo.svg -o logo-64.png
inkscape -w 96 -h 96 logo.svg -o logo-96.png
inkscape -w 128 -h 128 logo.svg -o logo-128.png
inkscape -w 256 -h 256 logo.svg -o logo-256.png

magick -colorspace RGB logo-16.png logo-24.png logo-32.png logo-48.png logo-64.png logo-96.png logo-128.png logo-256.png icon.ico

