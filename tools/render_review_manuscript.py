"""Typeset the review manuscript using the previously selected reference layout.

Uses retained licensed font assets and a preserved renderer, not a private
reference PDF or machine-specific temporary source. Word export is separate.
"""
from pathlib import Path
import json,re,shutil,hashlib

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'tmp/review_typesetting';WORK.mkdir(parents=True,exist_ok=True)
INPUTS=ROOT/'output/review_revision/publication_inputs.json'
metadata=json.loads(INPUTS.read_text(encoding='utf8'))
for path in (ROOT/'tools/publication_assets/reference_fonts').iterdir():
    if path.suffix in ['.pfb','.otf','.ttf']:shutil.copy2(path,WORK/path.name)
base=ROOT/'tools/publication_assets/reference_renderer_base.py'
code=base.read_text(encoding='utf8')
code=code.replace('ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parents[1]')
code=code.replace('TMP=Path(__file__).resolve().parent',"TMP=ROOT/'tmp/review_typesetting'")
code=code.replace("OUT=ROOT/'output'/'new format'","OUT=ROOT/'paper'")
code=code.replace("SOURCE=ROOT/'paper'/'Revon_Research_Paper_Discover_Computing.docx'","SOURCE=ROOT/'output/review_revision/Revon_Review_Revised_Source.docx'")
code=code.replace("STEM='Revon_Research_Paper_TFIDF_Reference_Format'","STEM='Revon Research Paper Springer'")
# No author-private reference PDF is needed to reproduce the retained geometry.
code=re.sub(r'^REFERENCE=.*$',"REFERENCE=None",code,flags=re.M)
code=code.replace("hashlib.sha256(REFERENCE.read_bytes()).hexdigest()","'reference-layout-measurements-retained-in-renderer'")
code=code.replace("'tables':11,'figures':7,'references':31","'tables':len(word.tables),'figures':len(word.inline_shapes),'references':len(refs)")
code=code.replace("(TMP/'audit.json').write_text","(ROOT/'output/review_revision/format_audit.json').write_text")
code=re.sub(r'widths=\{1:\[91,144,169\.5\].*?\}\[num\]', 'widths=TABLE_WIDTHS[num]',code,flags=re.S)
code=re.sub(r'widths=\{1:\[91,144,169\.5\].*?\}\[ti\]', 'widths=TABLE_WIDTHS[ti]',code,flags=re.S)
assert 'TABLE_WIDTHS[num]' in code and 'TABLE_WIDTHS[ti]' in code
# Standalone headings must travel with the following block in Word. Run-in
# headings retain normal pagination after their body paragraph is merged.
code=code.replace("p.paragraph_format.keep_with_next=False\n        if nxt is not None", "p.paragraph_format.keep_with_next=True\n        if nxt is not None")
code=code.replace("if np.style.name=='Normal' and np.text.strip():", "if np.style.name=='Normal' and np.text.strip():\n                p.paragraph_format.keep_with_next=False")
# Extract both appendices, including detailed methods, before declarations.
code=code.replace("end=next(i for i in range(start+1,len(records)) if records[i].get('style')=='Heading 1')", "end=next(i for i in range(start+1,len(records)) if records[i].get('text')=='DECLARATIONS')")
code=code.replace("if r.get('idx') in range(135,141)","if any(r.get('text','').startswith(label+':') for label in DECLARATION_LABELS)")
code=code.replace("if text.startswith('APPENDIX A.'):","if text.startswith('APPENDIX '):")
old="story.append(Paragraph('APPENDIX A: REPRODUCIBILITY',styles['center']))\nfor r in appendix[1:]: story.append(Paragraph(body_markup(r['text']),styles['body']))"
new='''for r in appendix:
    if r['kind']=='table':
        story.extend([make_table(r),Spacer(1,12)])
    elif r['text'].startswith('APPENDIX '):
        p=Paragraph(re.sub(r'^(APPENDIX [A-Z])\\. ',r'\\1: ',r['text']),styles['center']);p.keepWithNext=True;story.append(p)
    elif r.get('style')=='Caption':
        m=re.match(r'Table (\\d+)\\s+(.*)',r['text'])
        if m:
            label=Paragraph(sc('Table',SMALL,True)+' '+m[1],styles['tablabel']);label.keepWithNext=True
            caption=Paragraph(body_markup(m[2]),styles['tabcaption']);caption.keepWithNext=True
            story.extend([label,caption])
    else:story.append(Paragraph(body_markup(r['text']),styles['body']))'''
assert old in code;code=code.replace(old,new)
# Keep original node identities before heading/declaration processing changes them.
code=code.replace('word=Document(SOURCE)', '''word=Document(SOURCE)
all_nodes=list(word.element.body)
appendix_start=next(i for i,n in enumerate(all_nodes) if ''.join(n.itertext()).startswith('APPENDIX A.'))
appendix_end=next(i for i in range(appendix_start+1,len(all_nodes)) if ''.join(all_nodes[i].itertext()).startswith('DECLARATIONS'))
appendix_nodes=all_nodes[appendix_start:appendix_end]''')
start=code.index('# The supplied reference puts appendices after references.')
end=code.index('\ndef page_field(p):',start)
code=code[:start]+'''# The supplied reference puts appendices after references.
for node in appendix_nodes:
    if node.getparent() is not None:node.getparent().remove(node)
    word.element.body.insert(len(word.element.body)-1,node)
for ap in word.paragraphs:
    if ap.text.startswith('APPENDIX '):
        ap.text=re.sub(r'^(APPENDIX [A-Z])\\. ',r'\\1: ',ap.text)
        ap.alignment=WD_ALIGN_PARAGRAPH.CENTER
        ap.paragraph_format.first_line_indent=Pt(0);ap.paragraph_format.space_before=Pt(16)
        ap.paragraph_format.space_after=Pt(8);ap.paragraph_format.keep_with_next=True
        for run in ap.runs:run.font.name=family;run.font.size=Pt(11);run.bold=False
''' +code[end:]
# Correct URL tokenisation; the old expression incorrectly excluded letters l/t.
code=code.replace(r"(https?://[^\s&lt;]+)",r"(https?://[^\s<>]+)")
code=code.replace("t=linked(remap(t))", "t=linked(remap(t))\n    t=t.replace('Revon GitHub repository','<link href=\"https://github.com/atharvasheersh/Revon\" color=\"blue\">Revon GitHub repository</link>')\n    t=t.replace('Revon_Review_Revision_Reproducibility_20261016.zip','<link href=\"https://github.com/atharvasheersh/Revon/blob/main/paper/Revon_Review_Revision_Reproducibility_20261016.zip\" color=\"blue\">Revon_Review_Revision_Reproducibility_20261016.zip</link>')")
code=code.replace("docx=OUT/(STEM+'.docx');word.save(docx)", '''
from docx.opc.constants import RELATIONSHIP_TYPE as RT
def link_label(p,label,url):
    for run in list(p.runs):
        if label not in run.text:continue
        left,right=run.text.split(label,1);run.text=left
        link=OxmlElement('w:hyperlink');link.set(qn('r:id'),word.part.relate_to(url,RT.HYPERLINK,is_external=True))
        r=OxmlElement('w:r');pr=deepcopy(run._r.rPr) if run._r.rPr is not None else OxmlElement('w:rPr')
        color=OxmlElement('w:color');color.set(qn('w:val'),'0000FF');pr.append(color);r.append(pr)
        t=OxmlElement('w:t');t.text=label;r.append(t);link.append(r);run._r.addnext(link)
        tail=OxmlElement('w:r')
        if run._r.rPr is not None:tail.append(deepcopy(run._r.rPr))
        t=OxmlElement('w:t');t.text=right;t.set(qn('xml:space'),'preserve');tail.append(t);link.addnext(tail)
        break
for p in word.paragraphs:
    link_label(p,'https://github.com/atharvasheersh/Revon','https://github.com/atharvasheersh/Revon')
    link_label(p,'Revon GitHub repository','https://github.com/atharvasheersh/Revon')
    link_label(p,'Revon_Review_Revision_Reproducibility_20261016.zip','https://github.com/atharvasheersh/Revon/blob/main/paper/Revon_Review_Revision_Reproducibility_20261016.zip')
docx=OUT/(STEM+'.docx');word.save(docx)''')
namespace={'__file__':str(__file__),'__name__':'__main__','TABLE_WIDTHS':{int(k):v for k,v in metadata['table_widths'].items()},
  'DECLARATION_LABELS':['Funding','Competing interests','Author contributions','Ethics and consent to participate','Consent for publication','Data and code availability']}
exec(compile(code,str(base),'exec'),namespace)
audit=json.loads((ROOT/'output/review_revision/format_audit.json').read_text())
metadata['citation_mapping']=audit['citation_mapping'];metadata['format']=audit
metadata['figure_sha256']={i:hashlib.sha256(shape._inline.xml.encode()).hexdigest() for i,shape in enumerate(namespace['word'].inline_shapes,1)}
metadata['source_sha256']=audit['source_sha256']
(ROOT/'output/review_revision/publication_inputs.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
print('Reference-layout PDF and Word companion generated; render/visual QA still required.')
