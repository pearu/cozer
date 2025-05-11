import time
import ampron
import urllib.request

led_name=["192x48", "128x32"][0]
try_run = not True

def main():
    display = ampron.make_display(name=led_name)
    text = 'Tallinna Veemoto Klubi 2024'
    url = ampron.make_url(display, id='main', layout='full', text=text)

    tm = time.localtime()
    current_time = tm.tm_mday, tm.tm_hour, tm.tm_min
    record = dict(day=current_time[0], hours=current_time[1], minutes=current_time[2],
                  layout='L1_2_3',
                  texts=dict(text1='Tallinna Veemoto Klubi 2024',
                             text2='Tallinna Veemoto Klubi 2024 Hooaja Lõpp',
                             text3='Tallinna Veemoto Klubi 2024'))
    url = ampron.make_url(display, id='main', layout=record['layout'], **record['texts'])

    urllib.request.urlopen(url)

if __name__ == "__main__":
    main()
