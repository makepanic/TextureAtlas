import sys
import os
from PIL import Image
from PIL import ImageDraw
import math

# Configurations you need to set. Only use borders if you ever do filtering on your sprites. And then you should
# probably set it to transparent or duplicate the edges depending on your use case. Using solid red now to
# make it clear they're there.
folderInput = './images/'
folderOutput = './result/'

atlasBaseName = 'search-icons'

#css specific
useTabs = False
tabSize = 4

borderColor = ''
tileCssClass = '.search-icon'


tabBuf = ''
images = []

# A source image structure that loads the image and stores the
# extents. It will also get the destination rect in the atlas written to it.
class SourceImage:
  def __init__(self, filePath, fileName, oi):
    self.filePath = filePath
    self.fileName = fileName
    self.fullPath = filePath + '/' + fileName
    self.origIndex = oi
    # Open the image and make sure it's in RGBA mode.
    self.img = Image.open(self.fullPath)
    self.img = self.img.convert('RGBA')
    self.uncropped = Rect(0,0, self.img.size[0]-1, self.img.size[1]-1)
    # Grab the bounding box from the alpha channel.
    alpha = self.img.split()[3]
    bbox = alpha.getbbox()
    if bbox == None:
      bbox = [0,0,1,1];
    alpha = None
    # Crop it and get the new extents.
    self.img = self.img.crop(bbox)
    self.img.load()
    self.offset = (bbox[0], bbox[1])
    self.rect = Rect(0,0, self.img.size[0]-1, self.img.size[1]-1)


# A simple rect class using inclusive coordinates.
class Rect:
  def __init__(self, x0,y0,x1,y1):
    self.xmin = int(x0)
    self.xmax = int(x1)
    self.ymin = int(y0)
    self.ymax = int(y1)

  def width(self):
    return int(self.xmax - self.xmin + 1)

  def height(self):
    return int(self.ymax - self.ymin + 1)

# A k-d tree node containing rectangles used to tightly pack images.
class Node:
  def __init__(self):
    self.image = None
    self.rect = Rect(0,0,0,0)
    self.child0 = None
    self.child1 = None

  # Iterate the full tree and write the destination rects to the source images.
  def finalize(self):
    if self.image != None:
      self.image.destRect = self.rect
    else:
      if self.child0 != None:
        self.child0.finalize()
      if self.child1 != None:
        self.child1.finalize()

  # Insert a single rect into the tree by recursing into the children.
  def insert(self, r, img):
    if self.child0 != None or self.child1 != None:
      newNode = self.child0.insert(r, img)
      if newNode != None:
        return newNode
      return self.child1.insert(r, img)
    else:
      if self.image != None:
        return None
      if r.width() > self.rect.width() or r.height() > self.rect.height():
        return None
      if r.width() == self.rect.width() and r.height() == self.rect.height():
        self.image = img
        return self
      self.child0 = Node()
      self.child1 = Node()
      dw = self.rect.width() - r.width()
      dh = self.rect.height() - r.height()
      if dw > dh:
        self.child0.rect = Rect(self.rect.xmin, self.rect.ymin, self.rect.xmin + r.width() - 1, self.rect.ymax)
        self.child1.rect = Rect(self.rect.xmin + r.width(), self.rect.ymin, self.rect.xmax, self.rect.ymax)
      else:
        self.child0.rect = Rect(self.rect.xmin, self.rect.ymin, self.rect.xmax, self.rect.ymin + r.height() - 1)
        self.child1.rect = Rect(self.rect.xmin, self.rect.ymin + r.height(), self.rect.xmax, self.rect.ymax)
      return self.child0.insert(r,img)

# An alternate heuristic for insertion order.
def imageArea(i):
  return i.rect.width() * i.rect.height()

# The used heuristic for insertion order, inserting images with the
# largest extent (in any direction) first.
def maxExtent(i):
  print "maxExtent"
  print [i.rect.width(), i.rect.height()]
  print max([i.rect.width(), i.rect.height()])
  return max([i.rect.width(), i.rect.height()])

def writeAtlas(images, atlasW, atlasH):
  atlasImg = Image.new('RGBA', [atlasW, atlasH])
  for i in images:
    atlasImg.paste(i.img, [int(i.img.destRect.xmin), int(i.img.destRect.ymin), int(i.img.destRect.xmax + 1), int(i.img.destRect.ymax + 1)])
  atlasImg.save(folderOutput + atlasBaseName + '.png')
  atlasImg = None

# Remove one pixel on each side of the images before dumping the CSS and JSON info.
def removeBorders(images):
  for i in images:
    i.img.destRect.xmin += 1
    i.img.destRect.ymin += 1
    i.img.destRect.xmax -= 1
    i.img.destRect.ymax -= 1

def addPx(value):
  pxVal = ""
  if value == 0:
    pxVal = str(value)
  else:
    pxVal = str(value) + 'px'
  return pxVal

def getTab():
  global tabBuf
  tab = ''
  if tabBuf != '':
    return tabBuf
  if useTabs:
    tab = '\t'
  else:
    for i in range(tabSize):
      tab += ' '
  tabBuf = tab
  return tab

def makeCssRule(selector, prop):
  rule = selector + '{\n'
  for i in prop:
    rule += getTab() + i + ':' + prop[i] + ";\n"
  rule += '}'
  return '\n' + rule

def writeCSS(images, atlasW, atlasH):
  css = open(folderOutput + atlasBaseName + '.css', 'w')
  css.write(makeCssRule(tileCssClass, {
    'position' : 'relative',
    'background' : 'url("' + atlasBaseName + '") no-repeat',
    'background-clip' : 'content-box'
  }))
  for i in images:
    rules = {
      'padding' : addPx(i.offset[1]) + ' ' + addPx(i.uncropped.width() - i.img.destRect.width() - i.offset[0]) + ' ' + addPx
    (i.uncropped.height() - i.img.destRect.height() - i.offset[1]) + ' ' + addPx(i.offset[0]),
      'width' : addPx(i.img.destRect.width()),
      'height' : addPx(i.img.destRect.height()),
      'background-position' : addPx(-i.img.destRect.xmin+i.offset[0]) + ' ' + addPx(-i.img.destRect.ymin+i.offset[1])
    }
    css.write(makeCssRule(tileCssClass + '.' + i.fileName.replace('.', '-'), rules))
  css.close()

originalIndex = 0

def addfolderInput(folderInput):
  global originalIndex
  folderInputList = os.listdir(folderInput);
  for folderInputName in folderInputList:
    if folderInputName[0] == '.':
      continue
    fullPath = folderInput + folderInputName
    if os.path.isdir(fullPath) == True:
      addfolderInput(fullPath)
    else:
      # Create source image structs and give them a unique index.
      print(fullPath)
      images.append(SourceImage(folderInput, folderInputName, originalIndex))
      originalIndex = originalIndex + 1

addfolderInput(folderInput)

# Sort the source images using the insert heuristic.
images.sort(None, maxExtent, True)

# Calculate the total area of all the source images and figure out a starting
# width and height to use when creating the atlas.
totalArea = 0
totalAreaUncropped = 0
for i in images:
  totalArea = totalArea + i.rect.width() * i.rect.height()
  totalAreaUncropped = totalAreaUncropped + i.uncropped.width() * i.uncropped.height()
width = math.floor(math.sqrt(totalArea))
height = math.floor(totalArea / width)

# Loop until success.
while True:
  # Set up an empty tree the size of the expected atlas.
  root = Node()
  root.rect = Rect(0,0,width,height)
  # Try to insert all the source images.
  ok = True
  for i in images:
    n = root.insert(i.rect, i.img)
    if n == None:
      ok = False
      break
  # If all source images fit break out of the loop.
  if ok:
    break

  # Increase the width or height by one and try again.
  if width > height:
    height = height + 1
  else:
    width = width + 1

# We've succeeded so write the dest rects to the source images.
root.finalize()
root = None

# Figure out the actual size of the atlas as it may not fill the entire area.
atlasW = 0
atlasH = 0
for i in images:
  atlasW = max([atlasW, i.img.destRect.xmax])
  atlasH = max([atlasH, i.img.destRect.ymax])
atlasW = int(atlasW+1)
atlasH = int(atlasH+1)
print('AtlasDimensions: ' + str(atlasW) + 'x' + str(atlasH) + '  :  ' + str(int(100.0 * (atlasW * atlasH)/totalAreaUncropped)) + '% of original')

writeAtlas(images, atlasW, atlasH)
writeCSS(images, atlasW, atlasH)
