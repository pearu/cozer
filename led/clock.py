import time
import ampron
import urllib.request

led_name=["192x48", "128x32"][1]
try_run = not True

def main():
    display = ampron.make_display(name=led_name)

    if 0:
        ampron.update_config(display)

    last_url = None
    while 1:
        tm = time.localtime()
        tm = f"{tm.tm_hour:02}:{tm.tm_min:02}'{tm.tm_sec:02}"
        url = ampron.make_url(display, id='main', layout='full', text=tm)
        if last_url != url:
            print(f'{tm}', end=' ', flush=True)
            last_url = url
            if not try_run:
                urllib.request.urlopen(url)

        time.sleep(1)

if __name__ == "__main__":
    main()
