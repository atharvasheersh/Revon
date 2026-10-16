from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

root=Path(__file__).resolve().parent
for style in ['Regular','Bold','Italic','BoldItalic']:
    original=TTFont(root/f'TeXGyreTermesX-{style}.otf')
    glyphset=original.getGlyphSet()
    glyphs={}
    for name in original.getGlyphOrder():
        pen=TTGlyphPen(glyphset)
        qp=Cu2QuPen(pen,max_err=0.25,reverse_direction=True)
        glyphset[name].draw(qp)
        glyphs[name]=pen.glyph()
    fb=FontBuilder(original['head'].unitsPerEm,isTTF=True)
    fb.setupGlyphOrder(original.getGlyphOrder())
    fb.setupCharacterMap(original.getBestCmap())
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(dict(original['hmtx'].metrics))
    fb.setupHorizontalHeader(ascent=original['hhea'].ascent,descent=original['hhea'].descent,lineGap=original['hhea'].lineGap)
    fb.font['name']=original['name']
    fb.font['OS/2']=original['OS/2']
    fb.setupPost(italicAngle=original['post'].italicAngle,underlinePosition=original['post'].underlinePosition,underlineThickness=original['post'].underlineThickness)
    for tag in ['GSUB','GPOS','GDEF','kern']:
        if tag in original:fb.font[tag]=original[tag]
    fb.font['head'].macStyle=original['head'].macStyle
    fb.save(root/f'TeXGyreTermesX-{style}.ttf')
    print(style,'converted with 0.25/1000 em curve tolerance')
