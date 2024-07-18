import time
import ampron
import urllib.request

led_name=["192x48", "128x32"][0]
try_run = True

participants = {
    "F-125": {
        10: 'HENRYK SYNORACKI',
        12: 'THOMAS MANTRIPP - GBR',
        21: 'MATTIA CALŽOLARI',
        22: 'JOONAS LEMBER - EST',
        25: 'SEBASTIAN KECINSKI - POL',
        27: 'DANIELE GHIRALDI',
        30: 'THOMAS TRABITŽSCH - GER',
        44: 'KRISTERS MUSTS - LAT',
        52: 'MICHAŁ KAUSA - POL',
        62: 'LADISLAV HERBANSKY - SVK',
        71: 'JURI SUVOROV',
        76: 'RASMUS LAURIK - EST',
        85: 'KRISTAPS STURIS - LAT',
        91: 'TOBIAS WAHLSTEN',
    },
    'GT-15': {
        4: 'PAUL RICHARD LAUR - EST',
        6: 'MARKUS KOIT - EST',
        8: 'TRISTAN KOIT - EST',
        9: 'ALFRED RAADIK - EST',
        19: 'HĒRA BIETE',
        33: 'OLIVER LÄÄNE',
        38: 'ROBIN LÄÄNE - EST',
        44: 'KEVIN SILLAOTS - EST',
        54: 'TONI KADE',
        69: 'JOOSEP PETERSON - EST',
        90: 'LUCAS TAURÉN',
    },
    'GT-30': {
        7: 'KÄROL SOODLA - EST',
        19: 'RENE SUUK - EST',
        20: 'DINIJA IVANOVA - LAT',
        21: 'KRZYSZTOF GAJEWSKI',
        24: 'NICO GUSTAVSON',
        26: 'ERIK SUUK - EST',
        29: 'OLIVER HORNTVEDT',
        47: 'MANTAS KULCINAVICIUS - LAT',
        50: 'MARCIN KOCIUCKI',
        60: 'MIKAEL BENGTSSON - SWE',
        61: 'ENDIJS BOKIS',
        65: 'ADRIAN OSTBY - NOR',
        77: 'KARLIS DEGAINIS - LAT',
        91: 'RAUNO PEET - EST',
        92: 'JENNI RANTALA',
        
    },
    'OSY-400': {
        7: 'KÄROL SOODLA - EST',
        11: 'PHILIPP ZEIBIG',
        19: 'RENE SUUK - EST',
        22: 'AKOS KASZA - HUN',
        # 23: 'PHILIP ZEIBIG - GER'
        24: 'BARTOSZ ROCHOWIAK',
        26: 'MARTINA BARBARINI - ITA',
        27: 'FRANŽ TROGLIO',
        28: 'BARBARA NIKOLETT BAZINSKA - SVK',
        29: 'CEZARY STRUMNIK - POL',
        37: 'JAMES BOWMAN',
        39: 'SIXTEN ERIKSSON',
        43: 'ARVYDAS DRANSEIKA - LIT',
        62: 'MIROSLAV BAZINSKY - SVK',
        65: 'JORIS GUŽĖ',
        88: 'JAAN ERIK BRANNO - EST',
        94: 'MICHAL POŽNIAK - POL',     
    }
}

roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X',
         11: 'XI', 12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI', 17: 'XVII', 18: 'XVIII', 19: 'XIX', 20: 'XX',
         21: 'XXI', 22: 'XXII', 23: 'XXIII', 24: 'XXIV', 25: 'XXV', 26: 'XXVI', 27: 'XXVII', 28: 'XXVIII', 29: 'XXIX', 30: 'XXX',
         }

order = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th', 6: '6th', 7: '7th', 8: '8th', 9: '9th', 10: '10th',
         11: '11th', 12: '12th', 13: '13th', 14: '14th', 15: '15th', 16: '16th', 17: '17th', 18: '18th', 19: '19th', 20: '20th',
         21: '21st', 22: '22nd', 23: '23rd', 24: '24th', 25: '25th', 26: '26th', 27: '27th', 28: '28th', 29: '29th', 30: '30th',
         }

TBD = "TBD"

# TODO: f("10 12") -> "1st: 10, 2nd: 12"

results = {
    "F-125": dict(
        timetrial=TBD, # "10: 1'35.1, 12: N/A",
        positions1=TBD, #"1st: 10, 2nd: 12",
        heat1=TBD, # "10: 400pts, 12: DNS",
        heat1r=TBD,
        positions2=TBD,
        heat2=TBD,
        heat2r=TBD,
        positions3=TBD,
        heat3=TBD,
        heat3r=TBD,
        positions4=TBD,
        heat4=TBD,
        heat4r=TBD,
    ),
    "GT-30": dict(
        timetrial=TBD,
        positions1=TBD,
        heat1=TBD,
        heat1r=TBD,
        positions2=TBD,
        heat2=TBD,
        heat2r=TBD,
        positions3=TBD,
        heat3=TBD,
        heat3r=TBD,
        positions4=TBD,
        heat4=TBD,
        heat4r=TBD,
    ),
    "GT-15": dict(
        timetrial=TBD,
        positions1=TBD,
        heat1=TBD,
        heat1r=TBD,
        positions2=TBD,
        heat2=TBD,
        heat2r=TBD,
        positions3=TBD,
        heat3=TBD,
        heat3r=TBD,
        positions4=TBD,
        heat4=TBD,
        heat4r=TBD,
    ),
    "OSY-400": dict(
        timetrial=TBD,
        positions1=TBD,
        heat1=TBD,
        heat1r=TBD,
        positions2=TBD,
        heat2=TBD,
        heat2r=TBD,
        positions3=TBD,
        heat3=TBD,
        heat3r=TBD,
        positions4=TBD,
        heat4=TBD,
        heat4r=TBD,
    ),
}


participants_text = {'all': ''}
for clsname, parts in participants.items():
    participants_text[clsname] = ", ".join(f'{boat}: {name}' for boat, name in parts.items())

    participants_text['all'] += f'{clsname} drivers:: {participants_text[clsname]}     ' 

title = "U.I.M. World Championship OSY-400, U.I.M. World Championship GT-30, U.I.M. European Championship F-125, Estonian Championship II round GT-15"

schedule = f"""
DAY: 18

@ 10:33
1: Testing 1 ...
2: {title}
3: The event starts tomorrow.

@ +0:01
11: GT-15
12: Drivers
2: {participants_text["GT-15"]}
3: The event starts tomorrow.

@ +0:01
11: GT-30
12: Drivers
2: {participants_text["GT-30"]}
3: The event starts tomorrow.

@ +0:01
11: F-125
12: Drivers
2: {participants_text["F-125"]}
3: The event starts tomorrow.

@ +0:01
11: OSY-400
12: Drivers
2: {participants_text["OSY-400"]}
3: The event starts tomorrow.

@ +0:01
11: All
12: Drivers
2: {participants_text["all"]}
3: The event starts tomorrow.

DAY: 19

@ 8:00
1: Welcome to Tallinn!
2: {title}
3: Pit area open 12:00-23:00, Race administration 12:00-20:00, Scrutineering 16:00-20:00, Organizing committee and organization meeting 20:00-20:30.

@ 12:00
1: Race administration open til 20:00
2: {title}
3: Pit area open til 23:00, Scrutineering 16:00-20:00, Organizing committee and organization meeting 20:00-20:30.

@ 16:00
1: Scrutineering open til 20:00
2: {title}
3: Pit area open til 23:00, Race administration open til 20:00, Organizing committee and organization meeting 20:00-20:30

@ 20:00
1: Organizing committee and organization meeting
2: {title}
3: Pit area is open til 23:00

@ 20:30
1: Have a pleasent evening!
2: {title}
3: Pit area is open til 23:00, <nextat>

@ 23:00
1: Night hours
2: {title}
3: Pit area is closed til 7:00 tomorrow

@ +1:00
1: Pleasant dreams... Zzz
2: {title}
3: Pit area is closed til 7:00

DAY: 20
@ 7:00
1: Good Morning!
2: {title}
3: Pit area open til 21:00, Race office open at 8:00

@ 8:00
1: Race office open
2: {title}
3: <nextat>

@ 8:30
1: Drivers' briefing
2: {title}
3: <nextat>

@ 9:00
11: GT-30
12: Free practice
2: {participants_text["GT-30"]}
3: <nextat>

@ 9:30
11: F-125
12: Free practice
2: {participants_text["F-125"]}
3: <nextat>

@ 10:00
11: OSY-400
12: Free practice
2: {participants_text["OSY-400"]}
3: <nextat>

@ 10:30
11: GT-15
12: Free practice
2: {participants_text["GT-15"]}
3: <nextat>

@ 10:45
11: F-125
12: Time-trial
2: {results["F-125"]["timetrial"]}
3: <nextat>

@ 11:00
11: GT-30
12: Time-trial
2: {results["GT-30"]["timetrial"]}
3: <nextat>

@ 11:15
11: GT-15
12: Time-trial
2: {results["GT-15"]["timetrial"]}
3: <nextat>

@ 11:30
11: OSY-400
12: Time-trial
2: {results["OSY-400"]["timetrial"]}
3: <nextat>

@ 12:00
1: Opening Ceremony
2: {title}
3: <nextat>

@ 12:15
1: Lunch Break 
2: F2 two seater demo
3: <nextat>

@ 12:55
11: GT-30
12: Prepare for heat 1
2: {results["GT-30"]["positions1"]}
3: <nextat>

@ 13:00
11: GT-30
12: Heat 1
2: {results["GT-30"]["heat1"]}
3: <nextat>

@ 13:25
11: F-125
12: Prepare for heat 1
2: {results["F-125"]["positions1"]}
3: <nextat>

@ 13:30
11: F-125
12: Heat 1
2: {results["F-125"]["heat1"]}
3: <nextat>

@ 13:55
11: GT-15
12: Prepare for heat 1
2: {results["GT-15"]["positions1"]}
3: <nextat>

@ 14:00
11: GT-15
12: Heat 1
2: {results["GT-15"]["heat1"]}
3: <nextat>

@ 14:25
11: OSY-400
12: Prepare for heat 1
2: {results["OSY-400"]["positions1"]}
3: <nextat>

@ 14:30
11: OSY-400
12: Heat 1
2: {results["OSY-400"]["heat1"]}
3: <nextat>

@ 14:55
11: GT-15
12: Prepare for heat 2
2: {results["GT-15"]["positions2"]}
3: <nextat>

@ 15:00
11: GT-15
12: Heat 2
2: {results["GT-15"]["heat2"]}
3: <nextat>

@ 15:25
11: F-125
12: Prepare for heat 2
2: {results["F-125"]["positions2"]}
3: <nextat>

@ 15:30
11: F-125
12: Heat 2
2: {results["F-125"]["heat2"]}
3: <nextat>

@ 15:55
11: GT-30
12: Prepare for heat 2
2: {results["GT-30"]["positions2"]}
3: <nextat>

@ 16:00
11: GT-30
12: Heat 2
2: {results["GT-30"]["heat2"]}
3: <nextat>

@ 16:30
1: F2 two seater demo
2: {title}
3: F2 two seater demo til 18:00, Organizing committee and organization meeting at 19:30

@ 18:00
1: Enjoy life!
2: {title}
3: <nextat>, Organizing committee and organization meeting at 19:30

@ 19:00
1: Race office closed
2: {title}
3: <nextat>

@ 19:30
1: Organizing committee and organization meeting
2: {title}
3: Pit area is open til 21:00

@ 20:00
1: Have a pleasent evening!
2: {title}
3: Pit area is open til 21:00, <nextat>

@ 21:00
1: Dj Kat Sun
2: {title}
3: Pit area is closed til 7:00 tomorrow, <nextat>

@ 23:00
1: Night hours
2: {title}
3: Pit area is closed til 7:00 tomorrow

@ +1:00
1: Pleasant dreams... Zzz
2: {title}
3: Pit area is closed til 7:00

DAY: 21
@  7:00
1: Good Morning!
2: {title}
3: <nextat>

@ 8:30
1: Race office open
2: {title}
3: <nextat>

@ 9:00
1: Drivers' briefing
2: {title}
3: <nextat>

@ 9:30
11: GT-30
12: Free practice
2: {participants_text["GT-30"]}
3: <nextat>

@ 9:45
11: F-125
12: Free practice
2: {participants_text["F-125"]}
3: <nextat>

@ 10:00
11: OSY-400
12: Free practice
2: {participants_text["OSY-400"]}
3: <nextat>

@ 10:25
11: GT-30
12: Prepare for heat 3
2: {results["GT-30"]["positions3"]}
3: <nextat>

@ 10:30
11: GT-30
12: Heat 3
2: {results["GT-30"]["heat3"]}
3: <nextat>

@ 10:55
11: F-125
12: Prepare for heat 3
2: {results["F-125"]["positions3"]}
3: <nextat>

@ 11:00
11: F-125
12: Heat 3
2: {results["F-125"]["heat3"]}
3: <nextat>

@ 11:25
11: OSY-400
12: Prepare for heat 2
2: {results["OSY-400"]["positions2"]}
3: <nextat>

@ 11:30
11: OSY-400
12: Heat 2
2: {results["OSY-400"]["heat2"]}
3: <nextat>

@ 11:55
11: GT-30
12: Prepare for heat 4
2: {results["GT-30"]["positions4"]}
3: <nextat>

@ 12:00
11: GT-30
12: Heat 4
2: {results["GT-30"]["heat4"]}
3: <nextat>

@ 12:30
1: Lunch Break 
2: F2 two seater demo
3: <nextat>

@ 13:25
11: OSY-400
12: Prepare for heat 3
2: {results["OSY-400"]["positions3"]}
3: <nextat>

@ 13:30
11: OSY-400
12: Heat 3
2: {results["OSY-400"]["heat3"]}
3: <nextat>

@ 13:55
11: F-125
12: Prepare for heat 4
2: {results["F-125"]["positions4"]}
3: <nextat>

@ 14:00
11: F-125
12: Heat 4
2: {results["F-125"]["heat4"]}
3: <nextat>

@ 14:25
11: GT-15
12: Prepare for heat 3
2: {results["GT-15"]["positions3"]}
3: <nextat>

@ 14:30
11: GT-15
12: Heat 3
2: {results["GT-15"]["heat3"]}
3: <nextat>

@ 15:25
11: OSY-400
12: Prepare for heat 4
2: {results["OSY-400"]["positions4"]}
3: <nextat>

@ 15:30
11: OSY-400
12: Heat 4
2: {results["OSY-400"]["heat4"]}
3: <nextat>

@ 17:30
1: Price Giving Ceremony
2: {title}
3: Congratulations to winners!

@ 18:00
1: Have a safe trip home! 
2: {title}
3:
"""



def get_records(schedule):
    day = 19
    hours = 0
    minutes = 0
    new_record = False
    texts = dict()
    record = None
    layout = ''
    for line in (schedule + '\n\n').splitlines():
        line = line.lstrip()
        if line.startswith('#'):
            continue
        if not line:
            if new_record:
                if 'text11' in texts:
                    nextat = f'{texts["text11"]} {texts["text12"]} at {hours:02}:{minutes:02}'
                elif 'text1' in texts:
                    nextat = f'{texts["text1"]} at {hours:02}:{minutes:02}'
                else:
                    print(f'No nextat info in {texts=}')
                    nextat = ''
                if record is not None:
                    for k, v in record['texts'].items():
                        record['texts'][k] = v.replace('<nextat>', nextat)
                record = dict(day=day, hours=hours, minutes=minutes, texts=texts, layout='L' + layout)
                yield record
                new_record = False
                texts = dict()
                layout = ''
            continue

        if line.startswith('DAY:'):
            day = int(line[4:].strip())
            continue
        
        if line.startswith('@'):
            new_record = True
            line = line[1:].lstrip()
            if line.startswith('+'):
                line = line[1:].lstrip()
                delta_hours, delta_minutes = map(int, line.split(':'))
                hours += delta_hours
                minutes += delta_minutes
                while minutes >= 60:
                    hours += 1
                    minutes -= 60
                while hours >= 24:
                    day += 1
                    hours -= 24
            else:
                hours, minutes = map(int, line.split(':'))
            continue

        if not new_record:
            print(f'Unexpected {line=}')
            continue

        kind, text = line.split(':', 1)
        if layout:
            layout += '_'
        layout += kind
        texts[f'text{kind}'] = text.strip()

    if record is not None:
        for k, v in record['texts'].items():
            record['texts'][k] = v.replace('<nextat>', '')




        
def main():

    display = ampron.make_display(name=led_name)

    if 0:
        ampron.update_config(display)

    layouts = {
        'L11_12_2_3': '''\
{text11} {text12}
{text2}
{text3}''',
        'L1_2_3': '''\
{text1}
{text2}
{text3}'''
    }

    records = list(get_records(schedule))
    for record in records:
        print()
        print("July {day}, {hours:02}:{minutes:02}".format(**record))
        print("-"*80)
        print(layouts[record['layout']].format(**record['texts']))
        print("-"*80)

    current_record = None
    next_time = None
    last_url = None
    while 1:
        tm = time.localtime()
        current_time = tm.tm_mday, tm.tm_hour, tm.tm_min

        record = dict(day=current_time[0], hours=current_time[1], minutes=current_time[2],
                      layout='L1_2_3',
                      texts=dict(text1='TBD', text2='TBD', text3='TBD'))
        for record_ in records:
            next_time = record_['day'], record_['hours'], record_['minutes']                
            if next_time > current_time:
                break
            record = record_
        if next_time is None:
            sleep_secs = 1
        else:
            sleep_secs = ((next_time[0] - current_time[0]) * 24 * 60 + (next_time[1] - current_time[1]) * 60 + next_time[2] - current_time[2]) * 60 - tm.tm_sec

        url = ampron.make_url(display, id='main', layout=record['layout'], **record['texts'])
        if last_url != url:
            print(f'{url=}')
            last_url = url
            if not try_run:
                urllib.request.urlopen(url)

            print('\nCURRENT\n')
            print("July {day}, {hours:02}:{minutes:02}  {layout}".format(**record))
            print("-"*80)
            print(layouts[record['layout']].format(**record['texts']))
            print("-"*80)

        if sleep_secs:
            print(f'{sleep_secs}', end=' ', flush=True)
        sleep = min(max(sleep_secs-1, 1), 1)
        time.sleep(sleep)

if __name__ == "__main__":
    main()
