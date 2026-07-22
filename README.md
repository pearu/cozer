# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                          |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| cozer/\_\_init\_\_.py         |        1 |        0 |        0 |        0 |    100% |           |
| cozer/\_\_main\_\_.py         |       28 |       14 |        6 |        2 |     47% | 22, 25-47 |
| cozer/\_py2compat.py          |       30 |        0 |       14 |        0 |    100% |           |
| cozer/analyzer.py             |      631 |        7 |      372 |       24 |     96% |179-\>181, 181-\>173, 243-\>245, 245-\>298, 273-279, 284-\>286, 286-\>298, 315-\>317, 408-\>410, 410-\>402, 467-\>469, 469-\>427, 486-\>488, 517-\>427, 521-\>427, 525-\>427, 527-\>529, 529-\>427, 598-\>608, 606-\>608, 670-\>684, 673-\>684, 676-\>684, 682-\>684 |
| cozer/app/\_\_init\_\_.py     |        0 |        0 |        0 |        0 |    100% |           |
| cozer/app/broadcast.py        |       29 |        0 |        0 |        0 |    100% |           |
| cozer/app/classpart.py        |      588 |       80 |      192 |       37 |     82% |73, 108, 118, 140-\>139, 142-146, 150, 160-\>163, 169-176, 183-\>185, 186-187, 194, 203, 267, 281, 287, 290, 293-\>297, 295-\>297, 300, 301-\>303, 307-\>310, 312-\>314, 315, 334-\>exit, 372-374, 377-379, 412-\>417, 444-453, 477-479, 482, 556-557, 635-\>639, 637-\>639, 648-654, 657-664, 678-\>680, 703, 771-776, 781-791, 798-\>exit, 800, 815-\>exit, 818, 827-\>826, 829-830, 831-\>827, 849, 861 |
| cozer/app/crashreport.py      |      233 |        9 |       56 |        7 |     94% |47, 161-\>168, 164-165, 276, 280, 323, 334, 358-359 |
| cozer/app/editor.py           |      492 |       55 |      154 |       19 |     86% |196-200, 218-232, 254-255, 298, 301-302, 317-\>exit, 319-\>exit, 328, 331-344, 347-\>exit, 459-\>456, 474, 482-488, 541, 551, 573-\>exit, 580, 590, 592, 650-651, 655, 670, 673-\>672, 681-\>683 |
| cozer/app/grids.py            |      421 |       75 |      108 |       20 |     77% |82, 121-125, 129, 132-\>140, 134-\>140, 136-\>138, 139, 141, 147, 150-153, 156-159, 174-177, 239, 242-244, 246, 253-255, 260, 268, 296-302, 331, 339, 360, 379-391, 394, 403-406, 463-\>466, 476-\>478, 506, 509-511, 517-518, 524-531, 555-\>exit, 571 |
| cozer/app/live.py             |       37 |        0 |       16 |        2 |     96% |50-\>54, 54-\>56 |
| cozer/app/main.py             |      756 |       96 |      206 |       36 |     85% |129, 153-\>155, 326-327, 343-\>348, 357-\>exit, 363-368, 446, 454-\>exit, 464, 473, 485, 488, 503, 505-\>exit, 604, 606-\>exit, 615, 623, 625, 724, 729, 738-\>736, 742-\>740, 763-764, 771-\>exit, 838-\>840, 846, 848, 864-\>866, 871-\>exit, 876-877, 884-909, 913-940, 955-980, 985, 1076, 1171, 1192-\>1194, 1232, 1250, 1252-\>exit |
| cozer/app/ruleset.py          |       83 |        0 |       38 |        3 |     98% |125-\>124, 131-\>127, 143-\>145 |
| cozer/app/timer.py            |      594 |       55 |      162 |       28 |     88% |92-93, 103-104, 111, 115, 119, 186, 271, 385, 389, 463-\>465, 467-\>exit, 488-\>490, 491-\>exit, 545, 582, 596, 600, 629, 633-634, 647-\>644, 674-675, 681-\>684, 687-689, 697-698, 719-722, 731-\>733, 733-\>exit, 746-749, 758-765, 769-772, 783-785, 792, 808, 828-829, 838-840, 864-866 |
| cozer/app/update.py           |      106 |       21 |       44 |        7 |     77% |37-40, 62-67, 86-88, 98, 100-\>102, 116-121, 129-130, 196-\>200 |
| cozer/classes.py              |       15 |        0 |        0 |        0 |    100% |           |
| cozer/countries.py            |        5 |        1 |        0 |        0 |     80% |       227 |
| cozer/native.py               |      174 |        9 |       98 |       13 |     91% |64, 148, 155, 159, 160-\>exit, 162-\>exit, 164-\>exit, 167-169, 188, 228, 276-\>279, 287-\>290, 290-\>293 |
| cozer/phases.py               |      127 |        1 |       52 |        0 |     99% |        68 |
| cozer/qualification.py        |      100 |        2 |       36 |        2 |     97% |    95, 98 |
| cozer/raceclock.py            |       38 |        4 |        8 |        2 |     83% |90, 106-108 |
| cozer/racepattern.py          |      323 |       18 |      188 |       14 |     94% |34, 36, 63, 96, 98, 185-\>182, 216-217, 319, 333-334, 336, 339, 342, 355, 365, 374-375, 425, 439-\>418 |
| cozer/records.py              |       60 |        0 |       20 |        2 |     98% |77-\>71, 94-\>93 |
| cozer/reports/\_\_init\_\_.py |       10 |        0 |        0 |        0 |    100% |           |
| cozer/reports/common.py       |      102 |        4 |       42 |        4 |     94% |48, 62, 95, 98 |
| cozer/reports/endurance.py    |       95 |        1 |       36 |        2 |     98% |38-\>40, 53 |
| cozer/reports/final.py        |      203 |        1 |       78 |        4 |     98% |62-\>60, 234-\>236, 237, 266-\>268 |
| cozer/reports/inspection.py   |       77 |        0 |       14 |        0 |    100% |           |
| cozer/reports/intermediate.py |      123 |        0 |       46 |        1 |     99% | 150-\>121 |
| cozer/reports/labels.py       |       15 |        0 |        0 |        0 |    100% |           |
| cozer/reports/laps.py         |       54 |        0 |       16 |        0 |    100% |           |
| cozer/reports/latexish.py     |       74 |        4 |       44 |        4 |     93% |59, 78, 104, 114 |
| cozer/reports/letters.py      |       54 |        2 |       10 |        0 |     97% |     55-56 |
| cozer/reports/output.py       |       15 |        0 |        4 |        0 |    100% |           |
| cozer/reports/participants.py |       70 |        1 |       22 |        2 |     97% |17-\>19, 22 |
| cozer/reports/qsummary.py     |       71 |        3 |       26 |        5 |     92% |26-\>28, 36, 46, 101, 106-\>92 |
| cozer/reports/render.py       |       10 |        0 |        0 |        0 |    100% |           |
| cozer/reports/timetrial.py    |       88 |        5 |       36 |       10 |     88% |38-\>40, 49, 53, 65-\>61, 71-\>43, 87-\>89, 90, 97-\>99, 100, 105 |
| cozer/seeding.py              |       89 |        0 |       36 |        1 |     99% | 144-\>142 |
| cozer/store.py                |      227 |        5 |       72 |        3 |     97% |98, 267-268, 317-\>319, 351-\>exit, 354-355 |
| cozer/validate.py             |      114 |        7 |       52 |        3 |     94% |63-\>65, 74-\>85, 105-106, 156, 166-167, 206-207 |
| **TOTAL**                     | **6362** |  **480** | **2304** |  **257** | **90%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/pearu/cozer/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pearu/cozer/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fpearu%2Fcozer%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.