import re,sys
VOID={'input','img','br','meta','link','hr','path','rect','circle','line','polyline','polygon','ellipse','stop','use','source'}
UP='M6 15l6-6 6 6'; DOWN='M6 9l6 6 6-6'
CSS="summary{list-style:none;cursor:pointer}summary::-webkit-details-marker{display:none}summary:focus-visible{outline:2px solid #7750D4;outline-offset:-2px}details>summary .chev{transition:transform .15s}details:not([open])>summary .chev{transform:rotate(180deg)}"
BODY='<div style="padding: 0 16px 14px 60px; font-size: 12.5px; color: #4D5065; line-height: 1.5;">Section content opens here, with the same field layout as the open sections.</div>'
def parse(s):
    body_start=s.index('<x-dc>'); body_end=s.index('</x-dc>')
    els=[];stack=[]
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)\b[^>]*?(/?)>',s[body_start:body_end]):
        a=m.start()+body_start;b=m.end()+body_start;close,name,selfc=m.group(1),m.group(2).lower(),m.group(3)
        if close:
            while stack and els[stack[-1]]['name']!=name: stack.pop()
            if stack: i=stack.pop(); els[i]['end']=(a,b)
            continue
        e={'name':name,'start':(a,b),'end':None,'parent':stack[-1] if stack else None}
        els.append(e)
        if not selfc and name not in VOID: stack.append(len(els)-1)
    return els
def run(path):
    s=open(path).read()
    if '<details' in s: print('skip',path); return
    els=parse(s); edits=[]
    for i,e in enumerate(els):
        if e['name']!='svg': continue
        st=s[e['start'][0]:e['end'][1]] if e['end'] else ''
        if UP not in st and DOWN not in st or 'width="18"' not in s[e['start'][0]:e['start'][1]]: continue
        is_open=UP in st
        # chevron: add class, normalise to UP
        edits.append((e['start'][0],e['end'][1],st.replace('<svg ','<svg class="chev" ',1).replace(DOWN,UP)))
        h=els[e['parent']]; hs=s[h['start'][0]:h['start'][1]]
        tag=h['name']
        def sumtag(open_tag,extra=''):
            t=re.sub(r'^<'+tag,'<summary',open_tag)
            t=re.sub(r'\s(type|aria-expanded)="[^"]*"','',t)
            if extra: t=t.replace('style="','style="'+extra,1) if False else re.sub(r'style="([^"]*)"',lambda m:'style="'+m.group(1).rstrip('; ')+'; '+extra+'"',t,1)
            return t
        if is_open:
            c=els[h['parent']]; cs=s[c['start'][0]:c['start'][1]]
            edits.append((c['start'][0],c['start'][1],re.sub(r'^<'+c['name'],'<details open',cs)))
            edits.append((c['end'][0],c['end'][1],'</details>'))
            edits.append((h['start'][0],h['start'][1],sumtag(hs)))
            edits.append((h['end'][0],h['end'][1],'</summary>'))
        else:
            box='border-radius: 14px; box-shadow: 0 0 0 1px rgba(15,16,32,0.11); background: #FFFFFF; overflow: hidden;'
            edits.append((h['start'][0],h['start'][1],'<details style="'+box+'">'+sumtag(hs,'box-shadow: none; border-radius: 0;')))
            edits.append((h['end'][0],h['end'][1],'</summary>'+BODY+'</details>'))
    # chevron edit is nested inside header edits ranges? header start/end tags don't overlap svg range. sort desc
    edits.sort(key=lambda x:x[0],reverse=True)
    for a,b,t in edits: s=s[:a]+t+s[b:]
    s=s.replace('<style>\nbody{margin:0}','<style>\nbody{margin:0}\n'+CSS,1)
    open(path,'w').write(s); print('ok',path,len(edits))
for p in sys.argv[1:]: run(p)
