# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                          |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| cozer/\_\_init\_\_.py         |        1 |        0 |        0 |        0 |    100% |           |
| cozer/\_\_main\_\_.py         |       28 |       14 |        6 |        2 |     47% | 22, 25-47 |
| cozer/\_py2compat.py          |       30 |        0 |       14 |        0 |    100% |           |
| cozer/analyzer.py             |      632 |        7 |      372 |       24 |     96% |179-\>181, 181-\>173, 243-\>245, 245-\>298, 273-279, 284-\>286, 286-\>298, 315-\>317, 408-\>410, 410-\>402, 460-\>462, 462-\>426, 479-\>481, 510-\>426, 514-\>426, 518-\>426, 520-\>522, 522-\>426, 581-\>592, 590-\>592, 654-\>668, 657-\>668, 660-\>668, 666-\>668 |
| cozer/app/\_\_init\_\_.py     |        0 |        0 |        0 |        0 |    100% |           |
| cozer/app/classpart.py        |      291 |       23 |       70 |       15 |     87% |60, 67, 71-\>73, 73-\>81, 77-\>80, 82, 88, 98-\>exit, 156-158, 182-184, 187, 261-262, 306-\>305, 345-352, 365-\>exit, 368, 380-\>379, 381-\>380, 388, 397-\>401 |
| cozer/app/crashreport.py      |      191 |        7 |       38 |        5 |     95% |43, 157-\>164, 160-161, 258, 262, 301-302 |
| cozer/app/editor.py           |      417 |       33 |      126 |       15 |     90% |191-195, 213-227, 289-\>exit, 291-\>exit, 296-\>exit, 301-\>exit, 397-\>394, 412, 420-426, 475, 485, 507-\>exit, 514, 524, 526, 577, 580-\>579, 588-\>590 |
| cozer/app/grids.py            |      287 |       33 |       74 |       16 |     85% |52, 82-\>89, 84-\>89, 109, 112, 142, 149, 152-\>160, 156-\>158, 161, 167, 170-173, 176-179, 194-197, 259, 262-264, 266, 273-275, 280, 314-316, 339-\>342, 344-\>351, 364-365, 387-\>exit, 401-\>exit |
| cozer/app/main.py             |      446 |       23 |      130 |       26 |     91% |105, 129-\>131, 289-\>294, 299-304, 339, 348, 360, 363, 378, 380-\>exit, 458, 460-\>exit, 469, 477, 479, 574, 578, 587-\>585, 591-\>589, 612-613, 620-\>exit, 725, 739-\>745, 741-\>743, 768, 786, 788-\>exit |
| cozer/app/ruleset.py          |       82 |        0 |       38 |        3 |     98% |124-\>123, 130-\>126, 142-\>144 |
| cozer/app/timer.py            |      321 |       17 |       82 |       13 |     93% |54-55, 65-66, 73, 77, 81, 136, 169, 317, 323-\>322, 353, 360, 366, 370, 392, 394-395, 418-\>420, 435-\>exit |
| cozer/classes.py              |       12 |        0 |        0 |        0 |    100% |           |
| cozer/racepattern.py          |      214 |       10 |      128 |        9 |     94% |40, 146, 148, 162-163, 165, 168, 171, 184, 194, 259-\>245 |
| cozer/records.py              |       60 |        0 |       20 |        1 |     99% |   92-\>91 |
| cozer/reports/\_\_init\_\_.py |        7 |        0 |        0 |        0 |    100% |           |
| cozer/reports/common.py       |       60 |        5 |       24 |        3 |     90% |35, 47, 50, 66-67 |
| cozer/reports/endurance.py    |       68 |        1 |       22 |        2 |     97% |39-\>41, 45 |
| cozer/reports/final.py        |      128 |        1 |       46 |        3 |     98% |57-\>55, 72, 167-\>169 |
| cozer/reports/intermediate.py |       92 |        1 |       30 |        3 |     97% |22-\>24, 28, 122-\>99 |
| cozer/reports/labels.py       |        9 |        0 |        0 |        0 |    100% |           |
| cozer/reports/laps.py         |       49 |        1 |       14 |        2 |     95% |18-\>20, 23 |
| cozer/reports/latexish.py     |       74 |        4 |       44 |        4 |     93% |59, 78, 104, 114 |
| cozer/reports/letters.py      |       54 |        2 |       10 |        0 |     97% |     55-56 |
| cozer/reports/output.py       |       12 |        0 |        2 |        0 |    100% |           |
| cozer/reports/participants.py |       66 |        1 |       22 |        2 |     97% |15-\>17, 20 |
| cozer/reports/render.py       |       10 |        0 |        0 |        0 |    100% |           |
| cozer/store.py                |      209 |        4 |       68 |        2 |     98% |240-241, 280-\>282, 314-\>exit, 317-318 |
| cozer/validate.py             |       58 |        6 |       18 |        0 |     92% |40-41, 69-70, 109-110 |
| **TOTAL**                     | **3908** |  **193** | **1398** |  **150** | **93%** |           |


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