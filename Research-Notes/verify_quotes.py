import re,glob,sys
def norm(s):
    s=s.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"').replace(' ',' ')
    s=re.sub(r'[-‐-―]',' ',s)
    return re.sub(r'\s+',' ',s).lower().strip()
files=glob.glob('r1/dl/*.txt')+glob.glob('r1/pdfs/*.txt')+glob.glob('gs/*.txt')+glob.glob('r1/raw/*.txt')
txt={f:norm(open(f,errors='ignore').read()) for f in files}
Q=[
("1.1 end of economic life","These properties have high maintenance costs and are at the end of their economic life"),
("1.2 do nothing","Doing nothing is not considered an appropriate outcome for Waterloo South"),
("1.2 catalytic","Maintaining the existing site conditions would be ignoring the potential catalytic effects of the new Metro station"),
("1.3 mixed tenure","integrated and inclusive mixed-tenure community, replacing and providing fit for purpose social"),
("1.5 island","Today, the Estate is an 'island', physically disconnected from the surrounding context"),
("1.6 urban village","Waterloo will become a new urban village and local centre"),
("1.6 world class","create a new public domain that is the basis of a world class urban precinct"),
("1.7 44 years","average age of 44 years against a benchmark economic life of 60 years"),
("1.9 takeover","appointed the Secretary of the Department as the Planning Proposal Authority"),
("1.10 847","847 social housing, 227 affordable housing, and 1,938 market dwellings"),
("1.13 disadv","Targeted local responses to address spatial variations in socioeconomic disadvantage"),
("2.1 run down","run down 1950s-style accommodation"),
("2.1 need of change","a transformation of a part of Sydney which is in need of change"),
("2.3 change demographic","change the demographic"),
("2.3 push down","a very big downward push on anti-social behaviour"),
("2.4 failed experiment","failed social experiment"),
("2.5 attractive","one of the most attractive suburbs in inner Sydney"),
("2.6 cannibalising","cannibalising"),
("2.6 2773","only 2,773 new social housing properties of a planned 23,000"),
("2.7 model","a model for the future across metropolitan Sydney"),
("2.8 not functional","they're not functional communities"),
("2.8 home","Waterloo is my home, I want to stay here"),
("3.1 concentrated","many estates experience high levels of crime, unemployment, domestic violence"),
("3.3 right to return","will be given the right to return once the renewal is complete"),
("3.3 50","An increase in delivery of 50% social and affordable housing across the Waterloo Estate, up from 34%"),
("3.3 use-by","many of the buildings have reached their use-by date"),
("3.4 sense of place","vibrant and mixed inner-city community with a genuine sense of place"),
("3.5 indistinguishable","social and private housing are indistinguishable"),
("3.5 lifespan","nearing the end of their intended lifespan of 40-70 years"),
("3.6 viable","a commercially viable development"),
("3.9 stigmatisation","neighbourhood stigmatisation that comes with concentrations of disadvantage"),
("4.2 FSR","only if all of the following are satisfied"),
("4.6 return","Residents will be provided with the right of return"),
("5.5 vision","a vision for a vibrant new inner-city neighbourhood"),
("5.5 stalled","the Waterloo South renewal stalled for years"),
("5.7 world class","world-class housing right above a world-class metro"),
("5.6 30 years","staged over the next 30 years"),
("T1 deconcentrating","By deconcentrating disadvantage"),
("T2 gritty","gritty industrial area"),
("T3 industrial heartland","oldest industrial heartland"),
]
for lab,q in Q:
    nq=norm(q); hit=[f for f,t in txt.items() if nq in t]
    print(('OK  ' if hit else 'MISS'),lab,'|',(hit[0].split('/',1)[1] if hit else ''))
