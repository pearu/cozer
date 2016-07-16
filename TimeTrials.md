The following section titles correspond to tab names in the Cozer program.

## General Information ##
### Classes ###
To setup a time-trial race for a class, say, `FT-125`, create a new class that ends with `/T`. For the given example:
```
FT-125/T
```
The `Race Pattern` must declare a 2 lap race, first for warm-up lap (boat starts from yeti till the finish line) and the next for time-trial lap (boat makes one lap at full speed).
For the given example, the race pattern would read:
```
1*(1400+1500):1
```
where `1400` is the length of first lap (from starting yeti till finish line)
and `1500` is the full length of one lap.

  * Alternatively, when time-trial race consists of two laps and the best lap should be taken into account, use
```
1*(1400+2*1500):1
```

Warning: when using time-trial races, there must be always two rows per class in the Classes tab. For instance, `FT-125` is used for participants and actual race while `FT-125/T` is a special class name used for time-trial races only.

### Participants ###
No changes needed, all participants have the original class name, say, `FT-125`. Warning: Do not use time-trial class names for participants! For instance, when specifying `FT-125/T` as a class name for a participant, the Timer tab will not show the Id button for this particular participant.

### Races ###
Create a new race and specify the time-trial class name for `Class`, for instance,
```
FT-125/T
```
The `Heat` will be automatically set to
```
1t
```

## Timer ##
Select time-trial race and press `Start` button when the first boat leaves a yeti.

It is expected that all boats will take part of the time-trail race by subsequently starting from yeti, completing three laps (warm-up lap, time-trial lap, and safety lap), and return to yeti. The order of boats must be drawn at the drivers meeting. It is up to organizers to decide what is the frequency of letting the boats to time-trial race but normally the next boat can leave the yeti for warm-up lap immediately after the previous one has finished the time-trial lap.

During the time-trial race, **do not** `Stop` the race until all boats have completed their time-trial laps.

The operator using Cozer should press boat number button when boat leaves yeti and then each time a boat crosses finish line of time trial (don't click when boat returns yeti from safety lap). For each boat the operator should press the corresponding boat number button **at least three times** (first when leaving yeti, second when starting time-trial lap, and third when finishing time-trial lap). In case of more button clicks, only the **last two** button clicks are taken into account.

Note that the boat numbers do not change their locations during time-trial race, nor the boat numbers will change colors when clicking.

When time-trial race is completed, press `Stop` and save Cozer document.

  * In case of two-lap time-trial race, in above increase the counts accordingly.


## Edit Race Records ##

Select time-trial race and insert any needed comments to time-trial records.
Most probably only `Interruption` and `Did't start` comments are need at this stage of the event.

  * In case of two-lap time-trial, note that Cozer uses the lap time of the last lap by default (note to Cozer developers: this should be changed to the best lap). So, operator needs to manually edit the race record when the lap time of the first lap was best (smallest). For that, just disable the mark of the last lap. Recall that in time-trial races Cozer uses only the last two marks for computing the best lap time.

## Reports ##

Select `Intermediate` for report type and press `Preview` button to vied the time-trial race results. Note that the corresponding time-trial class and time-trial heat (`F-125/T` and `1t`) selections must be marked to see the results.
