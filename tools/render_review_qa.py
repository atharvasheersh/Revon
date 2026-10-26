"""Rasterise both publication renderings for full-page visual inspection."""
from pathlib import Path
import json
import pymupdf
from PIL import Image,ImageOps,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/review_revision/visual_qa'

def main():
    OUT.mkdir(exist_ok=True,parents=True);report={}
    for label,path in [('reference',ROOT/'paper/Revon Research Paper Springer Nature.pdf'),('word',ROOT/'output/review_revision/word-render.pdf')]:
        target=OUT/label;target.mkdir(exist_ok=True)
        pages=[]
        with pymupdf.open(path) as pdf:
            for i,page in enumerate(pdf,1):
                page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(target/f'page-{i:02}.png')
                thumb=Image.open(target/f'page-{i:02}.png').convert('RGB');thumb.thumbnail((459,594))
                card=Image.new('RGB',(479,624),'#dddddd');card.paste(thumb,((479-thumb.width)//2,24));ImageDraw.Draw(card).text((10,7),f'{label} page {i}',fill='black');pages.append(card)
            report[label]={'pages':len(pdf),'replacement_glyphs':sum(p.get_text().count('\ufffd') for p in pdf),'source':str(path)}
        for start in range(0,len(pages),4):
            sheet=Image.new('RGB',(958,1248),'#aaaabb')
            for j,card in enumerate(pages[start:start+4]):sheet.paste(card,((j%2)*479,(j//2)*624))
            sheet.save(target/f'sheet-{start//4+1:02}.png')
    (OUT/'render-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
