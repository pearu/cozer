# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                          |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| cozer/\_\_init\_\_.py         |        1 |        0 |        0 |        0 |    100% |           |
| cozer/\_\_main\_\_.py         |       28 |       14 |        6 |        2 |     47% | 22, 25-47 |
| cozer/\_py2compat.py          |       30 |        0 |       14 |        0 |    100% |           |
| cozer/analyzer.py             |      630 |        7 |      370 |       24 |     96% |179-\>181, 181-\>173, 243-\>245, 245-\>298, 273-279, 284-\>286, 286-\>298, 315-\>317, 408-\>410, 410-\>402, 462-\>464, 464-\>427, 481-\>483, 512-\>427, 516-\>427, 520-\>427, 522-\>524, 524-\>427, 593-\>603, 601-\>603, 665-\>679, 668-\>679, 671-\>679, 677-\>679 |
| cozer/app/\_\_init\_\_.py     |        0 |        0 |        0 |        0 |    100% |           |
| cozer/app/broadcast.py        |       29 |        0 |        0 |        0 |    100% |           |
| cozer/app/classpart.py        |      588 |       80 |      192 |       37 |     82% |73, 108, 118, 140-\>139, 142-146, 150, 160-\>163, 169-176, 183-\>185, 186-187, 194, 203, 267, 281, 287, 290, 293-\>297, 295-\>297, 300, 301-\>303, 307-\>310, 312-\>314, 315, 334-\>exit, 372-374, 377-379, 412-\>417, 444-453, 477-479, 482, 556-557, 635-\>639, 637-\>639, 648-654, 657-664, 678-\>680, 703, 771-776, 781-791, 798-\>exit, 800, 815-\>exit, 818, 827-\>826, 829-830, 831-\>827, 849, 861 |
| cozer/app/crashreport.py      |      233 |        9 |       56 |        7 |     94% |47, 161-\>168, 164-165, 276, 280, 323, 334, 358-359 |
| cozer/app/editor.py           |      448 |       36 |      136 |       17 |     90% |194-198, 216-230, 292-\>exit, 294-\>exit, 299-\>exit, 304-\>exit, 416-\>413, 431, 439-445, 494, 504, 526-\>exit, 533, 543, 545, 602-603, 607, 622, 625-\>624, 633-\>635 |
| cozer/app/grids.py            |      421 |       75 |      108 |       20 |     77% |82, 121-125, 129, 132-\>140, 134-\>140, 136-\>138, 139, 141, 147, 150-153, 156-159, 174-177, 239, 242-244, 246, 253-255, 260, 268, 296-302, 331, 339, 360, 379-391, 394, 403-406, 463-\>466, 476-\>478, 506, 509-511, 517-518, 524-531, 555-\>exit, 571 |
| cozer/app/live.py             |       35 |        0 |       14 |        2 |     96% |44-\>48, 48-\>50 |
| cozer/app/main.py             |      736 |       96 |      196 |       36 |     84% |121, 145-\>147, 318-319, 335-\>340, 349-\>exit, 355-360, 438, 446-\>exit, 456, 465, 477, 480, 495, 497-\>exit, 596, 598-\>exit, 607, 615, 617, 716, 721, 730-\>728, 734-\>732, 755-756, 763-\>exit, 830-\>832, 838, 840, 856-\>858, 863-\>exit, 868-869, 876-901, 905-932, 947-972, 977, 1068, 1135, 1156-\>1158, 1196, 1214, 1216-\>exit |
| cozer/app/ruleset.py          |       83 |        0 |       38 |        3 |     98% |125-\>124, 131-\>127, 143-\>145 |
| cozer/app/timer.py            |      566 |       54 |      150 |       25 |     88% |92-93, 103-104, 111, 115, 119, 175, 357, 361, 434-\>exit, 455-\>exit, 513, 550, 564, 568, 597, 601-602, 615-\>612, 642-643, 647-\>649, 652-654, 662-663, 684-687, 696-\>698, 698-\>exit, 711-714, 723-730, 734-737, 748-750, 757, 773, 787-788, 797-799, 823-825 |
| cozer/app/update.py           |      106 |       21 |       44 |        7 |     77% |37-40, 62-67, 86-88, 98, 100-\>102, 116-121, 129-130, 196-\>200 |
| cozer/classes.py              |       15 |        0 |        0 |        0 |    100% |           |
| cozer/countries.py            |        5 |        1 |        0 |        0 |     80% |       227 |
| cozer/native.py               |      174 |        9 |       98 |       13 |     91% |64, 148, 155, 159, 160-\>exit, 162-\>exit, 164-\>exit, 167-169, 188, 228, 276-\>279, 287-\>290, 290-\>293 |
| cozer/phases.py               |      127 |        1 |       52 |        0 |     99% |        68 |
| cozer/qualification.py        |      100 |        2 |       36 |        2 |     97% |    95, 98 |
| cozer/raceclock.py            |       38 |        4 |        8 |        2 |     83% |90, 106-108 |
| cozer/racepattern.py          |      323 |       18 |      188 |       14 |     94% |34, 36, 63, 96, 98, 185-\>182, 216-217, 319, 333-334, 336, 339, 342, 355, 365, 374-375, 425, 439-\>418 |
| cozer/records.py              |       60 |        0 |       20 |        2 |     98% |77-\>71, 92-\>91 |
| cozer/reports/\_\_init\_\_.py |        8 |        0 |        0 |        0 |    100% |           |
| cozer/reports/common.py       |      102 |        4 |       42 |        4 |     94% |48, 62, 95, 98 |
| cozer/reports/endurance.py    |       95 |        1 |       36 |        2 |     98% |38-\>40, 53 |
| cozer/reports/final.py        |      203 |        1 |       78 |        4 |     98% |62-\>60, 234-\>236, 237, 266-\>268 |
| cozer/reports/intermediate.py |      123 |        0 |       46 |        1 |     99% | 150-\>121 |
| cozer/reports/labels.py       |       15 |        0 |        0 |        0 |    100% |           |
| cozer/reports/laps.py         |       54 |        0 |       16 |        0 |    100% |           |
| cozer/reports/latexish.py     |       74 |        4 |       44 |        4 |     93% |59, 78, 104, 114 |
| cozer/reports/letters.py      |       54 |        2 |       10 |        0 |     97% |     55-56 |
| cozer/reports/output.py       |       12 |        0 |        2 |        0 |    100% |           |
| cozer/reports/participants.py |       70 |        1 |       22 |        2 |     97% |17-\>19, 22 |
| cozer/reports/qsummary.py     |       71 |        3 |       26 |        5 |     92% |26-\>28, 36, 46, 101, 106-\>92 |
| cozer/reports/render.py       |       10 |        0 |        0 |        0 |    100% |           |
| cozer/seeding.py              |       89 |        0 |       36 |        1 |     99% | 144-\>142 |
| cozer/store.py                |      227 |        5 |       72 |        3 |     97% |98, 267-268, 317-\>319, 351-\>exit, 354-355 |
| cozer/validate.py             |      102 |       10 |       42 |        5 |     90% |65-66, 113-\>116, 118, 126-\>130, 132-133, 172-173, 182, 186-187, 208-\>193 |
| **TOTAL**                     | **6085** |  **458** | **2198** |  **244** | **90%** |           |


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