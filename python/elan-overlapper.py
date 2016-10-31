#!/usr/bin/python
from collections import defaultdict
import argparse
from sys import stderr
import os.path


class ElanParser:
    
    def __init__(self, transcriptFile):
        self.transcriptFile = transcriptFile
        self.currentOverlapIndex = 0
        self.linesSinceOverlap = 0
        self.overlapItems = defaultdict(int)
        self.newLines = []
        self.additionalOffset = 0
        self.newOverlapsInLine = 0

    def GenerateIndentedText(self):
        for linno, line in enumerate(inTranFile):
            newLine = line
            self.additionalOffset = 0
            self.newOverlapsInLine = 0
            lineContainedOverlap = False
            for charpos, character in enumerate(line):
                if character == '[':
                    verbosePrint('Found new overlap at line {} pos {}'.format(linno, charpos))
                    newLine = self.handleOverlap(newLine, charpos+self.additionalOffset)
                    lineContainedOverlap = True
            if lineContainedOverlap:
                self.linesSinceOverlap = 0
            else:
                self.linesSinceOverlap += 1
            self.newLines.append(newLine)
        return self.newLines

    def ParseOutputFilenameTemplate(self, inTranFilename, outputPattern):
        return outputPattern.replace('[INPUT-FILE]', os.path.splitext(inTranFilename)[0]).replace('[INPUT-EXTENSION]', os.path.splitext(inTranFilename)[1])       

    def WriteNewFile(self, inTranFilename, outputPattern):
        with open(self.ParseOutputFilenameTemplate(inTranFilename, outputPattern), 'w') as outTranFile:
            for line in self.newLines:
                outTranFile.write(self.cleanNewLine(line)) 

    def scanStringForDigit(self, stringToScan):
        digitString = ''
        for character in stringToScan:
            if character.isdigit():
                digitString += character
            else:
                break
        return digitString

    def handleOverlap(self, line, charpos):
        pass

    def cleanNewLine(self, line):
        pass


class SimpleElanParser(ElanParser):
    def handleOverlap(self, line, charpos):
        verbosePrint(self.linesSinceOverlap)
        if self.linesSinceOverlap > 0:
            verbosePrint("Reseting overlaps...")
            self.overlapItems = defaultdict(int)
            self.linesSinceOverlap = 0
        newLine = line
        adjustedCharpos = charpos - 1 # I forget why this is necessary
        self.currentOverlapIndex = self.scanStringForDigit(line[charpos + 1:]) or 0
        verbosePrint("Working on {} index".format(self.currentOverlapIndex))
        if not self.overlapItems[self.currentOverlapIndex]:
            # Assuming this is an entirely new block. Start a new reference position.
            self.overlapItems[self.currentOverlapIndex] = adjustedCharpos
            verbosePrint('\tDoing new block. Next will start at char {}'.format(self.overlapItems[self.currentOverlapIndex]))
        else:
            newLine = newLine[:adjustedCharpos] + ' ' * (self.overlapItems[self.currentOverlapIndex] - (adjustedCharpos)) + newLine[adjustedCharpos:] # The -1 here accounts for the eventual removal of the double [[
            verbosePrint('\tAdding position offset {}'.format(self.overlapItems[self.currentOverlapIndex] - (adjustedCharpos)))
            self.additionalOffset += (self.overlapItems[self.currentOverlapIndex] - (adjustedCharpos))
        return newLine

    def cleanNewLine(self, line):
        return line


class MarkedElanParser(ElanParser):
    def handleOverlap(self, line, charpos):
        newLine = line
        adjustedCharpos = charpos - 1 # I forget why this is necessary
        if line[charpos:charpos + 1] == '[[':
            self.currentOverlapIndex = self.scanStringForDigit(line[charpos + 2:]) or 0
            # This is an entirely new block. Start a new reference position.
            self.overlapItems[self.currentOverlapIndex] = adjustedCharpos - self.newOverlapsInLine # This takes into account the additional offset caused by previous offset actions in this line (multiple overlaps per IU), caused by the eventual removal of the double [[]]
            verbosePrint('\tDoing new block. Next will start at char {}'.format(self.overlapItems[self.currentOverlapIndex]))
            self.newOverlapsInLine += 1
        else: 
            self.currentOverlapIndex = self.scanStringForDigit(line[charpos + 1:]) or 0
            newLine = newLine[:adjustedCharpos] + ' ' * (self.overlapItems[self.currentOverlapIndex] - (adjustedCharpos)) + newLine[adjustedCharpos:] # The -1 here accounts for the eventual removal of the double [[
            verbosePrint('\tAdding position offset {}'.format(self.overlapItems[self.currentOverlapIndex] - (adjustedCharpos)))
            self.additionalOffset += (self.overlapItems[self.currentOverlapIndex] - (adjustedCharpos))
        return newLine

    def cleanNewLine(self, line):
        return line.replace('[[', '[')

# Begin runtime stuff
# Handle arguments
argParser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argParser.add_argument("input_file", metavar="input-file", nargs="+", help="the raw ELAN Traditional Transcript output")
argParser.add_argument("-e", '--explicit-start', action="store_true", help="parse inputfile for nonstandard [[ signifier of new overlap block")
argParser.add_argument("-o", '--output-pattern', default="[INPUT-FILE]-indented[INPUT-EXTENSION]", help="filename format for the output indented files")
argParser.add_argument("-v", '--verbose', action="store_true", help="output additional messages (primarily for debugging, useless in general)")
args = argParser.parse_args()

if args.explicit_start:
    elanParser = MarkedElanParser
else:
    elanParser = SimpleElanParser

if args.verbose:
    def verbosePrint(msg):
        print(msg)
else:
    verbosePrint = lambda *a: None

# Iterate over list of files, parse each one, and write indented file
for argFilename in args.input_file:
    with open(argFilename, 'r') as inTranFile:
        currentElanParser = elanParser(inTranFile)
        currentElanParser.GenerateIndentedText()
        currentElanParser.WriteNewFile(argFilename, args.output_pattern)
