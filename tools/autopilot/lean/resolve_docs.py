import re,sys
for p in sys.argv[1:]:
  s=open(p).read()
  pat=re.compile(r'<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n',re.S)
  def r(m):
    o,t=m.group(1),m.group(2)
    t=t if t.endswith('\n') else t+'\n'
    if t.count('```')%2: t+='```\n'
    return t+'\n'+o
  s,n=pat.subn(r,s); open(p,'w').write(s); print(p,n,'odd-fences' if s.count('```')%2 else 'ok')
