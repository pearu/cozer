# How to specify race course? #

In `General Information/Race pattern` table column, specify the course using the following pattern:
```
<Lap length>/<Race time>
```
where lap length should be given in meters and race time in hours.
For example,
```
5000/6
```
specifies 6h endurance race on 5000m circuit.

# How to resume a race and enable auto save? #

Because of long race time, anything can happen, for instance, a electricity failure or timers computer goes crazy.

To minimize data loss, cozer supports auto saving data during a race. To enable it, in `Timer` page, toggle `Auto Save OFF` button to `Auto Save ON`. As a result, the cozer session will be saved every 30 seconds. Note that when you `Stop` a race, auto save will be disabled. So, after stopping the race, always manually save cozer session using `File/Save` menu.

When you need to resume a race, in `Timer` page, press `Resume` instead of `Start`.

# How to generate intermediate results? #

U.I.M. rules require that intermediate results are posted during a race.

In cozer, everytime you wish to generate a results report, in `Edit Race Record` page you must re-select all class/heat combinations currently running. Then go to `Reports` page and select `Endurance Full Final` as a report type.

# Can I use the same Cozer file for both endurance and circuit races #

No, you cannot. The main reason is that they have different scoring systems and cozer can use only one at the time.

# How to finish a race? #

Say, endurance race is for 6 hours. The race is finished when leader boat has completed 6 hours and after that has crossed the finish line
when the square flag is flown for the first time. Say, this happens
at 6h2min37sec. After that all other boats have to cross the finish
line within 10 minutes in order to score points.

By default, cozer sets the race time for 6 hours exactly. To obtain
correct results for the race report, in "Edit Race Records" you must shift the race stoppage line just a little bit before the leader
finishes. For the above example, the race stoppage should be set
to 6h2min36sec. Be careful not the shift the race stoppage line
over the time when leader finishes, otherwise the report will be incorrect.

Note that when the leader boat receives penalties after finishing, as a
result of it looses its leader position, the race stoppage line
should be still set at the time position when the square flag was
first flown.