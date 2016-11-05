#!/usr/bin/python
from collections import defaultdict
import argparse
from sys import stderr
import os.path
import re


class ElanParser:
    
    def __init__(self, transcriptFile, spaced):
        self.transcriptFile = transcriptFile
        self.currentOverlapIndex = 0
        self.linesSinceOverlap = 0
        self.overlapItems = defaultdict(int)
        self.newLines = []
        self.additionalOffset = 0
        self.newOverlapsInLine = 0
        self.subscriptRegex = re.compile(r'\[(\d*)')
        self.splitSpeakerContentRegex = re.compile(r';\s*')

        # Hacky solution. If the line is blank, the first statement will fail.
        if spaced:
            verbosePrint('setting spaced')
            self.skipWhite = self.assertIsEmptyLine
        else:
            self.skipWhite = lambda l: None

    def assertIsEmptyLine(self, line):
        assert line[0] != '\n'

    def GenerateIndentedText(self):
        for linno, line in enumerate(inTranFile):
            try:
                verbosePrint(self.skipWhite(line))
            except:
                verbosePrint("found blank")
                self.newLines.append(line)
                continue
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

    def WriteNewTextFile(self, inTranFilename, outputPattern):
        with open(self.ParseOutputFilenameTemplate(inTranFilename, outputPattern), 'w') as outTranFile:
            for line in self.newLines:
                outTranFile.write(self.cleanNewLine(line))

    def WriteNewHtmlFile(self, inTranFilename, outputPattern):
        with open(self.ParseOutputFilenameTemplate(inTranFilename, outputPattern) + '.html', 'w') as outTranFile:
            outTranFile.write("""<html>
    <head>
        <title>{title}</title>
        <style type="text/css">
body {{
    font-family: "{fontfamily}";
}}
td.speaker {{
    padding-right: 3em;
}}
        </style>
        <script type="text/javascript">
window.addEventListener("load", function() {{
    positions = Array();
    lines = document.getElementsByTagName("tr");
    overlapInLastLine = false;
    for (let line of lines) {{
        overlapInLine = false;
        overlaps = line.getElementsByClassName("overlap_start");
        for (let overlap of overlaps) {{
            console.log(overlap.dataset.overlapIndex);
            if (overlap.dataset.overlapIndex) {{
                overlapIndex = overlap.dataset.overlapIndex;
            }} else {{
                overlapIndex = 1;
            }}
            newOverlap = !overlapInLastLine || positions[overlapIndex] == undefined
            overlapInLine = true;
            if (newOverlap) {{
                    positions[overlapIndex] = getPosition(overlap)['x'];
            }} else {{
                // difference
                differenceInPosition = positions[overlapIndex] - getPosition(overlap)['x'];
            
                overlap.insertAdjacentHTML('beforebegin', '<span style="display: inline-block; width: ' + differenceInPosition + 'px;">&nbsp;</div>')
            }}
        }}
        if (!overlapInLine) {{
            positions = Array();
            overlapInLastLine = false
        }} else {{
            overlapInLastLine = true
        }}
    }}
}});

// Helper function to get an element's exact position
function getPosition(el) {{
  var xPos = 0;
  var yPos = 0;
 
  while (el) {{
    if (el.tagName == "BODY") {{
      // deal with browser quirks with body/window/document and page scroll
      var xScroll = el.scrollLeft || document.documentElement.scrollLeft;
      var yScroll = el.scrollTop || document.documentElement.scrollTop;
 
      xPos += (el.offsetLeft - xScroll + el.clientLeft);
      yPos += (el.offsetTop - yScroll + el.clientTop);
    }} else {{
      // for all other non-BODY elements
      xPos += (el.offsetLeft - el.scrollLeft + el.clientLeft);
      yPos += (el.offsetTop - el.scrollTop + el.clientTop);
    }}
 
    el = el.offsetParent;
  }}
  return {{
    x: xPos,
    y: yPos
  }};
}}
        </script>
    </head>
    <body>
        <table>
""".format(title='Transcript ({})'.format(inTranFilename), fontfamily=args.font))
            for linno, line in enumerate(self.newLines):
                # Set up table format
                parts = re.split(self.splitSpeakerContentRegex, self.cleanNewLine(line))
                assert len(parts) <= 2, "Splitting by semicolon did not work."
                try:
                    outTranFile.write("<tr><td>{linno}</td><td class=\"speaker\">{speaker};</td><td class=\"utterance\">{utterance}</td></tr>\n".format(linno=linno + 1, speaker=parts[0], utterance=self.createSubscripts(parts[1].strip())))
                except:
                    outTranFile.write("<tr><td>{linno}</td><td class=\"speaker\">&nbsp;</td><td class=\"utterance\">{utterance}</td></tr>\n".format(linno=linno + 1, utterance=self.createSubscripts(parts[0].strip())))
            outTranFile.write("""
        </table>
    </body>
</html>""")

    def createSubscripts(self, line):
        return re.sub(self.subscriptRegex, '<span class="overlap_start" data-overlap-index="\\1">[<sub>\\1</sub></span>', line)


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
argParser.add_argument("-s", '--spaced', action="store_true", help="Transcript file contains a blank space between IUs")
argParser.add_argument("-v", '--verbose', action="store_true", help="output additional messages (primarily for debugging, useless in general)")
argParser.add_argument("--html", action="store_true", help="output an html format")
argParser.add_argument("--font", default="Times New Roman", help="with the --html option, the font for output to HTML")
args = argParser.parse_args()

if args.explicit_start:
    elanParser = MarkedElanParser
else:
    elanParser = SimpleElanParser

if args.verbose:
    def verbosePrint(msg):
        print(msg)
else:
    def verbosePrint(msg):
        None

# Iterate over list of files, parse each one, and write indented file
for argFilename in args.input_file:
    with open(argFilename, 'r') as inTranFile:
        currentElanParser = elanParser(inTranFile, args.spaced)
        currentElanParser.GenerateIndentedText()
        if (args.html):
            try:
                import html
            except Exception as e:
                print("Tried to load `html` library, but the library was not found. Install it from pip or pypy for python3.", file=stderr)
                raise
            currentElanParser.WriteNewHtmlFile(argFilename, args.output_pattern)
        else:
            currentElanParser.WriteNewTextFile(argFilename, args.output_pattern)
