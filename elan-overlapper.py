#!/usr/bin/python
import re
from collections import defaultdict
import argparse
from sys import stderr
import os.path

argParser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
argParser.add_argument("input_file", metavar="input-file", nargs="+", help="the raw ELAN Traditional Transcript output")
argParser.add_argument("-e", '--explicit-start', action="store_true", help="parse inputfile for nonstandard [[ signifier of new overlap block")
argParser.add_argument("-o", '--output-pattern', default="[INPUT-FILE]-indented[INPUT-EXTENSION]", help="filename format for the output indented files")
args = argParser.parse_args()

def scanStringForDigit(stringToScan):
    digitString = ''
    for character in stringToScan:
        if character.isdigit():
            digitString += character
        else:
            break
    return digitString

if args.explicit_start:
    for argFilename in args.input_file:
        inTranFilename = argFilename
        newLines = []
        with open(inTranFilename, 'r') as inTranFile:
            overlapItems = defaultdict(int)
            linesSinceLast = defaultdict(int)
            for linno, line in enumerate(inTranFile):
                newLine = line
                additionalOffset = 0
                overlapsInLine = 0
                for charpos, character in enumerate(line):
                    if character == '[':
                        if (line[charpos - 1] == '['): 
                            # If the previous character was a [, the current [ just represents a new overlap; skip over it, it'll be removed later
                            continue
                        print('Found [ at line {} pos {}'.format(linno, charpos))
                        if line[charpos + 1] == '[':
                            # If this is a new overlap, the index character position is offset +2; otherwise, it's adjacent
                            newOverlap = True
                            indexCharacterPos = charpos + 2
                        else:
                            newOverlap = False
                            indexCharacterPos = charpos + 1
                        charpos -= 1
                        if not line[indexCharacterPos].isdigit():
                            # If there's no index character, assume it's 0 index
                            digit = 0
                            print('\tNo digit after [ ({}); assuming 0'.format(line[indexCharacterPos]))
                        else:
                            digit = scanStringForDigit(line[indexCharacterPos:])
                            print('\t{} found after ['.format(digit))

                        if newOverlap:
                            # Assuming this is an entirely new block. Start a new reference position.
                            overlapItems[digit] = additionalOffset + charpos - overlapsInLine # This takes into account the additional offset caused by previous offset actions in this line (multiple overlaps per IU)
                            print('\tDoing new block. Next will start at char {}'.format(overlapItems[digit] ))
                            overlapsInLine += 1
                        else:
                            newLine = newLine[:charpos] + ' ' * (overlapItems[digit] - (charpos)) + newLine[charpos:] # The -1 here accounts for the eventual removal of the double [[
                            print('\tAdding position offset {}'.format(overlapItems[digit] - (charpos)))
                            additionalOffset += (overlapItems[digit] - (charpos))
                        linesSinceLast[digit] = linno
                        
                newLines.append(newLine)
        with open(args.output_pattern.replace('[INPUT-FILE]', os.path.splitext(inTranFilename)[0]).replace('[INPUT-EXTENSION]', os.path.splitext(inTranFilename)[1]), 'w') as outTranFile:
            for line in newLines:
                outTranFile.write(line.replace('[[', '['))
else:
    for argFilename in args.input_file:
        inTranFilename = argFilename
        newLines = []
        with open(inTranFilename, 'r') as inTranFile:
            overlapItems = defaultdict(int)
            linesSinceOverlap = 0
            for linno, line in enumerate(inTranFile):
                newLine = line
                additionalOffset = 0
                lineContainsOverlap = False
                for charpos, character in enumerate(line):
                    if character == '[':
                        print('Found [ at line {} pos {}'.format(linno, charpos))
                        indexCharacterPos = charpos + 1
                        charpos -= 1

                        if not line[indexCharacterPos].isdigit():
                            # If there's no index character, assume it's 0 index
                            digit = 0
                            print('\tNo digit after [ ({}); assuming 0'.format(line[indexCharacterPos]))
                        else:
                            digit = scanStringForDigit(line[indexCharacterPos:])
                            print('\t{} found after ['.format(digit))

                        if not overlapItems[digit] or linesSinceOverlap > 0:
                            # Assuming this is an entirely new block. Start a new reference position.
                            overlapItems[digit] = additionalOffset + charpos
                            print('\tDoing new block. Next will start at char {}'.format(overlapItems[digit] ))
                        else:
                            newLine = newLine[:charpos] + ' ' * (overlapItems[digit] - (charpos)) + newLine[charpos:] # The -1 here accounts for the eventual removal of the double [[
                            print('\tAdding position offset {}'.format(overlapItems[digit] - (charpos)))
                            additionalOffset += (overlapItems[digit] - (charpos))
                        
                        lineContainsOverlap = True
                if not lineContainsOverlap:
                    print("Reseting overlaps in line {}".format(linno))
                    linesSinceOverlap += 1
                    overlapItems = defaultdict(int)
                else:
                    linesSinceOverlap = 0
                newLines.append(newLine)
        with open(args.output_pattern.replace('[INPUT-FILE]', os.path.splitext(inTranFilename)[0]).replace('[INPUT-EXTENSION]', os.path.splitext(inTranFilename)[1]), 'w') as outTranFile:
            for line in newLines:
                outTranFile.write(line) 